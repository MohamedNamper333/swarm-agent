"""
Execution Context — globally unique IDs, delegation tracking, deadline propagation.

F-005: Process-Local Request IDs fix.
F-037: Missing Recursion/Delegation Limits fix.
F-032: No Deadline Propagation fix.
"""
import uuid
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Set, Any
from datetime import datetime, timezone, timedelta
from enum import Enum


class ExecutionState(str, Enum):
    CREATED = "created"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REQUIRES_HUMAN_REVIEW = "requires_human_review"


@dataclass(frozen=True)
class ExecutionIdentity:
    """Globally unique identifiers for an execution."""
    request_id: str          # UUIDv7 - client-facing request ID
    execution_id: str        # UUIDv7 - internal execution ID
    trace_id: str            # UUIDv7 - distributed trace ID
    correlation_id: str      # UUIDv7 - correlation across services
    causation_id: Optional[str] = None  # UUIDv7 - what caused this execution

    @classmethod
    def new(cls, causation_id: Optional[str] = None) -> "ExecutionIdentity":
        return cls(
            request_id=cls._generate_id(),
            execution_id=cls._generate_id(),
            trace_id=cls._generate_id(),
            correlation_id=cls._generate_id(),
            causation_id=causation_id,
        )

    @classmethod
    def child_of(cls, parent: "ExecutionIdentity") -> "ExecutionIdentity":
        """Create child execution with same trace/correlation, new execution_id."""
        return cls(
            request_id=parent.request_id,
            execution_id=cls._generate_id(),
            trace_id=parent.trace_id,
            correlation_id=parent.correlation_id,
            causation_id=parent.execution_id,
        )

    @staticmethod
    def _generate_id() -> str:
        # Use UUIDv7-like format (timestamp + random)
        # For true UUIDv7, use uuid.uuid7() in Python 3.13+
        return uuid.uuid4().hex


@dataclass
class ExecutionDeadline:
    """Deadline propagation for execution stages."""
    total_deadline_ms: int
    stage_budgets: Dict[str, int]  # stage_name -> budget_ms
    started_at: datetime
    stage_start_times: Dict[str, datetime] = field(default_factory=dict)

    def __post_init__(self):
        if self.started_at.tzinfo is None:
            self.started_at = self.started_at.replace(tzinfo=timezone.utc)

    def stage_started(self, stage: str) -> None:
        self.stage_start_times[stage] = datetime.now(timezone.utc)

    def remaining_for_stage(self, stage: str) -> int:
        """Get remaining ms for a specific stage."""
        budget = self.stage_budgets.get(stage, 0)
        if stage in self.stage_start_times:
            elapsed = (datetime.now(timezone.utc) - self.stage_start_times[stage]).total_seconds() * 1000
            return max(0, budget - int(elapsed))
        return budget

    def total_remaining_ms(self) -> int:
        """Get total remaining ms."""
        elapsed = (datetime.now(timezone.utc) - self.started_at).total_seconds() * 1000
        return max(0, self.total_deadline_ms - int(elapsed))

    def is_expired(self) -> bool:
        return self.total_remaining_ms() <= 0

    def check_and_raise(self, stage: str = "overall") -> None:
        """Raise if deadline exceeded."""
        if self.is_expired():
            raise TimeoutError(f"Execution deadline exceeded (stage: {stage})")


@dataclass
class DelegationContext:
    """Tracks agent delegation to prevent loops and enforce limits."""
    max_depth: int = 10
    max_hops: int = 20
    max_agents_per_execution: int = 50
    current_depth: int = 0
    visited_agents: Set[str] = field(default_factory=set)
    delegation_chain: list = field(default_factory=list)  # [(from_agent, to_agent, timestamp)]
    delegation_budget: int = 0

    def can_delegate(self, from_agent: str, to_agent: str) -> tuple[bool, str]:
        """Check if delegation is allowed. Returns (allowed, reason)."""
        # Check depth
        if self.current_depth >= self.max_depth:
            return False, f"Max delegation depth {self.max_depth} exceeded"

        # Check hops
        if len(self.delegation_chain) >= self.max_hops:
            return False, f"Max delegation hops {self.max_hops} exceeded"

        # Check agent count
        all_agents = self.visited_agents | {from_agent, to_agent}
        if len(all_agents) >= self.max_agents_per_execution:
            return False, f"Max agents per execution {self.max_agents_per_execution} exceeded"

        # Check for loops
        if to_agent in self.visited_agents:
            # Allow if not immediate loop
            for i, (f, t, _) in enumerate(self.delegation_chain):
                if t == to_agent and f == from_agent:
                    return False, f"Direct delegation loop detected: {from_agent} -> {to_agent}"

            # Check for longer cycles
            chain_agents = [f for f, _, _ in self.delegation_chain] + [self.delegation_chain[-1][1] if self.delegation_chain else ""]
            if to_agent in chain_agents:
                return False, f"Delegation cycle detected involving {to_agent}"

        return True, "ok"

    def record_delegation(self, from_agent: str, to_agent: str) -> None:
        """Record a delegation."""
        self.delegation_chain.append((from_agent, to_agent, datetime.now(timezone.utc)))
        self.visited_agents.add(from_agent)
        self.visited_agents.add(to_agent)
        self.current_depth = max(self.current_depth, len(self.delegation_chain))
        self.delegation_budget += 1


@dataclass
class ResourceBudget:
    """Per-execution resource budgets."""
    max_tokens: int = 100000
    max_tool_calls: int = 100
    max_runtime_seconds: int = 300
    max_cost: float = 100.0
    max_agents: int = 20
    max_depth: int = 10

    tokens_used: int = 0
    tool_calls_used: int = 0
    runtime_ms: int = 0
    cost_used: float = 0.0
    agents_spawned: int = 0

    def check_tokens(self, amount: int) -> bool:
        if self.tokens_used + amount > self.max_tokens:
            return False
        self.tokens_used += amount
        return True

    def check_tool_call(self) -> bool:
        if self.tool_calls_used + 1 > self.max_tool_calls:
            return False
        self.tool_calls_used += 1
        return True

    def check_agent(self) -> bool:
        if self.agents_spawned + 1 > self.max_agents:
            return False
        self.agents_spawned += 1
        return True


@dataclass
class ExecutionContext:
    """Complete execution context carrying all tracking information."""
    identity: ExecutionIdentity
    deadline: ExecutionDeadline
    delegation: DelegationContext
    resources: ResourceBudget
    tenant_id: str
    principal_id: str
    authorization_context: Optional[Any] = None
    state: ExecutionState = ExecutionState.CREATED
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def create(
        cls,
        tenant_id: str,
        principal_id: str,
        total_deadline_ms: int = 60000,
        stage_budgets: Optional[Dict[str, int]] = None,
        resource_budget: Optional[ResourceBudget] = None,
        authorization_context: Optional[Any] = None,
        causation_id: Optional[str] = None,
    ) -> "ExecutionContext":
        identity = ExecutionIdentity.new(causation_id=causation_id)
        deadline = ExecutionDeadline(
            total_deadline_ms=total_deadline_ms,
            stage_budgets=stage_budgets or {
                "safety": 5000,
                "board": 10000,
                "csuite": 10000,
                "routing": 2000,
                "execution": 33000,
            },
            started_at=datetime.now(timezone.utc),
        )
        delegation = DelegationContext()
        resources = resource_budget or ResourceBudget()
        return cls(
            identity=identity,
            deadline=deadline,
            delegation=delegation,
            resources=resources,
            tenant_id=tenant_id,
            principal_id=principal_id,
            authorization_context=authorization_context,
        )

    def transition_state(self, new_state: ExecutionState) -> None:
        """Transition execution state."""
        valid_transitions = {
            ExecutionState.CREATED: {ExecutionState.QUEUED, ExecutionState.RUNNING, ExecutionState.CANCELLED, ExecutionState.FAILED},
            ExecutionState.QUEUED: {ExecutionState.RUNNING, ExecutionState.CANCELLED, ExecutionState.FAILED},
            ExecutionState.RUNNING: {ExecutionState.SUCCEEDED, ExecutionState.FAILED, ExecutionState.REQUIRES_HUMAN_REVIEW, ExecutionState.CANCELLED},
            ExecutionState.REQUIRES_HUMAN_REVIEW: {ExecutionState.RUNNING, ExecutionState.CANCELLED, ExecutionState.FAILED},
        }
        if new_state not in valid_transitions.get(self.state, set()):
            raise ValueError(f"Invalid state transition: {self.state} -> {new_state}")
        self.state = new_state

    def is_terminal(self) -> bool:
        return self.state in (ExecutionState.SUCCEEDED, ExecutionState.FAILED, ExecutionState.CANCELLED)


# Thread-local storage for current execution context
_execution_context: threading.local = threading.local()


def get_current_context() -> Optional[ExecutionContext]:
    """Get current thread's execution context."""
    return getattr(_execution_context, "context", None)


def set_current_context(context: Optional[ExecutionContext]) -> None:
    """Set current thread's execution context."""
    _execution_context.context = context


def clear_current_context() -> None:
    """Clear current thread's execution context."""
    if hasattr(_execution_context, "context"):
        del _execution_context.context


__all__ = [
    "ExecutionState",
    "ExecutionIdentity",
    "ExecutionDeadline",
    "DelegationContext",
    "ResourceBudget",
    "ExecutionContext",
    "get_current_context",
    "set_current_context",
    "clear_current_context",
]
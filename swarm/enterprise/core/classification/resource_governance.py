"""
Resource Governance — F-036: Missing Resource Governance fix.

Per-execution resource budgets: max_tokens, max_tool_calls, max_runtime, max_cost, max_agents, max_depth.
Prevents recursive/unbounded agent execution.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Set, Callable
from enum import Enum
from datetime import datetime, timezone
import threading
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class ResourceType(str, Enum):
    TOKENS = "tokens"
    TOOL_CALLS = "tool_calls"
    RUNTIME_SECONDS = "runtime_seconds"
    COST_USD = "cost_usd"
    AGENTS = "agents"
    DEPTH = "depth"
    MEMORY_MB = "memory_mb"
    CPU_SECONDS = "cpu_seconds"


class LimitAction(str, Enum):
    """Action when limit exceeded."""
    THROTTLE = "throttle"       # Slow down
    DENY = "deny"               # Block operation
    TERMINATE = "terminate"     # Kill execution
    ALERT = "alert"             # Just alert


@dataclass(frozen=True)
class ResourceLimit:
    """Resource limit configuration."""
    resource_type: ResourceType
    limit: float
    action: LimitAction = LimitAction.DENY
    warning_threshold: float = 0.8  # 80% warning
    unit: str = ""


@dataclass
class ResourceUsage:
    """Current resource usage."""
    usage: Dict[ResourceType, float] = field(default_factory=dict)
    warnings_issued: Set[ResourceType] = field(default_factory=set)

    def get(self, resource_type: ResourceType) -> float:
        return self.usage.get(resource_type, 0.0)

    def add(self, resource_type: ResourceType, amount: float) -> None:
        self.usage[resource_type] = self.usage.get(resource_type, 0.0) + amount

    def set(self, resource_type: ResourceType, amount: float) -> None:
        self.usage[resource_type] = amount

    def get_percentage(self, resource_type: ResourceType, limit: float) -> float:
        if limit <= 0:
            return 0.0
        return self.get(resource_type) / limit


class ResourceBudget:
    """Per-execution resource budget with limits."""

    DEFAULT_LIMITS = {
        ResourceType.TOKENS: ResourceLimit(ResourceType.TOKENS, 100000, LimitAction.DENY, 0.8, "tokens"),
        ResourceType.TOOL_CALLS: ResourceLimit(ResourceType.TOOL_CALLS, 100, LimitAction.DENY, 0.8, "calls"),
        ResourceType.RUNTIME_SECONDS: ResourceLimit(ResourceType.RUNTIME_SECONDS, 300, LimitAction.TERMINATE, 0.8, "seconds"),
        ResourceType.COST_USD: ResourceLimit(ResourceType.COST_USD, 100.0, LimitAction.DENY, 0.8, "USD"),
        ResourceType.AGENTS: ResourceLimit(ResourceType.AGENTS, 20, LimitAction.DENY, 0.8, "agents"),
        ResourceType.DEPTH: ResourceLimit(ResourceType.DEPTH, 10, LimitAction.DENY, 0.9, "levels"),
        ResourceType.MEMORY_MB: ResourceLimit(ResourceType.MEMORY_MB, 1024, LimitAction.THROTTLE, 0.8, "MB"),
        ResourceType.CPU_SECONDS: ResourceLimit(ResourceType.CPU_SECONDS, 300, LimitAction.THROTTLE, 0.8, "seconds"),
    }

    def __init__(self, custom_limits: Dict[ResourceType, ResourceLimit] = None):
        self._limits = {**self.DEFAULT_LIMITS, **(custom_limits or {})}
        self._usage = ResourceUsage()
        self._lock = threading.RLock()
        self._start_time = datetime.now(timezone.utc)
        self._terminated = False
        self._termination_reason: Optional[str] = None

    def check_limit(self, resource_type: ResourceType, amount: float = 1.0) -> bool:
        """Check if adding amount would exceed limit."""
        with self._lock:
            if self._terminated:
                return False

            limit = self._limits.get(resource_type)
            if not limit:
                return True  # No limit = unlimited

            current = self._usage.get(resource_type)
            projected = current + amount

            if projected > limit.limit:
                self._handle_limit_exceeded(resource_type, limit, projected)
                return False

            # Check warning threshold
            if projected >= limit.limit * limit.warning_threshold and resource_type not in self._usage.warnings_issued:
                self._usage.warnings_issued.add(resource_type)
                logger.warning(
                    f"Resource {resource_type.value} at {projected/limit.limit*100:.1f}% "
                    f"(limit: {limit.limit} {limit.unit})"
                )

            return True

    def consume(self, resource_type: ResourceType, amount: float = 1.0) -> bool:
        """Consume resource. Returns True if allowed."""
        if not self.check_limit(resource_type, amount):
            return False

        with self._lock:
            self._usage.add(resource_type, amount)
            return True

    def release(self, resource_type: ResourceType, amount: float) -> None:
        """Release resource."""
        with self._lock:
            current = self._usage.get(resource_type)
            self._usage.set(resource_type, max(0, current - amount))

    def _handle_limit_exceeded(self, resource_type: ResourceType, limit: ResourceLimit, projected: float) -> None:
        logger.error(
            f"Resource limit exceeded: {resource_type.value} = {projected} "
            f"(limit: {limit.limit} {limit.unit}), action: {limit.action.value}"
        )

        if limit.action == LimitAction.TERMINATE:
            self._terminated = True
            self._termination_reason = f"Resource limit exceeded: {resource_type.value}"

    def is_terminated(self) -> bool:
        return self._terminated

    def get_termination_reason(self) -> Optional[str]:
        return self._termination_reason

    def get_usage(self, resource_type: ResourceType) -> float:
        return self._usage.get(resource_type)

    def get_all_usage(self) -> Dict[ResourceType, float]:
        return dict(self._usage.usage)

    def get_percentage(self, resource_type: ResourceType) -> float:
        limit = self._limits.get(resource_type)
        if not limit or limit.limit <= 0:
            return 0.0
        return self._usage.get_percentage(resource_type, limit.limit)

    def get_status(self) -> Dict[str, Any]:
        return {
            "terminated": self._terminated,
            "termination_reason": self._termination_reason,
            "usage": {rt.value: self._usage.get(rt) for rt in ResourceType},
            "limits": {rt.value: {"limit": l.limit, "unit": l.unit} for rt, l in self._limits.items()},
            "percentages": {rt.value: self.get_percentage(rt) for rt in ResourceType if rt in self._limits},
            "warnings": [rt.value for rt in self._usage.warnings_issued],
        }


class ResourceGovernor:
    """
    Global resource governor enforcing limits across all executions.
    
    Prevents:
    - Recursive/unbounded agent execution
    - Resource exhaustion
    - Cost overruns
    """

    def __init__(self):
        self._execution_budgets: Dict[str, ResourceBudget] = {}
        self._global_limits = ResourceBudget()
        self._lock = threading.RLock()
        self._tenant_limits: Dict[str, ResourceBudget] = defaultdict(ResourceBudget)

    def create_budget(
        self,
        execution_id: str,
        custom_limits: Dict[ResourceType, ResourceLimit] = None,
    ) -> ResourceBudget:
        """Create resource budget for execution."""
        with self._lock:
            budget = ResourceBudget(custom_limits)
            self._execution_budgets[execution_id] = budget
            return budget

    def get_budget(self, execution_id: str) -> Optional[ResourceBudget]:
        with self._lock:
            return self._execution_budgets.get(execution_id)

    def remove_budget(self, execution_id: str) -> bool:
        with self._lock:
            if execution_id in self._execution_budgets:
                del self._execution_budgets[execution_id]
                return True
            return False

    def check_global_limit(self, resource_type: ResourceType, amount: float = 1.0) -> bool:
        """Check global limit."""
        return self._global_limits.check_limit(resource_type, amount)

    def consume_global(self, resource_type: ResourceType, amount: float = 1.0) -> bool:
        """Consume from global budget."""
        return self._global_limits.consume(resource_type, amount)

    def get_global_status(self) -> Dict[str, Any]:
        return self._global_limits.get_status()

    def get_tenant_budget(self, tenant_id: str) -> ResourceBudget:
        with self._lock:
            return self._tenant_limits[tenant_id]

    def check_tenant_limit(self, tenant_id: str, resource_type: ResourceType, amount: float = 1.0) -> bool:
        return self._tenant_limits[tenant_id].check_limit(resource_type, amount)

    def consume_tenant(self, tenant_id: str, resource_type: ResourceType, amount: float = 1.0) -> bool:
        return self._tenant_limits[tenant_id].consume(resource_type, amount)

    def get_all_execution_status(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [
                {"execution_id": eid, **budget.get_status()}
                for eid, budget in self._execution_budgets.items()
            ]

    def terminate_execution(self, execution_id: str, reason: str) -> bool:
        """Force terminate execution."""
        with self._lock:
            budget = self._execution_budgets.get(execution_id)
            if budget:
                budget._terminated = True
                budget._termination_reason = reason
                return True
            return False


# Global governor
_resource_governor: Optional["ResourceGovernor"] = None
_rg_lock = threading.Lock()


def get_resource_governor() -> ResourceGovernor:
    global _resource_governor
    with _rg_lock:
        if _resource_governor is None:
            _resource_governor = ResourceGovernor()
        return _resource_governor


__all__ = [
    "ResourceType",
    "LimitAction",
    "ResourceLimit",
    "ResourceUsage",
    "ResourceBudget",
    "ResourceGovernor",
    "get_resource_governor",
]
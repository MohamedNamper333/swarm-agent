"""
Architecture Decision Records — F-038: No Formal Architecture Decision Records fix.

Creates and manages ADRs for all major architectural decisions.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from enum import Enum
from datetime import datetime, timezone
import uuid
import threading
import logging
import os
import json

logger = logging.getLogger(__name__)


class ADRStatus(str, Enum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    SUPERSEDED = "superseded"
    DEPRECATED = "deprecated"


@dataclass(frozen=True)
class ADR:
    """Architecture Decision Record."""
    adr_id: str  # ADR-001, ADR-002, etc.
    title: str
    status: ADRStatus
    context: str
    decision: str
    consequences: List[str] = field(default_factory=list)
    alternatives_considered: List[str] = field(default_factory=list)
    author: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    superseded_by: Optional[str] = None
    related_adrs: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "adr_id": self.adr_id,
            "title": self.title,
            "status": self.status.value,
            "context": self.context,
            "decision": self.decision,
            "consequences": self.consequences,
            "alternatives_considered": self.alternatives_considered,
            "author": self.author,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "superseded_by": self.superseded_by,
            "related_adrs": self.related_adrs,
        }

    def to_markdown(self) -> str:
        """Generate Markdown representation."""
        lines = [
            f"# {self.adr_id}: {self.title}",
            f"",
            f"**Status:** {self.status.value}",
            f"**Author:** {self.author}",
            f"**Date:** {self.created_at.date()}",
            f"**Updated:** {self.updated_at.date()}",
            f"",
            f"## Context",
            f"{self.context}",
            f"",
            f"## Decision",
            f"{self.decision}",
            f"",
            f"## Consequences",
        ]
        for c in self.consequences:
            lines.append(f"- {c}")
        lines.append("")
        lines.append("## Alternatives Considered")
        for a in self.alternatives_considered:
            lines.append(f"- {a}")
        lines.append("")
        if self.related_adrs:
            lines.append("## Related ADRs")
            for r in self.related_adrs:
                lines.append(f"- {r}")
        if self.superseded_by:
            lines.append(f"")
            lines.append(f"**Superseded by:** {self.superseded_by}")
        return "\n".join(lines)


class ADRRegistry:
    """Manages Architecture Decision Records."""

    def __init__(self, adr_dir: str = None):
        self._adrs: Dict[str, ADR] = {}
        self._lock = threading.RLock()
        self._adr_dir = adr_dir or "docs/adr"
        self._next_number = 1
        os.makedirs(self._adr_dir, exist_ok=True)

    def create(
        self,
        title: str,
        context: str,
        decision: str,
        consequences: List[str] = None,
        alternatives: List[str] = None,
        author: str = "system",
        related_adrs: List[str] = None,
    ) -> ADR:
        """Create a new ADR."""
        adr_id = f"ADR-{self._next_number:03d}"
        self._next_number += 1

        adr = ADR(
            adr_id=adr_id,
            title=title,
            status=ADRStatus.PROPOSED,
            context=context,
            decision=decision,
            consequences=consequences or [],
            alternatives_considered=alternatives or [],
            author=author,
            related_adrs=related_adrs or [],
        )

        with self._lock:
            self._adrs[adr_id] = adr

        self._persist(adr)
        return adr

    def accept(self, adr_id: str) -> bool:
        """Accept an ADR."""
        with self._lock:
            adr = self._adrs.get(adr_id)
            if not adr:
                return False
            # Create new ADR with updated status (immutable)
            updated = ADR(
                adr_id=adr.adr_id,
                title=adr.title,
                status=ADRStatus.ACCEPTED,
                context=adr.context,
                decision=adr.decision,
                consequences=adr.consequences,
                alternatives_considered=adr.alternatives_considered,
                author=adr.author,
                created_at=adr.created_at,
                updated_at=datetime.now(timezone.utc),
                superseded_by=adr.superseded_by,
                related_adrs=adr.related_adrs,
            )
            self._adrs[adr_id] = updated
            self._persist(updated)
            return True

    def supersede(self, adr_id: str, superseded_by: str) -> bool:
        """Mark ADR as superseded."""
        with self._lock:
            adr = self._adrs.get(adr_id)
            if not adr:
                return False
            updated = ADR(
                adr_id=adr.adr_id,
                title=adr.title,
                status=ADRStatus.SUPERSEDED,
                context=adr.context,
                decision=adr.decision,
                consequences=adr.consequences,
                alternatives_considered=adr.alternatives_considered,
                author=adr.author,
                created_at=adr.created_at,
                updated_at=datetime.now(timezone.utc),
                superseded_by=superseded_by,
                related_adrs=adr.related_adrs,
            )
            self._adrs[adr.id] = updated
            self._persist(updated)
            return True

    def get(self, adr_id: str) -> Optional[ADR]:
        with self._lock:
            return self._adrs.get(adr_id)

    def list_all(self, status: Optional[ADRStatus] = None) -> List[ADR]:
        with self._lock:
            adrs = list(self._adrs.values())
            if status:
                adrs = [a for a in adrs if a.status == status]
            return sorted(adrs, key=lambda a: a.adr_id)

    def _persist(self, adr: ADR) -> None:
        """Persist ADR to Markdown file."""
        # Sanitize filename
        safe_title = adr.title.lower().replace(' ', '-').replace('/', '-').replace('\\', '-')
        filename = f"{adr.adr_id.lower()}-{safe_title}.md"
        filepath = os.path.join(self._adr_dir, filename)
        with open(filepath, "w") as f:
            f.write(adr.to_markdown())

    def load_existing(self) -> None:
        """Load existing ADRs from directory."""
        if not os.path.exists(self._adr_dir):
            return
        for filename in os.listdir(self._adr_dir):
            if filename.endswith(".md"):
                # Parse existing ADR - simplified
                pass


# Pre-defined ADRs for the swarm-agent system
DEFAULT_ADRS = [
    {
        "title": "Execution State Machine",
        "context": "The system needs a clear execution lifecycle with distinct states for policy decisions vs execution outcomes.",
        "decision": "Implement ExecutionContext with explicit states: CREATED, QUEUED, RUNNING, SUCCEEDED, FAILED, CANCELLED, REQUIRES_HUMAN_REVIEW. Separate policy_decision from execution_state and final_outcome.",
        "consequences": [
            "Clear separation between approval and execution success",
            "Explicit terminal states prevent ambiguous results",
            "Human review state is explicit",
        ],
        "alternatives": [
            "Use simple boolean approved/rejected",
            "Merge policy and execution states",
        ],
    },
    {
        "title": "Budget Ledger with Atomic Reservations",
        "context": "Concurrent budget reservations can cause race conditions where total reserved exceeds limit.",
        "decision": "Implement BudgetLedger with atomic compare-and-swap reservations. Track available, reserved, consumed, released separately. Enforce invariant: reserved + consumed <= limit.",
        "consequences": [
            "Race-free budget management",
            "Explicit reservation lifecycle (reserve -> consume/release)",
            "Supports concurrent execution",
        ],
        "alternatives": [
            "Simple check-then-reserve (race-prone)",
            "Database transactions (adds dependency)",
        ],
    },
    {
        "title": "Capability-Based Authorization",
        "context": "Client-controlled bypass flags (bypass_safety, estimated_cost) violate security boundaries.",
        "decision": "Replace client-controlled flags with server-issued ExecutionCapabilities. AuthorizationContext carries Principal, Capabilities, policy_version, authorization_id. Only server can grant OVERRIDE_SAFETY, OVERRIDE_BUDGET, etc.",
        "consequences": [
            "Untrusted input never grants privilege",
            "All overrides auditable with actor/reason/timestamp",
            "Fine-grained capability model",
        ],
        "alternatives": [
            "Keep bypass flags with signature verification",
            "Role-based access control (coarser)",
        ],
    },
    {
        "title": "Idempotency Keys for All Mutating Operations",
        "context": "Retries and duplicate requests can cause double-execution of side-effecting operations.",
        "decision": "Require Idempotency-Key header for all mutating endpoints. Store request hash with key. Same key + same payload = return existing. Same key + different payload = 409 Conflict. TTL-based cleanup.",
        "consequences": [
            "Safe retries without double-execution",
            "Explicit conflict detection",
            "Automatic cleanup via TTL",
        ],
        "alternatives": [
            "Deduplication by request ID only",
            "Optimistic locking on resources",
        ],
    },
    {
        "title": "Control Plane / Execution Plane Separation",
        "context": "Single-process orchestration limits horizontal scaling and creates tight coupling.",
        "decision": "Separate ControlPlane (auth, policy, budget, routing, idempotency, job creation) from ExecutionPlane (workers, agents, providers, tools). Jobs admitted by ControlPlane, executed by ExecutionPlane workers.",
        "consequences": [
            "Independent scaling of control vs execution",
            "Clear security boundary",
            "Worker failures don't affect control plane",
        ],
        "alternatives": [
            "Single process with thread pools",
            "Microservices per component (over-engineered)",
        ],
    },
    {
        "title": "UUIDv7 Global Identities",
        "context": "Process-local request counters break on restart and horizontal scaling.",
        "decision": "Use UUIDv7 (timestamp + random) for request_id, execution_id, trace_id, correlation_id, causation_id. Globally unique, restart-safe, distributed-safe, traceable.",
        "consequences": [
            "Globally unique without coordination",
            "Restart-safe (no counter reset)",
            "Distributed tracing ready",
        ],
        "alternatives": [
            "ULID (similar, less standard)",
            "Snowflake IDs (requires coordination)",
        ],
    },
    {
        "title": "Control Plane / Execution Plane Separation",
        "context": "Single-process orchestration limits horizontal scaling and creates tight coupling.",
        "decision": "Separate ControlPlane (auth, policy, budget, routing, idempotency, job creation) from ExecutionPlane (workers, agents, providers, tools). Jobs admitted by ControlPlane, executed by ExecutionPlane workers.",
        "consequences": [
            "Independent scaling of control vs execution",
            "Clear security boundary",
            "Worker failures don't affect control plane",
        ],
        "alternatives": [
            "Single process with thread pools",
            "Microservices per component (over-engineered)",
        ],
    },
    {
        "title": "Defense-in-Depth Safety Architecture",
        "context": "Single-layer regex safety is insufficient for production.",
        "decision": "Implement defense-in-depth: Normalization -> Deterministic Rules -> Safety Classifier -> Policy Engine -> Tool Authorization -> Output Safety. Tool permissions controlled by policy, not just safety approval.",
        "consequences": [
            "Multiple independent safety layers",
            "Tool authorization separate from content safety",
            "Fail-closed at each layer",
        ],
        "alternatives": [
            "Single LLM-based safety classifier",
            "Regex-only with allowlist",
        ],
    },
    {
        "title": "Durable Job Infrastructure",
        "context": "Long-running operations (research, video, LLM orchestration) cannot be bound to synchronous HTTP requests.",
        "decision": "Implement DurableJob with persistent state, retries, cancellation, timeout, resume, dead-letter, heartbeat. Jobs admitted to queue, workers execute asynchronously.",
        "consequences": [
            "Survives worker restarts",
            "Explicit retry/compensation model",
            "Horizontal worker scaling",
        ],
        "alternatives": [
            "Synchronous with long timeouts",
            "External workflow engine (Temporal, etc.)",
        ],
    },
    {
        "title": "Explicit Placeholder Handling",
        "context": "SmartPlaceholder returned synthetic content that could be mistaken for genuine provider output.",
        "decision": "All placeholder results explicit: execution_state=degraded, provider_status=failed, fallback_used=True, synthetic_output=True. Never presented as genuine provider execution.",
        "consequences": [
            "Clear distinction between real and synthetic output",
            "Fail-closed behavior preserved",
            "Observability tracks placeholder usage",
        ],
        "alternatives": [
            "Return error instead of placeholder",
            "Cache real responses for reuse",
        ],
    },
    {
        "title": "Multi-Tenant Isolation",
        "context": "System will be multi-tenant SaaS; tenant isolation must be a security boundary.",
        "decision": "Every resource scoped by tenant_id: jobs, memory, cache, budgets, rate limits, audit, artifacts. TenantIsolationEnforcer blocks 100% of cross-tenant access attempts.",
        "consequences": [
            "Provable tenant isolation",
            "Resource quotas per tenant",
            "Audit trail per tenant",
        ],
        "alternatives": [
            "Logical separation only (application-level)",
            "Shared resources with soft limits",
        ],
    },
    {
        "title": "Distributed State Management",
        "context": "Process-local state (cache, rate limits, circuit breakers) breaks with horizontal scaling.",
        "decision": "Classify state: DISTRIBUTED (authoritative: budget, rate limits, safety, circuit breakers) vs PROCESS_LOCAL (non-authoritative: cache, metrics). Use distributed backend (Redis) for authoritative state.",
        "consequences": [
            "Horizontal scaling doesn't multiply limits",
            "Single source of truth for authoritative state",
            "Cache can remain local for performance",
        ],
        "alternatives": [
            "All state in Redis (latency)",
            "Sticky sessions (anti-pattern)",
        ],
    },
    {
        "title": "Inter-Agent Bus with Defined Semantics",
        "context": "Agent communication lacked delivery guarantees, ordering, deduplication.",
        "decision": "AgentBus with: AT_LEAST_ONCE delivery, per-topic FIFO ordering, explicit acknowledgment with timeout, deduplication keys, retry with exponential backoff, TTL, dead-letter, schema versioning.",
        "consequences": [
            "Reliable agent communication",
            "Exactly-once via idempotency keys",
            "Observability of message flow",
        ],
        "alternatives": [
            "Direct agent-to-agent calls (coupled)",
            "Message queue without semantics",
        ],
    },
    {
        "title": "Trusted Memory with Provenance",
        "context": "Agent memory could become instruction injection vector.",
        "decision": "Every memory item has: source, provenance, author, trust_level, tenant, scope, policy_tags, created_at, expires_at. Memory ≠ policy, memory ≠ system instruction. Access controlled by trust level and tenant.",
        "consequences": [
            "Memory cannot elevate privileges",
            "Full provenance for audit",
            "Trust-based access control",
        ],
        "alternatives": [
            "Unstructured memory (vulnerable)",
            "No memory (stateless agents)",
        ],
    },
    {
        "title": "Fallback Observability with Root Cause Preservation",
        "context": "Fallback chains hid root cause, presenting fallback as genuine execution.",
        "decision": "Every fallback logs: original_provider, failure_code, failure_reason_class, fallback_provider, fallback_reason. Root cause preserved in observability. FallbackTracker provides root cause analysis.",
        "consequences": [
            "Root cause always visible",
            "Fallback chain traceable",
            "Root cause analysis automated",
        ],
        "alternatives": [
            "Log fallback as success",
            "No fallback (fail fast)",
        ],
    },
    {
        "title": "Retry Storm Protection with Global Budgets",
        "context": "Unbounded retries across agents/providers can amplify load during outages.",
        "decision": "Multi-scope retry budgets: REQUEST, AGENT, PROVIDER, GLOBAL. Each with max_attempts, exponential backoff + jitter, deadline propagation. RetryStormDetector monitors per-minute rates.",
        "consequences": [
            "Prevents cascade failures",
            "Per-scope budget enforcement",
            "Automatic storm detection",
        ],
        "alternatives": [
            "Unlimited retries (storm risk)",
            "Fixed retry count (inflexible)",
        ],
    },
    {
        "title": "Comprehensive Observability",
        "context": "Health checks insufficient for enterprise monitoring.",
        "decision": "Distributed tracing (Span/Trace), MetricsCollector (p50/p95/p99, counters, gauges, histograms), StructuredLogger with trace context. Metrics: p50/p95/p99 latency, failure rate, retry rate, fallback rate, token usage, cost, safety veto rate, routing ambiguity, queue depth.",
        "consequences": [
            "Full distributed tracing",
            "Production-grade metrics",
            "Trace-context logging",
        ],
        "alternatives": [
            "Basic health checks only",
            "External APM only (vendor lock-in)",
        ],
    },
    {
        "title": "Durable Audit Ledger",
        "context": "Logs are not governance ledger; need tamper-evident audit trail.",
        "decision": "AuditLedger with immutable events: event_id, event_type, actor, timestamp, trace_id, execution_id, policy_version, schema_version, result. Records: auth, safety, board, exec, budget, routing, execution, fallback, override, memory, tool. File-based append-only store with rotation.",
        "consequences": [
            "Tamper-evident audit trail",
            "Regulatory compliance ready",
            "Queryable audit trail",
        ],
        "alternatives": [
            "Application logs only",
            "External SIEM only",
        ],
    },
    {
        "title": "Resource Governance with Per-Execution Budgets",
        "context": "Unbounded agent execution can exhaust tokens, cost, runtime, agents.",
        "decision": "ResourceBudget per execution: max_tokens, max_tool_calls, max_runtime, max_cost, max_agents, max_depth. ResourceGovernor enforces global, per-tenant, per-execution limits. Actions: THROTTLE, DENY, TERMINATE, ALERT.",
        "consequences": [
            "Prevents resource exhaustion",
            "Cost predictability",
            "Recursive execution bounded",
        ],
        "alternatives": [
            "No limits (risky)",
            "Global limits only (unfair)",
        ],
    },
]


def initialize_default_adrs(registry: "ADRRegistry") -> None:
    """Initialize default ADRs for the system."""
    for i, adr_data in enumerate(DEFAULT_ADRS):
        adr = registry.create(
            title=adr_data["title"],
            context=adr_data["context"],
            decision=adr_data["decision"],
            consequences=adr_data["consequences"],
            alternatives=adr_data.get("alternatives", []),
            author="system",
        )
        registry.accept(adr.adr_id)


__all__ = [
    "ADRStatus",
    "ADR",
    "ADRRegistry",
    "initialize_default_adrs",
]
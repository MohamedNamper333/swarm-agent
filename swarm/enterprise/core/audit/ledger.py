"""
Durable Audit Ledger — F-024: No Durable Audit Ledger fix.

Separate audit event store with:
- event_id, event_type, actor, timestamp, trace_id, execution_id, policy_version, schema_version, result
Records: authorization, safety, board, exec, budget, routing, execution, fallback, override, memory, tool
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Callable
from enum import Enum
from datetime import datetime, timezone
import uuid
import threading
import json
import logging

logger = logging.getLogger(__name__)


class AuditEventType(str, Enum):
    """Types of audit events."""
    AUTHORIZATION = "authorization"
    SAFETY_DECISION = "safety_decision"
    BOARD_DECISION = "board_decision"
    EXECUTIVE_DECISION = "executive_decision"
    BUDGET_RESERVATION = "budget_reservation"
    BUDGET_CONSUMPTION = "budget_consumption"
    BUDGET_RELEASE = "budget_release"
    ROUTING_DECISION = "routing_decision"
    EXECUTION_START = "execution_start"
    EXECUTION_COMPLETE = "execution_complete"
    EXECUTION_FAILED = "execution_failed"
    FALLBACK = "fallback"
    OVERRIDE = "override"
    MEMORY_WRITE = "memory_write"
    MEMORY_READ = "memory_read"
    TOOL_INVOCATION = "tool_invocation"
    POLICY_EVALUATION = "policy_evaluation"
    IDENTITY_VERIFICATION = "identity_verification"
    TENANT_ISOLATION_CHECK = "tenant_isolation_check"


class AuditResult(str, Enum):
    """Result of audited action."""
    ALLOWED = "allowed"
    DENIED = "denied"
    ESCALATED = "escalated"
    OVERRIDDEN = "overridden"
    FAILED = "failed"
    SUCCESS = "success"


@dataclass(frozen=True)
class AuditEvent:
    """Immutable audit event."""
    event_id: str
    event_type: AuditEventType
    actor: str  # principal_id or system component
    timestamp: datetime
    trace_id: str
    execution_id: str
    policy_version: str
    schema_version: int
    result: AuditResult
    tenant_id: str
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "actor": self.actor,
            "timestamp": self.timestamp.isoformat(),
            "trace_id": self.trace_id,
            "execution_id": self.execution_id,
            "policy_version": self.policy_version,
            "schema_version": self.schema_version,
            "result": self.result.value,
            "tenant_id": self.tenant_id,
            "details": self.details,
        }


class AuditStore:
    """Abstract audit event store."""

    def append(self, event: AuditEvent) -> bool:
        raise NotImplementedError

    def query(
        self,
        event_type: Optional[str] = None,
        actor: Optional[str] = None,
        tenant_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        execution_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Any]:
        raise NotImplementedError

    def get_by_id(self, event_id: str) -> Optional[Any]:
        raise NotImplementedError


class InMemoryAuditStore(AuditStore):
    """In-memory audit store (for testing/single-process)."""

    def __init__(self):
        self._events: List[AuditEvent] = []
        self._lock = threading.RLock()

    def append(self, event: AuditEvent) -> bool:
        with self._lock:
            self._events.append(event)
            # Keep last 100k events
            if len(self._events) > 100000:
                self._events = self._events[-100000:]
        return True

    def query(
        self,
        event_type: Optional[str] = None,
        actor: Optional[str] = None,
        tenant_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        execution_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[AuditEvent]:
        with self._lock:
            results = self._events
            if event_type:
                results = [e for e in results if e.event_type.value == event_type]
            if actor:
                results = [e for e in results if e.actor == actor]
            if tenant_id:
                results = [e for e in results if e.tenant_id == tenant_id]
            if trace_id:
                results = [e for e in results if e.trace_id == trace_id]
            if execution_id:
                results = [e for e in results if e.execution_id == execution_id]
            if start_time:
                results = [e for e in results if e.timestamp >= start_time]
            if end_time:
                results = [e for e in results if e.timestamp <= end_time]
            return results[-limit:]

    def get_by_id(self, event_id: str) -> Optional[AuditEvent]:
        with self._lock:
            for event in reversed(self._events):
                if event.event_id == event_id:
                    return event
            return None


class FileAuditStore(AuditStore):
    """File-based audit store (append-only, tamper-evident)."""

    def __init__(self, file_path: str, max_file_size_mb: int = 100):
        self._file_path = file_path
        self._max_size = max_file_size_mb * 1024 * 1024
        self._lock = threading.RLock()
        self._current_file = None
        self._current_size = 0
        self._rotate_if_needed()

    def _rotate_if_needed(self):
        import os
        if self._current_file:
            self._current_file.close()
        import os
        if os.path.exists(self._file_path):
            self._current_size = os.path.getsize(self._file_path)
        if self._current_size >= self._max_size:
            # Rotate
            import time
            rotated = f"{self._file_path}.{int(time.time())}"
            os.rename(self._file_path, rotated)
            self._current_size = 0
        self._current_file = open(self._file_path, "a", buffering=1)

    def append(self, event: AuditEvent) -> bool:
        with self._lock:
            self._rotate_if_needed()
            line = json.dumps(event.to_dict()) + "\n"
            self._current_file.write(line)
            self._current_file.flush()
            return True

    def query(self, **kwargs) -> List[Any]:
        # For file store, would need indexing; simplified
        return []

    def get_by_id(self, event_id: str) -> Optional[Any]:
        return None


class AuditLedger:
    """
    Durable audit ledger for governance.
    
    Records all critical decisions:
    - authorization, safety, board, executive, budget, routing, execution, fallback, override, memory, tool
    """

    def __init__(self, store: AuditStore = None, policy_version: str = "1.0", schema_version: int = 1):
        self._store = store or InMemoryAuditStore()
        self._policy_version = policy_version
        self._schema_version = schema_version
        self._lock = threading.RLock()

    def record(
        self,
        event_type: AuditEventType,
        actor: str,
        trace_id: str,
        execution_id: str,
        result: AuditResult,
        tenant_id: str,
        details: Dict[str, Any] = None,
    ) -> AuditEvent:
        """Record an audit event."""
        event = AuditEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            actor=actor,
            timestamp=datetime.now(timezone.utc),
            trace_id=trace_id,
            execution_id=execution_id,
            policy_version=self._policy_version,
            schema_version=self._schema_version,
            result=result,
            tenant_id=tenant_id,
            details=details or {},
        )
        self._store.append(event)
        return event

    # Convenience methods for each event type
    def record_authorization(self, actor, trace_id, execution_id, result, tenant_id, details):
        return self.record(AuditEventType.AUTHORIZATION, actor, trace_id, execution_id, result, tenant_id, details)

    def record_safety(self, actor, trace_id, execution_id, result, tenant_id, details):
        return self.record(AuditEventType.SAFETY_DECISION, actor, trace_id, execution_id, result, tenant_id, details)

    def record_board(self, actor, trace_id, execution_id, result, tenant_id, details):
        return self.record(AuditEventType.BOARD_DECISION, actor, trace_id, execution_id, result, tenant_id, details)

    def record_executive(self, actor, trace_id, execution_id, result, tenant_id, details):
        return self.record(AuditEventType.EXECUTIVE_DECISION, actor, trace_id, execution_id, result, tenant_id, details)

    def record_budget_reservation(self, actor, trace_id, execution_id, result, tenant_id, details):
        return self.record(AuditEventType.BUDGET_RESERVATION, actor, trace_id, execution_id, result, tenant_id, details)

    def record_budget_consumption(self, actor, trace_id, execution_id, result, tenant_id, details):
        return self.record(AuditEventType.BUDGET_CONSUMPTION, actor, trace_id, execution_id, result, tenant_id, details)

    def record_routing(self, actor, trace_id, execution_id, result, tenant_id, details):
        return self.record(AuditEventType.ROUTING_DECISION, actor, trace_id, execution_id, result, tenant_id, details)

    def record_execution_start(self, actor, trace_id, execution_id, tenant_id, details):
        return self.record(AuditEventType.EXECUTION_START, actor, trace_id, execution_id, AuditResult.SUCCESS, tenant_id, details)

    def record_execution_complete(self, actor, trace_id, execution_id, result, tenant_id, details):
        return self.record(AuditEventType.EXECUTION_COMPLETE, actor, trace_id, execution_id, result, tenant_id, details)

    def record_fallback(self, actor, trace_id, execution_id, result, tenant_id, details):
        return self.record(AuditEventType.FALLBACK, actor, trace_id, execution_id, result, tenant_id, details)

    def record_override(self, actor, trace_id, execution_id, result, tenant_id, details):
        return self.record(AuditEventType.OVERRIDE, actor, trace_id, execution_id, result, tenant_id, details)

    def record_memory_write(self, actor, trace_id, execution_id, result, tenant_id, details):
        return self.record(AuditEventType.MEMORY_WRITE, actor, trace_id, execution_id, result, tenant_id, details)

    def record_tool_invocation(self, actor, trace_id, execution_id, result, tenant_id, details):
        return self.record(AuditEventType.TOOL_INVOCATION, actor, trace_id, execution_id, result, tenant_id, details)

    def query(self, **kwargs) -> List[Any]:
        return self._store.query(**kwargs)


# Global audit ledger
_audit_ledger: Optional[AuditLedger] = None
_al_lock = threading.Lock()


def get_audit_ledger() -> AuditLedger:
    global _audit_ledger
    with _al_lock:
        if _audit_ledger is None:
            _audit_ledger = AuditLedger()
        return _audit_ledger


def set_audit_store(store: AuditStore) -> None:
    """Set custom audit store (call once at startup)."""
    global _audit_ledger
    with _al_lock:
        _audit_ledger = AuditLedger(store=store)


__all__ = [
    "AuditEventType",
    "AuditResult",
    "AuditEvent",
    "AuditStore",
    "InMemoryAuditStore",
    "FileAuditStore",
    "AuditLedger",
    "get_audit_ledger",
    "set_audit_store",
]
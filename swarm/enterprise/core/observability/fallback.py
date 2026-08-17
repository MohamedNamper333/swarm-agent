"""
Fallback Observability — F-030: Fallback Can Hide Root Cause fix.

Every fallback logs: original_provider, failure_code, failure_reason_class, fallback_provider, fallback_reason.
Root cause preserved in observability.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from enum import Enum
from datetime import datetime, timezone
import uuid
import threading
import logging

logger = logging.getLogger(__name__)


class FailureReasonClass(str, Enum):
    """Classification of failure reasons."""
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    PROVIDER_TIMEOUT = "provider_timeout"
    PROVIDER_RATE_LIMITED = "provider_rate_limited"
    PROVIDER_ERROR = "provider_error"
    INVALID_REQUEST = "invalid_request"
    QUOTA_EXHAUSTED = "quota_exhausted"
    AUTHENTICATION_FAILED = "authentication_failed"
    NETWORK_ERROR = "network_error"
    UNKNOWN = "unknown"


class FallbackReason(str, Enum):
    """Reason for fallback."""
    PRIMARY_FAILED = "primary_failed"
    PRIMARY_TIMEOUT = "primary_timeout"
    PRIMARY_RATE_LIMITED = "primary_rate_limited"
    PRIMARY_QUOTA_EXHAUSTED = "primary_quota_exhausted"
    CIRCUIT_OPEN = "circuit_open"
    MANUAL_OVERRIDE = "manual_override"


@dataclass(frozen=True)
class FallbackEvent:
    """Record of a fallback occurrence."""
    event_id: str
    timestamp: datetime
    chain_id: str  # Identifier for the fallback chain
    step: int  # Which fallback step (1=primary, 2=fallback1, etc.)

    # Original provider info
    original_provider: str
    original_model: str
    failure_code: str
    failure_reason_class: FailureReasonClass
    failure_message: str

    # Fallback info
    fallback_provider: str
    fallback_model: str
    fallback_reason: FallbackReason
    fallback_step: int  # Which fallback was used

    # Context
    request_id: str
    execution_id: str
    tenant_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "chain_id": self.chain_id,
            "step": self.step,
            "original_provider": self.original_provider,
            "original_model": self.original_model,
            "failure_code": self.failure_code,
            "failure_reason_class": self.failure_reason_class.value,
            "failure_message": self.failure_message,
            "fallback_provider": self.fallback_provider,
            "fallback_model": self.fallback_model,
            "fallback_reason": self.fallback_reason.value,
            "fallback_step": self.fallback_step,
            "request_id": self.request_id,
            "execution_id": self.execution_id,
            "tenant_id": self.tenant_id,
            "metadata": self.metadata,
        }


@dataclass
class FallbackChainContext:
    """Context for a fallback chain execution."""
    chain_id: str
    request_id: str
    execution_id: str
    tenant_id: str
    primary_provider: str
    primary_model: str
    fallback_providers: List[tuple[str, str]]  # [(provider, model), ...]
    events: List[FallbackEvent] = field(default_factory=list)
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    final_provider: Optional[str] = None
    final_model: Optional[str] = None
    success: bool = False


class FallbackTracker:
    """Tracks fallback events for observability."""

    def __init__(self):
        self._chains: Dict[str, FallbackChainContext] = {}
        self._events: List[FallbackEvent] = []
        self._lock = threading.RLock()
        self._metrics = {
            "total_fallbacks": 0,
            "by_failure_class": {},
            "by_fallback_reason": {},
            "by_provider": {},
            "chains_completed": 0,
            "chains_failed": 0,
        }

    def start_chain(
        self,
        request_id: str,
        execution_id: str,
        tenant_id: str,
        primary_provider: str,
        primary_model: str,
        fallback_providers: List[tuple[str, str]],
    ) -> str:
        """Start tracking a fallback chain."""
        chain_id = str(uuid.uuid4())
        context = FallbackChainContext(
            chain_id=chain_id,
            request_id=request_id,
            execution_id=execution_id,
            tenant_id=tenant_id,
            primary_provider=primary_provider,
            primary_model=primary_model,
            fallback_providers=fallback_providers,
        )
        with self._lock:
            self._chains[chain_id] = context
        return chain_id

    def record_fallback(
        self,
        chain_id: str,
        step: int,
        original_provider: str,
        original_model: str,
        failure_code: str,
        failure_reason_class: FailureReasonClass,
        failure_message: str,
        fallback_provider: str,
        fallback_model: str,
        fallback_reason: FallbackReason,
        fallback_step: int,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> FallbackEvent:
        """Record a fallback event."""
        chain = self._chains.get(chain_id)
        if not chain:
            logger.warning(f"Fallback chain {chain_id} not found")
            # Create minimal event
            chain = FallbackChainContext(
                chain_id=chain_id,
                request_id="unknown",
                execution_id="unknown",
                tenant_id="unknown",
                primary_provider=original_provider,
                primary_model=original_model,
                fallback_providers=[],
            )

        event = FallbackEvent(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc),
            chain_id=chain_id,
            step=step,
            original_provider=original_provider,
            original_model=original_model,
            failure_code=failure_code,
            failure_reason_class=failure_reason_class,
            failure_message=failure_message[:500],  # Truncate
            fallback_provider=fallback_provider,
            fallback_model=fallback_model,
            fallback_reason=fallback_reason,
            fallback_step=fallback_step,
            request_id=chain.request_id,
            execution_id=chain.execution_id,
            tenant_id=chain.tenant_id,
            metadata=metadata or {},
        )

        with self._lock:
            chain.events.append(event)
            self._events.append(event)
            self._metrics["total_fallbacks"] += 1
            self._metrics["by_failure_class"][failure_reason_class.value] = \
                self._metrics["by_failure_class"].get(failure_reason_class.value, 0) + 1
            self._metrics["by_fallback_reason"][fallback_reason.value] = \
                self._metrics["by_fallback_reason"].get(fallback_reason.value, 0) + 1
            self._metrics["by_provider"][original_provider] = \
                self._metrics["by_provider"].get(original_provider, 0) + 1

        return event

    def complete_chain(
        self,
        chain_id: str,
        final_provider: str,
        final_model: str,
        success: bool,
    ) -> Optional[FallbackChainContext]:
        """Mark chain as complete."""
        with self._lock:
            chain = self._chains.get(chain_id)
            if not chain:
                return None
            chain.completed_at = datetime.now(timezone.utc)
            chain.final_provider = final_provider
            chain.final_model = final_model
            chain.success = success

            if success:
                self._metrics["chains_completed"] += 1
            else:
                self._metrics["chains_failed"] += 1

            return chain

    def get_chain(self, chain_id: str) -> Optional[FallbackChainContext]:
        with self._lock:
            return self._chains.get(chain_id)

    def get_events(
        self,
        chain_id: Optional[str] = None,
        request_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[FallbackEvent]:
        with self._lock:
            events = self._events
            if chain_id:
                events = [e for e in events if e.chain_id == chain_id]
            if request_id:
                events = [e for e in events if e.request_id == request_id]
            if tenant_id:
                events = [e for e in events if e.tenant_id == tenant_id]
            return events[-limit:]

    def get_metrics(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._metrics)

    def get_root_cause_analysis(self, chain_id: str) -> Optional[Dict[str, Any]]:
        """Analyze root cause for a chain."""
        chain = self.get_chain(chain_id)
        if not chain or not chain.events:
            return None

        # Find the first failure (root cause)
        first_event = chain.events[0]
        return {
            "chain_id": chain_id,
            "root_cause": {
                "provider": first_event.original_provider,
                "model": first_event.original_model,
                "failure_class": first_event.failure_reason_class.value,
                "failure_code": first_event.failure_code,
                "message": first_event.failure_message,
            },
            "fallback_chain": [
                {
                    "step": e.step,
                    "fallback_provider": e.fallback_provider,
                    "fallback_model": e.fallback_model,
                    "reason": e.fallback_reason.value,
                }
                for e in chain.events
            ],
            "final_outcome": {
                "provider": chain.final_provider,
                "model": chain.final_model,
                "success": chain.success,
            },
        }


# Global tracker
_fallback_tracker: Optional[FallbackTracker] = None
_ft_lock = threading.Lock()


def get_fallback_tracker() -> FallbackTracker:
    global _fallback_tracker
    with _ft_lock:
        if _fallback_tracker is None:
            _fallback_tracker = FallbackTracker()
        return _fallback_tracker


__all__ = [
    "FailureReasonClass",
    "FallbackReason",
    "FallbackEvent",
    "FallbackChainContext",
    "FallbackTracker",
    "get_fallback_tracker",
]
"""
Explicit Placeholder Handling — F-018: SmartPlaceholder Can Create False Success fix.

Placeholder results are explicit about being synthetic:
- execution_state="degraded"
- provider_status="failed"
- fallback_used=True
- synthetic_output=True
Synthetic output never presented as genuine provider execution.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from enum import Enum
import threading
import logging

logger = logging.getLogger(__name__)


class PlaceholderReason(str, Enum):
    """Reason for placeholder response."""
    NO_API_KEY = "no_api_key"
    PROVIDER_FAILED = "provider_failed"
    ALL_FALLBACKS_FAILED = "all_fallbacks_failed"
    CIRCUIT_OPEN = "circuit_open"
    RATE_LIMITED = "rate_limited"
    TIMEOUT = "timeout"


@dataclass(frozen=True)
class ExplicitPlaceholderResult:
    """Explicit placeholder result - never presented as genuine."""
    execution_state: str = "degraded"  # Always "degraded", never "succeeded"
    provider_status: str = "failed"    # Always "failed", never "success"
    fallback_used: bool = True         # Always True
    synthetic_output: bool = True      # Always True - prevents misrepresentation
    reason: PlaceholderReason = PlaceholderReason.NO_API_KEY
    original_provider: Optional[str] = None
    original_model: Optional[str] = None
    fallback_provider: Optional[str] = None
    fallback_model: Optional[str] = None
    content: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "execution_state": self.execution_state,
            "provider_status": self.provider_status,
            "fallback_used": self.fallback_used,
            "synthetic_output": self.synthetic_output,
            "reason": self.reason.value,
            "original_provider": self.original_provider,
            "original_model": self.original_model,
            "fallback_provider": self.fallback_provider,
            "fallback_model": self.fallback_model,
            "content": self.content,
            "metadata": self.metadata,
        }

    @classmethod
    def from_failure(
        cls,
        reason: PlaceholderReason,
        original_provider: str = None,
        original_model: str = None,
        fallback_provider: str = None,
        fallback_model: str = None,
        content: Any = None,
        metadata: Dict[str, Any] = None,
    ) -> "ExplicitPlaceholderResult":
        """Create placeholder from provider failure."""
        return cls(
            reason=reason,
            original_provider=original_provider,
            original_model=original_model,
            fallback_provider=fallback_provider,
            fallback_model=fallback_model,
            content=content,
            metadata=metadata or {},
        )

    @classmethod
    def from_no_api_key(
        cls,
        provider: str,
        model: str,
        content: Any = None,
        metadata: Dict[str, Any] = None,
    ) -> "ExplicitPlaceholderResult":
        """Create placeholder for missing API key."""
        return cls(
            reason=PlaceholderReason.NO_API_KEY,
            original_provider=provider,
            original_model=model,
            content=content,
            metadata=metadata or {},
        )


class PlaceholderPolicy:
    """Policy for handling placeholder results."""

    def __init__(
        self,
        allow_synthetic_in_production: bool = False,
        require_explicit_flag: bool = True,
        log_all_placeholders: bool = True,
    ):
        self.allow_synthetic_in_production = allow_synthetic_in_production
        self.require_explicit_flag = require_explicit_flag
        self.log_all_placeholders = log_all_placeholders

    def validate_result(self, result: ExplicitPlaceholderResult) -> bool:
        """Validate placeholder result meets policy."""
        # Must have synthetic_output=True
        if not result.synthetic_output:
            logger.error("Placeholder missing synthetic_output flag")
            return False

        # Must have execution_state=degraded
        if result.execution_state != "degraded":
            logger.error(f"Placeholder has invalid execution_state: {result.execution_state}")
            return False

        # Must have provider_status=failed
        if result.provider_status != "failed":
            logger.error(f"Placeholder has invalid provider_status: {result.provider_status}")
            return False

        # Must have fallback_used=True
        if not result.fallback_used:
            logger.error("Placeholder missing fallback_used flag")
            return False

        return True

    def is_safe_for_production(self, result: ExplicitPlaceholderResult) -> bool:
        """Check if placeholder is safe to return to production."""
        if not self.allow_synthetic_in_production:
            return False

        # Additional safety checks for production
        if result.metadata.get("contains_sensitive_data"):
            return False

        return True


class ExplicitPlaceholderHandler:
    """Handles explicit placeholder creation and validation."""

    def __init__(self, policy: PlaceholderPolicy = None):
        self._policy = policy or PlaceholderPolicy()

    def create_placeholder(
        self,
        reason: PlaceholderReason,
        original_provider: str = None,
        original_model: str = None,
        fallback_provider: str = None,
        fallback_model: str = None,
        content: Any = None,
        metadata: Dict[str, Any] = None,
    ) -> ExplicitPlaceholderResult:
        """Create explicit placeholder."""
        result = ExplicitPlaceholderResult.from_failure(
            reason=reason,
            original_provider=original_provider,
            original_model=original_model,
            fallback_provider=fallback_provider,
            fallback_model=fallback_model,
            content=content,
            metadata=metadata,
        )

        if not self._policy.validate_result(result):
            raise ValueError("Placeholder validation failed")

        if self._policy.log_all_placeholders:
            logger.warning(
                f"Placeholder created: reason={result.reason.value}, "
                f"provider={result.original_provider}/{result.original_model}, "
                f"fallback={result.fallback_provider}/{result.fallback_model}"
            )

        return result

    def wrap_provider_failure(
        self,
        original_provider: str,
        original_model: str,
        failure_reason: str,
        fallback_provider: str = None,
        fallback_model: str = None,
    ) -> ExplicitPlaceholderResult:
        """Create placeholder from provider failure."""
        reason_map = {
            "timeout": PlaceholderReason.TIMEOUT,
            "rate_limit": PlaceholderReason.RATE_LIMITED,
            "circuit_open": PlaceholderReason.CIRCUIT_OPEN,
            "provider_failed": PlaceholderReason.PROVIDER_FAILED,
        }
        reason = None
        for key, value in reason_map.items():
            if key in failure_reason.lower():
                reason = value
                break
        reason = reason or PlaceholderReason.PROVIDER_FAILED

        return self.create_placeholder(
            reason=reason,
            original_provider=original_provider,
            original_model=original_model,
            fallback_provider=fallback_provider,
            fallback_model=fallback_model,
            metadata={"failure_reason": failure_reason},
        )


# Global handler
_placeholder_handler: Optional[ExplicitPlaceholderHandler] = None
_ph_lock = threading.Lock()


def get_placeholder_handler() -> ExplicitPlaceholderHandler:
    global _placeholder_handler
    with _ph_lock:
        if _placeholder_handler is None:
            _placeholder_handler = ExplicitPlaceholderHandler()
        return _placeholder_handler


import threading


__all__ = [
    "PlaceholderReason",
    "ExplicitPlaceholderResult",
    "PlaceholderPolicy",
    "ExplicitPlaceholderHandler",
    "get_placeholder_handler",
]
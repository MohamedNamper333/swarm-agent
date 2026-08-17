"""
Domain Error Taxonomy — structured exceptions with retry/alert policies.

Each error carries policy: retryable, max_retries, backoff, severity, client_visibility, alert_level.
"""
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from enum import Enum


class ErrorSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(str, Enum):
    VALIDATION = "validation"
    AUTHORIZATION = "authorization"
    POLICY = "policy"
    BUDGET = "budget"
    ROUTING = "routing"
    PROVIDER = "provider"
    EXECUTION = "execution"
    PERSISTENCE = "persistence"
    INTERNAL = "internal"


class RetryPolicy(str, Enum):
    NEVER = "never"
    IMMEDIATE = "immediate"
    EXPONENTIAL = "exponential"
    LINEAR = "linear"


@dataclass(frozen=True)
class ErrorPolicy:
    """Policy for how an error should be handled."""
    retryable: bool = False
    max_retries: int = 0
    backoff: RetryPolicy = RetryPolicy.NEVER
    base_delay_ms: int = 1000
    max_delay_ms: int = 30000
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
    category: ErrorCategory = ErrorCategory.INTERNAL
    client_visible: bool = True
    alert_level: str = "warning"  # "none", "info", "warning", "critical"


# Default policies per error category
DEFAULT_POLICIES: Dict[ErrorCategory, ErrorPolicy] = {
    ErrorCategory.VALIDATION: ErrorPolicy(
        retryable=False, max_retries=0, backoff=RetryPolicy.NEVER,
        severity=ErrorSeverity.LOW, category=ErrorCategory.VALIDATION,
        client_visible=True, alert_level="info"
    ),
    ErrorCategory.AUTHORIZATION: ErrorPolicy(
        retryable=False, max_retries=0, backoff=RetryPolicy.NEVER,
        severity=ErrorSeverity.HIGH, category=ErrorCategory.AUTHORIZATION,
        client_visible=True, alert_level="warning"
    ),
    ErrorCategory.POLICY: ErrorPolicy(
        retryable=False, max_retries=0, backoff=RetryPolicy.NEVER,
        severity=ErrorSeverity.HIGH, category=ErrorCategory.POLICY,
        client_visible=True, alert_level="warning"
    ),
    ErrorCategory.BUDGET: ErrorPolicy(
        retryable=True, max_retries=0, backoff=RetryPolicy.NEVER,
        severity=ErrorSeverity.HIGH, category=ErrorCategory.BUDGET,
        client_visible=True, alert_level="warning"
    ),
    ErrorCategory.ROUTING: ErrorPolicy(
        retryable=False, max_retries=0, backoff=RetryPolicy.NEVER,
        severity=ErrorSeverity.MEDIUM, category=ErrorCategory.ROUTING,
        client_visible=True, alert_level="info"
    ),
    ErrorCategory.PROVIDER: ErrorPolicy(
        retryable=True, max_retries=3, backoff=RetryPolicy.EXPONENTIAL,
        base_delay_ms=1000, max_delay_ms=30000,
        severity=ErrorSeverity.MEDIUM, category=ErrorCategory.PROVIDER,
        client_visible=True, alert_level="warning"
    ),
    ErrorCategory.EXECUTION: ErrorPolicy(
        retryable=True, max_retries=1, backoff=RetryPolicy.EXPONENTIAL,
        base_delay_ms=2000, max_delay_ms=10000,
        severity=ErrorSeverity.MEDIUM, category=ErrorCategory.EXECUTION,
        client_visible=True, alert_level="warning"
    ),
    ErrorCategory.PERSISTENCE: ErrorPolicy(
        retryable=True, max_retries=3, backoff=RetryPolicy.EXPONENTIAL,
        base_delay_ms=1000, max_delay_ms=30000,
        severity=ErrorSeverity.HIGH, category=ErrorCategory.PERSISTENCE,
        client_visible=False, alert_level="critical"
    ),
    ErrorCategory.INTERNAL: ErrorPolicy(
        retryable=False, max_retries=0, backoff=RetryPolicy.NEVER,
        severity=ErrorSeverity.CRITICAL, category=ErrorCategory.INTERNAL,
        client_visible=False, alert_level="critical"
    ),
}


class SwarmError(Exception):
    """Base exception for all swarm errors."""

    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.INTERNAL,
        policy: Optional[ErrorPolicy] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(message)
        self.message = message
        self.category = category
        self.policy = policy or DEFAULT_POLICIES.get(category, DEFAULT_POLICIES[ErrorCategory.INTERNAL])
        self.details = details or {}
        self.cause = cause

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "category": self.category.value,
            "retryable": self.policy.retryable,
            "max_retries": self.policy.max_retries,
            "backoff": self.policy.backoff.value,
            "base_delay_ms": self.policy.base_delay_ms,
            "max_delay_ms": self.policy.max_delay_ms,
            "severity": self.policy.severity.value,
            "client_visible": self.policy.client_visible,
            "alert_level": self.policy.alert_level,
            "details": self.details,
        }


class ValidationError(SwarmError):
    """Input validation failed."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None, cause: Optional[Exception] = None):
        super().__init__(message, ErrorCategory.VALIDATION, DEFAULT_POLICIES[ErrorCategory.VALIDATION], details, cause)


class AuthorizationError(SwarmError):
    """Authentication or authorization failed."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None, cause: Optional[Exception] = None):
        super().__init__(message, ErrorCategory.AUTHORIZATION, DEFAULT_POLICIES[ErrorCategory.AUTHORIZATION], details, cause)


class PolicyRejectedError(SwarmError):
    """Request rejected by policy (safety, ethics, legal, budget)."""
    def __init__(self, message: str, policy_name: str, details: Optional[Dict[str, Any]] = None, cause: Optional[Exception] = None):
        d = details or {}
        d["policy_name"] = policy_name
        super().__init__(message, ErrorCategory.POLICY, DEFAULT_POLICIES[ErrorCategory.POLICY], d, cause)


class BudgetExceededError(SwarmError):
    """Budget limit exceeded."""
    def __init__(self, message: str, budget_type: str, limit: float, used: float, details: Optional[Dict[str, Any]] = None, cause: Optional[Exception] = None):
        d = details or {}
        d["budget_type"] = budget_type
        d["limit"] = limit
        d["used"] = used
        super().__init__(message, ErrorCategory.BUDGET, DEFAULT_POLICIES[ErrorCategory.BUDGET], d, cause)


class RoutingError(SwarmError):
    """Routing failed (ambiguous, no match, etc.)."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None, cause: Optional[Exception] = None):
        super().__init__(message, ErrorCategory.ROUTING, DEFAULT_POLICIES[ErrorCategory.ROUTING], details, cause)


class ProviderUnavailableError(SwarmError):
    """Model provider unavailable."""
    def __init__(self, message: str, provider: str, model: str, details: Optional[Dict[str, Any]] = None, cause: Optional[Exception] = None):
        d = details or {}
        d["provider"] = provider
        d["model"] = model
        super().__init__(message, ErrorCategory.PROVIDER, DEFAULT_POLICIES[ErrorCategory.PROVIDER], d, cause)


class ProviderTimeoutError(SwarmError):
    """Model provider request timed out."""
    def __init__(self, message: str, provider: str, model: str, timeout_ms: int, details: Optional[Dict[str, Any]] = None, cause: Optional[Exception] = None):
        d = details or {}
        d["provider"] = provider
        d["model"] = model
        d["timeout_ms"] = timeout_ms
        super().__init__(message, ErrorCategory.PROVIDER, DEFAULT_POLICIES[ErrorCategory.PROVIDER], d, cause)


class ProviderRateLimitedError(SwarmError):
    """Model provider rate limited."""
    def __init__(self, message: str, provider: str, model: str, retry_after_ms: Optional[int] = None, details: Optional[Dict[str, Any]] = None, cause: Optional[Exception] = None):
        d = details or {}
        d["provider"] = provider
        d["model"] = model
        d["retry_after_ms"] = retry_after_ms
        super().__init__(message, ErrorCategory.PROVIDER, DEFAULT_POLICIES[ErrorCategory.PROVIDER], d, cause)


class AgentExecutionError(SwarmError):
    """Agent execution failed."""
    def __init__(self, message: str, agent_role: str, details: Optional[Dict[str, Any]] = None, cause: Optional[Exception] = None):
        d = details or {}
        d["agent_role"] = agent_role
        super().__init__(message, ErrorCategory.EXECUTION, DEFAULT_POLICIES[ErrorCategory.EXECUTION], d, cause)


class PersistenceError(SwarmError):
    """Persistence operation failed."""
    def __init__(self, message: str, operation: str, details: Optional[Dict[str, Any]] = None, cause: Optional[Exception] = None):
        d = details or {}
        d["operation"] = operation
        super().__init__(message, ErrorCategory.PERSISTENCE, DEFAULT_POLICIES[ErrorCategory.PERSISTENCE], d, cause)


class InternalError(SwarmError):
    """Unexpected internal error."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None, cause: Optional[Exception] = None):
        super().__init__(message, ErrorCategory.INTERNAL, DEFAULT_POLICIES[ErrorCategory.INTERNAL], details, cause)


def get_policy_for_category(category: ErrorCategory) -> ErrorPolicy:
    """Get default policy for error category."""
    return DEFAULT_POLICIES.get(category, DEFAULT_POLICIES[ErrorCategory.INTERNAL])


def is_retryable(error: Exception) -> bool:
    """Check if an error is retryable."""
    if isinstance(error, SwarmError):
        return error.policy.retryable
    return False


def get_retry_policy(error: Exception) -> Optional[ErrorPolicy]:
    """Get retry policy for an error."""
    if isinstance(error, SwarmError):
        return error.policy
    return None


# Export all error types
__all__ = [
    "ErrorSeverity",
    "ErrorCategory",
    "RetryPolicy",
    "ErrorPolicy",
    "DEFAULT_POLICIES",
    "SwarmError",
    "ValidationError",
    "AuthorizationError",
    "PolicyRejectedError",
    "BudgetExceededError",
    "RoutingError",
    "ProviderUnavailableError",
    "ProviderTimeoutError",
    "ProviderRateLimitedError",
    "AgentExecutionError",
    "PersistenceError",
    "InternalError",
    "get_policy_for_category",
    "is_retryable",
    "get_retry_policy",
]
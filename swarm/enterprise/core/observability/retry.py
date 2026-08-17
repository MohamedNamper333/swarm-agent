"""
Retry Storm Protection — F-031: Retry Storm Risk fix.

Global retry budgets: request, agent, provider.
Exponential backoff + jitter + max attempts + deadline propagation.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Callable
from enum import Enum
from datetime import datetime, timezone
import threading
import time
import random
import logging

logger = logging.getLogger(__name__)


class RetryPolicy(str, Enum):
    NEVER = "never"
    FIXED = "fixed"
    EXPONENTIAL = "exponential"
    LINEAR = "linear"


class BudgetScope(str, Enum):
    REQUEST = "request"          # Per-request retry budget
    AGENT = "agent"              # Per-agent retry budget
    PROVIDER = "provider"        # Per-provider retry budget
    GLOBAL = "global"            # Global system retry budget


@dataclass(frozen=True)
class RetryBudget:
    """Retry budget configuration."""
    scope: BudgetScope
    max_attempts: int
    base_delay_ms: int
    max_delay_ms: int
    jitter_factor: float = 0.1  # 10% jitter
    deadline_ms: Optional[int] = None  # Absolute deadline from start


@dataclass
class RetryState:
    """Current state of a retry budget."""
    scope: BudgetScope
    scope_key: str  # e.g., "request:req-123", "agent:code", "provider:nvidia/nemotron"
    attempts: int = 0
    last_attempt_at: Optional[datetime] = None
    total_delay_ms: int = 0
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def can_retry(self, budget: RetryBudget) -> bool:
        """Check if retry is allowed within budget."""
        if self.attempts >= budget.max_attempts:
            return False
        if budget.deadline_ms:
            elapsed = (datetime.now(timezone.utc) - self.start_time).total_seconds() * 1000
            if elapsed >= budget.deadline_ms:
                return False
        return True

    def next_delay_ms(self, budget: RetryPolicy, base_delay: int, max_delay: int, jitter: float) -> int:
        """Calculate next retry delay with jitter."""
        if budget == RetryPolicy.FIXED:
            delay = base_delay
        elif budget == RetryPolicy.LINEAR:
            delay = base_delay * (self.attempts + 1)
        elif budget == RetryPolicy.EXPONENTIAL:
            delay = base_delay * (2 ** self.attempts)
        else:
            delay = base_delay

        delay = min(delay, max_delay)

        # Add jitter
        jitter_amount = delay * jitter
        delay = delay + random.uniform(-jitter_amount, jitter_amount)

        return max(0, int(delay))


class RetryBudgetManager:
    """
    Manages retry budgets at multiple scopes to prevent retry storms.
    
    Budgets enforced:
    - Request-level: max retries per request
    - Agent-level: max retries per agent across all requests
    - Provider-level: max retries per provider across all agents
    - Global: system-wide retry rate limiting
    """

    def __init__(self):
        self._budgets: Dict[BudgetScope, Dict[str, RetryBudget]] = {
            BudgetScope.REQUEST: {},
            BudgetScope.AGENT: {},
            BudgetScope.PROVIDER: {},
            BudgetScope.GLOBAL: {"global": RetryBudget(
                scope=BudgetScope.GLOBAL,
                max_attempts=1000,
                base_delay_ms=1000,
                max_delay_ms=60000,
            )},
        }
        self._states: Dict[str, RetryState] = {}
        self._lock = threading.RLock()

    def register_budget(
        self,
        scope: BudgetScope,
        key: str,
        max_attempts: int,
        base_delay_ms: int = 1000,
        max_delay_ms: int = 30000,
        jitter_factor: float = 0.1,
        deadline_ms: Optional[int] = None,
    ) -> None:
        """Register a retry budget."""
        with self._lock:
            self._budgets[scope][key] = RetryBudget(
                scope=scope,
                max_attempts=max_attempts,
                base_delay_ms=base_delay_ms,
                max_delay_ms=max_delay_ms,
                jitter_factor=jitter_factor,
                deadline_ms=deadline_ms,
            )

    def get_budget(self, scope: BudgetScope, key: str) -> Optional[RetryBudget]:
        """Get budget for scope and key."""
        with self._lock:
            return self._budgets.get(scope, {}).get(key)

    def can_retry(self, scope: BudgetScope, key: str) -> bool:
        """Check if retry is allowed."""
        state_key = f"{scope.value}:{key}"
        with self._lock:
            budget = self._budgets.get(scope, {}).get(key)
            if not budget:
                return True  # No budget = unlimited

            state = self._states.get(state_key)
            if not state:
                state = RetryState(scope=scope, scope_key=key)
                self._states[state_key] = state

            return state.can_retry(budget)

    def record_attempt(self, scope: BudgetScope, key: str) -> Optional[int]:
        """Record a retry attempt. Returns next delay in ms, or None if not allowed."""
        state_key = f"{scope.value}:{key}"
        with self._lock:
            budget = self._budgets.get(scope, {}).get(key)
            if not budget:
                return None  # No budget = no delay

            state = self._states.get(state_key)
            if not state:
                state = RetryState(scope=scope, scope_key=key)
                self._states[state_key] = state

            if not state.can_retry(budget):
                return None

            state.attempts += 1
            state.last_attempt_at = datetime.now(timezone.utc)
            delay = state.next_delay_ms(
                RetryPolicy.EXPONENTIAL,
                budget.base_delay_ms,
                budget.max_delay_ms,
                budget.jitter_factor,
            )
            state.total_delay_ms += delay
            return delay

    def reset_budget(self, scope: BudgetScope, key: str) -> None:
        """Reset a retry budget."""
        state_key = f"{scope.value}:{key}"
        with self._lock:
            self._states.pop(state_key, None)

    def get_state(self, scope: BudgetScope, key: str) -> Optional[RetryState]:
        """Get current retry state."""
        state_key = f"{scope.value}:{key}"
        with self._lock:
            return self._states.get(state_key)

    def get_all_states(self) -> Dict[str, RetryState]:
        with self._lock:
            return dict(self._states)


class RetryStormDetector:
    """Detects potential retry storm conditions."""

    def __init__(self, manager: RetryBudgetManager):
        self._manager = manager
        self._thresholds = {
            "provider_retry_rate_per_minute": 100,  # Max retries/min per provider
            "agent_retry_rate_per_minute": 50,      # Max retries/min per agent
            "global_retry_rate_per_minute": 500,    # Max retries/min global
        }
        self._recent_attempts: Dict[str, List[datetime]] = defaultdict(list)
        self._lock = threading.Lock()

    def record_attempt(self, scope: BudgetScope, key: str) -> None:
        """Record an attempt for storm detection."""
        now = datetime.now(timezone.utc)
        metric_key = f"{scope.value}:{key}"
        with self._lock:
            self._recent_attempts[metric_key].append(now)
            # Clean old entries
            cutoff = now.timestamp() - 60  # 1 minute window
            self._recent_attempts[metric_key] = [
                t for t in self._recent_attempts[metric_key]
                if t.timestamp() > cutoff
            ]

    def check_storm_risk(self, scope: BudgetScope, key: str) -> bool:
        """Check if retry storm risk exists."""
        metric_key = f"{scope.value}:{key}"
        with self._lock:
            attempts = self._recent_attempts.get(metric_key, [])
            threshold = self._thresholds.get(f"{scope.value}_retry_rate_per_minute", 100)
            return len(attempts) >= threshold

    def get_retry_rate(self, scope: BudgetScope, key: str) -> int:
        """Get current retry rate per minute."""
        metric_key = f"{scope.value}:{key}"
        with self._lock:
            attempts = self._recent_attempts.get(metric_key, [])
            return len(attempts)


from collections import defaultdict


class RetryExecutor:
    """
    Executes operations with retry budgets and storm protection.
    """

    def __init__(
        self,
        budget_manager: RetryBudgetManager = None,
        storm_detector: RetryStormDetector = None,
    ):
        self._budget_manager = budget_manager or RetryBudgetManager()
        self._storm_detector = storm_detector or RetryStormDetector(self._budget_manager)

    def execute_with_retry(
        self,
        operation: Callable[[], Any],
        request_id: str,
        agent_id: str,
        provider: str,
        max_request_attempts: int = 3,
        max_agent_attempts: int = 10,
        max_provider_attempts: int = 50,
        base_delay_ms: int = 1000,
        max_delay_ms: int = 30000,
        deadline_ms: Optional[int] = None,
    ) -> Any:
        """
        Execute operation with multi-scope retry budgets.
        
        Budgets checked in order: request → agent → provider → global
        """
        # Register budgets if not exists
        self._budget_manager.register_budget(
            BudgetScope.REQUEST, request_id,
            max_attempts=max_request_attempts,
            base_delay_ms=base_delay_ms,
            max_delay_ms=max_delay_ms,
            deadline_ms=deadline_ms,
        )
        self._budget_manager.register_budget(
            BudgetScope.AGENT, agent_id,
            max_attempts=max_agent_attempts,
            base_delay_ms=base_delay_ms,
            max_delay_ms=max_delay_ms,
        )
        self._budget_manager.register_budget(
            BudgetScope.PROVIDER, provider,
            max_attempts=max_provider_attempts,
            base_delay_ms=base_delay_ms,
            max_delay_ms=max_delay_ms,
        )

        last_error = None

        while True:
            # Check all budgets
            for scope, key in [
                (BudgetScope.REQUEST, request_id),
                (BudgetScope.AGENT, agent_id),
                (BudgetScope.PROVIDER, provider),
                (BudgetScope.GLOBAL, "global"),
            ]:
                if not self._budget_manager.can_retry(scope, key):
                    raise RetryBudgetExhausted(
                        f"Retry budget exhausted for {scope.value}:{key}"
                    )

                # Check storm risk
                if self._storm_detector.check_storm_risk(scope, key):
                    logger.warning(f"Retry storm risk detected for {scope.value}:{key}")
                    raise RetryStormRisk(
                        f"Retry storm risk for {scope.value}:{key}"
                    )

            try:
                result = operation()
                return result

            except Exception as e:
                last_error = e

                # Record attempts
                for scope, key in [
                    (BudgetScope.REQUEST, request_id),
                    (BudgetScope.AGENT, agent_id),
                    (BudgetScope.PROVIDER, provider),
                    (BudgetScope.GLOBAL, "global"),
                ]:
                    delay = self._budget_manager.record_attempt(scope, key)
                    self._storm_detector.record_attempt(scope, key)

                    if delay is not None:
                        logger.info(f"Retry {scope.value}:{key} in {delay}ms")
                        time.sleep(delay / 1000)
                    else:
                        # Budget exhausted
                        raise RetryBudgetExhausted(
                            f"Retry budget exhausted for {scope.value}:{key}"
                        ) from e

                # If we get here, all budgets allowed retry but operation failed
                # Loop will continue and check budgets again


class RetryBudgetExhausted(Exception):
    """Raised when retry budget is exhausted."""
    pass


class RetryStormRisk(Exception):
    """Raised when retry storm risk is detected."""
    pass


# Global instances
_retry_budget_manager: Optional[RetryBudgetManager] = None
_rbm_lock = threading.Lock()


def get_retry_budget_manager() -> RetryBudgetManager:
    global _retry_budget_manager
    with _rbm_lock:
        if _retry_budget_manager is None:
            _retry_budget_manager = RetryBudgetManager()
        return _retry_budget_manager


__all__ = [
    "RetryPolicy",
    "BudgetScope",
    "RetryBudget",
    "RetryState",
    "RetryBudgetManager",
    "RetryStormDetector",
    "RetryExecutor",
    "RetryBudgetExhausted",
    "RetryStormRisk",
    "get_retry_budget_manager",
]
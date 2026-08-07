"""Retry engine with exponential backoff and jitter.

Wraps any callable with smart retry logic for transient failures:
- Exponential backoff with configurable base and max
- Decorrelated jitter (Marc Brooker-style) to spread retries
- Selective retry based on exception type
- Total deadline / max attempts
- Per-attempt callbacks for observability

Honors the constitutional principle of EVIDENCE_OVER_AUTHORITY: only
retries when there is real evidence of a transient failure (the raised
exception type), not based on a guess.
"""

from __future__ import annotations

import functools
import random
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Iterable, Optional, Tuple, Type


class RetryStrategy(Enum):
    """How to compute the delay between retries."""
    FIXED = "fixed"               # constant delay
    LINEAR = "linear"             # delay * attempt
    EXPONENTIAL = "exponential"   # delay * (2 ** (attempt - 1))
    EXPONENTIAL_JITTER = "exp_jitter"   # exponential + uniform jitter
    DECORRELATED_JITTER = "decorrelated_jitter"  # Brooker-style


class RetryExhausted(Exception):
    """Raised when all retry attempts have been exhausted."""

    def __init__(self, attempts: int, last_exception: BaseException):
        super().__init__(
            f"Retry exhausted after {attempts} attempts; last error: {last_exception!r}"
        )
        self.attempts = attempts
        self.last_exception = last_exception


@dataclass
class RetryPolicy:
    """Configuration for retry behavior."""

    max_attempts: int = 3
    initial_delay_seconds: float = 1.0
    max_delay_seconds: float = 30.0
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_JITTER
    jitter_factor: float = 0.5           # 0..1; 0.5 means delay * [0.5, 1.5]
    total_timeout_seconds: Optional[float] = None
    retriable_exceptions: Tuple[Type[BaseException], ...] = (Exception,)
    non_retriable_exceptions: Tuple[Type[BaseException], ...] = ()
    on_retry: Optional[Callable[[int, float, BaseException], None]] = None

    def __post_init__(self):
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if self.initial_delay_seconds < 0:
            raise ValueError("initial_delay_seconds must be >= 0")
        if self.max_delay_seconds < self.initial_delay_seconds:
            raise ValueError("max_delay_seconds must be >= initial_delay_seconds")
        if not 0.0 <= self.jitter_factor <= 1.0:
            raise ValueError("jitter_factor must be in [0, 1]")


def compute_backoff(
    attempt: int,
    policy: RetryPolicy,
    rng: random.Random,
    previous_delay: Optional[float] = None,
) -> float:
    """Pure function — given an attempt (1-based) and policy, return the delay."""
    delay = policy.initial_delay_seconds
    if policy.strategy == RetryStrategy.FIXED:
        delay = policy.initial_delay_seconds
    elif policy.strategy == RetryStrategy.LINEAR:
        delay = policy.initial_delay_seconds * attempt
    elif policy.strategy == RetryStrategy.EXPONENTIAL:
        delay = policy.initial_delay_seconds * (2 ** (attempt - 1))
    elif policy.strategy == RetryStrategy.EXPONENTIAL_JITTER:
        base = policy.initial_delay_seconds * (2 ** (attempt - 1))
        # random factor in [1 - jitter_factor, 1 + jitter_factor]
        f = 1.0 + policy.jitter_factor * (2 * rng.random() - 1)
        delay = base * f
    elif policy.strategy == RetryStrategy.DECORRELATED_JITTER:
        # Marc Brooker decorrelated jitter: capped at base * 3
        if previous_delay is None:
            previous_delay = policy.initial_delay_seconds
        delay = min(
            policy.max_delay_seconds,
            rng.uniform(policy.initial_delay_seconds, previous_delay * 3),
        )
    else:
        raise ValueError(f"Unknown strategy: {policy.strategy}")

    return max(0.0, min(delay, policy.max_delay_seconds))


@dataclass
class AttemptRecord:
    """Record of one retry attempt (for observability)."""
    attempt: int
    delay_seconds: float
    exception: Optional[BaseException]
    duration_seconds: float
    timestamp: float = field(default_factory=time.time)


@dataclass
class BackoffSchedule:
    """Materialized schedule of delays for a retry policy.

    Useful for:
    - Unit testing backoff behavior deterministically
    - Inspecting the full plan before execution
    - Pre-computing a schedule for a fixed number of attempts

    Attributes:
        strategy: The strategy used to compute the delays
        delays: Delay in seconds for each attempt (index 0 = first retry)
        total_delay: Sum of all delays
    """
    strategy: RetryStrategy
    delays: list = field(default_factory=list)
    total_delay: float = 0.0

    def get_delay(self, attempt_index: int) -> float:
        """Get delay for a specific retry attempt (0-based)."""
        if attempt_index < 0 or attempt_index >= len(self.delays):
            raise IndexError(f"attempt_index {attempt_index} out of range [0, {len(self.delays)})")
        return self.delays[attempt_index]

    def __len__(self) -> int:
        return len(self.delays)

    @classmethod
    def compute(
        cls,
        policy: "RetryPolicy",
        rng: Optional[random.Random] = None,
        attempts: Optional[int] = None,
    ) -> "BackoffSchedule":
        """Compute a full backoff schedule for the given policy."""
        rng = rng or random.Random()
        n = attempts if attempts is not None else max(0, policy.max_attempts - 1)
        delays: list = []
        previous_delay: Optional[float] = None
        for attempt in range(1, n + 1):
            delay = compute_backoff(attempt, policy, rng, previous_delay)
            delays.append(delay)
            previous_delay = delay
        return cls(
            strategy=policy.strategy,
            delays=delays,
            total_delay=sum(delays),
        )


class RetryEngine:
    """Executes callables under a RetryPolicy with full observability."""

    def __init__(self, policy: RetryPolicy, rng: Optional[random.Random] = None,
                 clock=time.monotonic, sleeper: Callable[[float], None] = time.sleep):
        self.policy = policy
        self._rng = rng or random.Random()
        self._clock = clock
        self._sleep = sleeper
        self._history: list[AttemptRecord] = []
        self._lock = threading.Lock()

    def _is_retriable(self, exc: BaseException) -> bool:
        for non_retriable in self.policy.non_retriable_exceptions:
            if isinstance(exc, non_retriable):
                return False
        for retriable in self.policy.retriable_exceptions:
            if isinstance(exc, retriable):
                return True
        return False

    def execute(self, fn: Callable[..., Any], *args, **kwargs) -> Any:
        """Execute fn(*args, **kwargs) under retry semantics."""
        deadline = (
            self._clock() + self.policy.total_timeout_seconds
            if self.policy.total_timeout_seconds is not None
            else None
        )
        previous_delay: Optional[float] = None
        last_exc: Optional[BaseException] = None
        attempt = 0
        self._history.clear()

        while attempt < self.policy.max_attempts:
            attempt += 1
            attempt_started = self._clock()
            try:
                result = fn(*args, **kwargs)
                with self._lock:
                    self._history.append(AttemptRecord(
                        attempt=attempt, delay_seconds=0.0,
                        exception=None,
                        duration_seconds=self._clock() - attempt_started,
                    ))
                return result
            except BaseException as exc:
                duration = self._clock() - attempt_started
                last_exc = exc
                with self._lock:
                    self._history.append(AttemptRecord(
                        attempt=attempt, delay_seconds=0.0,
                        exception=exc, duration_seconds=duration,
                    ))
                if not self._is_retriable(exc):
                    raise
                if attempt >= self.policy.max_attempts:
                    break
                # Compute backoff
                delay = compute_backoff(attempt, self.policy, self._rng, previous_delay)
                previous_delay = delay
                if deadline is not None:
                    remaining = deadline - self._clock()
                    if remaining <= 0:
                        break
                    delay = min(delay, remaining)
                if self.policy.on_retry is not None:
                    try:
                        self.policy.on_retry(attempt, delay, exc)
                    except Exception:
                        # Callback errors must never break retries
                        pass
                if delay > 0:
                    self._sleep(delay)

        raise RetryExhausted(attempt, last_exc)  # type: ignore[misc]

    def execute_with_callbacks(
        self,
        fn: Callable[..., Any],
        on_success: Optional[Callable[[Any], None]] = None,
        on_failure: Optional[Callable[[BaseException], None]] = None,
        *args, **kwargs,
    ) -> Any:
        try:
            result = self.execute(fn, *args, **kwargs)
            if on_success is not None:
                on_success(result)
            return result
        except RetryExhausted as exc:
            if on_failure is not None:
                on_failure(exc.last_exception)
            raise

    def get_history(self) -> list:
        """Return a copy of the attempt history."""
        with self._lock:
            return list(self._history)

    def get_stats(self) -> dict:
        """Return aggregate stats over the history."""
        with self._lock:
            history = list(self._history)
        if not history:
            return {"attempts": 0, "successes": 0, "failures": 0, "total_delay": 0.0}
        successes = sum(1 for r in history if r.exception is None)
        failures = sum(1 for r in history if r.exception is not None)
        return {
            "attempts": len(history),
            "successes": successes,
            "failures": failures,
            "total_delay": sum(r.delay_seconds for r in history),
            "total_duration": sum(r.duration_seconds for r in history),
        }

    def reset_history(self) -> None:
        with self._lock:
            self._history.clear()


def retry(
    policy: Optional[RetryPolicy] = None,
    *,
    max_attempts: int = 3,
    initial_delay_seconds: float = 1.0,
    max_delay_seconds: float = 30.0,
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_JITTER,
    retriable_exceptions: Tuple[Type[BaseException], ...] = (Exception,),
    on_retry: Optional[Callable[[int, float, BaseException], None]] = None,
) -> Callable:
    """Decorator that wraps a function with retry semantics."""
    if policy is None:
        policy = RetryPolicy(
            max_attempts=max_attempts,
            initial_delay_seconds=initial_delay_seconds,
            max_delay_seconds=max_delay_seconds,
            strategy=strategy,
            retriable_exceptions=retriable_exceptions,
            on_retry=on_retry,
        )
    engine = RetryEngine(policy)

    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            return engine.execute(fn, *args, **kwargs)
        wrapper.retry_engine = engine  # type: ignore[attr-defined]
        return wrapper

    return decorator

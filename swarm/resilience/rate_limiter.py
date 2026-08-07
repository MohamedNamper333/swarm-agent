"""Token bucket rate limiter for per-model request throttling.

Implements the classic token bucket algorithm:
- Each model/provider has a bucket with a fixed capacity
- Tokens refill at a configured rate
- Each request consumes one token
- If no tokens are available, the request blocks (with optional timeout)
  or raises RateLimitExceeded

This prevents 429 errors from upstream LLM providers and lets us model
real-world capacity constraints per model (e.g., free tier limits).
"""

from __future__ import annotations

import asyncio
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional


class RateLimitExceeded(Exception):
    """Raised when no tokens are available and block=False."""

    def __init__(self, scope: str, retry_after_seconds: float):
        super().__init__(f"Rate limit exceeded for {scope}; retry after {retry_after_seconds:.3f}s")
        self.scope = scope
        self.retry_after_seconds = retry_after_seconds


@dataclass(frozen=True)
class RateLimitConfig:
    """Per-scope token bucket configuration.

    capacity:  Maximum tokens that can accumulate (burst size).
    refill_rate:  Tokens added per second (sustained throughput).
    """

    capacity: float
    refill_rate: float

    def __post_init__(self):
        if self.capacity <= 0:
            raise ValueError("capacity must be > 0")
        if self.refill_rate <= 0:
            raise ValueError("refill_rate must be > 0")


class TokenBucket:
    """Thread-safe token bucket.

    Tokens regenerate continuously. acquire() returns the wait time when
    no tokens are available (0.0 if tokens are immediately available).
    """

    def __init__(self, scope: str, config: RateLimitConfig, clock=time.monotonic):
        self.scope = scope
        self.config = config
        self._clock = clock
        self._tokens = float(config.capacity)
        self._last_refill = clock()
        self._lock = threading.Lock()
        # Stats
        self.total_acquired = 0
        self.total_wait_seconds = 0.0
        self.total_rejections = 0

    def _refill(self) -> None:
        now = self._clock()
        elapsed = now - self._last_refill
        if elapsed <= 0:
            return
        self._tokens = min(
            self.config.capacity,
            self._tokens + elapsed * self.config.refill_rate,
        )
        self._last_refill = now

    def try_acquire(self, tokens: float = 1.0) -> bool:
        """Try to acquire tokens without blocking. Returns True if successful."""
        if tokens > self.config.capacity:
            raise ValueError(
                f"requested {tokens} tokens exceeds bucket capacity {self.config.capacity}"
            )
        with self._lock:
            self._refill()
            if self._tokens >= tokens:
                self._tokens -= tokens
                self.total_acquired += 1
                return True
            self.total_rejections += 1
            return False

    def time_to_available(self, tokens: float = 1.0) -> float:
        """How many seconds until `tokens` are available (0.0 if already)."""
        with self._lock:
            self._refill()
            if self._tokens >= tokens:
                return 0.0
            deficit = tokens - self._tokens
            return deficit / self.config.refill_rate

    def acquire(self, tokens: float = 1.0, timeout: Optional[float] = None,
                block: bool = True) -> None:
        """Acquire tokens, blocking up to `timeout` seconds if needed."""
        wait = self.time_to_available(tokens)
        if wait == 0.0:
            with self._lock:
                self._tokens -= tokens
                self.total_acquired += 1
                return
        if not block:
            self.total_rejections += 1
            raise RateLimitExceeded(self.scope, wait)
        if timeout is not None and wait > timeout:
            self.total_rejections += 1
            raise RateLimitExceeded(self.scope, wait)
        time.sleep(wait)
        with self._lock:
            self._refill()
            self._tokens -= tokens
            self.total_acquired += 1
            self.total_wait_seconds += wait

    def snapshot(self) -> Dict[str, float]:
        with self._lock:
            self._refill()
            return {
                "scope": self.scope,
                "tokens_available": self._tokens,
                "capacity": self.config.capacity,
                "refill_rate": self.config.refill_rate,
                "total_acquired": self.total_acquired,
                "total_rejections": self.total_rejections,
            }


class RateLimiter:
    """Manages token buckets per scope (model id, agent id, provider, etc.).

    Default configurations are applied per scope via configure().
    """

    def __init__(self, default_config: Optional[RateLimitConfig] = None,
                 clock=time.monotonic):
        self._buckets: Dict[str, TokenBucket] = {}
        self._configs: Dict[str, RateLimitConfig] = {}
        self._default_config = default_config or RateLimitConfig(
            capacity=60.0, refill_rate=1.0,  # 1 req/sec sustained, 60 burst
        )
        self._clock = clock
        self._lock = threading.Lock()

    def configure(self, scope: str, config: RateLimitConfig) -> None:
        """Set/override a scope's bucket config. Resets the bucket if it existed."""
        with self._lock:
            self._configs[scope] = config
            self._buckets[scope] = TokenBucket(scope, config, self._clock)

    def _bucket_for(self, scope: str) -> TokenBucket:
        with self._lock:
            if scope not in self._buckets:
                cfg = self._configs.get(scope, self._default_config)
                self._buckets[scope] = TokenBucket(scope, cfg, self._clock)
            return self._buckets[scope]

    def try_acquire(self, scope: str, tokens: float = 1.0) -> bool:
        return self._bucket_for(scope).try_acquire(tokens)

    def acquire(self, scope: str, tokens: float = 1.0, timeout: Optional[float] = None,
                block: bool = True) -> None:
        self._bucket_for(scope).acquire(tokens, timeout=timeout, block=block)

    def time_to_available(self, scope: str, tokens: float = 1.0) -> float:
        return self._bucket_for(scope).time_to_available(tokens)

    async def aacquire(self, scope: str, tokens: float = 1.0,
                       timeout: Optional[float] = None) -> None:
        """Async version of acquire — sleeps via asyncio.sleep."""
        wait = self.time_to_available(scope, tokens)
        if wait == 0.0:
            self._bucket_for(scope).try_acquire(tokens)
            return
        if timeout is not None and wait > timeout:
            raise RateLimitExceeded(scope, wait)
        await asyncio.sleep(wait)
        self._bucket_for(scope).try_acquire(tokens)

    def snapshot_all(self) -> Dict[str, Dict[str, float]]:
        with self._lock:
            return {scope: b.snapshot() for scope, b in self._buckets.items()}

    def reset(self, scope: Optional[str] = None) -> None:
        with self._lock:
            if scope is None:
                self._buckets.clear()
            else:
                self._buckets.pop(scope, None)

    def get_stats(self, scope: str) -> Dict[str, float]:
        return self._bucket_for(scope).snapshot()

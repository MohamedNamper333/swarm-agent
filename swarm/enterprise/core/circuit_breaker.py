"""
Circuit Breaker — per-model circuit protection.

Triggers when a model hits 80% of daily limit (per RateLimiterV2).
When OPEN: requests are queued (or rejected with 503 if queue full).
Resets automatically at 00:00 UTC (when daily counters reset).

States:
  CLOSED  — normal, requests pass through
  OPEN    — model near/at limit, requests queued or rejected
  HALF_OPEN — daily reset happened, probing with limited traffic
"""
import threading
import time
import logging
from collections import defaultdict, deque
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Deque, Optional, Any

from swarm.resilience.rate_limiter_v2 import RateLimiterV2, get_rate_limiter

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Per-model circuit breaker with queue."""

    TRIGGER_THRESHOLD = 0.80  # 80% → open
    QUEUE_MAX = 100           # max queued requests per model
    QUEUE_TTL_SEC = 3600      # queued requests expire after 1h
    HALF_OPEN_PROBES = 3      # probes allowed in HALF_OPEN state

    def __init__(self, rate_limiter: Optional[RateLimiterV2] = None):
        self._rl = rate_limiter or get_rate_limiter()
        self._state: Dict[str, CircuitState] = defaultdict(lambda: CircuitState.CLOSED)
        self._queues: Dict[str, Deque] = defaultdict(deque)
        self._lock = threading.RLock()
        self._half_open_probes_used: Dict[str, int] = defaultdict(int)

    def state_of(self, model_id: str) -> CircuitState:
        with self._lock:
            return self._state[model_id]

    def is_open(self, model_id: str) -> bool:
        return self.state_of(model_id) == CircuitState.OPEN

    def check_and_update(self, model_id: str) -> CircuitState:
        """Re-evaluate circuit state based on rate limiter data."""
        with self._lock:
            used = self._rl.get_used(model_id)
            limit = self._rl.get_limit(model_id)
            pct = used / limit if limit > 0 else 0
            current = self._state[model_id]

            if pct >= self.TRIGGER_THRESHOLD:
                if current == CircuitState.CLOSED:
                    logger.warning("Circuit OPEN for %s (%.1f%%)", model_id, pct * 100)
                    self._state[model_id] = CircuitState.OPEN
                elif current == CircuitState.HALF_OPEN:
                    # Re-tripped on probe
                    self._state[model_id] = CircuitState.OPEN
            else:
                # Below threshold — close the circuit
                if current != CircuitState.CLOSED:
                    logger.info("Circuit CLOSED for %s (now %.1f%%)", model_id, pct * 100)
                    self._state[model_id] = CircuitState.CLOSED
                    self._half_open_probes_used[model_id] = 0
            return self._state[model_id]

    def allow_request(self, model_id: str) -> bool:
        """Decide whether to allow a request. Returns True if should proceed."""
        state = self.check_and_update(model_id)
        if state == CircuitState.CLOSED:
            return True
        if state == CircuitState.HALF_OPEN:
            with self._lock:
                if self._half_open_probes_used[model_id] < self.HALF_OPEN_PROBES:
                    self._half_open_probes_used[model_id] += 1
                    return True
                return False
        # OPEN: request must go to queue or be rejected
        return False

    def enqueue(self, model_id: str, request_data: Any) -> bool:
        """Queue a request when circuit is OPEN. Returns False if queue full."""
        with self._lock:
            q = self._queues[model_id]
            if len(q) >= self.QUEUE_MAX:
                logger.warning("Queue full for %s (rejected)", model_id)
                return False
            q.append((time.time(), request_data))
            return True

    def dequeue(self, model_id: str) -> Optional[Any]:
        """Pop the oldest queued request (and expire stale ones)."""
        with self._lock:
            q = self._queues[model_id]
            now = time.time()
            while q and (now - q[0][0]) > self.QUEUE_TTL_SEC:
                q.popleft()
            if not q:
                return None
            return q.popleft()[1]

    def queue_size(self, model_id: str) -> int:
        with self._lock:
            return len(self._queues[model_id])

    def reset_daily(self) -> None:
        """Call after daily reset to clear all circuits."""
        with self._lock:
            for m in self._state:
                self._state[m] = CircuitState.CLOSED
                self._half_open_probes_used[m] = 0
            self._queues.clear()
            logger.info("All circuits reset (daily)")

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "open_circuits": [m for m, s in self._state.items() if s == CircuitState.OPEN],
                "half_open": [m for m, s in self._state.items() if s == CircuitState.HALF_OPEN],
                "queued_requests": {m: len(q) for m, q in self._queues.items() if q},
                "trigger_threshold_pct": self.TRIGGER_THRESHOLD * 100,
            }


_default: Optional[CircuitBreaker] = None
_lock = threading.Lock()


def get_circuit_breaker() -> CircuitBreaker:
    global _default
    with _lock:
        if _default is None:
            _default = CircuitBreaker()
        return _default


if __name__ == "__main__":
    cb = CircuitBreaker()
    rl = cb._rl

    print(f"Initial state (nemotron-ultra): {cb.state_of('nvidia/nemotron-3-ultra-550b-a55b')}")
    # Simulate heavy usage: 161/200 = 80.5% → should open
    for _ in range(161):
        rl.acquire("nvidia/nemotron-3-ultra-550b-a55b")
        rl.record_success("nvidia/nemotron-3-ultra-550b-a55b")
    cb.check_and_update("nvidia/nemotron-3-ultra-550b-a55b")
    print(f"After 161 reqs: state={cb.state_of('nvidia/nemotron-3-ultra-550b-a55b')}")
    print(f"allow_request: {cb.allow_request('nvidia/nemotron-3-ultra-550b-a55b')}")
    # Queue test
    cb.enqueue("nvidia/nemotron-3-ultra-550b-a55b", {"q": "test1"})
    print(f"Queue size: {cb.queue_size('nvidia/nemotron-3-ultra-550b-a55b')}")
    print(f"Stats: {cb.stats()}")

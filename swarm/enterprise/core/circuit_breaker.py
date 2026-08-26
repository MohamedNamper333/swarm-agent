"""
Circuit Breaker — per-model circuit protection.

2026-08-25 rewrite fixing three defects found by institutional audit:
- N1: HALF_OPEN was never ASSIGNED anywhere (dead state / dead branch).
- N2: "auto reset at 00:00 UTC" was false — reset_daily() had no callers,
      so an opened circuit stayed open until manual restart.
- N3: opening at 80% wasted the remaining 20% of quota with no recovery.

Semantics now:
  OPEN triggers at 100% of daily limit (80% remains a logged warning).
  On UTC day rollover, fresh quota means circuits return directly to
  CLOSED (probing an empty budget is meaningless). HALF_OPEN remains the
  mid-day recovery state between OPEN and below-threshold health.
  Queued requests survive until recovered via drain(); stale entries
  expire after QUEUE_TTL_SEC.
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
        self._last_seen_date: str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def state_of(self, model_id: str) -> CircuitState:
        with self._lock:
            return self._state[model_id]

    def is_open(self, model_id: str) -> bool:
        return self.state_of(model_id) == CircuitState.OPEN

    def check_and_update(self, model_id: str) -> CircuitState:
        """Re-evaluate circuit state from rate limiter data + day rollover."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        with self._lock:
            # N2 fix: detect UTC day rollover ourselves. Fresh quota ->
            # straight back to CLOSED (a probe against an untouched budget
            # proves nothing; this also makes queued work recoverable ASAP).
            if self._last_seen_date != today:
                self._last_seen_date = today
                self._half_open_probes_used.clear()
                changed = [m for m, s in self._state.items()
                           if s != CircuitState.CLOSED]
                for m in self._state:
                    self._state[m] = CircuitState.CLOSED
                if changed:
                    logger.info("UTC day rollover -> circuits CLOSED: %s",
                                changed)

            used = self._rl.get_used(model_id)
            limit = self._rl.get_limit(model_id)
            pct = used / limit if limit > 0 else 0
            current = self._state[model_id]

            if pct >= 1.0:
                # Truly exhausted (N3: was 0.80, wasting 20% headroom)
                if current != CircuitState.OPEN:
                    logger.warning("Circuit OPEN for %s (%.1f%%)", model_id, pct * 100)
                    self._state[model_id] = CircuitState.OPEN
            elif current == CircuitState.OPEN:
                # Below exhaustion mid-day (e.g., penalty decay) -> recover
                self._state[model_id] = CircuitState.HALF_OPEN
            elif current == CircuitState.HALF_OPEN and pct < self.TRIGGER_THRESHOLD:
                logger.info("Circuit CLOSED for %s (%.1f%%)", model_id, pct * 100)
                self._state[model_id] = CircuitState.CLOSED
                self._half_open_probes_used[model_id] = 0
            return self._state[model_id]

    def allow_request(self, model_id: str) -> bool:
        """Decide whether a request may proceed right now."""
        state = self.check_and_update(model_id)
        if state == CircuitState.CLOSED:
            return True
        if state == CircuitState.HALF_OPEN:
            with self._lock:
                if self._half_open_probes_used[model_id] < self.HALF_OPEN_PROBES:
                    self._half_open_probes_used[model_id] += 1
                    return True
                return False
        return False  # OPEN

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

    def drain(self, model_id: str) -> list:
        """Return ALL currently-queued payloads for a model (oldest first),
        expiring stale ones. Callers own re-dispatching them."""
        out = []
        with self._lock:
            q = self._queues[model_id]
            now = time.time()
            while q:
                ts, data = q[0]
                if now - ts > self.QUEUE_TTL_SEC:
                    q.popleft(); continue
                q.popleft()
                out.append(data)
        return out

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

"""
Rate Limiter V2 — per-model daily counter + concurrent in-flight limit.

Builds on swarm/resilience/rate_limiter.py. Adds:
- Per-model daily counter (resets at 00:00 UTC)
- Per-model concurrent in-flight counter (max 10 by default)
- Auto signal when 80% of daily limit reached (for circuit breaker)
- Thread-safe, process-local

For distributed multi-instance, swap to Redis-backed via env REDIS_URL.
"""
import threading
import time
import logging
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Any, Deque, Dict, Optional, Tuple


logger = logging.getLogger(__name__)


# Free-tier limits per model — synced to the LIVE NVIDIA NIM catalog
# verified 2026-08-25 (see docs/institutional_audit/LEDGER.md T1).
# Dead models removed; new live models added with conservative tiers.
DAILY_TIERS = {"frontier": 200, "large": 500, "medium": 1000,
               "small": 5000, "safety": 10000}
RPM_TIERS = {"frontier": 12, "large": 20, "medium": 30, "small": 45, "safety": 90}

_LIVE_MODELS = {
    # model_id: (daily_tier, rpm_tier)
    "moonshotai/kimi-k3": ("frontier", "frontier"),
    "stepfun-ai/step-3.7-flash": ("large", "large"),
    "minimaxai/minimax-m3": ("large", "large"),
    "nvidia/nemotron-3-ultra-550b-a55b": ("frontier", "frontier"),
    "openai/gpt-oss-120b": ("large", "large"),
    "nvidia/nemotron-3-super-120b-a12b": ("large", "large"),
    "nvidia/nemotron-3.5-lightning-30b-a3b": ("medium", "medium"),
    "mistralai/mistral-nemotron": ("medium", "medium"),
    "meta/llama-3.3-70b-instruct": ("large", "large"),
    "meta/llama-3.1-70b-instruct": ("medium", "medium"),
    "meta/llama-3.2-11b-vision-instruct": ("medium", "medium"),
    "meta/llama-3.2-90b-vision-instruct": ("large", "large"),
    "nvidia/nemotron-3-nano-30b-a3b": ("small", "small"),
    "nvidia/nemotron-mini-4b-instruct": ("small", "small"),
    "nvidia/nvidia-nemotron-nano-9b-v2": ("small", "small"),
    "openai/gpt-oss-20b": ("small", "small"),
    "google/gemma-3-4b-it": ("small", "small"),
    "nvidia/riva-translate-4b-instruct-v2": ("safety", "safety"),
    "nvidia/riva-translate-4b-instruct-v1.1": ("safety", "safety"),
    "nvidia/nemotron-3.5-content-safety": ("safety", "safety"),
    "nvidia/llama-3.1-nemoguard-8b-content-safety": ("safety", "safety"),
    "nvidia/llama-3.1-nemoguard-8b-topic-control": ("safety", "safety"),
    # Retrieval/embeddings (cheap)
    "baai/bge-m3": ("safety", "safety"),
    "nvidia/nv-embed-v1": ("safety", "safety"),
    "nvidia/llama-3.2-nv-embedqa-1b-v2": ("safety", "safety"),
    "nvidia/llama-3.2-nemoretriever-300m-embed-v2": ("safety", "safety"),
    "nvidia/llama-3.2-nemoretriever-1b-vlm-embed-v1": ("safety", "safety"),
    "nvidia/nemoretriever-parse": ("small", "small"),
    "nvidia/nemotron-parse": ("small", "small"),
}

DEFAULT_DAILY_LIMITS: Dict[str, int] = {
    m: DAILY_TIERS[t] for m, (t, _) in _LIVE_MODELS.items()
}

DEFAULT_RPM_LIMITS: Dict[str, int] = {
    m: RPM_TIERS[t] for m, (_, t) in _LIVE_MODELS.items()
}


class RateLimiterV2:
    """Per-model RPM + daily + concurrent limiter, thread-safe.

    2026-08-25 hardening:
    - RPM sliding window added (NIM free tier is burst-limited per minute;
      a daily-only limiter cannot prevent burst 429s).
    - Attempts are counted at ACQUIRE time (true attempt accounting) —
      previously only successes counted, so a model failing 100% never
      throttled itself.
    - acquire_ex() distinguishes denial reasons so callers (fallback chain)
      stop poisoning daily counters on mere concurrency pressure.
    - All date-reset logic and counter mutations are fully lock-contained;
      stats() iterates over snapshots.
    """

    CONCURRENT_DEFAULT = 10
    WARNING_THRESHOLD = 0.80

    def __init__(
        self,
        custom_limits: Optional[Dict[str, int]] = None,
        custom_rpm: Optional[Dict[str, int]] = None,
        default_rpm: int = 30,
    ):
        self._daily_limits = dict(DEFAULT_DAILY_LIMITS)
        if custom_limits:
            self._daily_limits.update(custom_limits)
        self._rpm_limits = dict(DEFAULT_RPM_LIMITS)
        if custom_rpm:
            self._rpm_limits.update(custom_rpm)
        self._default_rpm = default_rpm

        self._daily_used: Dict[str, int] = defaultdict(int)
        self._daily_reset_date: str = ""
        self._concurrent: Dict[str, int] = defaultdict(int)
        self._rpm_window: Dict[str, Deque[float]] = defaultdict(deque)
        self._warning_emitted: Dict[str, bool] = defaultdict(bool)
        self._lock = threading.RLock()
        self._total_429s = 0

    # ------------------------------------------------------------------
    # Internals (all under _lock unless noted)
    # ------------------------------------------------------------------

    def _check_reset_locked(self) -> None:
        """Reset daily counters when the UTC date changes. Lock MUST be held."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if self._daily_reset_date != today:
            self._daily_used.clear()
            self._warning_emitted.clear()
            self._daily_reset_date = today

    def _prune_rpm_locked(self, model_id: str, now: float) -> None:
        window = self._rpm_window[model_id]
        while window and now - window[0] >= 60.0:
            window.popleft()

    def get_limit(self, model_id: str) -> int:
        return self._daily_limits.get(model_id, 1000)

    def get_rpm(self, model_id: str) -> int:
        return self._rpm_limits.get(model_id, self._default_rpm)

    def get_used(self, model_id: str) -> int:
        with self._lock:
            self._check_reset_locked()
            return self._daily_used[model_id]

    def get_remaining(self, model_id: str) -> int:
        return max(0, self.get_limit(model_id) - self.get_used(model_id))

    def is_near_limit(self, model_id: str) -> bool:
        used, limit = self.get_used(model_id), self.get_limit(model_id)
        return used >= limit * self.WARNING_THRESHOLD

    def is_at_limit(self, model_id: str) -> bool:
        return self.get_used(model_id) >= self.get_limit(model_id)

    # ------------------------------------------------------------------
    # Acquisition
    # ------------------------------------------------------------------

    def acquire_ex(
        self, model_id: str, concurrent: int = CONCURRENT_DEFAULT
    ) -> tuple[bool, Optional[str]]:
        """Try to acquire a slot. Returns (ok, denial_reason).

        Reasons: 'daily' | 'rpm' | 'concurrent' | None.
        On success the attempt IS counted toward daily + RPM immediately
        (attempt accounting), regardless of the call's later outcome.
        """
        now = time.time()
        with self._lock:
            self._check_reset_locked()

            if self._daily_used[model_id] >= self.get_limit(model_id):
                self._total_429s += 1
                logger.warning("Daily rate limit hit for %s", model_id)
                return False, "daily"

            self._prune_rpm_locked(model_id, now)
            if len(self._rpm_window[model_id]) >= self.get_rpm(model_id):
                logger.info("RPM limit hit for %s (%d/min)",
                            model_id, self.get_rpm(model_id))
                return False, "rpm"

            if self._concurrent[model_id] >= concurrent:
                logger.debug("Concurrent limit hit for %s (%d/%d)",
                             model_id, self._concurrent[model_id], concurrent)
                return False, "concurrent"

            self._concurrent[model_id] += 1
            self._rpm_window[model_id].append(now)
            self._daily_used[model_id] += 1
            if (self.is_near_limit(model_id)
                    and not self._warning_emitted[model_id]):
                self._warning_emitted[model_id] = True
                logger.warning("Model %s crossed 80%% of daily limit (%d/%d)",
                               model_id, self._daily_used[model_id],
                               self.get_limit(model_id))
            return True, None

    def acquire(self, model_id: str, concurrent: int = CONCURRENT_DEFAULT) -> bool:
        """Backward-compatible boolean acquisition."""
        ok, _reason = self.acquire_ex(model_id, concurrent)
        return ok

    def release(self, model_id: str) -> None:
        """Release a concurrent slot after the request finishes."""
        with self._lock:
            if self._concurrent[model_id] > 0:
                self._concurrent[model_id] -= 1
            else:
                logger.debug("release() underflow for %s — caller mismatch",
                             model_id)

    # ------------------------------------------------------------------
    # Outcome signals (attempt already counted at acquire; these only add
    # conservative penalties / keep API compatibility)
    # ------------------------------------------------------------------

    def record_success(self, model_id: str) -> None:
        """Success signal. Attempt was counted at acquire; no double count."""

    def record_429(self, model_id: str) -> None:
        """Provider-side 429 penalty bump (conservative safety margin)."""
        with self._lock:
            self._total_429s += 1
            self._daily_used[model_id] += 1

    def record_failure(self, model_id: str) -> None:
        """Non-429 failure signal. Attempt already counted at acquire."""
        # Reserved for future backoff scoring; keeps callers explicit.

    def reset(self, model_id: Optional[str] = None) -> None:
        with self._lock:
            if model_id:
                self._daily_used[model_id] = 0
                self._warning_emitted[model_id] = False
                self._rpm_window[model_id].clear()
            else:
                self._daily_used.clear()
                self._warning_emitted.clear()
                self._rpm_window.clear()

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            self._check_reset_locked()
            snapshot = list(self._daily_used.items())
            total_429s = self._total_429s
            concurrent = dict(self._concurrent)
            limits = dict(self._daily_limits)
            near = [
                {"model": m, "used": u, "limit": limits.get(m, 1000),
                 "pct": round(u / limits.get(m, 1000) * 100, 1)}
                for m, u in snapshot
                if u >= limits.get(m, 1000) * self.WARNING_THRESHOLD
            ]
            at_limit = [m for m, u in snapshot if u >= limits.get(m, 1000)]
        return {
            "reset_date": self._daily_reset_date,
            "total_429s": total_429s,
            "models_tracked": len(snapshot),
            "near_limit": near,
            "at_limit": at_limit,
            "concurrent_in_flight": concurrent,
        }


# Singleton
_default: Optional[RateLimiterV2] = None
_lock = threading.Lock()


def get_rate_limiter() -> RateLimiterV2:
    global _default
    with _lock:
        if _default is None:
            _default = RateLimiterV2()
        return _default


if __name__ == "__main__":
    rl = RateLimiterV2()
    print(f"Nemotron Ultra limit: {rl.get_limit('nvidia/nemotron-3-ultra-550b-a55b')}")
    # Simulate usage
    rl.acquire("nvidia/nemotron-3-ultra-550b-a55b")
    rl.record_success("nvidia/nemotron-3-ultra-550b-a55b")
    print(f"Used: {rl.get_used('nvidia/nemotron-3-ultra-550b-a55b')}")
    print(f"Near limit: {rl.is_near_limit('nvidia/nemotron-3-ultra-550b-a55b')}")
    print(f"Stats: {rl.stats()}")

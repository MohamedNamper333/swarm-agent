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
from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)


# Estimated free-tier daily limits per model (from NVIDIA NIM docs)
# Conservative estimates; actual may be lower — circuit breaker handles overflow.
DEFAULT_DAILY_LIMITS: Dict[str, int] = {
    # Frontier (~200/day)
    "nvidia/nemotron-3-ultra-550b-a55b": 200,
    "deepseek-ai/deepseek-v4-pro": 200,
    "moonshotai/kimi-k2.5": 200,
    # Large (~500/day)
    "nvidia/nemotron-3-super-120b-a12b": 500,
    "nvidia/llama-3.3-nemotron-super-49b-v1.5": 500,
    "nvidia/llama-3.1-nemotron-ultra-253b-v1": 500,
    "openai/gpt-oss-120b": 500,
    "meta/llama-3.3-70b-instruct": 500,
    "z-ai/glm5.1": 500,
    "mistralai/mistral-small-4-119b-2603": 500,
    "mistralai/mistral-medium-3.5-128b": 500,
    "qwen/qwen3-coder-480b-a35b-instruct": 500,
    "qwen/qwen3-next-80b-a3b-instruct": 500,
    # Medium (~1000/day)
    "deepseek-ai/deepseek-v4-flash": 1000,
    "meta/llama-3.1-70b-instruct": 1000,
    "meta/llama-3.2-11b-vision-instruct": 1000,
    "google/gemma-3-27b-it": 1000,
    "qwen/qwen2.5-coder-32b-instruct": 1000,
    "qwen/qwq-32b": 1000,
    "moonshotai/kimi-k2-instruct": 1000,
    "moonshotai/kimi-k2-thinking": 1000,
    "z-ai/glm4.7": 1000,
    "z-ai/glm-5.2": 1000,
    "mistralai/mistral-nemotron": 1000,
    "mistralai/mixtral-8x22b-instruct": 1000,
    "mistralai/ministral-14b-instruct-2512": 1000,
    "sarvamai/sarvam-m": 1000,
    "thinking machines/inkling": 1000,
    "microsoft/phi-4-mini-instruct": 1000,
    "microsoft/phi-4-mini-flash-reasoning": 1000,
    "microsoft/phi-4-multimodal-instruct": 1000,
    "nvidia/llama-3.1-nemotron-nano-8b-v1": 1000,
    "nvidia/nvidia-nemotron-nano-9b-v2": 1000,
    "google/gemma-3n-e4b-it": 1000,
    "meta/llama-3.1-8b-instruct": 1000,
    # Small / Nano (~5000/day)
    "nvidia/nemotron-3-nano-30b-a3b": 5000,
    "nvidia/nemotron-mini-4b-instruct": 5000,
    "nvidia/nemotron-content-safety-reasoning-4b": 5000,
    "nvidia/riva-translate-4b-instruct-v1.1": 5000,
    "nvidia/riva-translate-4b-instruct-v2": 5000,
    "meta/llama-3.2-1b-instruct": 5000,
    "meta/llama-3.2-3b-instruct": 5000,
    "openai/gpt-oss-20b": 5000,
    # Safety (very high — inline filters should never bottleneck)
    "nvidia/nemotron-3.5-content-safety": 10000,
    "nvidia/nemotron-3-content-safety": 10000,
    "nvidia/llama-3.1-nemoguard-8b-content-safety": 5000,
    "nvidia/llama-3.1-nemoguard-8b-topic-control": 5000,
    "nvidia/nemoguard-jailbreak-detect": 5000,
    "nvidia/llama-3.1-nemotron-safety-guard-8b-v3": 5000,
    # Visual / Image (~100-500/day)
    "black-forest-labs/flux.1-dev": 100,
    "black-forest-labs/flux.1-schnell": 500,
    "black-forest-labs/flux.2-klein-4b": 500,
    "black-forest-labs/flux.1-kontext-dev": 200,
    "stabilityai/stable-diffusion-3-medium": 200,
    "stabilityai/stable-diffusion-xl": 200,
    "stabilityai/stable-video-diffusion": 100,
    "microsoft/trellis": 100,
    "nvidia/cosmos-predict1-7b": 100,
    # Retrieval (~5000/day, cheap)
    "baai/bge-m3": 10000,
    "nvidia/nv-embed-v1": 10000,
    "nvidia/llama-3.2-nv-embedqa-1b-v2": 10000,
    "nvidia/llama-3.2-nemoretriever-1b-vlm-embed-v1": 10000,
    "nvidia/llama-3.2-nemoretriever-300m-embed-v2": 10000,
    "nvidia/llama-3.2-nemoretriever-500m-rerank-v2": 10000,
    "nvidia/llama-3.2-nv-rerankqa-1b-v2": 10000,
    "nvidia/nemoretriever-parse": 5000,
    "nvidia/nemotron-parse": 5000,
}


class RateLimiterV2:
    """Per-model daily + concurrent limiter, thread-safe."""

    CONCURRENT_DEFAULT = 10
    WARNING_THRESHOLD = 0.80  # 80% of daily limit triggers warning

    def __init__(self, custom_limits: Optional[Dict[str, int]] = None):
        self._daily_limits = dict(DEFAULT_DAILY_LIMITS)
        if custom_limits:
            self._daily_limits.update(custom_limits)
        self._daily_used: Dict[str, int] = defaultdict(int)
        self._daily_reset_date: str = ""
        self._concurrent: Dict[str, int] = defaultdict(int)
        self._lock = threading.RLock()
        self._warning_emitted: Dict[str, bool] = defaultdict(bool)
        self._total_429s = 0

    def _check_reset(self) -> None:
        """Reset daily counters when UTC date changes."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if self._daily_reset_date != today:
            with self._lock:
                self._daily_used.clear()
                self._warning_emitted.clear()
                self._daily_reset_date = today

    def get_limit(self, model_id: str) -> int:
        return self._daily_limits.get(model_id, 1000)  # default 1000

    def get_used(self, model_id: str) -> int:
        self._check_reset()
        with self._lock:
            return self._daily_used[model_id]

    def get_remaining(self, model_id: str) -> int:
        return max(0, self.get_limit(model_id) - self.get_used(model_id))

    def is_near_limit(self, model_id: str) -> bool:
        """True if >=80% of daily limit used."""
        used = self.get_used(model_id)
        limit = self.get_limit(model_id)
        return used >= limit * self.WARNING_THRESHOLD

    def is_at_limit(self, model_id: str) -> bool:
        return self.get_used(model_id) >= self.get_limit(model_id)

    def acquire(self, model_id: str, concurrent: int = CONCURRENT_DEFAULT) -> bool:
        """Try to acquire a request slot. Returns False if at daily limit or concurrent full."""
        self._check_reset()
        with self._lock:
            if self.is_at_limit(model_id):
                self._total_429s += 1
                logger.warning("Rate limit hit for %s", model_id)
                return False
            if self._concurrent[model_id] >= concurrent:
                logger.debug("Concurrent limit hit for %s (%d/%d)",
                             model_id, self._concurrent[model_id], concurrent)
                return False
            self._concurrent[model_id] += 1
            return True

    def release(self, model_id: str) -> None:
        """Release a concurrent slot after request completes (success or fail)."""
        with self._lock:
            if self._concurrent[model_id] > 0:
                self._concurrent[model_id] -= 1

    def record_success(self, model_id: str) -> None:
        """Record a successful request (after concurrent slot released)."""
        with self._lock:
            self._daily_used[model_id] += 1
            if self.is_near_limit(model_id) and not self._warning_emitted[model_id]:
                self._warning_emitted[model_id] = True
                logger.warning("Model %s reached 80%% of daily limit (%d/%d)",
                               model_id, self._daily_used[model_id], self.get_limit(model_id))

    def record_429(self, model_id: str) -> None:
        """Server-side 429 — also counts toward limit."""
        self._total_429s += 1
        with self._lock:
            self._daily_used[model_id] += 1

    def reset(self, model_id: Optional[str] = None) -> None:
        """Reset counter(s) — useful for tests."""
        with self._lock:
            if model_id:
                self._daily_used[model_id] = 0
                self._warning_emitted[model_id] = False
            else:
                self._daily_used.clear()
                self._warning_emitted.clear()

    def stats(self) -> Dict[str, Any]:
        self._check_reset()
        with self._lock:
            return {
                "reset_date": self._daily_reset_date,
                "total_429s": self._total_429s,
                "models_tracked": len(self._daily_used),
                "near_limit": [
                    {"model": m, "used": u, "limit": self.get_limit(m),
                     "pct": round(u / self.get_limit(m) * 100, 1)}
                    for m, u in self._daily_used.items()
                    if self.is_near_limit(m)
                ],
                "at_limit": [
                    m for m in self._daily_used
                    if self.is_at_limit(m)
                ],
                "concurrent_in_flight": dict(self._concurrent),
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

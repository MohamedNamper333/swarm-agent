"""
Fallback Chain Executor — 2 retries × 3s timeout per level, 3 levels max.

For a role, tries primary → fallback1 → fallback2 in sequence.
Each level: 2 retries with exponential backoff (1s, 2s), 3s timeout.
Integrates with RateLimiterV2 (records success/429) and CircuitBreaker
(consults before sending, queues if open).

Returns a FallbackResult with the chosen model, output, and trace.
"""
import time
import logging
import threading
from typing import Optional, Any, Dict, Callable, List
from dataclasses import dataclass, field

from swarm.enterprise.core.model_registry_v2 import FallbackChain, EnterpriseModelRegistry
from swarm.resilience.rate_limiter_v2 import RateLimiterV2, get_rate_limiter
from swarm.enterprise.core.circuit_breaker import CircuitBreaker, get_circuit_breaker

logger = logging.getLogger(__name__)


@dataclass
class FallbackResult:
    role: str
    chosen_model: Optional[str]
    level_used: int  # 1, 2, or 3 (3 = fallback2)
    output: Any
    success: bool
    attempts: int
    total_latency_ms: float
    trace: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "chosen_model": self.chosen_model,
            "level_used": self.level_used,
            "output": self.output,
            "success": self.success,
            "attempts": self.attempts,
            "total_latency_ms": self.total_latency_ms,
            "error": self.error,
            "trace": self.trace,
        }


class FallbackChainExecutor:
    """Executes fallback chains with retries, timeout, rate limiting, circuit breaking."""

    def __init__(
        self,
        rate_limiter: Optional[RateLimiterV2] = None,
        circuit_breaker: Optional[CircuitBreaker] = None,
        call_fn: Optional[Callable[..., Any]] = None,
        nim_client: Optional[Any] = None,
    ):
        self._rl = rate_limiter or get_rate_limiter()
        self._cb = circuit_breaker or get_circuit_breaker()
        # Production default: real NVIDIA NIM integration.
        # Tests pass an explicit call_fn (mock or recording).
        # Lazy import to avoid circular dependency.
        if call_fn is not None:
            self._call_fn = call_fn
        else:
            self._call_fn = self._make_nim_call(nim_client)

    @staticmethod
    def _make_nim_client():
        """Build a NIM client, or return None if NVIDIA_API_KEY is missing."""
        import os
        api_key = os.environ.get("NVIDIA_API_KEY")
        if not api_key:
            return None
        try:
            from swarm.integrations.nvidia_nim import NVIDIANIMClient
            return NVIDIANIMClient(api_key=api_key)
        except Exception as exc:
            logger.warning("NIM client init failed: %s", exc)
            return None

    def _make_nim_call(self, nim_client=None):
        """Build a real call_fn that invokes NVIDIA NIM via the executor chain.

        If no NVIDIA_API_KEY is configured, falls back to placeholder so tests
        can still run without network access. Production deployments MUST set
        the env var.
        """
        client = nim_client or self._make_nim_client()
        if client is None:
            # SAFETY: never fabricate responses silently in production. Placeholder
            # is opt-in for offline tests only via SWARM_ALLOW_PLACEHOLDER=1.
            import os
            if os.environ.get("SWARM_ALLOW_PLACEHOLDER") == "1":
                logger.warning(
                    "NVIDIA_API_KEY not set — placeholder responses ENABLED "
                    "(SWARM_ALLOW_PLACEHOLDER=1). For tests only!"
                )
                return self._placeholder_call
            logger.error(
                "NVIDIA_API_KEY not set and SWARM_ALLOW_PLACEHOLDER!=1 — "
                "inference calls will fail fast. Set the env var for real inference."
            )

            def _no_client_call(model_id: str, prompt: Any, timeout: float = 3.0, **kwargs):
                raise RuntimeError(
                    "NVIDIA_API_KEY not configured; refusing to fabricate model output"
                )
            return _no_client_call

        def nim_call(model_id: str, prompt: Any, timeout: float = 3.0, **kwargs):
            from swarm.integrations.nvidia_nim import ChatMessage
            messages = [ChatMessage(role="user", content=str(prompt))]
            kwargs.setdefault("temperature", 0.7)
            kwargs.setdefault("max_tokens", 1024)
            result = client.chat(
                model=model_id, messages=messages, timeout=timeout, **kwargs
            )
            # Return content string; orchestrators store this as result.output.
            return result.content

        return nim_call

    @staticmethod
    def _placeholder_call(model_id: str, prompt: Any, timeout: float = 0.0, **kwargs: Any) -> Any:
        """Smart placeholder for tests / when no API key.

        Uses SmartPlaceholder to generate realistic responses based on model type
        (reasoning, code, image, video, embedding, safety, translation, text).
        Returns a string that can be safely parsed by all downstream agents.
        """
        from swarm.enterprise.core.placeholder import SmartPlaceholder
        placeholder = SmartPlaceholder()
        response = placeholder.generate(model_id, prompt, timeout=timeout, **kwargs)
        # Return as string for backward compatibility with nim_call
        return response.response_text

    def execute(
        self,
        role: str,
        prompt: Any,
        chain: Optional[FallbackChain] = None,
        **call_kwargs: Any,
    ) -> FallbackResult:
        """Execute the fallback chain for a role with full retry/timeout logic."""
        if chain is None:
            chain = EnterpriseModelRegistry.get_chain(role)
        if chain is None:
            return FallbackResult(
                role=role, chosen_model=None, level_used=0, output=None,
                success=False, attempts=0, total_latency_ms=0.0,
                error=f"unknown role: {role}",
            )

        start = time.time()
        trace: List[Dict[str, Any]] = []
        attempts = 0
        levels = chain.levels()

        for level_idx, model_id in enumerate(levels):
            level = level_idx + 1
            timeout = chain.timeout_sec
            for retry in range(chain.max_retries):
                attempts += 1
                # Circuit breaker gate
                if not self._cb.allow_request(model_id):
                    queued = self._cb.enqueue(model_id, {"role": role, "prompt": prompt})
                    trace.append({
                        "level": level, "retry": retry + 1, "model": model_id,
                        "skipped": "circuit_open", "queued": queued,
                    })
                    break  # skip to next level

                # Rate limiter gate — reason-aware (H1 fix):
                # 'daily'  → real quota exhaustion: record penalty + skip level.
                # 'rpm'    → burst window full: brief wait then retry same level.
                # 'concurrent' → local pressure only; NEVER poisons counters.
                ok, reason = self._rl.acquire_ex(model_id, concurrent=10)
                if not ok:
                    if reason == "rpm":
                        time.sleep(0.5)
                        ok, reason = self._rl.acquire_ex(model_id, concurrent=10)
                        if ok:
                            reason = None
                    if not ok and reason == "daily":
                        self._rl.record_429(model_id)
                    trace.append({
                        "level": level, "retry": retry + 1, "model": model_id,
                        "skipped": f"rate_limit:{reason}",
                    })
                    break  # skip to next level

                # Try the call with timeout
                t0 = time.time()
                try:
                    output = self._call_fn(model_id, prompt, timeout=timeout, **call_kwargs)
                    latency_ms = (time.time() - t0) * 1000
                    self._rl.release(model_id)
                    self._rl.record_success(model_id)
                    trace.append({
                        "level": level, "retry": retry + 1, "model": model_id,
                        "latency_ms": latency_ms, "success": True,
                    })
                    return FallbackResult(
                        role=role, chosen_model=model_id, level_used=level,
                        output=output, success=True, attempts=attempts,
                        total_latency_ms=(time.time() - start) * 1000,
                        trace=trace,
                    )
                except Exception as e:
                    latency_ms = (time.time() - t0) * 1000
                    self._rl.release(model_id)
                    err_type = type(e).__name__
                    trace.append({
                        "level": level, "retry": retry + 1, "model": model_id,
                        "latency_ms": latency_ms, "error": err_type,
                        "error_msg": str(e)[:200],
                    })
                    logger.warning("Fallback exec %s [%s, retry %d]: %s",
                                   role, model_id, retry + 1, err_type)
                    # Exponential backoff before retry
                    if retry < chain.max_retries - 1:
                        time.sleep(1 * (2 ** retry))
                    continue

        # All levels failed
        return FallbackResult(
            role=role, chosen_model=None, level_used=0, output=None,
            success=False, attempts=attempts,
            total_latency_ms=(time.time() - start) * 1000,
            trace=trace,
            error="all_fallback_levels_failed",
        )


if __name__ == "__main__":
    exe = FallbackChainExecutor()
    chain = EnterpriseModelRegistry.get_chain("chairman")
    print(f"Chairman chain: primary={chain.primary} f1={chain.fallback1} f2={chain.fallback2}")

    result = exe.execute("chairman", "Should we deploy to prod?")
    print(f"Success: {result.success}, model: {result.chosen_model}, "
          f"level: {result.level_used}, attempts: {result.attempts}, "
          f"latency: {result.total_latency_ms:.1f}ms")
    print(f"Trace: {result.trace}")

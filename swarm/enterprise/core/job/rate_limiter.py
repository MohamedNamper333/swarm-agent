"""
Rate Limiter - Token bucket and sliding window rate limiting per tenant/worker.
"""

import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
from collections import deque
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# Rate Limit Models
# =============================================================================

class RateLimitAlgorithm(str, Enum):
    """Rate limiting algorithm."""
    TOKEN_BUCKET = "token_bucket"      # Token bucket - allows bursts
    SLIDING_WINDOW = "sliding_window"  # Sliding window - smooth rate
    FIXED_WINDOW = "fixed_window"      # Fixed window - simple but can burst at boundaries


@dataclass(frozen=True)
class RateLimitConfig:
    """Configuration for a rate limit."""
    # Key format: "tenant:{tenant_id}" or "worker:{worker_id}" or "global"
    key: str
    
    # Limits
    max_requests: int                     # Max requests per window
    window_seconds: int                   # Time window in seconds
    
    # Token bucket specific
    tokens_per_second: Optional[float] = None  # Refill rate
    bucket_capacity: Optional[int] = None      # Max bucket size
    
    # Algorithm
    algorithm: RateLimitAlgorithm = RateLimitAlgorithm.TOKEN_BUCKET
    
    # Metadata
    description: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class RateLimitState:
    """Current state of a rate limit."""
    key: str
    
    # Token bucket state
    tokens: float = 0.0
    last_refill: float = 0.0
    
    # Sliding window state
    requests: List[float] = field(default_factory=list)  # Timestamps
    
    # Fixed window state
    window_start: float = 0.0
    window_count: int = 0
    
    # Stats
    total_requests: int = 0
    rejected_requests: int = 0
    last_rejected_at: Optional[float] = None


@dataclass
class RateLimitResult:
    """Result of a rate limit check."""
    allowed: bool
    remaining: int
    reset_at: float  # Unix timestamp when limit resets
    retry_after: Optional[float] = None  # Seconds until next allowed
    limit: int = 0
    used: int = 0


# =============================================================================
# Rate Limiter
# =============================================================================

class RateLimiter:
    """
    Multi-algorithm rate limiter with per-key limits.
    
    Supports:
    - Token Bucket (allows controlled bursts)
    - Sliding Window (smooth rate limiting)
    - Fixed Window (simple, memory efficient)
    - Hierarchical limits (global + tenant + worker)
    """
    
    def __init__(
        self,
        default_config: Optional[RateLimitConfig] = None,
        cleanup_interval_sec: int = 300,
    ):
        self.default_config = default_config or RateLimitConfig(
            key="global",
            max_requests=1000,
            window_seconds=60,
            algorithm=RateLimitAlgorithm.TOKEN_BUCKET,
        )
        
        self._configs: Dict[str, RateLimitConfig] = {}
        self._states: Dict[str, RateLimitState] = {}
        self._lock = threading.RLock()
        
        # Background cleanup
        self._cleanup_interval_sec = cleanup_interval_sec
        self._cleanup_running = False
        self._cleanup_thread: Optional[threading.Thread] = None
        self._shutdown_event = threading.Event()
    
    def add_limit(self, config: RateLimitConfig) -> None:
        """Add or update a rate limit configuration."""
        with self._lock:
            self._configs[config.key] = config
            
            # Initialize state if needed
            if config.key not in self._states:
                self._init_state(config.key)
    
    def remove_limit(self, key: str) -> bool:
        """Remove a rate limit configuration."""
        with self._lock:
            if key in self._configs:
                del self._configs[key]
                if key in self._states:
                    del self._states[key]
                return True
            return False
    
    def get_limit(self, key: str) -> Optional[RateLimitConfig]:
        """Get rate limit configuration."""
        with self._lock:
            return self._configs.get(key)
    
    def _init_state(self, key: str) -> None:
        """Initialize state for a key."""
        now = time.time()
        config = self._configs.get(key, self.default_config)
        
        state = RateLimitState(key=key)
        
        if config.algorithm == RateLimitAlgorithm.TOKEN_BUCKET:
            state.tokens = config.bucket_capacity or config.max_requests
            state.last_refill = now
        
        elif config.algorithm == RateLimitAlgorithm.FIXED_WINDOW:
            state.window_start = now
            state.window_count = 0
        
        self._states[key] = state
    
    def check_limit(
        self,
        key: str,
        cost: int = 1,
    ) -> RateLimitResult:
        """
        Check if request is allowed under rate limit.
        
        Args:
            key: Rate limit key (e.g., "tenant:abc", "worker:xyz")
            cost: Number of tokens/requests to consume
            
        Returns:
            RateLimitResult with allowed status and metadata
        """
        with self._lock:
            config = self._configs.get(key)
            if not config:
                # Use default config
                config = RateLimitConfig(
                    key=key,
                    max_requests=self.default_config.max_requests,
                    window_seconds=self.default_config.window_seconds,
                    algorithm=self.default_config.algorithm,
                    tokens_per_second=self.default_config.tokens_per_second,
                    bucket_capacity=self.default_config.bucket_capacity,
                )
                self._configs[key] = config
                self._init_state(key)
            
            state = self._states.get(key)
            if not state:
                self._init_state(key)
                state = self._states[key]
            
            # Apply appropriate algorithm
            if config.algorithm == RateLimitAlgorithm.TOKEN_BUCKET:
                return self._check_token_bucket(config, state, cost)
            elif config.algorithm == RateLimitAlgorithm.SLIDING_WINDOW:
                return self._check_sliding_window(config, state, cost)
            else:  # FIXED_WINDOW
                return self._check_fixed_window(config, state, cost)
    
    def _check_token_bucket(
        self,
        config: RateLimitConfig,
        state: RateLimitState,
        cost: int,
    ) -> RateLimitResult:
        """Check rate limit using token bucket algorithm."""
        now = time.time()
        
        # Refill tokens
        refill_rate = config.tokens_per_second or (config.max_requests / config.window_seconds)
        capacity = config.bucket_capacity or config.max_requests
        
        elapsed = now - state.last_refill
        state.tokens = min(capacity, state.tokens + elapsed * refill_rate)
        state.last_refill = now
        
        # Check if allowed
        if state.tokens >= cost:
            state.tokens -= cost
            state.total_requests += 1
            
            return RateLimitResult(
                allowed=True,
                remaining=int(state.tokens),
                reset_at=now + (state.tokens / refill_rate) if refill_rate > 0 else now + config.window_seconds,
                limit=capacity,
                used=cost,
            )
        else:
            state.rejected_requests += 1
            state.last_rejected_at = now
            
            # Calculate retry_after
            tokens_needed = cost - state.tokens
            retry_after = tokens_needed / refill_rate if refill_rate > 0 else config.window_seconds
            
            return RateLimitResult(
                allowed=False,
                remaining=int(state.tokens),
                reset_at=now + retry_after,
                retry_after=retry_after,
                limit=capacity,
                used=0,
            )
    
    def _check_sliding_window(
        self,
        config: RateLimitConfig,
        state: RateLimitState,
        cost: int,
    ) -> RateLimitResult:
        """Check rate limit using sliding window algorithm."""
        now = time.time()
        window_start = now - config.window_seconds
        
        # Remove old requests
        state.requests = [t for t in state.requests if t > window_start]
        
        current_count = len(state.requests)
        
        if current_count + cost <= config.max_requests:
            # Add new requests
            for _ in range(cost):
                state.requests.append(now)
            state.total_requests += 1
            
            return RateLimitResult(
                allowed=True,
                remaining=config.max_requests - current_count - cost,
                reset_at=now + config.window_seconds,
                limit=config.max_requests,
                used=cost,
            )
        else:
            state.rejected_requests += 1
            state.last_rejected_at = now
            
            # Find when oldest request expires
            oldest = min(state.requests) if state.requests else now
            retry_after = (oldest + config.window_seconds) - now
            
            return RateLimitResult(
                allowed=False,
                remaining=0,
                reset_at=oldest + config.window_seconds,
                retry_after=max(0, retry_after),
                limit=config.max_requests,
                used=0,
            )
    
    def _check_fixed_window(
        self,
        config: RateLimitConfig,
        state: RateLimitState,
        cost: int,
    ) -> RateLimitResult:
        """Check rate limit using fixed window algorithm."""
        now = time.time()
        
        # Check if window expired
        if now - state.window_start >= config.window_seconds:
            state.window_start = now
            state.window_count = 0
        
        if state.window_count + cost <= config.max_requests:
            state.window_count += cost
            state.total_requests += 1
            
            return RateLimitResult(
                allowed=True,
                remaining=config.max_requests - state.window_count,
                reset_at=state.window_start + config.window_seconds,
                limit=config.max_requests,
                used=cost,
            )
        else:
            state.rejected_requests += 1
            state.last_rejected_at = now
            
            retry_after = (state.window_start + config.window_seconds) - now
            
            return RateLimitResult(
                allowed=False,
                remaining=0,
                reset_at=state.window_start + config.window_seconds,
                retry_after=max(0, retry_after),
                limit=config.max_requests,
                used=0,
            )
    
    def check_multiple(
        self,
        keys: List[str],
        cost: int = 1,
    ) -> Dict[str, RateLimitResult]:
        """Check multiple rate limits at once (all must pass)."""
        results = {}
        for key in keys:
            results[key] = self.check_limit(key, cost)
        return results
    
    def check_all_allowed(
        self,
        keys: List[str],
        cost: int = 1,
    ) -> Tuple[bool, Dict[str, RateLimitResult]]:
        """Check if all rate limits allow the request."""
        results = self.check_multiple(keys, cost)
        all_allowed = all(r.allowed for r in results.values())
        return all_allowed, results
    
    def get_state(self, key: str) -> Optional[RateLimitState]:
        """Get current state for a key."""
        with self._lock:
            return self._states.get(key)
    
    def get_all_states(self) -> Dict[str, RateLimitState]:
        """Get all current states."""
        with self._lock:
            return dict(self._states)
    
    def reset(self, key: str) -> bool:
        """Reset rate limit state for a key."""
        with self._lock:
            if key in self._states:
                self._init_state(key)
                return True
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get rate limiter statistics."""
        with self._lock:
            total_requests = sum(s.total_requests for s in self._states.values())
            total_rejected = sum(s.rejected_requests for s in self._states.values())
            
            return {
                "total_limits": len(self._configs),
                "active_keys": len(self._states),
                "total_requests": total_requests,
                "total_rejected": total_rejected,
                "rejection_rate": total_rejected / max(1, total_requests),
                "by_key": {
                    key: {
                        "total_requests": state.total_requests,
                        "rejected_requests": state.rejected_requests,
                        "rejection_rate": state.rejected_requests / max(1, state.total_requests),
                    }
                    for key, state in self._states.items()
                },
            }
    
    def start_cleanup(self) -> None:
        """Start background cleanup of stale states."""
        if self._cleanup_running:
            return
        
        self._cleanup_running = True
        self._shutdown_event.clear()
        
        def cleanup_loop():
            logger.info("Rate limiter cleanup started")
            
            while self._cleanup_running and not self._shutdown_event.is_set():
                try:
                    self._cleanup_stale_states()
                except Exception as e:
                    logger.error(f"Rate limiter cleanup error: {e}")
                
                self._shutdown_event.wait(timeout=self._cleanup_interval_sec)
            
            logger.info("Rate limiter cleanup stopped")
        
        self._cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)
        self._cleanup_thread.start()
    
    def stop_cleanup(self) -> None:
        """Stop background cleanup."""
        if not self._cleanup_running:
            return
        
        self._cleanup_running = False
        self._shutdown_event.set()
        
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=5)
    
    def _cleanup_stale_states(self) -> None:
        """Remove states that haven't been used recently."""
        with self._lock:
            now = time.time()
            stale_threshold = 3600  # 1 hour
            
            stale_keys = []
            for key, state in self._states.items():
                # Check last activity
                last_activity = state.last_refill
                if state.requests:
                    last_activity = max(last_activity, max(state.requests))
                if state.last_rejected_at:
                    last_activity = max(last_activity, state.last_rejected_at)
                
                if now - last_activity > stale_threshold:
                    stale_keys.append(key)
            
            for key in stale_keys:
                if key != "global":  # Never remove global
                    del self._states[key]
                    logger.debug(f"Cleaned up stale rate limit state: {key}")


# =============================================================================
# Hierarchical Rate Limiter (Global + Tenant + Worker)
# =============================================================================

class HierarchicalRateLimiter:
    """
    Rate limiter with hierarchy: Global -> Tenant -> Worker.
    
    All levels must allow for request to proceed.
    """
    
    def __init__(
        self,
        global_config: RateLimitConfig,
        tenant_config_template: Optional[RateLimitConfig] = None,
        worker_config_template: Optional[RateLimitConfig] = None,
    ):
        self.global_limiter = RateLimiter(global_config)
        
        self.tenant_config_template = tenant_config_template
        self.worker_config_template = worker_config_template
        
        self._tenant_limiters: Dict[str, RateLimiter] = {}
        self._worker_limiters: Dict[str, RateLimiter] = {}
        self._lock = threading.RLock()
    
    def check(
        self,
        tenant_id: str,
        worker_id: Optional[str] = None,
        cost: int = 1,
    ) -> Tuple[bool, Dict[str, RateLimitResult]]:
        """Check all applicable rate limits."""
        keys = ["global"]
        limiters = [self.global_limiter]
        
        # Tenant limit
        if tenant_id:
            tenant_key = f"tenant:{tenant_id}"
            keys.append(tenant_key)
            
            with self._lock:
                if tenant_id not in self._tenant_limiters:
                    if self.tenant_config_template:
                        config = RateLimitConfig(
                            key=tenant_key,
                            max_requests=self.tenant_config_template.max_requests,
                            window_seconds=self.tenant_config_template.window_seconds,
                            algorithm=self.tenant_config_template.algorithm,
                            tokens_per_second=self.tenant_config_template.tokens_per_second,
                            bucket_capacity=self.tenant_config_template.bucket_capacity,
                        )
                    else:
                        config = RateLimitConfig(
                            key=tenant_key,
                            max_requests=100,
                            window_seconds=60,
                        )
                    limiter = RateLimiter(config)
                    self._tenant_limiters[tenant_id] = limiter
                else:
                    limiter = self._tenant_limiters[tenant_id]
                limiters.append(limiter)
        
        # Worker limit
        if worker_id:
            worker_key = f"worker:{worker_id}"
            keys.append(worker_key)
            
            with self._lock:
                if worker_id not in self._worker_limiters:
                    if self.worker_config_template:
                        config = RateLimitConfig(
                            key=worker_key,
                            max_requests=self.worker_config_template.max_requests,
                            window_seconds=self.worker_config_template.window_seconds,
                            algorithm=self.worker_config_template.algorithm,
                            tokens_per_second=self.worker_config_template.tokens_per_second,
                            bucket_capacity=self.worker_config_template.bucket_capacity,
                        )
                    else:
                        config = RateLimitConfig(
                            key=worker_key,
                            max_requests=10,
                            window_seconds=60,
                        )
                    limiter = RateLimiter(config)
                    self._worker_limiters[worker_id] = limiter
                else:
                    limiter = self._worker_limiters[worker_id]
                limiters.append(limiter)
        
        # Check all
        results = {}
        for key, limiter in zip(keys, limiters):
            results[key] = limiter.check_limit(key, cost)
        
        all_allowed = all(r.allowed for r in results.values())
        return all_allowed, results
    
    def get_stats(self) -> Dict[str, Any]:
        """Get combined statistics."""
        stats = {
            "global": self.global_limiter.get_stats(),
            "tenants": {},
            "workers": {},
        }
        
        for tenant_id, limiter in self._tenant_limiters.items():
            stats["tenants"][tenant_id] = limiter.get_stats()
        
        for worker_id, limiter in self._worker_limiters.items():
            stats["workers"][worker_id] = limiter.get_stats()
        
        return stats


# =============================================================================
# Factory
# =============================================================================

def create_rate_limiter(
    max_requests: int = 1000,
    window_seconds: int = 60,
    algorithm: RateLimitAlgorithm = RateLimitAlgorithm.TOKEN_BUCKET,
    tokens_per_second: Optional[float] = None,
    bucket_capacity: Optional[int] = None,
) -> RateLimiter:
    """Create a RateLimiter with default config."""
    config = RateLimitConfig(
        key="global",
        max_requests=max_requests,
        window_seconds=window_seconds,
        algorithm=algorithm,
        tokens_per_second=tokens_per_second,
        bucket_capacity=bucket_capacity,
    )
    return RateLimiter(config)


def create_hierarchical_rate_limiter(
    global_max_requests: int = 10000,
    global_window_seconds: int = 60,
    tenant_max_requests: int = 1000,
    tenant_window_seconds: int = 60,
    worker_max_requests: int = 100,
    worker_window_seconds: int = 60,
) -> HierarchicalRateLimiter:
    """Create a HierarchicalRateLimiter with sensible defaults."""
    global_config = RateLimitConfig(
        key="global",
        max_requests=global_max_requests,
        window_seconds=global_window_seconds,
    )
    
    tenant_template = RateLimitConfig(
        key="tenant:template",
        max_requests=tenant_max_requests,
        window_seconds=tenant_window_seconds,
    )
    
    worker_template = RateLimitConfig(
        key="worker:template",
        max_requests=worker_max_requests,
        window_seconds=worker_window_seconds,
    )
    
    return HierarchicalRateLimiter(
        global_config=global_config,
        tenant_config_template=tenant_template,
        worker_config_template=worker_template,
    )

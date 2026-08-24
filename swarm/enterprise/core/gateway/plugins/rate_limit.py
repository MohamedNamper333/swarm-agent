"""
Rate Limiting Plugins for API Gateway.
Implements various rate limiting algorithms.
"""

import asyncio
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from collections import deque
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# Rate Limit Models
# =============================================================================

class RateLimitAlgorithm(str, Enum):
    TOKEN_BUCKET = "token_bucket"
    SLIDING_WINDOW = "sliding_window"
    FIXED_WINDOW = "fixed_window"


@dataclass
class RateLimitConfig:
    """Configuration for a rate limit."""
    key: str
    max_requests: int
    window_seconds: int
    algorithm: RateLimitAlgorithm = RateLimitAlgorithm.SLIDING_WINDOW


@dataclass
class RateLimitState:
    """Current state of a rate limit."""
    key: str
    tokens: float = 0.0
    last_refill: float = 0.0
    requests: List[float] = field(default_factory=list)


@dataclass
class RateLimitResult:
    """Result of a rate limit check."""
    allowed: bool
    remaining: int
    reset_at: float
    retry_after: Optional[float] = None
    limit: int = 0
    used: int = 0


# =============================================================================
# Rate Limiter Backend
# =============================================================================

class RateLimiterBackend(ABC):
    """Abstract rate limiter backend."""
    
    @abstractmethod
    async def check_limit(
        self,
        key: str,
        limit: int,
        window_seconds: int,
    ) -> bool:
        pass
    
    @abstractmethod
    async def get_remaining(self, key: str, limit: int, window_seconds: int) -> int:
        pass
    
    @abstractmethod
    async def reset(self, key: str) -> None:
        pass


class InMemoryRateLimiter:
    """In-memory rate limiter with sliding window."""
    
    def __init__(self):
        self._requests: Dict[str, List[float]] = {}
        self._lock = asyncio.Lock()
    
    async def check_limit(self, key: str, limit: int, window_seconds: int) -> bool:
        now = time.time()
        window_start = now - window_seconds
        
        async with self._lock:
            # Clean old requests
            if key in self._requests:
                self._requests[key] = [
                    ts for ts in self._requests[key] 
                    if ts > now - window_seconds
                ]
            else:
                self._requests[key] = []
            
            if len(self._requests[key]) >= limit:
                return False
            
            self._requests[key].append(now)
            return True
    
    async def get_remaining(self, key: str, limit: int, window_seconds: int) -> int:
        window_start = time.time() - window_seconds
        if key in self._requests:
            count = sum(1 for ts in self._requests[key] if ts > time.time() - window_seconds)
            return max(0, limit - len(self._requests[key]))
        return 0
    
    async def reset(self, key: str) -> None:
        if key in self._requests:
            del self._requests[key]


class SlidingWindowRateLimiter:
    """Sliding window rate limiter with configurable precision."""
    
    def __init__(
        self,
        default_limit: int = 1000,
        default_window_seconds: int = 60,
        key_func: Optional[Callable[[Dict], str]] = None,
    ):
        self.default_limit = default_limit
        self.default_window = default_window_seconds
        self.key_func = key_func or (lambda req: req.get("client_ip", "unknown"))
        self._requests: Dict[str, List[float]] = {}
        self._lock = asyncio.Lock()
    
    async def check_limit(
        self,
        request: Dict[str, Any],
        limit: Optional[int] = None,
        window_seconds: Optional[int] = None,
        key: Optional[str] = None,
    ) -> tuple[bool, Dict[str, Any]]:
        """Check if request is within rate limit.
        
        Returns:
            Tuple of (allowed, metadata_dict)
        """
        now = time.time()
        limit = limit or self.default_limit
        window = window_seconds or self.default_window
        key = key or self.key_func(request)
        
        window_start = now - window
        
        async with self._lock:
            if key not in self._requests:
                self._requests[key] = []
            
            # Clean old requests
            self._requests[key] = [
                ts for ts in self._requests[key] 
                if ts > now - window
            ]
            
            current_count = len(self._requests[key])
            
            if current_count >= limit:
                # Rate limited
                return False, {
                    "allowed": False,
                    "limit": limit,
                    "remaining": 0,
                    "reset_at": time.time() + window,
                    "retry_after": window,
                }
            
            # Add request
            self._requests[key].append(now)
            
            return True, {
                "allowed": True,
                "limit": limit,
                "remaining": limit - len(self._requests[key]),
                "reset_at": now + window,
            }
    
    def get_remaining(self, key: str, limit: int, window_seconds: int) -> int:
        window_start = time.time() - window_seconds
        if key in self._requests:
            count = sum(1 for ts in self._requests[key] if ts > time.time() - window_seconds)
            return max(0, limit - count)
        return 0
    
    def reset(self, key: str) -> None:
        if key in self._requests:
            del self._requests[key]


class TokenBucketRateLimiter:
    """Token bucket rate limiter for smoother rate limiting."""
    
    def __init__(
        self,
        rate: float = 100,  # requests per second
        burst: int = 100,
    ):
        self.rate = rate
        self.burst = burst
        self.buckets: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
    
    async def check_limit(self, key: str, tokens: int = 1) -> bool:
        """Check if request is allowed, consuming tokens."""
        async with self._lock:
            now = time.time()
            
            if key not in self._buckets:
                self._buckets[key] = {
                    "tokens": float(burst),
                    "last_refill": time.time(),
                }
            
            bucket = self._buckets[key]
            
            # Refill tokens
            elapsed = now - bucket["last_refill"]
            bucket["tokens"] = min(
                self.burst,
                bucket["tokens"] + elapsed * self.rate
            )
            bucket["last_refill"] = now
            
            if bucket["tokens"] >= 1:
                bucket["tokens"] -= 1
                return True
            
            return False
    
    def get_tokens(self, key: str) -> float:
        if key in self._buckets:
            bucket = self._buckets[key]
            elapsed = time.time() - bucket["last_refill"]
            tokens = min(
                self.burst,
                bucket["tokens"] + (time.time() - bucket["last_refill"]) * self.rate
            )
            return tokens
        return self.burst


class AdaptiveRateLimiter:
    """Adaptive rate limiter that adjusts based on error rates."""
    
    def __init__(
        self,
        min_limit: int = 10,
        max_limit: int = 10000,
        target_error_rate: float = 0.01,
        adjustment_factor: float = 1.5,
    ):
        self.min_limit = min_limit
        self.max_limit = max_limit
        self.target_error_rate = target_error_rate
        self.adjustment_factor = adjustment_factor
        self.current_limit = 1000
        self.error_count = 0
        self.request_count = 0
        self._lock = asyncio.Lock()
        self._window_start = time.time()
    
    async def check_limit(self, key: str) -> bool:
        async with self._lock:
            self.request_count += 1
            
            # Reset window every minute
            if time.time() - self._window_start > 60:
                self._adjust_limit()
                self._window_start = time.time()
                self.error_count = 0
                self.request_count = 0
            
            return True
    
    def record_error(self):
        self.error_count += 1
    
    def record_success(self):
        pass
    
    def _adjust_limit(self):
        if self.request_count == 0:
            return
        
        error_rate = self.error_count / self.request_count
        
        if error_rate > self.target_error_rate:
            # Reduce limit
            self.current_limit = max(
                self.min_limit,
                int(self.current_limit / self.adjustment_factor)
            )
        elif error_rate < self.target_error_rate / 2:
            # Increase limit
            self.current_limit = min(
                self.max_limit,
                int(self.current_limit * self.adjustment_factor)
            )


class RateLimitMiddleware:
    """Rate limiting middleware for gateway."""
    
    def __init__(
        self,
        limiter,
        key_func: Optional[Callable] = None,
        exempt_routes: Optional[List[str]] = None,
        exempt_ips: Optional[Set[str]] = None,
    ):
        self.limiter = limiter
        self.key_func = key_func or (lambda req: req.get("client_ip", "unknown"))
        self.exempt_routes = exempt_routes or ["/health", "/metrics", "/ready"]
        self.exempt_ips = exempt_ips or set()
    
    async def __call__(self, request: Dict[str, Any]) -> Dict[str, Any]:
        # Check exemptions
        path = request.get("path", "")
        if any(request.get("path", "").startswith(route) for route in self.exempt_routes):
            return request
        
        client_ip = request.get("client_ip", "unknown")
        if client_ip in self.exempt_ips:
            return request
        
        # Check rate limit
        key = self.key_func(request)
        allowed, metadata = await self.limiter.check_limit(
            request,
            key=key,
        )
        
        if not allowed:
            # Rate limited
            return {
                "status": 429,
                "error": "Rate limit exceeded",
                "headers": {
                    "X-RateLimit-Limit": str(metadata.get("limit", 0)),
                    "X-RateLimit-Remaining": str(metadata.get("remaining", 0)),
                    "X-RateLimit-Reset": str(int(metadata.get("reset_at", 0))),
                    "Retry-After": str(metadata.get("retry_after", 60)),
                }
            }
        
        # Add rate limit headers
        request["rate_limit"] = {
            "limit": metadata.get("limit"),
            "remaining": metadata.get("remaining"),
            "reset_at": metadata.get("reset_at"),
        }
        
        return request


# =============================================================================
# Factory Functions
# =============================================================================

def create_rate_limiter(
    max_requests: int = 1000,
    window_seconds: int = 60,
    algorithm: RateLimitAlgorithm = RateLimitAlgorithm.SLIDING_WINDOW,
) -> RateLimiterBackend:
    """Create a rate limiter with the specified configuration."""
    if algorithm == RateLimitAlgorithm.TOKEN_BUCKET:
        return TokenBucketRateLimiter(rate=max_requests/window_seconds, burst=max_requests)
    elif algorithm == RateLimitAlgorithm.SLIDING_WINDOW:
        return SlidingWindowRateLimiter(
            default_limit=max_requests,
            default_window_seconds=window_seconds,
        )
    else:
        return InMemoryRateLimiter()


def create_sliding_window_rate_limiter(
    default_limit: int = 1000,
    default_window_seconds: int = 60,
    key_func: Optional[Callable[[Dict], str]] = None,
) -> SlidingWindowRateLimiter:
    """Create a sliding window rate limiter."""
    return SlidingWindowRateLimiter(default_limit, default_window_seconds, key_func)


def create_token_bucket_rate_limiter(
    rate: float = 100,
    burst: int = 100,
) -> TokenBucketRateLimiter:
    """Create a token bucket rate limiter."""
    return TokenBucketRateLimiter(rate, burst)


def create_adaptive_rate_limiter(
    min_limit: int = 10,
    max_limit: int = 10000,
    target_error_rate: float = 0.01,
    adjustment_factor: float = 1.5,
) -> AdaptiveRateLimiter:
    """Create an adaptive rate limiter."""
    return AdaptiveRateLimiter(min_limit, max_limit, target_error_rate, adjustment_factor)


def create_rate_limit_middleware(
    limiter,
    key_func: Optional[Callable] = None,
    exempt_routes: Optional[List[str]] = None,
    exempt_ips: Optional[Set[str]] = None,
) -> RateLimitMiddleware:
    """Create rate limit middleware."""
    return RateLimitMiddleware(limiter, key_func, exempt_routes, exempt_ips)

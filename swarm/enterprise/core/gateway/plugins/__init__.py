"""
Gateway Plugins - Extensible plugin system for API Gateway.
"""

from .auth import AuthPlugin, JWTAuthPlugin, APIKeyAuthPlugin, OAuth2AuthPlugin
from .rate_limit import (
    SlidingWindowRateLimiter,
    TokenBucketRateLimiter,
    AdaptiveRateLimiter,
    RateLimitMiddleware,
    create_rate_limit_middleware,
    create_sliding_window_rate_limiter,
    create_token_bucket_rate_limiter,
    create_adaptive_rate_limiter,
)
from .transform import RequestTransformPlugin, ResponseTransformPlugin
from .logging import RequestLoggingPlugin, AccessLogPlugin
from .circuit_breaker import CircuitBreakerPlugin
from .load_balancer import (
    LoadBalancingStrategy,
    RoundRobinBalancer,
    WeightedRoundRobinBalancer,
    LeastConnectionsBalancer,
    LeastResponseTimeBalancer,
    ConsistentHashBalancer,
    LeastLoadedBalancer,
    AdaptiveBalancer,
    create_load_balancer,
)
from .cache import (
    CacheBackend,
    MemoryCacheBackend,
    RedisCacheBackend,
    CacheConfig,
    CacheManager,
    CacheMiddleware,
    CacheInvalidator,
)

__all__ = [
    "AuthPlugin",
    "JWTAuthPlugin", 
    "APIKeyAuthPlugin",
    "OAuth2AuthPlugin",
    "SlidingWindowRateLimiter",
    "TokenBucketRateLimiter",
    "AdaptiveRateLimiter",
    "RateLimitMiddleware",
    "create_rate_limit_middleware",
    "create_sliding_window_rate_limiter",
    "create_token_bucket_rate_limiter",
    "create_adaptive_rate_limiter",
    "RequestTransformPlugin",
    "ResponseTransformPlugin",
    "RequestLoggingPlugin",
    "AccessLogPlugin",
    "CircuitBreakerPlugin",
    "LoadBalancingStrategy",
    "RoundRobinBalancer",
    "WeightedRoundRobinBalancer",
    "LeastConnectionsBalancer",
    "LeastResponseTimeBalancer",
    "ConsistentHashBalancer",
    "LeastLoadedBalancer",
    "AdaptiveBalancer",
    "create_load_balancer",
    "CacheBackend",
    "MemoryCacheBackend",
    "RedisCacheBackend",
    "CacheConfig",
    "CacheManager",
    "CacheMiddleware",
    "CacheInvalidator",
]

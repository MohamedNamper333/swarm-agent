"""
Cache Plugins for API Gateway.
Provides response caching with multiple backend support.
"""

import asyncio
import hashlib
import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
import redis
from collections import OrderedDict

logger = logging.getLogger(__name__)


# =============================================================================
# Cache Models
# =============================================================================

@dataclass
class CacheConfig:
    """Cache configuration."""
    enabled: bool = True
    default_ttl_seconds: int = 300  # 5 minutes
    max_size_mb: int = 100
    max_entries: int = 10000
    key_prefix: str = "gateway:cache:"
    compress: bool = False
    compression_threshold: int = 1024  # bytes


@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    key: str
    value: bytes
    headers: Dict[str, str] = field(default_factory=dict)
    status_code: int = 200
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    access_count: int = 0
    last_accessed: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    vary_headers: List[str] = field(default_factory=list)
    etag: Optional[str] = None
    compressed: bool = False
    original_size: int = 0
    compressed_size: int = 0


@dataclass
class CacheStats:
    """Cache statistics."""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    size_bytes: int = 0
    entry_count: int = 0
    hit_rate: float = 0.0


# =============================================================================
# Cache Backends
# =============================================================================

class CacheBackend(ABC):
    """Abstract cache backend."""

    @abstractmethod
    async def get(self, key: str) -> Optional[bytes]:
        pass

    @abstractmethod
    async def set(
        self,
        key: str,
        value: bytes,
        ttl_seconds: int,
        metadata: Optional[Dict] = None,
    ) -> bool:
        pass

    @staticmethod
    def _entry_size(key: str, value: bytes) -> int:
        """Consistent accounting helper shared by backends."""
        return len(key.encode()) + len(value) + 64


class MemoryCacheBackend(CacheBackend):
    """In-memory cache backend with LRU eviction."""

    def __init__(self, max_size_mb: int = 100, max_entries: int = 10000):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._access_order: "OrderedDict" = OrderedDict()
        self._max_size_bytes = max_size_mb * 1024 * 1024
        self._max_entries = max_entries
        self._current_size_bytes = 0
        self._lock = asyncio.Lock()
        self._stats = {"hits": 0, "misses": 0, "evictions": 0}

    async def get(self, key: str) -> Optional[bytes]:
        async with self._lock:
            if key not in self._cache:
                self._stats["misses"] += 1
                return None

            entry = self._cache[key]
            if entry["expires_at"] and datetime.now(timezone.utc) > entry["expires_at"]:
                del self._cache[key]
                self._access_order.pop(key, None)
                self._current_size_bytes -= entry.get("size", 0)
                self._stats["misses"] += 1
                return None

            # Move to end (LRU)
            self._access_order.move_to_end(key)
            self._stats["hits"] += 1
            return entry["value"]

    async def set(
        self,
        key: str,
        value: bytes,
        ttl_seconds: int,
        metadata: Optional[Dict] = None,
    ) -> bool:
        async with self._lock:
            new_size = self._entry_size(key, value)
            if new_size > self._max_size_bytes:
                return False

            # Drop stale entry if overwriting (its old size must be removed)
            old = self._cache.get(key)
            if old is not None:
                self._current_size_bytes -= old.get(
                    "size", self._entry_size(key, old.get("value", b"")))
                self._access_order.pop(key, None)

            await self._ensure_space(new_size)

            expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
            self._cache[key] = {
                "value": value,
                "expires_at": expires_at,
                "size": new_size,
            }
            self._access_order[key] = True
            self._access_order.move_to_end(key)
            self._current_size_bytes += new_size
            return True

    async def _ensure_space(self, needed_bytes: int) -> None:
        """LRU eviction until the new entry fits BOTH byte and count caps.

        Fixed three defects: eviction never subtracted the evicted entry's
        size from _current_size_bytes (accounting drifted up forever), the
        per-entry "size" field measured 3x-key-length instead of the payload
        (so _max_size_mb gated nothing), and expired entries deleted in get()
        leaked both size and access_order slots.
        """
        while (
            self._current_size_bytes + needed_bytes > self._max_size_bytes
            or len(self._cache) >= self._max_entries
        ):
            if not self._access_order:
                break
            oldest_key = next(iter(self._access_order))
            entry = self._cache.pop(oldest_key, None)
            self._access_order.pop(oldest_key, None)
            if entry is not None:
                self._current_size_bytes -= entry.get(
                    "size", self._entry_size(oldest_key, entry.get("value", b"")))
            self._stats["evictions"] += 1

    async def delete(self, key: str) -> bool:
        async with self._lock:
            if key in self._cache:
                entry = self._cache.pop(key)
                self._access_order.pop(key, None)
                self._current_size_bytes -= entry.get(
                    "size", self._entry_size(key, entry.get("value", b"")))
                return True
            return False
    
    async def exists(self, key: str) -> bool:
        async with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                if entry["expires_at"] and datetime.now(timezone.utc) > entry["expires_at"]:
                    del self._cache[key]
                    self._access_order.pop(key, None)
                    self._current_size_bytes -= entry.get("size", 0)
                    return False
                return True
            return False
    
    async def clear(self) -> int:
        async with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self._access_order.clear()
            self._current_size_bytes = 0
            return count
    
    async def get_stats(self) -> Dict[str, Any]:
        return {
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "evictions": self._stats["evictions"],
            "size_bytes": self._current_size_bytes,
            "entry_count": len(self._cache),
            "hit_rate": self._stats["hits"] / max(self._stats["hits"] + self._stats["misses"], 1),
        }


class RedisCacheBackend:
    """Redis cache backend for distributed caching."""
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        key_prefix: str = "gateway:cache:",
        default_ttl: int = 300,
        max_connections: int = 50,
    ):
        self.redis_url = redis_url
        self.key_prefix = key_prefix
        self.default_ttl = default_ttl
        self._client: Optional[redis.asyncio.Redis] = None
        self._pool: Optional[redis.ConnectionPool] = None
        self._max_connections = max_connections
    
    async def _get_client(self) -> redis.asyncio.Redis:
        if self._client is None:
            self._pool = redis.ConnectionPool.from_url(
                self.redis_url,
                max_connections=self.max_connections,
                decode_responses=False,
            )
            self._client = redis.Redis(connection_pool=self._pool)
        return self._client
    
    def _key(self, key: str) -> str:
        return f"{self.key_prefix}{key}"
    
    async def get(self, key: str) -> Optional[bytes]:
        try:
            client = await self._get_client()
            data = await self._client.get(self._key(key))
            return data
        except Exception as e:
            logger.error(f"Redis get failed: {e}")
            return None
    
    async def set(
        self,
        key: str,
        value: bytes,
        ttl_seconds: int,
        metadata: Optional[Dict] = None,
    ) -> bool:
        try:
            client = await self._get_client()
            key = self._key(key)
            pipe = self._client.pipeline()
            pipe.set(key, value, ex=ttl_seconds)
            await pipe.execute()
            return True
        except Exception as e:
            logger.error(f"Redis set failed: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        try:
            client = await self._get_client()
            result = await self._client.delete(self._key(key))
            return result > 0
        except Exception as e:
            logger.error(f"Redis delete failed: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        try:
            client = await self._get_client()
            return await self._client.exists(self._key(key)) > 0
        except Exception:
            return False
    
    async def clear(self) -> int:
        try:
            client = await self._get_client()
            keys = await client.keys(f"{self.key_prefix}*")
            if keys:
                return await client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Redis clear failed: {e}")
            return 0
    
    async def get_stats(self) -> Dict[str, Any]:
        try:
            client = await self._get_client()
            info = await client.info("memory")
            return {
                "used_memory": info.get("used_memory", 0),
                "used_memory_human": info.get("used_memory_human", "0B"),
                "connected_clients": info.get("connected_clients", 0),
            }
        except Exception:
            return {}


# =============================================================================
# Cache Manager
# =============================================================================

@dataclass
class CacheRule:
    """Cache rule for matching requests."""
    path_patterns: List[str] = field(default_factory=list)
    methods: List[str] = field(default_factory=lambda: ["GET", "HEAD"])
    status_codes: List[int] = field(default_factory=lambda: [200])
    ttl_seconds: int = 300
    vary_headers: List[str] = field(default_factory=list)
    exclude_query_params: List[str] = field(default_factory=lambda: ["utm_*", "fbclid", "gclid"])
    cache_control: bool = True  # Respect Cache-Control headers
    private: bool = False  # Don't cache in shared caches


@dataclass




class CacheManager:
    """High-level cache manager for gateway responses."""
    
    def __init__(
        self,
        backend: CacheBackend,
        config: Optional[CacheConfig] = None,
        rules: Optional[List[CacheRule]] = None,
    ):
        self.backend = backend
        self.config = config or CacheConfig()
        self.rules = rules or []
        self._lock = asyncio.Lock()
        self._stats = {
            "hits": 0,
            "misses": 0,
            "errors": 0,
        }
    
    def add_rule(self, rule: CacheRule) -> None:
        """Add a cache rule."""
        self.rules.append(rule)
        # Sort by specificity (more specific paths first)
        self.rules.sort(key=lambda r: -len(r.path_patterns[0]) if r.path_patterns else 0)
    
    def _match_rule(self, request: Dict[str, Any]) -> Optional[CacheRule]:
        """Find matching cache rule for request."""
        method = request.get("method", "").upper()
        path = request.get("path", "")
        
        for rule in self.rules:
            if rule.methods and request.get("method", "").upper() not in rule.methods:
                continue
            
            # Check path patterns
            for pattern in rule.path_patterns:
                import fnmatch
                if fnmatch.fnmatch(path, pattern):
                    return rule
        
        return None
    
    def _generate_cache_key(
        self,
        request: Dict[str, Any],
        rule: CacheRule,
    ) -> str:
        """Generate cache key from request."""
        parts = []
        
        # Method
        parts = [request.get("method", "GET").upper()]
        
        # Path
        parts.append(request.get("path", "/"))
        
        # Query parameters (excluding excluded)
        query_params = request.get("query_params", {})
        filtered_params = {
            k: v for k, v in request.get("query_params", {}).items()
            if not any(fnmatch.fnmatch(k, pattern) for pattern in rule.exclude_query_params)
        }
        if filtered_params:
            # Sort for consistent key
            sorted_params = "&".join(f"{k}={v}" for k, v in sorted(filtered_params.items()))
            parts.append(sorted_params)
        
        # Vary headers
        for header in rule.vary_headers:
            value = request.get("headers", {}).get(header.lower(), "")
            if value:
                parts.append(f"{header}:{value}")
        
        # Tenant isolation
        if request.get("tenant_id"):
            parts.append(f"tenant:{request['tenant_id']}")
        
        key_string = "|".join(parts)
        return hashlib.sha256(key_string.encode()).hexdigest()
    
    async def get(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get cached response for request."""
        rule = self._match_rule(request)
        if not rule:
            return None
        
        key = self._generate_cache_key(request, rule)
        full_key = f"{self.config.key_prefix}{key}"
        
        data = await self.backend.get(full_key)
        if not data:
            self._stats["misses"] += 1
            return None
        
        try:
            entry = json.loads(data.decode())
            # Check expiration
            if entry.get("expires_at"):
                expires_at = datetime.fromisoformat(entry["expires_at"])
                if datetime.now(timezone.utc) > expires_at:
                    await self.backend.delete(key)
                    self._stats["misses"] += 1
                    return None
            
            # Update access stats
            self._stats["hits"] += 1
            return entry
        except Exception as e:
            logger.error(f"Cache get failed: {e}")
            self._stats["misses"] += 1
            return None
    
    async def set(
        self,
        request: Dict[str, Any],
        response: Dict[str, Any],
        rule: Optional[CacheRule] = None,
    ) -> bool:
        """Store response in cache."""
        rule = rule or self._match_rule(request)
        if not rule:
            return False
        
        # Check if response is cacheable
        status_code = response.get("status_code", 200)
        if rule.status_codes and response.get("status_code") not in rule.status_codes:
            return False
        
        # Check Cache-Control
        if rule.cache_control:
            cache_control = response.get("headers", {}).get("Cache-Control", "")
            if "no-store" in cache_control or "private" in cache_control:
                return False
        
        # Generate cache key
        rule = rule or self._match_rule(request)
        if not rule:
            return False
        
        key = self._generate_cache_key(request, rule)
        full_key = f"{self.config.key_prefix}{key}"
        
        # Prepare cache entry
        entry = {
            "value": response.get("body", b""),
            "headers": response.get("headers", {}),
            "status_code": response.get("status_code", 200),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": (datetime.now(timezone.utc) + timedelta(seconds=rule.ttl_seconds)).isoformat(),
            "vary_headers": rule.vary_headers,
            "etag": response.get("headers", {}).get("ETag"),
        }
        
        # Serialize
        data = json.dumps(entry).encode()
        
        # Store in backend
        ttl = rule.ttl_seconds
        success = await self.backend.set(key, data, ttl)
        
        if success:
            self._stats["hits"] += 1
        else:
            self._stats["errors"] += 1
        
        return success
    
    async def get(self, request: Dict[str, Any]) -> Optional[Dict]:
        """Get cached response for request."""
        rule = self._match_rule(request)
        if not rule:
            return None
        
        key = self._generate_cache_key(request, rule)
        full_key = f"{self.config.key_prefix}{key}"
        
        data = await self.backend.get(full_key)
        if not data:
            self._stats["misses"] += 1
            return None
        
        try:
            entry = json.loads(data.decode())
            # Check expiration
            if entry.get("expires_at"):
                expires_at = datetime.fromisoformat(entry["expires_at"])
                if datetime.now(timezone.utc) > expires_at:
                    await self.backend.delete(key)
                    self._stats["misses"] += 1
                    return None
            
            self._stats["hits"] += 1
            return entry
        except Exception as e:
            logger.error(f"Cache get failed: {e}")
            self._stats["misses"] += 1
            return None
    
    async def invalidate(self, pattern: str) -> int:
        """Invalidate cache entries matching pattern."""
        # In production, would use SCAN for Redis
        count = 0
        # Simplified - in production use SCAN
        return count
    
    async def clear(self) -> int:
        """Clear all cache entries."""
        count = await self.backend.clear()
        self._stats = {"hits": 0, "misses": 0, "errors": 0}
        return count
    
    def get_stats(self) -> Dict[str, Any]:
        stats = self._stats.copy()
        total = stats["hits"] + stats["misses"]
        stats["hit_rate"] = stats["hits"] / max(total, 1)
        return stats
    

# =============================================================================
# Response Caching Middleware
# =============================================================================

class CacheMiddleware:
    """Middleware for automatic response caching."""
    
    def __init__(
        self,
        cache_manager: CacheManager,
        default_rules: Optional[List[CacheRule]] = None,
    ):
        self.cache_manager = cache_manager
        self.default_rules = default_rules or []
    
    async def __call__(
        self,
        request: Dict[str, Any],
        next_handler: Callable,
    ) -> Dict[str, Any]:
        # Check if request is cacheable
        rule = self.cache_manager._match_rule(request)
        if not rule:
            return await self._call_next(request)
        
        # Try to get from cache
        cached = await self.cache_manager.get(request)
        if cached:
            # Return cached response
            return {
                "status_code": cached.get("status_code", 200),
                "headers": cached.get("headers", {}),
                "body": cached.get("value", b""),
                "headers": {**cached.get("headers", {}), "X-Cache": "HIT"},
            }
        
        # Execute request
        response = await self._call_next(request)
        
        # Store in cache if successful
        if 200 <= response.get("status_code", 500) < 300:
            await self.cache_manager.set(request, response)
        
        response["headers"]["X-Cache"] = "MISS"
        return response
    
    async def _call_next(self, request: Dict[str, Any]) -> Dict:
        # Placeholder - in real implementation, this would call the next handler
        return {"status_code": 404, "body": b"Not Found", "headers": {}}


# =============================================================================
# Cache Invalidation Strategies
# =============================================================================

class CacheInvalidator:
    """Handles cache invalidation strategies."""
    
    def __init__(self, cache_manager: CacheManager):
        self.cache_manager = cache_manager
    
    async def invalidate_by_pattern(self, pattern: str) -> int:
        """Invalidate cache entries matching pattern."""
        # In production, would use SCAN for Redis
        # For memory backend, iterate keys
        return 0
    
    async def invalidate_by_tags(self, tags: List[str]) -> int:
        """Invalidate entries by tags."""
        return 0
    
    async def invalidate_by_dependency(self, dependency_key: str) -> int:
        """Invalidate entries that depend on a key."""
        return 0
    
    async def purge_all(self) -> int:
        """Purge all cache entries."""
        return await self.cache_manager.clear()


# =============================================================================
# Factory Functions
# =============================================================================

def create_cache_manager(
    backend: Optional[CacheBackend] = None,
    config: Optional[CacheConfig] = None,
    rules: Optional[List[CacheRule]] = None,
) -> CacheManager:
    """Create a cache manager."""
    if backend is None:
        backend = MemoryCacheBackend()
    return CacheManager(backend, config, rules)


def create_memory_cache_backend(
    max_size_mb: int = 100,
    max_entries: int = 10000,
) -> MemoryCacheBackend:
    """Create in-memory cache backend."""
    return MemoryCacheBackend(max_size_mb, max_entries)


def create_redis_cache_backend(
    redis_url: str = "redis://localhost:6379/0",
    key_prefix: str = "gateway:cache:",
    default_ttl: int = 300,
) -> RedisCacheBackend:
    """Create Redis cache backend."""
    return RedisCacheBackend(redis_url, key_prefix, default_ttl)


def create_cache_middleware(
    cache_manager: CacheManager,
    default_rules: Optional[List[CacheRule]] = None,
) -> CacheMiddleware:
    return CacheMiddleware(cache_manager, default_rules)


# =============================================================================
# HTTP Caching Utilities
# =============================================================================

def generate_etag(content: bytes) -> str:
    """Generate ETag for content."""
    return f'"{hashlib.sha256(content).hexdigest()[:16]}"'


def is_cacheable(request: Dict, response: Dict) -> bool:
    """Determine if response is cacheable."""
    # Check method
    if request.get("method", "").upper() not in ("GET", "HEAD"):
        return False
    
    # Check status code
    status = response.get("status_code", 200)
    if status not in (200, 203, 204, 206, 300, 301, 404, 405, 410, 414, 501):
        return False
    
    # Check Cache-Control
    cache_control = response.get("headers", {}).get("Cache-Control", "")
    if "no-store" in cache_control:
        return False
    
    return True


def parse_cache_control(header: str) -> Dict[str, Any]:
    """Parse Cache-Control header."""
    directives = {}
    for part in header.split(","):
        part = part.strip()
        if "=" in part:
            k, v = part.split("=", 1)
            directives[k.strip()] = v.strip()
        else:
            directives[part] = True
    return directives


def should_cache_response(request: Dict, response: Dict) -> bool:
    """Determine if response should be cached."""
    return is_cacheable(request, response)

"""
Cache Manager — pluggable backend (in-memory default, Redis optional).

When Redis is reachable on REDIS_URL (default redis://localhost:27123/0),
the Redis backend is used. Otherwise, falls back to an in-memory LRU+TTL cache.

Both backends expose the same API:
  get(key) -> Optional[Any]
  set(key, value, ttl_sec)
  delete(key)
  clear()
  stats() -> Dict[str, Any]

Keys are namespaced as: swarm:cache:{agent_id}:{hash(query)}
"""
import hashlib
import json
import logging
import os
import time
import threading
from collections import OrderedDict
from typing import Any, Dict, Optional, Protocol

logger = logging.getLogger(__name__)


def hash_query(query: Any) -> str:
    """Stable hash for cache key derivation."""
    if isinstance(query, str):
        payload = query
    else:
        payload = json.dumps(query, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def make_key(agent_id: str, query: Any) -> str:
    """Namespaced cache key: swarm:cache:{agent_id}:{hash}."""
    return f"swarm:cache:{agent_id}:{hash_query(query)}"


class CacheBackend(Protocol):
    def get(self, key: str) -> Optional[Any]: ...
    def set(self, key: str, value: Any, ttl_sec: int) -> bool: ...
    def delete(self, key: str) -> bool: ...
    def clear(self) -> bool: ...
    def stats(self) -> Dict[str, Any]: ...


class InMemoryCache:
    """LRU + TTL cache, thread-safe. Default backend."""

    def __init__(self, max_size: int = 10000):
        self._data: OrderedDict[str, tuple] = OrderedDict()
        self._max_size = max_size
        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self._data.get(key)
            if entry is None:
                self._misses += 1
                return None
            value, expires_at = entry
            if expires_at and time.time() > expires_at:
                del self._data[key]
                self._misses += 1
                return None
            # LRU: move to end
            self._data.move_to_end(key)
            self._hits += 1
            return value

    def set(self, key: str, value: Any, ttl_sec: int) -> bool:
        with self._lock:
            expires_at = (time.time() + ttl_sec) if ttl_sec > 0 else 0
            self._data[key] = (value, expires_at)
            self._data.move_to_end(key)
            # Evict LRU
            while len(self._data) > self._max_size:
                self._data.popitem(last=False)
            return True

    def delete(self, key: str) -> bool:
        with self._lock:
            return self._data.pop(key, None) is not None

    def clear(self) -> bool:
        with self._lock:
            self._data.clear()
            return True

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            total = self._hits + self._misses
            return {
                "backend": "in_memory",
                "size": len(self._data),
                "max_size": self._max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": (self._hits / total) if total > 0 else 0.0,
            }


class RedisCache:
    """Redis backend. Imported lazily so missing redis doesn't break startup."""

    def __init__(self, url: str, namespace: str = "swarm:cache"):
        import redis  # lazy
        self._client = redis.Redis.from_url(url, decode_responses=True)
        self._ns = namespace
        try:
            self._client.ping()
            logger.info("Redis cache connected: %s", url)
        except Exception as e:
            logger.warning("Redis ping failed (%s); cache will be a no-op", e)
            self._client = None

    def get(self, key: str) -> Optional[Any]:
        if not self._client:
            return None
        try:
            raw = self._client.get(f"{self._ns}:{key}")
            return json.loads(raw) if raw else None
        except Exception as e:
            logger.warning("Redis GET error: %s", e)
            return None

    def set(self, key: str, value: Any, ttl_sec: int) -> bool:
        if not self._client:
            return False
        try:
            payload = json.dumps(value, default=str)
            return bool(self._client.setex(f"{self._ns}:{key}", ttl_sec, payload))
        except Exception as e:
            logger.warning("Redis SET error: %s", e)
            return False

    def delete(self, key: str) -> bool:
        if not self._client:
            return False
        try:
            return bool(self._client.delete(f"{self._ns}:{key}"))
        except Exception as e:
            logger.warning("Redis DEL error: %s", e)
            return False

    def clear(self) -> bool:
        if not self._client:
            return False
        try:
            cursor = 0
            pattern = f"{self._ns}:*"
            while True:
                cursor, keys = self._client.scan(cursor, match=pattern, count=500)
                if keys:
                    self._client.delete(*keys)
                if cursor == 0:
                    break
            return True
        except Exception as e:
            logger.warning("Redis CLEAR error: %s", e)
            return False

    def stats(self) -> Dict[str, Any]:
        if not self._client:
            return {"backend": "redis", "connected": False}
        try:
            info = self._client.info("stats")
            return {
                "backend": "redis",
                "connected": True,
                "hits": int(info.get("keyspace_hits", 0)),
                "misses": int(info.get("keyspace_misses", 0)),
            }
        except Exception as e:
            return {"backend": "redis", "connected": False, "error": str(e)}


class CacheManager:
    """Pluggable cache: tries Redis first, falls back to in-memory."""

    def __init__(self, redis_url: Optional[str] = None):
        if redis_url is None:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:27123/0")
        # Try Redis (lazy/optional)
        backend: CacheBackend = InMemoryCache()
        if redis_url:
            try:
                rc = RedisCache(redis_url)
                if rc._client is not None:
                    backend = rc  # type: ignore[assignment]
                    logger.info("CacheManager using Redis backend")
            except Exception as e:
                logger.info("Redis unavailable (%s); using in-memory cache", e)
        self._backend = backend
        self._agent_hits: Dict[str, int] = {}
        self._agent_misses: Dict[str, int] = {}

    @property
    def backend_name(self) -> str:
        return "redis" if isinstance(self._backend, RedisCache) and self._backend._client else "in_memory"

    def get(self, agent_id: str, query: Any) -> Optional[Any]:
        key = make_key(agent_id, query)
        value = self._backend.get(key)
        if value is not None:
            self._agent_hits[agent_id] = self._agent_hits.get(agent_id, 0) + 1
        else:
            self._agent_misses[agent_id] = self._agent_misses.get(agent_id, 0) + 1
        return value

    def set(self, agent_id: str, query: Any, value: Any, ttl_sec: int = 3600) -> bool:
        key = make_key(agent_id, query)
        return self._backend.set(key, value, ttl_sec)

    def delete(self, agent_id: str, query: Any) -> bool:
        key = make_key(agent_id, query)
        return self._backend.delete(key)

    def clear(self) -> bool:
        return self._backend.clear()

    def stats(self) -> Dict[str, Any]:
        backend_stats = self._backend.stats()
        total_hits = sum(self._agent_hits.values())
        total_misses = sum(self._agent_misses.values())
        total = total_hits + total_misses
        backend_stats.update({
            "agent_hits": dict(self._agent_hits),
            "agent_misses": dict(self._agent_misses),
            "total_hits": total_hits,
            "total_misses": total_misses,
            "global_hit_rate": (total_hits / total) if total > 0 else 0.0,
        })
        return backend_stats


# Module-level singleton
_default_cache: Optional[CacheManager] = None
_cache_lock = threading.Lock()


def get_default_cache() -> CacheManager:
    global _default_cache
    with _cache_lock:
        if _default_cache is None:
            _default_cache = CacheManager()
        return _default_cache


if __name__ == "__main__":
    cm = CacheManager()
    print(f"Backend: {cm.backend_name}")
    cm.set("chairman", "test_query", {"answer": 42}, ttl_sec=60)
    v = cm.get("chairman", "test_query")
    print(f"Round-trip: {v}")
    print(f"Miss: {cm.get('chairman', 'unknown')}")
    print(f"Stats: {cm.stats()}")

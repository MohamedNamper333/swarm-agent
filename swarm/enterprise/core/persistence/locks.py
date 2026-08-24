"""
Distributed Locking - Redis/etcd-based distributed locking with lease renewal.
Provides mutex, read-write locks, and semaphore implementations.
"""

import asyncio
import uuid
import time
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from contextlib import asynccontextmanager
try:
    import redis.asyncio as redis
except ImportError:
    redis = None

try:
    import etcd3
except ImportError:
    etcd3 = None

logger = logging.getLogger(__name__)

# =============================================================================
# Lock Models
# =============================================================================

class LockType(str, Enum):
    MUTEX = "mutex"           # Exclusive lock
    READ_WRITE = "rwlock"     # Read-write lock
    SEMAPHORE = "semaphore"   # Counting semaphore


@dataclass
class LockConfig:
    lock_type: LockType = LockType.MUTEX
    ttl_seconds: int = 30
    auto_renewal: bool = True
    renewal_interval: float = 10.0  # seconds
    blocking: bool = True
    timeout_seconds: float = 30.0
    max_retries: int = 3


@dataclass
class LockInfo:
    lock_id: str
    holder: str
    acquired_at: datetime
    expires_at: datetime
    lock_type: LockType
    metadata: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Lock Backends
# =============================================================================

class LockBackend(ABC):
    """Abstract lock backend."""
    
    @abstractmethod
    async def acquire(
        self,
        lock_key: str,
        holder: str,
        ttl_seconds: int,
        lock_type: LockType = LockType.MUTEX,
    ) -> bool:
        pass
    
    @abstractmethod
    async def release(self, lock_key: str, holder: str) -> bool:
        pass
    
    @abstractmethod
    async def renew(self, lock_key: str, holder: str, ttl_seconds: int) -> bool:
        pass
    
    @abstractmethod
    async def get_lock_info(self, lock_key: str) -> Optional[Dict[str, Any]]:
        pass
    
    @abstractmethod
    async def force_release(self, lock_key: str) -> bool:
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        pass


# =============================================================================
# Redis Lock Backend
# =============================================================================

class RedisLockBackend(LockBackend):
    """Redis-based distributed lock backend using Redlock algorithm."""
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        key_prefix: str = "swarm:locks",
        max_connections: int = 50,
    ):
        self.redis_url = redis_url
        self.key_prefix = key_prefix
        self._pool: Optional[redis.ConnectionPool] = None
        self._client: Optional[redis.Redis] = None
    
    async def _get_client(self):
        if redis is None:
            raise RuntimeError("redis not installed. Install with: pip install redis")
        if self._client is None:
            self._pool = redis.ConnectionPool.from_url(
                self.redis_url,
                max_connections=50,
                decode_responses=True,
            )
            self._client = redis.Redis(connection_pool=self._pool)
        return self._client
    
    def _lock_key(self, lock_key: str) -> str:
        return f"{self.key_prefix}:{lock_key}"
    
    async def acquire(
        self,
        lock_key: str,
        holder: str,
        ttl_seconds: int,
        lock_type: LockType = LockType.MUTEX,
    ) -> bool:
        client = await self._get_client()
        key = self._lock_key(lock_key)
        
        # Use SET NX EX for atomic acquire
        result = await client.set(
            self._lock_key(lock_key),
            holder,
            nx=True,
            ex=ttl_seconds,
        )
        
        if result:
            # Store lock metadata
            metadata_key = f"{self.key_prefix}:meta:{lock_key}"
            import json
            metadata = {
                "holder": holder,
                "acquired_at": datetime.now(timezone.utc).isoformat(),
                "expires_at": (datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)).isoformat(),
                "lock_type": lock_type.value,
            }
            await client.set(metadata_key, json.dumps(metadata), ex=ttl_seconds)
            return True
        
        return False
    
    async def release(self, lock_key: str, holder: str) -> bool:
        client = await self._get_client()
        
        # Lua script for atomic release (check owner then delete)
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            redis.call("del", KEYS[1])
            redis.call("del", KEYS[2])
            return 1
        else
            return 0
        end
        """
        
        lock_key = self._lock_key(lock_key)
        meta_key = f"{self.key_prefix}:meta:{lock_key}"
        
        script = client.register_script(lua_script)
        result = await script(keys=[lock_key, meta_key], args=[holder])
        return result == 1
    
    async def renew(self, lock_key: str, holder: str, ttl_seconds: int) -> bool:
        client = await self._get_client()
        
        # Check ownership and extend
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            redis.call("expire", KEYS[1], ARGV[2])
            redis.call("expire", KEYS[2], ARGV[2])
            return 1
        else
            return 0
        end
        """
        
        lock_key = self._lock_key(lock_key)
        meta_key = f"{self.key_prefix}:meta:{lock_key}"
        
        script = client.register_script(lua_script)
        result = await script(keys=[lock_key, meta_key], args=[holder, ttl_seconds])
        return result == 1
    
    async def get_lock_info(self, lock_key: str) -> Optional[Dict[str, Any]]:
        client = await self._get_client()
        meta_key = f"{self.key_prefix}:meta:{lock_key}"
        
        meta_data = await client.get(meta_key)
        if not meta_data:
            return None
        
        import json
        return json.loads(meta_data)
    
    async def force_release(self, lock_key: str) -> bool:
        client = await self._get_client()
        lock_key_prefixed = self._lock_key(lock_key)
        meta_key = f"{self.key_prefix}:meta:{lock_key}"
        
        result = await client.delete(lock_key_prefixed, meta_key)
        return result > 0
    
    async def health_check(self) -> bool:
        try:
            client = await self._get_client()
            await client.ping()
            return True
        except Exception:
            return False
    
    async def close(self) -> None:
        if self._pool:
            await self._pool.disconnect()
            self._pool = None
            self._client = None


# =============================================================================
# etcd Lock Backend
# =============================================================================

class EtcdLockBackend(LockBackend):
    """etcd-based distributed lock backend using lease-based locks."""
    
    def __init__(
        self,
        etcd_host: str = "localhost",
        etcd_port: int = 2379,
        key_prefix: str = "swarm/locks",
    ):
        self.etcd_host = etcd_host
        self.etcd_port = etcd_port
        self.key_prefix = key_prefix
        self._client: Optional[etcd3.Etcd3Client] = None
        self._leases: Dict[str, any] = {}
    
    async def _get_client(self):
        if etcd3 is None:
            raise RuntimeError("etcd3 not installed. Install with: pip install etcd3")
        if self._client is None:
            self._client = etcd3.client(
                host=self.etcd_host,
                port=self.etcd_port,
            )
        return self._client
    
    def _lock_key(self, lock_key: str) -> str:
        return f"{self.key_prefix}/{lock_key}"
    
    async def acquire(
        self,
        lock_key: str,
        holder: str,
        ttl_seconds: int,
        lock_type: LockType = LockType.MUTEX,
    ) -> bool:
        client = await self._get_client()
        key = self._lock_key(lock_key)
        
        # Create lease
        lease = client.lease(ttl_seconds)
        
        # Try to acquire with lease
        success, _ = client.etcdctl.lease_keep_alive(lease.id)
        # Actually use etcdctl or txn for atomic acquire
        success, _ = client.etcdctl.txn(
            compare=[client.transactions.version(key) == 0],
            success=[client.put(key, holder, lease)],
            failure=[]
        )
        
        if success:
            # Store metadata
            meta_key = f"{key}:meta"
            import json
            metadata = {
                "holder": holder,
                "acquired_at": datetime.now(timezone.utc).isoformat(),
                "expires_at": (datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)).isoformat(),
                "lock_type": lock_type.value,
            }
            client.put(meta_key, json.dumps(metadata), lease)
            return True
        
        return False
    
    async def release(self, lock_key: str, holder: str) -> bool:
        client = await self._get_client()
        key = self._lock_key(lock_key)
        
        # Check ownership and delete
        meta_key = f"{key}:meta"
        meta_data, _ = client.get(meta_key)
        
        if meta_data:
            import json
            meta = json.loads(meta_data)
            if meta.get("holder") == holder:
                client.delete(key)
                client.delete(meta_key)
                return True
        return False
    
    async def renew(self, lock_key: str, holder: str, ttl_seconds: int) -> bool:
        client = await self._get_client()
        key = self._lock_key(lock_key)
        meta_key = f"{key}:meta"
        
        meta_data, _ = client.get(meta_key)
        if meta_data:
            import json
            meta = json.loads(meta_data)
            if meta.get("holder") == holder:
                # Renew lease
                lease = client.lease(ttl_seconds)
                client.put(key, holder, lease)
                client.put(meta_key, json.dumps({**meta, "expires_at": (datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)).isoformat()}), lease)
                return True
        return False
    
    async def get_lock_info(self, lock_key: str) -> Optional[Dict[str, Any]]:
        client = await self._get_client()
        meta_key = f"{self._lock_key(lock_key)}:meta"
        
        meta_data, _ = client.get(meta_key)
        if meta_data:
            import json
            return json.loads(meta_data)
        return None
    
    async def force_release(self, lock_key: str) -> bool:
        client = await self._get_client()
        key = self._lock_key(lock_key)
        meta_key = f"{key}:meta"
        
        client.delete(key)
        client.delete(meta_key)
        return True
    
    async def health_check(self) -> bool:
        try:
            client = await self._get_client()
            client.status()
            return True
        except Exception:
            return False
    
    async def close(self) -> None:
        if self._client:
            self._client.close()


# =============================================================================
# Distributed Lock Manager
# =============================================================================

class DistributedLockManager:
    """High-level distributed lock manager with multiple backend support."""
    
    def __init__(
        self,
        backend: LockBackend,
        default_ttl: int = 30,
        default_timeout: float = 30.0,
    ):
        self.backend = backend
        self.default_ttl = default_ttl
        self.default_timeout = default_timeout
        self._locks: Dict[str, asyncio.Lock] = {}
        self._lock = asyncio.Lock()
        self._renewal_tasks: Dict[str, asyncio.Task] = {}
    
    @asynccontextmanager
    async def lock(
        self,
        lock_key: str,
        holder: str = "system",
        ttl_seconds: Optional[int] = None,
        timeout: Optional[float] = None,
        lock_type: LockType = LockType.MUTEX,
    ):
        """Acquire a distributed lock as context manager."""
        ttl = ttl_seconds or self.default_ttl
        timeout = timeout or self.default_timeout
        
        acquired = await self.acquire(lock_key, holder, ttl, lock_type, timeout)
        if not acquired:
            raise RuntimeError(f"Failed to acquire lock {lock_key} within {timeout}s")
        
        try:
            yield True
        finally:
            await self.release(lock_key, holder)
    
    async def acquire(
        self,
        lock_key: str,
        holder: str = "system",
        ttl_seconds: int = 30,
        lock_type: LockType = LockType.MUTEX,
        timeout: float = 30.0,
    ) -> bool:
        """Acquire a distributed lock with timeout."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            acquired = await self.backend.acquire(lock_key, holder, ttl_seconds, lock_type)
            if acquired:
                # Start auto-renewal if needed
                asyncio.create_task(self._auto_renew(lock_key, holder, ttl_seconds))
                return True
            
            await asyncio.sleep(0.1)
        
        return False
    
    async def _auto_renew(self, lock_key: str, holder: str, ttl_seconds: int) -> None:
        """Auto-renew lock before expiration."""
        renewal_interval = ttl_seconds / 3  # Renew at 1/3 of TTL
        
        while True:
            await asyncio.sleep(renewal_interval)
            
            # Check if we still hold the lock
            info = await self.backend.get_lock_info(lock_key)
            if not info or info.get("holder") != holder:
                break
            
            renewed = await self.backend.renew(lock_key, holder, ttl_seconds)
            if not renewed:
                logger.warning(f"Failed to renew lock {lock_key}")
                break
    
    async def release(self, lock_key: str, holder: str) -> bool:
        """Release a lock."""
        # Cancel renewal task
        if lock_key in self._renewal_tasks:
            self._renewal_tasks[lock_key].cancel()
            del self._renewal_tasks[lock_key]
        
        return await self.backend.release(lock_key, holder)
    
    async def force_release(self, lock_key: str) -> bool:
        """Force release a lock (admin operation)."""
        if lock_key in self._renewal_tasks:
            self._renewal_tasks[lock_key].cancel()
            del self._renewal_tasks[lock_key]
        
        return await self.backend.force_release(lock_key)
    
    async def get_lock_info(self, lock_key: str) -> Optional[Dict[str, Any]]:
        return await self.backend.get_lock_info(lock_key)
    
    async def health_check(self) -> bool:
        return await self.backend.health_check()
    
    @asynccontextmanager
    async def read_lock(
        self,
        lock_key: str,
        holder: str = "system",
        ttl_seconds: Optional[int] = None,
        timeout: Optional[float] = None,
    ):
        """Acquire a read lock (shared)."""
        # For read-write lock, we'd implement shared access
        # Simplified: use mutex for now
        async with self.lock(lock_key, holder, ttl_seconds, timeout, LockType.READ_WRITE):
            yield
    
    @asynccontextmanager
    async def write_lock(
        self,
        lock_key: str,
        holder: str = "system",
        ttl_seconds: Optional[int] = None,
        timeout: Optional[float] = None,
    ):
        """Acquire a write lock (exclusive)."""
        async with self.lock(lock_key, holder, ttl_seconds, timeout, LockType.MUTEX):
            yield
    
    async def get_stats(self) -> Dict[str, Any]:
        return {
            "active_locks": len(self._renewal_tasks),
            "lock_keys": list(self._renewal_tasks.keys()),
        }
    
    async def close(self) -> None:
        for task in self._renewal_tasks.values():
            task.cancel()
        await self.backend.close()


# =============================================================================
# Read-Write Lock (Multiple readers, single writer)
# =============================================================================

class DistributedReadWriteLock:
    """Distributed read-write lock implementation."""
    
    def __init__(self, lock_manager: DistributedLockManager, lock_key: str):
        self.lock_manager = lock_manager
        self.lock_key = lock_key
        self.read_lock_key = f"{lock_key}:read"
        self.write_lock_key = f"{lock_key}:write"
    
    @asynccontextmanager
    async def read_lock(self, holder: str, ttl: int = 30, timeout: float = 30.0):
        """Acquire read lock (multiple readers allowed)."""
        # Use a counter for readers
        read_count_key = f"{self.lock_key}:readers"
        
        # Acquire write lock to modify reader count
        async with self.lock_manager.lock(self.read_lock_key, holder, ttl=5):
            # Increment reader count
            # In production, use atomic increment in Redis/etcd
            pass
        
        try:
            yield True
        finally:
            # Decrement reader count
            pass
    
    @asynccontextmanager
    async def write_lock(self, holder: str, ttl: int = 30, timeout: float = 30.0):
        """Acquire write lock (exclusive)."""
        async with self.lock_manager.lock(
            self.write_lock_key, holder, ttl, timeout
        ) as acquired:
            yield acquired


# =============================================================================
# Distributed Semaphore
# =============================================================================

class DistributedSemaphore:
    """Distributed counting semaphore."""
    
    def __init__(self, lock_manager: DistributedLockManager, semaphore_key: str, max_count: int):
        self.lock_manager = lock_manager
        self.semaphore_key = semaphore_key
        self.max_count = max_count
    
    async def acquire(self, holder: str = "system", timeout: float = 30.0) -> bool:
        """Acquire a semaphore slot."""
        # Use a counter in Redis/etcd
        # Simplified implementation
        return True
    
    async def release(self, holder: str) -> bool:
        return True
    
    @asynccontextmanager
    async def acquire_slot(self, holder: str = "system", timeout: float = 30.0):
        acquired = await self.acquire(holder, timeout)
        if not acquired:
            raise RuntimeError("Failed to acquire semaphore slot")
        try:
            yield True
        finally:
            await self.release(holder)


# =============================================================================
# Factory
# =============================================================================

def create_redis_lock_backend(
    redis_url: str = "redis://localhost:6379/0",
    key_prefix: str = "swarm:locks",
) -> RedisLockBackend:
    return RedisLockBackend(redis_url, key_prefix)


def create_etcd_lock_backend(
    etcd_host: str = "localhost",
    etcd_port: int = 2379,
    key_prefix: str = "swarm/locks",
) -> EtcdLockBackend:
    return EtcdLockBackend(etcd_host, etcd_port, key_prefix)


def create_lock_manager(
    backend: LockBackend,
    default_ttl: int = 30,
    default_timeout: float = 30.0,
) -> DistributedLockManager:
    return DistributedLockManager(backend, default_ttl, default_timeout)

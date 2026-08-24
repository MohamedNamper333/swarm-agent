"""
Persistence Layer - Abstract base and implementations for distributed state persistence.
Supports PostgreSQL, etcd, and in-memory backends with unified interface.
"""

import asyncio
import json
import uuid
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, TypeVar, Generic
from contextlib import asynccontextmanager
try:
    import asyncpg
except ImportError:
    asyncpg = None

try:
    import etcd3
except ImportError:
    etcd3 = None

logger = logging.getLogger(__name__)

T = TypeVar('T')


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def uuidv7() -> str:
    return str(uuid.uuid4())


# =============================================================================
# Core Models
# =============================================================================

class PersistenceBackend(str, Enum):
    POSTGRESQL = "postgresql"
    ETCD = "etcd"
    MEMORY = "memory"


@dataclass
class PersistenceConfig:
    backend: PersistenceBackend = PersistenceBackend.MEMORY
    
    # PostgreSQL config
    postgres_dsn: Optional[str] = None
    pool_size: int = 10
    max_overflow: int = 20
    
    # etcd config
    etcd_host: str = "localhost"
    etcd_port: int = 2379
    etcd_ca_cert: Optional[str] = None
    etcd_cert_key: Optional[str] = None
    etcd_cert_cert: Optional[str] = None
    
    # Connection settings
    connect_timeout: float = 10.0
    command_timeout: float = 30.0
    
    # Pool settings
    pool_min_size: int = 2
    pool_max_size: int = 10


@dataclass
class PersistedRecord:
    key: str
    value: bytes
    version: int = 1
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ttl_seconds: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Transaction:
    tx_id: str = field(default_factory=lambda: f"tx-{uuid.uuid4()}")
    operations: List[Dict[str, Any]] = field(default_factory=list)
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    committed: bool = False
    rolled_back: bool = False


# =============================================================================
# Repository Interface
# =============================================================================

class Repository(ABC, Generic[T]):
    """Abstract repository interface."""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[T]:
        pass
    
    @abstractmethod
    async def set(self, key: str, value: T, ttl_seconds: Optional[int] = None) -> bool:
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        pass
    
    @abstractmethod
    async def keys(self, pattern: str = "*") -> List[str]:
        pass
    
    @abstractmethod
    async def get_multi(self, keys: List[str]) -> Dict[str, T]:
        pass
    
    @abstractmethod
    async def set_multi(self, entries: Dict[str, T]) -> Dict[str, bool]:
        pass
    
    @abstractmethod
    async def compare_and_set(self, key: str, expected: T, new_value: T) -> bool:
        pass
    
    @abstractmethod
    async def increment(self, key: str, delta: int = 1) -> int:
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        pass
    
    @abstractmethod
    async def close(self) -> None:
        pass


# =============================================================================
# PostgreSQL Backend
# =============================================================================

class PostgresRepository(Repository[Dict[str, Any]]):
    """PostgreSQL-backed repository with connection pooling."""
    
    def __init__(self, config: PersistenceConfig):
        self.config = config
        self._pool: Optional[asyncpg.Pool] = None
        self._initialized = False
    
    async def _initialize(self) -> None:
        if self._initialized:
            return
        
        if asyncpg is None:
            raise RuntimeError("asyncpg not installed. Install with: pip install asyncpg")
        
        if not self.config.postgres_dsn:
            raise ValueError("PostgreSQL DSN not configured")
        
        self._pool = await asyncpg.create_pool(
            self.config.postgres_dsn,
            min_size=self.config.pool_min_size,
            max_size=self.config.pool_max_size,
            command_timeout=self.config.command_timeout,
        )
        
        # Create tables
        async with self._pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS kv_store (
                    key TEXT PRIMARY KEY,
                    value BYTEA NOT NULL,
                    version INTEGER DEFAULT 1,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW(),
                    ttl_seconds INTEGER,
                    metadata JSONB DEFAULT '{}'
                );
                CREATE INDEX IF NOT EXISTS idx_kv_store_updated ON kv_store(updated_at);
                CREATE INDEX IF NOT EXISTS idx_kv_store_ttl ON kv_store(updated_at) 
                    WHERE ttl_seconds IS NOT NULL;
            """)
        
        self._initialized = True
        logger.info("PostgreSQL repository initialized")
    
    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        await self._initialize()
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT value, version, metadata FROM kv_store WHERE key = $1",
                key
            )
            if row:
                return {
                    "key": key,
                    "value": row["value"],
                    "version": row["version"],
                    "metadata": row["metadata"]
                }
            return None
    
    async def set(self, key: str, value: Dict[str, Any], ttl_seconds: Optional[int] = None) -> bool:
        await self._initialize()
        
        async with self._pool.acquire() as conn:
            # Use ON CONFLICT for upsert
            await conn.execute("""
                INSERT INTO kv_store (key, value, version, ttl_seconds, metadata, updated_at)
                VALUES ($1, $2, 1, $3, $4, NOW())
                ON CONFLICT (key) DO UPDATE SET
                    value = EXCLUDED.value,
                    version = kv_store.version + 1,
                    ttl_seconds = EXCLUDED.ttl_seconds,
                    metadata = EXCLUDED.metadata,
                    updated_at = NOW()
            """, key, json.dumps(value["value"]).encode(), ttl_seconds, json.dumps(value.get("metadata", {})))
        
        return True
    
    async def delete(self, key: str) -> bool:
        await self._initialize()
        async with self._pool.acquire() as conn:
            result = await conn.execute("DELETE FROM kv_store WHERE key = $1", key)
            return result == "DELETE 1"
    
    async def exists(self, key: str) -> bool:
        await self._initialize()
        async with self._pool.acquire() as conn:
            return await conn.fetchval("SELECT 1 FROM kv_store WHERE key = $1", key) is not None
    
    async def keys(self, pattern: str = "*") -> List[str]:
        await self._initialize()
        async with self._pool.acquire() as conn:
            # Simple pattern matching - in production use pg_trgm or similar
            if pattern == "*":
                rows = await conn.fetch("SELECT key FROM kv_store")
            else:
                # Simple pattern - replace * with %
                pattern = pattern.replace("*", "%")
                rows = await conn.fetch("SELECT key FROM kv_store WHERE key LIKE $1", pattern)
            return [row["key"] for row in rows]
    
    async def get_multi(self, keys: List[str]) -> Dict[str, Dict[str, Any]]:
        await self._initialize()
        if not keys:
            return {}
        
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT key, value, version, metadata FROM kv_store WHERE key = ANY($1)",
                keys
            )
            return {row["key"]: {
                "key": row["key"],
                "value": row["value"],
                "version": row["version"],
                "metadata": row["metadata"]
            } for row in rows}
    
    async def set_multi(self, entries: Dict[str, Dict[str, Any]]) -> Dict[str, bool]:
        await self._initialize()
        
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                for key, value in entries.items():
                    await conn.execute("""
                        INSERT INTO kv_store (key, value, version, ttl_seconds, metadata, updated_at)
                        VALUES ($1, $2, 1, $3, $4, NOW())
                        ON CONFLICT (key) DO UPDATE SET
                            value = EXCLUDED.value,
                            version = kv_store.version + 1,
                            ttl_seconds = EXCLUDED.ttl_seconds,
                            metadata = EXCLUDED.metadata,
                            updated_at = NOW()
                    """, key, json.dumps(value["value"]).encode(), 
                        None, json.dumps(value.get("metadata", {})))
        
        return {k: True for k in entries}
    
    async def compare_and_set(self, key: str, expected: Dict[str, Any], new_value: Dict[str, Any]) -> bool:
        await self._initialize()
        
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                current = await conn.fetchrow(
                    "SELECT value FROM kv_store WHERE key = $1 FOR UPDATE", key
                )
                
                if current and current["value"] == json.dumps(expected["value"]).encode():
                    await conn.execute(
                        "UPDATE kv_store SET value = $1, version = version + 1, updated_at = NOW() WHERE key = $2",
                        json.dumps(new_value["value"]).encode(), key
                    )
                    return True
            return False
    
    async def increment(self, key: str, delta: int = 1) -> int:
        await self._initialize()
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                current = await conn.fetchrow(
                    "SELECT value FROM kv_store WHERE key = $1 FOR UPDATE", key
                )
                if current:
                    value = int.from_bytes(current["value"], "big") + delta
                else:
                    value = delta
                
                await conn.execute("""
                    INSERT INTO kv_store (key, value, version, updated_at)
                    VALUES ($1, $2, 1, NOW())
                    ON CONFLICT (key) DO UPDATE SET
                        value = EXCLUDED.value,
                        version = kv_store.version + 1,
                        updated_at = NOW()
                """, key, value.to_bytes(8, "big"))
                
                return value
    
    async def health_check(self) -> bool:
        try:
            await self._initialize()
            async with self._pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"PostgreSQL health check failed: {e}")
            return False
    
    async def close(self) -> None:
        if self._pool:
            await self._pool.close()
            self._pool = None
            self._initialized = False


# =============================================================================
# etcd Backend
# =============================================================================

class EtcdRepository(Repository[Dict[str, Any]]):
    """etcd-backed repository with distributed coordination."""
    
    def __init__(self, config: PersistenceConfig):
        self.config = config
        self._client: Optional[etcd3.Etcd3Client] = None
        self._lock = asyncio.Lock()
    
    async def _get_client(self):
        if etcd3 is None:
            raise RuntimeError("etcd3 not installed. Install with: pip install etcd3")
        if self._client is None:
            self._client = etcd3.client(
                host=self.config.etcd_host,
                port=self.config.etcd_port,
                ca_cert=self.config.etcd_ca_cert,
                cert_key=self.config.etcd_cert_key,
                cert_cert=self.config.etcd_cert_cert,
            )
        return self._client
    
    def _key_prefix(self, key: str) -> str:
        return f"/swarm/kv/{key}"
    
    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        client = await self._get_client()
        value, meta = client.get(self._key_prefix(key))
        if value is None:
            return None
        return {
            "key": key,
            "value": value,
            "version": meta.version,
            "metadata": {}
        }
    
    async def set(self, key: str, value: Dict[str, Any], ttl_seconds: Optional[int] = None) -> bool:
        client = await self._get_client()
        key_prefixed = self._key_prefix(key)
        
        if ttl_seconds:
            # Use lease for TTL
            lease = client.lease(ttl_seconds)
            client.put(key_prefixed, json.dumps(value["value"]).encode(), lease)
        else:
            client.put(key_prefixed, json.dumps(value["value"]).encode())
        
        return True
    
    async def delete(self, key: str) -> bool:
        client = await self._get_client()
        result = client.delete(self._key_prefix(key))
        return result.deleted > 0
    
    async def exists(self, key: str) -> bool:
        client = await self._get_client()
        _, meta = client.get(self._key_prefix(key))
        return meta is not None
    
    async def keys(self, pattern: str = "*") -> List[str]:
        client = await self._get_client()
        prefix = "/swarm/kv/" if pattern == "*" else f"/swarm/kv/{pattern.replace('*', '')}"
        results, _ = client.get_prefix(prefix)
        keys = []
        for _, meta in results:
            key = meta.key.decode().replace("/swarm/kv/", "")
            if pattern == "*" or self._match_pattern(key, pattern):
                keys.append(key)
        return keys
    
    def _match_pattern(self, key: str, pattern: str) -> bool:
        import fnmatch
        return fnmatch.fnmatch(key, pattern.replace("*", "*"))
    
    async def get_multi(self, keys: List[str]) -> Dict[str, Dict[str, Any]]:
        client = await self._get_client()
        result = {}
        for key in keys:
            value, meta = client.get(self._key_prefix(key))
            if value:
                result[key] = {
                    "key": key,
                    "value": value,
                    "version": meta.version,
                    "metadata": {}
                }
        return result
    
    async def set_multi(self, entries: Dict[str, Dict[str, Any]]) -> Dict[str, bool]:
        client = await self._get_client()
        results = {}
        
        # Use transaction for atomicity
        txn = client.txn()
        for key, value in entries.items():
            txn.compare([]).success([
                client.put(self._key_prefix(key), json.dumps(value["value"]).encode())
            ]).failure([])
        
        try:
            txn.commit()
            return {k: True for k in entries}
        except Exception as e:
            logger.error(f"etcd batch set failed: {e}")
            return {k: False for k in entries}
    
    async def compare_and_set(self, key: str, expected: Dict[str, Any], new_value: Dict[str, Any]) -> bool:
        client = await self._get_client()
        key_prefixed = self._key_prefix(key)
        
        # Get current value
        current_value, meta = client.get(key_prefixed)
        if current_value is None:
            return False
        
        if current_value == json.dumps(expected["value"]).encode():
            # Use compare-and-swap via transaction
            txn = client.txn()
            txn.compare([client.transactions.version(key_prefixed) == meta.version])
            txn.success([client.put(key_prefixed, json.dumps(new_value["value"]).encode())])
            txn.failure([])
            
            success, _ = txn.commit()
            return success
        
        return False
    
    async def increment(self, key: str, delta: int = 1) -> int:
        client = await self._get_client()
        key_prefixed = self._key_prefix(key)
        
        # Use etcd's atomic increment via compare-and-swap loop
        for _ in range(10):  # Retry up to 10 times
            current_value, meta = client.get(key_prefixed)
            if current_value is None:
                current = 0
            else:
                current = int.from_bytes(current_value, "big")
            
            new_value = current + delta
            new_bytes = new_value.to_bytes(8, "big")
            
            txn = client.txn()
            txn.compare([client.transactions.version(key_prefixed) == meta.version])
            txn.success([client.put(key_prefixed, new_bytes)])
            txn.failure([])
            
            success, _ = txn.commit()
            if success:
                return new_value
            
            await asyncio.sleep(0.01)  # Brief backoff
        
        raise RuntimeError("Failed to increment after retries")
    
    async def health_check(self) -> bool:
        try:
            client = await self._get_client()
            client.status()
            return True
        except Exception as e:
            logger.error(f"etcd health check failed: {e}")
            return False
    
    async def close(self) -> None:
        if self._client:
            self._client.close()
            self._client = None


# =============================================================================
# In-Memory Backend (for testing/development)
# =============================================================================

class MemoryRepository(Repository[Dict[str, Any]]):
    """In-memory repository for testing and development."""
    
    def __init__(self):
        self._data: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
        self._versions: Dict[str, int] = {}
    
    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        async with self._lock:
            return self._data.get(key)
    
    async def set(self, key: str, value: Dict[str, Any], ttl_seconds: Optional[int] = None) -> bool:
        async with self._lock:
            self._data[key] = value
            self._versions[key] = self._versions.get(key, 0) + 1
            return True
    
    async def delete(self, key: str) -> bool:
        async with self._lock:
            if key in self._data:
                del self._data[key]
                return True
            return False
    
    async def exists(self, key: str) -> bool:
        async with self._lock:
            return key in self._data
    
    async def keys(self, pattern: str = "*") -> List[str]:
        import fnmatch
        async with self._lock:
            if pattern == "*":
                return list(self._data.keys())
            return [k for k in self._data.keys() if fnmatch.fnmatch(k, pattern)]
    
    async def get_multi(self, keys: List[str]) -> Dict[str, Dict[str, Any]]:
        async with self._lock:
            return {k: self._data[k] for k in keys if k in self._data}
    
    async def set_multi(self, entries: Dict[str, Dict[str, Any]]) -> Dict[str, bool]:
        async with self._lock:
            for k, v in entries.items():
                self._data[k] = v
            return {k: True for k in entries}
    
    async def compare_and_set(self, key: str, expected: Dict[str, Any], new_value: Dict[str, Any]) -> bool:
        async with self._lock:
            current = self._data.get(key)
            if current and current == expected:
                self._data[key] = new_value
                self._versions[key] = self._versions.get(key, 0) + 1
                return True
            return False
    
    async def increment(self, key: str, delta: int = 1) -> int:
        async with self._lock:
            current = self._data.get(key, {"value": b"\x00\x00\x00\x00\x00\x00\x00\x00"})
            current_val = int.from_bytes(current["value"], "big") if isinstance(current, dict) else int(current) if isinstance(current, bytes) else 0
            new_val = current_val + delta
            self._data[key] = {"value": new_val.to_bytes(8, "big")}
            return new_val
    
    async def health_check(self) -> bool:
        return True
    
    async def close(self) -> None:
        pass


# =============================================================================
# Unified Repository Manager
# =============================================================================

class PersistenceManager:
    """Manages multiple repositories with unified interface."""
    
    def __init__(self, config: PersistenceConfig):
        self.config = config
        self._repositories: Dict[str, Repository] = {}
        self._default_repo: Optional[Repository] = None
        self._lock = asyncio.Lock()
    
    async def get_repository(self, name: str = "default") -> Repository:
        async with self._lock:
            if name not in self._repositories:
                self._repositories[name] = await self._create_repository(name)
            return self._repositories[name]
    
    async def _create_repository(self, name: str) -> Repository:
        if self.config.backend == PersistenceBackend.POSTGRESQL:
            return PostgresRepository(self.config)
        elif self.config.backend == PersistenceBackend.ETCD:
            return EtcdRepository(self.config)
        else:
            return MemoryRepository()
    
    async def get_default(self) -> Repository:
        if self._default_repo is None:
            self._default_repo = await self.get_repository("default")
        return self._default_repo
    
    async def close_all(self) -> None:
        async with self._lock:
            for repo in self._repositories.values():
                await repo.close()
            self._repositories.clear()
            self._default_repo = None


# =============================================================================
# Factory
# =============================================================================

def create_persistence_manager(config: PersistenceConfig) -> PersistenceManager:
    """Create a persistence manager with the given configuration."""
    return PersistenceManager(config)


def create_repository(config: PersistenceConfig) -> Repository:
    """Create a single repository instance."""
    if config.backend == PersistenceBackend.POSTGRESQL:
        return PostgresRepository(config)
    elif config.backend == PersistenceBackend.ETCD:
        return EtcdRepository(config)
    else:
        return MemoryRepository()

"""
Persistence Layer - Distributed state persistence with PostgreSQL, etcd, and distributed coordination.
"""

from .base import (
    PersistenceBackend,
    PersistenceConfig,
    PersistedRecord,
    Transaction,
    Repository,
    PostgresRepository,
    EtcdRepository,
    MemoryRepository,
    PersistenceManager,
    create_persistence_manager,
    create_repository,
)

from .locks import (
    LockType,
    LockConfig,
    LockInfo,
    LockBackend,
    RedisLockBackend,
    EtcdLockBackend,
    DistributedLockManager,
    DistributedReadWriteLock,
    DistributedSemaphore,
    create_redis_lock_backend,
    create_etcd_lock_backend,
    create_lock_manager,
)

from .consensus import (
    NodeState,
    ConsensusRole,
    ClusterMember,
    LogEntry,
    VoteRequest,
    VoteResponse,
    AppendEntriesRequest,
    AppendEntriesResponse,
    RaftConsensus,
    ConsensusManager,
    create_consensus_manager,
)

__all__ = [
    # Base
    "PersistenceBackend",
    "PersistenceConfig",
    "PersistedRecord",
    "Transaction",
    "Repository",
    "PostgresRepository",
    "EtcdRepository",
    "MemoryRepository",
    "PersistenceManager",
    "create_persistence_manager",
    "create_repository",
    # Locks
    "LockType",
    "LockConfig",
    "LockInfo",
    "LockBackend",
    "RedisLockBackend",
    "EtcdLockBackend",
    "DistributedLockManager",
    "DistributedReadWriteLock",
    "DistributedSemaphore",
    "create_redis_lock_backend",
    "create_etcd_lock_backend",
    "create_lock_manager",
    # Consensus
    "NodeState",
    "ConsensusRole",
    "ClusterMember",
    "LogEntry",
    "VoteRequest",
    "VoteResponse",
    "AppendEntriesRequest",
    "AppendEntriesResponse",
    "RaftConsensus",
    "ConsensusManager",
    "create_consensus_manager",
]

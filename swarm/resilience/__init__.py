"""Resilience module for swarm-agent.

Provides production-grade resilience primitives:
- RateLimiter: Token bucket per model/provider to prevent API throttling
- RetryEngine: Exponential backoff with jitter for transient failures
- TaskQueue: Priority queue with persistence for reliable task execution
- RecoveryEngine: Snapshot-based failure recovery
- SnapshotManager: Pre-stage state snapshots for fast rollback

Phase 3 / Weeks 10-11 of the Enterprise Roadmap.
"""

from swarm.resilience.rate_limiter import (
    RateLimiter,
    TokenBucket,
    RateLimitExceeded,
    RateLimitConfig,
)
from swarm.resilience.retry_engine import (
    RetryEngine,
    RetryPolicy,
    RetryStrategy,
    RetryExhausted,
    BackoffSchedule,
    AttemptRecord,
)
from swarm.resilience.task_queue import (
    TaskQueue,
    PriorityQueue,
    QueueItem,
    QueueStatus,
    TaskStatus,
)
from swarm.resilience.recovery_engine import (
    RecoveryEngine,
    RecoveryPlan,
    RecoveryStep,
    RecoveryStatus,
    RecoveryPoint,
    RecoveryEvent,
    RecoveryStats,
)
from swarm.resilience.snapshot_manager import (
    SnapshotManager,
    Snapshot,
    SnapshotMetadata,
    SnapshotScope,
    SnapshotStats,
    SnapshotStatus,
    SnapshotType,
)

__all__ = [
    # Rate limiter
    "RateLimiter",
    "TokenBucket",
    "RateLimitExceeded",
    "RateLimitConfig",
    # Retry engine
    "RetryEngine",
    "RetryPolicy",
    "RetryStrategy",
    "RetryExhausted",
    "BackoffSchedule",
    "AttemptRecord",
    # Task queue
    "TaskQueue",
    "PriorityQueue",
    "QueueItem",
    "QueueStatus",
    "TaskStatus",
    # Recovery
    "RecoveryEngine",
    "RecoveryPlan",
    "RecoveryStep",
    "RecoveryStatus",
    "RecoveryPoint",
    "RecoveryEvent",
    "RecoveryStats",
    # Snapshots
    "SnapshotManager",
    "Snapshot",
    "SnapshotMetadata",
    "SnapshotScope",
    "SnapshotStats",
    "SnapshotStatus",
    "SnapshotType",
]

"""
Durable Job Infrastructure — async execution with persistence, retries, cancellation.

F-010: Synchronous Long-Running Execution fix.
Implements: Command Accepted → Durable Job → Queue → Worker → Event Store → Result.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Callable
from enum import Enum
from datetime import datetime, timezone
import uuid
import threading
import time
import json
import logging

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    """Job lifecycle states."""
    PENDING = "pending"           # Created, not yet queued
    QUEUED = "queued"             # Waiting for worker
    ASSIGNED = "assigned"         # Worker claimed
    RUNNING = "running"           # Actively executing
    PAUSED = "paused"             # Paused by user/system
    SUCCEEDED = "succeeded"       # Completed successfully
    FAILED = "failed"             # Failed (may be retryable)
    CANCELLED = "cancelled"       # Cancelled by user
    DEAD_LETTER = "dead_letter"   # Max retries exceeded


class JobPriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


class RetryPolicy(str, Enum):
    NEVER = "never"
    FIXED = "fixed"
    EXPONENTIAL = "exponential"
    LINEAR = "linear"


@dataclass(frozen=True)
class JobConfig:
    """Job execution configuration."""
    max_retries: int = 3
    retry_policy: RetryPolicy = RetryPolicy.EXPONENTIAL
    base_retry_delay_ms: int = 1000
    max_retry_delay_ms: int = 60000
    timeout_ms: int = 300000  # 5 minutes default
    priority: JobPriority = JobPriority.NORMAL
    idempotency_key: Optional[str] = None
    tenant_id: str = "default"
    tags: List[str] = field(default_factory=list)


@dataclass
class JobResult:
    """Job execution result."""
    success: bool
    output: Optional[Any] = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    retryable: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    execution_time_ms: int = 0


@dataclass
class JobEvent:
    """Event in job lifecycle."""
    event_id: str
    job_id: str
    event_type: str  # status_change, progress, log, heartbeat
    timestamp: datetime
    data: Dict[str, Any] = field(default_factory=dict)
    worker_id: Optional[str] = None


@dataclass
class DurableJob:
    """Durable job with full lifecycle tracking."""
    job_id: str
    job_type: str
    payload: Dict[str, Any]
    config: JobConfig
    status: JobStatus = JobStatus.PENDING
    result: Optional[JobResult] = None
    events: List[JobEvent] = field(default_factory=list)
    current_worker: Optional[str] = None
    retry_count: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    assigned_at: Optional[datetime] = None
    last_heartbeat: Optional[datetime] = None
    deadline: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    # Persistence fields
    persisted_at: Optional[datetime] = None
    repository_version: int = 0
    tenant_id: str = "default"

    def __post_init__(self):
        if self.deadline is None and self.config.timeout_ms:
            self.deadline = datetime.fromtimestamp(
                self.created_at.timestamp() + self.config.timeout_ms / 1000,
                tz=timezone.utc,
            )

    def add_event(self, event_type: str, data: Dict[str, Any] = None, worker_id: str = None) -> None:
        """Add lifecycle event."""
        event = JobEvent(
            event_id=str(uuid.uuid4()),
            job_id=self.job_id,
            event_type=event_type,
            timestamp=datetime.now(timezone.utc),
            data=data or {},
            worker_id=worker_id,
        )
        self.events.append(event)
        self.updated_at = datetime.now(timezone.utc)

    def transition_to(self, new_status: JobStatus, worker_id: str = None, reason: str = "") -> bool:
        """Transition job status with validation."""
        valid_transitions = {
            JobStatus.PENDING: {JobStatus.QUEUED, JobStatus.CANCELLED},
            JobStatus.QUEUED: {JobStatus.ASSIGNED, JobStatus.CANCELLED, JobStatus.DEAD_LETTER},
            JobStatus.ASSIGNED: {JobStatus.RUNNING, JobStatus.QUEUED, JobStatus.CANCELLED},
            JobStatus.RUNNING: {JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.PAUSED, JobStatus.CANCELLED},
            JobStatus.PAUSED: {JobStatus.RUNNING, JobStatus.CANCELLED, JobStatus.QUEUED},
            JobStatus.FAILED: {JobStatus.QUEUED, JobStatus.DEAD_LETTER, JobStatus.CANCELLED},
        }

        allowed = valid_transitions.get(self.status, set())
        if new_status not in allowed:
            logger.warning(f"Invalid job transition: {self.status} -> {new_status}")
            return False

        old_status = self.status
        self.status = new_status
        self.updated_at = datetime.now(timezone.utc)

        if new_status == JobStatus.ASSIGNED:
            self.assigned_at = datetime.now(timezone.utc)
            self.current_worker = worker_id
        elif new_status == JobStatus.RUNNING:
            self.started_at = datetime.now(timezone.utc)
        elif new_status in (JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELLED):
            self.completed_at = datetime.now(timezone.utc)

        self.add_event("status_change", {
            "from": old_status.value,
            "to": new_status.value,
            "reason": reason,
        }, worker_id)

        return True

    def can_retry(self) -> bool:
        """Check if job can be retried."""
        if self.status != JobStatus.FAILED:
            return False
        if self.retry_count >= self.config.max_retries:
            return False
        if self.config.retry_policy == RetryPolicy.NEVER:
            return False
        return True

    def next_retry_delay_ms(self) -> int:
        """Calculate next retry delay based on policy."""
        if self.config.retry_policy == RetryPolicy.FIXED:
            return self.config.base_retry_delay_ms
        elif self.config.retry_policy == RetryPolicy.LINEAR:
            return self.config.base_retry_delay_ms * (self.retry_count + 1)
        elif self.config.retry_policy == RetryPolicy.EXPONENTIAL:
            delay = self.config.base_retry_delay_ms * (2 ** self.retry_count)
            return min(delay, self.config.max_retry_delay_ms)
        return self.config.base_retry_delay_ms

    def is_expired(self) -> bool:
        """Check if job deadline has passed."""
        if self.deadline is None:
            return False
        return datetime.now(timezone.utc) >= self.deadline

    def heartbeat(self, worker_id: str) -> bool:
        """Update worker heartbeat."""
        if self.current_worker != worker_id:
            return False
        self.last_heartbeat = datetime.now(timezone.utc)
        self.add_event("heartbeat", {"worker_id": worker_id}, worker_id)
        return True

    def to_dict(self) -> Dict[str, Any]:
        """Serialize job for storage/transport."""
        return {
            "job_id": self.job_id,
            "job_type": self.job_type,
            "payload": self.payload,
            "config": {
                "max_retries": self.config.max_retries,
                "retry_policy": self.config.retry_policy.value,
                "base_retry_delay_ms": self.config.base_retry_delay_ms,
                "max_retry_delay_ms": self.config.max_retry_delay_ms,
                "timeout_ms": self.config.timeout_ms,
                "priority": self.config.priority.value,
                "idempotency_key": self.config.idempotency_key,
                "tenant_id": self.config.tenant_id,
                "tags": self.config.tags,
            },
            "status": self.status.value,
            "result": {
                "success": self.result.success,
                "output": self.result.output,
                "error": self.result.error,
                "error_code": self.result.error_code,
                "retryable": self.result.retryable,
                "metadata": self.result.metadata,
                "started_at": self.result.started_at.isoformat() if self.result.started_at else None,
                "completed_at": self.result.completed_at.isoformat() if self.result.completed_at else None,
                "execution_time_ms": self.result.execution_time_ms,
            } if self.result else None,
            "retry_count": self.retry_count,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "assigned_at": self.assigned_at.isoformat() if self.assigned_at else None,
            "last_heartbeat": self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "current_worker": self.current_worker,
            "metadata": self.metadata,
            "persisted_at": self.persisted_at.isoformat() if self.persisted_at else None,
            "repository_version": self.repository_version,
            "tenant_id": self.tenant_id,
            "events": [
                {
                    "event_id": e.event_id,
                    "job_id": e.job_id,
                    "event_type": e.event_type,
                    "timestamp": e.timestamp.isoformat(),
                    "data": e.data,
                    "worker_id": e.worker_id,
                }
                for e in self.events
            ],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DurableJob":
        """Deserialize job from storage."""
        config = JobConfig(
            max_retries=data["config"].get("max_retries", 3),
            retry_policy=RetryPolicy(data["config"].get("retry_policy", "exponential")),
            base_retry_delay_ms=data["config"].get("base_retry_delay_ms", 1000),
            max_retry_delay_ms=data["config"].get("max_retry_delay_ms", 60000),
            timeout_ms=data["config"].get("timeout_ms", 300000),
            priority=JobPriority(data["config"].get("priority", "normal")),
            idempotency_key=data["config"].get("idempotency_key"),
            tenant_id=data["config"].get("tenant_id", "default"),
            tags=data["config"].get("tags", []),
        )
        job = cls(
            job_id=data["job_id"],
            job_type=data["job_type"],
            payload=data["payload"],
            config=config,
            status=JobStatus(data["status"]),
            retry_count=data.get("retry_count", 0),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            assigned_at=datetime.fromisoformat(data["assigned_at"]) if data.get("assigned_at") else None,
            last_heartbeat=datetime.fromisoformat(data["last_heartbeat"]) if data.get("last_heartbeat") else None,
            deadline=datetime.fromisoformat(data["deadline"]) if data.get("deadline") else None,
            current_worker=data.get("current_worker"),
            metadata=data.get("metadata", {}),
            persisted_at=datetime.fromisoformat(data["persisted_at"]) if data.get("persisted_at") else None,
            repository_version=data.get("repository_version", 0),
            tenant_id=data.get("tenant_id", "default"),
        )
        if data.get("result"):
            r = data["result"]
            job.result = JobResult(
                success=r["success"],
                output=r.get("output"),
                error=r.get("error"),
                error_code=r.get("error_code"),
                retryable=r.get("retryable", False),
                metadata=r.get("metadata", {}),
                started_at=datetime.fromisoformat(r["started_at"]) if r.get("started_at") else None,
                completed_at=datetime.fromisoformat(r["completed_at"]) if r.get("completed_at") else None,
                execution_time_ms=r.get("execution_time_ms", 0),
            )
        for e in data.get("events", []):
            job.events.append(JobEvent(
                event_id=e["event_id"],
                job_id=e["job_id"],
                event_type=e["event_type"],
                timestamp=datetime.fromisoformat(e["timestamp"]),
                data=e.get("data", {}),
                worker_id=e.get("worker_id"),
            ))
        return job


class JobQueue:
    """Thread-safe priority job queue."""

    def __init__(self):
        self._queues: Dict[JobPriority, List[DurableJob]] = {
            JobPriority.CRITICAL: [],
            JobPriority.HIGH: [],
            JobPriority.NORMAL: [],
            JobPriority.LOW: [],
        }
        self._lock = threading.RLock()
        self._job_index: Dict[str, DurableJob] = {}  # job_id -> job

    def enqueue(self, job: DurableJob) -> None:
        """Add job to appropriate priority queue."""
        with self._lock:
            self._queues[job.config.priority].append(job)
            self._job_index[job.job_id] = job
            # Sort by priority (created_at for FIFO within priority)
            self._queues[job.config.priority].sort(key=lambda j: j.created_at)

    def dequeue(
        self,
        worker_id: str,
        max_jobs: int = 1,
        tenant_id: Optional[str] = None,
    ) -> List[DurableJob]:
        """Dequeue jobs for a worker (highest priority first).

        If tenant_id is provided, only jobs with matching config.tenant_id
        are returned. Jobs of other tenants are skipped (not re-queued in
        this pass — they remain in the queue for their own workers).

        If tenant_id is None, backward-compatible behavior: all jobs
        are returned regardless of tenant (used by system workers).
        """
        with self._lock:
            jobs = []
            for priority in [JobPriority.CRITICAL, JobPriority.HIGH, JobPriority.NORMAL, JobPriority.LOW]:
                queue = self._queues[priority]
                idx = 0
                while idx < len(queue) and len(jobs) < max_jobs:
                    job = queue[idx]
                    if job.status != JobStatus.QUEUED:
                        # Job was cancelled/removed — remove from list
                        queue.pop(idx)
                        continue
                    if tenant_id is not None and job.config.tenant_id != tenant_id:
                        # Skip — leave in place for tenant-matching worker
                        idx += 1
                        continue
                    # Match — pop and assign
                    queue.pop(idx)
                    job.transition_to(JobStatus.ASSIGNED, worker_id)
                    jobs.append(job)
            return jobs

    def requeue(self, job: DurableJob) -> None:
        """Re-queue a job (e.g., after failure)."""
        with self._lock:
            job.transition_to(JobStatus.QUEUED)
            self.enqueue(job)

    def get(self, job_id: str) -> Optional[DurableJob]:
        """Get job by ID."""
        with self._lock:
            return self._job_index.get(job_id)

    def remove(self, job_id: str) -> bool:
        """Remove job from queue."""
        with self._lock:
            job = self._job_index.pop(job_id, None)
            if job:
                for queue in self._queues.values():
                    if job in queue:
                        queue.remove(job)
                return True
            return False

    def get_pending_count(self) -> Dict[JobPriority, int]:
        """Get count of pending jobs per priority."""
        with self._lock:
            return {p: len(q) for p, q in self._queues.items()}

    def get_all_jobs(self) -> List[DurableJob]:
        """Get all jobs (for admin/monitoring)."""
        with self._lock:
            return list(self._job_index.values())


# Global queue
_job_queue: Optional[JobQueue] = None
_queue_lock = threading.Lock()


def get_job_queue() -> JobQueue:
    global _job_queue
    with _queue_lock:
        if _job_queue is None:
            _job_queue = JobQueue()
        return _job_queue


__all__ = [
    "JobStatus",
    "JobPriority",
    "RetryPolicy",
    "JobConfig",
    "JobResult",
    "JobEvent",
    "DurableJob",
    "JobQueue",
    "get_job_queue",
]
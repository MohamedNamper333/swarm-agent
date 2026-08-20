"""
Dead Letter Queue - Handles failed jobs that exceeded max retries.
"""

import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# Dead Letter Models
# =============================================================================

class DeadLetterReason(str, Enum):
    """Reason why job ended up in DLQ."""
    MAX_RETRIES_EXCEEDED = "max_retries_exceeded"
    COMPENSATION_FAILED = "compensation_failed"
    MANUAL_APPROVAL_REQUIRED = "manual_approval_required"
    VALIDATION_FAILED = "validation_failed"
    EXECUTOR_NOT_FOUND = "executor_not_found"
    WORKER_SHUTDOWN = "worker_shutdown"
    UNKNOWN = "unknown"


@dataclass
class DeadLetterEntry:
    """A job in the dead letter queue."""
    entry_id: str
    job_id: str
    job_type: str
    payload: Dict[str, Any]
    config: "JobConfig"
    reason: DeadLetterReason
    error: str
    retry_count: int
    tenant_id: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_attempt_at: Optional[datetime] = None
    attempts: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    resolution_note: Optional[str] = None


@dataclass
class RetryPolicy:
    """Policy for retrying dead letter entries."""
    max_retry_attempts: int = 3
    retry_delay_seconds: int = 300  # 5 minutes
    exponential_backoff: bool = True
    max_delay_seconds: int = 3600  # 1 hour
    allowed_reasons: List[DeadLetterReason] = field(default_factory=lambda: [
        DeadLetterReason.MAX_RETRIES_EXCEEDED,
        DeadLetterReason.WORKER_SHUTDOWN,
    ])


# Import JobConfig from models
from .models import JobConfig, DurableJob, JobStatus


# =============================================================================
# Dead Letter Queue
# =============================================================================

class DeadLetterQueue:
    """
    Queue for jobs that have permanently failed.
    
    Features:
    - Automatic capture from worker/compensation engine
    - Configurable retry policies per reason
    - Manual requeue/retry
    - Resolution tracking
    - Metrics and monitoring
    """
    
    def __init__(
        self,
        job_repository: "JobRepository",
        queue: "JobQueue",
        retry_policy: Optional[RetryPolicy] = None,
        max_entries: int = 10000,
    ):
        from .repository import JobRepository
        from .models import JobQueue
        
        self.job_repository = job_repository
        self.queue = queue
        self.retry_policy = retry_policy or RetryPolicy()
        self.max_entries = max_entries
        
        self._entries: Dict[str, DeadLetterEntry] = {}
        self._lock = threading.RLock()
        
        # Background processor for auto-retry
        self._processor_running = False
        self._processor_thread: Optional[threading.Thread] = None
        self._shutdown_event = threading.Event()
    
    def add(
        self,
        job: DurableJob,
        reason: DeadLetterReason,
        error: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Add a failed job to the dead letter queue."""
        with self._lock:
            # Check if we need to evict oldest entries
            if len(self._entries) >= self.max_entries:
                self._evict_oldest()
            
            entry = DeadLetterEntry(
                entry_id=str(uuid.uuid4()),
                job_id=job.job_id,
                job_type=job.job_type,
                payload=job.payload,
                config=job.config,
                reason=reason,
                error=error,
                retry_count=job.retry_count,
                tenant_id=job.tenant_id,
                metadata=metadata or {},
            )
            
            self._entries[entry.entry_id] = entry
            
            # Update job status
            job.transition_to(JobStatus.DEAD_LETTER, "dead_letter_queue", reason.value)
            
            # Persist to repository
            if self.job_repository:
                try:
                    import asyncio
                    loop = asyncio.get_running_loop()
                    loop.create_task(self.job_repository.save_job(job))
                except RuntimeError:
                    pass
            
            logger.warning(
                f"Job {job.job_id} added to DLQ: {reason.value} - {error}"
            )
            
            return entry.entry_id
    
    def _evict_oldest(self) -> None:
        """Remove oldest resolved entries to make space."""
        resolved = [
            (eid, e) for eid, e in self._entries.items() if e.resolved
        ]
        if resolved:
            # Sort by resolved_at, remove oldest
            resolved.sort(key=lambda x: x[1].resolved_at or datetime.min)
            for eid, _ in resolved[:10]:  # Remove up to 10
                del self._entries[eid]
                logger.debug(f"Evicted resolved DLQ entry: {eid}")
    
    def get(self, entry_id: str) -> Optional[DeadLetterEntry]:
        """Get a dead letter entry by ID."""
        with self._lock:
            return self._entries.get(entry_id)
    
    def list(
        self,
        tenant_id: Optional[str] = None,
        reason: Optional[DeadLetterReason] = None,
        resolved: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[DeadLetterEntry]:
        """List dead letter entries with filters."""
        with self._lock:
            entries = list(self._entries.values())
            
            if tenant_id:
                entries = [e for e in entries if e.tenant_id == tenant_id]
            if reason:
                entries = [e for e in entries if e.reason == reason]
            if resolved is not None:
                entries = [e for e in entries if e.resolved == resolved]
            
            # Sort by created_at desc
            entries.sort(key=lambda e: e.created_at, reverse=True)
            
            return entries[offset:offset + limit]
    
    def retry(self, entry_id: str, modified_payload: Optional[Dict[str, Any]] = None) -> bool:
        """Manually retry a dead letter entry."""
        with self._lock:
            entry = self._entries.get(entry_id)
            if not entry:
                return False
            
            if entry.resolved:
                logger.warning(f"Entry {entry_id} already resolved")
                return False
            
            # Create new job with optionally modified payload
            payload = modified_payload or entry.payload
            
            job = DurableJob(
                job_id=str(uuid.uuid4()),
                job_type=entry.job_type,
                payload=payload,
                config=entry.config,
                tenant_id=entry.tenant_id,
            )
            
            # Track retry attempt
            entry.attempts.append({
                "attempt_id": str(uuid.uuid4()),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "new_job_id": job.job_id,
                "modified_payload": modified_payload is not None,
            })
            entry.last_attempt_at = datetime.now(timezone.utc)
            
            # Enqueue
            self.queue.enqueue(job)
            
            logger.info(f"Retried DLQ entry {entry_id} as job {job.job_id}")
            return True
    
    def requeue_original(self, entry_id: str) -> bool:
        """Requeue the exact original job."""
        return self.retry(entry_id, modified_payload=None)
    
    def resolve(
        self,
        entry_id: str,
        resolved_by: str,
        note: Optional[str] = None,
    ) -> bool:
        """Mark a dead letter entry as resolved."""
        with self._lock:
            entry = self._entries.get(entry_id)
            if not entry:
                return False
            
            entry.resolved = True
            entry.resolved_at = datetime.now(timezone.utc)
            entry.resolved_by = resolved_by
            entry.resolution_note = note
            
            logger.info(f"Resolved DLQ entry {entry_id} by {resolved_by}: {note}")
            return True
    
    def delete(self, entry_id: str) -> bool:
        """Permanently delete a dead letter entry."""
        with self._lock:
            if entry_id in self._entries:
                del self._entries[entry_id]
                logger.info(f"Deleted DLQ entry: {entry_id}")
                return True
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get DLQ statistics."""
        with self._lock:
            entries = list(self._entries.values())
            
            by_reason: Dict[str, int] = {}
            by_tenant: Dict[str, int] = {}
            resolved_count = 0
            
            for e in entries:
                by_reason[e.reason.value] = by_reason.get(e.reason.value, 0) + 1
                by_tenant[e.tenant_id] = by_tenant.get(e.tenant_id, 0) + 1
                if e.resolved:
                    resolved_count += 1
            
            return {
                "total_entries": len(entries),
                "resolved": resolved_count,
                "unresolved": len(entries) - resolved_count,
                "by_reason": by_reason,
                "by_tenant": by_tenant,
                "oldest_unresolved": (
                    min((e.created_at for e in entries if not e.resolved), default=None)
                ),
            }
    
    def start_auto_retry(self, check_interval_sec: int = 60) -> None:
        """Start background auto-retry processor."""
        if self._processor_running:
            return
        
        self._processor_running = True
        self._shutdown_event.clear()
        
        def processor_loop():
            logger.info("DLQ auto-retry processor started")
            
            while self._processor_running and not self._shutdown_event.is_set():
                try:
                    self._process_auto_retries()
                except Exception as e:
                    logger.error(f"DLQ processor error: {e}")
                
                self._shutdown_event.wait(timeout=check_interval_sec)
            
            logger.info("DLQ auto-retry processor stopped")
        
        self._processor_thread = threading.Thread(target=processor_loop, daemon=True)
        self._processor_thread.start()
    
    def stop_auto_retry(self) -> None:
        """Stop background auto-retry processor."""
        if not self._processor_running:
            return
        
        self._processor_running = False
        self._shutdown_event.set()
        
        if self._processor_thread and self._processor_thread.is_alive():
            self._processor_thread.join(timeout=5)
    
    def _process_auto_retries(self) -> None:
        """Process entries eligible for auto-retry."""
        with self._lock:
            now = datetime.now(timezone.utc)
            eligible = []
            
            for entry in self._entries.values():
                if entry.resolved:
                    continue
                
                # Check if reason is allowed for auto-retry
                if entry.reason not in self.retry_policy.allowed_reasons:
                    continue
                
                # Check attempt count
                if len(entry.attempts) >= self.retry_policy.max_retry_attempts:
                    continue
                
                # Check delay since last attempt
                if entry.last_attempt_at:
                    delay = self.retry_policy.retry_delay_seconds
                    if self.retry_policy.exponential_backoff:
                        delay = min(
                            delay * (2 ** len(entry.attempts)),
                            self.retry_policy.max_delay_seconds
                        )
                    
                    if (now - entry.last_attempt_at).total_seconds() < delay:
                        continue
                
                eligible.append(entry)
            
            for entry in eligible:
                logger.info(f"Auto-retrying DLQ entry {entry.entry_id} (attempt {len(entry.attempts) + 1})")
                self.retry(entry.entry_id)


# =============================================================================
# Integration with Worker
# =============================================================================

class DLQIntegration:
    """Helper to integrate DLQ with Worker and CompensationEngine."""
    
    def __init__(
        self,
        dead_letter_queue: DeadLetterQueue,
    ):
        self.dlq = dead_letter_queue
    
    def handle_worker_failure(
        self,
        job: DurableJob,
        error: str,
    ) -> str:
        """Handle job failure from worker."""
        if job.retry_count >= job.config.max_retries:
            return self.dlq.add(job, DeadLetterReason.MAX_RETRIES_EXCEEDED, error)
        return ""
    
    def handle_compensation_failure(
        self,
        job: DurableJob,
        step_id: str,
        error: str,
    ) -> str:
        """Handle compensation failure."""
        return self.dlq.add(
            job,
            DeadLetterReason.COMPENSATION_FAILED,
            f"Compensation failed for step {step_id}: {error}",
            metadata={"failed_step": step_id}
        )
    
    def handle_validation_failure(
        self,
        job: DurableJob,
        error: str,
    ) -> str:
        """Handle payload validation failure."""
        return self.dlq.add(job, DeadLetterReason.VALIDATION_FAILED, error)
    
    def handle_executor_not_found(
        self,
        job: DurableJob,
        job_type: str,
    ) -> str:
        """Handle missing executor."""
        return self.dlq.add(
            job,
            DeadLetterReason.EXECUTOR_NOT_FOUND,
            f"No executor for job type: {job_type}"
        )


# =============================================================================
# Factory
# =============================================================================

def create_dead_letter_queue(
    job_repository: "JobRepository",
    queue: "JobQueue",
    retry_policy: Optional[RetryPolicy] = None,
    max_entries: int = 10000,
) -> DeadLetterQueue:
    """Create a DeadLetterQueue instance."""
    return DeadLetterQueue(job_repository, queue, retry_policy, max_entries)

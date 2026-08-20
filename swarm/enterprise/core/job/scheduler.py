"""
Job Scheduler - Cron-like scheduling and delayed execution for durable jobs.
"""

import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Callable, Dict, List, Optional, Set
from enum import Enum
import heapq
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# Schedule Models
# =============================================================================

class ScheduleType(str, Enum):
    """Type of schedule."""
    ONCE = "once"           # Run once at specific time
    INTERVAL = "interval"   # Run every N seconds
    CRON = "cron"           # Cron expression


@dataclass(frozen=True)
class ScheduleConfig:
    """Configuration for a scheduled job."""
    schedule_id: str
    schedule_type: ScheduleType
    job_type: str
    payload: Dict[str, Any]
    config: "JobConfig"
    
    # Timing
    start_at: Optional[datetime] = None       # When to start (for all types)
    end_at: Optional[datetime] = None         # When to stop (for recurring)
    interval_seconds: Optional[int] = None    # For INTERVAL type
    cron_expression: Optional[str] = None     # For CRON type
    
    # Execution
    max_runs: Optional[int] = None            # Limit total runs
    timezone: str = "UTC"                     # Timezone for cron
    
    # Metadata
    tenant_id: str = "default"
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def __post_init__(self):
        if self.schedule_type == ScheduleType.INTERVAL and not self.interval_seconds:
            raise ValueError("interval_seconds required for INTERVAL schedule")
        if self.schedule_type == ScheduleType.CRON and not self.cron_expression:
            raise ValueError("cron_expression required for CRON schedule")


@dataclass
class ScheduledJob:
    """A scheduled job instance."""
    schedule_id: str
    job_type: str
    payload: Dict[str, Any]
    config: "JobConfig"
    run_count: int = 0
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    is_active: bool = True
    tenant_id: str = "default"
    tags: List[str] = field(default_factory=list)
    
    def __lt__(self, other: "ScheduledJob") -> bool:
        """For priority queue ordering by next_run_at."""
        if self.next_run_at is None and other.next_run_at is None:
            return False
        if self.next_run_at is None:
            return False
        if other.next_run_at is None:
            return True
        return self.next_run_at < other.next_run_at


# Import JobConfig from models
from .models import JobConfig, JobPriority, DurableJob


# =============================================================================
# Cron Parser (Simple implementation)
# =============================================================================

class CronParser:
    """Simple cron expression parser. Supports standard 5-field cron."""
    
    @staticmethod
    def parse(cron_expr: str, base_time: datetime) -> Optional[datetime]:
        """
        Parse cron expression and return next matching time after base_time.
        
        Format: minute hour day_of_month month day_of_week
        Supports: *, */n, n, n-m, n,m
        """
        try:
            parts = cron_expr.strip().split()
            if len(parts) != 5:
                return None
            
            minute_spec, hour_spec, dom_spec, month_spec, dow_spec = parts
            
            current = base_time.replace(second=0, microsecond=0)
            
            # Search forward for next match (max 1 year)
            for _ in range(366 * 24 * 60):  # Max minutes in a year
                current += timedelta(minutes=1)
                
                if CronParser._matches_spec(current.minute, minute_spec, 0, 59) and \
                   CronParser._matches_spec(current.hour, hour_spec, 0, 23) and \
                   CronParser._matches_spec(current.day, dom_spec, 1, 31) and \
                   CronParser._matches_spec(current.month, month_spec, 1, 12) and \
                   CronParser._matches_spec(current.weekday(), dow_spec, 0, 6):
                    return current
            
            return None
        except Exception as e:
            logger.error(f"Cron parse error for '{cron_expr}': {e}")
            return None
    
    @staticmethod
    def _matches_spec(value: int, spec: str, min_val: int, max_val: int) -> bool:
        """Check if value matches cron spec."""
        if spec == "*":
            return True
        
        if spec.startswith("*/"):
            step = int(spec[2:])
            return value % step == 0
        
        # Handle ranges and lists
        for part in spec.split(","):
            if "-" in part:
                start, end = map(int, part.split("-"))
                if start <= value <= end:
                    return True
            else:
                if value == int(part):
                    return True
        
        return False


# =============================================================================
# Job Scheduler
# =============================================================================

class JobScheduler:
    """
    Scheduler for delayed and recurring jobs.
    
    Features:
    - One-time delayed execution
    - Interval-based recurring jobs
    - Cron-expression based scheduling
    - Tenant isolation
    - Max runs limit
    - Graceful shutdown
    """
    
    def __init__(
        self,
        job_repository: "JobRepository",
        queue: "JobQueue",
        check_interval_sec: int = 10,
    ):
        from .repository import JobRepository
        from .models import JobQueue
        
        self.job_repository = job_repository
        self.queue = queue
        self.check_interval_sec = check_interval_sec
        
        self._schedules: Dict[str, ScheduleConfig] = {}
        self._scheduled_jobs: Dict[str, ScheduledJob] = {}
        self._heap: List[ScheduledJob] = []  # Min-heap by next_run_at
        
        self._running = False
        self._shutdown_event = threading.Event()
        self._scheduler_thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()
        
        # Register signal handlers
        import signal
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        logger.info(f"Scheduler received signal {signum}, initiating shutdown")
        self.stop()
    
    def add_schedule(self, schedule: ScheduleConfig) -> str:
        """Add a new schedule. Returns schedule_id."""
        with self._lock:
            if schedule.schedule_id in self._schedules:
                raise ValueError(f"Schedule {schedule.schedule_id} already exists")
            
            self._schedules[schedule.schedule_id] = schedule
            
            # Create initial scheduled job
            scheduled_job = self._create_scheduled_job(schedule)
            if scheduled_job:
                self._scheduled_jobs[schedule.schedule_id] = scheduled_job
                if scheduled_job.next_run_at:
                    heapq.heappush(self._heap, scheduled_job)
            
            logger.info(f"Added schedule: {schedule.schedule_id} ({schedule.schedule_type.value})")
            return schedule.schedule_id
    
    def remove_schedule(self, schedule_id: str) -> bool:
        """Remove a schedule."""
        with self._lock:
            if schedule_id not in self._schedules:
                return False
            
            del self._schedules[schedule_id]
            
            if schedule_id in self._scheduled_jobs:
                job = self._scheduled_jobs.pop(schedule_id)
                job.is_active = False
                # Note: Can't efficiently remove from heap, will be filtered on pop
            
            logger.info(f"Removed schedule: {schedule_id}")
            return True
    
    def get_schedule(self, schedule_id: str) -> Optional[ScheduleConfig]:
        """Get schedule configuration."""
        with self._lock:
            return self._schedules.get(schedule_id)
    
    def list_schedules(self, tenant_id: Optional[str] = None) -> List[ScheduleConfig]:
        """List all schedules, optionally filtered by tenant."""
        with self._lock:
            schedules = list(self._schedules.values())
            if tenant_id:
                schedules = [s for s in schedules if s.tenant_id == tenant_id]
            return schedules
    
    def pause_schedule(self, schedule_id: str) -> bool:
        """Pause a schedule."""
        with self._lock:
            if schedule_id in self._scheduled_jobs:
                self._scheduled_jobs[schedule_id].is_active = False
                logger.info(f"Paused schedule: {schedule_id}")
                return True
            return False
    
    def resume_schedule(self, schedule_id: str) -> bool:
        """Resume a paused schedule."""
        with self._lock:
            if schedule_id in self._scheduled_jobs:
                job = self._scheduled_jobs[schedule_id]
                job.is_active = True
                # Recalculate next run
                schedule = self._schedules.get(schedule_id)
                if schedule:
                    self._update_next_run(job, schedule)
                    heapq.heappush(self._heap, job)
                logger.info(f"Resumed schedule: {schedule_id}")
                return True
            return False
    
    def _create_scheduled_job(self, schedule: ScheduleConfig) -> Optional[ScheduledJob]:
        """Create a ScheduledJob from ScheduleConfig."""
        now = datetime.now(timezone.utc)
        start_at = schedule.start_at or now
        
        if start_at > now:
            next_run = start_at
        else:
            next_run = self._calculate_next_run(schedule, now)
        
        if next_run is None:
            return None
        
        return ScheduledJob(
            schedule_id=schedule.schedule_id,
            job_type=schedule.job_type,
            payload=schedule.payload,
            config=schedule.config,
            next_run_at=next_run,
            tenant_id=schedule.tenant_id,
            tags=schedule.tags,
        )
    
    def _calculate_next_run(
        self,
        schedule: ScheduleConfig,
        from_time: datetime,
    ) -> Optional[datetime]:
        """Calculate next run time based on schedule type."""
        if schedule.schedule_type == ScheduleType.ONCE:
            if schedule.start_at and schedule.start_at > from_time:
                return schedule.start_at
            return None  # One-time already passed
        
        elif schedule.schedule_type == ScheduleType.INTERVAL:
            if schedule.interval_seconds:
                next_time = from_time + timedelta(seconds=schedule.interval_seconds)
                if schedule.end_at and next_time > schedule.end_at:
                    return None
                return next_time
            return None
        
        elif schedule.schedule_type == ScheduleType.CRON:
            if schedule.cron_expression:
                return CronParser.parse(schedule.cron_expression, from_time)
            return None
        
        return None
    
    def _update_next_run(self, job: ScheduledJob, schedule: ScheduleConfig) -> None:
        """Update next_run_at for a scheduled job."""
        now = datetime.now(timezone.utc)
        
        # Check max runs
        if schedule.max_runs and job.run_count >= schedule.max_runs:
            job.is_active = False
            job.next_run_at = None
            logger.info(f"Schedule {schedule.schedule_id} reached max runs ({schedule.max_runs})")
            return
        
        # Check end_at
        if schedule.end_at and now >= schedule.end_at:
            job.is_active = False
            job.next_run_at = None
            logger.info(f"Schedule {schedule.schedule_id} reached end_at")
            return
        
        job.next_run_at = self._calculate_next_run(schedule, now)
    
    def _execute_scheduled_job(self, scheduled_job: ScheduledJob) -> None:
        """Execute a scheduled job by enqueueing it."""
        try:
            # Create DurableJob
            job = DurableJob(
                job_id=str(uuid.uuid4()),
                job_type=scheduled_job.job_type,
                payload=scheduled_job.payload,
                config=scheduled_job.config,
                tenant_id=scheduled_job.tenant_id,
            )
            
            # Enqueue
            self.queue.enqueue(job)
            
            # Update scheduled job
            scheduled_job.run_count += 1
            scheduled_job.last_run_at = datetime.now(timezone.utc)
            
            logger.info(f"Executed scheduled job: {scheduled_job.schedule_id} (run #{scheduled_job.run_count})")
            
        except Exception as e:
            logger.error(f"Failed to execute scheduled job {scheduled_job.schedule_id}: {e}")
    
    def _scheduler_loop(self) -> None:
        """Main scheduler loop."""
        logger.info("Scheduler loop started")
        
        while self._running and not self._shutdown_event.is_set():
            try:
                now = datetime.now(timezone.utc)
                
                with self._lock:
                    # Process due jobs
                    while self._heap and self._heap[0].next_run_at and self._heap[0].next_run_at <= now:
                        scheduled_job = heapq.heappop(self._heap)
                        
                        # Skip if inactive or removed
                        if not scheduled_job.is_active:
                            continue
                        
                        schedule = self._schedules.get(scheduled_job.schedule_id)
                        if not schedule:
                            continue
                        
                        # Execute
                        self._execute_scheduled_job(scheduled_job)
                        
                        # Update for next run
                        self._update_next_run(scheduled_job, schedule)
                        
                        # Re-add to heap if still active
                        if scheduled_job.is_active and scheduled_job.next_run_at:
                            heapq.heappush(self._heap, scheduled_job)
                
            except Exception as e:
                logger.error(f"Scheduler loop error: {e}")
            
            # Sleep with shutdown awareness
            self._shutdown_event.wait(timeout=self.check_interval_sec)
        
        logger.info("Scheduler loop stopped")
    
    def start(self) -> None:
        """Start the scheduler."""
        if self._running:
            return
        
        self._running = True
        self._shutdown_event.clear()
        
        # Rebuild heap from existing scheduled jobs
        with self._lock:
            self._heap = [
                job for job in self._scheduled_jobs.values()
                if job.is_active and job.next_run_at
            ]
            heapq.heapify(self._heap)
        
        self._scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self._scheduler_thread.start()
        
        logger.info("Scheduler started")
    
    def stop(self, graceful: bool = True) -> None:
        """Stop the scheduler."""
        if not self._running:
            return
        
        self._running = False
        self._shutdown_event.set()
        
        if self._scheduler_thread and self._scheduler_thread.is_alive():
            if graceful:
                self._scheduler_thread.join(timeout=5)
            else:
                self._scheduler_thread.join(timeout=1)
        
        logger.info("Scheduler stopped")
    
    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status."""
        with self._lock:
            return {
                "running": self._running,
                "schedules_count": len(self._schedules),
                "active_scheduled_jobs": sum(1 for j in self._scheduled_jobs.values() if j.is_active),
                "heap_size": len(self._heap),
                "next_scheduled_run": (
                    min(j.next_run_at for j in self._scheduled_jobs.values() if j.next_run_at).isoformat()
                    if any(j.next_run_at for j in self._scheduled_jobs.values())
                    else None
                ),
            }


# =============================================================================
# Convenience Functions
# =============================================================================

def create_scheduler(
    job_repository: "JobRepository",
    queue: "JobQueue",
    check_interval_sec: int = 10,
) -> JobScheduler:
    """Create a JobScheduler instance."""
    return JobScheduler(job_repository, queue, check_interval_sec)


def schedule_once(
    scheduler: JobScheduler,
    job_type: str,
    payload: Dict[str, Any],
    run_at: datetime,
    config: Optional[JobConfig] = None,
    tenant_id: str = "default",
) -> str:
    """Schedule a one-time job."""
    from .models import JobConfig
    
    schedule = ScheduleConfig(
        schedule_id=str(uuid.uuid4()),
        schedule_type=ScheduleType.ONCE,
        job_type=job_type,
        payload=payload,
        config=config or JobConfig(tenant_id=tenant_id),
        start_at=run_at,
        tenant_id=tenant_id,
    )
    return scheduler.add_schedule(schedule)


def schedule_interval(
    scheduler: JobScheduler,
    job_type: str,
    payload: Dict[str, Any],
    interval_seconds: int,
    config: Optional[JobConfig] = None,
    start_at: Optional[datetime] = None,
    end_at: Optional[datetime] = None,
    max_runs: Optional[int] = None,
    tenant_id: str = "default",
) -> str:
    """Schedule a recurring job at fixed interval."""
    from .models import JobConfig
    
    schedule = ScheduleConfig(
        schedule_id=str(uuid.uuid4()),
        schedule_type=ScheduleType.INTERVAL,
        job_type=job_type,
        payload=payload,
        config=config or JobConfig(tenant_id=tenant_id),
        start_at=start_at,
        end_at=end_at,
        interval_seconds=interval_seconds,
        max_runs=max_runs,
        tenant_id=tenant_id,
    )
    return scheduler.add_schedule(schedule)


def schedule_cron(
    scheduler: JobScheduler,
    job_type: str,
    payload: Dict[str, Any],
    cron_expression: str,
    config: Optional[JobConfig] = None,
    start_at: Optional[datetime] = None,
    end_at: Optional[datetime] = None,
    max_runs: Optional[int] = None,
    tenant_id: str = "default",
) -> str:
    """Schedule a recurring job using cron expression."""
    from .models import JobConfig
    
    schedule = ScheduleConfig(
        schedule_id=str(uuid.uuid4()),
        schedule_type=ScheduleType.CRON,
        job_type=job_type,
        payload=payload,
        config=config or JobConfig(tenant_id=tenant_id),
        start_at=start_at,
        end_at=end_at,
        cron_expression=cron_expression,
        max_runs=max_runs,
        tenant_id=tenant_id,
    )
    return scheduler.add_schedule(schedule)

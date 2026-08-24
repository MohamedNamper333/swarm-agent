"""
Worker Infrastructure — executes durable jobs with heartbeat, cancellation, recovery.

F-010: Synchronous Long-Running Execution fix (Worker side).
"""
import threading
import time
import uuid
import logging
import signal
import sys
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, Future

from swarm.enterprise.core.job.models import (
    DurableJob, JobQueue, JobStatus, JobResult, get_job_queue,
    JobPriority,
)
from swarm.enterprise.core.job.repository import (
    JobRepository, create_job_repository, InMemoryJobRepository,
)

logger = logging.getLogger(__name__)


@dataclass
class WorkerConfig:
    """Worker configuration."""
    worker_id: str
    max_concurrent_jobs: int = 1
    heartbeat_interval_sec: int = 30
    poll_interval_sec: int = 5
    graceful_shutdown_timeout_sec: int = 60
    job_types: List[str] = field(default_factory=list)  # Empty = all types
    # Repository for persistence
    job_repository: Optional[JobRepository] = None
    repository_backend: str = "memory"  # "memory" or "redis"
    repository_config: Dict[str, Any] = field(default_factory=dict)


class JobExecutor:
    """Base class for job type executors."""

    def execute(self, job: DurableJob) -> JobResult:
        """Execute a job. Override in subclasses."""
        raise NotImplementedError

    def validate_payload(self, payload: Dict[str, Any]) -> bool:
        """Validate job payload before execution."""
        return True


class Worker:
    """Durable job worker with heartbeat and graceful shutdown."""

    def __init__(
        self,
        config: WorkerConfig,
        executors: Dict[str, JobExecutor] = None,
        queue: JobQueue = None,
    ):
        self.config = config
        self.executors = executors or {}
        self.queue = queue or get_job_queue()
        
        # Initialize repository
        if config.job_repository:
            self.job_repository = config.job_repository
        else:
            self.job_repository = create_job_repository(
                config.repository_backend,
                **config.repository_config,
            )
        
        self._running = False
        self._shutdown_event = threading.Event()
        self._active_jobs: Dict[str, DurableJob] = {}
        self._active_futures: Dict[str, Future] = {}
        self._executor = ThreadPoolExecutor(max_workers=config.max_concurrent_jobs)
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._poll_thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()

        # Register signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

    def _signal_handler(self, signum, frame):
        logger.info(f"Worker {self.config.worker_id} received signal {signum}, initiating graceful shutdown")
        self.stop()

    def register_executor(self, job_type: str, executor: JobExecutor) -> None:
        """Register an executor for a job type."""
        self.executors[job_type] = executor

    def start(self) -> None:
        """Start the worker."""
        if self._running:
            return
        self._running = True
        self._shutdown_event.clear()

        self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._heartbeat_thread.start()

        self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._poll_thread.start()

        logger.info(f"Worker {self.config.worker_id} started")

    def stop(self, graceful: bool = True) -> None:
        """Stop the worker."""
        if not self._running:
            return
        self._running = False
        self._shutdown_event.set()

        if graceful:
            logger.info(f"Worker {self.config.worker_id} waiting for active jobs...")
            deadline = time.time() + self.config.graceful_shutdown_timeout_sec
            while self._active_jobs and time.time() < deadline:
                time.sleep(1)
            if self._active_jobs:
                logger.warning(f"Worker {self.config.worker_id} force-cancelling {len(self._active_jobs)} jobs")
                self._cancel_all_jobs("worker_shutdown")
        else:
            self._cancel_all_jobs("worker_force_stop")

        self._executor.shutdown(wait=graceful)
        
        # Close repository if it has close method
        if self.job_repository and hasattr(self.job_repository, 'close'):
            try:
                import asyncio
                try:
                    loop = asyncio.get_running_loop()
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(asyncio.run, self.job_repository.close())
                        future.result()
                except RuntimeError:
                    asyncio.run(self.job_repository.close())
            except Exception as e:
                logger.warning(f"Error closing repository: {e}")
        
        logger.info(f"Worker {self.config.worker_id} stopped")

    def _cancel_all_jobs(self, reason: str) -> None:
        """Cancel all active jobs."""
        with self._lock:
            for job_id, job in self._active_jobs.items():
                try:
                    job.transition_to(JobStatus.CANCELLED, self.config.worker_id, reason)
                except Exception as e:
                    logger.error(f"Error cancelling job {job_id}: {e}")

    def _heartbeat_loop(self) -> None:
        """Monitor active jobs for stale heartbeats.

        A job is considered stale if its last_heartbeat is older than
        3x the heartbeat_interval_sec. Stale jobs are cancelled and
        transitioned to FAILED with reason 'heartbeat_timeout'.

        On shutdown, performs one final scan to catch jobs that became
        stale while the shutdown signal was being processed.
        """
        timeout_sec = self.config.heartbeat_interval_sec * 3

        def _scan_stale_jobs() -> List[tuple]:
            now = datetime.now(timezone.utc)
            stale: List[tuple] = []
            with self._lock:
                for job_id, job in self._active_jobs.items():
                    if job.last_heartbeat is None:
                        continue
                    age = (now - job.last_heartbeat).total_seconds()
                    if age > timeout_sec:
                        stale.append((job_id, job))
            return stale

        def _fail_stale_jobs(stale_jobs: List[tuple]) -> None:
            for job_id, job in stale_jobs:
                logger.warning(
                    f"Job {job_id} heartbeat stale ({timeout_sec}s timeout), failing"
                )
                future = self._active_futures.get(job_id)
                if future and not future.done():
                    future.cancel()
                try:
                    job.transition_to(
                        JobStatus.FAILED,
                        self.config.worker_id,
                        "heartbeat_timeout",
                    )
                    # Persist failed state
                    job.persisted_at = datetime.now(timezone.utc)
                    job.repository_version += 1
                    if self.job_repository:
                        try:
                            loop = asyncio.get_running_loop()
                            loop.create_task(self.job_repository.save_job(job))
                        except RuntimeError:
                            pass
                except Exception as e:
                    logger.error(f"Error failing stale job {job_id}: {e}")

        # Main loop — runs while worker is running
        while self._running:
            # Scan for stale jobs in local cache
            _fail_stale_jobs(_scan_stale_jobs())
            
            # Also check repository for stale jobs (for distributed workers)
            if self.job_repository and hasattr(self.job_repository, 'get_stale_jobs'):
                try:
                    import asyncio
                    try:
                        loop = asyncio.get_running_loop()
                        import concurrent.futures
                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            future = executor.submit(
                                asyncio.run,
                                self.job_repository.get_stale_jobs(
                                    max_heartbeat_age_seconds=timeout_sec,
                                    limit=100,
                                )
                            )
                            stale_jobs = future.result()
                    except RuntimeError:
                        stale_jobs = asyncio.run(self.job_repository.get_stale_jobs(
                            max_heartbeat_age_seconds=timeout_sec,
                            limit=100,
                        ))
                    for job in stale_jobs:
                        if job.job_id not in self._active_jobs:
                            logger.warning(f"Found stale job from repository: {job.job_id}")
                except Exception as e:
                    logger.debug(f"Repository stale check failed: {e}")

            # Sleep with shutdown awareness
            if self._shutdown_event.wait(timeout=self.config.heartbeat_interval_sec):
                # Shutdown signaled — do one final scan then exit
                _fail_stale_jobs(_scan_stale_jobs())
                break

    def _poll_loop(self) -> None:
        """Main polling loop - fetch and execute jobs."""
        while self._running and not self._shutdown_event.is_set():
            try:
                # Check capacity
                with self._lock:
                    if len(self._active_jobs) >= self.config.max_concurrent_jobs:
                        time.sleep(self.config.poll_interval_sec)
                        continue

                # Determine job types to poll
                job_types = self.config.job_types if self.config.job_types else None

                # Dequeue jobs
                jobs = self.queue.dequeue(
                    worker_id=self.config.worker_id,
                    max_jobs=self.config.max_concurrent_jobs - len(self._active_jobs),
                )

                for job in jobs:
                    if not self._running:
                        # Re-queue if shutting down
                        self.queue.requeue(job)
                        break
                    self._submit_job(job)

            except Exception as e:
                logger.error(f"Poll loop error: {e}")
                time.sleep(self.config.poll_interval_sec)

    def _submit_job(self, job: DurableJob) -> None:
        """Submit job to executor."""
        if job.job_type not in self.executors:
            logger.error(f"No executor for job type: {job.job_type}")
            job.transition_to(JobStatus.FAILED, self.config.worker_id, f"No executor for {job.job_type}")
            # Persist failure
            if self.job_repository:
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(self.job_repository.save_job(job))
                except RuntimeError:
                    pass
            return

        with self._lock:
            self._active_jobs[job.job_id] = job
        
        # Update job status and persist
        job.transition_to(JobStatus.RUNNING, self.config.worker_id)
        job.persisted_at = datetime.now(timezone.utc)
        job.repository_version += 1
        if self.job_repository:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self.job_repository.save_job(job))
            except RuntimeError:
                pass

        future = self._executor.submit(self._execute_job, job)
        self._active_futures[job.job_id] = future
        future.add_done_callback(lambda f: self._job_done(job.job_id, f))

    def _execute_job(self, job: DurableJob) -> JobResult:
        """Execute a single job."""
        executor = self.executors[job.job_type]
        try:
            # Validate payload
            if not executor.validate_payload(job.payload):
                return JobResult(
                    success=False,
                    error="Payload validation failed",
                    error_code="VALIDATION_FAILED",
                    retryable=False,
                )

            # Execute (status already RUNNING from _submit_job)
            start_time = time.time()
            result = executor.execute(job)
            execution_time = int((time.time() - start_time) * 1000)

            result.execution_time_ms = execution_time
            result.started_at = datetime.fromtimestamp(start_time, tz=timezone.utc)
            result.completed_at = datetime.now(timezone.utc)

            return result

        except Exception as e:
            logger.exception(f"Job {job.job_id} execution failed")
            return JobResult(
                success=False,
                error=str(e),
                error_code="EXECUTION_ERROR",
                retryable=True,
            )

    def _job_done(self, job_id: str, future: Future) -> None:
        """Handle job completion."""
        with self._lock:
            job = self._active_jobs.pop(job_id, None)
            self._active_futures.pop(job_id, None)

        if not job:
            return

        try:
            result = future.result()
            if result.success:
                job.result = result
                job.transition_to(JobStatus.SUCCEEDED, self.config.worker_id)
            else:
                job.result = result
                if result.retryable and job.can_retry():
                    job.retry_count += 1
                    delay = job.next_retry_delay_ms() / 1000
                    logger.info(f"Job {job_id} failed, scheduling retry {job.retry_count} in {delay}s")
                    time.sleep(delay)
                    self.queue.requeue(job)
                else:
                    job.transition_to(JobStatus.FAILED, self.config.worker_id, result.error or "Unknown error")
                    if job.retry_count >= job.config.max_retries:
                        job.transition_to(JobStatus.DEAD_LETTER, self.config.worker_id, "Max retries exceeded")

            # Persist final state
            job.persisted_at = datetime.now(timezone.utc)
            job.repository_version += 1
            if self.job_repository:
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(self.job_repository.save_job(job))
                except RuntimeError:
                    pass

        except Exception as e:
            logger.exception(f"Job {job_id} callback error")
            job.transition_to(JobStatus.FAILED, self.config.worker_id, f"Callback error: {e}")
            # Persist error state
            job.persisted_at = datetime.now(timezone.utc)
            job.repository_version += 1
            if self.job_repository:
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(self.job_repository.save_job(job))
                except RuntimeError:
                    pass

    def get_status(self) -> Dict[str, Any]:
        """Get worker status."""
        with self._lock:
            status = {
                "worker_id": self.config.worker_id,
                "running": self._running,
                "active_jobs": len(self._active_jobs),
                "max_concurrent": self.config.max_concurrent_jobs,
                "job_types": self.config.job_types,
                "active_job_ids": list(self._active_jobs.keys()),
            }
        
        # Add repository health
        if self.job_repository:
            try:
                import asyncio
                repo_healthy = asyncio.run(self.job_repository.health_check())
                status["repository_healthy"] = repo_healthy
            except Exception:
                status["repository_healthy"] = False
        
        return status


class WorkerPool:
    """Manages a pool of workers for horizontal scaling."""

    def __init__(self):
        self._workers: Dict[str, Worker] = {}
        self._lock = threading.RLock()

    def add_worker(self, worker: Worker) -> None:
        with self._lock:
            self._workers[worker.config.worker_id] = worker

    def remove_worker(self, worker_id: str, graceful: bool = True) -> bool:
        with self._lock:
            worker = self._workers.pop(worker_id, None)
            if worker:
                worker.stop(graceful)
                return True
            return False

    def get_worker(self, worker_id: str) -> Optional[Worker]:
        with self._lock:
            return self._workers.get(worker_id)

    def start_all(self) -> None:
        with self._lock:
            for worker in self._workers.values():
                worker.start()

    def stop_all(self, graceful: bool = True) -> None:
        with self._lock:
            for worker in self._workers.values():
                worker.stop(graceful)

    def get_total_status(self) -> Dict[str, Any]:
        with self._lock:
            total_active = sum(len(w._active_jobs) for w in self._workers.values())
            return {
                "worker_count": len(self._workers),
                "total_active_jobs": total_active,
                "workers": {wid: w.get_status() for wid, w in self._workers.items()},
            }


# Global worker pool
_worker_pool: Optional[WorkerPool] = None
_pool_lock = threading.Lock()


def get_worker_pool() -> WorkerPool:
    global _worker_pool
    with _pool_lock:
        if _worker_pool is None:
            _worker_pool = WorkerPool()
        return _worker_pool


__all__ = [
    "WorkerConfig",
    "JobExecutor",
    "Worker",
    "WorkerPool",
    "get_worker_pool",
]
"""
Execution Plane — workers, agents, providers, tools execute admitted jobs.

F-028: Missing Distributed Execution Model fix.
Separated from Control Plane for horizontal scaling.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timezone
import uuid
import threading
import logging

from swarm.enterprise.core.job.models import DurableJob, JobQueue, JobStatus, get_job_queue, JobResult
from swarm.enterprise.core.job.worker import Worker, WorkerConfig, JobExecutor, get_worker_pool
from swarm.enterprise.core.execution.context import ExecutionContext, get_current_context, set_current_context

logger = logging.getLogger(__name__)


class JobExecutorRegistry:
    """Registry of job type executors for the execution plane."""

    def __init__(self):
        self._executors: Dict[str, JobExecutor] = {}
        self._lock = threading.RLock()

    def register(self, job_type: str, executor: JobExecutor) -> None:
        with self._lock:
            self._executors[job_type] = executor

    def get(self, job_type: str) -> Optional[JobExecutor]:
        with self._lock:
            return self._executors.get(job_type)

    def list_types(self) -> List[str]:
        with self._lock:
            return list(self._executors.keys())


class ExecutionPlane:
    """
    Execution Plane — runs the actual work.
    
    Responsibilities:
    - Worker management
    - Job execution
    - Provider/model invocation
    - Tool invocation
    - State persistence
    - Metrics collection
    """

    def __init__(
        self,
        executor_registry: JobExecutorRegistry = None,
        worker_pool: Any = None,
        job_queue: JobQueue = None,
    ):
        self.executor_registry = executor_registry or JobExecutorRegistry()
        self.worker_pool = worker_pool or get_worker_pool()
        self.job_queue = job_queue or get_job_queue()
        self._lock = threading.RLock()
        self._metrics = {
            "jobs_executed": 0,
            "jobs_succeeded": 0,
            "jobs_failed": 0,
            "total_execution_time_ms": 0,
        }

    def register_executor(self, job_type: str, executor: JobExecutor) -> None:
        """Register an executor for a job type."""
        self.executor_registry.register(job_type, executor)

    def execute_job(self, job: DurableJob) -> JobResult:
        """
        Execute a single job synchronously (for testing/simple cases).
        In production, jobs are dequeued by workers.
        """
        executor = self.executor_registry.get(job.job_type)
        if not executor:
            return JobResult(
                success=False,
                error=f"No executor for job type: {job.job_type}",
                error_code="NO_EXECUTOR",
                retryable=False,
            )

        # Set execution context
        exec_context = ExecutionContext.create(
            tenant_id=job.config.tenant_id,
            principal_id=job.metadata.get("principal_id", "system"),
        )
        set_current_context(exec_context)

        try:
            # Validate
            if not executor.validate_payload(job.payload):
                return JobResult(
                    success=False,
                    error="Payload validation failed",
                    error_code="VALIDATION_FAILED",
                    retryable=False,
                )

            job.transition_to(JobStatus.RUNNING, "execution_plane")
            start_time = datetime.now(timezone.utc)

            result = executor.execute(job)

            job.result = result
            if result.success:
                job.transition_to(JobStatus.SUCCEEDED, "execution_plane")
                self._record_success(job)
            else:
                if result.retryable and job.can_retry():
                    job.retry_count += 1
                    job.transition_to(JobStatus.QUEUED, "execution_plane")
                else:
                    job.transition_to(JobStatus.FAILED, "execution_plane", result.error or "Unknown error")
                    if job.retry_count >= job.config.max_retries:
                        job.transition_to(JobStatus.DEAD_LETTER, "execution_plane", "Max retries exceeded")
                self._record_failure(job)

            return result

        except Exception as e:
            logger.exception(f"Job {job.job_id} execution error")
            return JobResult(
                success=False,
                error=str(e),
                error_code="EXECUTION_ERROR",
                retryable=True,
            )
        finally:
            # Clear context
            from swarm.enterprise.core.execution.context import clear_current_context
            clear_current_context()

    def _record_success(self, job: DurableJob) -> None:
        with self._lock:
            self._metrics["jobs_executed"] += 1
            self._metrics["jobs_succeeded"] += 1
            if job.result:
                self._metrics["total_execution_time_ms"] += job.result.execution_time_ms

    def _record_failure(self, job: DurableJob) -> None:
        with self._lock:
            self._metrics["jobs_failed"] += 1

    def get_metrics(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._metrics)

    def start_workers(self, worker_configs: List[WorkerConfig]) -> None:
        """Start workers for this execution plane."""
        for config in worker_configs:
            worker = Worker(
                config=config,
                executors=dict(self.executor_registry._executors),
                queue=self.job_queue,
            )
            self.worker_pool.add_worker(worker)
        self.worker_pool.start_all()

    def stop_workers(self, graceful: bool = True) -> None:
        """Stop all workers."""
        self.worker_pool.stop_all(graceful)


# Default executors for common job types
class SwarmProcessExecutor(JobExecutor):
    """Executor for swarm process jobs."""

    def __init__(self, swarm_master):
        self.swarm_master = swarm_master

    def validate_payload(self, payload: Dict[str, Any]) -> bool:
        return "question" in payload

    def execute(self, job: DurableJob) -> JobResult:
        from swarm.enterprise.core.auth import AuthorizationContext
        from swarm.enterprise.swarm_master import SwarmRequest

        payload = job.payload
        req = SwarmRequest(
            question=payload["question"],
            type=payload.get("type", "general"),
            context=payload.get("context", {}),
            require_human_review=payload.get("require_human_review", False),
            idempotency_key=job.config.idempotency_key,
            tenant_id=job.config.tenant_id,
            principal_id=job.metadata.get("principal_id", "system"),
        )

        auth_context = AuthorizationContext.for_system()
        result = self.swarm_master.process(req, authorization_context=auth_context)

        return JobResult(
            success=result.policy_decision == "approved",
            output=result.output,
            error=result.veto_reason if result.policy_decision != "approved" else None,
            retryable=False,
            metadata={
                "request_id": result.request_id,
                "execution_id": result.execution_id,
                "trace_id": result.trace_id,
                "policy_decision": result.policy_decision,
                "execution_state": result.execution_state,
                "final_outcome": result.final_outcome,
                "stages": result.stages,
            },
        )


# Global execution plane
_execution_plane: Optional["ExecutionPlane"] = None
_ep_lock = threading.Lock()


def get_execution_plane() -> ExecutionPlane:
    global _execution_plane
    with _ep_lock:
        if _execution_plane is None:
            _execution_plane = ExecutionPlane()
        return _execution_plane


__all__ = [
    "JobExecutorRegistry",
    "ExecutionPlane",
    "SwarmProcessExecutor",
    "get_execution_plane",
]
"""
Execution Plane — workers, agents, providers, tools execute admitted jobs.

F-028: Missing Distributed Execution Model fix.
Separated from Control Plane for horizontal scaling.
"""

import importlib
import threading
import logging
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timezone
import uuid

logger = logging.getLogger(__name__)


# =============================================================================
# Lazy Imports
# =============================================================================

class LazyImports:
    """Lazy loader for core modules to break static import chains."""
    
    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._module_cache: Dict[str, Any] = {}
    
    def _get_module(self, module_path: str):
        if module_path not in self._module_cache:
            self._module_cache[module_path] = importlib.import_module(module_path)
        return self._module_cache[module_path]
    
    def _get_attr(self, module_path: str, attr: str):
        module = self._get_module(module_path)
        return getattr(module, attr)
    
    # Core Services
    def get_durable_job(self):
        return self._get_attr("swarm.enterprise.core.job.models", "DurableJob")
    
    def get_job_queue(self):
        return self._get_attr("swarm.enterprise.core.job.models", "JobQueue")
    
    def get_job_status(self):
        return self._get_attr("swarm.enterprise.core.job.models", "JobStatus")
    
    def get_job_queue(self):
        return self._get_attr("swarm.enterprise.core.job.models", "get_job_queue")
    
    def get_job_result(self):
        return self._get_attr("swarm.enterprise.core.job.models", "JobResult")
    
    def get_worker(self):
        return self._get_attr("swarm.enterprise.core.job.worker", "Worker")
    
    def get_worker_config(self):
        return self._get_attr("swarm.enterprise.core.job.worker", "WorkerConfig")
    
    def get_job_executor(self):
        return self._get_attr("swarm.enterprise.core.job.worker", "JobExecutor")
    
    def get_worker_pool(self):
        return self._get_attr("swarm.enterprise.core.job.worker", "get_worker_pool")
    
    def get_execution_context(self):
        return self._get_attr("swarm.enterprise.core.execution.context", "ExecutionContext")
    
    def get_current_context(self):
        return self._get_attr("swarm.enterprise.core.execution.context", "get_current_context")
    
    def get_set_current_context(self):
        return self._get_attr("swarm.enterprise.core.execution.context", "set_current_context")


_lazy = LazyImports()


# =============================================================================
# Data Classes
# =============================================================================

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timezone
import uuid

@dataclass
class JobExecutorRegistry:
    """Registry of job type executors for the execution plane."""

    def __init__(self):
        self._executors: Dict[str, Any] = {}
        self._lock = threading.RLock()

    def register(self, job_type: str, executor: Any) -> None:
        with self._lock:
            self._executors[job_type] = executor

    def get(self, job_type: str) -> Optional[Any]:
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
        executor_registry: Any = None,
        worker_pool: Any = None,
        job_queue: Any = None,
    ):
        self.executor_registry = executor_registry or self._lazy.get_durable_job()  # Will be replaced
        self.worker_pool = worker_pool
        self.job_queue = job_queue
        self._lock = threading.RLock()
        self._metrics = {
            "jobs_executed": 0,
            "jobs_succeeded": 0,
            "jobs_failed": 0,
            "total_execution_time_ms": 0,
        }
        
        # Initialize lazy
        self._lazy = LazyImports()
        
        # Initialize real dependencies
        self.executor_registry = executor_registry or JobExecutorRegistry()
        self.worker_pool = worker_pool or self._lazy.get_worker_pool()()
        self.job_queue = job_queue or self._lazy.get_job_queue()()
        
        self._metrics = {
            "jobs_executed": 0,
            "jobs_succeeded": 0,
            "jobs_failed": 0,
            "total_execution_time_ms": 0,
        }

    def register_executor(self, job_type: str, executor: Any) -> None:
        """Register an executor for a job type."""
        self.executor_registry.register(job_type, executor)

    def execute_job(self, job: Any) -> Any:
        """
        Execute a single job synchronously (for testing/simple cases).
        In production, jobs are dequeued by workers.
        """
        executor = self.executor_registry.get(job.job_type)
        if not executor:
            raise ValueError(f"No executor registered for job type: {job.job_type}")
        
        result = executor.execute(job)
        self._metrics["jobs_executed"] += 1
        if result.success:
            self._metrics["jobs_succeeded"] += 1
        else:
            self._metrics["jobs_failed"] += 1
        self._metrics["total_execution_time_ms"] += result.duration_ms
        return result

    def submit_job(self, job: Any) -> str:
        """Submit job to queue for async processing."""
        self.job_queue.enqueue(job)
        return job.job_id

    def get_metrics(self) -> Dict[str, Any]:
        with self._lock:
            return self._metrics.copy()


def get_execution_plane(*args, **kwargs):
    """Factory function to create ExecutionPlane instance."""
    return ExecutionPlane(*args, **kwargs)

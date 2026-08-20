"""
Persistent Job Repository - Redis-backed implementation for DurableJob and WorkflowExecution.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

import orjson

from .models import DurableJob, JobPriority, JobStatus


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def uuidv7() -> str:
    return str(uuid4())


# =============================================================================
# Repository Protocol
# =============================================================================

class JobRepository(ABC):
    """Abstract repository for durable job persistence."""
    
    @abstractmethod
    async def save_job(self, job: DurableJob) -> None:
        """Save or update a job."""
        pass
    
    @abstractmethod
    async def get_job(self, job_id: str) -> Optional[DurableJob]:
        """Get a job by ID."""
        pass
    
    @abstractmethod
    async def delete_job(self, job_id: str) -> bool:
        """Delete a job. Returns True if deleted."""
        pass
    
    @abstractmethod
    async def list_jobs(
        self,
        tenant_id: Optional[str] = None,
        status: Optional[JobStatus] = None,
        priority: Optional[JobPriority] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[DurableJob]:
        """List jobs with filters."""
        pass
    
    @abstractmethod
    async def get_pending_jobs(
        self,
        tenant_id: Optional[str] = None,
        priorities: Optional[List[JobPriority]] = None,
        limit: int = 100,
    ) -> List[DurableJob]:
        """Get pending jobs ordered by priority and creation time."""
        pass
    
    @abstractmethod
    async def save_workflow(self, workflow: "WorkflowExecution") -> None:
        """Save a workflow execution."""
        pass
    
    @abstractmethod
    async def get_workflow(self, workflow_id: str) -> Optional["WorkflowExecution"]:
        """Get a workflow execution by ID."""
        pass
    
    @abstractmethod
    async def list_workflows(
        self,
        tenant_id: Optional[str] = None,
        limit: int = 100,
    ) -> List["WorkflowExecution"]:
        """List workflow executions."""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check repository health."""
        pass


# =============================================================================
# Redis Implementation
# =============================================================================

@dataclass
class RedisJobRepositoryConfig:
    """Configuration for RedisJobRepository."""
    redis_url: str = "redis://localhost:6379/0"
    key_prefix: str = "swarm:jobs"
    default_ttl_seconds: int = 86400 * 30  # 30 days
    max_connections: int = 50
    socket_timeout: float = 5.0
    socket_connect_timeout: float = 5.0


class RedisJobRepository(JobRepository):
    """Redis-backed job repository with Lua scripts for atomic operations."""
    
    def __init__(self, config: Optional[RedisJobRepositoryConfig] = None):
        self.config = config or RedisJobRepositoryConfig()
        self._redis: Optional[Any] = None
        self._scripts_loaded = False
    
    async def _get_redis(self):
        """Lazy initialization of Redis connection."""
        if self._redis is None:
            import redis.asyncio as redis
            self._redis = redis.from_url(
                self.config.redis_url,
                max_connections=self.config.max_connections,
                socket_timeout=self.config.socket_timeout,
                socket_connect_timeout=self.config.socket_connect_timeout,
                decode_responses=False,
            )
            await self._load_scripts()
        return self._redis
    
    async def _load_scripts(self):
        """Load Lua scripts for atomic operations."""
        if self._scripts_loaded:
            return
        
        redis = await self._get_redis()
        
        # Atomic job claim script (for worker dequeue)
        self._claim_script = redis.register_script("""
            local job_key = KEYS[1]
            local index_key = KEYS[2]
            local worker_id = ARGV[1]
            local now = ARGV[2]
            local ttl = ARGV[3]
            
            local job_data = redis.call('GET', job_key)
            if not job_data then
                return nil
            end
            
            local job = cjson.decode(job_data)
            if job.status ~= 'pending' then
                return nil
            end
            
            job.status = 'running'
            job.worker_id = worker_id
            job.started_at = now
            job.updated_at = now
            job.last_heartbeat = now
            job.heartbeat_count = 0
            
            redis.call('SET', job_key, cjson.encode(job), 'EX', ttl)
            redis.call('ZREM', index_key, job_key)
            redis.call('ZADD', index_key .. ':running', now, job_key)
            
            return cjson.encode(job)
        """)
        
        # Atomic job complete script
        self._complete_script = redis.register_script("""
            local job_key = KEYS[1]
            local running_index = KEYS[2]
            local completed_index = KEYS[3]
            local status = ARGV[1]
            local result = ARGV[2]
            local error = ARGV[3]
            local now = ARGV[4]
            local ttl = ARGV[5]
            
            local job_data = redis.call('GET', job_key)
            if not job_data then
                return nil
            end
            
            local job = cjson.decode(job_data)
            job.status = status
            job.completed_at = now
            job.updated_at = now
            if result then
                job.result = result
            end
            if error then
                job.error = error
            end
            
            redis.call('SET', job_key, cjson.encode(job), 'EX', ttl)
            redis.call('ZREM', running_index, job_key)
            redis.call('ZADD', completed_index, now, job_key)
            
            return cjson.encode(job)
        """)
        
        # Atomic heartbeat script
        self._heartbeat_script = redis.register_script("""
            local job_key = KEYS[1]
            local worker_id = ARGV[1]
            local now = ARGV[2]
            local ttl = ARGV[3]
            
            local job_data = redis.call('GET', job_key)
            if not job_data then
                return 0
            end
            
            local job = cjson.decode(job_data)
            if job.worker_id ~= worker_id then
                return -1  -- Not owner
            end
            if job.status ~= 'running' then
                return -2  -- Not running
            end
            
            job.last_heartbeat = now
            job.heartbeat_count = job.heartbeat_count + 1
            job.updated_at = now
            
            redis.call('SET', job_key, cjson.encode(job), 'EX', ttl)
            return 1
        """)
        
        self._scripts_loaded = True
    
    def _job_key(self, job_id: str) -> str:
        return f"{self.config.key_prefix}:job:{job_id}"
    
    def _index_key(self, tenant_id: Optional[str] = None) -> str:
        if tenant_id:
            return f"{self.config.key_prefix}:index:{tenant_id}"
        return f"{self.config.key_prefix}:index:global"
    
    def _status_index_key(self, tenant_id: Optional[str], status: JobStatus) -> str:
        if tenant_id:
            return f"{self.config.key_prefix}:index:{tenant_id}:{status.value}"
        return f"{self.config.key_prefix}:index:global:{status.value}"
    
    def _workflow_key(self, workflow_id: str) -> str:
        return f"{self.config.key_prefix}:workflow:{workflow_id}"
    
    def _workflow_index_key(self, tenant_id: Optional[str] = None) -> str:
        if tenant_id:
            return f"{self.config.key_prefix}:workflow_index:{tenant_id}"
        return f"{self.config.key_prefix}:workflow_index:global"
    
    async def save_job(self, job: DurableJob) -> None:
        redis = await self._get_redis()
        job.updated_at = now_utc()
        
        # Serialize job
        job_data = job.to_dict()
        serialized = orjson.dumps(job_data).decode()
        
        key = self._job_key(job.job_id)
        ttl = self.config.default_ttl_seconds
        
        # Use pipeline for atomicity
        pipe = redis.pipeline()
        pipe.set(key, serialized, ex=ttl if ttl > 0 else None)
        
        # Update indexes
        index_key = self._index_key(job.tenant_id)
        pipe.zadd(index_key, {key: job.created_at.timestamp()})
        
        status_index = self._status_index_key(job.tenant_id, job.status)
        pipe.zadd(status_index, {key: job.updated_at.timestamp()})
        
        # If pending, add to priority queue
        if job.status == JobStatus.PENDING:
            priority_key = f"{self.config.key_prefix}:queue:{job.tenant_id or 'global'}:{job.priority.value}"
            pipe.zadd(priority_key, {key: job.created_at.timestamp()})
        
        await pipe.execute()
    
    async def get_job(self, job_id: str) -> Optional[DurableJob]:
        redis = await self._get_redis()
        key = self._job_key(job_id)
        data = await redis.get(key)
        if not data:
            return None
        return DurableJob.from_dict(orjson.loads(data))
    
    async def delete_job(self, job_id: str) -> bool:
        redis = await self._get_redis()
        key = self._job_key(job_id)
        
        # Get job first to know indexes
        job = await self.get_job(job_id)
        if not job:
            return False
        
        pipe = redis.pipeline()
        pipe.delete(key)
        pipe.zrem(self._index_key(job.tenant_id), key)
        pipe.zrem(self._status_index_key(job.tenant_id, job.status), key)
        if job.status == JobStatus.PENDING:
            priority_key = f"{self.config.key_prefix}:queue:{job.tenant_id or 'global'}:{job.priority.value}"
            pipe.zrem(priority_key, key)
        await pipe.execute()
        return True
    
    async def list_jobs(
        self,
        tenant_id: Optional[str] = None,
        status: Optional[JobStatus] = None,
        priority: Optional[JobPriority] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[DurableJob]:
        redis = await self._get_redis()
        
        if status:
            index_key = self._status_index_key(tenant_id, status)
        else:
            index_key = self._index_key(tenant_id)
        
        keys = await redis.zrevrange(index_key, offset, offset + limit - 1)
        if not keys:
            return []
        
        pipe = redis.pipeline()
        for key in keys:
            pipe.get(key)
        results = await pipe.execute()
        
        jobs = []
        for data in results:
            if data:
                jobs.append(DurableJob.from_dict(orjson.loads(data)))
        
        if priority:
            jobs = [j for j in jobs if j.priority == priority]
        
        return jobs
    
    async def get_pending_jobs(
        self,
        tenant_id: Optional[str] = None,
        priorities: Optional[List[JobPriority]] = None,
        limit: int = 100,
    ) -> List[DurableJob]:
        redis = await self._get_redis()
        
        if priorities is None:
            priorities = [JobPriority.CRITICAL, JobPriority.HIGH, JobPriority.NORMAL, JobPriority.LOW]
        
        all_keys = []
        for priority in priorities:
            priority_key = f"{self.config.key_prefix}:queue:{tenant_id or 'global'}:{priority.value}"
            keys = await redis.zrange(priority_key, 0, limit - 1)
            all_keys.extend(keys)
            if len(all_keys) >= limit:
                break
        
        if not all_keys:
            return []
        
        pipe = redis.pipeline()
        for key in all_keys[:limit]:
            pipe.get(key)
        results = await pipe.execute()
        
        jobs = []
        for data in results:
            if data:
                jobs.append(DurableJob.from_dict(orjson.loads(data)))
        
        return jobs
    
    async def claim_job(self, job_id: str, worker_id: str) -> Optional[DurableJob]:
        """Atomically claim a pending job for a worker."""
        redis = await self._get_redis()
        key = self._job_key(job_id)
        index_key = self._index_key()
        running_index = f"{self.config.key_prefix}:index:global:running"
        now = now_utc().isoformat()
        ttl = self.config.default_ttl_seconds
        
        result = await self._claim_script(
            keys=[key, index_key],
            args=[worker_id, now, str(ttl)],
        )
        if result:
            return DurableJob.from_dict(orjson.loads(result))
        return None
    
    async def complete_job(
        self,
        job_id: str,
        status: JobStatus,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> Optional[DurableJob]:
        """Atomically complete a running job."""
        redis = await self._get_redis()
        key = self._job_key(job_id)
        running_index = f"{self.config.key_prefix}:index:global:running"
        completed_index = f"{self.config.key_prefix}:index:global:{status.value}"
        now = now_utc().isoformat()
        ttl = self.config.default_ttl_seconds
        
        result_json = orjson.dumps(result).decode() if result else ""
        error_json = orjson.dumps(error).decode() if error else ""
        
        result_data = await self._complete_script(
            keys=[key, running_index, completed_index],
            args=[status.value, result_json, error_json, now, str(ttl)],
        )
        if result_data:
            return DurableJob.from_dict(orjson.loads(result_data))
        return None
    
    async def heartbeat_job(self, job_id: str, worker_id: str) -> int:
        """Update job heartbeat. Returns 1=success, 0=not found, -1=not owner, -2=not running."""
        redis = await self._get_redis()
        key = self._job_key(job_id)
        now = now_utc().isoformat()
        ttl = self.config.default_ttl_seconds
        
        return await self._heartbeat_script(
            keys=[key],
            args=[worker_id, now, str(ttl)],
        )
    
    async def get_stale_jobs(
        self,
        max_heartbeat_age_seconds: int = 60,
        tenant_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[DurableJob]:
        """Find jobs that haven't sent heartbeat in time."""
        redis = await self._get_redis()
        running_index = f"{self.config.key_prefix}:index:global:running"
        cutoff = (datetime.now(timezone.utc).timestamp() - max_heartbeat_age_seconds)
        
        keys = await redis.zrangebyscore(running_index, 0, cutoff, start=0, num=limit)
        if not keys:
            return []
        
        pipe = redis.pipeline()
        for key in keys:
            pipe.get(key)
        results = await pipe.execute()
        
        jobs = []
        for data in results:
            if data:
                job = DurableJob.from_dict(orjson.loads(data))
                if tenant_id is None or job.tenant_id == tenant_id:
                    jobs.append(job)
        
        return jobs
    
    async def save_workflow(self, workflow: "WorkflowExecution") -> None:
        redis = await self._get_redis()
        
        workflow_data = {
            "workflow_id": workflow.workflow_id,
            "workflow_type": workflow.workflow_type,
            "status": workflow.status.value,
            "steps": [
                {
                    "step_id": s.step_id,
                    "name": s.name,
                    "execute_fn_name": s.execute_fn.__name__ if s.execute_fn else None,
                    "depends_on": s.depends_on,
                    "requires": s.requires,
                    "provides": s.provides,
                    "timeout_ms": s.timeout_ms,
                    "retry_policy": s.retry_policy.value,
                    "max_retries": s.max_retries,
                    "compensation_fn_name": s.compensation_fn.__name__ if s.compensation_fn else None,
                    "status": s.status.value,
                    "started_at": s.started_at.isoformat() if s.started_at else None,
                    "completed_at": s.completed_at.isoformat() if s.completed_at else None,
                    "result": s.result,
                    "error": s.error,
                    "retry_count": s.retry_count,
                }
                for s in workflow.steps
            ],
            "created_at": workflow.created_at.isoformat(),
            "updated_at": now_utc().isoformat(),
            "tenant_id": workflow.tenant_id,
            "context": workflow.context,
        }
        
        key = self._workflow_key(workflow.workflow_id)
        serialized = orjson.dumps(workflow_data).decode()
        ttl = self.config.default_ttl_seconds
        
        pipe = redis.pipeline()
        pipe.set(key, serialized, ex=ttl if ttl > 0 else None)
        pipe.zadd(self._workflow_index_key(workflow.tenant_id), {key: workflow.created_at.timestamp()})
        await pipe.execute()
    
    async def get_workflow(self, workflow_id: str) -> Optional["WorkflowExecution"]:
        redis = await self._get_redis()
        key = self._workflow_key(workflow_id)
        data = await redis.get(key)
        if not data:
            return None
        
        from .compensation import WorkflowExecution, WorkflowStep, WorkflowStepStatus
        wf_data = orjson.loads(data)
        
        steps = []
        for s in wf_data["steps"]:
            steps.append(WorkflowStep(
                step_id=s["step_id"],
                name=s["name"],
                execute_fn=None,  # Can't serialize functions
                depends_on=s["depends_on"],
                requires=s["requires"],
                provides=s["provides"],
                timeout_ms=s["timeout_ms"],
                retry_policy=s["retry_policy"],
                max_retries=s["max_retries"],
                compensation_fn=None,
                status=WorkflowStepStatus(s["status"]),
                started_at=datetime.fromisoformat(s["started_at"]) if s["started_at"] else None,
                completed_at=datetime.fromisoformat(s["completed_at"]) if s["completed_at"] else None,
                result=s["result"],
                error=s["error"],
                retry_count=s["retry_count"],
            ))
        
        return WorkflowExecution(
            workflow_id=wf_data["workflow_id"],
            workflow_type=wf_data["workflow_type"],
            status=WorkflowStepStatus(wf_data["status"]),
            steps=steps,
            created_at=datetime.fromisoformat(wf_data["created_at"]),
            tenant_id=wf_data["tenant_id"],
            context=wf_data["context"],
        )
    
    async def list_workflows(
        self,
        tenant_id: Optional[str] = None,
        limit: int = 100,
    ) -> List["WorkflowExecution"]:
        redis = await self._get_redis()
        index_key = self._workflow_index_key(tenant_id)
        keys = await redis.zrevrange(index_key, 0, limit - 1)
        
        workflows = []
        for key in keys:
            data = await redis.get(key)
            if data:
                wf = await self.get_workflow(orjson.loads(data)["workflow_id"])
                if wf:
                    workflows.append(wf)
        return workflows
    
    async def health_check(self) -> bool:
        try:
            redis = await self._get_redis()
            await redis.ping()
            return True
        except Exception:
            return False
    
    async def close(self):
        if self._redis:
            await self._redis.close()
            self._redis = None


# =============================================================================
# In-Memory Implementation (for testing)
# =============================================================================

class InMemoryJobRepository(JobRepository):
    """In-memory job repository for testing."""
    
    def __init__(self):
        self._jobs: Dict[str, DurableJob] = {}
        self._workflows: Dict[str, "WorkflowExecution"] = {}
    
    async def save_job(self, job: DurableJob) -> None:
        job.updated_at = now_utc()
        self._jobs[job.job_id] = job
    
    async def get_job(self, job_id: str) -> Optional[DurableJob]:
        return self._jobs.get(job_id)
    
    async def delete_job(self, job_id: str) -> bool:
        if job_id in self._jobs:
            del self._jobs[job_id]
            return True
        return False
    
    async def list_jobs(
        self,
        tenant_id: Optional[str] = None,
        status: Optional[JobStatus] = None,
        priority: Optional[JobPriority] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[DurableJob]:
        jobs = list(self._jobs.values())
        if tenant_id:
            jobs = [j for j in jobs if j.tenant_id == tenant_id]
        if status:
            jobs = [j for j in jobs if j.status == status]
        if priority:
            jobs = [j for j in jobs if j.priority == priority]
        jobs.sort(key=lambda j: j.created_at, reverse=True)
        return jobs[offset:offset + limit]
    
    async def get_pending_jobs(
        self,
        tenant_id: Optional[str] = None,
        priorities: Optional[List[JobPriority]] = None,
        limit: int = 100,
    ) -> List[DurableJob]:
        jobs = [j for j in self._jobs.values() if j.status == JobStatus.PENDING]
        if tenant_id:
            jobs = [j for j in jobs if j.tenant_id == tenant_id]
        if priorities:
            jobs = [j for j in jobs if j.priority in priorities]
        jobs.sort(key=lambda j: (priorities.index(j.priority) if priorities else 0, j.created_at))
        return jobs[:limit]
    
    async def save_workflow(self, workflow: "WorkflowExecution") -> None:
        self._workflows[workflow.workflow_id] = workflow
    
    async def get_workflow(self, workflow_id: str) -> Optional["WorkflowExecution"]:
        return self._workflows.get(workflow_id)
    
    async def list_workflows(
        self,
        tenant_id: Optional[str] = None,
        limit: int = 100,
    ) -> List["WorkflowExecution"]:
        workflows = list(self._workflows.values())
        if tenant_id:
            workflows = [w for w in workflows if w.tenant_id == tenant_id]
        workflows.sort(key=lambda w: w.created_at, reverse=True)
        return workflows[:limit]
    
    async def health_check(self) -> bool:
        return True


# =============================================================================
# Factory
# =============================================================================

def create_job_repository(
    backend: str = "memory",
    **kwargs,
) -> JobRepository:
    """Create a job repository instance."""
    if backend == "redis":
        config = RedisJobRepositoryConfig(**kwargs)
        return RedisJobRepository(config)
    elif backend == "memory":
        return InMemoryJobRepository()
    else:
        raise ValueError(f"Unknown backend: {backend}")

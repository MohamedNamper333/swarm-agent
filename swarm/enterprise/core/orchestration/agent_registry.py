"""
Agent Registry - Dynamic agent registration, discovery, and health monitoring.
"""

import threading
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# Agent Models
# =============================================================================

class AgentStatus(str, Enum):
    """Agent lifecycle status."""
    REGISTERING = "registering"
    STARTING = "starting"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    STOPPING = "stopping"
    STOPPED = "stopped"
    UNHEALTHY = "unhealthy"
    ERROR = "error"


class AgentCapability(str, Enum):
    """Standard agent capabilities."""
    CODE_GENERATION = "code_generation"
    CODE_REVIEW = "code_review"
    DESIGN = "design"
    RESEARCH = "research"
    DATA_ANALYSIS = "data_analysis"
    TEXT_GENERATION = "text_generation"
    TRANSLATION = "translation"
    SUMMARIZATION = "summarization"
    QUESTION_ANSWERING = "question_answering"
    PLANNING = "planning"
    ORCHESTRATION = "orchestration"
    SAFETY_CHECK = "safety_check"
    KNOWLEDGE_RETRIEVAL = "knowledge_retrieval"


@dataclass
class AgentMetadata:
    """Agent registration metadata."""
    agent_id: str
    agent_type: str
    name: str
    description: str
    capabilities: List[AgentCapability]
    department: str
    version: str = "1.0.0"
    config: Dict[str, Any] = field(default_factory=dict)
    tags: Set[str] = field(default_factory=set)
    registered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class AgentInstance:
    """Running agent instance."""
    instance_id: str
    metadata: AgentMetadata
    status: AgentStatus = AgentStatus.REGISTERING
    started_at: Optional[datetime] = None
    last_heartbeat: Optional[datetime] = None
    heartbeat_interval_sec: int = 30
    current_load: float = 0.0  # 0.0 - 1.0
    max_concurrent_tasks: int = 1
    active_task_count: int = 0
    total_tasks_processed: int = 0
    total_tasks_failed: int = 0
    error_count: int = 0
    last_error: Optional[str] = None
    metadata_extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentHealth:
    """Agent health check result."""
    agent_id: str
    instance_id: str
    status: AgentStatus
    is_healthy: bool
    latency_ms: Optional[float] = None
    details: Dict[str, Any] = field(default_factory=dict)
    checked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# =============================================================================
# Agent Executor Interface
# =============================================================================

class AgentExecutor(ABC):
    """Base class for agent executors."""
    
    @abstractmethod
    def execute(self, task: "AgentTask") -> "AgentTaskResult":
        """Execute a task synchronously."""
        pass
    
    @abstractmethod
    async def execute_async(self, task: "AgentTask") -> "AgentTaskResult":
        """Execute a task asynchronously."""
        pass
    
    @abstractmethod
    def health_check(self) -> AgentHealth:
        """Perform health check."""
        pass
    
    @abstractmethod
    def shutdown(self, graceful: bool = True) -> None:
        """Shutdown the executor."""
        pass


@dataclass
class AgentTask:
    """Task to be executed by an agent."""
    task_id: str
    agent_type: str
    capability: AgentCapability
    payload: Dict[str, Any]
    context: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0  # Higher = more urgent
    timeout_seconds: int = 300
    retry_count: int = 0
    max_retries: int = 3
    tenant_id: str = "default"
    trace_id: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class AgentTaskResult:
    """Result of agent task execution."""
    task_id: str
    success: bool
    output: Any = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    execution_time_ms: int = 0
    agent_instance_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Agent Registry
# =============================================================================

class AgentRegistry:
    """
    Central registry for agent discovery and lifecycle management.
    
    Features:
    - Dynamic agent registration/deregistration
    - Capability-based discovery
    - Health monitoring with heartbeats
    - Load balancing across instances
    - Tenant isolation
    """
    
    def __init__(
        self,
        heartbeat_timeout_sec: int = 90,
        cleanup_interval_sec: int = 60,
    ):
        self.heartbeat_timeout_sec = heartbeat_timeout_sec
        self.cleanup_interval_sec = cleanup_interval_sec
        
        # Agent metadata (type -> metadata)
        self._agent_types: Dict[str, AgentMetadata] = {}
        
        # Running instances (instance_id -> instance)
        self._instances: Dict[str, AgentInstance] = {}
        
        # Type -> instance_ids mapping
        self._type_instances: Dict[str, Set[str]] = {}
        
        # Tenant -> instance_ids mapping
        self._tenant_instances: Dict[str, Set[str]] = {}
        
        # Capability -> instance_ids mapping
        self._capability_instances: Dict[AgentCapability, Set[str]] = {}
        
        # Executors (instance_id -> executor)
        self._executors: Dict[str, AgentExecutor] = {}
        
        # Task queue per capability
        self._task_queues: Dict[AgentCapability, List[AgentTask]] = {}
        
        self._lock = threading.RLock()
        self._cleanup_running = False
        self._cleanup_thread: Optional[threading.Thread] = None
        self._shutdown_event = threading.Event()
    
    def register_agent_type(
        self,
        agent_type: str,
        name: str,
        description: str,
        capabilities: List[AgentCapability],
        department: str,
        version: str = "1.0.0",
        config: Optional[Dict[str, Any]] = None,
        tags: Optional[Set[str]] = None,
    ) -> AgentMetadata:
        """Register an agent type (template)."""
        with self._lock:
            if agent_type in self._agent_types:
                raise ValueError(f"Agent type {agent_type} already registered")
            
            metadata = AgentMetadata(
                agent_id=str(uuid.uuid4()),
                agent_type=agent_type,
                name=name,
                description=description,
                capabilities=capabilities,
                department=department,
                version=version,
                config=config or {},
                tags=tags or set(),
            )
            
            self._agent_types[agent_type] = metadata
            self._type_instances[agent_type] = set()
            
            for cap in capabilities:
                if cap not in self._capability_instances:
                    self._capability_instances[cap] = set()
            
            logger.info(f"Registered agent type: {agent_type} ({name})")
            return metadata
    
    def register_instance(
        self,
        agent_type: str,
        instance_id: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        tenant_id: str = "default",
        max_concurrent_tasks: int = 1,
        heartbeat_interval_sec: int = 30,
        executor: Optional[AgentExecutor] = None,
    ) -> AgentInstance:
        """Register a running agent instance."""
        with self._lock:
            if agent_type not in self._agent_types:
                raise ValueError(f"Agent type {agent_type} not registered")
            
            instance_id = instance_id or f"{agent_type}-{uuid.uuid4().hex[:8]}"
            
            if instance_id in self._instances:
                raise ValueError(f"Instance {instance_id} already exists")
            
            metadata = self._agent_types[agent_type]
            instance = AgentInstance(
                instance_id=instance_id,
                metadata=metadata,
                status=AgentStatus.STARTING,
                heartbeat_interval_sec=heartbeat_interval_sec,
                max_concurrent_tasks=max_concurrent_tasks,
                metadata_extra=config or {},
            )
            
            self._instances[instance_id] = instance
            self._type_instances[agent_type].add(instance_id)
            
            if tenant_id not in self._tenant_instances:
                self._tenant_instances[tenant_id] = set()
            self._tenant_instances[tenant_id].add(instance_id)
            
            for cap in metadata.capabilities:
                self._capability_instances[cap].add(instance_id)
            
            if executor:
                self._executors[instance_id] = executor
            
            logger.info(f"Registered agent instance: {instance_id} ({agent_type})")
            return instance
    
    def start_instance(self, instance_id: str) -> bool:
        """Mark instance as started."""
        with self._lock:
            instance = self._instances.get(instance_id)
            if not instance:
                return False
            
            instance.status = AgentStatus.HEALTHY
            instance.started_at = datetime.now(timezone.utc)
            instance.last_heartbeat = datetime.now(timezone.utc)
            logger.info(f"Agent instance started: {instance_id}")
            return True
    
    def heartbeat(
        self,
        instance_id: str,
        current_load: float = 0.0,
        active_task_count: int = 0,
    ) -> bool:
        """Update instance heartbeat."""
        with self._lock:
            instance = self._instances.get(instance_id)
            if not instance:
                return False
            
            instance.last_heartbeat = datetime.now(timezone.utc)
            instance.current_load = max(0.0, min(1.0, current_load))
            instance.active_task_count = active_task_count
            
            # Update status based on load
            if instance.current_load > 0.9:
                instance.status = AgentStatus.DEGRADED
            elif instance.status == AgentStatus.DEGRADED and instance.current_load < 0.7:
                instance.status = AgentStatus.HEALTHY
            
            return True
    
    def record_task_result(
        self,
        instance_id: str,
        success: bool,
        execution_time_ms: int = 0,
    ) -> None:
        """Record task execution result for statistics."""
        with self._lock:
            instance = self._instances.get(instance_id)
            if instance:
                instance.total_tasks_processed += 1
                if not success:
                    instance.total_tasks_failed += 1
                    instance.error_count += 1
    
    def stop_instance(self, instance_id: str, graceful: bool = True) -> bool:
        """Stop an agent instance."""
        with self._lock:
            instance = self._instances.get(instance_id)
            if not instance:
                return False
            
            instance.status = AgentStatus.STOPPING
            
            # Shutdown executor
            executor = self._executors.get(instance_id)
            if executor:
                try:
                    executor.shutdown(graceful)
                except Exception as e:
                    logger.error(f"Error shutting down executor for {instance_id}: {e}")
            
            instance.status = AgentStatus.STOPPED
            
            # Remove from indexes
            self._type_instances[instance.metadata.agent_type].discard(instance_id)
            self._tenant_instances.get(instance.metadata_extra.get("tenant_id", "default"), set()).discard(instance_id)
            for cap in instance.metadata.capabilities:
                self._capability_instances[cap].discard(instance_id)
            
            if instance_id in self._executors:
                del self._executors[instance_id]
            
            logger.info(f"Agent instance stopped: {instance_id}")
            return True
    
    def deregister_instance(self, instance_id: str) -> bool:
        """Completely remove an instance."""
        with self._lock:
            if instance_id not in self._instances:
                return False
            
            instance = self._instances[instance_id]
            
            # Remove from all indexes
            self._type_instances[instance.metadata.agent_type].discard(instance_id)
            tenant_id = instance.metadata_extra.get("tenant_id", "default")
            self._tenant_instances.get(tenant_id, set()).discard(instance_id)
            for cap in instance.metadata.capabilities:
                self._capability_instances[cap].discard(instance_id)
            
            if instance_id in self._executors:
                del self._executors[instance_id]
            
            del self._instances[instance_id]
            logger.info(f"Agent instance deregistered: {instance_id}")
            return True
    
    def get_instance(self, instance_id: str) -> Optional[AgentInstance]:
        """Get instance by ID."""
        with self._lock:
            return self._instances.get(instance_id)
    
    def list_instances(
        self,
        agent_type: Optional[str] = None,
        tenant_id: Optional[str] = None,
        status: Optional[AgentStatus] = None,
        capability: Optional[AgentCapability] = None,
    ) -> List[AgentInstance]:
        """List instances with filters."""
        with self._lock:
            instances = list(self._instances.values())
            
            if agent_type:
                instances = [i for i in instances if i.metadata.agent_type == agent_type]
            if tenant_id:
                instances = [i for i in instances if i.metadata_extra.get("tenant_id") == tenant_id]
            if status:
                instances = [i for i in instances if i.status == status]
            if capability:
                instances = [i for i in instances if capability in i.metadata.capabilities]
            
            return instances
    
    def find_available_instance(
        self,
        capability: AgentCapability,
        tenant_id: Optional[str] = None,
        preferred_instance_id: Optional[str] = None,
    ) -> Optional[AgentInstance]:
        """Find best available instance for a capability."""
        with self._lock:
            candidates = self._capability_instances.get(capability, set())
            
            if not candidates:
                return None
            
            # Filter by tenant
            if tenant_id:
                tenant_instances = self._tenant_instances.get(tenant_id, set())
                candidates = candidates & tenant_instances
            
            # Filter healthy instances
            healthy = [
                self._instances[iid] for iid in candidates
                if iid in self._instances and
                self._instances[iid].status in (AgentStatus.HEALTHY, AgentStatus.DEGRADED) and
                self._instances[iid].active_task_count < self._instances[iid].max_concurrent_tasks
            ]
            
            if not healthy:
                return None
            
            # Prefer specific instance
            if preferred_instance_id:
                for inst in healthy:
                    if inst.instance_id == preferred_instance_id:
                        return inst
            
            # Return least loaded
            return min(healthy, key=lambda i: (i.current_load, i.active_task_count))
    
    def health_check(self, instance_id: str) -> Optional[AgentHealth]:
        """Perform health check on an instance."""
        with self._lock:
            instance = self._instances.get(instance_id)
            if not instance:
                return None
            
            executor = self._executors.get(instance_id)
            
            if executor:
                return executor.health_check()
            
            # Basic health check based on heartbeat
            now = datetime.now(timezone.utc)
            is_healthy = False
            latency_ms = None
            
            if instance.last_heartbeat:
                age = (now - instance.last_heartbeat).total_seconds()
                is_healthy = age < self.heartbeat_timeout_sec and instance.status in (AgentStatus.HEALTHY, AgentStatus.DEGRADED)
            
            return AgentHealth(
                agent_id=instance.metadata.agent_type,
                instance_id=instance_id,
                status=instance.status,
                is_healthy=is_healthy,
                latency_ms=latency_ms,
                details={
                    "current_load": instance.current_load,
                    "active_tasks": instance.active_task_count,
                    "total_processed": instance.total_tasks_processed,
                    "total_failed": instance.total_tasks_failed,
                    "last_heartbeat_age_sec": age if instance.last_heartbeat else None,
                },
            )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        with self._lock:
            by_type: Dict[str, int] = {}
            by_status: Dict[str, int] = {}
            by_tenant: Dict[str, int] = {}
            
            for inst in self._instances.values():
                by_type[inst.metadata.agent_type] = by_type.get(inst.metadata.agent_type, 0) + 1
                by_status[inst.status.value] = by_status.get(inst.status.value, 0) + 1
                tenant = inst.metadata_extra.get("tenant_id", "default")
                by_tenant[tenant] = by_tenant.get(tenant, 0) + 1
            
            return {
                "total_types": len(self._agent_types),
                "total_instances": len(self._instances),
                "by_type": by_type,
                "by_status": by_status,
                "by_tenant": by_tenant,
                "capabilities": list(self._capability_instances.keys()),
            }
    
    def start_cleanup(self) -> None:
        """Start background cleanup of stale instances."""
        if self._cleanup_running:
            return
        
        self._cleanup_running = True
        self._shutdown_event.clear()
        
        def cleanup_loop():
            logger.info("Agent registry cleanup started")
            
            while self._cleanup_running and not self._shutdown_event.is_set():
                try:
                    self._cleanup_stale_instances()
                except Exception as e:
                    logger.error(f"Agent registry cleanup error: {e}")
                
                self._shutdown_event.wait(timeout=self.cleanup_interval_sec)
            
            logger.info("Agent registry cleanup stopped")
        
        self._cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)
        self._cleanup_thread.start()
    
    def stop_cleanup(self) -> None:
        """Stop background cleanup."""
        if not self._cleanup_running:
            return
        
        self._cleanup_running = False
        self._shutdown_event.set()
        
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=5)
    
    def _cleanup_stale_instances(self) -> None:
        """Remove instances that haven't sent heartbeat."""
        with self._lock:
            now = datetime.now(timezone.utc)
            stale_ids = []
            
            for instance_id, instance in self._instances.items():
                if instance.status in (AgentStatus.STOPPED, AgentStatus.STOPPING):
                    continue
                
                if instance.last_heartbeat:
                    age = (now - instance.last_heartbeat).total_seconds()
                    if age > self.heartbeat_timeout_sec:
                        stale_ids.append(instance_id)
            
            for instance_id in stale_ids:
                logger.warning(f"Removing stale agent instance: {instance_id}")
                instance = self._instances[instance_id]
                instance.status = AgentStatus.UNHEALTHY
                self.stop_instance(instance_id, graceful=False)
    
    def shutdown(self) -> None:
        """Shutdown registry and all instances."""
        self.stop_cleanup()
        
        with self._lock:
            for instance_id in list(self._instances.keys()):
                self.stop_instance(instance_id, graceful=True)
            self._instances.clear()
            self._type_instances.clear()
            self._tenant_instances.clear()
            self._capability_instances.clear()
            self._executors.clear()


# =============================================================================
# Default In-Memory Executor
# =============================================================================

class InMemoryAgentExecutor(AgentExecutor):
    """Simple in-memory agent executor for testing."""
    
    def __init__(self, agent_type: str, handler: Callable[[AgentTask], AgentTaskResult]):
        self.agent_type = agent_type
        self.handler = handler
        self._healthy = True
    
    def execute(self, task: AgentTask) -> AgentTaskResult:
        import time
        start = time.time()
        try:
            result = self.handler(task)
            result.execution_time_ms = int((time.time() - start) * 1000)
            return result
        except Exception as e:
            return AgentTaskResult(
                task_id=task.task_id,
                success=False,
                error=str(e),
                error_code="EXECUTION_ERROR",
                execution_time_ms=int((time.time() - start) * 1000),
            )
    
    async def execute_async(self, task: AgentTask) -> AgentTaskResult:
        return self.execute(task)
    
    def health_check(self) -> AgentHealth:
        return AgentHealth(
            agent_id=self.agent_type,
            instance_id="in_memory",
            status=AgentStatus.HEALTHY if self._healthy else AgentStatus.UNHEALTHY,
            is_healthy=self._healthy,
        )
    
    def shutdown(self, graceful: bool = True) -> None:
        self._healthy = False


# =============================================================================
# Factory
# =============================================================================

def create_agent_registry(
    heartbeat_timeout_sec: int = 90,
    cleanup_interval_sec: int = 60,
) -> AgentRegistry:
    """Create an AgentRegistry instance."""
    return AgentRegistry(heartbeat_timeout_sec, cleanup_interval_sec)

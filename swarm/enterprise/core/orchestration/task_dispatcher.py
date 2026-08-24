"""
Task Dispatcher - Routes tasks to appropriate agents with load balancing.
"""

import threading
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Set
from enum import Enum
import logging

from .agent_registry import (
    AgentRegistry, AgentCapability, AgentTask, AgentTaskResult,
    AgentInstance, AgentExecutor, InMemoryAgentExecutor,
    create_agent_registry,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Dispatcher Models
# =============================================================================

class DispatchStrategy(str, Enum):
    """Task dispatch strategy."""
    LEAST_LOADED = "least_loaded"           # Pick instance with lowest load
    ROUND_ROBIN = "round_robin"             # Round robin across instances
    CAPABILITY_FIRST = "capability_first"   # Prefer instances with exact capability
    AFFINITY = "affinity"                   # Prefer same instance for related tasks
    PRIORITY = "priority"                   # High priority tasks get best instances


@dataclass
class DispatchConfig:
    """Configuration for task dispatcher."""
    strategy: DispatchStrategy = DispatchStrategy.LEAST_LOADED
    default_timeout_seconds: int = 300
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    enable_circuit_breaker: bool = True
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout_seconds: float = 60.0
    enable_fallback: bool = True
    fallback_capabilities: Dict[AgentCapability, List[AgentCapability]] = field(default_factory=dict)


@dataclass
class DispatchResult:
    """Result of task dispatch."""
    task_id: str
    success: bool
    instance_id: Optional[str] = None
    result: Optional[AgentTaskResult] = None
    error: Optional[str] = None
    dispatch_time_ms: int = 0
    attempts: int = 0


# =============================================================================
# Circuit Breaker
# =============================================================================

class CircuitBreakerState(str, Enum):
    CLOSED = "closed"       # Normal operation
    OPEN = "open"           # Failing, reject requests
    HALF_OPEN = "half_open" # Testing if recovered


@dataclass
class CircuitBreaker:
    """Circuit breaker for agent instances."""
    instance_id: str
    failure_threshold: int = 5
    timeout_seconds: float = 60.0
    state: CircuitBreakerState = CircuitBreakerState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[datetime] = None
    last_state_change: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def record_success(self) -> None:
        self.failure_count = 0
        self.success_count += 1
        if self.state == CircuitBreakerState.HALF_OPEN and self.success_count >= 2:
            self.state = CircuitBreakerState.CLOSED
            self.last_state_change = datetime.now(timezone.utc)
            logger.info(f"Circuit breaker CLOSED for {self.instance_id}")
    
    def record_failure(self) -> None:
        self.failure_count += 1
        self.success_count = 0
        self.last_failure_time = datetime.now(timezone.utc)
        
        if self.state == CircuitBreakerState.CLOSED and self.failure_count >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN
            self.last_state_change = datetime.now(timezone.utc)
            logger.warning(f"Circuit breaker OPEN for {self.instance_id}")
        elif self.state == CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.OPEN
            self.last_state_change = datetime.now(timezone.utc)
    
    def can_execute(self) -> bool:
        if self.state == CircuitBreakerState.CLOSED:
            return True
        
        if self.state == CircuitBreakerState.OPEN:
            if self.last_failure_time:
                elapsed = (datetime.now(timezone.utc) - self.last_failure_time).total_seconds()
                if elapsed >= self.timeout_seconds:
                    self.state = CircuitBreakerState.HALF_OPEN
                    self.last_state_change = datetime.now(timezone.utc)
                    logger.info(f"Circuit breaker HALF_OPEN for {self.instance_id}")
                    return True
            return False
        
        # HALF_OPEN
        return True
    
    def reset(self) -> None:
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.last_state_change = datetime.now(timezone.utc)


# =============================================================================
# Task Dispatcher
# =============================================================================

class TaskDispatcher:
    """
    Dispatches tasks to registered agents with load balancing,
    retries, circuit breaking, and fallback support.
    """
    
    def __init__(
        self,
        registry: AgentRegistry,
        config: Optional[DispatchConfig] = None,
    ):
        self.registry = registry
        self.config = config or DispatchConfig()
        
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._round_robin_counters: Dict[str, int] = {}
        self._lock = threading.RLock()
        
        # Task callbacks
        self._pre_dispatch_hooks: List[Callable[[AgentTask], None]] = []
        self._post_dispatch_hooks: List[Callable[[DispatchResult], None]] = []
    
    def add_pre_dispatch_hook(self, hook: Callable[[AgentTask], None]) -> None:
        """Add hook called before dispatch."""
        self._pre_dispatch_hooks.append(hook)
    
    def add_post_dispatch_hook(self, hook: Callable[[DispatchResult], None]) -> None:
        """Add hook called after dispatch."""
        self._post_dispatch_hooks.append(hook)
    
    def dispatch(
        self,
        capability: AgentCapability,
        payload: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        priority: int = 0,
        timeout_seconds: Optional[int] = None,
        tenant_id: str = "default",
        trace_id: Optional[str] = None,
        preferred_instance_id: Optional[str] = None,
        capability_fallback: bool = True,
    ) -> DispatchResult:
        """
        Dispatch a task to an agent.
        
        Args:
            capability: Required agent capability
            payload: Task payload
            context: Additional context
            priority: Task priority (higher = more urgent)
            timeout_seconds: Override default timeout
            tenant_id: Tenant ID for isolation
            trace_id: Trace ID for observability
            preferred_instance_id: Preferred instance (affinity)
            capability_fallback: Try fallback capabilities if primary fails
            
        Returns:
            DispatchResult with execution result
        """
        task_id = str(uuid.uuid4())
        start_time = datetime.now(timezone.utc)
        
        task = AgentTask(
            task_id=task_id,
            agent_type="",  # Will be set by dispatcher
            capability=capability,
            payload=payload,
            context=context or {},
            priority=priority,
            timeout_seconds=timeout_seconds or self.config.default_timeout_seconds,
            tenant_id=tenant_id,
            trace_id=trace_id,
        )
        
        # Run pre-dispatch hooks
        for hook in self._pre_dispatch_hooks:
            try:
                hook(task)
            except Exception as e:
                logger.warning(f"Pre-dispatch hook failed: {e}")
        
        # Try primary capability
        result = self._dispatch_to_capability(
            task, capability, preferred_instance_id
        )
        
        # Try fallback capabilities if primary failed
        if (not result.success and capability_fallback and 
            self.config.enable_fallback):
            
            fallback_caps = self.config.fallback_capabilities.get(capability, [])
            for fallback_cap in fallback_caps:
                logger.info(f"Trying fallback capability: {fallback_cap.value}")
                task.capability = fallback_cap
                result = self._dispatch_to_capability(
                    task, fallback_cap, preferred_instance_id
                )
                if result.success:
                    result.error = f"Primary failed, used fallback: {fallback_cap.value}"
                    break
        
        # Update timing
        end_time = datetime.now(timezone.utc)
        result.dispatch_time_ms = int((end_time - start_time).total_seconds() * 1000)
        
        # Run post-dispatch hooks
        for hook in self._post_dispatch_hooks:
            try:
                hook(result)
            except Exception as e:
                logger.warning(f"Post-dispatch hook failed: {e}")
        
        return result
    
    def _dispatch_to_capability(
        self,
        task: AgentTask,
        capability: AgentCapability,
        preferred_instance_id: Optional[str],
    ) -> DispatchResult:
        """Dispatch to a specific capability."""
        task.capability = capability
        
        # Find available instance
        instance = self.registry.find_available_instance(
            capability=capability,
            tenant_id=task.tenant_id,
            preferred_instance_id=preferred_instance_id,
        )
        
        if not instance:
            return DispatchResult(
                task_id=task.task_id,
                success=False,
                error=f"No available agent for capability: {capability.value}",
            )
        
        # Check circuit breaker
        breaker = self._get_circuit_breaker(instance.instance_id)
        if self.config.enable_circuit_breaker and not breaker.can_execute():
            # Try to find another instance
            instance = self._find_alternative_instance(capability, task.tenant_id, instance.instance_id)
            if not instance:
                return DispatchResult(
                    task_id=task.task_id,
                    success=False,
                    error=f"All instances for {capability.value} are circuit-broken",
                )
            breaker = self._get_circuit_breaker(instance.instance_id)
        
        # Execute with retries
        max_attempts = self.config.max_retries + 1
        last_error = None
        
        for attempt in range(max_attempts):
            task.retry_count = attempt
            task.agent_type = instance.metadata.agent_type
            
            result = self._execute_task(instance, task)
            result.attempts = attempt + 1
            
            if result.success:
                breaker.record_success()
                return DispatchResult(
                    task_id=task.task_id,
                    success=True,
                    instance_id=instance.instance_id,
                    result=result,
                    attempts=attempt + 1,
                )
            else:
                last_error = result.error
                breaker.record_failure()
                logger.warning(f"Task {task.task_id} attempt {attempt + 1} failed: {result.error}")
                
                # Try alternative instance on retry
                if attempt < max_attempts - 1:
                    alt_instance = self._find_alternative_instance(
                        capability, task.tenant_id, instance.instance_id
                    )
                    if alt_instance:
                        instance = alt_instance
                        breaker = self._get_circuit_breaker(instance.instance_id)
        
        return DispatchResult(
            task_id=task.task_id,
            success=False,
            instance_id=instance.instance_id,
            error=last_error or "Max retries exceeded",
            attempts=max_attempts,
        )
    
    def _execute_task(self, instance: AgentInstance, task: AgentTask) -> AgentTaskResult:
        """Execute task on agent instance."""
        executor = self.registry._executors.get(instance.instance_id)
        
        if not executor:
            # Create default executor if not registered
            executor = InMemoryAgentExecutor(
                instance.metadata.agent_type,
                self._default_handler,
            )
            self.registry._executors[instance.instance_id] = executor
        
        try:
            result = executor.execute(task)
            result.agent_instance_id = instance.instance_id
            
            # Update instance stats
            self.registry.record_task_result(
                instance.instance_id,
                result.success,
                result.execution_time_ms,
            )
            
            return result
        except Exception as e:
            logger.exception(f"Task execution failed on {instance.instance_id}")
            return AgentTaskResult(
                task_id=task.task_id,
                success=False,
                error=str(e),
                error_code="EXECUTION_ERROR",
                agent_instance_id=instance.instance_id,
            )
    
    def _default_handler(self, task: AgentTask) -> AgentTaskResult:
        """Default handler for tasks without custom executor."""
        return AgentTaskResult(
            task_id=task.task_id,
            success=False,
            error=f"No handler for capability {task.capability.value}",
            error_code="NO_HANDLER",
        )
    
    def _get_circuit_breaker(self, instance_id: str) -> CircuitBreaker:
        """Get or create circuit breaker for instance."""
        with self._lock:
            if instance_id not in self._circuit_breakers:
                self._circuit_breakers[instance_id] = CircuitBreaker(
                    instance_id=instance_id,
                    failure_threshold=self.config.circuit_breaker_threshold,
                    timeout_seconds=self.config.circuit_breaker_timeout_seconds,
                )
            return self._circuit_breakers[instance_id]
    
    def _find_alternative_instance(
        self,
        capability: AgentCapability,
        tenant_id: str,
        exclude_instance_id: str,
    ) -> Optional[AgentInstance]:
        """Find alternative healthy instance."""
        candidates = self.registry._capability_instances.get(capability, set())
        
        for instance_id in candidates:
            if instance_id == exclude_instance_id:
                continue
            
            instance = self.registry._instances.get(instance_id)
            if not instance:
                continue
            
            if instance.status not in (instance.status.HEALTHY, instance.status.DEGRADED):
                continue
            
            if instance.active_task_count >= instance.max_concurrent_tasks:
                continue
            
            # Check tenant
            if instance.metadata_extra.get("tenant_id") != tenant_id:
                continue
            
            # Check circuit breaker
            breaker = self._get_circuit_breaker(instance_id)
            if not breaker.can_execute():
                continue
            
            return instance
        
        return None
    
    def get_circuit_breaker_status(self, instance_id: str) -> Optional[Dict[str, Any]]:
        """Get circuit breaker status for an instance."""
        with self._lock:
            breaker = self._circuit_breakers.get(instance_id)
            if not breaker:
                return None
            return {
                "instance_id": instance_id,
                "state": breaker.state.value,
                "failure_count": breaker.failure_count,
                "success_count": breaker.success_count,
                "last_failure_time": breaker.last_failure_time.isoformat() if breaker.last_failure_time else None,
            }
    
    def reset_circuit_breaker(self, instance_id: str) -> bool:
        """Manually reset circuit breaker."""
        with self._lock:
            if instance_id in self._circuit_breakers:
                self._circuit_breakers[instance_id].reset()
                return True
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get dispatcher statistics."""
        with self._lock:
            return {
                "strategy": self.config.strategy.value,
                "circuit_breakers": {
                    k: v.state.value for k, v in self._circuit_breakers.items()
                },
                "round_robin_counters": dict(self._round_robin_counters),
            }


# =============================================================================
# Factory
# =============================================================================

def create_task_dispatcher(
    registry: AgentRegistry,
    config: Optional[DispatchConfig] = None,
) -> TaskDispatcher:
    """Create a TaskDispatcher instance."""
    return TaskDispatcher(registry, config)

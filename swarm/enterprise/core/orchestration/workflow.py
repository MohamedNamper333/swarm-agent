"""
Workflow Orchestration - Saga patterns, compensation, and workflow management.
"""

import threading
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from collections import defaultdict, deque
import logging

logger = logging.getLogger(__name__)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def uuidv7() -> str:
    return str(uuid.uuid4())


# =============================================================================
# Workflow Models
# =============================================================================

class WorkflowStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    COMPENSATING = "compensating"
    COMPENSATED = "compensated"
    PARTIALLY_COMPLETED = "partially_completed"
    CANCELLED = "cancelled"


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    COMPENSATING = "compensating"
    COMPENSATED = "compensated"
    SKIPPED = "skipped"


class CompensationStrategy(str, Enum):
    SEQUENTIAL = "sequential"           # Reverse order, one by one
    PARALLEL = "parallel"               # All at once
    BEST_EFFORT = "best_effort"         # Try all, continue on failure


@dataclass
class WorkflowStep:
    step_id: str
    name: str
    execute_fn: Callable[[Dict[str, Any]], Any]
    compensate_fn: Optional[Callable[[Dict[str, Any], Any], Any]] = None
    depends_on: List[str] = field(default_factory=list)
    provides: List[str] = field(default_factory=list)  # Keys this step adds to context
    requires: List[str] = field(default_factory=list)  # Keys this step needs from context
    timeout_seconds: int = 300
    retry_count: int = 0
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    status: StepStatus = StepStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    compensation_result: Any = None
    compensation_error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowContext:
    """Context passed between workflow steps."""
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        self.data[key] = value
    
    def update(self, other: Dict[str, Any]) -> None:
        self.data.update(other)
    
    def has(self, key: str) -> bool:
        return key in self.data


@dataclass
class Workflow:
    workflow_id: str = field(default_factory=lambda: f"wf-{uuid.uuid4()}")
    name: str = ""
    workflow_type: str = ""
    steps: Dict[str, WorkflowStep] = field(default_factory=dict)
    execution_order: List[str] = field(default_factory=list)
    status: WorkflowStatus = WorkflowStatus.PENDING
    context: WorkflowContext = field(default_factory=WorkflowContext)
    current_step: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    compensation_strategy: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    tenant_id: str = "default"
    trace_id: Optional[str] = None


# =============================================================================
# Workflow Builder
# =============================================================================

class WorkflowBuilder:
    """Fluent builder for creating workflows."""
    
    def __init__(self, workflow_id: str, name: str, workflow_type: str):
        self.workflow = Workflow(
            workflow_id=workflow_id,
            name=name,
            workflow_type=workflow_type,
        )
    
    def add_step(
        self,
        step_id: str,
        name: str,
        execute_fn: Callable[[Dict[str, Any]], Any],
        compensate_fn: Optional[Callable[[Dict[str, Any], Any], Any]] = None,
        depends_on: Optional[List[str]] = None,
        provides: Optional[List[str]] = None,
        requires: Optional[List[str]] = None,
        timeout_seconds: int = 300,
        max_retries: int = 3,
        retry_delay_seconds: float = 1.0,
    ) -> "WorkflowBuilder":
        step = WorkflowStep(
            step_id=step_id,
            name=name,
            execute_fn=execute_fn,
            compensate_fn=compensate_fn,
            depends_on=depends_on or [],
            provides=provides or [],
            requires=requires or [],
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            retry_delay_seconds=retry_delay_seconds,
        )
        self.workflow.steps[step_id] = step
        return self
    
    def set_compensation_strategy(self, strategy: Any) -> "WorkflowBuilder":
        self.workflow.compensation_strategy = strategy
        return self
    
    def set_tenant(self, tenant_id: str) -> "WorkflowBuilder":
        self.workflow.tenant_id = tenant_id
        return self
    
    def set_trace_id(self, trace_id: str) -> "WorkflowBuilder":
        self.workflow.trace_id = trace_id
        return self
    
    def build(self) -> Workflow:
        # Compute execution order using topological sort
        self.workflow.execution_order = self._topological_sort()
        return self.workflow
    
    def _topological_sort(self) -> List[str]:
        """Kahn's algorithm for topological sorting."""
        in_degree = {sid: 0 for sid in self.workflow.steps}
        adj = {sid: [] for sid in self.workflow.steps}
        
        for step_id, step in self.workflow.steps.items():
            for dep in step.depends_on:
                if dep not in self.workflow.steps:
                    raise ValueError(f"Step '{step_id}' depends on unknown step '{dep}'")
                adj[dep].append(step_id)
                in_degree[step_id] += 1
        
        queue = deque(sorted(sid for sid, deg in in_degree.items() if deg == 0))
        order = []
        
        while queue:
            current = queue.popleft()
            order.append(current)
            for neighbor in adj[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        if len(order) != len(self.workflow.steps):
            cycle_steps = [sid for sid, deg in in_degree.items() if deg > 0]
            raise ValueError(f"Cycle detected in workflow dependencies. Steps in cycle: {cycle_steps}")
        
        return order


# =============================================================================
# Workflow Engine
# =============================================================================

class WorkflowEngine:
    """Executes workflows with saga pattern compensation."""
    
    def __init__(
        self,
        default_timeout: int = 300,
        max_concurrent_workflows: int = 10,
    ):
        self.default_timeout = default_timeout
        self.max_concurrent_workflows = max_concurrent_workflows
        
        self._workflows: Dict[str, Workflow] = {}
        self._running: Dict[str, threading.Thread] = {}
        self._lock = threading.RLock()
        
        # Callbacks
        self._step_callbacks: List[Callable[[Workflow, WorkflowStep, str], None]] = []
        self._workflow_callbacks: List[Callable[[Workflow, str], None]] = []
    
    def register_workflow(self, workflow: Workflow) -> None:
        """Register a workflow for execution."""
        with self._lock:
            if workflow.workflow_id in self._workflows:
                raise ValueError(f"Workflow {workflow.workflow_id} already registered")
            self._workflows[workflow.workflow_id] = workflow
            logger.info(f"Registered workflow: {workflow.workflow_id} ({workflow.name})")
    
    def unregister_workflow(self, workflow_id: str) -> bool:
        with self._lock:
            if workflow_id in self._workflows:
                del self._workflows[workflow_id]
                return True
            return False
    
    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        with self._lock:
            return self._workflows.get(workflow_id)
    
    def list_workflows(
        self,
        status: Optional[Any] = None,
        tenant_id: Optional[str] = None,
    ) -> List[Workflow]:
        with self._lock:
            workflows = list(self._workflows.values())
            
            if status:
                workflows = [w for w in workflows if w.status == status]
            if tenant_id:
                workflows = [w for w in workflows if w.tenant_id == tenant_id]
            
            return workflows
    
    def execute(
        self,
        workflow_id: str,
        initial_context: Optional[Dict[str, Any]] = None,
    ) -> Workflow:
        """Execute a workflow synchronously."""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        if workflow.status != WorkflowStatus.PENDING:
            raise ValueError(f"Workflow {workflow_id} is not in PENDING state")
        
        with self._lock:
            if len(self._running) >= self.max_concurrent_workflows:
                raise RuntimeError("Max concurrent workflows reached")
        
        # Initialize context
        if initial_context:
            workflow.context.update(initial_context)
        
        workflow.status = WorkflowStatus.RUNNING
        workflow.started_at = now_utc()
        
        try:
            # Execute steps in order
            for step_id in workflow.execution_order:
                step = workflow.steps[step_id]
                workflow.current_step = step_id
                self._execute_step(workflow, step)
            
            workflow.status = WorkflowStatus.COMPLETED
            workflow.completed_at = now_utc()
            
            # Notify callbacks
            for cb in self._workflow_callbacks:
                try:
                    cb(workflow, "completed")
                except Exception as e:
                    logger.error(f"Workflow callback error: {e}")
            
        except Exception as e:
            logger.error(f"Workflow {workflow_id} failed at step {workflow.current_step}: {e}")
            workflow.error = str(e)
            workflow.status = WorkflowStatus.COMPENSATING
            
            # Trigger compensation
            self._compensate(workflow)
            
            workflow.status = WorkflowStatus.FAILED
            workflow.completed_at = now_utc()
            
            for cb in self._workflow_callbacks:
                try:
                    cb(workflow, "failed")
                except Exception as e:
                    logger.error(f"Workflow callback error: {e}")
            
            raise
        
        return workflow
    
    def execute_async(
        self,
        workflow_id: str,
        initial_context: Optional[Dict[str, Any]] = None,
        callback: Optional[Callable[[Workflow], None]] = None,
    ) -> threading.Thread:
        """Execute workflow asynchronously."""
        
        def run():
            try:
                result = self.execute(workflow_id, initial_context)
                if callback:
                    callback(result)
            except Exception as e:
                if callback:
                    # Get workflow to pass to callback
                    wf = self._workflows.get(workflow_id)
                    if wf:
                        callback(wf)
        
        thread = threading.Thread(target=run, daemon=True)
        with self._lock:
            self._running[workflow_id] = thread
        thread.start()
        return thread
    
    def _execute_step(self, workflow: Workflow, step: WorkflowStep) -> None:
        """Execute a single workflow step."""
        logger.info(f"Executing step: {step.step_id} ({step.name})")
        
        step.status = StepStatus.RUNNING
        step.started_at = now_utc()
        
        # Validate required inputs
        missing = [k for k in step.requires if not workflow.context.has(k)]
        if missing:
            raise ValueError(
                f"Step '{step.step_id}' requires missing keys {missing}. "
                f"Available: {list(workflow.context.data.keys())}"
            )
        
        # Prepare inputs
        inputs = {k: workflow.context.get(k) for k in step.requires}
        
        # Execute with retry
        for attempt in range(step.max_retries + 1):
            step.retry_count = attempt
            try:
                result = step.execute_fn(workflow.context.data)
                step.result = result
                step.status = StepStatus.COMPLETED
                step.completed_at = now_utc()
                
                # Store outputs in context
                for key in step.provides:
                    if hasattr(result, key):
                        workflow.context.set(key, getattr(result, key))
                    elif isinstance(result, dict) and key in result:
                        workflow.context.set(key, result[key])
                    else:
                        # Store full result if key not found
                        workflow.context.set(key, result)
                
                logger.info(f"Step {step.step_id} completed successfully")
                
                # Step callbacks
                for cb in self._step_callbacks:
                    try:
                        cb(workflow, step, "completed")
                    except Exception as e:
                        logger.error(f"Step callback error: {e}")
                
                return
                
            except Exception as e:
                logger.warning(f"Step {step.step_id} attempt {attempt + 1} failed: {e}")
                step.error = str(e)
                
                if attempt < step.max_retries:
                    import time
                    time.sleep(step.retry_delay_seconds * (2 ** attempt))  # Exponential backoff
                else:
                    step.status = StepStatus.FAILED
                    step.completed_at = now_utc()
                    raise
    
    def _compensate(self, workflow: Workflow) -> None:
        """Run compensation for completed steps in reverse order."""
        logger.info(f"Starting compensation for workflow {workflow.workflow_id}")
        
        # Get completed steps in reverse order
        completed_steps = [
            s for s in workflow.execution_order
            if workflow.steps[s].status == StepStatus.COMPLETED
        ]
        
        for step_id in reversed(completed_steps):
            step = workflow.steps[step_id]
            if not step.compensate_fn:
                logger.warning(f"No compensation function for step {step_id}")
                step.status = StepStatus.COMPENSATED  # Mark as compensated (no-op)
                continue
            
            step.status = StepStatus.COMPENSATING
            
            try:
                # Pass context and original result to compensation
                result = step.compensate_fn(workflow.context.data, step.result)
                step.compensation_result = result
                step.status = StepStatus.COMPENSATED
                logger.info(f"Compensated step: {step_id}")
            except Exception as e:
                logger.error(f"Compensation failed for step {step_id}: {e}")
                step.compensation_error = str(e)
                step.status = StepStatus.FAILED
                # Continue with other compensations
    
    def cancel_workflow(self, workflow_id: str) -> bool:
        """Cancel a running workflow."""
        with self._lock:
            workflow = self._workflows.get(workflow_id)
            if not workflow:
                return False
            
            if workflow.status == WorkflowStatus.RUNNING:
                workflow.status = WorkflowStatus.CANCELLED
                # Trigger compensation for completed steps
                self._compensate(workflow)
                return True
            return False
    
    def add_step_callback(self, callback: Callable[[Workflow, WorkflowStep, str], None]) -> None:
        """Add callback for step events."""
        self._step_callbacks.append(callback)
    
    def add_workflow_callback(self, callback: Callable[[Workflow, str], None]) -> None:
        """Add callback for workflow events."""
        self._workflow_callbacks.append(callback)
    
    def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed workflow status."""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return None
        
        step_statuses = {}
        for step_id, step in workflow.steps.items():
            step_statuses[step_id] = {
                "name": step.name,
                "status": step.status.value,
                "started_at": step.started_at.isoformat() if step.started_at else None,
                "completed_at": step.completed_at.isoformat() if step.completed_at else None,
                "error": step.error,
                "retry_count": step.retry_count,
            }
        
        return {
            "workflow_id": workflow.workflow_id,
            "name": workflow.name,
            "type": workflow.workflow_type,
            "status": workflow.status.value,
            "current_step": workflow.current_step,
            "progress": f"{len([s for s in workflow.steps.values() if s.status == StepStatus.COMPLETED])}/{len(workflow.steps)}",
            "steps": step_statuses,
            "error": workflow.error,
            "started_at": workflow.started_at.isoformat() if workflow.started_at else None,
            "completed_at": workflow.completed_at.isoformat() if workflow.completed_at else None,
        }


# =============================================================================
# Saga Coordinator
# =============================================================================

class SagaCoordinator:
    """Coordinates distributed sagas across multiple services."""
    
    def __init__(self, workflow_engine: WorkflowEngine):
        self.workflow_engine = workflow_engine
        self._saga_log: Dict[str, List[Dict[str, Any]]] = {}
        self._lock = threading.RLock()
    
    def create_saga(
        self,
        saga_id: str,
        workflow_type: str,
        steps: List[Dict[str, Any]],
    ) -> Workflow:
        """Create a saga workflow from step definitions."""
        workflow = WorkflowBuilder(saga_id, f"Saga-{saga_id}", workflow_type)
        
        for step_def in steps:
            workflow.add_step(
                step_id=step_def["step_id"],
                name=step_def.get("name", step_def["step_id"]),
                execute_fn=step_def["execute_fn"],
                compensate_fn=step_def.get("compensate_fn"),
                depends_on=step_def.get("depends_on", []),
                provides=step_def.get("provides", []),
                requires=step_def.get("requires", []),
                timeout_seconds=step_def.get("timeout_seconds", 300),
                max_retries=step_def.get("max_retries", 3),
            )
        
        workflow = workflow.build()
        workflow.workflow_type = workflow_type
        workflow.metadata["saga"] = True
        
        self.workflow_engine.register_workflow(workflow)
        
        return workflow
    
    def execute_saga(self, saga_id: str, context: Optional[Dict[str, Any]] = None) -> Any:
        """Execute a saga."""
        return self.workflow_engine.execute(saga_id, context)
    
    def get_saga_status(self, saga_id: str) -> Optional[Dict[str, Any]]:
        return self.workflow_engine.get_workflow_status(saga_id)


# =============================================================================
# Factory
# =============================================================================

def create_workflow_engine(
    default_timeout: int = 300,
    max_concurrent_workflows: int = 10,
) -> WorkflowEngine:
    """Create a WorkflowEngine instance."""
    return WorkflowEngine(default_timeout, max_concurrent_workflows)


def create_saga_coordinator(workflow_engine: WorkflowEngine) -> SagaCoordinator:
    """Create a SagaCoordinator instance."""
    return SagaCoordinator(workflow_engine)


def create_workflow(
    workflow_id: str,
    name: str,
    workflow_type: str,
    steps: List[Dict[str, Any]],
) -> Workflow:
    """Convenience function to create a workflow."""
    builder = WorkflowBuilder(workflow_id, name, workflow_type)
    
    for step_def in steps:
        builder.add_step(
            step_id=step_def["step_id"],
            name=step_def.get("name", step_def["step_id"]),
            execute_fn=step_def["execute_fn"],
            compensate_fn=step_def.get("compensate_fn"),
            depends_on=step_def.get("depends_on", []),
            provides=step_def.get("provides", []),
            requires=step_def.get("requires", []),
            timeout_seconds=step_def.get("timeout_seconds", 300),
            max_retries=step_def.get("max_retries", 3),
        )
    
    return builder.build()

"""
Compensation Model — explicit retry, compensation, recovery for side-effecting operations.

F-027: No Explicit Compensation Model fix.
Every side-effecting workflow defines: retry behavior, compensation behavior, recovery behavior.
"""
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Callable, Set, Tuple
from enum import Enum
from datetime import datetime, timezone
import uuid
import logging

from .repository import JobRepository, create_job_repository, InMemoryJobRepository

logger = logging.getLogger(__name__)


class StepTimeoutError(Exception):
    """Raised when a workflow step or compensation exceeds its timeout."""

    def __init__(self, step_id: str, timeout_ms: int, phase: str):
        self.step_id = step_id
        self.timeout_ms = timeout_ms
        self.phase = phase  # "execute" or "compensate"
        super().__init__(
            f"Step '{step_id}' {phase} timed out after {timeout_ms}ms"
        )


def _run_with_timeout(fn: Callable, args: Tuple, timeout_ms: int) -> Any:
    """Execute fn(*args) with an effective timeout.

    Runs the callable on a single-thread executor so we can enforce
    a hard timeout. On timeout, attempts to cancel the future (best-effort
    for cooperative cancellation) and raises StepTimeoutError.

    Returns the result of fn(*args) on success.
    """
    executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="step")
    try:
        future = executor.submit(fn, *args)
        try:
            return future.result(timeout=timeout_ms / 1000)
        except FuturesTimeoutError:
            future.cancel()
            raise StepTimeoutError(
                step_id=getattr(fn, "__name__", "<step>"),
                timeout_ms=timeout_ms,
                phase="execute",
            )
    finally:
        executor.shutdown(wait=False)


class CompensationAction(str, Enum):
    """Types of compensation actions."""
    UNDO = "undo"                    # Reverse the operation
    COMPENSATE = "compensate"        # Apply counteracting operation
    RECONCILE = "reconcile"          # Reconcile state
    NOTIFY = "notify"                # Alert humans
    IGNORE = "ignore"                # No compensation (best effort)
    ESCALATE = "escalate"            # Escalate to human


class WorkflowStepStatus(str, Enum):
    """Status of a workflow step."""
    PENDING = "pending"
    EXECUTING = "executing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    COMPENSATING = "compensating"
    COMPENSATED = "compensated"
    COMPENSATION_FAILED = "compensation_failed"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class CompensationPolicy:
    """Policy for handling failures in a workflow step."""
    action: CompensationAction = CompensationAction.UNDO
    retryable: bool = False
    max_retries: int = 0
    retry_policy: str = "exponential"  # "fixed", "exponential", "linear"
    base_retry_delay_ms: int = 1000
    compensation_timeout_ms: int = 30000
    requires_manual_approval: bool = False
    escalation_role: Optional[str] = None


@dataclass
class WorkflowStep:
    """A single step in a compensable workflow."""
    step_id: str
    name: str
    execute_fn: Callable[[Dict[str, Any]], Any]
    compensate_fn: Optional[Callable[[Dict[str, Any], Any], Any]] = None
    compensation_policy: CompensationPolicy = field(default_factory=CompensationPolicy)
    depends_on: List[str] = field(default_factory=list)  # step_ids this depends on
    provides: List[str] = field(default_factory=list)  # output keys this step provides
    requires: List[str] = field(default_factory=list)  # input keys this step requires
    status: WorkflowStepStatus = WorkflowStepStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    compensation_result: Any = None


@dataclass
class WorkflowExecution:
    """Execution state of a compensable workflow."""
    workflow_id: str
    workflow_type: str
    steps: Dict[str, WorkflowStep] = field(default_factory=dict)
    execution_order: List[str] = field(default_factory=list)  # topological order
    context: Dict[str, Any] = field(default_factory=dict)  # shared state
    status: str = "pending"  # pending, running, succeeded, failed, compensating, compensated
    current_step: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


class CompensationEngine:
    """Executes workflows with automatic compensation on failure."""

    def _persist_state(self, workflow: "WorkflowExecution") -> None:
        """Fire-and-forget persistence that NEVER drops writes silently.

        Fixes three audit defects repeated across 5 call sites:
        - create_task() result was discarded: the task could be GC'd before
          running (CPython documented hazard) -> save silently never happens.
        - No-running-loop path swallowed the write with `pass`.
        - Failures inside the save task were unobserved.
        """
        if not self.job_repository:
            return
        import asyncio as _aio
        import threading as _threading

        try:
            loop = _aio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop is not None:
            task = loop.create_task(self.job_repository.save_workflow(workflow))
            self._persist_tasks.add(task)
            task.add_done_callback(self._persist_tasks.discard)
            def _observe(t):
                exc = t.exception() if not t.cancelled() else None
                if exc:
                    logger.error(f"Workflow persistence failed: {exc}")
            task.add_done_callback(_observe)
        else:
            # Sync context: persist on a worker thread with its own loop.
            import logging as _lg
            def _run():
                try:
                    _aio.run(self.job_repository.save_workflow(workflow))
                except Exception as exc:  # pragma: no cover
                    _lg.getLogger(__name__).error(
                        f"Workflow persistence (sync ctx) failed: {exc}")
            _threading.Thread(target=_run, daemon=True, name="wf-persist").start()

    def __init__(self, job_repository: Optional[JobRepository] = None):
        self._persist_tasks: set = set()
        self._workflows: Dict[str, WorkflowExecution] = {}
        self._lock = threading.RLock()
        self.job_repository = job_repository or create_job_repository("memory")

    def register_workflow(self, workflow: WorkflowExecution) -> None:
        """Register a workflow for execution."""
        with self._lock:
            # Validate and compute execution order
            workflow.execution_order = self._topological_sort(workflow)
            self._workflows[workflow.workflow_id] = workflow
        
        # Persist workflow
        self._persist_state(workflow)

    def _topological_sort(self, workflow: WorkflowExecution) -> List[str]:
        """Compute topological order using Kahn's algorithm (iterative).

        Iterative to avoid RecursionError on deep workflows. Detects cycles
        by checking if all steps are visited.
        """
        in_degree: Dict[str, int] = {sid: 0 for sid in workflow.steps}
        adj: Dict[str, List[str]] = {sid: [] for sid in workflow.steps}

        # Build adjacency list and in-degree counts
        for step_id, step in workflow.steps.items():
            for dep in step.depends_on:
                if dep not in workflow.steps:
                    raise ValueError(
                        f"Step '{step_id}' depends on unknown step '{dep}'"
                    )
                adj[dep].append(step_id)
                in_degree[step_id] += 1

        # Start with steps that have no dependencies
        # Use deque for O(1) popleft (better than list.pop(0) which is O(n))
        from collections import deque
        queue = deque(sorted(sid for sid, deg in in_degree.items() if deg == 0))
        order: List[str] = []

        while queue:
            current = queue.popleft()
            order.append(current)
            for neighbor in adj[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(order) != len(workflow.steps):
            cycle_steps = [sid for sid, deg in in_degree.items() if deg > 0]
            raise ValueError(
                f"Cycle detected in workflow dependencies. "
                f"Steps in cycle: {cycle_steps}"
            )
        return order

    def execute(self, workflow_id: str) -> WorkflowExecution:
        """Execute a workflow with automatic compensation on failure."""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")

        workflow.status = "running"
        workflow.started_at = datetime.now(timezone.utc)
        
        # Persist initial running state
        self._persist_state(workflow)

        try:
            for step_id in workflow.execution_order:
                step = workflow.steps[step_id]
                workflow.current_step = step_id
                step.status = WorkflowStepStatus.EXECUTING
                step.started_at = datetime.now(timezone.utc)

                # Prepare inputs from context — strictly validate required keys
                inputs: Dict[str, Any] = {}
                missing_keys = [k for k in step.requires if k not in workflow.context]
                if missing_keys:
                    raise ValueError(
                        f"Step '{step_id}' requires missing keys {missing_keys}. "
                        f"Available context keys: {list(workflow.context.keys())}. "
                        f"Check that upstream steps declared these in 'provides'."
                    )
                inputs = {k: workflow.context[k] for k in step.requires}

                # Execute step with effective timeout enforcement
                timeout_ms = step.compensation_policy.compensation_timeout_ms
                try:
                    result = _run_with_timeout(step.execute_fn, (inputs,), timeout_ms)
                except StepTimeoutError:
                    step.status = WorkflowStepStatus.FAILED
                    step.error = f"timeout after {timeout_ms}ms"
                    step.completed_at = datetime.now(timezone.utc)
                    raise

                step.result = result
                step.status = WorkflowStepStatus.SUCCEEDED
                step.completed_at = datetime.now(timezone.utc)

                # Store outputs in context
                for key in step.provides:
                    if hasattr(result, key):
                        workflow.context[key] = getattr(result, key)
                    elif isinstance(result, dict) and key in result:
                        workflow.context[key] = result[key]

            workflow.status = "succeeded"
            workflow.completed_at = datetime.now(timezone.utc)
            
            # Persist final state
            self._persist_state(workflow)
            
            return workflow

        except Exception as e:
            logger.error(f"Workflow {workflow_id} failed at step {workflow.current_step}: {e}")
            workflow.error = str(e)
            workflow.status = "compensating"
            
            # Persist compensating state
            self._persist_state(workflow)
            
            self._compensate(workflow)
            workflow.status = "failed"
            workflow.completed_at = datetime.now(timezone.utc)
            
            # Persist final failed state
            self._persist_state(workflow)
            
            raise

    def _compensate(self, workflow: WorkflowExecution) -> None:
        """Run compensation for completed steps in reverse order.

        Each compensation function is wrapped in _run_with_timeout using
        its step's compensation_timeout_ms policy. If compensation times
        out, the step is marked COMPENSATION_FAILED and escalation policy
        is honored.
        """
        completed_steps = [
            s for s in workflow.execution_order
            if workflow.steps[s].status == WorkflowStepStatus.SUCCEEDED
        ]

        for step_id in reversed(completed_steps):
            step = workflow.steps[step_id]
            if not step.compensate_fn:
                logger.warning(f"No compensation function for step {step_id}")
                step.status = WorkflowStepStatus.COMPENSATION_FAILED
                continue

            step.status = WorkflowStepStatus.COMPENSATING
            timeout_ms = step.compensation_policy.compensation_timeout_ms
            try:
                # Pass original result and context to compensation
                result = _run_with_timeout(
                    step.compensate_fn,
                    (workflow.context, step.result),
                    timeout_ms,
                )
                step.compensation_result = result
                step.status = WorkflowStepStatus.COMPENSATED
                logger.info(f"Compensated step {step_id}")
                
                # Persist after each compensation
                if self.job_repository:
                    import asyncio
                    asyncio.create_task(self.job_repository.save_workflow(workflow))
            except Exception as e:
                logger.error(f"Compensation failed for step {step_id}: {e}")
                step.status = WorkflowStepStatus.COMPENSATION_FAILED
                step.error = str(e)

                # Check policy for escalation
                policy = step.compensation_policy
                if policy.requires_manual_approval:
                    logger.critical(f"Manual approval required for compensation of {step_id}")
                    workflow.status = "requires_manual_approval"
            
            # Persist workflow after compensation phase
            self._persist_state(workflow)

    def get_workflow(self, workflow_id: str) -> Optional[WorkflowExecution]:
        with self._lock:
            workflow = self._workflows.get(workflow_id)
            if workflow:
                return workflow
        
        # Fallback to repository
        if self.job_repository:
            import asyncio
            try:
                loop = asyncio.get_running_loop()
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self.job_repository.get_workflow(workflow_id))
                    return future.result()
            except RuntimeError:
                return asyncio.run(self.job_repository.get_workflow(workflow_id))
        return None

    def list_workflows(self) -> List[WorkflowExecution]:
        with self._lock:
            workflows = list(self._workflows.values())
        
        # Merge with repository if available
        if self.job_repository:
            try:
                import asyncio
                try:
                    loop = asyncio.get_running_loop()
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(asyncio.run, self.job_repository.list_workflows())
                        repo_workflows = future.result()
                except RuntimeError:
                    repo_workflows = asyncio.run(self.job_repository.list_workflows())
                # Merge avoiding duplicates
                seen = {w.workflow_id for w in workflows}
                for w in repo_workflows:
                    if w.workflow_id not in seen:
                        workflows.append(w)
            except Exception as e:
                # Degrade to in-memory view, but never silently.
                logger.warning(f"list_workflows: repository merge failed: {e}")
        
        return workflows


# Convenience function for simple workflows
def create_compensable_workflow(
    workflow_id: str,
    workflow_type: str,
    steps: List[Dict[str, Any]],
) -> WorkflowExecution:
    """
    Create a workflow from step definitions.
    
    Each step dict:
    {
        "step_id": "step1",
        "name": "Create User",
        "execute_fn": lambda inputs: {...},
        "compensate_fn": lambda context, result: {...},  # optional
        "depends_on": ["step0"],  # optional
        "provides": ["user_id"],  # optional
        "requires": ["email"],    # optional
        "compensation_policy": CompensationPolicy(...),  # optional
    }
    """
    workflow = WorkflowExecution(
        workflow_id=workflow_id,
        workflow_type=workflow_type,
    )
    for step_def in steps:
        step = WorkflowStep(
            step_id=step_def["step_id"],
            name=step_def["name"],
            execute_fn=step_def["execute_fn"],
            compensate_fn=step_def.get("compensate_fn"),
            compensation_policy=step_def.get("compensation_policy", CompensationPolicy()),
            depends_on=step_def.get("depends_on", []),
            provides=step_def.get("provides", []),
            requires=step_def.get("requires", []),
        )
        workflow.steps[step.step_id] = step
    return workflow


import threading


__all__ = [
    "CompensationAction",
    "WorkflowStepStatus",
    "CompensationPolicy",
    "WorkflowStep",
    "WorkflowExecution",
    "CompensationEngine",
    "create_compensable_workflow",
]
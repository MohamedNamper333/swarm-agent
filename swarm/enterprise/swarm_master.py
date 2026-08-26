"""
SwarmMaster v3.1 — Production orchestrator.

Clean rewrite (2026-08-25) after institutional audit found the original file
was assembled from copy-paste blocks with duplicated definitions, a missing
ServiceAccessor class, a stub _ensure_core_services shadowing the real one,
and seven attributes referenced but never initialized.

Pipeline: validate → safety → board → c-suite → routing → dispatch.
"""

import asyncio
import importlib
import logging
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def uuidv7() -> str:
    return str(uuid.uuid4())


# =============================================================================
# Lazy Service Accessor
# =============================================================================

class LazyServiceAccessor:
    """Lazy accessor for core modules using importlib to break static chains."""

    def __init__(self, service_registry: Any = None):
        self._cache: Dict[str, Any] = {}
        self._module_cache: Dict[str, Any] = {}
        self._service_registry = service_registry

    def _get_module(self, module_path: str):
        if module_path not in self._module_cache:
            self._module_cache[module_path] = importlib.import_module(module_path)
        return self._module_cache[module_path]

    def _get_attr(self, module_path: str, attr: str):
        return getattr(self._get_module(module_path), attr)

    def get_policy_engine(self):
        return self._get_attr("swarm.enterprise.core.policy.engine", "PolicyEngine")

    def get_cost_service(self):
        return self._get_attr("swarm.enterprise.core.budget.cost_estimation", "CostEstimationService")

    def get_budget_ledger(self):
        return self._get_attr("swarm.enterprise.core.budget.ledger", "BudgetLedger")

    def get_routing_engine(self):
        return self._get_attr("swarm.enterprise.core.routing.engine", "RoutingEngine")

    def get_control_plane(self):
        return self._get_attr("swarm.enterprise.core.plane.control_plane", "ControlPlane")

    def get_execution_plane(self):
        return self._get_attr("swarm.enterprise.core.plane.execution_plane", "ExecutionPlane")

    def get_audit_emitter(self):
        return self._get_attr("swarm.enterprise.core.orchestration.components", "AuditEmitter")

    # Departments (factory functions — call the result)
    def get_safety_dept(self):
        return self._get_attr("swarm.enterprise.safety", "create_safety_dept")

    def get_board(self):
        return self._get_attr("swarm.enterprise.board", "create_board")

    def get_csuite(self):
        return self._get_attr("swarm.enterprise.csuite", "create_c_suite")

    def get_code_dept(self):
        return self._get_attr("swarm.enterprise.code", "create_code_dept")

    def get_design_dept(self):
        return self._get_attr("swarm.enterprise.design", "create_design_dept")

    def get_video_dept(self):
        return self._get_attr("swarm.enterprise.video", "create_video_dept")

    def get_research_dept(self):
        return self._get_attr("swarm.enterprise.research", "create_research_dept")

    def get_data_dept(self):
        return self._get_attr("swarm.enterprise.data", "create_data_dept")

    def get_language_dept(self):
        return self._get_attr("swarm.enterprise.language", "create_language_dept")

    def get_knowledge_dept(self):
        return self._get_attr("swarm.enterprise.knowledge", "create_knowledge_dept")



# Keyword table for legacy dept routing (module-level contract used by tests
# and external callers; the production path is RoutingEngine.route()).
_DEPT_ROUTING_KEYWORDS: Dict[str, List[str]] = {
    "code": ["code", "python", "function", "script", "bug", "refactor",
             "implement", "api", "database", "sql"],
    "design": ["design", "logo", "ui", "ux", "brand", "color", "layout"],
    "video": ["video", "animation", "render", "clip", "motion"],
    "research": ["research", "analyze", "papers", "study", "investigate"],
    "data": ["data", "dataset", "datasets", "metrics", "statistics",
             "chart", "sales", "pipeline", "analytics", "warehouse"],
    "language": ["translate", "translation", "localize", "language"],
    "knowledge": ["search", "docs", "documentation", "knowledge", "retrieval"],
    "safety": ["safety", "moderation", "toxic", "content check"],
}
DEPT_ROUTING_KEYWORDS = _DEPT_ROUTING_KEYWORDS

# =============================================================================
# Core Models
# =============================================================================

class DeptType(str, Enum):
    CODE = "code"
    DESIGN = "design"
    VIDEO = "video"
    RESEARCH = "research"
    DATA = "data"
    LANGUAGE = "language"
    KNOWLEDGE = "knowledge"
    SAFETY = "safety"
    GENERAL = "general"


@dataclass
class SwarmRequest:
    question: str
    type: str = "general"
    context: Dict[str, Any] = field(default_factory=dict)
    require_human_review: bool = False
    bypass_safety: bool = False
    idempotency_key: Optional[str] = None
    tenant_id: str = "default"
    principal_id: str = "user"
    capability: Optional[str] = None
    priority: int = 0
    timeout_seconds: Optional[int] = None
    trace_id: Optional[str] = None


@dataclass
class SwarmResult:
    request_id: str
    execution_id: str
    trace_id: str
    policy_decision: str
    execution_state: str
    final_outcome: Optional[str] = None
    stages: Dict[str, Any] = field(default_factory=dict)
    output: Optional[Any] = None
    vetoed_by: Optional[str] = None
    veto_reason: Optional[str] = None
    executed_by: Optional[str] = None
    cost_estimate: Optional[Dict[str, Any]] = None
    actual_cost: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    dispatched_to: Optional[str] = None
    dispatch_time_ms: int = 0

    @property
    def verdict(self) -> str:
        return self.policy_decision

    @property
    def final_decision(self) -> str:
        return self.policy_decision


# =============================================================================
# Default dispatchable agent executor
# =============================================================================

class ChainAgentExecutor:
    """Executes tasks via the enterprise model fallback chain.

    payload["question"] is sent to the role's primary model; on failure the
    chain's fallback levels are used automatically. Duck-types the
    AgentExecutor interface (execute / execute_async / health_check).
    """

    def __init__(self):
        from swarm.enterprise.core.fallback_chain import FallbackChainExecutor
        self._chain = FallbackChainExecutor()

    def execute(self, task) -> Any:
        from swarm.enterprise.core.orchestration.agent_registry import AgentTaskResult
        t0 = datetime.now(timezone.utc)
        agent_type = getattr(task, 'agent_type', '')
        role = agent_type.replace('chain_', '', 1) if agent_type.startswith('chain_') \
            else 'research_director'
        payload = getattr(task, 'payload', {}) or {}
        prompt = str(payload.get("question", ""))
        context = payload.get("context") or {}
        if context:
            prompt = f"{prompt}\n\nContext: {context}"
        try:
            result = self._chain.execute(role, prompt)
        except Exception as e:
            logger.exception("ChainAgentExecutor failed: %s", e)
            return AgentTaskResult(task_id=task.task_id, success=False,
                                   error=str(e), error_code="EXECUTION_ERROR")
        latency_ms = int((datetime.now(timezone.utc) - t0).total_seconds() * 1000)
        return AgentTaskResult(
            task_id=task.task_id,
            success=result.success,
            output=result.output,
            error=result.error,
            execution_time_ms=latency_ms,
            metadata={"role": role, "model": result.chosen_model,
                      "level": result.level_used},
        )

    async def execute_async(self, task) -> Any:
        return await asyncio.to_thread(self.execute, task)

    def health_check(self) -> Any:
        from swarm.enterprise.core.orchestration.agent_registry import (
            AgentHealth, AgentStatus,
        )
        return AgentHealth(
            agent_id="chain-executor", instance_id="chain-executor",
            status=AgentStatus.IDLE, is_healthy=True,
            details={"executor": "chain"},
        )


# =============================================================================
# SwarmMaster
# =============================================================================

class SwarmMaster:
    """Production orchestrator with lazy service wiring."""

    CAPABILITY_ROLES = {
        # AgentCapability enum values are lowercase
        "code_generation": "coder_1",
        "design": "design_director",
        "research": "researcher_1",
        "data_analysis": "data_analyst",
        "translation": "translator",
        "knowledge_retrieval": "fact_checker",
        "safety_check": "safety_director",
        "text_generation": "research_director",
    }

    def __init__(
        self,
        cfo_budget_limit: float = float("inf"),
        tenant_id: str = "default",
        service_registry: Any = None,
        validator: Any = None,
        safety_gate: Any = None,
        board_coordinator: Any = None,
        executive_coordinator: Any = None,
        cost_controller: Any = None,
        result_assembler: Any = None,
        audit_emitter: Any = None,
        routing_engine: Any = None,
        policy_engine: Any = None,
        control_plane: Any = None,
        execution_plane: Any = None,
        auth_policy: Any = None,
        cost_service: Any = None,
        budget_ledger: Any = None,
        board: Any = None,
        csuite: Any = None,
        depts: Dict[str, Any] = None,
        memory_fabric: Any = None,
    ):
        self.validator = validator
        self.safety_gate = safety_gate
        self.board_coordinator = board_coordinator
        self.executive_coordinator = executive_coordinator
        self.cost_controller = cost_controller
        self.result_assembler = result_assembler
        self.audit_emitter = audit_emitter
        self.routing_engine = routing_engine
        self.policy_engine = policy_engine
        self.control_plane = control_plane
        self.execution_plane = execution_plane
        self.auth_policy = auth_policy
        self.cost_service = cost_service
        self.budget_ledger = budget_ledger
        self.board = board
        self.csuite = csuite
        self.depts = depts
        self.memory_fabric = memory_fabric

        self._lock = threading.Lock()
        self._lazy = LazyServiceAccessor(service_registry)
        self.service_accessor = self._lazy

        self._ensure_core_services()
        self._init_components(
            board=board, csuite=csuite, depts=depts,
            cfo_budget_limit=cfo_budget_limit, tenant_id=tenant_id,
        )
        self._init_infrastructure()
        self._init_budget_account(tenant_id, cfo_budget_limit)

    # ------------------------------------------------------------------
    # Lazy initialization
    # ------------------------------------------------------------------

    def _ensure_core_services(self):
        """Instantiate core services once (classes, not classes-as-singletons)."""
        if self.validator is None:
            RequestValidator = self._lazy._get_attr(
                "swarm.enterprise.core.orchestration.components", "RequestValidator")
            self.validator = RequestValidator()

        if self.routing_engine is None:
            self.routing_engine = self._lazy.get_routing_engine()()

        if self.policy_engine is None:
            self.policy_engine = self._lazy.get_policy_engine()()

        if self.auth_policy is None:
            AuthorizationPolicy = self._lazy._get_attr(
                "swarm.enterprise.core.auth", "AuthorizationPolicy")
            self.auth_policy = AuthorizationPolicy()

        if self.cost_service is None:
            self.cost_service = self._lazy.get_cost_service()()

        if self.budget_ledger is None:
            self.budget_ledger = self._lazy.get_budget_ledger()()

        if self.control_plane is None:
            ControlPlane = self._lazy.get_control_plane()
            self.control_plane = ControlPlane(
                budget_ledger=self.budget_ledger,
                cost_estimation=self.cost_service,
                policy_engine=self.policy_engine,
                routing_engine=self.routing_engine,
            )

        if self.execution_plane is None:
            self.execution_plane = self._lazy.get_execution_plane()()

        if self.audit_emitter is None:
            AuditEmitter = self._lazy.get_audit_emitter()
            try:
                self.audit_emitter = AuditEmitter()
            except TypeError:
                self.audit_emitter = AuditEmitter.__new__(AuditEmitter)

    def _init_components(self, board, csuite, depts, cfo_budget_limit, tenant_id):
        """Build tier 1-4 org structure. Factories must be CALLED."""
        self.safety_dept = self._lazy.get_safety_dept()()
        self.board = board or self._lazy.get_board()()
        self.csuite = csuite or self._lazy.get_csuite()()
        self.depts = depts or {
            "code": self._lazy.get_code_dept()(),
            "design": self._lazy.get_design_dept()(),
            "video": self._lazy.get_video_dept()(),
            "research": self._lazy.get_research_dept()(),
            "data": self._lazy.get_data_dept()(),
            "language": self._lazy.get_language_dept()(),
            "knowledge": self._lazy.get_knowledge_dept()(),
            "safety": self.safety_dept,
        }
        self._init_infrastructure()

    def _init_infrastructure(self):
        """Agent registry + default chain agents + job system + DLQ + metrics."""
        from swarm.enterprise.core.orchestration.agent_registry import (
            create_agent_registry, AgentCapability,
        )
        from swarm.enterprise.core.job.repository import create_job_repository
        from swarm.enterprise.core.job.models import JobQueue
        from swarm.enterprise.core.job.compensation import CompensationEngine
        from swarm.enterprise.core.job.scheduler import JobScheduler
        from swarm.enterprise.core.job.dead_letter import DeadLetterQueue
        from swarm.enterprise.core.job.metrics import MetricsRegistry
        from swarm.enterprise.core.job.worker import WorkerPool

        self.job_repository = getattr(self, "job_repository", None) \
            or create_job_repository(backend="memory")
        self.queue = getattr(self, "queue", None) or JobQueue()
        self.dlq = getattr(self, "dlq", None) or DeadLetterQueue(self.job_repository, self.queue)
        self.metrics = getattr(self, "metrics", None) or MetricsRegistry()
        self.compensation_engine = getattr(self, "compensation_engine", None) \
            or CompensationEngine(self.job_repository)
        self.job_scheduler = getattr(self, "job_scheduler", None) \
            or JobScheduler(self.job_repository, self.queue)
        self.worker_pool = getattr(self, "worker_pool", None) or WorkerPool()
        self.agent_registry = getattr(self, "agent_registry", None) or create_agent_registry()

        if not getattr(self, "_default_agents_registered", False):
            executor = ChainAgentExecutor()
            for cap_name, role in self.CAPABILITY_ROLES.items():
                agent_type = f"chain_{role}"
                try:
                    self.agent_registry.register_agent_type(
                        agent_type=agent_type,
                        name=f"Chain agent ({role})",
                        description=f"Dispatchable agent using fallback chain role '{role}'",
                        capabilities=[AgentCapability(cap_name)],
                        department="general",
                    )
                    instance = self.agent_registry.register_instance(
                        agent_type=agent_type,
                        tenant_id="default",
                        max_concurrent_tasks=4,
                        executor=executor,
                    )
                    self.agent_registry.start_instance(instance.instance_id)
                except ValueError:
                    pass  # already registered (e.g., shared registry across instances)
            self._default_agents_registered = True

    def _init_budget_account(self, tenant_id: str, limit: float):
        from decimal import Decimal
        account_id = f"budget-{tenant_id}"
        try:
            self.budget_ledger.create_account(
                account_id=account_id,
                tenant_id=tenant_id,
                budget_type="DAILY",
                limit=Decimal(str(limit)) if limit != float("inf") else Decimal("1000000"),
            )
        except ValueError:
            pass  # Account already exists

    # ------------------------------------------------------------------
    # Main processing pipeline
    # ------------------------------------------------------------------

    @staticmethod
    async def _maybe_await(value):
        import inspect as _inspect
        if _inspect.isawaitable(value):
            return await value
        return value

    def process(self, request: SwarmRequest,
                authorization_context: Any = None):
        """Process request (sync-friendly). Returns SwarmResult directly when no
        event loop is running; returns an awaitable inside a running loop."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self._process_impl(request, authorization_context))
        return self._process_impl(request, authorization_context)

    async def _process_impl(self, request: SwarmRequest,
                            authorization_context: Any = None) -> SwarmResult:
        """Process a request through safety → board → c-suite → routing → dispatch."""
        ExecutionContextMod = importlib.import_module(
            "swarm.enterprise.core.execution.context")
        exec_context = ExecutionContextMod.ExecutionContext.create(
            tenant_id=request.tenant_id,
            principal_id=request.principal_id,
            authorization_context=authorization_context,
        )
        ExecutionContextMod.set_current_context(exec_context)

        if authorization_context is None:
            Principal = self._lazy._get_attr("swarm.enterprise.core.auth", "Principal")
            AuthorizationContext = self._lazy._get_attr(
                "swarm.enterprise.core.auth", "AuthorizationContext")
            principal = Principal.user(request.principal_id, request.tenant_id)  # noqa: F841
            authorization_context = AuthorizationContext.for_user(
                user_id=request.principal_id, tenant_id=request.tenant_id)

        # 1. Validate
        if self.validator:
            valid, error = self.validator.validate(request)
            if not valid:
                return self._error_result(request, error)

        stages: Dict[str, Any] = {}
        final_output = None
        policy_decision = "approved"
        execution_state = "pending"
        final_outcome = None
        executed_by = None
        vetoed_by = None
        veto_reason = None
        dispatched_to = None
        dispatch_time_ms = 0
        cost_estimate = self._estimate_cost(request)

        try:
            # Stage 1: Safety
            safety_gate = self._get_safety_gate()
            safety_result = await self._maybe_await(
                safety_gate.check(request, exec_context, authorization_context))
            stages["safety"] = safety_result
            if not safety_result.success:
                return self._build_result(
                    exec_context, stages, "vetoed", "failed", "failure",
                    vetoed_by="safety_dept", veto_reason=safety_result.error,
                    cost_estimate=cost_estimate)

            # Stage 2: Board
            board_coordinator = self._get_board_coordinator()
            board_result = await self._maybe_await(
                board_coordinator.deliberate(request, exec_context, authorization_context))
            stages["board"] = board_result
            if not board_result.success:
                return self._build_result(
                    exec_context, stages, "vetoed", "failed", "failure",
                    vetoed_by=(board_result.output or {}).get("vetoed_by", "board"),
                    veto_reason=board_result.error,
                    cost_estimate=cost_estimate)

            # Stage 3: C-Suite
            exec_coordinator = self._get_executive_coordinator()
            exec_result = await self._maybe_await(
                exec_coordinator.decide(request, None, exec_context, authorization_context))
            stages["csuite"] = exec_result
            if not exec_result.success:
                verdict = (exec_result.output or {}).get("verdict")
                policy_decision = "vetoed" if verdict == "vetoed" else "rejected"
                return self._build_result(
                    exec_context, stages, policy_decision, "failed", "failure",
                    vetoed_by=(exec_result.output or {}).get("vetoed_by", "csuite"),
                    veto_reason=exec_result.error,
                    cost_estimate=cost_estimate)

            # Stage 4: Routing
            routing_decision = self.routing_engine.route(
                question=request.question,
                explicit_type=request.type if request.type != "general" else None,
                context={},
            )
            stages["routing"] = {
                "stage_name": "routing",
                "success": True,
                "output": routing_decision.to_dict(),
                "error": None,
                "metadata": {},
            }

            # Stage 5: Dispatch
            dispatch_start = datetime.now(timezone.utc)
            capability = self._map_routing_to_capability(routing_decision)
            merged_context = dict(request.context or {})
            dispatch_start_dt = dispatch_start
            dispatch_result = await self._dispatch_task(
                capability=capability, request=request,
                context=merged_context, routing=routing_decision)
            dispatch_time_ms = int((datetime.now(timezone.utc)
                                    - dispatch_start_dt).total_seconds() * 1000)
            dispatched_to = dispatch_result.instance_id if dispatch_result else None
            del dispatch_start

            stages["execution"] = {
                "stage_name": "execution",
                "success": bool(dispatch_result and dispatch_result.success),
                "output": (dispatch_result.result.output
                           if dispatch_result and dispatch_result.result else None),
                "error": dispatch_result.error if dispatch_result else "no dispatch result",
                "metadata": {},
            }

            if not dispatch_result or not dispatch_result.success:
                policy_decision = "failed"
                execution_state = "failed"
                final_outcome = "failure"
                veto_reason = dispatch_result.error if dispatch_result else "Dispatch failed"
            else:
                execution_state = "succeeded"
                final_outcome = "success"
                executed_by = (routing_decision.primary_department.value
                               if hasattr(routing_decision, 'primary_department')
                               else "unknown")
                final_output = (dispatch_result.result.output
                                if dispatch_result and dispatch_result.result else None)
                policy_decision = "approved"

        except Exception as e:
            logger.exception("SwarmMaster processing error: %s", e)
            policy_decision = "error"
            execution_state = "failed"
            final_outcome = "failure"
            veto_reason = f"Orchestration error: {e}"

        return self._build_result(
            exec_context, stages, policy_decision, execution_state, final_outcome,
            vetoed_by=vetoed_by, veto_reason=veto_reason,
            cost_estimate=cost_estimate, output=final_output,
            executed_by=executed_by, dispatched_to=dispatched_to,
            dispatch_time_ms=dispatch_time_ms,
        )

    # ------------------------------------------------------------------
    # Stage helpers
    # ------------------------------------------------------------------

    def _estimate_cost(self, request: SwarmRequest) -> Dict[str, Any]:
        base = {"estimated_total": "0", "currency": "USD"}
        if not self.cost_service:
            return base
        try:
            CostEstimationRequest = self._lazy._get_attr(
                "swarm.enterprise.core.budget.cost_estimation", "CostEstimationRequest")
            est = self.cost_service.estimate(CostEstimationRequest(
                provider="nvidia_nim",
                model="nvidia/nemotron-3-super-120b-a12b",
                estimated_input_tokens=2000,
                estimated_output_tokens=4000,
                estimated_tool_calls=5,
                tenant_id=getattr(request, 'tenant_id', 'default'),
            ))
            total = getattr(est, 'total', None)
            return {"estimated_total": str(total) if total is not None else "0",
                    "currency": getattr(est, 'currency', 'USD')}
        except Exception as e:
            logger.warning("Cost estimation failed (non-fatal): %s", e)
            return {**base, "error": str(e)}

    def _get_safety_gate(self):
        SafetyGate = self._lazy._get_attr(
            "swarm.enterprise.core.orchestration.components", "SafetyGate")
        return (self.safety_gate if self.safety_gate
                else SafetyGate(self.safety_dept, self.policy_engine))

    def _get_board_coordinator(self):
        BoardCoordinator = self._lazy._get_attr(
            "swarm.enterprise.core.orchestration.components", "BoardCoordinator")
        return self.board_coordinator or BoardCoordinator(self.board)

    def _get_executive_coordinator(self):
        ExecutiveCoordinator = self._lazy._get_attr(
            "swarm.enterprise.core.orchestration.components", "ExecutiveCoordinator")
        return self.executive_coordinator or ExecutiveCoordinator(
            self.csuite, self.cost_service, self.budget_ledger)


    # ------------------------------------------------------------------
    # Backward-compatible routing contract (tests + legacy callers)
    # ------------------------------------------------------------------

    DEPT_ROUTING_KEYWORDS = _DEPT_ROUTING_KEYWORDS

    def _route_to_dept(self, request: SwarmRequest) -> DeptType:
        """Legacy keyword-based dept routing, backed by the real engine when
        explicit types are given. Returns DeptType for compatibility."""
        if request.type and request.type != "general":
            try:
                return DeptType(request.type)
            except ValueError:
                pass
        q = (request.question or "").lower()
        best_dept, best_score = DeptType.GENERAL, 0
        for dept_str, keywords in self.DEPT_ROUTING_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in q)
            if score > best_score:
                best_dept, best_score = DeptType(dept_str), score
        return best_dept

    def _map_routing_to_capability(self, routing_decision) -> str:
        dept = (routing_decision.primary_department.value
                if hasattr(routing_decision, 'primary_department')
                else str(getattr(routing_decision, 'department', 'general')))
        capability_map = {
            "code": "code_generation",
            "design": "design",
            "video": "code_generation",
            "research": "research",
            "data": "data_analysis",
            "language": "translation",
            "knowledge": "knowledge_retrieval",
            "safety": "safety_check",
        }
        return capability_map.get(dept, "text_generation")

    async def _dispatch_task(self, capability: str, request: Any,
                             context: Dict[str, Any], routing: Any) -> Any:
        create_task_dispatcher = self._lazy._get_attr(
            "swarm.enterprise.core.orchestration.task_dispatcher", "create_task_dispatcher")
        DispatchConfig = self._lazy._get_attr(
            "swarm.enterprise.core.orchestration.task_dispatcher", "DispatchConfig")
        DispatchStrategy = self._lazy._get_attr(
            "swarm.enterprise.core.orchestration.task_dispatcher", "DispatchStrategy")

        if not hasattr(self, '_task_dispatcher') or self._task_dispatcher is None:
            self._task_dispatcher = create_task_dispatcher(
                self.agent_registry,
                DispatchConfig(
                    strategy=DispatchStrategy.LEAST_LOADED,
                    enable_circuit_breaker=True,
                    enable_fallback=True,
                ),
            )

        from swarm.enterprise.core.orchestration.agent_registry import AgentCapability
        capability_enum = capability if isinstance(capability, AgentCapability) \
            else AgentCapability(str(capability).lower())

        result = self._task_dispatcher.dispatch(
            capability=capability_enum,
            payload={
                "question": request.question,
                "context": context,
                "routing": routing.to_dict() if hasattr(routing, 'to_dict') else {},
            },
            context=context,
            priority=request.priority,
            timeout_seconds=request.timeout_seconds,
            tenant_id=request.tenant_id,
            trace_id=request.trace_id,
        )
        return await self._maybe_await(result)

    # ------------------------------------------------------------------
    # Result building
    # ------------------------------------------------------------------

    def _create_result(self, **kwargs) -> SwarmResult:
        return SwarmResult(
            request_id=kwargs.get("request_id", ""),
            execution_id=kwargs.get("execution_id", ""),
            trace_id=kwargs.get("trace_id", ""),
            policy_decision=kwargs.get("policy_decision", "unknown"),
            execution_state=kwargs.get("execution_state", "unknown"),
            final_outcome=kwargs.get("final_outcome"),
            stages=kwargs.get("stages", {}),
            output=kwargs.get("output"),
            executed_by=kwargs.get("executed_by"),
            vetoed_by=kwargs.get("vetoed_by"),
            veto_reason=kwargs.get("veto_reason"),
            cost_estimate=kwargs.get("cost_estimate"),
            actual_cost=kwargs.get("actual_cost"),
            metadata=kwargs.get("metadata", {}),
        )

    def _build_result(self, exec_context, stages, policy_decision, execution_state,
                      final_outcome, vetoed_by=None, veto_reason=None,
                      cost_estimate=None, output=None, executed_by=None,
                      dispatched_to=None, dispatch_time_ms=0) -> SwarmResult:
        ResultAssembler = self._lazy._get_attr(
            "swarm.enterprise.core.orchestration.components", "ResultAssembler")
        assembler = ResultAssembler(result_factory=self._create_result)
        normalized_stages = {}
        for k, v in (stages or {}).items():
            if hasattr(v, 'stage_name'):
                normalized_stages[k] = {
                    "stage_name": v.stage_name, "success": v.success,
                    "output": v.output, "error": v.error, "metadata": v.metadata,
                }
            elif isinstance(v, dict):
                normalized_stages[k] = dict(v)
            else:
                normalized_stages[k] = {"raw": str(v)}
        return assembler.assemble(
            request_id=exec_context.identity.request_id,
            execution_id=exec_context.identity.execution_id,
            trace_id=exec_context.identity.trace_id,
            stages=normalized_stages,
            final_output=output,
            policy_decision=policy_decision,
            execution_state=execution_state,
            final_outcome=final_outcome,
            executed_by=executed_by,
            vetoed_by=vetoed_by,
            veto_reason=veto_reason,
            cost_estimate=cost_estimate,
            metadata={
                "tenant_id": exec_context.tenant_id,
                "principal_id": exec_context.principal_id,
                "dispatched_to": dispatched_to,
                "dispatch_time_ms": dispatch_time_ms,
            },
        )

    def _error_result(self, request, error: str) -> SwarmResult:
        ExecutionContextMod = importlib.import_module(
            "swarm.enterprise.core.execution.context")
        exec_context = ExecutionContextMod.ExecutionContext.create(
            tenant_id=request.tenant_id, principal_id=request.principal_id)
        return self._build_result(
            exec_context, {}, "error", "failed", "failure", veto_reason=error)

    # ------------------------------------------------------------------
    # Agent management API
    # ------------------------------------------------------------------

    def register_agent(self, agent_type: str, name: str, description: str,
                       capabilities: List[str], department: str,
                       executor: Any = None, max_concurrent: int = 1,
                       tenant_id: str = "default") -> str:
        from swarm.enterprise.core.orchestration.agent_registry import AgentCapability
        self.agent_registry.register_agent_type(
            agent_type=agent_type, name=name, description=description,
            capabilities=[AgentCapability(c) for c in capabilities],
            department=department,
        )
        instance = self.agent_registry.register_instance(
            agent_type=agent_type, tenant_id=tenant_id,
            max_concurrent_tasks=max_concurrent, executor=executor)
        self.agent_registry.start_instance(instance.instance_id)
        return instance.instance_id

    def unregister_agent(self, instance_id: str) -> bool:
        return self.agent_registry.deregister_instance(instance_id)

    def get_agent_status(self, instance_id: str) -> Optional[Dict[str, Any]]:
        instance = self.agent_registry.get_instance(instance_id)
        if not instance:
            return None
        health = self.agent_registry.health_check(instance_id)
        return {
            "instance_id": instance.instance_id,
            "agent_type": instance.metadata.agent_type,
            "name": instance.metadata.name,
            "department": instance.metadata.department,
            "status": instance.status.value,
            "current_load": instance.current_load,
            "active_tasks": instance.active_task_count,
            "max_concurrent": instance.max_concurrent_tasks,
            "total_processed": instance.total_tasks_processed,
            "total_failed": instance.total_tasks_failed,
            "health": {
                "is_healthy": health.is_healthy if health else False,
                "details": health.details if health else {},
            } if health else None,
        }

    def list_agents(self, tenant_id: Optional[str] = None) -> Dict[str, Any]:
        """Org-structure view: board(5), csuite(7) and per-department rosters."""
        def _roster(names):
            return [{"role": n} for n in names]
        view = {
            "board": _roster(["chairman", "strategy_advisor", "ethics_advisor",
                              "risk_advisor", "user_advisor"]),
            "csuite": _roster(["ceo", "cto", "cfo", "coo", "cmo", "chro", "clo"]),
        }
        for dept in ("code", "design", "video", "research",
                     "data", "language", "knowledge", "safety"):
            try:
                dept_obj = self.depts.get(dept)
                roles = getattr(dept_obj, "roles", None) or                         getattr(dept_obj, "agents", None) or []
                if isinstance(roles, dict):
                    names = list(roles.keys())
                else:
                    names = [getattr(r, 'role', getattr(r, 'name', str(r)))
                             for r in roles]
                view[dept] = _roster(names) if names else []
            except Exception:
                view[dept] = []
        return view

    def list_agent_instances(self, tenant_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Runtime agent instances from the dispatcher registry."""
        return [
            {
                "instance_id": i.instance_id,
                "agent_type": i.metadata.agent_type,
                "name": i.metadata.name,
                "department": i.metadata.department,
                "status": i.status.value,
                "capabilities": [c.value for c in i.metadata.capabilities],
                "current_load": i.current_load,
                "active_tasks": i.active_task_count,
                "total_processed": i.total_tasks_processed,
            }
            for i in self.agent_registry.list_instances(tenant_id=tenant_id)
        ]

    # ------------------------------------------------------------------
    # Workflows & jobs
    # ------------------------------------------------------------------

    def create_workflow(self, workflow_id: str, workflow_type: str,
                        steps: List[Dict]) -> Any:
        create_compensable_workflow = self._lazy._get_attr(
            "swarm.enterprise.core.job.compensation", "create_compensable_workflow")
        workflow = create_compensable_workflow(workflow_id, workflow_type, steps)
        self.compensation_engine.register_workflow(workflow)
        return workflow

    def execute_workflow(self, workflow_id: str) -> Any:
        return self.compensation_engine.execute(workflow_id)

    def schedule_job(self, job_type: str, payload: Dict[str, Any],
                     run_at: Optional[datetime] = None,
                     interval_seconds: Optional[int] = None,
                     cron_expression: Optional[str] = None,
                     max_runs: Optional[int] = None,
                     tenant_id: str = "default") -> str:
        schedule_once = self._lazy._get_attr("swarm.enterprise.core.job.scheduler", "schedule_once")
        schedule_interval = self._lazy._get_attr("swarm.enterprise.core.job.scheduler", "schedule_interval")
        schedule_cron = self._lazy._get_attr("swarm.enterprise.core.job.scheduler", "schedule_cron")
        if run_at:
            return schedule_once(self.job_scheduler, job_type, payload, run_at, tenant_id=tenant_id)
        elif interval_seconds:
            return schedule_interval(self.job_scheduler, job_type, payload,
                                     interval_seconds, max_runs=max_runs, tenant_id=tenant_id)
        elif cron_expression:
            return schedule_cron(self.job_scheduler, job_type, payload,
                                 cron_expression, max_runs=max_runs, tenant_id=tenant_id)
        raise ValueError("Must specify run_at, interval_seconds, or cron_expression")

    # ------------------------------------------------------------------
    # Memory (optional fabric)
    # ------------------------------------------------------------------

    def write_memory(self, content: Dict[str, Any], layer: str = "WORKING",
                     tenant_id: str = "default", actor_id: str = "swarm_master",
                     trust_level: str = "AGENT_GENERATED",
                     tags: Optional[set] = None) -> str:
        MemoryV2 = importlib.import_module("swarm.memory.v2")
        entry = MemoryV2.MemoryEntry(
            metadata=MemoryV2.MemoryMetadata(
                layer=MemoryV2.MemoryLayer(layer),
                tenant_id=tenant_id, actor_id=actor_id,
                trust_level=MemoryV2.TrustLevel(trust_level),
                tags=tags or set(),
            ),
            content=content,
        )
        if not self.memory_fabric:
            raise RuntimeError("Memory fabric not configured; cannot write memory")
        write = MemoryV2.MemoryWrite(entry=entry)
        asyncio.run(self.memory_fabric._repository.write(write))
        return entry.metadata.memory_id

    def search_memory(self, query: str, tenant_id: str = "default",
                      top_k: int = 10, mode: str = "HYBRID") -> List[Dict[str, Any]]:
        if not self.memory_fabric or not hasattr(self.memory_fabric, 'get_search_manager'):
            return []
        search_manager = self.memory_fabric.get_search_manager()
        if not search_manager:
            return []
        MemoryV2 = importlib.import_module("swarm.memory.v2")
        results = asyncio.run(search_manager.search(MemoryV2.SearchRequest(
            query=query, tenant_id=tenant_id, top_k=top_k,
            mode=MemoryV2.SearchMode(mode))))
        return [
            {"content": r.entry.content, "score": r.score,
             "layer": getattr(getattr(r.entry, 'metadata', None), 'layer', None)}
            for r in results
        ]

    # ------------------------------------------------------------------
    # Status / health
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        # Department agent counts from the enterprise model registry
        try:
            from swarm.enterprise.core.model_registry_v2 import EnterpriseModelRegistry as _EMR
            reg_summary = _EMR.summary()
            department_agents = sum(
                len(roles) for tier, roles in reg_summary.items()
                if tier not in ('total_chains', 'unique_models', 'board', 'c_suite')
            )
            total_chains = reg_summary['total_chains']
        except Exception:
            department_agents = 0
            total_chains = 0

        status = {
            "version": "3.1",
            "board_agents": 5,
            "csuite_agents": 7,
            "department_agents": department_agents,
            "total_chains": total_chains,
            "departments": len(self.depts),
            "control_plane": "active",
            "execution_plane": "active",
            "routing_engine": "active",
            "policy_engine": "active",
            "audit_emitter": "active",
            "memory_v2": "active" if self.memory_fabric else "disabled",
            "job_system": "active",
            "job_scheduler": "active" if self.job_scheduler else "disabled",
            "dead_letter_queue": "active" if getattr(self, 'dlq', None) else "disabled",
            "agent_registry": "active",
            "task_dispatcher": "active" if getattr(self, '_task_dispatcher', None) else "lazy",
            "worker_pool": "active" if getattr(self, 'worker_pool', None) else "disabled",
            "metrics": "active" if getattr(self, 'metrics', None) else "disabled",
        }
        status["agents"] = self.agent_registry.get_stats()
        if hasattr(self.worker_pool, 'get_total_status'):
            status["worker_pool"] = self.worker_pool.get_total_status()
        return status

    def get_health(self) -> Dict[str, Any]:
        health: Dict[str, Any] = {"overall": "healthy", "components": {}}
        try:
            healthy = asyncio.run(self.memory_fabric.health_check()) if self.memory_fabric else False
            health["components"]["memory_v2"] = "healthy" if healthy else "disabled"
        except Exception:
            health["components"]["memory_v2"] = "unhealthy"
        try:
            healthy = asyncio.run(self.job_repository.health_check())
            health["components"]["job_repository"] = "healthy" if healthy else "unhealthy"
        except Exception as e:
            health["components"]["job_repository"] = f"degraded: {type(e).__name__}"

        agent_stats = self.agent_registry.get_stats()
        unhealthy_agents = agent_stats.get("by_status", {}).get("unhealthy", 0)
        health["components"]["agent_registry"] = ("degraded" if unhealthy_agents > 0
                                                  else "healthy")
        health["components"]["agent_registry_details"] = agent_stats

        if hasattr(self.worker_pool, 'get_total_status'):
            wp = self.worker_pool.get_total_status()
            health["components"]["worker_pool"] = ("healthy" if wp.get("running", False)
                                                   else "idle")
        unhealthy_count = sum(1 for v in health["components"].values()
                              if v == "unhealthy")
        if unhealthy_count > 0:
            health["overall"] = "degraded" if unhealthy_count < 3 else "unhealthy"
        return health


# Backward compatibility singleton
_master_instance: Optional[SwarmMaster] = None


def get_master() -> SwarmMaster:
    global _master_instance
    if _master_instance is None:
        _master_instance = SwarmMaster()
    return _master_instance


if __name__ == "__main__":
    async def _main():
        master = SwarmMaster()
        print("=== SwarmMaster v3.1 Status ===")
        for k, v in master.get_status().items():
            print(f"  {k}: {v}")
        print("\n=== Health ===")
        health = master.get_health()
        print(f"  Overall: {health['overall']}")
        request = SwarmRequest(
            question="Create a simple Python function for binary search",
            type="code", tenant_id="default", principal_id="test-user",
        )
        result = await master.process(request)
        print(f"\nDecision: {result.policy_decision} | State: {result.execution_state}")
        print(f"Output: {str(result.output)[:200]}")

    asyncio.run(_main())

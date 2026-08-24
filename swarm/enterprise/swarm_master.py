"""
SwarmMaster v3 — Production orchestrator with loose coupling via ServiceRegistry.
All core module access via lazy loading with importlib to break static import chains.
"""

import logging
import threading
import uuid
import importlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from datetime import datetime, timezone
import asyncio

logger = logging.getLogger(__name__)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def uuidv7() -> str:
    return str(uuid.uuid4())


# =============================================================================
# Lazy Service Accessor - Dynamic Imports via importlib
# =============================================================================

class LazyServiceAccessor:
    """Lazy accessor for core modules using importlib to break static import chains."""
    
    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._module_cache: Dict[str, Any] = {}
    
    def _get_module(self, module_path: str):
        """Dynamically import module using importlib."""
        if module_path not in self._module_cache:
            self._module_cache[module_path] = importlib.import_module(module_path)
        return self._module_cache[module_path]
    
    def _get_attr(self, module_path: str, attr: str):
        module = self._get_module(module_path)
        return getattr(module, attr)
    
    # =========================================================================
    # Core Module Accessors (Lazy Loading)
    # =========================================================================
    
    # Policy
    def get_policy_engine(self):
        return self._get_attr("swarm.enterprise.core.policy.engine", "PolicyEngine")
    
    # Budget
    def get_cost_service(self):
        return self._get_attr("swarm.enterprise.core.budget.cost_estimation", "CostEstimationService")
    
    def get_budget_ledger(self):
        return self._get_attr("swarm.enterprise.core.budget.ledger", "BudgetLedger")
    
    # Routing
    def get_routing_engine(self):
        return self._get_attr("swarm.enterprise.core.routing.engine", "RoutingEngine")
    
    # Plane
    def get_control_plane(self):
        return self._get_attr("swarm.enterprise.core.plane.control_plane", "ControlPlane")
    
    def get_execution_plane(self):
        return self._get_attr("swarm.enterprise.core.plane.execution_plane", "ExecutionPlane")
    
    # Orchestration Components
    def get_audit_emitter(self):
        return self._get_attr("swarm.enterprise.core.orchestration.components", "AuditEmitter")
    
    def get_safety_gate(self):
        return self._get_attr("swarm.enterprise.core.orchestration.components", "SafetyGate")
    
    def get_board_coordinator(self):
        return self._get_attr("swarm.enterprise.core.orchestration.components", "BoardCoordinator")
    
    def get_executive_coordinator(self):
        return self._get_attr("swarm.enterprise.core.orchestration.components", "ExecutiveCoordinator")
    
    def get_execution_coordinator(self):
        return self._get_attr("swarm.enterprise.core.orchestration.components", "ExecutionCoordinator")
    
    def get_cost_controller(self):
        return self._get_attr("swarm.enterprise.core.orchestration.components", "CostController")
    
    def get_result_assembler(self):
        return self._get_attr("swarm.enterprise.core.orchestration.components", "ResultAssembler")
    
    def get_safety_gate(self):
        return self._get_attr("swarm.enterprise.core.orchestration.components", "SafetyGate")
    
    def get_board_coordinator(self):
        return self._get_attr("swarm.enterprise.core.orchestration.components", "BoardCoordinator")
    
    def get_executive_coordinator(self):
        return self._get_attr("swarm.enterprise.core.orchestration.components", "ExecutiveCoordinator")
    
    def get_execution_coordinator(self):
        return self._get_attr("swarm.enterprise.core.orchestration.components", "ExecutionCoordinator")
    
    def get_cost_controller(self):
        return self._get_attr("swarm.enterprise.core.orchestration.components", "CostController")
    
    def get_result_assembler(self):
        return self._get_attr("swarm.enterprise.core.orchestration.components", "ResultAssembler")
    
    def get_safety_gate(self):
        return self._get_attr("swarm.enterprise.core.orchestration.components", "SafetyGate")
    
    def get_board_coordinator(self):
        return self._get_attr("swarm.enterprise.core.orchestration.components", "BoardCoordinator")
    
    def get_executive_coordinator(self):
        return self._get_attr("swarm.enterprise.core.orchestration.components", "ExecutiveCoordinator")
    
    def get_execution_coordinator(self):
        return self._get_attr("swarm.enterprise.core.orchestration.components", "ExecutionCoordinator")
    
    def get_cost_controller(self):
        return self._get_attr("swarm.enterprise.core.orchestration.components", "CostController")
    
    def get_result_assembler(self):
        return self._get_attr("swarm.enterprise.core.orchestration.components", "ResultAssembler")
    
    def get_safety_gate(self):
        return self._get_attr("swarm.enterprise.core.orchestration.components", "SafetyGate")
    
    def get_board_coordinator(self):
        return self._get_attr("swarm.enterprise.core.orchestration.components", "BoardCoordinator")
    
    def get_executive_coordinator(self):
        return self._get_attr("swarm.enterprise.core.orchestration.components", "ExecutiveCoordinator")
    
    def get_execution_coordinator(self):
        return self._get_attr("swarm.enterprise.core.orchestration.components", "ExecutionCoordinator")
    
    def get_cost_controller(self):
        return self._get_attr("swarm.enterprise.core.orchestration.components", "CostController")
    
    def get_result_assembler(self):
        return self._get_attr("swarm.enterprise.core.orchestration.components", "ResultAssembler")
    
    # Budget
    def get_budget_ledger(self):
        return self._get_attr("swarm.enterprise.core.budget.ledger", "BudgetLedger")
    
    def get_cost_service(self):
        return self._get_attr("swarm.enterprise.core.budget.cost_estimation", "CostEstimationService")
    
    # Routing
    def get_routing_engine(self):
        return self._get_attr("swarm.enterprise.core.routing.engine", "RoutingEngine")
    
    # Plane
    def get_control_plane(self):
        return self._get_attr("swarm.enterprise.core.plane.control_plane", "ControlPlane")
    
    def get_execution_plane(self):
        return self._get_attr("swarm.enterprise.core.plane.execution_plane", "ExecutionPlane")
    
    # Budget
    def get_budget_ledger(self):
        return self._get_attr("swarm.enterprise.core.budget.ledger", "BudgetLedger")
    
    def get_cost_service(self):
        return self._get_attr("swarm.enterprise.core.budget.cost_estimation", "CostEstimationService")
    
    # Routing
    def get_routing_engine(self):
        return self._get_attr("swarm.enterprise.core.routing.engine", "RoutingEngine")
    
    # Plane
    def get_control_plane(self):
        return self._get_attr("swarm.enterprise.core.plane.control_plane", "ControlPlane")
    
    def get_execution_plane(self):
        return self._get_attr("swarm.enterprise.core.plane.execution_plane", "ExecutionPlane")
    
    # Departments
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
    
    def get_safety_dept(self):
        return self._get_attr("swarm.enterprise.safety", "create_safety_dept")


# =============================================================================
# Core Models
# =============================================================================

import logging
import threading
import uuid
import importlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from datetime import datetime, timezone
import asyncio

logger = logging.getLogger(__name__)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def uuidv7() -> str:
    return str(uuid.uuid4())


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
# SwarmMaster v3 — Refactored with Dynamic Imports
# =============================================================================

class SwarmMaster:
    """Production orchestrator with loose coupling via dynamic imports."""

    def __init__(
        self,
        cfo_budget_limit: float = float("inf"),
        tenant_id: str = "default",
        service_registry: Optional[Any] = None,
        # Dependency injection for testability
        validator: Any = None,
        safety_gate: Any = None,
        board_coordinator: Any = None,
        executive_coordinator: Any = None,
        execution_coordinator: Any = None,
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
    ):
        # Service Registry
        from swarm.enterprise.core.interface import ServiceRegistry, get_service_registry
        from swarm.enterprise.core.interface.adapters import populate_service_registry
        
        self.service_registry = service_registry or get_service_registry()
        if not self.service_registry._services:
            from swarm.enterprise.core.interface.adapters import populate_service_registry
            populate_service_registry(self.service_registry)
        
        self.service_accessor = ServiceAccessor(self.service_registry)
        self._lazy = LazyServiceAccessor()
        
        # Core services - injected or lazy loaded
        self.validator = validator
        self.routing_engine = routing_engine
        self.policy_engine = policy_engine
        self.auth_policy = auth_policy
        self.cost_service = cost_service
        self.budget_ledger = budget_ledger
        self.control_plane = control_plane
        self.execution_plane = execution_plane
        self.auth_policy = auth_policy
        self.cost_service = cost_service
        self.budget_ledger = budget_ledger
        self.audit_emitter = audit_emitter
        
        self._init_components(
            board=board,
            csuite=csuite,
            depts=depts,
            cfo_budget_limit=cfo_budget_limit,
            tenant_id=tenant_id,
        )
        
        self._lock = threading.Lock()
        self._lazy = LazyServiceAccessor()

    # =========================================================================
    # Lazy Initialization
    # =========================================================================

    def _ensure_core_services(self):
        """Ensure core services are initialized."""
        if self.validator is None:
            from swarm.enterprise.core.orchestration.components import RequestValidator
            self.validator = RequestValidator()
        
        if self.routing_engine is None:
            self.routing_engine = self._lazy.get_routing_engine()
        
        if self.policy_engine is None:
            self.policy_engine = self._lazy.get_policy_engine()
        
        if self.auth_policy is None:
            from swarm.enterprise.core.auth import AuthorizationPolicy
            self.auth_policy = AuthorizationPolicy()
        
        if self.cost_service is None:
            self.cost_service = self._lazy.get_cost_service()
        
        if self.budget_ledger is None:
            self.budget_ledger = self._lazy.get_budget_ledger()
        
        if self.control_plane is None:
            self.control_plane = self._lazy.get_control_plane()
        
        if self.execution_plane is None:
            self.execution_plane = self._lazy.get_execution_plane()
        
        if self.auth_policy is None:
            from swarm.enterprise.core.auth import AuthorizationPolicy
            self.auth_policy = AuthorizationPolicy()
        
        if self.cost_service is None:
            self.cost_service = self._lazy.get_cost_service()
        
        if self.budget_ledger is None:
            self.budget_ledger = self._lazy.get_budget_ledger()
        
        if self.audit_emitter is None:
            self.audit_emitter = self._lazy.get_audit_emitter()

    def _init_components(
        self,
        board,
        csuite,
        depts,
        cfo_budget_limit,
        tenant_id,
    ):
        # Safety Dept (Tier 1 - VETO first)
        self.safety_dept = self._lazy.get_safety_dept()

        # Board (Tier 1 - strategic VETO)
        self.board = board or self._lazy.get_board()

        # C-Suite (Tier 2 - executive decision)
        self.csuite = csuite or self._lazy.get_csuite()

        # Departments (Tier 3+4 - execution)
        self.depts = depts or {
            "code": self._lazy.get_code_dept(),
            "design": self._lazy.get_design_dept(),
            "video": self._lazy.get_video_dept(),
            "research": self._lazy.get_research_dept(),
            "data": self._lazy.get_data_dept(),
            "language": self._lazy.get_language_dept(),
            "knowledge": self._lazy.get_knowledge_dept(),
            "safety": self._lazy.get_safety_dept(),
        }

        # Initialize budget account
        self._init_budget_account(tenant_id, cfo_budget_limit)

    def _init_budget_account(self, tenant_id: str, limit: float):
        """Initialize budget account for tenant."""
        from swarm.enterprise.core.budget.ledger import BudgetType
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

    # =========================================================================
    # Main Processing Pipeline
    # =========================================================================

    async def process(
        self,
        request: Any,
        authorization_context: Optional[Any] = None,
    ) -> Any:
        """Process request through all stages with full system integration."""
        from swarm.enterprise.core.orchestration.components import (
            RequestValidator, SafetyGate, BoardCoordinator, ExecutiveCoordinator,
            ExecutionCoordinator, CostController, ResultAssembler, AuditEmitter,
            SwarmStageResult,
        )
        from swarm.enterprise.core.auth import AuthorizationContext
        from swarm.enterprise.core.execution.context import ExecutionContext

        self._ensure_core_services()

        # 1. Validate request
        if self.validator:
            valid, error = self.validator.validate(request)
            if not valid:
                return self._error_result(request, error)

        # 2. Create execution context
        exec_context = ExecutionContext.create(
            tenant_id=request.tenant_id,
            principal_id=request.principal_id,
            authorization_context=authorization_context,
        )
        from swarm.enterprise.core.execution.context import set_current_context
        set_current_context(exec_context)

        # 3. Create authorization context if not provided
        if authorization_context is None:
            from swarm.enterprise.core.auth import Principal, AuthorizationContext
            principal = Principal.user(request.principal_id, request.tenant_id)
            authorization_context = AuthorizationContext.for_user(
                user_id=request.principal_id,
                tenant_id=request.tenant_id,
            )

        # 4. Compute cost estimate
        cost_estimate = {"estimated_total": "0", "currency": "USD"}
        if self.cost_service:
            cost_estimate = self.cost_controller.estimate_cost(request, request.tenant_id)

        # 5. Assemble context from Memory V2
        memory_context = {}
        if hasattr(self, 'memory_fabric') and self.memory_fabric and request.context.get("use_memory", True):
            memory_context = await self._assemble_memory_context(request, exec_context)

        merged_context = {**memory_context, **request.context}

        # 6. Run stages
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

        try:
            # Stage 1: Safety
            safety_gate = self._get_safety_gate()
            safety_result = await safety_gate.check(request, exec_context, authorization_context)
            stages = {"safety": safety_result}
            if not safety_result.success:
                return self._build_result(
                    exec_context, {"safety": safety_result}, "vetoed", "failed", "failure",
                    vetoed_by="safety_dept", veto_reason=safety_result.error,
                    cost_estimate=cost_estimate
                )

            # Stage 2: Board
            board_coordinator = self._get_board_coordinator()
            board_result = await board_coordinator.deliberate(request, exec_context, authorization_context)
            stages = {"board": board_result}
            if not board_result.success:
                return self._build_result(
                    exec_context, {"board": board_result}, "vetoed", "failed", "failure",
                    vetoed_by=board_result.output.get("vetoed_by", "board"),
                    veto_reason=board_result.error,
                    cost_estimate=cost_estimate
                )

            # Stage 3: C-Suite
            exec_coordinator = self._get_executive_coordinator()
            exec_result = await exec_coordinator.decide(request, None, exec_context, authorization_context)
            stages = {"csuite": exec_result}
            if not exec_result.success:
                policy_decision = "vetoed" if exec_result.output.get("verdict") == "vetoed" else "rejected"
                return self._build_result(
                    exec_context, {"csuite": exec_result}, policy_decision, "failed", "failure",
                    vetoed_by=exec_result.output.get("vetoed_by", "csuite"),
                    veto_reason=exec_result.error,
                    cost_estimate=cost_estimate
                )

            # Stage 4: Routing
            self._ensure_core_services()
            routing_decision = self.routing_engine.route(
                question=request.question,
                explicit_type=request.type if request.type != "general" else None,
                context={},
            )
            stages = {"routing": {"stage_name": "routing", "success": True, "output": routing_decision.to_dict()}}

            # Stage 5: Execution via Task Dispatcher
            dispatch_start = datetime.now(timezone.utc)
            
            capability = self._map_routing_to_capability(routing_decision)
            
            dispatch_result = await self._dispatch_task(
                capability=capability,
                request=request,
                context=merged_context,
                routing=routing_decision,
            )
            
            dispatch_time_ms = int((datetime.now(timezone.utc) - dispatch_start).total_seconds() * 1000)
            dispatched_to = dispatch_result.instance_id if dispatch_result else None
            
            stages["execution"] = {
                "stage_name": "execution",
                "success": dispatch_result.success if dispatch_result else False,
                "output": dispatch_result.result.output if dispatch_result and dispatch_result.result else None,
                "error": dispatch_result.error if dispatch_result else None,
            }
            
            if not dispatch_result or not dispatch_result.success:
                policy_decision = "error"
                execution_state = "failed"
                final_outcome = "failure"
                veto_reason = dispatch_result.error if dispatch_result else "Dispatch failed"
            else:
                execution_state = "succeeded"
                final_outcome = "success"
                executed_by = dispatch_result.result.agent_instance_id if dispatch_result and dispatch_result.result else "unknown"
                final_output = dispatch_result.result.output if dispatch_result and dispatch_result.result else None
                
                self._record_episode(request, exec_context, merged_context, final_output, True)

            policy_decision = "approved" if final_outcome == "success" else "approved"

        except Exception as e:
            logger.exception(f"SwarmMaster processing error: {e}")
            policy_decision = "error"
            execution_state = "failed"
            final_outcome = "failure"
            veto_reason = f"Orchestration error: {e}"
            
            self._record_episode(request, exec_context, {}, None, False, str(e))

        return self._build_result(
            exec_context, stages, policy_decision, execution_state, final_outcome,
            vetoed_by, veto_reason, cost_estimate, final_output, executed_by,
            dispatched_to, dispatch_time_ms
        )

    def _ensure_core_services(self):
        """Ensure core services are initialized."""
        if not hasattr(self, '_core_initialized'):
            self._core_initialized = True

    def _map_routing_to_capability(self, routing_decision) -> str:
        dept = routing_decision.department.value if hasattr(routing_decision.department, 'value') else str(routing_decision.department)
        capability_map = {
            "code": "CODE_GENERATION",
            "design": "DESIGN",
            "video": "CODE_GENERATION",
            "research": "RESEARCH",
            "data": "DATA_ANALYSIS",
            "language": "TRANSLATION",
            "knowledge": "KNOWLEDGE_RETRIEVAL",
            "safety": "SAFETY_CHECK",
        }
        return capability_map.get(dept, "TEXT_GENERATION")

    async def _dispatch_task(
        self,
        capability: str,
        request: Any,
        context: Dict[str, Any],
        routing: Any,
    ) -> Any:
        from swarm.enterprise.core.orchestration import create_task_dispatcher, DispatchConfig, DispatchStrategy
        
        if not hasattr(self, '_task_dispatcher'):
            from swarm.enterprise.core.orchestration import create_task_dispatcher, DispatchConfig, DispatchStrategy
            self._task_dispatcher = create_task_dispatcher(
                self.service_registry,
                DispatchConfig(
                    strategy=DispatchStrategy.LEAST_LOADED,
                    enable_circuit_breaker=True,
                    enable_fallback=True,
                ),
            )
        
        dispatch_result = await self._task_dispatcher.dispatch(
            capability=capability,
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
        
        return dispatch_result

    def _record_episode(
        self,
        request: Any,
        exec_context: Any,
        merged_context: Dict[str, Any],
        output: Any,
        success: bool,
        error: Optional[str] = None,
    ) -> None:
        pass  # Implement if memory_fabric available

    def _add_to_dlq(self, request: Any, error: str) -> None:
        pass

    def _map_routing_to_capability(self, routing_decision) -> str:
        dept = routing_decision.department.value if hasattr(routing_decision.department, 'value') else str(routing_decision.department)
        capability_map = {
            "code": "CODE_GENERATION",
            "design": "DESIGN",
            "video": "CODE_GENERATION",
            "research": "RESEARCH",
            "data": "DATA_ANALYSIS",
            "language": "TRANSLATION",
            "knowledge": "KNOWLEDGE_RETRIEVAL",
            "safety": "SAFETY_CHECK",
        }
        return capability_map.get(dept, "TEXT_GENERATION")

    def _build_result(
        self,
        exec_context: Any,
        stages: Dict[str, Any],
        policy_decision: str,
        execution_state: str,
        final_outcome: str,
        vetoed_by: Optional[str] = None,
        veto_reason: Optional[str] = None,
        cost_estimate: Optional[Dict] = None,
        output: Optional[Any] = None,
        executed_by: Optional[str] = None,
        dispatched_to: Optional[str] = None,
        dispatch_time_ms: int = 0,
    ) -> Any:
        from swarm.enterprise.core.orchestration.components import ResultAssembler
        
        assembler = None
        try:
            from swarm.enterprise.core.orchestration.components import ResultAssembler
            assembler = ResultAssembler(result_factory=self._create_result)
        except:
            from swarm.enterprise.core.orchestration.components import ResultAssembler
            assembler = ResultAssembler(result_factory=lambda **kwargs: None)
        
        return assembler.assemble(
            request_id=exec_context.identity.request_id,
            execution_id=exec_context.identity.execution_id,
            trace_id=exec_context.identity.trace_id,
            stages=stages,
            final_output=None,
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

    def _error_result(self, request, error: str):
        from swarm.enterprise.core.execution.context import ExecutionContext
        exec_context = ExecutionContext.create(
            tenant_id=request.tenant_id,
            principal_id=request.principal_id,
        )
        from swarm.enterprise.core.orchestration.components import ResultAssembler
        assembler = ResultAssembler(result_factory=lambda **kwargs: None)
        return assembler.assemble(
            request_id=exec_context.identity.request_id,
            execution_id=exec_context.identity.execution_id,
            trace_id=exec_context.identity.trace_id,
            stages={},
            final_output=None,
            policy_decision="error",
            execution_state="failed",
            final_outcome="failure",
            veto_reason=error,
            metadata={"tenant_id": request.tenant_id, "principal_id": request.principal_id},
        )

    # =========================================================================
    # Agent Management API
    # =========================================================================

    def register_agent(
        self,
        agent_type: str,
        name: str,
        description: str,
        capabilities: List[str],
        department: str,
        executor: Any = None,
        max_concurrent: int = 1,
        tenant_id: str = "default",
    ) -> str:
        from swarm.enterprise.core.orchestration import AgentCapability
        
        caps = [AgentCapability(c) for c in capabilities]
        
        self.agent_registry.register_agent_type(
            agent_type=agent_type,
            name=name,
            description=description,
            capabilities=[AgentCapability(c) for c in capabilities],
            department=department,
        )
        
        instance = self.agent_registry.register_instance(
            agent_type=agent_type,
            tenant_id=tenant_id,
            max_concurrent_tasks=max_concurrent,
            executor=executor,
        )
        
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

    def list_agents(self, tenant_id: Optional[str] = None) -> List[Dict[str, Any]]:
        instances = self.agent_registry.list_instances(tenant_id=tenant_id)
        
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
            for i in instances
        ]

    def create_workflow(self, workflow_id: str, workflow_type: str, steps: List[Dict]) -> Any:
        from swarm.enterprise.core.job import create_compensable_workflow
        workflow = create_compensable_workflow(workflow_id, workflow_type, steps)
        self.compensation_engine.register_workflow(workflow)
        return workflow

    def execute_workflow(self, workflow_id: str) -> Any:
        return self.compensation_engine.execute(workflow_id)

    def schedule_job(
        self,
        job_type: str,
        payload: Dict[str, Any],
        run_at: Optional[datetime] = None,
        interval_seconds: Optional[int] = None,
        cron_expression: Optional[str] = None,
        max_runs: Optional[int] = None,
        tenant_id: str = "default",
    ) -> str:
        if not self.job_scheduler:
            raise RuntimeError("Job scheduler not enabled")
        
        if run_at:
            return schedule_once(self.job_scheduler, job_type, payload, run_at, tenant_id=tenant_id)
        elif interval_seconds:
            return schedule_interval(self.job_scheduler, job_type, payload, interval_seconds, max_runs=max_runs, tenant_id=tenant_id)
        elif cron_expression:
            return schedule_cron(self.job_scheduler, job_type, payload, cron_expression, max_runs=max_runs, tenant_id=tenant_id)
        else:
            raise ValueError("Must specify run_at, interval_seconds, or cron_expression")

    def write_memory(
        self,
        content: Dict[str, Any],
        layer: str = "WORKING",
        tenant_id: str = "default",
        actor_id: str = "swarm_master",
        trust_level: str = "AGENT_GENERATED",
        tags: Optional[Set[str]] = None,
    ) -> str:
        from swarm.memory.v2 import MemoryLayer, TrustLevel, MemoryWrite, MemoryEntry, MemoryMetadata
        
        entry = MemoryEntry(
            metadata=MemoryMetadata(
                layer=MemoryLayer(layer),
                tenant_id=tenant_id,
                actor_id=actor_id,
                trust_level=TrustLevel(trust_level),
                tags=tags or set(),
            ),
            content=content,
        )
        
        write = MemoryWrite(entry=entry)
        import asyncio
        asyncio.run(self.memory_fabric._repository.write(write))
        
        return entry.metadata.memory_id

    def search_memory(
        self,
        query: str,
        tenant_id: str = "default",
        top_k: int = 10,
        mode: str = "HYBRID",
    ) -> List[Dict[str, Any]]:
        if not hasattr(self.memory_fabric, 'get_search_manager'):
            return []
        
        search_manager = self.memory_fabric.get_search_manager()
        if not search_manager:
            return []
        
        from swarm.memory.v2 import SearchRequest, SearchMode
        
        results = asyncio.run(search_manager.search(SearchRequest(
            query=query,
            tenant_id=tenant_id,
            top_k=top_k,
            mode=SearchMode(mode),
        )))
        
        return [
            {
                "content": r.entry.content,
                "score": r.score,
                "layer": r.entry.metadata.layer.value if hasattr(r.entry.metadata, 'layer') else "unknown",
            }
            for r in results
        ]

    def get_status(self) -> Dict[str, Any]:
        status = {
            "version": "3.0",
            "board_agents": 5,
            "csuite_agents": 7,
            "departments": len(self.depts),
            "control_plane": "active",
            "execution_plane": "active",
            "routing_engine": "active",
            "policy_engine": "active",
            "audit_emitter": "active",
            "memory_v2": "active" if self.memory_fabric else "disabled",
            "job_system": "active",
            "job_scheduler": "active" if self.job_scheduler else "disabled",
            "dead_letter_queue": "active" if self.dlq else "disabled",
            "agent_registry": "active",
            "task_dispatcher": "active",
            "worker_pool": "active",
            "metrics": "active" if self.metrics else "disabled",
        }
        
        agent_stats = self.agent_registry.get_stats()
        status["agents"] = agent_stats
        
        if hasattr(self.worker_pool, 'get_total_status'):
            status["worker_pool"] = self.worker_pool.get_total_status()
        
        return status

    def get_health(self) -> Dict[str, Any]:
        health = {
            "overall": "healthy",
            "components": {},
        }
        
        try:
            healthy = asyncio.run(self.memory_fabric.health_check()) if self.memory_fabric else False
            health["components"]["memory_v2"] = "healthy" if healthy else "unhealthy"
        except Exception:
            health["components"]["memory_v2"] = "unhealthy"
        
        try:
            healthy = asyncio.run(self.job_repository.health_check())
            health["components"]["job_repository"] = "healthy" if healthy else "unhealthy"
        except Exception:
            health["components"]["job_repository"] = "unhealthy"
        
        agent_stats = self.agent_registry.get_stats()
        unhealthy_agents = agent_stats.get("by_status", {}).get("unhealthy", 0)
        health["components"]["agent_registry"] = "degraded" if unhealthy_agents > 0 else "healthy"
        health["components"]["agent_registry_details"] = agent_stats
        
        if hasattr(self.worker_pool, 'get_total_status'):
            wp_status = self.worker_pool.get_total_status()
            health["components"]["worker_pool"] = "healthy" if wp_status.get("running", False) else "unhealthy"
        
        unhealthy_count = sum(1 for v in health["components"].values() if v == "unhealthy")
        if unhealthy_count > 0:
            health["overall"] = "degraded" if unhealthy_count < 3 else "unhealthy"
        
        return health


# Backward compatibility singleton
_master_instance: Optional[Any] = None


def get_master() -> Any:
    """Get SwarmMaster singleton."""
    global _master_instance
    if _master_instance is None:
        _master_instance = SwarmMaster()
    return _master_instance


if __name__ == "__main__":
    import asyncio
    
    async def main():
        master = SwarmMaster()
        
        print("=== SwarmMaster v3 Status ===")
        status = master.get_status()
        for k, v in status.items():
            print(f"  {k}: {v}")
        
        print("\n=== Health ===")
        health = master.get_health()
        print(f"  Overall: {health['overall']}")
        for comp, status in health["components"].items():
            print(f"  {comp}: {status}")
        
        print("\n=== Testing Request ===")
        from swarm.enterprise.core.auth import AuthorizationContext
        
        auth_ctx = AuthorizationContext.for_user(
            user_id="test-user",
            tenant_id="default",
        )
        
        request = SwarmRequest(
            question="Create a simple Python function for binary search",
            type="code",
            tenant_id="default",
            principal_id="test-user",
        )
        
        result = await master.process(request, auth_ctx)
        print(f"\nResult: {result.policy_decision}")
        print(f"Execution: {result.execution_state}")
        print(f"Dispatched to: {result.dispatched_to}")
        print(f"Dispatch time: {result.dispatch_time_ms}ms")
        print(f"Output: {result.output}")
        
        await master.memory_fabric.shutdown() if master.memory_fabric else None
        master.agent_registry.shutdown()
        if master.job_scheduler:
            master.job_scheduler.stop()
    
    import asyncio
    asyncio.run(main())

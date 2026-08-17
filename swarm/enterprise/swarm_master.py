"""
SwarmMaster v2 — Thin orchestrator using decomposed components.

F-008: SwarmMaster God Object fix.
F-009: Weak Dependency Injection fix.
Uses: RequestValidator, SafetyGate, BoardCoordinator, ExecutiveCoordinator,
      ExecutionCoordinator, CostController, ResultAssembler, AuditEmitter,
      RoutingEngine, PolicyEngine, ControlPlane
"""
import logging
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from swarm.enterprise.core.auth import AuthorizationContext, AuthorizationPolicy
from swarm.enterprise.core.budget.cost_estimation import CostEstimationService, get_cost_estimation_service
from swarm.enterprise.core.budget.ledger import BudgetLedger, get_budget_ledger
from swarm.enterprise.core.routing.engine import RoutingEngine, get_routing_engine
from swarm.enterprise.core.policy.engine import PolicyEngine, get_policy_engine
from swarm.enterprise.core.plane.control_plane import ControlPlane, get_control_plane, AdmissionRequest
from swarm.enterprise.core.plane.execution_plane import ExecutionPlane, get_execution_plane, SwarmProcessExecutor
from swarm.enterprise.core.orchestration.components import (
    RequestValidator, SafetyGate, BoardCoordinator, ExecutiveCoordinator,
    ExecutionCoordinator, CostController, ResultAssembler, AuditEmitter, SwarmStageResult,
)
from swarm.enterprise.core.execution.context import ExecutionContext, ExecutionIdentity
from swarm.enterprise.core.auth import AuthorizationContext

# Tier 1: Board
from swarm.enterprise.board import create_board, BoardDecision

# Tier 2: C-Suite
from swarm.enterprise.csuite import create_c_suite

# Tier 3+4: Departments
from swarm.enterprise.code import create_code_dept
from swarm.enterprise.design import create_design_dept
from swarm.enterprise.video import create_video_dept
from swarm.enterprise.research import create_research_dept
from swarm.enterprise.data import create_data_dept
from swarm.enterprise.language import create_language_dept
from swarm.enterprise.knowledge import create_knowledge_dept
from swarm.enterprise.safety import create_safety_dept

logger = logging.getLogger(__name__)


class DeptType(str, Enum):
    """Department types for routing."""
    CODE = "code"
    DESIGN = "design"
    VIDEO = "video"
    RESEARCH = "research"
    DATA = "data"
    LANGUAGE = "language"
    KNOWLEDGE = "knowledge"
    SAFETY = "safety"
    GENERAL = "general"


# Keywords for routing requests to appropriate departments
DEPT_ROUTING_KEYWORDS = {
    DeptType.CODE: [
        "code", "function", "class", "implement", "build app",
        "api endpoint", "database query", "python script",
        "javascript", "deploy", "refactor",
        "compile", "syntax", "debug", "fix bug",
    ],
    DeptType.DESIGN: [
        "logo", "image", "design", "ui mockup", "ux", "mockup",
        "icon", "brand", "color scheme", "typography", "3d model",
        "wireframe", "visual", "artwork", "illustration",
    ],
    DeptType.VIDEO: [
        "video", "animation", "animate", "motion graphic", "film",
        "clip", "storyboard", "movie", "mp4", "commercial",
    ],
    DeptType.RESEARCH: [
        "research", "investigate", "study", "literature review",
        "fact check", "verify", "find papers", "academic", "study of",
    ],
    DeptType.DATA: [
        "data analysis", "etl pipeline", "analytics", "metrics",
        "kpi", "sql query", "schema design", "dashboard", "data warehouse",
        "olap", "data lake", "pipeline", "data pipeline",
        "data processing", "data transformation",
    ],
    DeptType.LANGUAGE: [
        "translate", "translation", "localize", "localization",
        "i18n", "arabic text", "french text", "spanish text",
    ],
    DeptType.KNOWLEDGE: [
        "search docs", "knowledge base", "rag retrieval",
        "find document", "search knowledge", "document retrieval",
    ],
}


@dataclass
class SwarmRequest:
    """Request to SwarmMaster (hardened - no client-controlled security/cost)."""
    question: str
    type: str = "general"
    context: Dict[str, Any] = field(default_factory=dict)
    require_human_review: bool = False
    idempotency_key: Optional[str] = None
    tenant_id: str = "default"
    principal_id: str = "user"


@dataclass
class SwarmResult:
    """Result from SwarmMaster."""
    request_id: str
    execution_id: str
    trace_id: str
    policy_decision: str  # "approved" | "rejected" | "vetoed" | "escalated"
    execution_state: str  # "pending" | "queued" | "running" | "succeeded" | "failed"
    final_outcome: Optional[str] = None  # "success" | "failure" | null
    stages: Dict[str, Any] = field(default_factory=dict)
    output: Optional[Any] = None
    vetoed_by: Optional[str] = None
    veto_reason: Optional[str] = None
    executed_by: Optional[str] = None
    cost_estimate: Optional[Dict[str, Any]] = None
    actual_cost: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Backward compatibility
    @property
    def verdict(self) -> str:
        return self.policy_decision

    @property
    def final_decision(self) -> str:
        return self.policy_decision


class SwarmMaster:
    """Thin orchestrator for 50-Agent Swarm (Enterprise Hardened v2)."""

    def __init__(
        self,
        cfo_budget_limit: float = float("inf"),
        tenant_id: str = "default",
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
        # Injected dependencies (or defaults)
        self.validator = validator or RequestValidator()
        self.routing_engine = routing_engine or get_routing_engine()
        self.policy_engine = policy_engine or get_policy_engine()
        self.auth_policy = auth_policy or AuthorizationPolicy()
        self.cost_service = cost_service or get_cost_estimation_service()
        self.budget_ledger = budget_ledger or get_budget_ledger()
        self.control_plane = control_plane or get_control_plane()
        self.execution_plane = execution_plane or get_execution_plane()
        self.audit_emitter = audit_emitter or AuditEmitter()

        # Initialize core components if not injected
        self._init_components(
            board=board,
            csuite=csuite,
            depts=depts,
            cfo_budget_limit=cfo_budget_limit,
            tenant_id=tenant_id,
        )

        # Orchestration components (injected or created)
        self.safety_gate = safety_gate or SafetyGate(self.safety_dept, self.policy_engine)
        self.board_coordinator = board_coordinator or BoardCoordinator(self.board)
        self.executive_coordinator = executive_coordinator or ExecutiveCoordinator(
            self.csuite, self.cost_service, self.budget_ledger
        )
        self.execution_coordinator = execution_coordinator or ExecutionCoordinator(self.depts)
        self.cost_controller = cost_controller or CostController(self.cost_service, self.budget_ledger)
        self.result_assembler = result_assembler or ResultAssembler(result_factory=self._create_result)
        self.validator = validator or RequestValidator()

        self._lock = threading.Lock()

    def _init_components(self, board, csuite, depts, cfo_budget_limit, tenant_id):
        """Initialize core swarm components."""
        # Safety Dept (Tier 1 - VETO first)
        self.safety_dept = create_safety_dept()

        # Board (Tier 1 - strategic VETO)
        self.board = board or create_board()

        # C-Suite (Tier 2 - executive decision)
        self.csuite = csuite or create_c_suite(cfo_budget_limit=cfo_budget_limit)

        # Departments (Tier 3+4 - execution)
        self.depts = depts or {
            "code": create_code_dept(),
            "design": create_design_dept(),
            "video": create_video_dept(),
            "research": create_research_dept(),
            "data": create_data_dept(),
            "language": create_language_dept(),
            "knowledge": create_knowledge_dept(),
            "safety": self.safety_dept,
        }

        # Initialize budget account
        self._init_budget_account(tenant_id, cfo_budget_limit)

        # Register executor with execution plane
        self.execution_plane.register_executor(
            "swarm_process",
            SwarmProcessExecutor(self),
        )

    def _init_budget_account(self, tenant_id: str, limit: float):
        """Initialize budget account for tenant."""
        from swarm.enterprise.core.budget.ledger import BudgetType
        from decimal import Decimal
        account_id = f"budget-{tenant_id}"
        try:
            self.budget_ledger.create_account(
                account_id=account_id,
                tenant_id=tenant_id,
                budget_type=BudgetType.DAILY,
                limit=Decimal(str(limit)) if limit != float("inf") else Decimal("1000000"),
            )
        except ValueError:
            pass  # Account already exists

    def _create_result(self, **kwargs) -> "SwarmResult":
        """Factory method for creating SwarmResult objects."""
        return SwarmResult(**kwargs)

    def process(
        self,
        request: SwarmRequest,
        authorization_context: Optional[AuthorizationContext] = None,
    ) -> SwarmResult:
        """Process request through all stages (thin orchestration)."""

        # 1. Validate request
        valid, error = self.validator.validate(request)
        if not valid:
            return self._error_result(request, error)

        # 2. Create execution context
        exec_context = ExecutionContext.create(
            tenant_id=request.tenant_id,
            principal_id=request.principal_id,
            authorization_context=authorization_context,
        )
        from swarm.enterprise.core.execution.context import set_current_context, clear_current_context
        set_current_context(exec_context)

        # 3. Create authorization context if not provided
        if authorization_context is None:
            from swarm.enterprise.core.auth import Principal
            principal = Principal.user(request.principal_id, request.tenant_id)
            authorization_context = AuthorizationContext.for_user(
                user_id=request.principal_id,
                tenant_id=request.tenant_id,
            )

        # 4. Compute cost estimate
        cost_estimate = self.cost_controller.estimate_cost(request, request.tenant_id)

        # 5. Run stages
        stages: Dict[str, SwarmStageResult] = {}
        final_output = None
        policy_decision = "approved"
        execution_state = "pending"
        final_outcome = None
        executed_by = None
        vetoed_by = None
        veto_reason = None

        try:
            # Stage 1: Safety
            safety_result = self.safety_gate.check(request, exec_context, authorization_context)
            stages["safety"] = safety_result
            if not safety_result.success:
                policy_decision = "vetoed"
                execution_state = "failed"
                final_outcome = "failure"
                vetoed_by = "safety_dept"
                veto_reason = safety_result.error
                return self._build_result(exec_context, stages, policy_decision, execution_state, final_outcome, vetoed_by, veto_reason, cost_estimate)

            # Stage 2: Board
            board_result = self.board_coordinator.deliberate(request, exec_context, authorization_context)
            stages["board"] = board_result
            if not board_result.success:
                policy_decision = "vetoed"
                execution_state = "failed"
                final_outcome = "failure"
                vetoed_by = board_result.output.get("vetoed_by", "board")
                veto_reason = board_result.error
                return self._build_result(exec_context, stages, policy_decision, execution_state, final_outcome, vetoed_by, veto_reason, cost_estimate)

            # Stage 3: C-Suite
            exec_result = self.executive_coordinator.decide(request, None, exec_context, authorization_context)
            stages["csuite"] = exec_result
            if not exec_result.success:
                policy_decision = "vetoed" if exec_result.output.get("verdict") == "vetoed" else "rejected"
                execution_state = "failed"
                final_outcome = "failure"
                vetoed_by = exec_result.output.get("vetoed_by", "csuite")
                veto_reason = exec_result.error
                return self._build_result(exec_context, stages, policy_decision, execution_state, final_outcome, vetoed_by, veto_reason, cost_estimate)

            # Stage 4: Routing
            routing_decision = self.routing_engine.route(
                question=request.question,
                explicit_type=request.type if request.type != "general" else None,
                context=request.context,
            )
            stages["routing"] = SwarmStageResult(
                stage_name="routing",
                success=True,
                output=routing_decision.to_dict(),
            )

            # Stage 5: Execution
            exec_stage = self.execution_coordinator.execute(request, routing_decision, exec_context, authorization_context)
            stages["execution"] = exec_stage
            if not exec_stage.success:
                policy_decision = "error"
                execution_state = "failed"
                final_outcome = "failure"
                veto_reason = exec_stage.error
            else:
                execution_state = "succeeded"
                final_outcome = "success"
                executed_by = exec_stage.output.get("department")
                final_output = exec_stage.output

            policy_decision = "approved" if final_outcome == "success" else policy_decision

        except Exception as e:
            logger.exception("SwarmMaster processing error")
            policy_decision = "error"
            execution_state = "failed"
            final_outcome = "failure"
            veto_reason = f"Orchestration error: {e}"

        return self._build_result(
            exec_context, stages, policy_decision, execution_state, final_outcome,
            vetoed_by, veto_reason, cost_estimate, final_output, executed_by
        )

    def _build_result(
        self,
        exec_context: ExecutionContext,
        stages: Dict[str, SwarmStageResult],
        policy_decision: str,
        execution_state: str,
        final_outcome: Optional[str],
        vetoed_by: Optional[str] = None,
        veto_reason: Optional[str] = None,
        cost_estimate: Optional[Dict] = None,
        output: Optional[Any] = None,
        executed_by: Optional[str] = None,
    ) -> SwarmResult:
        """Build final result using ResultAssembler."""
        # Emit audit events
        for stage_name, stage_result in stages.items():
            if not stage_result.success:
                self.audit_emitter.emit(
                    event_type="stage_failed",
                    actor="swarm_master",
                    request_id=exec_context.identity.request_id,
                    execution_id=exec_context.identity.execution_id,
                    trace_id=exec_context.identity.trace_id,
                    decision=stage_result.error or "failed",
                    details={"stage": stage_name, "error": stage_result.error},
                )

        # Emit final decision
        self.audit_emitter.emit(
            event_type="final_decision",
            actor="swarm_master",
            request_id=exec_context.identity.request_id,
            execution_id=exec_context.identity.execution_id,
            trace_id=exec_context.identity.trace_id,
            decision=policy_decision,
            details={
                "execution_state": execution_state,
                "final_outcome": final_outcome,
                "executed_by": executed_by,
                "vetoed_by": vetoed_by,
            },
        )

        return self.result_assembler.assemble(
            request_id=exec_context.identity.request_id,
            execution_id=exec_context.identity.execution_id,
            trace_id=exec_context.identity.trace_id,
            stages=stages,
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
            },
        )

    def _error_result(self, request: SwarmRequest, error: str) -> SwarmResult:
        """Build error result."""
        exec_context = ExecutionContext.create(
            tenant_id=request.tenant_id,
            principal_id=request.principal_id,
        )
        return self.result_assembler.assemble(
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

    def get_status(self) -> Dict[str, Any]:
        """Swarm status."""
        return {
            "board_agents": 5,
            "csuite_agents": 7,
            "department_agents": sum(
                len(getattr(d, "_agents", {})) for d in self.depts.values()
                if hasattr(d, "_agents")
            ),
            "control_plane": "active",
            "execution_plane": "active",
            "routing_engine": "active",
            "policy_engine": "active",
            "audit_emitter": "active",
        }

    def list_agents(self) -> Dict[str, List[str]]:
        """List all agents by department."""
        return {
            "board": ["chairman", "strategy_advisor", "ethics_advisor", "risk_advisor", "user_advisor"],
            "csuite": ["ceo", "cto", "cfo", "coo", "cmo", "chro", "clo"],
            "code": list(self.depts["code"]._agents.keys()) if hasattr(self.depts["code"], "_agents") else [],
            "design": list(self.depts["design"]._agents.keys()) if hasattr(self.depts["design"], "_agents") else [],
            "video": list(self.depts["video"]._agents.keys()) if hasattr(self.depts["video"], "_agents") else [],
            "research": list(self.depts["research"]._agents.keys()) if hasattr(self.depts["research"], "_agents") else [],
            "data": list(self.depts["data"]._agents.keys()) if hasattr(self.depts["data"], "_agents") else [],
            "language": list(self.depts["language"]._agents.keys()) if hasattr(self.depts["language"], "_agents") else [],
            "knowledge": ["director", "curator", "retriever", "reranker", "parser"],
            "safety": ["director", "content", "topic", "jailbreak"],
        }


# Backward compatibility singleton
_master_instance: Optional[SwarmMaster] = None


def get_master() -> SwarmMaster:
    """Get SwarmMaster singleton."""
    global _master_instance
    if _master_instance is None:
        _master_instance = SwarmMaster()
    return _master_instance


if __name__ == "__main__":
    master = SwarmMaster()
    print("=== Swarm Status ===")
    status = master.get_status()
    for k, v in status.items():
        print(f"  {k}: {v}")
    print()
    print("=== Agents ===")
    agents = master.list_agents()
    for dept, roles in agents.items():
        print(f"  {dept}: {len(roles)} agents")
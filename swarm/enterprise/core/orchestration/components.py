"""
SwarmMaster Decomposition — F-008.

Breaks SwarmMaster into thin orchestration components:
- RequestValidator
- PolicyEngine (already created)
- SafetyGate
- BoardCoordinator
- ExecutiveCoordinator
- RoutingEngine (already created)
- ExecutionCoordinator
- CostController
- ResultAssembler
- AuditEmitter
"""

import importlib
import logging
import threading
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import uuid

logger = logging.getLogger(__name__)

# AuthorizationContext is referenced in method annotations below. Import lazily
# to avoid circular imports; fall back to Any if the auth module is unavailable.
try:
    from swarm.enterprise.core.auth import AuthorizationContext  # noqa: F401
except Exception:  # pragma: no cover - defensive for import cycles
    AuthorizationContext = Any

# Same pattern for PolicyEngine (used in factory annotation below).
PolicyEngine = Any

# Policy types referenced by SafetyGate.check
try:
    from swarm.enterprise.core.policy.engine import (  # noqa: F401
        PolicyDecision,
        EvaluationContext as PolicyContext,
    )
except Exception:  # pragma: no cover - defensive for import cycles
    PolicyDecision = None
    PolicyContext = None


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
    def get_authorization_context(self):
        return self._get_attr("swarm.enterprise.core.auth", "AuthorizationContext")
    
    def get_policy_engine(self):
        return self._get_attr("swarm.enterprise.core.policy.engine", "PolicyEngine")
    
    def get_routing_engine(self):
        return self._get_attr("swarm.enterprise.core.routing.engine", "RoutingEngine")
    
    def get_cost_estimation(self):
        return self._get_attr("swarm.enterprise.core.budget.cost_estimation", "CostEstimationService")
    
    def get_budget_ledger(self):
        return self._get_attr("swarm.enterprise.core.budget.ledger", "BudgetLedger")
    
    def get_control_plane(self):
        return self._get_attr("swarm.enterprise.core.plane.control_plane", "ControlPlane")
    
    def get_execution_context(self):
        return self._get_attr("swarm.enterprise.core.execution.context", "ExecutionContext")
    
    def get_current_context(self):
        return self._get_attr("swarm.enterprise.core.execution.context", "get_current_context")
    
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


_lazy = LazyImports()


# =============================================================================
# Components
# =============================================================================

@dataclass
class SwarmStageResult:
    """Result of a single stage."""
    stage_name: str
    success: bool
    output: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class RequestValidator:
    """Validates incoming requests before processing."""

    def validate(self, request: Any) -> tuple[bool, Optional[str]]:
        """Validate request. Returns (valid, error_message)."""
        if not request.question or not request.question.strip():
            return False, "Question is required"
        if len(request.question) > 100000:
            return False, "Question too long (max 100000 chars)"
        return True, None


class SafetyGate:
    """Safety check gate - runs safety department and policy evaluation."""

    def __init__(
        self,
        safety_dept: Any,
        policy_engine: Any = None,
    ):
        self.safety_dept = safety_dept
        self.policy_engine = policy_engine or _lazy.get_policy_engine()()

    def check(
        self,
        request: Any,
        exec_context: Any,
        auth_context: Any,
    ) -> SwarmStageResult:
        """Run safety check with policy evaluation."""
        # Policy evaluation (uses real EvaluationContext schema)
        policy_ctx = PolicyContext(
            subject={
                "principal_id": getattr(exec_context, 'principal_id', 'user'),
                "tenant_id": getattr(exec_context, 'tenant_id', 'default'),
            },
            resource={"id": request.question[:100]},
            action={"name": "safety_check"},
            environment={
                "require_human_review": getattr(request, 'require_human_review', False),
            },
        )
        allowed = True
        veto_reason = None
        try:
            result = self.policy_engine.evaluate(policy_ctx)
            if result is not None and getattr(result, 'decision', None) in (
                PolicyDecision.DENY, getattr(PolicyDecision, 'ESCALATE', object()),
            ):
                allowed = False
                veto_reason = f"policy:{getattr(result, 'policy_id', 'unknown')}"
        except Exception as e:
            logger.warning("Policy evaluation failed (fail-open for safety dept): %s", e)

        if not allowed:
            return SwarmStageResult(
                stage_name="safety",
                success=False,
                error=veto_reason or "policy denied",
                metadata={"stage": "safety", "policy_denied": True},
            )

        # Run safety department
        try:
            text = request.question + " " + str(getattr(request, 'context', {}))
            bypass = auth_context.capabilities.has("override_safety") if auth_context else False
            report = self.safety_dept.full_check(text, use_llm=not bypass)

            if report.verdict.value in ("unsafe", "critical"):
                return SwarmStageResult(
                    stage_name="safety",
                    success=False,
                    error=report.explanation,
                    metadata={
                        "verdict": report.verdict.value,
                        "flags": report.flags,
                        "analyst_votes": {k: v.value for k, v in report.analyst_votes.items()},
                    },
                )

            return SwarmStageResult(
                stage_name="safety",
                success=True,
                output={
                    "verdict": report.verdict.value,
                    "flags": report.flags,
                    "explanation": report.explanation,
                    "analyst_votes": {k: v.value for k, v in report.analyst_votes.items()},
                },
            )
        except Exception as e:
            return SwarmStageResult(
                stage_name="safety",
                success=False,
                error=f"Safety check failed: {e}",
            )


class BoardCoordinator:
    """Coordinates board deliberation."""

    def __init__(self, board: Any):
        self.board = board

    async def deliberate(
        self,
        request: Any,
        exec_context: Any,
        auth_context: Any,
    ) -> SwarmStageResult:
        """Run board deliberation."""
        try:
            auth_context = _lazy.get_authorization_context()
            bypass_safety = bool(getattr(auth_context, 'capabilities', None)) and \
                auth_context.capabilities.has("override_safety")
            _maybe_coro = self.board.deliberate(
                request.question,
                context=str(getattr(request, 'context', {})),
                bypass_safety=bypass_safety,
                authorization_context=auth_context,
            )
            import inspect as _inspect
            board_result = (await _maybe_coro) if _inspect.isawaitable(_maybe_coro) else _maybe_coro

            stage_result = SwarmStageResult(
                stage_name="board",
                success=not board_result.vetoed_by,
                output={
                    "verdict": board_result.final_decision,
                    "vetoed_by": board_result.vetoed_by,
                    "votes": board_result.votes,
                    "reasoning": getattr(board_result, 'reasoning', {}),
                },
            )

            if board_result.vetoed_by:
                stage_result.success = False
                stage_result.error = board_result.veto_reason

            return stage_result

        except Exception as e:
            return SwarmStageResult(
                stage_name="board",
                success=False,
                error=f"Board deliberation failed: {e}",
            )


class ExecutiveCoordinator:
    """Coordinates C-Suite executive decision."""

    def __init__(
        self,
        csuite: Any,
        cost_service: Any,
        budget_ledger: Any,
    ):
        self.csuite = csuite
        self.cost_service = cost_service
        self.budget_ledger = budget_ledger
        self._lazy = LazyImports()

    async def decide(
        self,
        request: Any,
        board_result: Any,
        exec_context: Any,
        auth_context: AuthorizationContext,
    ) -> SwarmStageResult:
        """Run C-Suite executive meeting."""
        try:
            # Compute cost estimate
            CostEstimationRequest = self._lazy._get_attr(
                "swarm.enterprise.core.budget.cost_estimation", "CostEstimationRequest")
            cost_est = self.cost_service.estimate(CostEstimationRequest(
                provider="nvidia_nim",
                model="nvidia/nemotron-3-super-120b-a12b",
                estimated_input_tokens=1000,
                estimated_output_tokens=1000,
                estimated_tool_calls=5,
                tenant_id=getattr(request, 'tenant_id', 'default'),
            ))

            # Atomic budget reservation (skipped for zero-cost / free-tier models)
            tenant_id = getattr(request, 'tenant_id', 'default')
            account_id = f"budget-{tenant_id}"
            if cost_est.total > 0:
                try:
                    self.budget_ledger.reserve(
                        account_id=account_id,
                        amount=cost_est.total,
                        metadata={"request_id": exec_context.identity.request_id},
                    )
                except ValueError as e:
                    return SwarmStageResult(
                        stage_name="csuite",
                        success=False,
                        error=f"Budget reservation failed: {e}",
                    )

            proposal = {
                "title": request.question[:100],
                "description": request.question,
                "type": getattr(request, 'type', 'general'),
                "estimated_cost": float(cost_est.total),
                "bypass_safety": auth_context.capabilities.has("override_safety"),
            }

            csuite_result = self.csuite.executive_meeting(proposal)

            stage_result = SwarmStageResult(
                stage_name="csuite",
                success=csuite_result.get("verdict") not in ("vetoed", "rejected"),
                output={
                    "verdict": csuite_result.get("verdict"),
                    "vetoed_by": csuite_result.get("vetoed_by"),
                    "votes": csuite_result.get("votes", {}),
                    "budget_status": csuite_result.get("budget_status"),
                    "cost_estimate": {
                        "estimated_total": str(cost_est.total),
                        "currency": cost_est.currency,
                    },
                },
            )

            if csuite_result.get("verdict") == "vetoed":
                stage_result.success = False
                stage_result.error = csuite_result.get("reason")
            elif csuite_result.get("verdict") == "rejected":
                stage_result.success = False
                stage_result.error = csuite_result.get("reason")

            return stage_result

        except Exception as e:
            return SwarmStageResult(
                stage_name="csuite",
                success=False,
                error=f"C-Suite decision failed: {e}",
            )


class ExecutionCoordinator:
    """Coordinates department execution."""

    def __init__(self, depts: Dict[str, Any]):
        self.depts = depts

    def execute(
        self,
        request: Any,
        routing_decision: Any,
        exec_context: Any,
        auth_context: AuthorizationContext,
    ) -> SwarmStageResult:
        """Execute in the routed department."""
        try:
            dept_name = routing_decision.primary_department.value
            dept = self.depts.get(dept_name)

            if not dept:
                return SwarmStageResult(
                    stage_name="execution",
                    success=False,
                    error=f"No department: {dept_name}",
                )

            # This would be replaced with actual department execution
            return SwarmStageResult(
                stage_name="execution",
                success=True,
                output={"department": dept_name, "status": "completed"},
                metadata={"department": dept_name},
            )

        except Exception as e:
            return SwarmStageResult(
                stage_name="execution",
                success=False,
                error=f"Execution failed: {e}",
            )


class CostController:
    """Controls cost estimation and budget management."""

    def __init__(self, cost_service: Any, budget_ledger: Any):
        self.cost_service = cost_service
        self.budget_ledger = budget_ledger

    def estimate_cost(self, request: Any, tenant_id: str) -> Dict[str, Any]:
        """Estimate cost for a request."""
        cost_request = self._lazy.get_attr("swarm.enterprise.core.budget.cost_estimation", "CostEstimationRequest")
        estimate = self.cost_service.estimate(CostEstimationRequest(
            provider="nvidia_nim",
            model="nvidia/nemotron-3-super-120b-a12b",
            estimated_input_tokens=1000,
            estimated_output_tokens=1000,
            estimated_tool_calls=5,
            tenant_id=tenant_id,
        ))
        return {
            "estimated_total": str(estimate.total),
            "currency": estimate.currency,
            "breakdown": estimate.breakdown,
        }

    def reserve_budget(self, tenant_id: str, amount: float, request_id: str) -> bool:
        """Reserve budget atomically."""
        from decimal import Decimal
        account_id = f"budget-{tenant_id}"
        try:
            self.budget_ledger.reserve(
                account_id=account_id,
                amount=Decimal(str(amount)),
                metadata={"request_id": request_id},
            )
            return True
        except ValueError:
            return False


class ResultAssembler:
    """Assembles final result from stage outputs."""

    def __init__(self, result_factory=None):
        self._result_factory = result_factory

    def assemble(
        self,
        request_id: str,
        execution_id: str,
        trace_id: str,
        stages: Dict[str, Any],
        final_output: Any,
        policy_decision: str,
        execution_state: str,
        final_outcome: str,
        executed_by: Optional[str] = None,
        vetoed_by: Optional[str] = None,
        veto_reason: Optional[str] = None,
        cost_estimate: Optional[Dict] = None,
        actual_cost: Optional[Dict] = None,
        metadata: Optional[Dict] = None,
    ):
        """Assemble final result."""
        if self._result_factory:
            return self._result_factory(
                request_id=request_id,
                execution_id=execution_id,
                trace_id=trace_id,
                policy_decision=policy_decision,
                execution_state=execution_state,
                final_outcome=final_outcome,
                stages={k: (
                    {
                        "stage_name": v.stage_name,
                        "success": v.success,
                        "output": v.output,
                        "error": v.error,
                        "metadata": v.metadata,
                    } if hasattr(v, 'stage_name') else dict(v) if isinstance(v, dict) else {"raw": str(v)}
                ) for k, v in stages.items()},
                output=final_output,
                executed_by=executed_by,
                vetoed_by=vetoed_by,
                veto_reason=veto_reason,
                cost_estimate=cost_estimate,
                actual_cost=actual_cost,
                metadata=metadata or {},
            )
        # Fallback: return dict
        return {
            "request_id": request_id,
            "execution_id": execution_id,
            "trace_id": trace_id,
            "policy_decision": policy_decision,
            "execution_state": execution_state,
            "final_outcome": final_outcome,
            "stages": {k: {
                "stage_name": v.stage_name,
                "success": v.success,
                "output": v.output,
                "error": v.error,
                "metadata": v.metadata,
            } for k, v in stages.items()},
            "output": final_output,
            "executed_by": executed_by,
            "vetoed_by": vetoed_by,
            "veto_reason": veto_reason,
            "cost_estimate": cost_estimate,
            "actual_cost": actual_cost,
            "metadata": metadata or {},
        }


class AuditEmitter:
    """Emits audit events for all critical decisions."""

    def __init__(self):
        self._events: List[Dict] = []
        self._lock = threading.Lock()

    def emit(
        self,
        event_type: str,
        actor: str,
        request_id: str,
        execution_id: str,
        trace_id: str,
        decision: str,
        details: Dict[str, Any],
    ) -> None:
        """Emit audit event."""
        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "actor": actor,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request_id": request_id,
            "execution_id": execution_id,
            "trace_id": trace_id,
            "decision": decision,
            "details": details,
        }
        with self._lock:
            self._events.append(event)

    def get_events(self, request_id: Optional[str] = None) -> List[Dict]:
        with self._lock:
            if request_id:
                return [e for e in self._events if e["request_id"] == request_id]
            return list(self._events)


# =============================================================================
# Factory Functions
# =============================================================================

_lazy = LazyImports()

def create_request_validator() -> RequestValidator:
    return RequestValidator()

def create_safety_gate(safety_dept: Any, policy_engine: Any = None) -> SafetyGate:
    return SafetyGate(safety_dept, policy_engine)

def create_board_coordinator(board: Any) -> BoardCoordinator:
    return BoardCoordinator(board)

def create_executive_coordinator(csuite: Any, cost_service: Any, budget_ledger: Any) -> ExecutiveCoordinator:
    return ExecutiveCoordinator(csuite, cost_service, budget_ledger)

def create_execution_coordinator(depts: Dict[str, Any]) -> ExecutionCoordinator:
    return ExecutionCoordinator(depts)

def create_cost_controller(cost_service: Any, budget_ledger: Any) -> CostController:
    return CostController(cost_service, budget_ledger)

def create_result_assembler(result_factory=None) -> ResultAssembler:
    return ResultAssembler(result_factory=result_factory)

def create_audit_emitter() -> AuditEmitter:
    return AuditEmitter()

def create_safety_gate(safety_dept: Any, policy_engine: PolicyEngine = None) -> SafetyGate:
    return SafetyGate(safety_dept, policy_engine)

def create_board_coordinator(board: Any) -> BoardCoordinator:
    return BoardCoordinator(board)

def create_executive_coordinator(csuite: Any, cost_service: Any, budget_ledger: Any) -> ExecutiveCoordinator:
    return ExecutiveCoordinator(csuite, cost_service, budget_ledger)

def create_execution_coordinator(depts: Dict[str, Any]) -> ExecutionCoordinator:
    return ExecutionCoordinator(depts)

def create_cost_controller(cost_service: Any, budget_ledger: Any) -> CostController:
    return CostController(cost_service, budget_ledger)

def create_result_assembler(result_factory=None) -> ResultAssembler:
    return ResultAssembler(result_factory=result_factory)

def create_audit_emitter() -> AuditEmitter:
    return AuditEmitter()

def create_safety_gate(safety_dept: Any, policy_engine: PolicyEngine = None) -> SafetyGate:
    return SafetyGate(safety_dept, policy_engine)

def create_board_coordinator(board: Any) -> BoardCoordinator:
    return BoardCoordinator(board)

def create_executive_coordinator(csuite: Any, cost_service: Any, budget_ledger: Any) -> ExecutiveCoordinator:
    return ExecutiveCoordinator(csuite, cost_service, budget_ledger)

def create_execution_coordinator(depts: Dict[str, Any]) -> ExecutionCoordinator:
    return ExecutionCoordinator(depts)

def create_cost_controller(cost_service: Any, budget_ledger: Any) -> CostController:
    return CostController(cost_service, budget_ledger)

def create_result_assembler(result_factory=None) -> ResultAssembler:
    return ResultAssembler(result_factory=result_factory)

def create_audit_emitter() -> AuditEmitter:
    return AuditEmitter()

def create_safety_gate(safety_dept: Any, policy_engine: PolicyEngine = None) -> SafetyGate:
    return SafetyGate(safety_dept, policy_engine)

def create_board_coordinator(board: Any) -> BoardCoordinator:
    return BoardCoordinator(board)

def create_executive_coordinator(csuite: Any, cost_service: Any, budget_ledger: Any) -> ExecutiveCoordinator:
    return ExecutiveCoordinator(csuite, cost_service, budget_ledger)

def create_execution_coordinator(depts: Dict[str, Any]) -> ExecutionCoordinator:
    return ExecutionCoordinator(depts)

def create_cost_controller(cost_service: Any, budget_ledger: Any) -> CostController:
    return CostController(cost_service, budget_ledger)

def create_result_assembler(result_factory=None) -> ResultAssembler:
    return ResultAssembler(result_factory=result_factory)

def create_audit_emitter() -> AuditEmitter:
    return AuditEmitter()

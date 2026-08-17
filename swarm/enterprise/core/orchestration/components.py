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
import logging
import threading
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import uuid

from swarm.enterprise.core.auth import AuthorizationContext
from swarm.enterprise.core.policy.engine import PolicyEngine, get_policy_engine, PolicyContext, PolicyDecision
from swarm.enterprise.core.routing.engine import RoutingEngine, get_routing_engine, RoutingDecision
from swarm.enterprise.core.budget.cost_estimation import CostEstimationService, get_cost_estimation_service
from swarm.enterprise.core.budget.ledger import BudgetLedger, get_budget_ledger
from swarm.enterprise.core.execution.context import ExecutionContext, get_current_context
from swarm.enterprise.core.plane.control_plane import ControlPlane, get_control_plane, AdmissionRequest

logger = logging.getLogger(__name__)


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
        safety_dept,
        policy_engine: PolicyEngine = None,
    ):
        self.safety_dept = safety_dept
        self.policy_engine = policy_engine or get_policy_engine()

    def check(
        self,
        request: Any,
        exec_context: ExecutionContext,
        auth_context: AuthorizationContext,
    ) -> SwarmStageResult:
        """Run safety check with policy evaluation."""
        # Policy evaluation
        policy_ctx = PolicyContext(
            execution_context=exec_context,
            action="safety_check",
            resource=request.question[:100],
            metadata={"require_human_review": getattr(request, 'require_human_review', False)},
        )
        policy_results = self.policy_engine.evaluate(policy_ctx)
        allowed, _ = self.policy_engine.is_allowed(policy_ctx)

        if not allowed:
            for result in policy_results:
                if result.decision in (PolicyDecision.DENY, PolicyDecision.ESCALATE):
                    return SwarmStageResult(
                        stage_name="safety",
                        success=False,
                        error=result.reason,
                        metadata={"policy_results": [r.__dict__ for r in policy_results]},
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

    def __init__(self, board):
        self.board = board

    def deliberate(
        self,
        request: Any,
        exec_context: Any,
        auth_context: AuthorizationContext,
    ) -> SwarmStageResult:
        """Run board deliberation."""
        try:
            bypass_safety = auth_context.capabilities.has("override_safety") if auth_context else False
            board_result = self.board.deliberate(
                request.question,
                context=str(getattr(request, 'context', {})),
                bypass_safety=bypass_safety,
                authorization_context=auth_context,
            )

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
        csuite,
        cost_service,
        budget_ledger,
    ):
        self.csuite = csuite
        self.cost_service = cost_service
        self.budget_ledger = budget_ledger

    def decide(
        self,
        request: Any,
        board_result: Any,
        exec_context: Any,
        auth_context: AuthorizationContext,
    ) -> SwarmStageResult:
        """Run C-Suite executive meeting."""
        try:
            # Compute cost estimate
            from swarm.enterprise.core.budget.cost_estimation import CostEstimationRequest
            cost_est = self.cost_service.estimate(CostEstimationRequest(
                provider="nvidia_nim",
                model="nvidia/nemotron-3-super-120b-a12b",
                estimated_input_tokens=1000,
                estimated_output_tokens=1000,
                estimated_tool_calls=5,
                tenant_id=getattr(request, 'tenant_id', 'default'),
            ))

            # Atomic budget reservation
            tenant_id = getattr(request, 'tenant_id', 'default')
            account_id = f"budget-{tenant_id}"
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
            # For now, return a placeholder
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

    def __init__(self, cost_service, budget_ledger):
        self.cost_service = cost_service
        self.budget_ledger = budget_ledger

    def estimate_cost(self, request: Any, tenant_id: str) -> Dict[str, Any]:
        """Estimate cost for a request."""
        from swarm.enterprise.core.budget.cost_estimation import CostEstimationRequest
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
        stages: Dict[str, SwarmStageResult],
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
                stages={k: {
                    "stage_name": v.stage_name,
                    "success": v.success,
                    "output": v.output,
                    "error": v.error,
                    "metadata": v.metadata,
                } for k, v in stages.items()},
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


import threading
import uuid
from datetime import datetime, timezone


__all__ = [
    "RequestValidator",
    "SafetyGate",
    "BoardCoordinator",
    "ExecutiveCoordinator",
    "ExecutionCoordinator",
    "CostController",
    "ResultAssembler",
    "AuditEmitter",
    "SwarmStageResult",
]
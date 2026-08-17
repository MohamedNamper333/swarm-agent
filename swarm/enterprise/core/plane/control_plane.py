"""
Control Plane / Execution Plane Separation — F-028.

Control Plane: auth, policy, routing, budgeting, job creation, admission control
Execution Plane: workers, agents, providers, tools, actual execution
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Callable
from enum import Enum
from datetime import datetime, timezone
import uuid
import threading
import logging

from swarm.enterprise.core.auth import AuthorizationContext, Capability, Principal
from swarm.enterprise.core.budget.ledger import BudgetLedger, get_budget_ledger, BudgetType
from swarm.enterprise.core.budget.cost_estimation import CostEstimationService, get_cost_estimation_service
from swarm.enterprise.core.idempotency.store import IdempotencyStore, get_idempotency_store
from swarm.enterprise.core.policy.engine import PolicyEngine, get_policy_engine, PolicyContext, PolicyDecision
from swarm.enterprise.core.routing.engine import RoutingEngine, get_routing_engine, RoutingDecision, Department
from swarm.enterprise.core.job.models import DurableJob, JobQueue, JobConfig, JobPriority, get_job_queue, JobStatus
from swarm.enterprise.core.execution.context import ExecutionContext, ExecutionIdentity, get_current_context, set_current_context

logger = logging.getLogger(__name__)


class AdmissionDecision(str, Enum):
    ADMITTED = "admitted"
    REJECTED = "rejected"
    PENDING_APPROVAL = "pending_approval"


@dataclass
class AdmissionRequest:
    """Request for admission to execution plane."""
    request_id: str
    tenant_id: str
    principal_id: str
    job_type: str
    payload: Dict[str, Any]
    priority: JobPriority = JobPriority.NORMAL
    idempotency_key: Optional[str] = None
    authorization_context: Optional[AuthorizationContext] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AdmissionResult:
    """Result of admission control."""
    decision: AdmissionDecision
    request_id: str
    job_id: Optional[str] = None
    reason: str = ""
    policy_results: List[Any] = field(default_factory=list)
    cost_estimate: Optional[Dict[str, Any]] = None
    routing_decision: Optional[Any] = None
    required_approvals: List[str] = field(default_factory=list)


class ControlPlane:
    """
    Control Plane — handles all admission, authorization, policy, budgeting, routing.
    
    Responsibilities:
    - Authentication & Authorization
    - Policy Evaluation (safety, budget, tool, data, human_review)
    - Budget Reservation (atomic)
    - Routing Decision
    - Idempotency Check
    - Job Creation & Queue Admission
    - Audit Logging
    """

    def __init__(
        self,
        policy_engine: PolicyEngine = None,
        budget_ledger: BudgetLedger = None,
        cost_service: CostEstimationService = None,
        idempotency_store: IdempotencyStore = None,
        routing_engine: RoutingEngine = None,
        job_queue: JobQueue = None,
    ):
        self.policy_engine = policy_engine or get_policy_engine()
        self.budget_ledger = budget_ledger or get_budget_ledger()
        self.cost_service = cost_service or get_cost_estimation_service()
        self.idempotency_store = idempotency_store or get_idempotency_store()
        self.routing_engine = routing_engine or get_routing_engine()
        self.job_queue = job_queue or get_job_queue()
        self._lock = threading.RLock()

    def admit(self, request: AdmissionRequest) -> AdmissionResult:
        """
        Main admission control entry point.
        Runs all control plane checks before admitting to execution plane.
        """
        # 1. Idempotency check
        if request.idempotency_key:
            existing, is_new = self.idempotency_store.check_and_store(
                key=request.idempotency_key,
                tenant_id=request.tenant_id,
                payload={
                    "job_type": request.job_type,
                    "payload": request.payload,
                },
            )
            if not is_new:
                if existing.status.value == "completed":
                    return AdmissionResult(
                        decision=AdmissionDecision.REJECTED,
                        request_id=request.request_id,
                        reason="Duplicate request (idempotent)",
                    )
                elif existing.status.value == "conflict":
                    return AdmissionResult(
                        decision=AdmissionDecision.REJECTED,
                        request_id=request.request_id,
                        reason="Idempotency key conflict",
                    )

        # 2. Create execution context for policy evaluation
        exec_context = ExecutionContext.create(
            tenant_id=request.tenant_id,
            principal_id=request.principal_id,
            authorization_context=request.authorization_context,
        )

        # 3. Policy evaluation
        policy_ctx = PolicyContext(
            execution_context=exec_context,
            action=request.job_type,
            resource=request.job_type,
            metadata=request.metadata,
        )
        policy_results = self.policy_engine.evaluate(policy_ctx)
        allowed, _ = self.policy_engine.is_allowed(policy_ctx)

        required_approvals = []
        for result in policy_results:
            if result.decision == PolicyDecision.REQUIRE_APPROVAL:
                required_approvals.extend(result.required_approvals)

        if not allowed and not required_approvals:
            return AdmissionResult(
                decision=AdmissionDecision.REJECTED,
                request_id=request.request_id,
                reason="Policy denied",
                policy_results=policy_results,
            )

        if required_approvals:
            return AdmissionResult(
                decision=AdmissionDecision.PENDING_APPROVAL,
                request_id=request.request_id,
                reason="Requires human approval",
                policy_results=policy_results,
                required_approvals=required_approvals,
            )

        # 4. Cost estimation
        cost_estimate = self._estimate_cost(request, exec_context)

        # 5. Budget reservation (atomic)
        if cost_estimate and cost_estimate.get("estimated_total", 0) > 0:
            account_id = f"budget-{request.tenant_id}"
            try:
                self.budget_ledger.reserve(
                    account_id=account_id,
                    amount=cost_estimate["estimated_total"],
                    metadata={"request_id": request.request_id},
                )
            except ValueError as e:
                return AdmissionResult(
                    decision=AdmissionDecision.REJECTED,
                    request_id=request.request_id,
                    reason=f"Budget reservation failed: {e}",
                )

        # 6. Routing decision
        routing_decision = self.routing_engine.route(
            question=request.payload.get("question", ""),
            explicit_type=request.metadata.get("explicit_type"),
            context=request.payload.get("context"),
        )

        # 7. Create durable job
        job = DurableJob(
            job_id=str(uuid.uuid4()),
            job_type=request.job_type,
            payload=request.payload,
            config=JobConfig(
                priority=request.priority,
                idempotency_key=request.idempotency_key,
                tenant_id=request.tenant_id,
                tags=request.metadata.get("tags", []),
            ),
            metadata={
                "request_id": request.request_id,
                "routing_decision": routing_decision.to_dict(),
                "cost_estimate": cost_estimate,
                "policy_results": [r.__dict__ for r in policy_results],
            },
        )

        # 8. Enqueue job
        self.job_queue.enqueue(job)

        # 9. Mark idempotency as admitted
        if request.idempotency_key:
            self.idempotency_store.mark_completed(
                key=request.idempotency_key,
                execution_id=job.job_id,
                response_reference=f"job:{job.job_id}",
            )

        return AdmissionResult(
            decision=AdmissionDecision.ADMITTED,
            request_id=request.request_id,
            job_id=job.job_id,
            reason="Admitted to execution plane",
            policy_results=policy_results,
            cost_estimate=cost_estimate,
            routing_decision=routing_decision,
        )

    def _estimate_cost(self, request: AdmissionRequest, exec_context: ExecutionContext) -> Optional[Dict[str, Any]]:
        """Estimate cost for the request."""
        # Get model for job type (simplified)
        model_map = {
            "code": "nvidia/nemotron-3-super-120b-a12b",
            "design": "black-forest-labs/flux.1-dev",
            "video": "nvidia/cosmos-predict1-7b",
            "research": "openai/gpt-oss-120b",
            "data": "google/gemma-3-27b-it",
            "language": "nvidia/riva-translate-4b-instruct-v2",
            "knowledge": "nvidia/llama-3.2-nemoretriever-300m-embed-v2",
            "safety": "nvidia/llama-3.1-nemoguard-8b-content-safety",
        }
        model = model_map.get(request.job_type, "nvidia/nemotron-3-super-120b-a12b")

        # Estimate tokens based on job type
        token_estimates = {
            "code": 5000,
            "design": 1000,
            "video": 2000,
            "research": 8000,
            "data": 3000,
            "language": 2000,
            "knowledge": 2000,
            "safety": 1000,
        }
        estimated_tokens = token_estimates.get(request.job_type, 2000)

        estimate = self.cost_service.estimate_from_execution(
            provider="nvidia_nim",
            model=model,
            actual_input_tokens=estimated_tokens // 2,
            actual_output_tokens=estimated_tokens // 2,
            actual_tool_calls=5,
        )

        return {
            "estimated_total": str(estimate.total),
            "currency": estimate.currency,
            "breakdown": estimate.breakdown,
            "pricing_version": estimate.pricing_version,
        }

    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job status from execution plane."""
        job = self.job_queue.get(job_id)
        if not job:
            return None
        return job.to_dict()

    def cancel_job(self, job_id: str, reason: str = "cancelled_by_user") -> bool:
        """Cancel a job."""
        job = self.job_queue.get(job_id)
        if not job:
            return False
        if job.status in (JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELLED, JobStatus.DEAD_LETTER):
            return False
        job.transition_to(JobStatus.CANCELLED, "control_plane", reason)
        return True


# Singleton
_control_plane: Optional["ControlPlane"] = None
_cp_lock = threading.Lock()


def get_control_plane() -> ControlPlane:
    global _control_plane
    with _cp_lock:
        if _control_plane is None:
            _control_plane = ControlPlane()
        return _control_plane


__all__ = [
    "AdmissionDecision",
    "AdmissionRequest",
    "AdmissionResult",
    "ControlPlane",
    "get_control_plane",
]
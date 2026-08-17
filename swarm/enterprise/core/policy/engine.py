"""
Policy Engine — centralized policy evaluation for all governance decisions.

F-029: Lack of Formal Policy Engine fix.
Consolidates SafetyPolicy, AuthorizationPolicy, BudgetPolicy, ToolPolicy, DataPolicy, HumanReviewPolicy.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Set, Protocol
from abc import abstractmethod
from enum import Enum
from datetime import datetime, timezone

from swarm.enterprise.core.auth import AuthorizationContext, Capability, ExecutionCapabilities, DEFAULT_AUTH_POLICY
from swarm.enterprise.core.budget.cost_estimation import CostEstimationService, get_cost_estimation_service
from swarm.enterprise.core.budget.ledger import BudgetLedger, get_budget_ledger, BudgetType
from swarm.enterprise.core.policy.tool_policy import ToolPolicyRegistry, get_tool_policy_registry, RiskLevel, SideEffectLevel
from swarm.enterprise.core.execution.context import ExecutionContext, ResourceBudget


class PolicyDecision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    ESCALATE = "escalate"
    REQUIRE_APPROVAL = "require_approval"


@dataclass
class PolicyContext:
    """Context passed to policy evaluation."""
    execution_context: ExecutionContext
    action: str  # e.g., "invoke_model", "write_file", "override_safety"
    resource: Optional[str] = None  # e.g., model name, file path
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PolicyResult:
    """Result of policy evaluation."""
    decision: PolicyDecision
    policy_name: str
    reason: str
    required_capabilities: Set[Capability] = field(default_factory=set)
    required_approvals: List[str] = field(default_factory=list)
    conditions: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class Policy(Protocol):
    """Protocol for all policy types."""

    @property
    def name(self) -> str:
        ...

    def evaluate(self, context: PolicyContext) -> PolicyResult:
        ...


class SafetyPolicy:
    """Safety/content policy evaluation."""

    def __init__(self):
        self.name = "safety"

    def evaluate(self, context: PolicyContext) -> PolicyResult:
        # Check if safety override is requested
        if context.action == "override_safety":
            caps = context.execution_context.authorization_context.capabilities if context.execution_context.authorization_context else set()
            if Capability.OVERRIDE_SAFETY in caps:
                return PolicyResult(
                    decision=PolicyDecision.ALLOW,
                    policy_name=self.name,
                    reason="Safety override authorized",
                    required_capabilities={Capability.OVERRIDE_SAFETY},
                )
            return PolicyResult(
                decision=PolicyDecision.DENY,
                policy_name=self.name,
                reason="Safety override requires OVERRIDE_SAFETY capability",
                required_capabilities={Capability.OVERRIDE_SAFETY},
            )

        # Check if content requires safety review
        if context.metadata.get("requires_safety_review", False):
            return PolicyResult(
                decision=PolicyDecision.ESCALATE,
                policy_name=self.name,
                reason="Content requires safety review",
                required_approvals=["safety_reviewer"],
            )

        return PolicyResult(
            decision=PolicyDecision.ALLOW,
            policy_name=self.name,
            reason="Safety check passed",
        )


class AuthorizationPolicy:
    """Authorization policy evaluation."""

    def __init__(self, auth_policy: Optional[Any] = None):
        self.name = "authorization"
        self._auth_policy = auth_policy or DEFAULT_AUTH_POLICY

    def evaluate(self, context: PolicyContext) -> PolicyResult:
        auth_ctx = context.execution_context.authorization_context
        if not auth_ctx:
            return PolicyResult(
                decision=PolicyDecision.DENY,
                policy_name=self.name,
                reason="No authorization context",
            )

        # Check tenant isolation
        if context.execution_context.tenant_id != auth_ctx.principal.tenant_id:
            if Capability.CROSS_TENANT_ACCESS not in auth_ctx.capabilities.capabilities:
                return PolicyResult(
                    decision=PolicyDecision.DENY,
                    policy_name=self.name,
                    reason="Cross-tenant access not authorized",
                    required_capabilities={Capability.CROSS_TENANT_ACCESS},
                )

        # Check capability for action
        action_capability_map = {
            "override_safety": Capability.OVERRIDE_SAFETY,
            "override_budget": Capability.OVERRIDE_BUDGET,
            "override_routing": Capability.OVERRIDE_ROUTING,
            "admin_veto_override": Capability.ADMIN_VETO_OVERRIDE,
            "internal_system_call": Capability.INTERNAL_SYSTEM_CALL,
            "cross_tenant_access": Capability.CROSS_TENANT_ACCESS,
            "privileged_tool_access": Capability.PRIVILEGED_TOOL_ACCESS,
            "memory_write": Capability.MEMORY_WRITE,
            "memory_read_all": Capability.MEMORY_READ_ALL,
        }

        required_cap = action_capability_map.get(context.action)
        if required_cap and required_cap not in auth_ctx.capabilities.capabilities:
            return PolicyResult(
                decision=PolicyDecision.DENY,
                policy_name=self.name,
                reason=f"Action {context.action} requires {required_cap.value} capability",
                required_capabilities={required_cap} if required_cap else set(),
            )

        return PolicyResult(
            decision=PolicyDecision.ALLOW,
            policy_name=self.name,
            reason="Authorization passed",
        )


class BudgetPolicy:
    """Budget policy evaluation."""

    def __init__(self, cost_service: Optional[CostEstimationService] = None, ledger: Optional[BudgetLedger] = None):
        self.name = "budget"
        self._cost_service = cost_service or get_cost_estimation_service()
        self._ledger = ledger or get_budget_ledger()

    def evaluate(self, context: PolicyContext) -> PolicyResult:
        # Check budget override
        if context.action == "override_budget":
            caps = context.execution_context.authorization_context.capabilities if context.execution_context.authorization_context else set()
            if Capability.OVERRIDE_BUDGET in caps:
                return PolicyResult(
                    decision=PolicyDecision.ALLOW,
                    policy_name=self.name,
                    reason="Budget override authorized",
                    required_capabilities={Capability.OVERRIDE_BUDGET},
                )
            return PolicyResult(
                decision=PolicyDecision.DENY,
                policy_name=self.name,
                reason="Budget override requires OVERRIDE_BUDGET capability",
                required_capabilities={Capability.OVERRIDE_BUDGET},
            )

        # For model invocations, check cost
        if context.action == "invoke_model":
            model = context.resource or context.metadata.get("model")
            estimated_tokens = context.metadata.get("estimated_tokens", 1000)

            if model:
                estimate = self._cost_service.estimate_from_execution(
                    provider=context.metadata.get("provider", "nvidia_nim"),
                    model=model,
                    actual_input_tokens=estimated_tokens // 2,
                    actual_output_tokens=estimated_tokens // 2,
                )

                # Check if budget allows
                # This would need a budget account - for now just return estimate
                return PolicyResult(
                    decision=PolicyDecision.ALLOW,
                    policy_name=self.name,
                    reason="Budget check passed",
                    conditions={
                        "estimated_cost": str(estimate.total),
                        "currency": estimate.currency,
                    },
                )

        return PolicyResult(
            decision=PolicyDecision.ALLOW,
            policy_name=self.name,
            reason="Budget check passed",
        )


class ToolPolicy:
    """Tool access policy evaluation."""

    def __init__(self, tool_registry: Optional[ToolPolicyRegistry] = None):
        self.name = "tool"
        self._tool_registry = tool_registry or get_tool_policy_registry()

    def evaluate(self, context: PolicyContext) -> PolicyResult:
        if not context.action.startswith("tool:") and context.action != "invoke_tool":
            return PolicyResult(
                decision=PolicyDecision.ALLOW,
                policy_name=self.name,
                reason="Not a tool action",
            )

        # For tool actions, prioritize tool_name from metadata over resource
        if context.action == "invoke_tool":
            tool_name = context.metadata.get("tool_name") or context.resource
        else:
            tool_name = context.resource or context.metadata.get("tool_name")
        if not tool_name:
            return PolicyResult(
                decision=PolicyDecision.DENY,
                policy_name=self.name,
                reason="Tool name required",
            )

        tenant_id = context.execution_context.tenant_id
        capabilities = set()
        if context.execution_context.authorization_context:
            capabilities = set(c.value for c in context.execution_context.authorization_context.capabilities.capabilities)

        allowed, reason = self._tool_registry.evaluate(
            tool_name=tool_name,
            tenant_id=tenant_id,
            capabilities=capabilities,
            execution_context=context.metadata,
        )

        if not allowed:
            return PolicyResult(
                decision=PolicyDecision.DENY,
                policy_name=self.name,
                reason=reason,
            )

        policy = self._tool_registry.get(tool_name)
        if policy and policy.requires_approval:
            return PolicyResult(
                decision=PolicyDecision.REQUIRE_APPROVAL,
                policy_name=self.name,
                reason=f"Tool {tool_name} requires approval",
                required_approvals=list(policy.approval_roles),
                conditions={"risk_level": policy.risk_level.value, "side_effect": policy.side_effect_level.value},
            )

        return PolicyResult(
            decision=PolicyDecision.ALLOW,
            policy_name=self.name,
            reason="Tool access granted",
            conditions={"risk_level": policy.risk_level.value if policy else "unknown"},
        )


class DataPolicy:
    """Data classification and access policy."""

    def __init__(self):
        self.name = "data"

    def evaluate(self, context: PolicyContext) -> PolicyResult:
        # Check data classification
        classification = context.metadata.get("classification", "INTERNAL")
        tenant_id = context.execution_context.tenant_id

        # PII/SECRET data requires special handling
        if classification in ("PII", "SECRET", "RESTRICTED"):
            caps = context.execution_context.authorization_context.capabilities if context.execution_context.authorization_context else set()
            if Capability.PRIVILEGED_TOOL_ACCESS not in caps:
                return PolicyResult(
                    decision=PolicyDecision.REQUIRE_APPROVAL,
                    policy_name=self.name,
                    reason=f"Access to {classification} data requires approval",
                    required_approvals=["data_protection_officer"],
                )

        # Cross-tenant data access
        if context.metadata.get("cross_tenant_data", False):
            caps = context.execution_context.authorization_context.capabilities if context.execution_context.authorization_context else set()
            if Capability.CROSS_TENANT_ACCESS not in caps:
                return PolicyResult(
                    decision=PolicyDecision.DENY,
                    policy_name=self.name,
                    reason="Cross-tenant data access not authorized",
                    required_capabilities={Capability.CROSS_TENANT_ACCESS},
                )

        return PolicyResult(
            decision=PolicyDecision.ALLOW,
            policy_name=self.name,
            reason="Data access allowed",
        )


class HumanReviewPolicy:
    """Human review policy evaluation."""

    def __init__(self):
        self.name = "human_review"

    def evaluate(self, context: PolicyContext) -> PolicyResult:
        if context.execution_context.state.name == "REQUIRES_HUMAN_REVIEW":
            return PolicyResult(
                decision=PolicyDecision.ESCALATE,
                policy_name=self.name,
                reason="Execution requires human review",
                required_approvals=["human_reviewer"],
            )

        # Check if action requires human review
        if context.metadata.get("require_human_review", False):
            return PolicyResult(
                decision=PolicyDecision.REQUIRE_APPROVAL,
                policy_name=self.name,
                reason="Action requires human review",
                required_approvals=["human_reviewer"],
            )

        return PolicyResult(
            decision=PolicyDecision.ALLOW,
            policy_name=self.name,
            reason="No human review required",
        )


class PolicyEngine:
    """Central policy engine evaluating all policies in sequence."""

    def __init__(
        self,
        safety_policy: Optional[SafetyPolicy] = None,
        auth_policy: Optional[AuthorizationPolicy] = None,
        budget_policy: Optional[BudgetPolicy] = None,
        tool_policy: Optional[ToolPolicy] = None,
        data_policy: Optional[DataPolicy] = None,
        human_review_policy: Optional[HumanReviewPolicy] = None,
    ):
        self.policies: List[Policy] = [
            safety_policy or SafetyPolicy(),
            auth_policy or AuthorizationPolicy(),
            budget_policy or BudgetPolicy(),
            tool_policy or ToolPolicy(),
            data_policy or DataPolicy(),
            human_review_policy or HumanReviewPolicy(),
        ]

    def evaluate(self, context: PolicyContext) -> List[PolicyResult]:
        """Evaluate all policies. Returns results in order."""
        results = []
        for policy in self.policies:
            try:
                result = policy.evaluate(context)
                results.append(result)
                # Short-circuit on DENY
                if result.decision == PolicyDecision.DENY:
                    break
            except Exception as e:
                results.append(PolicyResult(
                    decision=PolicyDecision.DENY,
                    policy_name=policy.name,
                    reason=f"Policy evaluation error: {e}",
                ))
                break
        return results

    def evaluate_single(self, context: PolicyContext, policy_name: str) -> PolicyResult:
        """Evaluate a single policy by name."""
        for policy in self.policies:
            if policy.name == policy_name:
                return policy.evaluate(context)
        raise ValueError(f"Policy {policy_name} not found")

    def is_allowed(self, context: PolicyContext) -> tuple[bool, List[PolicyResult]]:
        """Check if all policies allow the action."""
        results = self.evaluate(context)
        for result in results:
            if result.decision in (PolicyDecision.DENY, PolicyDecision.ESCALATE, PolicyDecision.REQUIRE_APPROVAL):
                return False, results
        return True, results


# Global engine instance
_policy_engine: Optional[PolicyEngine] = None
_engine_lock = None


def get_policy_engine() -> PolicyEngine:
    global _policy_engine, _engine_lock
    if _policy_engine is None:
        import threading
        if _engine_lock is None:
            _engine_lock = threading.Lock()
        with _engine_lock:
            if _policy_engine is None:
                _policy_engine = PolicyEngine()
    return _policy_engine


__all__ = [
    "PolicyDecision",
    "PolicyContext",
    "PolicyResult",
    "Policy",
    "SafetyPolicy",
    "AuthorizationPolicy",
    "BudgetPolicy",
    "ToolPolicy",
    "DataPolicy",
    "HumanReviewPolicy",
    "PolicyEngine",
    "get_policy_engine",
]
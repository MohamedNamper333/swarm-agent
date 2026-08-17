"""
Tool Policy — capability-based tool access control.

F-033: No Explicit Tool Authorization fix.
F-015: Safety Layer Too Dependent on Pattern Matching - adds policy-controlled tool access.
"""
from dataclasses import dataclass, field
from typing import Dict, Set, Optional, List, FrozenSet
from enum import Enum
from datetime import datetime, timezone


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SideEffectLevel(str, Enum):
    NONE = "none"           # Read-only, no external effects
    READ = "read"           # Reads external state
    WRITE = "write"         # Writes external state
    DESTRUCTIVE = "destructive"  # Deletes, modifies irreversibly
    FINANCIAL = "financial" # Involves money/costs
    PRIVILEGED = "privileged"    # Requires elevated permissions


@dataclass(frozen=True)
class ToolPolicy:
    """Policy governing access to a specific tool."""
    name: str
    risk_level: RiskLevel
    required_capability: str  # Capability name from auth.Capability
    allowed_tenants: FrozenSet[str] = field(default_factory=frozenset)  # Empty = all
    side_effect_level: SideEffectLevel = SideEffectLevel.READ
    description: str = ""
    max_calls_per_execution: int = 10
    requires_approval: bool = False
    approval_roles: FrozenSet[str] = field(default_factory=frozenset)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    version: int = 1

    def is_allowed_for_tenant(self, tenant_id: str) -> bool:
        if not self.allowed_tenants:
            return True
        return tenant_id in self.allowed_tenants

    def is_allowed_for_capability(self, capabilities: Set[str]) -> bool:
        return self.required_capability in capabilities

    def requires_explicit_approval(self) -> bool:
        return self.requires_approval


class ToolPolicyRegistry:
    """Registry of tool policies with evaluation logic."""

    def __init__(self):
        self._policies: Dict[str, ToolPolicy] = {}
        self._register_default_policies()

    def _register_default_policies(self):
        """Register default tool policies."""
        defaults = [
            # Read-only tools - low risk
            ToolPolicy(
                name="web_search",
                risk_level=RiskLevel.LOW,
                required_capability="tool:web_search",
                side_effect_level=SideEffectLevel.READ,
                description="Search the web for information",
                max_calls_per_execution=20,
            ),
            ToolPolicy(
                name="read_file",
                risk_level=RiskLevel.LOW,
                required_capability="tool:read_file",
                side_effect_level=SideEffectLevel.READ,
                description="Read file contents",
                max_calls_per_execution=50,
            ),
            ToolPolicy(
                name="list_directory",
                risk_level=RiskLevel.LOW,
                required_capability="tool:list_directory",
                side_effect_level=SideEffectLevel.READ,
                description="List directory contents",
                max_calls_per_execution=20,
            ),
            ToolPolicy(
                name="code_search",
                risk_level=RiskLevel.LOW,
                required_capability="tool:code_search",
                side_effect_level=SideEffectLevel.READ,
                description="Search codebase for patterns",
                max_calls_per_execution=30,
            ),

            # Write tools - medium risk
            ToolPolicy(
                name="write_file",
                risk_level=RiskLevel.MEDIUM,
                required_capability="tool:write_file",
                side_effect_level=SideEffectLevel.WRITE,
                description="Write file contents",
                max_calls_per_execution=20,
            ),
            ToolPolicy(
                name="edit_file",
                risk_level=RiskLevel.MEDIUM,
                required_capability="tool:edit_file",
                side_effect_level=SideEffectLevel.WRITE,
                description="Edit file contents",
                max_calls_per_execution=30,
            ),
            ToolPolicy(
                name="run_command",
                risk_level=RiskLevel.HIGH,
                required_capability="tool:run_command",
                side_effect_level=SideEffectLevel.WRITE,
                description="Execute shell command",
                max_calls_per_execution=10,
                requires_approval=True,
                approval_roles=frozenset(["admin", "system"]),
            ),
            ToolPolicy(
                name="create_directory",
                risk_level=RiskLevel.MEDIUM,
                required_capability="tool:create_directory",
                side_effect_level=SideEffectLevel.WRITE,
                description="Create directory",
                max_calls_per_execution=10,
            ),

            # Destructive tools - high/critical risk
            ToolPolicy(
                name="delete_file",
                risk_level=RiskLevel.HIGH,
                required_capability="tool:delete_file",
                side_effect_level=SideEffectLevel.DESTRUCTIVE,
                description="Delete file",
                max_calls_per_execution=5,
                requires_approval=True,
                approval_roles=frozenset(["admin", "system"]),
            ),
            ToolPolicy(
                name="delete_directory",
                risk_level=RiskLevel.CRITICAL,
                required_capability="tool:delete_directory",
                side_effect_level=SideEffectLevel.DESTRUCTIVE,
                description="Delete directory recursively",
                max_calls_per_execution=2,
                requires_approval=True,
                approval_roles=frozenset(["admin"]),
            ),

            # Financial tools
            ToolPolicy(
                name="charge_payment",
                risk_level=RiskLevel.CRITICAL,
                required_capability="tool:charge_payment",
                side_effect_level=SideEffectLevel.FINANCIAL,
                description="Process payment",
                max_calls_per_execution=1,
                requires_approval=True,
                approval_roles=frozenset(["admin", "finance"]),
            ),
            ToolPolicy(
                name="create_subscription",
                risk_level=RiskLevel.HIGH,
                required_capability="tool:create_subscription",
                side_effect_level=SideEffectLevel.FINANCIAL,
                description="Create recurring subscription",
                max_calls_per_execution=1,
                requires_approval=True,
                approval_roles=frozenset(["admin", "finance"]),
            ),

            # Model/API invocation tools
            ToolPolicy(
                name="invoke_model",
                risk_level=RiskLevel.MEDIUM,
                required_capability="tool:invoke_model",
                side_effect_level=SideEffectLevel.WRITE,
                description="Invoke LLM model",
                max_calls_per_execution=50,
            ),
            ToolPolicy(
                name="invoke_tool",
                risk_level=RiskLevel.MEDIUM,
                required_capability="tool:invoke_tool",
                side_effect_level=SideEffectLevel.WRITE,
                description="Invoke another tool",
                max_calls_per_execution=20,
            ),

            # Memory tools
            ToolPolicy(
                name="memory_write",
                risk_level=RiskLevel.MEDIUM,
                required_capability="tool:memory_write",
                side_effect_level=SideEffectLevel.WRITE,
                description="Write to agent memory",
                max_calls_per_execution=20,
            ),
            ToolPolicy(
                name="memory_read",
                risk_level=RiskLevel.LOW,
                required_capability="tool:memory_read",
                side_effect_level=SideEffectLevel.READ,
                description="Read from agent memory",
                max_calls_per_execution=50,
            ),

            # Department execution tools
            ToolPolicy(
                name="dept_code_execute",
                risk_level=RiskLevel.MEDIUM,
                required_capability="dept_code_execute",
                side_effect_level=SideEffectLevel.WRITE,
                description="Execute code department pipeline",
                max_calls_per_execution=1,
            ),
            ToolPolicy(
                name="dept_design_execute",
                risk_level=RiskLevel.MEDIUM,
                required_capability="dept_design_execute",
                side_effect_level=SideEffectLevel.WRITE,
                description="Execute design department pipeline",
                max_calls_per_execution=1,
            ),
            ToolPolicy(
                name="dept_video_execute",
                risk_level=RiskLevel.MEDIUM,
                required_capability="dept_video_execute",
                side_effect_level=SideEffectLevel.WRITE,
                description="Execute video department pipeline",
                max_calls_per_execution=1,
            ),
            ToolPolicy(
                name="dept_research_execute",
                risk_level=RiskLevel.MEDIUM,
                required_capability="dept_research_execute",
                side_effect_level=SideEffectLevel.WRITE,
                description="Execute research department pipeline",
                max_calls_per_execution=1,
            ),
            ToolPolicy(
                name="dept_data_execute",
                risk_level=RiskLevel.MEDIUM,
                required_capability="dept_data_execute",
                side_effect_level=SideEffectLevel.WRITE,
                description="Execute data department pipeline",
                max_calls_per_execution=1,
            ),
            ToolPolicy(
                name="dept_language_execute",
                risk_level=RiskLevel.MEDIUM,
                required_capability="dept_language_execute",
                side_effect_level=SideEffectLevel.WRITE,
                description="Execute language department pipeline",
                max_calls_per_execution=1,
            ),
            ToolPolicy(
                name="dept_knowledge_execute",
                risk_level=RiskLevel.MEDIUM,
                required_capability="dept_knowledge_execute",
                side_effect_level=SideEffectLevel.WRITE,
                description="Execute knowledge department pipeline",
                max_calls_per_execution=1,
            ),
            ToolPolicy(
                name="dept_safety_execute",
                risk_level=RiskLevel.MEDIUM,
                required_capability="dept_safety_execute",
                side_effect_level=SideEffectLevel.WRITE,
                description="Execute safety department pipeline",
                max_calls_per_execution=1,
            ),

            # System tools
            ToolPolicy(
                name="system_restart",
                risk_level=RiskLevel.CRITICAL,
                required_capability="tool:system_restart",
                side_effect_level=SideEffectLevel.DESTRUCTIVE,
                description="Restart system component",
                max_calls_per_execution=1,
                requires_approval=True,
                approval_roles=frozenset(["admin"]),
            ),
            ToolPolicy(
                name="deploy",
                risk_level=RiskLevel.CRITICAL,
                required_capability="tool:deploy",
                side_effect_level=SideEffectLevel.DESTRUCTIVE,
                description="Deploy to production",
                max_calls_per_execution=1,
                requires_approval=True,
                approval_roles=frozenset(["admin", "release_engineer"]),
            ),
        ]

        for policy in defaults:
            self.register(policy)

    def register(self, policy: ToolPolicy) -> None:
        """Register a tool policy."""
        self._policies[policy.name] = policy

    def get(self, tool_name: str) -> Optional[ToolPolicy]:
        """Get policy for a tool."""
        return self._policies.get(tool_name)

    def evaluate(
        self,
        tool_name: str,
        tenant_id: str,
        capabilities: Set[str],
        execution_context: Optional[Dict] = None,
    ) -> tuple[bool, str]:
        """
        Evaluate if tool invocation is allowed.
        Returns (allowed, reason).
        """
        policy = self._policies.get(tool_name)
        if not policy:
            return False, f"No policy registered for tool: {tool_name}"

        # Check tenant
        if not policy.is_allowed_for_tenant(tenant_id):
            return False, f"Tool {tool_name} not allowed for tenant {tenant_id}"

        # Check capability
        if not policy.is_allowed_for_capability(capabilities):
            return False, f"Missing required capability: {policy.required_capability}"

        # Check approval requirement
        if policy.requires_approval:
            approver_role = execution_context.get("approver_role") if execution_context else None
            if approver_role not in policy.approval_roles:
                return False, f"Tool {tool_name} requires approval from {policy.approval_roles}"

        return True, "allowed"

    def list_all(self) -> List[ToolPolicy]:
        """List all registered policies."""
        return list(self._policies.values())

    def list_by_risk(self, risk_level: RiskLevel) -> List[ToolPolicy]:
        """List policies by risk level."""
        return [p for p in self._policies.values() if p.risk_level == risk_level]


# Global registry
_tool_policy_registry: Optional[ToolPolicyRegistry] = None
_registry_lock = None  # Will be initialized on first access


def get_tool_policy_registry() -> ToolPolicyRegistry:
    global _tool_policy_registry, _registry_lock
    if _tool_policy_registry is None:
        import threading
        if _registry_lock is None:
            _registry_lock = threading.Lock()
        with _registry_lock:
            if _tool_policy_registry is None:
                _tool_policy_registry = ToolPolicyRegistry()
    return _tool_policy_registry


__all__ = [
    "RiskLevel",
    "SideEffectLevel",
    "ToolPolicy",
    "ToolPolicyRegistry",
    "get_tool_policy_registry",
]
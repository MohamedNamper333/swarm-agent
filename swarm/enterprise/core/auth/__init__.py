"""
Authorization Context & Capabilities — server-issued capabilities replacing client-controlled bypass.

F-001: Client-Controlled Safety Bypass fix.
Replaces `bypass_safety` in request with server-authorized `ExecutionCapabilities`.
"""
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Set, FrozenSet
from enum import Enum
from datetime import datetime, timezone
import uuid


class Capability(str, Enum):
    """Granular capabilities that can be granted to principals."""
    OVERRIDE_SAFETY = "override_safety"
    OVERRIDE_BUDGET = "override_budget"
    OVERRIDE_ROUTING = "override_routing"
    ADMIN_VETO_OVERRIDE = "admin_veto_override"
    INTERNAL_SYSTEM_CALL = "internal_system_call"
    CROSS_TENANT_ACCESS = "cross_tenant_access"
    PRIVILEGED_TOOL_ACCESS = "privileged_tool_access"
    MEMORY_WRITE = "memory_write"
    MEMORY_READ_ALL = "memory_read_all"
    # Department execution capabilities
    DEPT_CODE_EXECUTE = "dept_code_execute"
    DEPT_DESIGN_EXECUTE = "dept_design_execute"
    DEPT_VIDEO_EXECUTE = "dept_video_execute"
    DEPT_RESEARCH_EXECUTE = "dept_research_execute"
    DEPT_DATA_EXECUTE = "dept_data_execute"
    DEPT_LANGUAGE_EXECUTE = "dept_language_execute"
    DEPT_KNOWLEDGE_EXECUTE = "dept_knowledge_execute"
    DEPT_SAFETY_EXECUTE = "dept_safety_execute"


@dataclass(frozen=True)
class ExecutionCapabilities:
    """Immutable set of capabilities granted to an execution context."""
    capabilities: FrozenSet[Capability] = field(default_factory=frozenset)

    def has(self, capability: Capability) -> bool:
        return capability in self.capabilities

    def with_capability(self, capability: Capability) -> "ExecutionCapabilities":
        return ExecutionCapabilities(capabilities=self.capabilities | {capability})

    def without_capability(self, capability: Capability) -> "ExecutionCapabilities":
        return ExecutionCapabilities(capabilities=self.capabilities - {capability})

    @classmethod
    def none(cls) -> "ExecutionCapabilities":
        return cls(capabilities=frozenset())

    @classmethod
    def all(cls) -> "ExecutionCapabilities":
        return cls(capabilities=frozenset(Capability))

    @classmethod
    def for_system(cls) -> "ExecutionCapabilities":
        """Capabilities for internal system calls."""
        return cls(capabilities=frozenset([
            Capability.INTERNAL_SYSTEM_CALL,
            Capability.OVERRIDE_SAFETY,
            Capability.OVERRIDE_BUDGET,
            Capability.OVERRIDE_ROUTING,
            Capability.PRIVILEGED_TOOL_ACCESS,
            Capability.MEMORY_WRITE,
            Capability.MEMORY_READ_ALL,
            Capability.CROSS_TENANT_ACCESS,
            Capability.DEPT_CODE_EXECUTE,
            Capability.DEPT_DESIGN_EXECUTE,
            Capability.DEPT_VIDEO_EXECUTE,
            Capability.DEPT_RESEARCH_EXECUTE,
            Capability.DEPT_DATA_EXECUTE,
            Capability.DEPT_LANGUAGE_EXECUTE,
            Capability.DEPT_KNOWLEDGE_EXECUTE,
            Capability.DEPT_SAFETY_EXECUTE,
        ]))

    @classmethod
    def for_admin(cls) -> "ExecutionCapabilities":
        """Capabilities for admin users."""
        return cls(capabilities=frozenset([
            Capability.ADMIN_VETO_OVERRIDE,
            Capability.CROSS_TENANT_ACCESS,
            Capability.PRIVILEGED_TOOL_ACCESS,
            Capability.MEMORY_WRITE,
            Capability.MEMORY_READ_ALL,
        ]))

    @classmethod
    def for_user(cls) -> "ExecutionCapabilities":
        """Default capabilities for regular users."""
        return cls(capabilities=frozenset())


@dataclass(frozen=True)
class Principal:
    """Authenticated principal (user, service, system)."""
    id: str
    type: str  # "user", "service", "system", "admin"
    tenant_id: str
    roles: FrozenSet[str] = field(default_factory=frozenset)
    permissions: FrozenSet[str] = field(default_factory=frozenset)

    @classmethod
    def system(cls, tenant_id: str = "system") -> "Principal":
        return cls(id="system", type="system", tenant_id=tenant_id, roles=frozenset(["system"]))

    @classmethod
    def admin(cls, user_id: str, tenant_id: str) -> "Principal":
        return cls(id=user_id, type="admin", tenant_id=tenant_id, roles=frozenset(["admin"]))

    @classmethod
    def user(cls, user_id: str, tenant_id: str, roles: FrozenSet[str] = frozenset()) -> "Principal":
        return cls(id=user_id, type="user", tenant_id=tenant_id, roles=roles)

    @classmethod
    def service(cls, service_id: str, tenant_id: str) -> "Principal":
        return cls(id=service_id, type="service", tenant_id=tenant_id, roles=frozenset(["service"]))


@dataclass(frozen=True)
class AuthorizationContext:
    """Complete authorization context for an execution."""
    principal: Principal
    capabilities: ExecutionCapabilities
    policy_version: str
    authorized_at: datetime
    authorization_id: str
    reason: str = ""

    @classmethod
    def create(
        cls,
        principal: Principal,
        capabilities: ExecutionCapabilities,
        policy_version: str,
        reason: str = "",
    ) -> "AuthorizationContext":
        return cls(
            principal=principal,
            capabilities=capabilities,
            policy_version=policy_version,
            authorized_at=datetime.now(timezone.utc),
            authorization_id=str(uuid.uuid4()),
            reason=reason,
        )

    @classmethod
    def for_system(cls, policy_version: str = "1.0") -> "AuthorizationContext":
        return cls.create(
            principal=Principal.system(),
            capabilities=ExecutionCapabilities.for_system(),
            policy_version=policy_version,
            reason="Internal system call",
        )

    @classmethod
    def for_admin(cls, user_id: str, tenant_id: str, policy_version: str = "1.0", reason: str = "") -> "AuthorizationContext":
        return cls.create(
            principal=Principal.admin(user_id, tenant_id),
            capabilities=ExecutionCapabilities.for_admin(),
            policy_version=policy_version,
            reason=reason or f"Admin override by {user_id}",
        )

    @classmethod
    def for_user(cls, user_id: str, tenant_id: str, policy_version: str = "1.0") -> "AuthorizationContext":
        return cls.create(
            principal=Principal.user(user_id, tenant_id),
            capabilities=ExecutionCapabilities.for_user(),
            policy_version=policy_version,
            reason="Regular user request",
        )


class AuthorizationPolicy:
    """Evaluates whether a principal can be granted specific capabilities."""

    def __init__(self, policy_version: str = "1.0"):
        self.policy_version = policy_version
        self._capability_rules: Dict[Capability, callable] = {
            Capability.OVERRIDE_SAFETY: self._can_override_safety,
            Capability.OVERRIDE_BUDGET: self._can_override_budget,
            Capability.OVERRIDE_ROUTING: self._can_override_routing,
            Capability.ADMIN_VETO_OVERRIDE: self._can_admin_veto_override,
            Capability.INTERNAL_SYSTEM_CALL: self._can_internal_system_call,
            Capability.CROSS_TENANT_ACCESS: self._can_cross_tenant_access,
            Capability.PRIVILEGED_TOOL_ACCESS: self._can_privileged_tool_access,
            Capability.MEMORY_WRITE: self._can_memory_write,
            Capability.MEMORY_READ_ALL: self._can_memory_read_all,
        }

    def evaluate(self, principal: Principal, requested_capabilities: Set[Capability]) -> ExecutionCapabilities:
        """Evaluate which requested capabilities are granted."""
        granted = set()
        for cap in requested_capabilities:
            rule = self._capability_rules.get(cap)
            if rule and rule(principal):
                granted.add(cap)
        return ExecutionCapabilities(capabilities=frozenset(granted))

    def _can_override_safety(self, principal: Principal) -> bool:
        return principal.type in ("system", "admin") or "safety_override" in principal.permissions

    def _can_override_budget(self, principal: Principal) -> bool:
        return principal.type in ("system", "admin") or "budget_override" in principal.permissions

    def _can_override_routing(self, principal: Principal) -> bool:
        return principal.type in ("system", "admin") or "routing_override" in principal.permissions

    def _can_admin_veto_override(self, principal: Principal) -> bool:
        return principal.type == "admin" or "admin_veto_override" in principal.permissions

    def _can_internal_system_call(self, principal: Principal) -> bool:
        return principal.type == "system"

    def _can_cross_tenant_access(self, principal: Principal) -> bool:
        return principal.type == "admin" or "cross_tenant" in principal.permissions

    def _can_privileged_tool_access(self, principal: Principal) -> bool:
        return principal.type in ("system", "admin") or "privileged_tools" in principal.permissions

    def _can_memory_write(self, principal: Principal) -> bool:
        return principal.type in ("system", "admin", "service") or "memory_write" in principal.permissions

    def _can_memory_read_all(self, principal: Principal) -> bool:
        return principal.type in ("system", "admin") or "memory_read_all" in principal.permissions


# Default policy instance
DEFAULT_AUTH_POLICY = AuthorizationPolicy()

__all__ = [
    "Capability",
    "ExecutionCapabilities",
    "Principal",
    "AuthorizationContext",
    "AuthorizationPolicy",
    "DEFAULT_AUTH_POLICY",
]
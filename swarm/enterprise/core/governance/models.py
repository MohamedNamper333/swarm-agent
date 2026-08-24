"""
Governance Models - Policy, Compliance, and Audit data structures.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def uuidv7() -> str:
    return str(uuid4())


# =============================================================================
# Policy Models
# =============================================================================

class PolicyType(str, Enum):
    """Types of governance policies."""
    ACCESS_CONTROL = "access_control"
    DATA_PROTECTION = "data_protection"
    COST_CONTROL = "cost_control"
    SECURITY = "security"
    COMPLIANCE = "compliance"
    OPERATIONAL = "operational"
    ETHICAL = "ethical"
    CUSTOM = "custom"


class PolicyScope(str, Enum):
    """Scope of policy application."""
    GLOBAL = "global"
    TENANT = "tenant"
    DEPARTMENT = "department"
    AGENT = "agent"
    WORKFLOW = "workflow"
    RESOURCE = "resource"


class PolicyAction(str, Enum):
    """Action when policy is violated."""
    ALLOW = "allow"
    WARN = "warn"
    DENY = "deny"
    ESCALATE = "escalate"
    QUARANTINE = "quarantine"
    QUEUE = "queue"
    AUDIT = "audit"


@dataclass
class PolicyRule:
    """A single policy rule."""
    rule_id: str = field(default_factory=lambda: f"rule-{uuidv7()}")
    name: str = ""
    description: str = ""
    condition: str = ""
    action: PolicyAction = PolicyAction.DENY
    severity: str = "high"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Policy:
    """Governance policy definition."""
    policy_id: str = field(default_factory=lambda: f"pol-{uuidv7()}")
    name: str = ""
    description: str = ""
    policy_type: PolicyType = PolicyType.CUSTOM
    scope: PolicyScope = PolicyScope.GLOBAL
    scope_value: Optional[str] = None
    rules: List[PolicyRule] = field(default_factory=list)
    enabled: bool = True
    priority: int = 100
    tags: Set[str] = field(default_factory=set)
    created_at: datetime = field(default_factory=now_utc)
    updated_at: datetime = field(default_factory=now_utc)
    created_by: str = "system"
    version: int = 1
    
    def matches(self, context: Dict[str, Any]) -> bool:
        if not self.enabled:
            return False
        
        if self.scope == PolicyScope.GLOBAL:
            return True
        elif self.scope == PolicyScope.TENANT:
            return context.get("tenant_id") == self.scope_value
        elif self.scope == PolicyScope.DEPARTMENT:
            return context.get("department") == self.scope_value
        elif self.scope == PolicyScope.AGENT:
            return context.get("agent_type") == self.scope_value
        elif self.scope == PolicyScope.WORKFLOW:
            return context.get("workflow_type") == self.scope_value
        return False


@dataclass
class PolicyEvaluation:
    policy_id: str
    policy_name: str
    matched: bool
    rule_results: List[Dict[str, Any]] = field(default_factory=list)
    final_action: Any = None
    violations: List[str] = field(default_factory=list)
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# =============================================================================
# Compliance Models
# =============================================================================

class ComplianceFramework(str, Enum):
    GDPR = "gdpr"
    SOC2 = "soc2"
    HIPAA = "hipaa"
    PCI_DSS = "pci_dss"
    ISO_27001 = "iso_27001"
    NIST_800_53 = "nist_800_53"
    CUSTOM = "custom"


class ComplianceStatus(str, Enum):
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PARTIAL = "partial"
    NOT_ASSESSED = "not_assessed"
    EXEMPT = "exempt"


@dataclass
class ComplianceControl:
    """A single compliance control."""
    control_id: str = field(default_factory=lambda: f"ctrl-{uuidv7()}")
    framework: Any = None
    title: str = ""
    description: str = ""
    category: str = ""
    requirements: List[str] = field(default_factory=list)
    evidence_required: List[str] = field(default_factory=list)
    automated_check: bool = False
    check_script: Optional[str] = None


@dataclass
class ComplianceCheck:
    """Result of a compliance check."""
    check_id: str = field(default_factory=lambda: f"chk-{uuidv7()}")
    control_id: str = ""
    framework: Any = None
    status: Any = None
    score: float = 0.0
    findings: List[str] = field(default_factory=list)
    evidence: List[str] = field(default_factory=list)
    remediation: Optional[str] = None
    checked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    checked_by: str = "system"
    next_check_due: Optional[datetime] = None


@dataclass
class ComplianceReport:
    report_id: str = field(default_factory=lambda: f"rpt-{uuidv7()}")
    tenant_id: str = ""
    framework: Any = None
    overall_status: Any = None
    overall_score: float = 0.0
    checks: List[Any] = field(default_factory=list)
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    valid_until: Optional[datetime] = None


# =============================================================================
# Audit Models
# =============================================================================

class AuditEventType(str, Enum):
    POLICY_CREATED = "policy_created"
    POLICY_UPDATED = "policy_updated"
    POLICY_DELETED = "policy_deleted"
    POLICY_EVALUATED = "policy_evaluated"
    POLICY_VIOLATED = "policy_violated"
    COMPLIANCE_CHECKED = "compliance_checked"
    COMPLIANCE_VIOLATION = "compliance_violation"
    ACCESS_GRANTED = "access_granted"
    ACCESS_DENIED = "access_denied"
    DATA_ACCESSED = "data_accessed"
    DATA_MODIFIED = "data_modified"
    DATA_EXPORTED = "data_exported"
    CONFIG_CHANGED = "config_changed"
    USER_ACTION = "user_action"
    SYSTEM_EVENT = "system_event"
    SECURITY_INCIDENT = "security_incident"


class AuditSeverity(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    event_id: str = field(default_factory=lambda: f"audit-{uuidv7()}")
    event_type: Any = None
    severity: Any = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    tenant_id: str = "default"
    actor_id: str = "system"
    actor_type: str = "user"
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    action: str = ""
    outcome: str = "success"
    details: Dict[str, Any] = field(default_factory=dict)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    trace_id: Optional[str] = None
    correlation_id: Optional[str] = None
    previous_hash: Optional[str] = None
    event_hash: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value if hasattr(self.event_type, 'value') else str(self.event_type),
            "severity": self.severity.value if hasattr(self.severity, 'value') else str(self.severity),
            "timestamp": self.timestamp.isoformat(),
            "tenant_id": self.tenant_id,
            "actor_id": self.actor_id,
            "actor_type": self.actor_type,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "action": self.action,
            "outcome": self.outcome,
            "details": self.details,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "trace_id": self.trace_id,
            "correlation_id": self.correlation_id,
            "previous_hash": self.previous_hash,
            "event_hash": self.event_hash,
        }


# =============================================================================
# Risk Models
# =============================================================================

class RiskLevel(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NEGLIGIBLE = "negligible"


@dataclass
class Risk:
    risk_id: str = field(default_factory=lambda: f"risk-{uuidv7()}")
    title: str = ""
    description: str = ""
    category: str = ""
    level: Any = None
    likelihood: float = 0.5
    impact: float = 0.5
    mitigation: Optional[str] = None
    owner: Optional[str] = None
    status: str = "open"
    identified_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    mitigated_at: Optional[datetime] = None
    tags: Set[str] = field(default_factory=set)
    
    @property
    def risk_score(self) -> float:
        return self.likelihood * self.impact

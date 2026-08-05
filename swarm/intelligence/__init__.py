"""
Swarm Intelligence - Collective Intelligence Module
Agents learn and improve each other.
"""

from .self_reflection import SelfReflectionEngine, ReflectionEntry, ReflectionDepth, ReflectionTrigger
from .cross_review import (
    CrossReviewEngine,
    ReviewRequest,
    ReviewVerdictResult,
    ReviewFinding,
    ReviewCriteria,
    ReviewType,
    ReviewStatus,
    ReviewVerdict
)
from .learning_tracker import LearningTracker, AgentLearningProfile, MetricSnapshot, MetricType, TrendDirection
from .skill_discovery import (
    SkillDiscoveryEngine,
    SkillMetadata,
    SkillMatch,
    DiscoveryStats,
    SkillCategory,
    MatchStrength,
    get_discovery_engine
)
from .context_manager import (
    HierarchicalContextManager,
    ContextEntry,
    ContextSnapshot,
    ContextScope,
    ContextPriority,
    get_context_manager
)
from .context_compactor import (
    ContextCompactor,
    CompactionResult,
    CompactionStats,
    CompactionStrategy,
    get_context_compactor
)
from .constitutional_guard import (
    ConstitutionalGuard,
    PrincipleDefinition,
    Violation,
    CheckResult,
    Principle,
    Severity,
    CheckStatus,
    get_constitutional_guard
)
from .constitutional_audit import (
    ConstitutionalAudit,
    AuditEntry,
    AgentComplianceReport,
    SystemComplianceDashboard,
    AuditEventType,
    ComplianceLevel,
    get_constitutional_audit
)

__all__ = [
    # Week 6: Self-Reflection + Cross-Review
    "SelfReflectionEngine",
    "ReflectionEntry",
    "ReflectionDepth",
    "ReflectionTrigger",
    "CrossReviewEngine",
    "ReviewRequest",
    "ReviewVerdictResult",
    "ReviewFinding",
    "ReviewCriteria",
    "ReviewType",
    "ReviewStatus",
    "ReviewVerdict",
    # Week 7: Skill Discovery + Learning
    "LearningTracker",
    "AgentLearningProfile",
    "MetricSnapshot",
    "MetricType",
    "TrendDirection",
    "SkillDiscoveryEngine",
    "SkillMetadata",
    "SkillMatch",
    "DiscoveryStats",
    "SkillCategory",
    "MatchStrength",
    "get_discovery_engine",
    # Week 8: Context Management + Compaction
    "HierarchicalContextManager",
    "ContextEntry",
    "ContextSnapshot",
    "ContextScope",
    "ContextPriority",
    "get_context_manager",
    "ContextCompactor",
    "CompactionResult",
    "CompactionStats",
    "CompactionStrategy",
    "get_context_compactor",
    # Week 9: Constitutional AI Enforcement
    "ConstitutionalGuard",
    "PrincipleDefinition",
    "Violation",
    "CheckResult",
    "Principle",
    "Severity",
    "CheckStatus",
    "get_constitutional_guard",
    "ConstitutionalAudit",
    "AuditEntry",
    "AgentComplianceReport",
    "SystemComplianceDashboard",
    "AuditEventType",
    "ComplianceLevel",
    "get_constitutional_audit",
]

__version__ = "3.0.0"
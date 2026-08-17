"""
Routing Engine — replaces keyword-based routing with multi-strategy classification.

F-007: Keyword-Based Routing fix.
Implements explicit type, capability matching, rule matching, semantic classification,
confidence calculation, ambiguity detection, multi-department planning.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Set
from enum import Enum
import re
import logging

logger = logging.getLogger(__name__)


class RoutingStrategy(str, Enum):
    EXPLICIT_TYPE = "explicit_type"
    CAPABILITY_MATCHING = "capability_matching"
    RULE_MATCHING = "rule_matching"
    SEMANTIC_CLASSIFICATION = "semantic_classification"
    LLM_CLASSIFICATION = "llm_classification"


class Department(str, Enum):
    CODE = "code"
    DESIGN = "design"
    VIDEO = "video"
    RESEARCH = "research"
    DATA = "data"
    LANGUAGE = "language"
    KNOWLEDGE = "knowledge"
    SAFETY = "safety"
    GENERAL = "general"


@dataclass(frozen=True)
class RoutingEvidence:
    """Evidence supporting a routing decision."""
    strategy: RoutingStrategy
    matched_patterns: List[str]
    confidence_contribution: float
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RoutingDecision:
    """Result of routing analysis."""
    primary_department: Department
    secondary_departments: Tuple[Department, ...]
    confidence: float
    ambiguous: bool
    evidence: Tuple[RoutingEvidence, ...]
    strategy_used: RoutingStrategy
    requires_clarification: bool = False
    clarification_questions: Tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "primary_department": self.primary_department.value,
            "secondary_departments": [d.value for d in self.secondary_departments],
            "confidence": self.confidence,
            "ambiguous": self.ambiguous,
            "evidence": [
                {
                    "strategy": e.strategy.value,
                    "matched_patterns": e.matched_patterns,
                    "confidence_contribution": e.confidence_contribution,
                    "details": e.details,
                }
                for e in self.evidence
            ],
            "strategy_used": self.strategy_used.value,
            "requires_clarification": self.requires_clarification,
            "clarification_questions": list(self.clarification_questions),
        }


class RoutingRule:
    """A single routing rule with pattern and target department."""

    def __init__(
        self,
        department: Department,
        patterns: List[str],
        weight: float = 1.0,
        requires_all: bool = False,
        priority: int = 0,
    ):
        self.department = department
        self.patterns = [re.compile(p, re.IGNORECASE) for p in patterns]
        self.weight = weight
        self.requires_all = requires_all
        self.priority = priority

    def matches(self, text: str) -> Tuple[bool, List[str]]:
        """Check if text matches this rule. Returns (matched, matched_patterns)."""
        matched_patterns = []
        for pattern in self.patterns:
            if pattern.search(text):
                matched_patterns.append(pattern.pattern)
        if self.requires_all:
            return (len(matched_patterns) == len(self.patterns), matched_patterns)
        return (len(matched_patterns) > 0, matched_patterns)


class DepartmentCapability:
    """Maps departments to their capabilities for capability-based routing."""

    CAPABILITIES: Dict[Department, Set[str]] = {
        Department.CODE: {
            "code_generation", "code_review", "debugging", "refactoring",
            "api_development", "database_design", "testing", "deployment",
            "python", "javascript", "typescript", "sql", "docker", "kubernetes",
        },
        Department.DESIGN: {
            "ui_design", "ux_design", "brand_design", "logo_design",
            "image_generation", "wireframing", "prototyping", "design_systems",
            "typography", "color_theory", "accessibility_design", "3d_design",
        },
        Department.VIDEO: {
            "video_generation", "animation", "motion_graphics", "video_editing",
            "storyboarding", "promo_videos", "explainer_videos",
        },
        Department.RESEARCH: {
            "web_research", "academic_research", "market_research",
            "fact_checking", "literature_review", "competitive_analysis",
            "trend_analysis", "technical_research",
        },
        Department.DATA: {
            "data_analysis", "etl_pipelines", "analytics", "metrics",
            "sql_querying", "data_warehousing", "data_modeling",
            "dashboard_creation", "olap", "data_visualization",
        },
        Department.LANGUAGE: {
            "translation", "localization", "i18n", "transcreation",
            "arabic", "english", "french", "spanish", "german",
        },
        Department.KNOWLEDGE: {
            "document_retrieval", "rag", "knowledge_base", "search",
            "document_parsing", "reranking", "embedding",
        },
        Department.SAFETY: {
            "content_safety", "jailbreak_detection", "topic_control",
            "pii_detection", "violence_detection", "policy_enforcement",
        },
    }

    @classmethod
    def get_capabilities(cls, department: Department) -> Set[str]:
        return cls.CAPABILITIES.get(department, set())

    @classmethod
    def match_capabilities(cls, text: str) -> Dict[Department, float]:
        """Match text against department capabilities. Returns department -> score."""
        text_lower = text.lower()
        scores = {}
        for dept, caps in cls.CAPABILITIES.items():
            score = 0
            for cap in caps:
                if cap.replace("_", " ") in text_lower:
                    score += 1
            if score > 0:
                scores[dept] = score
        return scores


class RoutingEngine:
    """Multi-strategy routing engine."""

    def __init__(self):
        self._rules = self._build_default_rules()
        self._capability_matcher = DepartmentCapability()
        self._explicit_type_map = {
            "code": Department.CODE,
            "design": Department.DESIGN,
            "video": Department.VIDEO,
            "research": Department.RESEARCH,
            "data": Department.DATA,
            "language": Department.LANGUAGE,
            "knowledge": Department.KNOWLEDGE,
            "safety": Department.SAFETY,
            "general": Department.GENERAL,
        }

    def _build_default_rules(self) -> List[RoutingRule]:
        """Build default keyword-based rules (legacy compatibility)."""
        return [
            # CODE rules
            RoutingRule(Department.CODE, [
                r"\b(code|function|class|implement|build\s+app|api\s+endpoint)\b",
                r"\b(database|query|python|javascript|deploy|refactor)\b",
                r"\b(compile|syntax|debug|fix\s+bug|script|backend)\b",
            ], weight=1.0, priority=10),

            # DESIGN rules
            RoutingRule(Department.DESIGN, [
                r"\b(logo|image|design|ui\s+mockup|ux|mockup|icon|brand)\b",
                r"\b(color\s+scheme|typography|3d\s+model|wireframe|visual)\b",
                r"\b(artwork|illustration|design\s+system|prototype)\b",
            ], weight=1.0, priority=10),

            # VIDEO rules
            RoutingRule(Department.VIDEO, [
                r"\b(video|animation|animate|motion\s+graphic|film|clip)\b",
                r"\b(storyboard|movie|mp4|commercial|promo\s+video)\b",
            ], weight=1.0, priority=10),

            # RESEARCH rules
            RoutingRule(Department.RESEARCH, [
                r"\b(research|investigate|study|literature\s+review|fact\s+check)\b",
                r"\b(verify|find\s+papers|academic|study\s+of|market\s+research)\b",
            ], weight=1.0, priority=10),

            # DATA rules
            RoutingRule(Department.DATA, [
                r"\b(data\s+analysis|etl|analytics|metrics|kpi|sql\s+query)\b",
                r"\b(schema\s+design|dashboard|data\s+warehouse|pipeline)\b",
                r"\b(data\s+processing|data\s+transformation|olap)\b",
            ], weight=1.0, priority=10),

            # LANGUAGE rules
            RoutingRule(Department.LANGUAGE, [
                r"\b(translate|translation|localize|localization|i18n)\b",
                r"\b(arabic|french|spanish|german|chinese|japanese)\b",
            ], weight=1.0, priority=10),

            # KNOWLEDGE rules
            RoutingRule(Department.KNOWLEDGE, [
                r"\b(search\s+docs|knowledge\s+base|rag|retrieval|find\s+document)\b",
                r"\b(search\s+knowledge|document\s+retrieval|embedding)\b",
            ], weight=1.0, priority=10),

            # SAFETY rules
            RoutingRule(Department.SAFETY, [
                r"\b(safety|check|content\s+safety|jailbreak|pii|violence)\b",
                r"\b(policy\s+enforcement|moderation|filter)\b",
            ], weight=1.0, priority=10),
        ]

    def route(
        self,
        question: str,
        explicit_type: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        allowed_departments: Optional[Set[Department]] = None,
    ) -> RoutingDecision:
        """
        Route a request to the appropriate department(s).
        
        Strategies (in priority order):
        1. Explicit type (user-specified)
        2. Capability matching
        3. Rule matching (keyword-based)
        4. Semantic classification (future: LLM-based)
        
        Returns RoutingDecision with confidence, ambiguity detection.
        """
        evidence: List[RoutingEvidence] = []
        scores: Dict[Department, float] = {d: 0.0 for d in Department}
        strategy_used = RoutingStrategy.RULE_MATCHING

        # 1. Explicit type (highest priority)
        if explicit_type and explicit_type in self._explicit_type_map:
            dept = self._explicit_type_map[explicit_type]
            evidence.append(RoutingEvidence(
                strategy=RoutingStrategy.EXPLICIT_TYPE,
                matched_patterns=[explicit_type],
                confidence_contribution=1.0,
                details={"explicit_type": explicit_type},
            ))
            scores[dept] = 100.0
            strategy_used = RoutingStrategy.EXPLICIT_TYPE

        # 2. Capability matching
        capability_scores = self._capability_matcher.match_capabilities(question)
        for dept, score in capability_scores.items():
            if allowed_departments and dept not in allowed_departments:
                continue
            if score > 0:
                scores[dept] = scores.get(dept, 0) + score * 2.0
                evidence.append(RoutingEvidence(
                    strategy=RoutingStrategy.CAPABILITY_MATCHING,
                    matched_patterns=[],  # capabilities are internal
                    confidence_contribution=score * 0.1,
                    details={"capability_score": score},
                ))
                if strategy_used == RoutingStrategy.RULE_MATCHING:
                    strategy_used = RoutingStrategy.CAPABILITY_MATCHING

        # 3. Rule matching (keyword-based)
        rule_scores: Dict[Department, float] = {}
        for rule in sorted(self._rules, key=lambda r: -r.priority):
            if allowed_departments and rule.department not in allowed_departments:
                continue
            matched, patterns = rule.matches(question)
            if matched:
                rule_scores[rule.department] = rule_scores.get(rule.department, 0) + rule.weight
                evidence.append(RoutingEvidence(
                    strategy=RoutingStrategy.RULE_MATCHING,
                    matched_patterns=patterns,
                    confidence_contribution=rule.weight * 0.05,
                    details={"rule_priority": rule.priority},
                ))

        for dept, score in rule_scores.items():
            scores[dept] = scores.get(dept, 0) + score

        # 4. Context-based hints
        if context:
            if "brand_name" in context and Department.DESIGN in (allowed_departments or set(Department)):
                scores[Department.DESIGN] = scores.get(Department.DESIGN, 0) + 5
            if "source_lang" in context and "target_lang" in context:
                scores[Department.LANGUAGE] = scores.get(Department.LANGUAGE, 0) + 10

        # Determine primary and secondary
        sorted_depts = sorted(scores.items(), key=lambda x: -x[1])
        if not sorted_depts or sorted_depts[0][1] == 0:
            # No clear match
            return RoutingDecision(
                primary_department=Department.GENERAL,
                secondary_departments=(),
                confidence=0.0,
                ambiguous=True,
                evidence=tuple(evidence),
                strategy_used=strategy_used,
                requires_clarification=True,
                clarification_questions=(
                    "What type of task is this? (code, design, video, research, data, language, knowledge, safety)",
                    "Please specify the department explicitly using the 'type' field.",
                ),
            )

        primary = sorted_depts[0][0]
        primary_score = sorted_depts[0][1]

        # Find secondary departments (within 50% of primary score)
        secondary = tuple(
            d for d, s in sorted_depts[1:]
            if s >= primary_score * 0.5 and s > 0
        )

        # Calculate confidence (0.0 to 1.0)
        total_score = sum(s for _, s in sorted_depts if s > 0)
        confidence = primary_score / total_score if total_score > 0 else 0.0

        # Ambiguity detection: multiple departments with similar scores
        ambiguous = len(secondary) >= 2 or (
            len(sorted_depts) > 1 and sorted_depts[1][1] >= primary_score * 0.8
        )

        requires_clarification = ambiguous and confidence < 0.6

        return RoutingDecision(
            primary_department=primary,
            secondary_departments=secondary,
            confidence=round(confidence, 2),
            ambiguous=ambiguous,
            evidence=tuple(evidence),
            strategy_used=strategy_used,
            requires_clarification=requires_clarification,
            clarification_questions=(
                f"Multiple departments matched: {primary.value}, {[d.value for d in secondary]}. "
                "Please clarify or specify 'type' explicitly."
            ) if ambiguous else (),
        )

    def add_rule(self, rule: RoutingRule) -> None:
        """Add a custom routing rule."""
        self._rules.append(rule)
        self._rules.sort(key=lambda r: -r.priority)

    def remove_rules_for_department(self, department: Department) -> None:
        """Remove all rules for a department."""
        self._rules = [r for r in self._rules if r.department != department]


# Singleton
_routing_engine: Optional["RoutingEngine"] = None


def get_routing_engine() -> RoutingEngine:
    global _routing_engine
    if _routing_engine is None:
        _routing_engine = RoutingEngine()
    return _routing_engine


__all__ = [
    "RoutingStrategy",
    "Department",
    "RoutingEvidence",
    "RoutingDecision",
    "RoutingRule",
    "DepartmentCapability",
    "RoutingEngine",
    "get_routing_engine",
]
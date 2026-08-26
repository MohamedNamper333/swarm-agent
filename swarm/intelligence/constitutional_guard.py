"""
Constitutional Guard Module - Enforce 5 Constitutional Principles
Dynamically verifies artifacts against HONESTY, EVIDENCE, MINIMAL,
REVERSIBILITY, and HUMAN_AGENCY principles before delivery.
"""
import json
import time
import logging
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import defaultdict
import threading
import uuid

logger = logging.getLogger(__name__)


class Principle(Enum):
    """The 5 constitutional principles"""
    HONESTY = "HONESTY_OVER_HELPFULNESS"
    EVIDENCE = "EVIDENCE_OVER_AUTHORITY"
    MINIMAL = "MINIMAL_SURFACE_AREA"
    REVERSIBILITY = "REVERSIBILITY_BY_DEFAULT"
    HUMAN_AGENCY = "HUMAN_AGENCY_PRESERVATION"


class Severity(Enum):
    """Severity of a violation"""
    INFO = "info"               # Just informational
    WARNING = "warning"         # Should be noted
    CRITICAL = "critical"       # Must be fixed before proceeding
    BLOCKING = "blocking"       # Hard block, requires human review


class CheckStatus(Enum):
    """Result of a constitutional check"""
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    BLOCKED = "blocked"


@dataclass
class PrincipleDefinition:
    """Definition of a constitutional principle"""
    principle: Principle
    name: str
    description: str
    severity: Severity
    check_patterns: List[str]
    positive_indicators: List[str]
    negative_indicators: List[str]


@dataclass
class Violation:
    """A single constitutional violation"""
    id: str
    principle: Principle
    severity: Severity
    artifact_id: str
    agent_id: str
    evidence: str
    matched_pattern: str
    recommendation: str
    timestamp: str
    resolved: bool = False
    resolution_note: Optional[str] = None


@dataclass
class CheckResult:
    """Result of checking an artifact against the constitution"""
    artifact_id: str
    agent_id: str
    status: CheckStatus
    violations: List[Violation]
    passed_principles: List[Principle]
    failed_principles: List[Principle]
    requires_human_review: bool
    timestamp: str
    artifact_type: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class ConstitutionalGuard:
    """
    Enforces the 5 constitutional principles dynamically.
    All artifacts must pass before being delivered to users.
    """

    PRINCIPLES = {
        Principle.HONESTY: PrincipleDefinition(
            principle=Principle.HONESTY,
            name="Honesty Over Helpfulness",
            description="No fabricated results, honest failures, no deception",
            severity=Severity.BLOCKING,
            check_patterns=[
                r"\b(?:always|never)\s+(?:works?|will work|succeeds?|true|correct)",
                r"(?:i (?:can|will) (?:definitely|certainly) .+?)(?:\.|$)",
                r"100%\s+(?:success|certain|guaranteed)",
                r"no (?:issues|problems|bugs|errors)\b",
                r"\bperfect (?:solution|code|implementation)\b",
                r"\b(?:definitely|guaranteed|certainly)\s+(?:works?|true|correct)",
                r"\bwill definitely\b"
            ],
            positive_indicators=[
                "i don't know", "not certain", "approximately",
                "estimated", "needs verification", "may not work",
                "honest failure", "i cannot", "let me verify"
            ],
            negative_indicators=[
                "definitely works", "guaranteed success", "perfect solution",
                "no issues", "100% certain"
            ]
        ),
        Principle.EVIDENCE: PrincipleDefinition(
            principle=Principle.EVIDENCE,
            name="Evidence Over Authority",
            description="Every claim has source, every decision has trace",
            severity=Severity.CRITICAL,
            check_patterns=[
                r"\btrust me\b",
                r"\bbecause i said\b",
                r"\bobviously\b.*\btrue\b",
                r"\bclearly\b.*\btrue\b",
                r"without (?:any )?(?:source|evidence|proof|citation)"
            ],
            positive_indicators=[
                "according to", "based on", "source:", "reference:",
                "see:", "evidence:", "doc:", "spec:", "as documented",
                "tested:", "verified:", "cited from"
            ],
            negative_indicators=[
                "trust me", "because i said", "obviously", "clearly true",
                "without source"
            ]
        ),
        Principle.MINIMAL: PrincipleDefinition(
            principle=Principle.MINIMAL,
            name="Minimal Surface Area",
            description="Less code, less dependencies, less complexity",
            severity=Severity.WARNING,
            check_patterns=[
                r"\bjust in case\b",
                r"\bmaybe we need\b",
                r"\bfor future use\b",
                r"\b(?:TODO|FIXME|placeholder)\b",
                r"\bnot implemented yet\b",
                r"\bcoming soon\b",
                r"\b(?:comprehensive|full-featured|enterprise-grade)\b"
            ],
            positive_indicators=[
                "minimal", "simple", "remove", "delete unused",
                "no dependencies", "yagni", "essential only",
                "stripped down", "bare minimum"
            ],
            negative_indicators=[
                "just in case", "future use", "comprehensive", "full-featured",
                "enterprise-grade"
            ]
        ),
        Principle.REVERSIBILITY: PrincipleDefinition(
            principle=Principle.REVERSIBILITY,
            name="Reversibility By Default",
            description="Every change is reversible, rollback plan first",
            severity=Severity.CRITICAL,
            check_patterns=[
                r"\bcannot be undone\b",
                r"\birreversible\b",
                r"\bpermanent(?:ly)?\b.*\b(?:delete|change|update)\b",
                r"\bdestructive\b.*\b(?:operation|delete)\b",
                r"\bwipe all data\b",
                r"\bforce push\b"
            ],
            positive_indicators=[
                "rollback plan", "migration script", "backup before",
                "reversible", "undo", "can be reverted",
                "atomic change", "transactional"
            ],
            negative_indicators=[
                "irreversible", "permanent deletion", "no rollback",
                "destructive operation", "wipe all data"
            ]
        ),
        Principle.HUMAN_AGENCY: PrincipleDefinition(
            principle=Principle.HUMAN_AGENCY,
            name="Human Agency Preservation",
            description="Swarm suggests, human decides - no irreversible silent decisions",
            severity=Severity.BLOCKING,
            check_patterns=[
                r"\bautomatically\s+(?:delete|destroy|wipe|purge)\b",
                r"\bwithout (?:confirmation|approval|consent|asking)\b",
                r"\b(?:silently|secretly|quietly)\s+(?:delete|destroy|modify)\b",
                r"\bforce\s+(?:user|human)\s+to\b"
            ],
            positive_indicators=[
                "ask user", "requires approval", "human decides",
                "user confirmation", "needs review", "stop and ask",
                "interview-me", "escalate to human", "user choice"
            ],
            negative_indicators=[
                "automatically delete", "without confirmation",
                "silently modify", "force user", "skip human approval"
            ]
        )
    }

    def __init__(self, storage_path: str = "swarm/constitutional"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

        self.violations: Dict[str, Violation] = {}
        self.check_history: List[CheckResult] = []

        self.total_checks = 0
        self.total_violations = 0
        self.violations_by_principle: Dict[Principle, int] = defaultdict(int)

        self._load_state()

    def _load_state(self) -> None:
        """Load violations from disk"""
        state_file = self.storage_path / "violations.json"
        if state_file.exists():
            try:
                with open(state_file, "r") as f:
                    data = json.load(f)
                for v_id, v_data in data.get("violations", {}).items():
                    v_data["principle"] = Principle(v_data["principle"])
                    v_data["severity"] = Severity(v_data["severity"])
                    violation = Violation(**v_data)
                    self.violations[v_id] = violation
                self.total_violations = data.get("total_violations", 0)
                for p_name, count in data.get("by_principle", {}).items():
                    self.violations_by_principle[Principle(p_name)] = count
            except Exception as e:
                logger.error(f"Failed to load violations: {e}")

    def _save_state(self) -> None:
        """Save violations to disk"""
        state_file = self.storage_path / "violations.json"
        try:
            data = {
                "violations": {},
                "total_violations": self.total_violations,
                "by_principle": {
                    p.value: c for p, c in self.violations_by_principle.items()
                }
            }
            for v_id, v in self.violations.items():
                v_dict = asdict(v)
                v_dict["principle"] = v.principle.value
                v_dict["severity"] = v.severity.value
                data["violations"][v_id] = v_dict
            with open(state_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save violations: {e}")

    def check_artifact(
        self,
        artifact_id: str,
        artifact_content: Any,
        agent_id: str = "unknown",
        artifact_type: str = "text",
        metadata: Optional[Dict] = None
    ) -> CheckResult:
        """
        Check an artifact against all 5 constitutional principles.
        Returns CheckResult with violations list and overall status.
        """
        with self._lock:
            self.total_checks += 1
            violations: List[Violation] = []
            passed: List[Principle] = []
            failed: List[Principle] = []

            for principle, definition in self.PRINCIPLES.items():
                principle_violations = self._check_principle(
                    principle, definition,
                    artifact_id, artifact_content, agent_id
                )

                if principle_violations:
                    failed.append(principle)
                    violations.extend(principle_violations)
                else:
                    passed.append(principle)

            # Determine overall status
            has_blocking = any(v.severity == Severity.BLOCKING for v in violations)
            has_critical = any(v.severity == Severity.CRITICAL for v in violations)

            if has_blocking:
                status = CheckStatus.BLOCKED
            elif has_critical:
                status = CheckStatus.FAIL
            elif violations:
                status = CheckStatus.WARN
            else:
                status = CheckStatus.PASS

            requires_human = status in (CheckStatus.BLOCKED, CheckStatus.FAIL)

            result = CheckResult(
                artifact_id=artifact_id,
                agent_id=agent_id,
                status=status,
                violations=violations,
                passed_principles=passed,
                failed_principles=failed,
                requires_human_review=requires_human,
                timestamp=datetime.now().isoformat(),
                artifact_type=artifact_type,
                metadata=metadata or {}
            )

            # Record violations
            for v in violations:
                self.violations[v.id] = v
                self.violations_by_principle[v.principle] += 1
                self.total_violations += 1

            self.check_history.append(result)


            if len(self.check_history) > 5000:


                del self.check_history[:-5000]
            self._save_state()

            if status in (CheckStatus.BLOCKED, CheckStatus.FAIL):
                logger.warning(
                    f"Artifact {artifact_id} FAILED constitutional check "
                    f"({len(violations)} violations)"
                )

            return result

    def _check_principle(
        self,
        principle: Principle,
        definition: PrincipleDefinition,
        artifact_id: str,
        artifact_content: Any,
        agent_id: str
    ) -> List[Violation]:
        """Check a single principle against artifact content"""
        violations = []
        text_content = self._extract_text(artifact_content)

        if not text_content:
            return violations

        # Check for negative patterns
        for pattern in definition.check_patterns:
            matches = re.finditer(pattern, text_content, re.IGNORECASE)
            for match in matches:
                # Skip if a positive indicator also matches
                if self._has_positive_indicator(
                    text_content, match.start(), match.end()
                ):
                    continue

                violation = Violation(
                    id=f"vio-{uuid.uuid4().hex[:12]}",
                    principle=principle,
                    severity=definition.severity,
                    artifact_id=artifact_id,
                    agent_id=agent_id,
                    evidence=match.group(0)[:200],
                    matched_pattern=pattern,
                    recommendation=self._get_recommendation(principle),
                    timestamp=datetime.now().isoformat()
                )
                violations.append(violation)

        # Check for absence of positive indicators (when context demands them)
        if principle == Principle.EVIDENCE and self._needs_citations(text_content):
            has_evidence = any(
                re.search(p, text_content, re.IGNORECASE)
                for p in definition.positive_indicators
            )
            if not has_evidence:
                violation = Violation(
                    id=f"vio-{uuid.uuid4().hex[:12]}",
                    principle=principle,
                    severity=Severity.WARNING,
                    artifact_id=artifact_id,
                    agent_id=agent_id,
                    evidence="Missing source/citation for claims",
                    matched_pattern="missing_evidence",
                    recommendation="Add source references or 'based on ...' attributions",
                    timestamp=datetime.now().isoformat()
                )
                violations.append(violation)

        return violations

    def _extract_text(self, content: Any) -> str:
        """Extract text from various content types"""
        if isinstance(content, str):
            return content
        elif isinstance(content, dict):
            return json.dumps(content, default=str)
        elif isinstance(content, list):
            return "\n".join(str(item) for item in content)
        else:
            return str(content)

    def _has_positive_indicator(
        self, text: str, start: int, end: int
    ) -> bool:
        """Check if a positive indicator is near the match"""
        # Look at surrounding context (100 chars)
        context_start = max(0, start - 100)
        context_end = min(len(text), end + 100)
        context = text[context_start:context_end]

        positive_patterns = [
            r"however", r"but", r"actually", r"approximately",
            r"based on", r"according to", r"source:", r"reference:",
            r"see:", r"i'm not (?:sure|certain)", r"may not",
            r"needs verification", r"let me check", r"i don't know"
        ]
        return any(re.search(p, context, re.IGNORECASE) for p in positive_patterns)

    def _needs_citations(self, text: str) -> bool:
        """Determine if the text needs citations"""
        # Long technical content with claims usually needs citations
        if len(text) < 100:
            return False

        # Contains claims/assertions
        claim_patterns = [
            r"studies show", r"research indicates", r"experts say",
            r"according to", r"\d+% of", r"most .+ are",
            r"the best", r"the worst", r"always works", r"never works"
        ]
        return any(re.search(p, text, re.IGNORECASE) for p in claim_patterns)

    def _get_recommendation(self, principle: Principle) -> str:
        """Get remediation recommendation for a principle violation"""
        recommendations = {
            Principle.HONESTY: (
                "Replace absolute claims with honest uncertainty. "
                "Use 'I don't know', 'estimated', or 'needs verification'."
            ),
            Principle.EVIDENCE: (
                "Add source citations. Every claim must trace back to "
                "documentation, test, or verified source."
            ),
            Principle.MINIMAL: (
                "Remove unused code, dependencies, features. "
                "Justify every addition or remove it (YAGNI)."
            ),
            Principle.REVERSIBILITY: (
                "Add a rollback plan. Make changes atomic and transactional. "
                "Backup before destructive operations."
            ),
            Principle.HUMAN_AGENCY: (
                "STOP and ask the user. Do not make irreversible decisions "
                "silently. Escalate to human review."
            )
        }
        return recommendations.get(principle, "Review and remediate.")

    def resolve_violation(
        self, violation_id: str, resolution_note: str
    ) -> bool:
        """Mark a violation as resolved"""
        with self._lock:
            if violation_id not in self.violations:
                return False
            v = self.violations[violation_id]
            v.resolved = True
            v.resolution_note = resolution_note
            self._save_state()
            return True

    def get_violations(
        self,
        principle: Optional[Principle] = None,
        resolved: Optional[bool] = None,
        agent_id: Optional[str] = None
    ) -> List[Violation]:
        """Get violations filtered by criteria"""
        with self._lock:
            results = []
            for v in self.violations.values():
                if principle and v.principle != principle:
                    continue
                if resolved is not None and v.resolved != resolved:
                    continue
                if agent_id and v.agent_id != agent_id:
                    continue
                results.append(v)
            return results

    def get_check_history(
        self, limit: int = 50, status: Optional[CheckStatus] = None
    ) -> List[CheckResult]:
        """Get recent check history"""
        with self._lock:
            history = self.check_history[-limit:]
            if status:
                history = [h for h in history if h.status == status]
            return history

    def get_stats(self) -> Dict[str, Any]:
        """Get constitutional guard statistics"""
        with self._lock:
            return {
                "total_checks": self.total_checks,
                "total_violations": self.total_violations,
                "violations_by_principle": {
                    p.value: c for p, c in self.violations_by_principle.items()
                },
                "unresolved_violations": sum(
                    1 for v in self.violations.values() if not v.resolved
                ),
                "checks_by_status": {
                    status.value: sum(
                        1 for h in self.check_history if h.status == status
                    )
                    for status in CheckStatus
                }
            }

    def export_report(self) -> Dict[str, Any]:
        """Export full report for audit"""
        with self._lock:
            return {
                "stats": self.get_stats(),
                "violations": [
                    {
                        **asdict(v),
                        "principle": v.principle.value,
                        "severity": v.severity.value
                    }
                    for v in self.violations.values()
                ],
                "recent_checks": [
                    {
                        "artifact_id": h.artifact_id,
                        "agent_id": h.agent_id,
                        "status": h.status.value,
                        "violation_count": len(h.violations),
                        "timestamp": h.timestamp
                    }
                    for h in self.check_history[-50:]
                ]
            }


# Module-level singleton
_default_guard: Optional[ConstitutionalGuard] = None


def get_constitutional_guard() -> ConstitutionalGuard:
    """Get or create the default constitutional guard"""
    global _default_guard
    if _default_guard is None:
        _default_guard = ConstitutionalGuard()
    return _default_guard
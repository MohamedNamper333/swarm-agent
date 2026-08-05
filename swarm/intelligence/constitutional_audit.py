"""
Constitutional Audit Module - Audit Log and Dashboard
Maintains immutable audit trail of all constitutional checks
and provides dashboards for compliance monitoring.
"""
import json
import time
import logging
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import defaultdict
import threading
import uuid

from swarm.intelligence.constitutional_guard import (
    ConstitutionalGuard,
    CheckResult,
    Violation,
    Principle,
    Severity,
    CheckStatus,
    get_constitutional_guard
)

logger = logging.getLogger(__name__)


class AuditEventType(Enum):
    """Types of audit events"""
    CHECK_PERFORMED = "check_performed"
    VIOLATION_DETECTED = "violation_detected"
    VIOLATION_RESOLVED = "violation_resolved"
    PRINCIPLE_UPDATED = "principle_updated"
    AGENT_REVIEWED = "agent_reviewed"
    PERIODIC_REVIEW = "periodic_review"


class ComplianceLevel(Enum):
    """Overall compliance level for an agent or system"""
    EXCELLENT = "excellent"      # >95% pass rate
    GOOD = "good"               # 85-95%
    NEEDS_IMPROVEMENT = "needs_improvement"  # 70-85%
    POOR = "poor"               # <70%


@dataclass
class AuditEntry:
    """Single immutable audit entry"""
    id: str
    event_type: AuditEventType
    timestamp: str
    artifact_id: Optional[str]
    agent_id: str
    principle: Optional[Principle]
    severity: Optional[Severity]
    description: str
    evidence_hash: str  # hash of evidence for integrity
    previous_hash: Optional[str]  # chain integrity
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentComplianceReport:
    """Compliance report for a specific agent"""
    agent_id: str
    total_checks: int
    passed_checks: int
    failed_checks: int
    blocked_checks: int
    warning_checks: int
    pass_rate: float
    compliance_level: ComplianceLevel
    violations_by_principle: Dict[Principle, int]
    top_violation_patterns: List[str]
    recommendations: List[str]
    period_start: str
    period_end: str


@dataclass
class SystemComplianceDashboard:
    """System-wide compliance dashboard"""
    timestamp: str
    total_checks: int
    overall_pass_rate: float
    system_compliance_level: ComplianceLevel
    agents_count: int
    principle_violations: Dict[Principle, int]
    severity_breakdown: Dict[Severity, int]
    recent_critical_violations: List[Dict[str, Any]]
    top_offending_agents: List[Dict[str, Any]]
    trend: Dict[str, float]  # pass rate over time


class ConstitutionalAudit:
    """
    Maintains immutable audit log and generates compliance reports
    and dashboards for the constitutional system.
    """

    def __init__(
        self,
        constitutional_guard: Optional[ConstitutionalGuard] = None,
        storage_path: str = "swarm/constitutional/audit"
    ):
        self.guard = constitutional_guard or get_constitutional_guard()
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

        # Audit log (append-only, hash-chained)
        self.audit_log: List[AuditEntry] = []
        self.last_hash: Optional[str] = None

        # Cached compliance data
        self.agent_reports: Dict[str, AgentComplianceReport] = {}

        self._load_audit_log()
        self._register_with_guard()

    def _register_with_guard(self) -> None:
        """Register hooks to capture guard events"""
        # Patch the guard's check_artifact to also create audit entries
        original_check = self.guard.check_artifact

        def wrapped_check(*args, **kwargs):
            result = original_check(*args, **kwargs)
            self._audit_check(result)
            return result

        self.guard.check_artifact = wrapped_check

    def _audit_check(self, result: CheckResult) -> None:
        """Create audit entry for a check result"""
        with self._lock:
            entry = AuditEntry(
                id=f"audit-{uuid.uuid4().hex[:12]}",
                event_type=AuditEventType.CHECK_PERFORMED,
                timestamp=result.timestamp,
                artifact_id=result.artifact_id,
                agent_id=result.agent_id,
                principle=None,
                severity=None,
                description=(
                    f"Check {result.status.value} for artifact {result.artifact_id} "
                    f"({len(result.violations)} violations)"
                ),
                evidence_hash=self._hash_evidence(result),
                previous_hash=self.last_hash,
                metadata={
                    "artifact_type": result.artifact_type,
                    "requires_human_review": result.requires_human_review,
                    "passed_principles": [p.value for p in result.passed_principles],
                    "failed_principles": [p.value for p in result.failed_principles]
                }
            )
            self.audit_log.append(entry)
            self.last_hash = entry.evidence_hash

            # Create violation entries
            for v in result.violations:
                self._audit_violation(v)

            # Invalidate cached reports
            self.agent_reports.pop(result.agent_id, None)

            self._save_audit_log()

    def _audit_violation(self, violation: Violation) -> None:
        """Create audit entry for a violation"""
        with self._lock:
            entry = AuditEntry(
                id=f"audit-{uuid.uuid4().hex[:12]}",
                event_type=AuditEventType.VIOLATION_DETECTED,
                timestamp=violation.timestamp,
                artifact_id=violation.artifact_id,
                agent_id=violation.agent_id,
                principle=violation.principle,
                severity=violation.severity,
                description=(
                    f"Violation of {violation.principle.value} ({violation.severity.value})"
                ),
                evidence_hash=self._hash_violation(violation),
                previous_hash=self.last_hash,
                metadata={
                    "matched_pattern": violation.matched_pattern,
                    "recommendation": violation.recommendation,
                    "resolved": violation.resolved
                }
            )
            self.audit_log.append(entry)
            self.last_hash = entry.evidence_hash
            self._save_audit_log()

    def record_violation_resolved(
        self, violation_id: str, resolver_id: str = "system"
    ) -> bool:
        """Record audit entry when a violation is resolved"""
        with self._lock:
            violation = self.guard.violations.get(violation_id)
            if not violation:
                return False

            entry = AuditEntry(
                id=f"audit-{uuid.uuid4().hex[:12]}",
                event_type=AuditEventType.VIOLATION_RESOLVED,
                timestamp=datetime.now().isoformat(),
                artifact_id=violation.artifact_id,
                agent_id=resolver_id,
                principle=violation.principle,
                severity=violation.severity,
                description=f"Violation {violation_id} resolved by {resolver_id}",
                evidence_hash=self._hash_string(f"{violation_id}:{resolver_id}"),
                previous_hash=self.last_hash,
                metadata={"original_violation_id": violation_id}
            )
            self.audit_log.append(entry)
            self.last_hash = entry.evidence_hash
            self._save_audit_log()
            return True

    def generate_agent_report(
        self,
        agent_id: str,
        period_days: int = 30
    ) -> AgentComplianceReport:
        """Generate compliance report for a specific agent"""
        with self._lock:
            cutoff = (
                datetime.now() - timedelta(days=period_days)
            ).isoformat()

            agent_checks = [
                h for h in self.guard.check_history
                if h.agent_id == agent_id and h.timestamp >= cutoff
            ]

            if not agent_checks:
                return AgentComplianceReport(
                    agent_id=agent_id,
                    total_checks=0,
                    passed_checks=0,
                    failed_checks=0,
                    blocked_checks=0,
                    warning_checks=0,
                    pass_rate=0.0,
                    compliance_level=ComplianceLevel.GOOD,
                    violations_by_principle={},
                    top_violation_patterns=[],
                    recommendations=["No recent activity to evaluate"],
                    period_start=cutoff,
                    period_end=datetime.now().isoformat()
                )

            total = len(agent_checks)
            passed = sum(1 for c in agent_checks if c.status == CheckStatus.PASS)
            failed = sum(1 for c in agent_checks if c.status == CheckStatus.FAIL)
            blocked = sum(1 for c in agent_checks if c.status == CheckStatus.BLOCKED)
            warning = sum(1 for c in agent_checks if c.status == CheckStatus.WARN)

            pass_rate = passed / total if total > 0 else 0.0

            if pass_rate >= 0.95:
                level = ComplianceLevel.EXCELLENT
            elif pass_rate >= 0.85:
                level = ComplianceLevel.GOOD
            elif pass_rate >= 0.70:
                level = ComplianceLevel.NEEDS_IMPROVEMENT
            else:
                level = ComplianceLevel.POOR

            # Violations by principle
            violations_by_principle: Dict[Principle, int] = defaultdict(int)
            pattern_counts: Dict[str, int] = defaultdict(int)

            for check in agent_checks:
                for v in check.violations:
                    violations_by_principle[v.principle] += 1
                    pattern_counts[v.matched_pattern] += 1

            top_patterns = sorted(
                pattern_counts.items(), key=lambda x: x[1], reverse=True
            )[:5]
            top_pattern_list = [p for p, _ in top_patterns]

            # Recommendations
            recommendations = self._generate_recommendations(
                violations_by_principle, pass_rate
            )

            report = AgentComplianceReport(
                agent_id=agent_id,
                total_checks=total,
                passed_checks=passed,
                failed_checks=failed,
                blocked_checks=blocked,
                warning_checks=warning,
                pass_rate=pass_rate,
                compliance_level=level,
                violations_by_principle=dict(violations_by_principle),
                top_violation_patterns=top_pattern_list,
                recommendations=recommendations,
                period_start=cutoff,
                period_end=datetime.now().isoformat()
            )

            self.agent_reports[agent_id] = report
            return report

    def generate_system_dashboard(self) -> SystemComplianceDashboard:
        """Generate system-wide compliance dashboard"""
        with self._lock:
            total_checks = len(self.guard.check_history)
            if total_checks == 0:
                return SystemComplianceDashboard(
                    timestamp=datetime.now().isoformat(),
                    total_checks=0,
                    overall_pass_rate=0.0,
                    system_compliance_level=ComplianceLevel.GOOD,
                    agents_count=0,
                    principle_violations={},
                    severity_breakdown={},
                    recent_critical_violations=[],
                    top_offending_agents=[],
                    trend={}
                )

            passed = sum(
                1 for c in self.guard.check_history
                if c.status == CheckStatus.PASS
            )
            pass_rate = passed / total_checks

            if pass_rate >= 0.95:
                level = ComplianceLevel.EXCELLENT
            elif pass_rate >= 0.85:
                level = ComplianceLevel.GOOD
            elif pass_rate >= 0.70:
                level = ComplianceLevel.NEEDS_IMPROVEMENT
            else:
                level = ComplianceLevel.POOR

            # Unique agents
            agents = set(c.agent_id for c in self.guard.check_history)

            # Violations by principle
            principle_violations: Dict[Principle, int] = defaultdict(int)
            severity_breakdown: Dict[Severity, int] = defaultdict(int)

            for check in self.guard.check_history:
                for v in check.violations:
                    principle_violations[v.principle] += 1
                    severity_breakdown[v.severity] += 1

            # Recent critical violations
            recent_critical = sorted(
                [v for v in self.guard.violations.values()
                 if v.severity in (Severity.CRITICAL, Severity.BLOCKING)],
                key=lambda v: v.timestamp,
                reverse=True
            )[:10]

            recent_critical_list = [
                {
                    "id": v.id,
                    "principle": v.principle.value,
                    "severity": v.severity.value,
                    "artifact_id": v.artifact_id,
                    "agent_id": v.agent_id,
                    "evidence": v.evidence[:100],
                    "timestamp": v.timestamp,
                    "resolved": v.resolved
                }
                for v in recent_critical
            ]

            # Top offending agents
            agent_violations: Dict[str, int] = defaultdict(int)
            for check in self.guard.check_history:
                if check.violations:
                    agent_violations[check.agent_id] += len(check.violations)

            top_offenders = sorted(
                agent_violations.items(), key=lambda x: x[1], reverse=True
            )[:5]
            top_offender_list = [
                {"agent_id": aid, "violations": count}
                for aid, count in top_offenders
            ]

            # Trend: pass rate over last 7 days
            trend = self._calculate_trend(days=7)

            return SystemComplianceDashboard(
                timestamp=datetime.now().isoformat(),
                total_checks=total_checks,
                overall_pass_rate=pass_rate,
                system_compliance_level=level,
                agents_count=len(agents),
                principle_violations=dict(principle_violations),
                severity_breakdown=dict(severity_breakdown),
                recent_critical_violations=recent_critical_list,
                top_offending_agents=top_offender_list,
                trend=trend
            )

    def verify_audit_chain(self) -> Tuple[bool, Optional[str]]:
        """Verify the integrity of the audit log hash chain"""
        with self._lock:
            if not self.audit_log:
                return True, None

            previous_hash = None
            for i, entry in enumerate(self.audit_log):
                if entry.previous_hash != previous_hash:
                    return False, f"Chain broken at entry {i}"
                previous_hash = entry.evidence_hash

            return True, None

    def get_audit_log(
        self,
        event_type: Optional[AuditEventType] = None,
        agent_id: Optional[str] = None,
        limit: int = 100
    ) -> List[AuditEntry]:
        """Get audit log entries with filters"""
        with self._lock:
            log = self.audit_log
            if event_type:
                log = [e for e in log if e.event_type == event_type]
            if agent_id:
                log = [e for e in log if e.agent_id == agent_id]
            return log[-limit:]

    def export_full_audit(self) -> Dict[str, Any]:
        """Export complete audit log for external review"""
        with self._lock:
            valid, error = self.verify_audit_chain()
            return {
                "export_timestamp": datetime.now().isoformat(),
                "chain_valid": valid,
                "chain_error": error,
                "total_entries": len(self.audit_log),
                "entries": [
                    {
                        **asdict(e),
                        "event_type": e.event_type.value,
                        "principle": e.principle.value if e.principle else None,
                        "severity": e.severity.value if e.severity else None
                    }
                    for e in self.audit_log
                ]
            }

    def _generate_recommendations(
        self,
        violations_by_principle: Dict[Principle, int],
        pass_rate: float
    ) -> List[str]:
        """Generate improvement recommendations"""
        recs = []

        if pass_rate < 0.7:
            recs.append(
                "CRITICAL: Pass rate below 70%. Immediate review of agent workflow required."
            )

        if violations_by_principle.get(Principle.HONESTY, 0) > 0:
            recs.append(
                "Reduce absolute claims. Use 'I don't know' and 'needs verification'."
            )

        if violations_by_principle.get(Principle.EVIDENCE, 0) > 3:
            recs.append(
                "Add source citations to all claims. Use 'based on ...' format."
            )

        if violations_by_principle.get(Principle.MINIMAL, 0) > 5:
            recs.append(
                "Apply YAGNI principle. Remove unused code and dependencies."
            )

        if violations_by_principle.get(Principle.REVERSIBILITY, 0) > 0:
            recs.append(
                "Add rollback plans to all changes. Backup before destructive ops."
            )

        if violations_by_principle.get(Principle.HUMAN_AGENCY, 0) > 0:
            recs.append(
                "STOP and ask user before irreversible actions. Escalate to human review."
            )

        if not recs:
            recs.append("Compliance is excellent. Continue current practices.")

        return recs

    def _calculate_trend(self, days: int = 7) -> Dict[str, float]:
        """Calculate pass rate trend over time"""
        with self._lock:
            trend = {}
            now = datetime.now()

            for day_offset in range(days):
                day = (now - timedelta(days=day_offset)).date().isoformat()
                day_checks = [
                    c for c in self.guard.check_history
                    if c.timestamp.startswith(day)
                ]
                if day_checks:
                    passed = sum(
                        1 for c in day_checks if c.status == CheckStatus.PASS
                    )
                    trend[day] = passed / len(day_checks)
                else:
                    trend[day] = 0.0

            return trend

    def _hash_evidence(self, result: CheckResult) -> str:
        """Generate evidence hash for a check result"""
        content = json.dumps(
            {
                "artifact_id": result.artifact_id,
                "agent_id": result.agent_id,
                "status": result.status.value,
                "violations": [
                    {
                        "principle": v.principle.value,
                        "severity": v.severity.value,
                        "pattern": v.matched_pattern
                    }
                    for v in result.violations
                ]
            },
            sort_keys=True
        )
        return hashlib.sha256(content.encode()).hexdigest()

    def _hash_violation(self, violation: Violation) -> str:
        """Generate evidence hash for a violation"""
        content = json.dumps(
            {
                "principle": violation.principle.value,
                "severity": violation.severity.value,
                "pattern": violation.matched_pattern,
                "evidence": violation.evidence
            },
            sort_keys=True
        )
        return hashlib.sha256(content.encode()).hexdigest()

    def _hash_string(self, text: str) -> str:
        """Hash a string"""
        return hashlib.sha256(text.encode()).hexdigest()

    def _load_audit_log(self) -> None:
        """Load audit log from disk"""
        log_file = self.storage_path / "audit_log.json"
        if log_file.exists():
            try:
                with open(log_file, "r") as f:
                    data = json.load(f)
                for e_data in data.get("entries", []):
                    e_data["event_type"] = AuditEventType(e_data["event_type"])
                    if e_data.get("principle"):
                        e_data["principle"] = Principle(e_data["principle"])
                    if e_data.get("severity"):
                        e_data["severity"] = Severity(e_data["severity"])
                    entry = AuditEntry(**e_data)
                    self.audit_log.append(entry)
                if self.audit_log:
                    self.last_hash = self.audit_log[-1].evidence_hash
            except Exception as e:
                logger.error(f"Failed to load audit log: {e}")

    def _save_audit_log(self) -> None:
        """Save audit log to disk"""
        log_file = self.storage_path / "audit_log.json"
        try:
            data = {
                "entries": [
                    {
                        **asdict(e),
                        "event_type": e.event_type.value,
                        "principle": e.principle.value if e.principle else None,
                        "severity": e.severity.value if e.severity else None
                    }
                    for e in self.audit_log
                ]
            }
            with open(log_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save audit log: {e}")


# Module-level singleton
_default_audit: Optional[ConstitutionalAudit] = None


def get_constitutional_audit() -> ConstitutionalAudit:
    """Get or create the default constitutional audit"""
    global _default_audit
    if _default_audit is None:
        _default_audit = ConstitutionalAudit()
    return _default_audit
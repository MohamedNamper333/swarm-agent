"""
Unit tests for Constitutional Guard and Audit - Week 9
"""
import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch

from swarm.intelligence.constitutional_guard import (
    ConstitutionalGuard,
    Violation,
    CheckResult,
    Principle,
    Severity,
    CheckStatus,
    get_constitutional_guard
)
from swarm.intelligence.constitutional_audit import (
    ConstitutionalAudit,
    AuditEntry,
    AgentComplianceReport,
    SystemComplianceDashboard,
    AuditEventType,
    ComplianceLevel,
    get_constitutional_audit
)


@pytest.fixture
def temp_storage():
    """Create temporary storage directory"""
    tmpdir = tempfile.mkdtemp()
    yield tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def guard(temp_storage):
    """Create a constitutional guard with temporary storage"""
    g = ConstitutionalGuard(storage_path=temp_storage)
    yield g
    g.violations.clear()
    g.check_history.clear()


@pytest.fixture
def audit(guard, temp_storage):
    """Create a constitutional audit with the guard"""
    return ConstitutionalAudit(
        constitutional_guard=guard,
        storage_path=f"{temp_storage}/audit"
    )


class TestPrinciple:
    """Test Principle enum"""

    def test_principle_values(self):
        assert Principle.HONESTY.value == "HONESTY_OVER_HELPFULNESS"
        assert Principle.EVIDENCE.value == "EVIDENCE_OVER_AUTHORITY"
        assert Principle.MINIMAL.value == "MINIMAL_SURFACE_AREA"
        assert Principle.REVERSIBILITY.value == "REVERSIBILITY_BY_DEFAULT"
        assert Principle.HUMAN_AGENCY.value == "HUMAN_AGENCY_PRESERVATION"


class TestSeverity:
    """Test Severity enum"""

    def test_severity_values(self):
        assert Severity.INFO.value == "info"
        assert Severity.WARNING.value == "warning"
        assert Severity.CRITICAL.value == "critical"
        assert Severity.BLOCKING.value == "blocking"


class TestCheckStatus:
    """Test CheckStatus enum"""

    def test_status_values(self):
        assert CheckStatus.PASS.value == "pass"
        assert CheckStatus.WARN.value == "warn"
        assert CheckStatus.FAIL.value == "fail"
        assert CheckStatus.BLOCKED.value == "blocked"


class TestConstitutionalGuardInit:
    """Test guard initialization"""

    def test_guard_creates_storage(self, temp_storage):
        guard = ConstitutionalGuard(storage_path=temp_storage)
        assert Path(temp_storage).exists()

    def test_guard_initial_state(self, guard):
        stats = guard.get_stats()
        assert stats["total_checks"] == 0
        assert stats["total_violations"] == 0


class TestConstitutionalGuardCheck:
    """Test artifact checking"""

    def test_check_clean_text_passes(self, guard):
        result = guard.check_artifact(
            artifact_id="test-001",
            artifact_content="This is a normal sentence.",
            agent_id="agent-001"
        )
        assert result.status in (CheckStatus.PASS, CheckStatus.WARN)

    def test_check_honesty_violation(self, guard):
        result = guard.check_artifact(
            artifact_id="test-honesty",
            artifact_content="This will definitely work and is 100% guaranteed.",
            agent_id="agent-001"
        )
        honesty_violations = [
            v for v in result.violations if v.principle == Principle.HONESTY
        ]
        assert len(honesty_violations) > 0

    def test_check_evidence_violation(self, guard):
        result = guard.check_artifact(
            artifact_id="test-evidence",
            artifact_content="Trust me, this is the best solution.",
            agent_id="agent-001"
        )
        evidence_violations = [
            v for v in result.violations if v.principle == Principle.EVIDENCE
        ]
        assert len(evidence_violations) > 0

    def test_check_minimal_violation(self, guard):
        result = guard.check_artifact(
            artifact_id="test-minimal",
            artifact_content="Let's add this just in case for future use.",
            agent_id="agent-001"
        )
        minimal_violations = [
            v for v in result.violations if v.principle == Principle.MINIMAL
        ]
        assert len(minimal_violations) > 0

    def test_check_reversibility_violation(self, guard):
        result = guard.check_artifact(
            artifact_id="test-rev",
            artifact_content="This operation is permanent and cannot be undone.",
            agent_id="agent-001"
        )
        rev_violations = [
            v for v in result.violations if v.principle == Principle.REVERSIBILITY
        ]
        assert len(rev_violations) > 0

    def test_check_human_agency_violation(self, guard):
        result = guard.check_artifact(
            artifact_id="test-human",
            artifact_content="This will automatically delete all data without confirmation.",
            agent_id="agent-001"
        )
        human_violations = [
            v for v in result.violations if v.principle == Principle.HUMAN_AGENCY
        ]
        assert len(human_violations) > 0

    def test_blocking_severity_marks_blocked(self, guard):
        result = guard.check_artifact(
            artifact_id="test-block",
            artifact_content="This will automatically delete data without confirmation.",
            agent_id="agent-001"
        )
        # Should be BLOCKED due to human agency violation
        assert result.status in (CheckStatus.BLOCKED, CheckStatus.FAIL)

    def test_requires_human_review_set(self, guard):
        result = guard.check_artifact(
            artifact_id="test-review",
            artifact_content="This will automatically delete everything.",
            agent_id="agent-001"
        )
        # Critical violations should require human review
        if any(v.severity in (Severity.CRITICAL, Severity.BLOCKING)
               for v in result.violations):
            assert result.requires_human_review is True


class TestConstitutionalGuardPositiveContent:
    """Test content with positive indicators"""

    def test_honest_uncertainty_passes(self, guard):
        result = guard.check_artifact(
            artifact_id="test-honest",
            artifact_content=(
                "I'm not certain, but I think this might work. "
                "Needs verification before deployment."
            ),
            agent_id="agent-001"
        )
        honesty_violations = [
            v for v in result.violations if v.principle == Principle.HONESTY
        ]
        assert len(honesty_violations) == 0

    def test_with_citations_passes(self, guard):
        result = guard.check_artifact(
            artifact_id="test-cited",
            artifact_content=(
                "According to the documentation, this is the best approach. "
                "Source: official_docs.md"
            ),
            agent_id="agent-001"
        )
        evidence_violations = [
            v for v in result.violations if v.principle == Principle.EVIDENCE
        ]
        assert len(evidence_violations) == 0

    def test_with_rollback_plan_passes(self, guard):
        result = guard.check_artifact(
            artifact_id="test-rollback",
            artifact_content=(
                "This change includes a rollback plan and backup procedure. "
                "The operation is reversible and atomic."
            ),
            agent_id="agent-001"
        )
        rev_violations = [
            v for v in result.violations if v.principle == Principle.REVERSIBILITY
        ]
        assert len(rev_violations) == 0

    def test_with_user_approval_passes(self, guard):
        result = guard.check_artifact(
            artifact_id="test-approval",
            artifact_content=(
                "This requires user confirmation before proceeding. "
                "Will ask user and escalate to human review."
            ),
            agent_id="agent-001"
        )
        human_violations = [
            v for v in result.violations if v.principle == Principle.HUMAN_AGENCY
        ]
        assert len(human_violations) == 0


class TestViolationResolution:
    """Test violation resolution"""

    def test_resolve_violation(self, guard):
        result = guard.check_artifact(
            artifact_id="test-resolve",
            artifact_content="This will definitely work.",
            agent_id="agent-001"
        )
        assert len(result.violations) > 0

        violation_id = result.violations[0].id
        success = guard.resolve_violation(violation_id, "Fixed by rephrasing")
        assert success is True

        violations = guard.get_violations(resolved=False)
        assert not any(v.id == violation_id for v in violations)

    def test_resolve_nonexistent_violation(self, guard):
        success = guard.resolve_violation("nonexistent-id", "note")
        assert success is False


class TestViolationFiltering:
    """Test violation filtering"""

    def test_get_violations_by_principle(self, guard):
        guard.check_artifact(
            artifact_id="test-1",
            artifact_content="This will definitely work.",
            agent_id="agent-001"
        )
        guard.check_artifact(
            artifact_id="test-2",
            artifact_content="This is the best, trust me.",
            agent_id="agent-001"
        )

        honesty_v = guard.get_violations(principle=Principle.HONESTY)
        evidence_v = guard.get_violations(principle=Principle.EVIDENCE)
        assert len(honesty_v) >= 1
        assert len(evidence_v) >= 1

    def test_get_violations_by_agent(self, guard):
        guard.check_artifact(
            artifact_id="test-1",
            artifact_content="This will definitely work.",
            agent_id="agent-A"
        )
        guard.check_artifact(
            artifact_id="test-2",
            artifact_content="This will definitely work.",
            agent_id="agent-B"
        )

        a_v = guard.get_violations(agent_id="agent-A")
        b_v = guard.get_violations(agent_id="agent-B")
        assert all(v.agent_id == "agent-A" for v in a_v)
        assert all(v.agent_id == "agent-B" for v in b_v)

    def test_get_violations_resolved_filter(self, guard):
        result = guard.check_artifact(
            artifact_id="test-1",
            artifact_content="This will definitely work.",
            agent_id="agent-001"
        )
        guard.resolve_violation(result.violations[0].id, "Fixed")

        unresolved = guard.get_violations(resolved=False)
        resolved = guard.get_violations(resolved=True)
        assert len(resolved) >= 1


class TestCheckHistory:
    """Test check history"""

    def test_history_recorded(self, guard):
        guard.check_artifact(
            artifact_id="test-1",
            artifact_content="Test content",
            agent_id="agent-001"
        )
        history = guard.get_check_history()
        assert len(history) == 1

    def test_history_filtered_by_status(self, guard):
        guard.check_artifact(
            artifact_id="test-clean",
            artifact_content="Clean content here.",
            agent_id="agent-001"
        )
        passed = guard.get_check_history(status=CheckStatus.PASS)
        assert all(h.status == CheckStatus.PASS for h in passed)


class TestGuardStats:
    """Test guard statistics"""

    def test_stats_updated_after_check(self, guard):
        guard.check_artifact(
            artifact_id="test",
            artifact_content="Test content",
            agent_id="agent-001"
        )
        stats = guard.get_stats()
        assert stats["total_checks"] == 1


class TestGuardExport:
    """Test guard export"""

    def test_export_report(self, guard):
        guard.check_artifact(
            artifact_id="test-1",
            artifact_content="This will definitely work.",
            agent_id="agent-001"
        )
        report = guard.export_report()
        assert "stats" in report
        assert "violations" in report
        assert "recent_checks" in report


class TestConstitutionalAuditInit:
    """Test audit initialization"""

    def test_audit_creation(self, audit):
        assert audit is not None

    def test_audit_storage_path(self, audit, temp_storage):
        assert audit.storage_path.exists()


class TestAuditLogging:
    """Test audit logging"""

    def test_check_creates_audit_entry(self, audit):
        initial_count = len(audit.audit_log)
        audit.guard.check_artifact(
            artifact_id="test-audit",
            artifact_content="Test content",
            agent_id="agent-001"
        )
        assert len(audit.audit_log) > initial_count

    def test_violation_creates_audit_entry(self, audit):
        initial_count = len(audit.audit_log)
        audit.guard.check_artifact(
            artifact_id="test-violation",
            artifact_content="This will definitely work.",
            agent_id="agent-001"
        )
        assert len(audit.audit_log) > initial_count

    def test_resolve_creates_audit_entry(self, audit):
        result = audit.guard.check_artifact(
            artifact_id="test-resolve",
            artifact_content="This will definitely work.",
            agent_id="agent-001"
        )
        initial_count = len(audit.audit_log)
        violation_id = result.violations[0].id
        audit.record_violation_resolved(violation_id, "admin")
        assert len(audit.audit_log) > initial_count


class TestAuditChainIntegrity:
    """Test audit chain integrity"""

    def test_chain_valid_initially(self, audit):
        valid, error = audit.verify_audit_chain()
        assert valid is True
        assert error is None

    def test_chain_valid_after_checks(self, audit):
        for i in range(3):
            audit.guard.check_artifact(
                artifact_id=f"test-{i}",
                artifact_content=f"Content {i}",
                agent_id="agent-001"
            )
        valid, error = audit.verify_audit_chain()
        assert valid is True
        assert error is None


class TestAgentComplianceReport:
    """Test agent compliance reporting"""

    def test_report_no_activity(self, audit):
        report = audit.generate_agent_report("no-activity-agent")
        assert report.total_checks == 0
        assert report.pass_rate == 0.0

    def test_report_with_checks(self, audit):
        for i in range(5):
            audit.guard.check_artifact(
                artifact_id=f"test-{i}",
                artifact_content="Clean content here.",
                agent_id="agent-001"
            )
        report = audit.generate_agent_report("agent-001")
        assert report.total_checks == 5
        assert report.agent_id == "agent-001"

    def test_report_pass_rate_calculation(self, audit):
        for i in range(3):
            audit.guard.check_artifact(
                artifact_id=f"clean-{i}",
                artifact_content="Clean content.",
                agent_id="agent-001"
            )
        for i in range(1):
            audit.guard.check_artifact(
                artifact_id=f"violation-{i}",
                artifact_content="This will definitely work.",
                agent_id="agent-001"
            )
        report = audit.generate_agent_report("agent-001")
        assert report.passed_checks >= 3

    def test_report_compliance_levels(self, audit):
        for i in range(10):
            audit.guard.check_artifact(
                artifact_id=f"clean-{i}",
                artifact_content="Clean content.",
                agent_id="good-agent"
            )
        report = audit.generate_agent_report("good-agent")
        assert report.compliance_level in ComplianceLevel

    def test_report_recommendations(self, audit):
        audit.guard.check_artifact(
            artifact_id="test",
            artifact_content="This will definitely work.",
            agent_id="agent-001"
        )
        report = audit.generate_agent_report("agent-001")
        assert len(report.recommendations) > 0


class TestSystemDashboard:
    """Test system-wide dashboard"""

    def test_dashboard_no_activity(self, audit):
        dashboard = audit.generate_system_dashboard()
        assert dashboard.total_checks == 0

    def test_dashboard_with_activity(self, audit):
        for i in range(5):
            audit.guard.check_artifact(
                artifact_id=f"test-{i}",
                artifact_content=f"Content {i}",
                agent_id=f"agent-{i}"
            )
        dashboard = audit.generate_system_dashboard()
        assert dashboard.total_checks == 5
        assert dashboard.agents_count == 5

    def test_dashboard_compliance_level(self, audit):
        for i in range(10):
            audit.guard.check_artifact(
                artifact_id=f"test-{i}",
                artifact_content="Clean content.",
                agent_id="agent-001"
            )
        dashboard = audit.generate_system_dashboard()
        assert dashboard.system_compliance_level in ComplianceLevel

    def test_dashboard_trend(self, audit):
        for i in range(5):
            audit.guard.check_artifact(
                artifact_id=f"test-{i}",
                artifact_content="Clean content.",
                agent_id="agent-001"
            )
        dashboard = audit.generate_system_dashboard()
        assert isinstance(dashboard.trend, dict)


class TestAuditLogQuery:
    """Test audit log queries"""

    def test_get_audit_log(self, audit):
        audit.guard.check_artifact(
            artifact_id="test",
            artifact_content="Test content",
            agent_id="agent-001"
        )
        log = audit.get_audit_log()
        assert len(log) > 0

    def test_get_audit_log_by_event_type(self, audit):
        audit.guard.check_artifact(
            artifact_id="test",
            artifact_content="This will definitely work.",
            agent_id="agent-001"
        )
        checks = audit.get_audit_log(event_type=AuditEventType.CHECK_PERFORMED)
        violations = audit.get_audit_log(event_type=AuditEventType.VIOLATION_DETECTED)
        assert len(checks) > 0
        assert len(violations) > 0

    def test_get_audit_log_by_agent(self, audit):
        audit.guard.check_artifact(
            artifact_id="test",
            artifact_content="Test content",
            agent_id="specific-agent"
        )
        log = audit.get_audit_log(agent_id="specific-agent")
        assert all(e.agent_id == "specific-agent" for e in log)


class TestAuditExport:
    """Test audit export"""

    def test_export_full_audit(self, audit):
        audit.guard.check_artifact(
            artifact_id="test",
            artifact_content="Test content",
            agent_id="agent-001"
        )
        export = audit.export_full_audit()
        assert "chain_valid" in export
        assert "total_entries" in export
        assert "entries" in export


class TestSingleton:
    """Test singleton accessors"""

    def test_get_guard_returns_instance(self):
        g = get_constitutional_guard()
        assert isinstance(g, ConstitutionalGuard)

    def test_get_audit_returns_instance(self):
        a = get_constitutional_audit()
        assert isinstance(a, ConstitutionalAudit)


class TestEdgeCases:
    """Test edge cases"""

    def test_check_empty_content(self, guard):
        result = guard.check_artifact(
            artifact_id="empty",
            artifact_content="",
            agent_id="agent-001"
        )
        assert result is not None

    def test_check_dict_content(self, guard):
        result = guard.check_artifact(
            artifact_id="dict",
            artifact_content={"key": "value"},
            agent_id="agent-001"
        )
        assert result is not None

    def test_check_list_content(self, guard):
        result = guard.check_artifact(
            artifact_id="list",
            artifact_content=["item1", "item2"],
            agent_id="agent-001"
        )
        assert result is not None

    def test_check_with_metadata(self, guard):
        result = guard.check_artifact(
            artifact_id="meta",
            artifact_content="Test content",
            agent_id="agent-001",
            metadata={"source": "test", "version": 1}
        )
        assert result.metadata.get("source") == "test"

    def test_check_with_artifact_type(self, guard):
        result = guard.check_artifact(
            artifact_id="typed",
            artifact_content="Test",
            agent_id="agent-001",
            artifact_type="code"
        )
        assert result.artifact_type == "code"


class TestRecommendationEngine:
    """Test recommendation generation"""

    def test_honesty_recommendation(self, guard):
        rec = guard._get_recommendation(Principle.HONESTY)
        assert "honest" in rec.lower() or "uncertainty" in rec.lower()

    def test_evidence_recommendation(self, guard):
        rec = guard._get_recommendation(Principle.EVIDENCE)
        assert "source" in rec.lower() or "citation" in rec.lower()

    def test_minimal_recommendation(self, guard):
        rec = guard._get_recommendation(Principle.MINIMAL)
        assert "remove" in rec.lower() or "yagni" in rec.lower()

    def test_reversibility_recommendation(self, guard):
        rec = guard._get_recommendation(Principle.REVERSIBILITY)
        assert "rollback" in rec.lower() or "backup" in rec.lower()

    def test_human_agency_recommendation(self, guard):
        rec = guard._get_recommendation(Principle.HUMAN_AGENCY)
        assert "user" in rec.lower() or "human" in rec.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
"""
Unit tests for Learning Tracker
"""
import pytest
import tempfile
import shutil
from pathlib import Path

from swarm.intelligence.learning_tracker import (
    LearningTracker,
    AgentLearningProfile,
    MetricSnapshot,
    MetricType,
    TrendDirection,
    SkillProficiency,
    LearningCurve
)


@pytest.fixture
def temp_storage():
    """Create temporary storage directory"""
    tmpdir = tempfile.mkdtemp()
    yield tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def tracker(temp_storage):
    """Create a learning tracker with temporary storage"""
    t = LearningTracker(storage_path=temp_storage)
    yield t
    t.profiles.clear()


class TestMetricType:
    """Test MetricType enum"""

    def test_metric_types_exist(self):
        for metric in [
            MetricType.TASK_SUCCESS_RATE,
            MetricType.TASK_DURATION,
            MetricType.CODE_QUALITY,
            MetricType.SECURITY_SCORE,
            MetricType.TEST_COVERAGE,
            MetricType.REVIEW_SCORE,
            MetricType.REFLECTION_DEPTH,
            MetricType.CONSTITUTIONAL_COMPLIANCE,
            MetricType.COLLABORATION_SCORE,
            MetricType.INNOVATION_INDEX
        ]:
            assert metric.value is not None


class TestTrendDirection:
    """Test TrendDirection enum"""

    def test_trend_directions(self):
        assert TrendDirection.IMPROVING.value == "improving"
        assert TrendDirection.STABLE.value == "stable"
        assert TrendDirection.DECLINING.value == "declining"
        assert TrendDirection.VOLATILE.value == "volatile"


class TestLearningTrackerInit:
    """Test tracker initialization"""

    def test_tracker_creates_storage(self, temp_storage):
        tracker = LearningTracker(storage_path=temp_storage)
        assert Path(temp_storage).exists()

    def test_tracker_initial_state(self, tracker):
        assert len(tracker.profiles) == 0


class TestRecordMetric:
    """Test metric recording"""

    def test_record_metric_creates_profile(self, tracker):
        tracker.record_metric(
            agent_id="agent-001",
            metric_type=MetricType.TASK_SUCCESS_RATE,
            value=0.95,
            task_id="task-001"
        )
        assert "agent-001" in tracker.profiles

    def test_record_metric_updates_count(self, tracker):
        for i in range(5):
            tracker.record_metric(
                agent_id="agent-001",
                metric_type=MetricType.TASK_SUCCESS_RATE,
                value=0.8 + i * 0.02,
                task_id=f"task-{i}"
            )
        profile = tracker.get_profile("agent-001")
        # profile["metric_history"] is a dict keyed by MetricType, each value is a list
        total_snapshots = sum(
            len(snapshots) for snapshots in profile["metric_history"].values()
        )
        assert total_snapshots == 5

    def test_record_multiple_metrics(self, tracker):
        tracker.record_metric("agent-001", MetricType.TASK_SUCCESS_RATE, 0.9, "task-1")
        tracker.record_metric("agent-001", MetricType.CODE_QUALITY, 0.85, "task-1")
        tracker.record_metric("agent-001", MetricType.SECURITY_SCORE, 0.95, "task-1")
        profile = tracker.get_profile("agent-001")
        total_snapshots = sum(
            len(snapshots) for snapshots in profile["metric_history"].values()
        )
        assert total_snapshots == 3

    def test_record_metric_with_context(self, tracker):
        tracker.record_metric(
            agent_id="agent-001",
            metric_type=MetricType.TASK_SUCCESS_RATE,
            value=0.9,
            task_id="task-1",
            context={"complexity": "high"}
        )
        profile = tracker.get_profile("agent-001")
        assert profile is not None


class TestGetProfile:
    """Test profile retrieval"""

    def test_get_profile_returns_dict(self, tracker):
        tracker.record_metric("agent-001", MetricType.TASK_SUCCESS_RATE, 0.9, "task-1")
        profile = tracker.get_profile("agent-001")
        assert isinstance(profile, dict)

    def test_get_profile_includes_agent_id(self, tracker):
        tracker.record_metric("agent-001", MetricType.TASK_SUCCESS_RATE, 0.9, "task-1")
        profile = tracker.get_profile("agent-001")
        assert profile["agent_id"] == "agent-001"

    def test_get_profile_includes_metric_history(self, tracker):
        tracker.record_metric("agent-001", MetricType.TASK_SUCCESS_RATE, 0.9, "task-1")
        profile = tracker.get_profile("agent-001")
        assert "metric_history" in profile

    def test_get_profile_includes_learning_curves(self, tracker):
        tracker.record_metric("agent-001", MetricType.TASK_SUCCESS_RATE, 0.9, "task-1")
        profile = tracker.get_profile("agent-001")
        assert "learning_curves" in profile

    def test_get_unknown_profile(self, tracker):
        profile = tracker.get_profile("nonexistent")
        assert profile is None


class TestGetLearningCurve:
    """Test learning curve retrieval"""

    def test_get_learning_curve(self, tracker):
        tracker.record_metric("agent-001", MetricType.TASK_SUCCESS_RATE, 0.9, "task-1")
        curve = tracker.get_learning_curve("agent-001", MetricType.TASK_SUCCESS_RATE)
        assert curve is not None
        assert curve["metric_type"] == MetricType.TASK_SUCCESS_RATE

    def test_get_curve_unknown_agent(self, tracker):
        curve = tracker.get_learning_curve("nonexistent", MetricType.TASK_SUCCESS_RATE)
        assert curve is None


class TestGetPerformanceReport:
    """Test performance reporting"""

    def test_get_report(self, tracker):
        tracker.record_metric("agent-001", MetricType.TASK_SUCCESS_RATE, 0.9, "task-1")
        report = tracker.get_performance_report("agent-001")
        assert report is not None
        assert report["agent_id"] == "agent-001"
        assert "overall_score" in report
        assert "trend" in report


class TestCompareAgents:
    """Test agent comparison"""

    def test_compare_agents(self, tracker):
        tracker.record_metric("agent-001", MetricType.TASK_SUCCESS_RATE, 0.95, "task-1")
        tracker.record_metric("agent-002", MetricType.TASK_SUCCESS_RATE, 0.75, "task-1")
        comparison = tracker.compare_agents(["agent-001", "agent-002"])
        assert comparison is not None


class TestPredictPerformance:
    """Test performance prediction"""

    def test_predict_performance(self, tracker):
        for i in range(10):
            tracker.record_metric(
                "agent-001",
                MetricType.TASK_SUCCESS_RATE,
                0.8 + i * 0.01,
                f"task-{i}"
            )
        predictions = tracker.predict_performance(
            "agent-001", MetricType.TASK_SUCCESS_RATE, steps=3
        )
        assert isinstance(predictions, list)


class TestGetSkillProficiency:
    """Test skill proficiency"""

    def test_get_skill_proficiency(self, tracker):
        tracker.record_metric("agent-001", MetricType.CODE_QUALITY, 0.9, "task-1")
        prof = tracker.get_skill_proficiency("agent-001", "python")
        # May be None if no skills tracked
        assert prof is None or isinstance(prof, dict)


class TestGetTopSkills:
    """Test top skills retrieval"""

    def test_get_top_skills(self, tracker):
        tracker.record_metric("agent-001", MetricType.CODE_QUALITY, 0.9, "task-1")
        skills = tracker.get_top_skills("agent-001")
        assert isinstance(skills, list)


class TestEdgeCases:
    """Test edge cases"""

    def test_record_zero_value(self, tracker):
        tracker.record_metric("agent-001", MetricType.TASK_SUCCESS_RATE, 0.0, "task-1")
        profile = tracker.get_profile("agent-001")
        assert profile is not None

    def test_record_high_value(self, tracker):
        tracker.record_metric("agent-001", MetricType.TASK_SUCCESS_RATE, 1.0, "task-1")
        profile = tracker.get_profile("agent-001")
        assert profile is not None

    def test_record_negative_value(self, tracker):
        # Should not raise
        tracker.record_metric("agent-001", MetricType.TASK_DURATION, -1, "task-1")
        profile = tracker.get_profile("agent-001")
        assert profile is not None


class TestDataClasses:
    """Test dataclasses"""

    def test_metric_snapshot_creation(self):
        snap = MetricSnapshot(
            metric_type=MetricType.TASK_SUCCESS_RATE,
            value=0.95,
            timestamp="2026-08-05",
            task_id="task-1"
        )
        assert snap.value == 0.95
        assert snap.task_id == "task-1"

    def test_skill_proficiency_creation(self):
        prof = SkillProficiency(
            skill_name="python",
            current_level=0.9,
            confidence=0.85,
            tasks_completed=10,
            last_updated="2026-08-05"
        )
        assert prof.skill_name == "python"
        assert prof.current_level == 0.9

    def test_learning_curve_creation(self):
        curve = LearningCurve(metric_type=MetricType.TASK_SUCCESS_RATE)
        assert curve.metric_type == MetricType.TASK_SUCCESS_RATE
        assert curve.trend == TrendDirection.STABLE


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
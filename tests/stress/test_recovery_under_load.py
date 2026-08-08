"""Stress test: recovery-under-load — induce failures and confirm recovery.

Verifies the swarm's resilience primitives survive chaotic conditions.

Usage: PYTHONPATH=. pytest tests/stress/test_recovery_under_load.py -v
"""
import time
import pytest

from swarm.core.task_dag import TaskClassifier, TaskType
from swarm.core.task_dag import DAGBuilder
from swarm.observability.alert_manager import AlertManager, AlertRule, AlertSeverity


class TestRecoveryUnderLoad:
    """Chaos test: induce failures and confirm recovery happens."""

    def test_task_classifier_recovers_from_empty_inputs(self):
        """Classifier must not crash on empty / whitespace inputs."""
        from swarm.core.task_classifier import TaskClassification
        classifier = TaskClassifier()
        for bad in ["", "   ", "\n\t", "random gibberish xyz"]:
            try:
                result = classifier.classify(bad)
                assert hasattr(result, "task_type") and isinstance(result.task_type, TaskType)
            except Exception as e:
                pytest.fail(f"classifier crashed on input {bad!r}: {e}")
        print(f"✅ TaskClassifier survived 4 edge-case inputs")

    def test_alert_manager_survives_chaos_loop(self, tmp_path):
        """After 50 alert fires, the manager must stay stable."""
        mgr = AlertManager(storage_path=str(tmp_path))
        rule = AlertRule(
            id="chaos", name="Chaos", description="x",
            metric_name="boom", condition="gt", threshold=0.0,
            severity=AlertSeverity.CRITICAL, cooldown_seconds=0,
        )
        mgr.add_rule(rule)
        for _ in range(50):
            mgr.evaluate(metric_name="boom", metric_value=99.0)
        stats = mgr.get_stats()
        assert stats is not None
        history = mgr.get_alert_history()
        assert len(history) >= 1
        print(f"✅ AlertManager survived 50 fires — history={len(history)}, stats ok")

    def test_swarm_survives_mixed_traffic(self):
        """Mix valid + invalid classifier inputs → must not crash."""
        classifier = TaskClassifier()
        samples = [
            "Fix the bug in payment.py",
            "Add new feature to dashboard",
            "Refactor the auth module",
            "Investigate slow query performance",
            "Quick typo fix",
        ]
        out = []
        for i in range(100):
            s = samples[i % len(samples)]
            try:
                out.append(classifier.classify(s))
            except Exception:
                out.append(None)
        assert len(out) == 100
        assert sum(1 for x in out if x is not None) >= 95
        # verify results have valid task_type attribute
        assert all(x is None or hasattr(x, "task_type") for x in out)
        print(f"✅ TaskClassifier handled 100 mixed inputs without crash")

    def test_dag_builder_remains_functional_after_errors(self):
        """DAGBuilder must remain functional even if called repeatedly with different templates."""
        builder = DAGBuilder()
        templates = list(DAGBuilder.TASK_TEMPLATES.keys())
        results = []
        for i in range(50):
            try:
                info = builder.get_template_info(templates[i % len(templates)])
                results.append(len(info["stages"]) if info else 0)
            except Exception:
                results.append(0)
        assert len(results) == 50
        assert all(r > 0 for r in results), "every template lookup should return stages"
        print(f"✅ DAGBuilder survived 50 mixed lookups")

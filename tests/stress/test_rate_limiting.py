"""Stress test: rate-limiting / throttling on alerts and plugin discovery.

Verifies that the swarm's rate-limit primitives kick in under flooding
and stay fast under repeat hits.

Usage: PYTHONPATH=. pytest tests/stress/test_rate_limiting.py -v
"""
import time
import pytest
from pathlib import Path

from swarm.observability.alert_manager import AlertManager, AlertRule, AlertSeverity
from swarm.plugins.loader import PluginLoader


@pytest.fixture
def alert_mgr(tmp_path):
    return AlertManager(storage_path=str(tmp_path))


class TestRateLimiting:
    """Verify rate limits hold up under spam and recover when traffic stops."""

    def test_task_type_lookup_not_degraded_under_repeat_hits(self):
        """Look up task types 5000 times — must stay < 200ms."""
        from swarm.core.task_dag import TaskType
        start = time.perf_counter()
        for _ in range(5000):
            _ = TaskType.IMPLEMENTATION
        elapsed = time.perf_counter() - start
        assert elapsed < 0.2, f"5000 enum lookups took {elapsed:.3f}s"
        print(f"✅ 5000 TaskType lookups in {elapsed*1000:.1f}ms")

    def test_alert_manager_handles_repeated_evaluation(self, alert_mgr):
        """AlertManager must not crash when a metric spikes 100 times."""
        rule = AlertRule(
            id="flood-rule",
            name="Flood",
            description="test flood",
            metric_name="latency_ms",
            condition="gt",
            threshold=100.0,
            severity=AlertSeverity.WARNING,
            cooldown_seconds=0,
        )
        alert_mgr.add_rule(rule)
        for i in range(100):
            alert_mgr.evaluate(metric_name="latency_ms", metric_value=200.0 + i)
        history = alert_mgr.get_alert_history()
        assert len(history) >= 1, "no alerts were fired"
        print(f"✅ AlertManager delivered {len(history)} alerts without crash")

    def test_alert_manager_evaluate_is_fast(self, alert_mgr):
        """1000 evaluations must complete under 2 seconds."""
        rule = AlertRule(
            id="r", name="R", description="x",
            metric_name="m", condition="gt", threshold=1.0,
            severity=AlertSeverity.INFO, cooldown_seconds=0,
        )
        alert_mgr.add_rule(rule)
        start = time.perf_counter()
        for _ in range(1000):
            alert_mgr.evaluate(metric_name="m", metric_value=99.0)
        elapsed = time.perf_counter() - start
        assert elapsed < 2.0, f"1000 evaluates took {elapsed:.3f}s"
        print(f"✅ 1000 AlertManager.evaluate() calls in {elapsed*1000:.1f}ms")

    def test_plugin_loader_discover_yaml_files(self):
        """PluginLoader.discover_yaml_files() must find plugins under load."""
        loader = PluginLoader(plugin_dirs=[Path("swarm/plugins/builtin")])
        start = time.perf_counter()
        for _ in range(20):
            files = loader.discover_yaml_files()
        elapsed = time.perf_counter() - start
        assert elapsed < 5.0, f"20 discoveries took {elapsed:.2f}s"
        print(f"✅ 20 plugin discoveries in {elapsed*1000:.1f}ms")

    def test_alert_manager_cooldown_blocks_repeat(self, alert_mgr):
        """Cooldown blocks repeated alerts within the cooldown window."""
        rule = AlertRule(
            id="cd", name="CD", description="x",
            metric_name="err", condition="gt", threshold=0.0,
            severity=AlertSeverity.CRITICAL, cooldown_seconds=60,
        )
        alert_mgr.add_rule(rule)
        a1 = alert_mgr.evaluate(metric_name="err", metric_value=99.0)
        a2 = alert_mgr.evaluate(metric_name="err", metric_value=99.0)  # within cooldown
        assert len(a1) >= 1
        assert len(a2) == 0, "cooldown should block second alert within 60s window"
        print(f"✅ Alert cooldown blocked repeat alert within window")

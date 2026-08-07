"""
Unit tests for Observability modules - Week 12
"""
import pytest
import tempfile
import shutil
from pathlib import Path

from swarm.observability.metrics_server import (
    MetricsServer, MetricType, MetricPoint, HistogramData
)
from swarm.observability.event_logger import (
    EventLogger, LogLevel, EventCategory
)
from swarm.observability.alert_manager import (
    AlertManager, AlertRule, AlertSeverity
)


@pytest.fixture
def temp_storage():
    tmpdir = tempfile.mkdtemp()
    yield tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


# === Metrics Server Tests ===

class TestMetricType:
    def test_metric_types(self):
        assert MetricType.COUNTER.value == "counter"
        assert MetricType.GAUGE.value == "gauge"
        assert MetricType.HISTOGRAM.value == "histogram"


class TestMetricsServerInit:
    def test_init(self, temp_storage):
        server = MetricsServer(storage_path=temp_storage)
        assert server is not None

    def test_default_metrics_initialized(self, temp_storage):
        server = MetricsServer(storage_path=temp_storage)
        assert server.get_counter("swarm_tasks_total") == 0.0
        assert server.get_gauge("swarm_tasks_in_progress") == 0.0


class TestCounter:
    def test_counter_inc(self, temp_storage):
        server = MetricsServer(storage_path=temp_storage)
        server.counter_inc("test_counter")
        server.counter_inc("test_counter")
        assert server.get_counter("test_counter") == 2.0

    def test_counter_inc_with_labels(self, temp_storage):
        server = MetricsServer(storage_path=temp_storage)
        server.counter_inc("test", labels={"env": "prod"})
        server.counter_inc("test", labels={"env": "dev"})
        assert server.get_counter("test", labels={"env": "prod"}) == 1.0
        assert server.get_counter("test", labels={"env": "dev"}) == 1.0


class TestGauge:
    def test_gauge_set(self, temp_storage):
        server = MetricsServer(storage_path=temp_storage)
        server.gauge_set("test_gauge", 42.0)
        assert server.get_gauge("test_gauge") == 42.0

    def test_gauge_inc_dec(self, temp_storage):
        server = MetricsServer(storage_path=temp_storage)
        server.gauge_inc("test_g", 5.0)
        assert server.get_gauge("test_g") == 5.0
        server.gauge_dec("test_g", 2.0)
        assert server.get_gauge("test_g") == 3.0


class TestHistogram:
    def test_histogram_observe(self, temp_storage):
        server = MetricsServer(storage_path=temp_storage)
        server.histogram_observe("test_h", 0.1)
        server.histogram_observe("test_h", 0.5)
        server.histogram_observe("test_h", 2.0)

        hist = server.get_histogram("test_h")
        assert hist.count == 3
        assert hist.sum == 2.6

    def test_histogram_buckets(self, temp_storage):
        server = MetricsServer(storage_path=temp_storage)
        server.histogram_observe("test_h", 0.3)
        hist = server.get_histogram("test_h")
        assert hist.buckets[0.25] == 0
        assert hist.buckets[0.5] == 1


class TestSummary:
    def test_summary_observe(self, temp_storage):
        server = MetricsServer(storage_path=temp_storage)
        for v in [0.1, 0.2, 0.3, 0.4, 0.5]:
            server.summary_observe("test_s", v)
        quantiles = server.get_summary_quantiles("test_s")
        assert quantiles[0.5] >= 0.3


class TestMetricsSnapshot:
    def test_snapshot(self, temp_storage):
        server = MetricsServer(storage_path=temp_storage)
        server.counter_inc("c1")
        server.gauge_set("g1", 10.0)
        snapshot = server.get_snapshot()
        assert "c1" in snapshot.counters
        assert "g1" in snapshot.gauges

    def test_prometheus_export(self, temp_storage):
        server = MetricsServer(storage_path=temp_storage)
        server.counter_inc("c1")
        output = server.export_prometheus()
        assert "c1" in output
        assert "# TYPE" in output


class TestMetricsReset:
    def test_reset(self, temp_storage):
        server = MetricsServer(storage_path=temp_storage)
        server.counter_inc("c1", 10)
        server.reset()
        assert server.get_counter("c1") == 0


# === Event Logger Tests ===

class TestLogLevel:
    def test_levels(self):
        assert LogLevel.INFO.value == "INFO"
        assert LogLevel.ERROR.value == "ERROR"


class TestEventCategory:
    def test_categories(self):
        assert EventCategory.SYSTEM.value == "system"
        assert EventCategory.TASK.value == "task"


class TestEventLoggerInit:
    def test_init(self, temp_storage):
        log_path = f"{temp_storage}/events.jsonl"
        logger = EventLogger(log_file=log_path)
        assert logger is not None


class TestEventLogging:
    def test_log_event(self, temp_storage):
        log_path = f"{temp_storage}/events.jsonl"
        logger = EventLogger(log_file=log_path)
        event = logger.info(EventCategory.SYSTEM, "startup", "Swarm started")
        assert event.level == "INFO"
        assert event.category == "system"

    def test_log_levels(self, temp_storage):
        log_path = f"{temp_storage}/events.jsonl"
        logger = EventLogger(log_file=log_path)
        logger.debug(EventCategory.SYSTEM, "debug_msg", "debug")
        logger.info(EventCategory.TASK, "task_started", "task started")
        logger.warning(EventCategory.AGENT, "agent_warn", "warning")
        logger.error(EventCategory.SECURITY, "sec_error", "error")
        logger.critical(EventCategory.RECOVERY, "crit_fail", "critical")

    def test_log_with_metadata(self, temp_storage):
        log_path = f"{temp_storage}/events.jsonl"
        logger = EventLogger(log_file=log_path)
        event = logger.info(
            EventCategory.TASK, "task_completed", "Task done",
            task_id="t-1", agent_id="a-1",
            metadata={"duration": 5.2}
        )
        assert event.task_id == "t-1"
        assert event.metadata["duration"] == 5.2


class TestEventQuery:
    def test_query_by_level(self, temp_storage):
        log_path = f"{temp_storage}/events.jsonl"
        logger = EventLogger(log_file=log_path)
        logger.info(EventCategory.SYSTEM, "info_msg", "info")
        logger.error(EventCategory.SYSTEM, "error_msg", "error")
        events = logger.query(level=LogLevel.INFO)
        assert all(e.level == "INFO" for e in events)

    def test_query_by_category(self, temp_storage):
        log_path = f"{temp_storage}/events.jsonl"
        logger = EventLogger(log_file=log_path)
        logger.info(EventCategory.TASK, "t1", "task")
        logger.info(EventCategory.AGENT, "a1", "agent")
        events = logger.query(category=EventCategory.TASK)
        assert all(e.category == "task" for e in events)


class TestEventFlush:
    def test_flush(self, temp_storage):
        log_path = Path(f"{temp_storage}/events.jsonl")
        logger = EventLogger(log_file=str(log_path))
        logger.info(EventCategory.SYSTEM, "e1", "msg1")
        logger.info(EventCategory.SYSTEM, "e2", "msg2")
        logger.flush()
        assert log_path.exists()


class TestEventStats:
    def test_stats(self, temp_storage):
        log_path = f"{temp_storage}/events.jsonl"
        logger = EventLogger(log_file=log_path)
        logger.info(EventCategory.TASK, "t1", "msg")
        logger.error(EventCategory.SYSTEM, "e1", "msg")
        stats = logger.get_stats()
        assert stats["total_events"] >= 2


# === Alert Manager Tests ===

class TestAlertSeverity:
    def test_severities(self):
        assert AlertSeverity.INFO.value == "info"
        assert AlertSeverity.CRITICAL.value == "critical"


class TestAlertManagerInit:
    def test_init(self, temp_storage):
        manager = AlertManager(storage_path=temp_storage)
        assert manager is not None
        assert manager.get_stats()["total_rules"] >= 4  # Default rules


class TestAlertRules:
    def test_add_rule(self, temp_storage):
        manager = AlertManager(storage_path=temp_storage)
        rule = AlertRule(
            id="test_rule",
            name="Test Rule",
            description="Test",
            metric_name="test_metric",
            condition="gt",
            threshold=10.0,
            severity=AlertSeverity.WARNING
        )
        manager.add_rule(rule)
        assert manager.get_rule("test_rule") is not None

    def test_remove_rule(self, temp_storage):
        manager = AlertManager(storage_path=temp_storage)
        manager.remove_rule("high_error_rate")
        assert manager.get_rule("high_error_rate") is None

    def test_list_rules(self, temp_storage):
        manager = AlertManager(storage_path=temp_storage)
        rules = manager.list_rules()
        assert len(rules) >= 4


class TestAlertConditions:
    def test_gt_condition(self, temp_storage):
        manager = AlertManager(storage_path=temp_storage)
        # high_error_rate rule has condition "gt" threshold=10 duration=60
        # Just test the condition check directly
        rule = manager.get_rule("high_error_rate")
        assert manager._check_condition(15.0, rule) is True
        assert manager._check_condition(5.0, rule) is False

    def test_lt_condition(self, temp_storage):
        manager = AlertManager(storage_path=temp_storage)
        rule = AlertRule(
            id="lt_test",
            name="LT Test",
            description="test",
            metric_name="x",
            condition="lt",
            threshold=10.0,
            severity=AlertSeverity.WARNING,
            duration_seconds=0
        )
        assert manager._check_condition(5.0, rule) is True
        assert manager._check_condition(15.0, rule) is False


class TestAlertTriggering:
    def test_evaluate_triggers_alert(self, temp_storage):
        manager = AlertManager(storage_path=temp_storage)
        # duration_seconds=0 means instant trigger
        # Use a custom rule with duration=0
        rule = AlertRule(
            id="instant_alert",
            name="Instant Alert",
            description="test",
            metric_name="test_metric",
            condition="gt",
            threshold=5.0,
            severity=AlertSeverity.WARNING,
            duration_seconds=0
        )
        manager.add_rule(rule)

        triggered = manager.evaluate("test_metric", 10.0)
        assert len(triggered) >= 1
        assert triggered[0].severity == AlertSeverity.WARNING

    def test_evaluate_no_trigger_below_threshold(self, temp_storage):
        manager = AlertManager(storage_path=temp_storage)
        rule = AlertRule(
            id="no_trigger",
            name="No Trigger",
            description="test",
            metric_name="x",
            condition="gt",
            threshold=100.0,
            severity=AlertSeverity.INFO,
            duration_seconds=0
        )
        manager.add_rule(rule)
        triggered = manager.evaluate("x", 50.0)
        assert len(triggered) == 0


class TestAlertResolution:
    def test_manual_resolve(self, temp_storage):
        manager = AlertManager(storage_path=temp_storage)
        rule = AlertRule(
            id="resolve_test",
            name="Resolve Test",
            description="test",
            metric_name="x",
            condition="gt",
            threshold=5.0,
            severity=AlertSeverity.INFO,
            duration_seconds=0
        )
        manager.add_rule(rule)
        triggered = manager.evaluate("x", 10.0)
        alert_id = triggered[0].id
        assert manager.resolve_alert(alert_id) is True

    def test_silence_alert(self, temp_storage):
        manager = AlertManager(storage_path=temp_storage)
        rule = AlertRule(
            id="silence_test",
            name="Silence Test",
            description="test",
            metric_name="x",
            condition="gt",
            threshold=5.0,
            severity=AlertSeverity.INFO,
            duration_seconds=0
        )
        manager.add_rule(rule)
        triggered = manager.evaluate("x", 10.0)
        alert_id = triggered[0].id
        assert manager.silence_alert(alert_id, duration_seconds=600) is True


class TestAlertStats:
    def test_stats(self, temp_storage):
        manager = AlertManager(storage_path=temp_storage)
        rule = AlertRule(
            id="stats_test",
            name="Stats Test",
            description="test",
            metric_name="x",
            condition="gt",
            threshold=5.0,
            severity=AlertSeverity.INFO,
            duration_seconds=0
        )
        manager.add_rule(rule)
        manager.evaluate("x", 10.0)
        stats = manager.get_stats()
        assert stats["total_alerts"] >= 1


class TestAlertHistory:
    def test_get_history(self, temp_storage):
        manager = AlertManager(storage_path=temp_storage)
        rule = AlertRule(
            id="history_test",
            name="History Test",
            description="test",
            metric_name="x",
            condition="gt",
            threshold=5.0,
            severity=AlertSeverity.INFO,
            duration_seconds=0
        )
        manager.add_rule(rule)
        manager.evaluate("x", 10.0)
        history = manager.get_alert_history()
        assert len(history) >= 1


class TestSingleton:
    def test_get_metrics_server(self):
        from swarm.observability.metrics_server import get_metrics_server
        s = get_metrics_server()
        assert isinstance(s, MetricsServer)

    def test_get_event_logger(self):
        from swarm.observability.event_logger import get_event_logger
        l = get_event_logger()
        assert isinstance(l, EventLogger)

    def test_get_alert_manager(self):
        from swarm.observability.alert_manager import get_alert_manager
        m = get_alert_manager()
        assert isinstance(m, AlertManager)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
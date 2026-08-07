"""
Swarm Observability - Metrics, Logging, Alerting
Production-grade observability for the swarm system.
"""

from .metrics_server import (
    MetricsServer,
    MetricType,
    MetricPoint,
    HistogramData,
    MetricsSnapshot,
    get_metrics_server
)
from .event_logger import (
    EventLogger,
    LogEvent,
    LogLevel,
    EventCategory,
    LoggerStats,
    get_event_logger
)
from .alert_manager import (
    AlertManager,
    AlertRule,
    Alert,
    AlertSeverity,
    AlertStatus,
    AlertStats,
    get_alert_manager
)

__all__ = [
    # Week 12: Metrics + Logging + Alerting
    "MetricsServer",
    "MetricType",
    "MetricPoint",
    "HistogramData",
    "MetricsSnapshot",
    "get_metrics_server",
    "EventLogger",
    "LogEvent",
    "LogLevel",
    "EventCategory",
    "LoggerStats",
    "get_event_logger",
    "AlertManager",
    "AlertRule",
    "Alert",
    "AlertSeverity",
    "AlertStatus",
    "AlertStats",
    "get_alert_manager",
]

__version__ = "3.0.0"
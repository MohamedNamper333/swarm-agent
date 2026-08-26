"""
Metrics Server Module - Prometheus-style Metrics Collection
Tracks counters, gauges, histograms, and summaries for swarm observability.
"""
import time
import threading
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import math

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of metrics"""
    COUNTER = "counter"          # Monotonically increasing
    GAUGE = "gauge"              # Can go up or down
    HISTOGRAM = "histogram"      # Distribution of values
    SUMMARY = "summary"          # Quantiles


@dataclass
class MetricPoint:
    """A single metric data point"""
    name: str
    type: MetricType
    value: float
    timestamp: float
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class HistogramData:
    """Histogram data with buckets"""
    count: int = 0
    sum: float = 0.0
    buckets: Dict[float, int] = field(default_factory=dict)  # upper bound -> count
    min: float = float("inf")
    max: float = float("-inf")


@dataclass
class MetricsSnapshot:
    """Snapshot of all metrics"""
    timestamp: str
    counters: Dict[str, float]
    gauges: Dict[str, float]
    histograms: Dict[str, Dict[str, Any]]
    summaries: Dict[str, Dict[str, Any]]


class MetricsServer:
    """
    In-memory metrics collection with Prometheus-compatible export.
    Thread-safe counter/gauge/histogram tracking.
    """

    def __init__(self, storage_path: str = "swarm/observability/metrics"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

        self.counters: Dict[str, float] = defaultdict(float)
        self.gauges: Dict[str, float] = defaultdict(float)
        self.histograms: Dict[str, HistogramData] = {}
        self.summaries: Dict[str, List[float]] = defaultdict(list)
        self.metric_labels: Dict[str, Dict[str, str]] = {}

        # Default histogram buckets (Prometheus-style)
        self.default_buckets = [
            0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0
        ]

        # Standard swarm metrics
        self._init_default_metrics()

    def _init_default_metrics(self) -> None:
        """Initialize standard swarm metrics"""
        defaults = [
            ("swarm_tasks_total", MetricType.COUNTER),
            ("swarm_tasks_completed", MetricType.COUNTER),
            ("swarm_tasks_failed", MetricType.COUNTER),
            ("swarm_tasks_in_progress", MetricType.GAUGE),
            ("swarm_task_duration_seconds", MetricType.HISTOGRAM),
            ("swarm_agent_state_transitions", MetricType.COUNTER),
            ("swarm_api_requests_total", MetricType.COUNTER),
            ("swarm_api_request_duration", MetricType.HISTOGRAM),
            ("swarm_constitutional_violations", MetricType.COUNTER),
            ("swarm_rate_limit_denied", MetricType.COUNTER),
            ("swarm_retry_attempts", MetricType.COUNTER),
            ("swarm_recovery_events", MetricType.COUNTER),
            ("swarm_active_snapshots", MetricType.GAUGE),
            ("swarm_queue_depth", MetricType.GAUGE),
        ]
        for name, mtype in defaults:
            if mtype == MetricType.HISTOGRAM and name not in self.histograms:
                self.histograms[name] = HistogramData(
                    buckets={b: 0 for b in self.default_buckets}
                )

    def counter_inc(
        self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Increment a counter"""
        with self._lock:
            key = self._make_key(name, labels)
            self.counters[key] += value
            if labels:
                self.metric_labels[key] = labels

    def gauge_set(
        self, name: str, value: float, labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Set a gauge value"""
        with self._lock:
            key = self._make_key(name, labels)
            self.gauges[key] = value
            if labels:
                self.metric_labels[key] = labels

    def gauge_inc(
        self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Increment a gauge"""
        with self._lock:
            key = self._make_key(name, labels)
            self.gauges[key] += value
            if labels:
                self.metric_labels[key] = labels

    def gauge_dec(
        self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Decrement a gauge"""
        with self._lock:
            key = self._make_key(name, labels)
            self.gauges[key] -= value
            if labels:
                self.metric_labels[key] = labels

    def histogram_observe(
        self, name: str, value: float, labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Record a value in a histogram"""
        with self._lock:
            key = self._make_key(name, labels)
            if key not in self.histograms:
                self.histograms[key] = HistogramData(
                    buckets={b: 0 for b in self.default_buckets}
                )
            hist = self.histograms[key]
            hist.count += 1
            hist.sum += value
            hist.min = min(hist.min, value)
            hist.max = max(hist.max, value)
            for bucket_upper in self.default_buckets:
                if value <= bucket_upper:
                    hist.buckets[bucket_upper] += 1
            if labels:
                self.metric_labels[key] = labels

    def summary_observe(
        self, name: str, value: float, labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Record a value in a summary"""
        with self._lock:
            key = self._make_key(name, labels)
            self.summaries[key].append(value)
            # Keep last 1000 observations
            if len(self.summaries[key]) > 1000:
                self.summaries[key] = self.summaries[key][-1000:]
            if labels:
                self.metric_labels[key] = labels

    def get_counter(self, name: str, labels: Optional[Dict[str, str]] = None) -> float:
        """Get counter value"""
        with self._lock:
            return self.counters.get(self._make_key(name, labels), 0.0)

    def get_gauge(self, name: str, labels: Optional[Dict[str, str]] = None) -> float:
        """Get gauge value"""
        with self._lock:
            return self.gauges.get(self._make_key(name, labels), 0.0)

    def get_histogram(self, name: str, labels: Optional[Dict[str, str]] = None) -> Optional[HistogramData]:
        """Get histogram data"""
        with self._lock:
            return self.histograms.get(self._make_key(name, labels))

    def get_summary_quantiles(
        self, name: str, quantiles: List[float] = None,
        labels: Optional[Dict[str, str]] = None
    ) -> Dict[str, float]:
        """Get summary quantiles"""
        if quantiles is None:
            quantiles = [0.5, 0.9, 0.95, 0.99]
        with self._lock:
            values = self.summaries.get(self._make_key(name, labels), [])
            if not values:
                return {q: 0.0 for q in quantiles}
            sorted_values = sorted(values)
            result = {}
            for q in quantiles:
                idx = int(q * len(sorted_values))
                idx = min(idx, len(sorted_values) - 1)
                result[q] = sorted_values[idx]
            return result

    def get_snapshot(self) -> MetricsSnapshot:
        """Get snapshot of all metrics"""
        with self._lock:
            histograms = {}
            for name, hist in self.histograms.items():
                histograms[name] = {
                    "count": hist.count,
                    "sum": hist.sum,
                    "min": hist.min if hist.min != float("inf") else 0.0,
                    "max": hist.max if hist.max != float("-inf") else 0.0,
                    "buckets": dict(hist.buckets)
                }
            summaries = {}
            for name, values in self.summaries.items():
                quantiles = self.get_summary_quantiles(name)
                summaries[name] = {
                    "count": len(values),
                    "quantiles": quantiles
                }
            return MetricsSnapshot(
                timestamp=datetime.now(timezone.utc).isoformat(),
                counters=dict(self.counters),
                gauges=dict(self.gauges),
                histograms=histograms,
                summaries=summaries
            )

    def export_prometheus(self) -> str:
        """Export metrics in Prometheus text format"""
        snapshot = self.get_snapshot()
        lines = []

        for name, value in snapshot.counters.items():
            lines.append(f"# TYPE {self._extract_name(name)} counter")
            lines.append(f"{name} {value}")

        for name, value in snapshot.gauges.items():
            lines.append(f"# TYPE {self._extract_name(name)} gauge")
            lines.append(f"{name} {value}")

        for name, hist in snapshot.histograms.items():
            lines.append(f"# TYPE {self._extract_name(name)} histogram")
            lines.append(f"{name}_count {hist['count']}")
            lines.append(f"{name}_sum {hist['sum']}")
            for bucket_upper, count in hist["buckets"].items():
                lines.append(f'{name}_bucket{{le="{bucket_upper}"}} {count}')

        for name, summary in snapshot.summaries.items():
            lines.append(f"# TYPE {self._extract_name(name)} summary")
            lines.append(f"{name}_count {summary['count']}")
            for q, v in summary["quantiles"].items():
                lines.append(f'{name}{{quantile="{q}"}} {v}')

        return "\n".join(lines)

    def reset(self) -> None:
        """Reset all metrics (for testing)"""
        with self._lock:
            self.counters.clear()
            self.gauges.clear()
            self.histograms.clear()
            self.summaries.clear()
            self.metric_labels.clear()
            self._init_default_metrics()

    def _make_key(self, name: str, labels: Optional[Dict[str, str]]) -> str:
        """Make metric key with labels"""
        if not labels:
            return name
        label_str = ",".join(
            f'{k}="{v}"' for k, v in sorted(labels.items())
        )
        return f"{name}{{{label_str}}}"

    def _extract_name(self, key: str) -> str:
        """Extract metric name from key"""
        return key.split("{")[0]


# Module-level singleton
_default_server: Optional[MetricsServer] = None


def get_metrics_server() -> MetricsServer:
    """Get or create the default metrics server"""
    global _default_server
    if _default_server is None:
        _default_server = MetricsServer()
    return _default_server
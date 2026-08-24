"""
Observability - Unified metrics, tracing, logging, and alerting.
"""

import threading
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from collections import defaultdict
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def uuidv7() -> str:
    return str(uuid.uuid4())


# =============================================================================
# Metrics Models
# =============================================================================

class MetricType(str, Enum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class MetricLabel:
    name: str
    value: str


@dataclass
class MetricPoint:
    timestamp: datetime
    value: float
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class Metric:
    name: str
    metric_type: MetricType
    description: str = ""
    unit: str = ""
    labels: List[str] = field(default_factory=list)
    points: List[MetricPoint] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# =============================================================================
# In-Memory Metrics Registry
# =============================================================================

class MetricsRegistry:
    """Thread-safe metrics registry with Prometheus-compatible interface."""
    
    def __init__(self):
        self._metrics: Dict[str, Metric] = {}
        self._lock = threading.RLock()
        
        # Histogram buckets for latency measurements
        self._default_buckets = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
    
    def _make_key(self, name: str, labels: Dict[str, str]) -> str:
        """Create unique key for metric with labels."""
        if not labels:
            return name
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"
    
    def counter(
        self,
        name: str,
        description: str = "",
        labels: Optional[Dict[str, str]] = None,
    ) -> "Counter":
        """Create or get a counter metric."""
        key = self._make_key(name, labels or {})
        with self._lock:
            if key not in self._metrics:
                self._metrics[key] = Metric(
                    name=name,
                    metric_type=MetricType.COUNTER,
                    description=description,
                    labels=list(labels.keys()) if labels else [],
                )
            return Counter(self, name, labels or {})
    
    def gauge(
        self,
        name: str,
        description: str = "",
        labels: Optional[Dict[str, str]] = None,
    ) -> "Gauge":
        """Create or get a gauge metric."""
        key = self._make_key(name, labels or {})
        with self._lock:
            if key not in self._metrics:
                self._metrics[key] = Metric(
                    name=name,
                    metric_type=MetricType.GAUGE,
                    description=description,
                    labels=list(labels.keys()) if labels else [],
                )
            return Gauge(self, name, labels or {})
    
    def histogram(
        self,
        name: str,
        description: str = "",
        labels: Optional[Dict[str, str]] = None,
        buckets: Optional[List[float]] = None,
    ) -> "Histogram":
        """Create or get a histogram metric."""
        key = self._make_key(name, labels or {})
        with self._lock:
            if key not in self._metrics:
                self._metrics[key] = Metric(
                    name=name,
                    metric_type=MetricType.HISTOGRAM,
                    description=description,
                    labels=list(labels.keys()) if labels else [],
                )
            return Histogram(self, name, labels or {}, buckets or self._default_buckets)
    
    def get_metric(self, name: str, labels: Optional[Dict[str, str]] = None) -> Optional[Metric]:
        """Get metric by name and labels."""
        key = self._make_key(name, labels or {})
        with self._lock:
            return self._metrics.get(key)
    
    def get_all_metrics(self) -> List[Metric]:
        """Get all metrics."""
        with self._lock:
            return list(self._metrics.values())
    
    def reset(self) -> None:
        """Reset all metrics."""
        with self._lock:
            self._metrics.clear()


# =============================================================================
# Metric Wrappers
# =============================================================================

class Counter:
    """Counter metric wrapper."""
    
    def __init__(self, registry: MetricsRegistry, name: str, labels: Dict[str, str]):
        self.registry = registry
        self.name = name
        self.labels = labels
    
    def inc(self, value: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        """Increment counter."""
        merged_labels = {**self.labels, **(labels or {})}
        key = self.registry._make_key(self.name, merged_labels)
        with self.registry._lock:
            metric = self.registry._metrics.get(key)
            if not metric:
                return
            point = MetricPoint(
                timestamp=now_utc(),
                value=value,
                labels=merged_labels,
            )
            metric.points.append(point)
    
    def get_value(self, labels: Optional[Dict[str, str]] = None) -> float:
        """Get current counter value."""
        merged_labels = {**self.labels, **(labels or {})}
        key = self.registry._make_key(self.name, merged_labels)
        with self.registry._lock:
            metric = self.registry._metrics.get(key)
            if not metric:
                return 0.0
            return sum(p.value for p in metric.points)


class Gauge:
    """Gauge metric wrapper."""
    
    def __init__(self, registry: MetricsRegistry, name: str, labels: Dict[str, str]):
        self.registry = registry
        self.name = name
        self.labels = labels
    
    def set(self, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Set gauge value."""
        merged_labels = {**self.labels, **(labels or {})}
        key = self.registry._make_key(self.name, merged_labels)
        with self.registry._lock:
            metric = self.registry._metrics.get(key)
            if not metric:
                return
            point = MetricPoint(
                timestamp=now_utc(),
                value=value,
                labels=merged_labels,
            )
            metric.points = [point]  # Gauge keeps only latest
    
    def inc(self, value: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        """Increment gauge."""
        merged_labels = {**self.labels, **(labels or {})}
        key = self.registry._make_key(self.name, merged_labels)
        with self.registry._lock:
            metric = self.registry._metrics.get(key)
            if not metric:
                return
            current = metric.points[-1].value if metric.points else 0.0
            point = MetricPoint(
                timestamp=now_utc(),
                value=current + value,
                labels=merged_labels,
            )
            metric.points = [point]
    
    def dec(self, value: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        """Decrement gauge."""
        self.inc(-value, labels)
    
    def get_value(self, labels: Optional[Dict[str, str]] = None) -> float:
        """Get current gauge value."""
        merged_labels = {**self.labels, **(labels or {})}
        key = self.registry._make_key(self.name, merged_labels)
        with self.registry._lock:
            metric = self.registry._metrics.get(key)
            if not metric or not metric.points:
                return 0.0
            return metric.points[-1].value


class Histogram:
    """Histogram metric wrapper with bucketed observations."""
    
    def __init__(
        self,
        registry: MetricsRegistry,
        name: str,
        labels: Dict[str, str],
        buckets: List[float],
    ):
        self.registry = registry
        self.name = name
        self.labels = labels
        self.buckets = sorted(buckets)
    
    def observe(self, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Record an observation."""
        merged_labels = {**self.labels, **(labels or {})}
        key = self.registry._make_key(self.name, merged_labels)
        with self.registry._lock:
            metric = self.registry._metrics.get(key)
            if not metric:
                return
            
            # Add to buckets
            for bucket in self.buckets:
                bucket_key = f"{key}_bucket_{bucket}"
                bucket_metric = self.registry._metrics.get(bucket_key)
                if not bucket_metric:
                    bucket_metric = Metric(
                        name=f"{self.name}_bucket",
                        metric_type=MetricType.COUNTER,
                        description=f"Bucket for {self.name}",
                    )
                    self.registry._metrics[bucket_key] = bucket_metric
                
                if value <= bucket:
                    bucket_metric.points.append(MetricPoint(
                        timestamp=now_utc(),
                        value=1.0,
                        labels=merged_labels,
                    ))
            
            # Also record sum and count
            sum_key = f"{key}_sum"
            sum_metric = self.registry._metrics.get(sum_key)
            if not sum_metric:
                sum_metric = Metric(
                    name=f"{self.name}_sum",
                    metric_type=MetricType.COUNTER,
                )
                self.registry._metrics[sum_key] = sum_metric
            sum_metric.points.append(MetricPoint(
                timestamp=now_utc(),
                value=value,
                labels=merged_labels,
            ))
            
            count_key = f"{key}_count"
            count_metric = self.registry._metrics.get(count_key)
            if not count_metric:
                count_metric = Metric(
                    name=f"{self.name}_count",
                    metric_type=MetricType.COUNTER,
                )
                self.registry._metrics[count_key] = count_metric
            count_metric.points.append(MetricPoint(
                timestamp=now_utc(),
                value=1.0,
                labels=merged_labels,
            ))
    
    def get_quantile(self, quantile: float, labels: Optional[Dict[str, str]] = None) -> float:
        """Estimate quantile from buckets (approximate)."""
        # Simplified - in production use proper quantile estimation
        merged_labels = {**self.labels, **(labels or {})}
        key = self.registry._make_key(self.name, merged_labels)
        
        with self.registry._lock:
            # Get count
            count_key = f"{key}_count"
            count_metric = self.registry._metrics.get(count_key)
            if not count_metric:
                return 0.0
            
            total_count = sum(p.value for p in count_metric.points)
            if total_count == 0:
                return 0.0
            
            # Simple bucket-based estimation
            target_count = total_count * quantile
            cumulative = 0.0
            
            for bucket in self.buckets:
                bucket_key = f"{self.name}{{}}_bucket_{bucket}".format(
                    ",".join(f"{k}={v}" for k, v in sorted(self.labels.items()))
                )
                bucket_metric = self.registry._metrics.get(bucket_key)
                if bucket_metric:
                    cumulative += sum(p.value for p in bucket_metric.points)
                    if cumulative >= target_count:
                        return bucket
            
            return self.buckets[-1] if self.buckets else 0.0


# =============================================================================
# Standard Application Metrics
# =============================================================================

class StandardMetrics:
    """Pre-defined metrics for common application patterns."""
    
    def __init__(self, registry: MetricsRegistry, prefix: str = "app"):
        self.registry = registry
        self.prefix = prefix
        
        # HTTP metrics
        self.http_requests_total = registry.counter(
            f"{prefix}_http_requests_total",
            "Total HTTP requests",
            labels={},
        )
        self.http_request_duration = registry.histogram(
            f"{prefix}_http_request_duration_seconds",
            "HTTP request latency",
            buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
        )
        self.http_requests_in_flight = registry.gauge(
            f"{prefix}_http_requests_in_flight",
            "HTTP requests currently being processed",
        )
        
        # Job/Task metrics
        self.jobs_enqueued_total = registry.counter(
            f"{prefix}_jobs_enqueued_total",
            "Total jobs enqueued",
        )
        self.jobs_started_total = registry.counter(
            f"{prefix}_jobs_started_total",
            "Total jobs started",
        )
        self.jobs_completed_total = registry.counter(
            f"{prefix}_jobs_completed_total",
            "Total jobs completed successfully",
        )
        self.jobs_failed_total = registry.counter(
            f"{prefix}_jobs_failed_total",
            "Total jobs failed",
        )
        self.job_duration = registry.histogram(
            f"{prefix}_job_duration_seconds",
            "Job execution duration",
        )
        self.job_queue_depth = registry.gauge(
            f"{prefix}_job_queue_depth",
            "Current job queue depth",
        )
        
        # Memory metrics
        self.memory_entries_total = registry.gauge(
            f"{prefix}_memory_entries_total",
            "Total memory entries",
        )
        self.memory_search_duration = registry.histogram(
            f"{prefix}_memory_search_duration_seconds",
            "Memory search duration",
        )
        
        # Agent metrics
        self.agent_tasks_total = registry.counter(
            f"{prefix}_agent_tasks_total",
            "Total agent tasks executed",
        )
        self.agent_task_duration = registry.histogram(
            f"{prefix}_agent_task_duration_seconds",
            "Agent task execution duration",
        )
        self.agent_active = registry.gauge(
            f"{prefix}_agent_active",
            "Currently active agents",
        )
        
        # Workflow metrics
        self.workflow_started_total = registry.counter(
            f"{prefix}_workflow_started_total",
            "Total workflows started",
        )
        self.workflow_completed_total = registry.counter(
            f"{prefix}_workflow_completed_total",
            "Total workflows completed",
        )
        self.workflow_failed_total = registry.counter(
            f"{prefix}_workflow_failed_total",
            "Total workflows failed",
        )
        self.workflow_duration = registry.histogram(
            f"{prefix}_workflow_duration_seconds",
            "Workflow execution duration",
        )
        self.workflow_compensations_total = registry.counter(
            f"{prefix}_workflow_compensations_total",
            "Total workflow compensations executed",
        )
        
        # Cache metrics
        self.cache_hits_total = registry.counter(
            f"{prefix}_cache_hits_total",
            "Total cache hits",
        )
        self.cache_misses_total = registry.counter(
            f"{prefix}_cache_misses_total",
            "Total cache misses",
        )
        self.cache_size = registry.gauge(
            f"{prefix}_cache_size",
            "Current cache size",
        )
        
        # Error metrics
        self.errors_total = registry.counter(
            f"{prefix}_errors_total",
            "Total errors",
        )


# =============================================================================
# Prometheus Export
# =============================================================================

class PrometheusExporter:
    """Export metrics in Prometheus text format."""
    
    def __init__(self, registry: MetricsRegistry):
        self.registry = registry
    
    def export(self) -> str:
        """Export all metrics in Prometheus text format."""
        lines = []
        metrics = self.registry.get_all_metrics()
        
        for metric in metrics:
            if metric.metric_type == MetricType.COUNTER:
                lines.append(f"# TYPE {metric.name} counter")
            elif metric.metric_type == MetricType.GAUGE:
                lines.append(f"# TYPE {metric.name} gauge")
            elif metric.metric_type == MetricType.HISTOGRAM:
                lines.append(f"# TYPE {metric.name} histogram")
            
            if metric.description:
                lines.append(f"# HELP {metric.name} {metric.description}")
            
            # Group points by labels
            points_by_labels: Dict[str, List[MetricPoint]] = defaultdict(list)
            for point in metric.points:
                label_key = ",".join(f"{k}={v}" for k, v in sorted(point.labels.items()))
                points_by_labels[label_key].append(point)
            
            for label_key, points in points_by_labels.items():
                label_str = f"{{{label_key}}}" if label_key else ""
                
                if metric.metric_type in (MetricType.COUNTER, MetricType.GAUGE):
                    # Use latest value for gauge, sum for counter
                    if metric.metric_type == MetricType.GAUGE:
                        value = points[-1].value
                    else:
                        value = sum(p.value for p in points)
                    lines.append(f"{metric.name}{label_str} {value}")
                elif metric.metric_type == MetricType.HISTOGRAM:
                    # Export buckets
                    bucket_values = defaultdict(float)
                    for point in points:
                        if "_bucket_" in point.labels.get("__bucket__", ""):
                            bucket = point.labels.get("__bucket__", "").replace("_bucket_", "")
                            bucket_val = float(bucket) if bucket.replace(".", "").isdigit() else 0
                            if bucket_val > 0:
                                lines.append(f"{metric.name}_bucket{{le=\"{bucket_val}\"{',' + label_key if label_key else ''}}} {point.value}")
                    
                    # Sum and count
                    lines.append(f"{metric.name}_sum{{{label_key[1:-1] if label_key else ''}}} {sum(p.value for p in points)}")
                    lines.append(f"{metric.name}_count{{{label_key[1:-1] if label_key else ''}}} {len(points)}")
        
        return "\n".join(lines) + "\n"


# =============================================================================
# Metrics Middleware
# =============================================================================

class MetricsMiddleware:
    """Middleware to automatically collect HTTP metrics."""
    
    def __init__(self, registry: MetricsRegistry, prefix: str = "app"):
        self.registry = registry
        self.prefix = prefix
        
        # Create standard metrics
        self.metrics = StandardMetrics(registry, prefix)
    
    @contextmanager
    def track_request(self, method: str, path: str, status_code: int = 200):
        """Context manager to track HTTP request."""
        start = time.time()
        labels = {
            "method": method,
            "path": path,
            "status": str(status_code),
        }
        
        self.metrics.http_requests_in_flight.inc(labels=labels)
        
        try:
            yield
        except Exception:
            status_code = 500
            raise
        finally:
            duration = time.time() - start
            labels["status"] = str(status_code)
            self.metrics.http_requests_total.inc(labels=labels)
            self.metrics.http_request_duration.observe(duration, labels=labels)
            self.metrics.http_requests_in_flight.dec(labels=labels)
    
    @contextmanager
    def track_job(self, job_type: str, tenant_id: str = "default"):
        """Context manager to track job execution."""
        start = time.time()
        labels = {
            "job_type": job_type,
            "tenant_id": tenant_id,
        }
        
        self.metrics.jobs_started_total.inc(labels=labels)
        
        try:
            yield
            self.metrics.jobs_completed_total.inc(labels=labels)
        except Exception:
            self.metrics.jobs_failed_total.inc(labels=labels)
            raise
        finally:
            duration = time.time() - start
            self.metrics.job_duration.observe(duration, labels=labels)
    
    @contextmanager
    def track_agent_task(self, agent_type: str, capability: str):
        """Context manager to track agent task."""
        start = time.time()
        labels = {
            "agent_type": agent_type,
            "capability": capability,
        }
        
        self.metrics.agent_tasks_total.inc(labels=labels)
        self.metrics.agent_active.inc(labels=labels)
        
        try:
            yield
        finally:
            duration = time.time() - start
            self.metrics.agent_task_duration.observe(duration, labels=labels)
            self.metrics.agent_active.dec(labels=labels)


# =============================================================================
# Global Registry
# =============================================================================

_global_registry: Optional[MetricsRegistry] = None
_global_lock = threading.Lock()


def get_metrics_registry() -> MetricsRegistry:
    """Get global metrics registry."""
    global _global_registry
    with _global_lock:
        if _global_registry is None:
            _global_registry = MetricsRegistry()
        return _global_registry


def get_standard_metrics(prefix: str = "app") -> StandardMetrics:
    """Get standard metrics for application."""
    registry = get_metrics_registry()
    return StandardMetrics(registry, prefix)


def get_prometheus_exporter() -> PrometheusExporter:
    """Get Prometheus exporter."""
    registry = get_metrics_registry()
    return PrometheusExporter(registry)


# =============================================================================
# Factory
# =============================================================================

def create_metrics_registry() -> MetricsRegistry:
    """Create a new metrics registry."""
    return MetricsRegistry()

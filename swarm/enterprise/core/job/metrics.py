"""
Metrics & Observability - Prometheus metrics for job system.
"""

import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Callable
from collections import defaultdict
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)

# Try to import prometheus_client
try:
    from prometheus_client import (
        Counter, Gauge, Histogram, Summary, Info,
        CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST,
        REGISTRY,
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.warning("prometheus_client not installed, metrics will be no-op")


# =============================================================================
# Metrics Registry
# =============================================================================

class MetricsRegistry:
    """Central metrics registry with optional Prometheus backend."""
    
    def __init__(self, registry: Optional[Any] = None, namespace: str = "swarm_jobs"):
        self.namespace = namespace
        self._metrics: Dict[str, Any] = {}
        self._lock = threading.RLock()
        
        if PROMETHEUS_AVAILABLE:
            self._prom_registry = registry or REGISTRY
        else:
            self._prom_registry = None
    
    def _get_or_create(self, name: str, factory: Callable) -> Any:
        """Get or create a metric."""
        with self._lock:
            if name not in self._metrics:
                self._metrics[name] = factory()
            return self._metrics[name]


# =============================================================================
# Job Metrics
# =============================================================================

class JobMetrics:
    """Metrics for job execution."""
    
    def __init__(self, registry: MetricsRegistry):
        self.registry = registry
        
        # Counters
        self.jobs_enqueued = self._counter(
            "jobs_enqueued_total",
            "Total jobs enqueued",
            ["job_type", "tenant_id", "priority"],
        )
        
        self.jobs_started = self._counter(
            "jobs_started_total",
            "Total jobs started",
            ["job_type", "tenant_id", "worker_id"],
        )
        
        self.jobs_succeeded = self._counter(
            "jobs_succeeded_total",
            "Total jobs succeeded",
            ["job_type", "tenant_id", "worker_id"],
        )
        
        self.jobs_failed = self._counter(
            "jobs_failed_total",
            "Total jobs failed",
            ["job_type", "tenant_id", "worker_id", "error_code"],
        )
        
        self.jobs_retried = self._counter(
            "jobs_retried_total",
            "Total jobs retried",
            ["job_type", "tenant_id", "retry_count"],
        )
        
        self.jobs_dead_lettered = self._counter(
            "jobs_dead_lettered_total",
            "Total jobs sent to dead letter queue",
            ["job_type", "tenant_id", "reason"],
        )
        
        # Gauges
        self.jobs_pending = self._gauge(
            "jobs_pending",
            "Currently pending jobs",
            ["job_type", "tenant_id", "priority"],
        )
        
        self.jobs_running = self._gauge(
            "jobs_running",
            "Currently running jobs",
            ["job_type", "tenant_id", "worker_id"],
        )
        
        self.workers_active = self._gauge(
            "workers_active",
            "Active workers",
            ["worker_id", "job_types"],
        )
        
        self.queue_depth = self._gauge(
            "queue_depth",
            "Queue depth by priority",
            ["tenant_id", "priority"],
        )
        
        # Histograms
        self.job_duration = self._histogram(
            "job_duration_seconds",
            "Job execution duration",
            ["job_type", "tenant_id"],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 300.0],
        )
        
        self.job_queue_wait = self._histogram(
            "job_queue_wait_seconds",
            "Time job spent in queue before execution",
            ["job_type", "tenant_id", "priority"],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 300.0],
        )
        
        self.job_retry_delay = self._histogram(
            "job_retry_delay_seconds",
            "Delay before job retry",
            ["job_type", "tenant_id", "retry_count"],
            buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 300.0, 1800.0],
        )
        
        # Worker metrics
        self.worker_jobs_processed = self._counter(
            "worker_jobs_processed_total",
            "Total jobs processed by worker",
            ["worker_id", "job_type", "result"],
        )
        
        self.worker_uptime = self._gauge(
            "worker_uptime_seconds",
            "Worker uptime",
            ["worker_id"],
        )
        
        # Scheduler metrics
        self.scheduled_jobs_executed = self._counter(
            "scheduled_jobs_executed_total",
            "Total scheduled jobs executed",
            ["schedule_type", "tenant_id"],
        )
        
        self.scheduled_jobs_due = self._gauge(
            "scheduled_jobs_due",
            "Scheduled jobs due for execution",
            ["schedule_type", "tenant_id"],
        )
        
        # DLQ metrics
        self.dlq_entries = self._gauge(
            "dlq_entries",
            "Dead letter queue entries",
            ["tenant_id", "reason", "resolved"],
        )
        
        self.dlq_retries = self._counter(
            "dlq_retries_total",
            "Total DLQ retries",
            ["tenant_id", "reason", "attempt"],
        )
        
        # Rate limiter metrics
        self.rate_limit_allowed = self._counter(
            "rate_limit_allowed_total",
            "Rate limit allowed requests",
            ["key", "algorithm"],
        )
        
        self.rate_limit_rejected = self._counter(
            "rate_limit_rejected_total",
            "Rate limit rejected requests",
            ["key", "algorithm"],
        )
        
        self.rate_limit_remaining = self._gauge(
            "rate_limit_remaining",
            "Rate limit remaining tokens/requests",
            ["key", "algorithm"],
        )
        
        # Compensation/Workflow metrics
        self.workflow_started = self._counter(
            "workflow_started_total",
            "Workflows started",
            ["workflow_type", "tenant_id"],
        )
        
        self.workflow_completed = self._counter(
            "workflow_completed_total",
            "Workflows completed",
            ["workflow_type", "tenant_id", "status"],
        )
        
        self.workflow_step_duration = self._histogram(
            "workflow_step_duration_seconds",
            "Workflow step duration",
            ["workflow_type", "step_id"],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
        )
        
        self.workflow_compensations = self._counter(
            "workflow_compensations_total",
            "Workflow compensations executed",
            ["workflow_type", "step_id", "result"],
        )
        
        # System info
        self.info = self._info(
            "build_info",
            "Build information",
        )
    
    def _counter(self, name: str, description: str, labels: List[str]):
        if PROMETHEUS_AVAILABLE:
            return self.registry._get_or_create(
                f"{self.registry.namespace}_{name}",
                lambda: Counter(
                    f"{self.registry.namespace}_{name}",
                    description,
                    labels,
                    registry=self.registry._prom_registry,
                )
            )
        return NoOpCounter(labels)
    
    def _gauge(self, name: str, description: str, labels: List[str]):
        if PROMETHEUS_AVAILABLE:
            return self.registry._get_or_create(
                f"{self.registry.namespace}_{name}",
                lambda: Gauge(
                    f"{self.registry.namespace}_{name}",
                    description,
                    labels,
                    registry=self.registry._prom_registry,
                )
            )
        return NoOpGauge(labels)
    
    def _histogram(self, name: str, description: str, labels: List[str], buckets: List[float]):
        if PROMETHEUS_AVAILABLE:
            return self.registry._get_or_create(
                f"{self.registry.namespace}_{name}",
                lambda: Histogram(
                    f"{self.registry.namespace}_{name}",
                    description,
                    labels,
                    buckets=buckets,
                    registry=self.registry._prom_registry,
                )
            )
        return NoOpHistogram(labels)
    
    def _info(self, name: str, description: str):
        if PROMETHEUS_AVAILABLE:
            return self.registry._get_or_create(
                f"{self.registry.namespace}_{name}",
                lambda: Info(
                    f"{self.registry.namespace}_{name}",
                    description,
                    registry=self.registry._prom_registry,
                )
            )
        return NoOpInfo()


# =============================================================================
# No-op implementations (when Prometheus not available)
# =============================================================================

class NoOpCounter:
    def __init__(self, labels: List[str]):
        self.labels = labels
        self._counts: Dict[str, float] = defaultdict(float)
    
    def labels(self, **kwargs):
        key = tuple(sorted(kwargs.items()))
        return NoOpCounterLabels(self._counts, key)
    
    def inc(self, amount: float = 1):
        pass


class NoOpCounterLabels:
    def __init__(self, counts: Dict, key: tuple):
        self._counts = counts
        self._key = key
    
    def inc(self, amount: float = 1):
        self._counts[self._key] += amount


class NoOpGauge:
    def __init__(self, labels: List[str]):
        self.labels = labels
        self._values: Dict[str, float] = defaultdict(float)
    
    def labels(self, **kwargs):
        key = tuple(sorted(kwargs.items()))
        return NoOpGaugeLabels(self._values, key)
    
    def set(self, value: float):
        pass
    
    def inc(self, amount: float = 1):
        pass
    
    def dec(self, amount: float = 1):
        pass


class NoOpGaugeLabels:
    def __init__(self, values: Dict, key: tuple):
        self._values = values
        self._key = key
    
    def set(self, value: float):
        self._values[self._key] = value
    
    def inc(self, amount: float = 1):
        self._values[self._key] += amount
    
    def dec(self, amount: float = 1):
        self._values[self._key] -= amount


class NoOpHistogram:
    def __init__(self, labels: List[str]):
        self.labels = labels
        self._values: Dict[str, List[float]] = defaultdict(list)
    
    def labels(self, **kwargs):
        key = tuple(sorted(kwargs.items()))
        return NoOpHistogramLabels(self._values, key)
    
    def observe(self, value: float):
        pass


class NoOpHistogramLabels:
    def __init__(self, values: Dict, key: tuple):
        self._values = values
        self._key = key
    
    def observe(self, value: float):
        self._values[self._key].append(value)


class NoOpInfo:
    def __init__(self):
        self._info = {}
    
    def info(self, data: Dict[str, str]):
        self._info = data


# =============================================================================
# Convenience Functions
# =============================================================================

@contextmanager
def track_job_duration(metrics: JobMetrics, job_type: str, tenant_id: str):
    """Context manager to track job duration."""
    start = time.time()
    try:
        yield
    finally:
        duration = time.time() - start
        if PROMETHEUS_AVAILABLE:
            metrics.job_duration.labels(job_type=job_type, tenant_id=tenant_id).observe(duration)


@contextmanager
def track_workflow_step(metrics: JobMetrics, workflow_type: str, step_id: str):
    """Context manager to track workflow step duration."""
    start = time.time()
    try:
        yield
    finally:
        duration = time.time() - start
        if PROMETHEUS_AVAILABLE:
            metrics.workflow_step_duration.labels(
                workflow_type=workflow_type, step_id=step_id
            ).observe(duration)


def record_job_enqueued(metrics: JobMetrics, job_type: str, tenant_id: str, priority: str):
    """Record job enqueued."""
    if PROMETHEUS_AVAILABLE:
        metrics.jobs_enqueued.labels(
            job_type=job_type, tenant_id=tenant_id, priority=priority
        ).inc()


def record_job_started(metrics: JobMetrics, job_type: str, tenant_id: str, worker_id: str):
    """Record job started."""
    if PROMETHEUS_AVAILABLE:
        metrics.jobs_started.labels(
            job_type=job_type, tenant_id=tenant_id, worker_id=worker_id
        ).inc()
        metrics.jobs_running.labels(
            job_type=job_type, tenant_id=tenant_id, worker_id=worker_id
        ).inc()


def record_job_completed(
    metrics: JobMetrics,
    job_type: str,
    tenant_id: str,
    worker_id: str,
    success: bool,
    error_code: Optional[str] = None,
    duration: Optional[float] = None,
    queue_wait: Optional[float] = None,
):
    """Record job completion."""
    if not PROMETHEUS_AVAILABLE:
        return
    
    metrics.jobs_running.labels(
        job_type=job_type, tenant_id=tenant_id, worker_id=worker_id
    ).dec()
    
    if success:
        metrics.jobs_succeeded.labels(
            job_type=job_type, tenant_id=tenant_id, worker_id=worker_id
        ).inc()
    else:
        metrics.jobs_failed.labels(
            job_type=job_type,
            tenant_id=tenant_id,
            worker_id=worker_id,
            error_code=error_code or "unknown",
        ).inc()
    
    if duration is not None:
        metrics.job_duration.labels(job_type=job_type, tenant_id=tenant_id).observe(duration)
    
    if queue_wait is not None:
        metrics.job_queue_wait.labels(
            job_type=job_type, tenant_id=tenant_id, priority="normal"
        ).observe(queue_wait)


def record_job_retry(metrics: JobMetrics, job_type: str, tenant_id: str, retry_count: int, delay: float):
    """Record job retry."""
    if PROMETHEUS_AVAILABLE:
        metrics.jobs_retried.labels(
            job_type=job_type, tenant_id=tenant_id, retry_count=str(retry_count)
        ).inc()
        metrics.job_retry_delay.labels(
            job_type=job_type, tenant_id=tenant_id, retry_count=str(retry_count)
        ).observe(delay)


def record_dlq_entry(metrics: JobMetrics, job_type: str, tenant_id: str, reason: str):
    """Record DLQ entry."""
    if PROMETHEUS_AVAILABLE:
        metrics.jobs_dead_lettered.labels(
            job_type=job_type, tenant_id=tenant_id, reason=reason
        ).inc()
        metrics.dlq_entries.labels(
            tenant_id=tenant_id, reason=reason, resolved="false"
        ).inc()


def record_dlq_resolved(metrics: JobMetrics, tenant_id: str, reason: str):
    """Record DLQ entry resolved."""
    if PROMETHEUS_AVAILABLE:
        metrics.dlq_entries.labels(
            tenant_id=tenant_id, reason=reason, resolved="true"
        ).inc()
        metrics.dlq_entries.labels(
            tenant_id=tenant_id, reason=reason, resolved="false"
        ).dec()


def record_rate_limit(metrics: JobMetrics, key: str, algorithm: str, allowed: bool):
    """Record rate limit check."""
    if PROMETHEUS_AVAILABLE:
        if allowed:
            metrics.rate_limit_allowed.labels(key=key, algorithm=algorithm).inc()
        else:
            metrics.rate_limit_rejected.labels(key=key, algorithm=algorithm).inc()


# =============================================================================
# Global Metrics Instance
# =============================================================================

_global_registry: Optional[MetricsRegistry] = None
_global_metrics: Optional[JobMetrics] = None
_metrics_lock = threading.Lock()


def get_metrics_registry(namespace: str = "swarm_jobs") -> MetricsRegistry:
    """Get or create global metrics registry."""
    global _global_registry
    with _metrics_lock:
        if _global_registry is None:
            _global_registry = MetricsRegistry(namespace=namespace)
        return _global_registry


def get_job_metrics(namespace: str = "swarm_jobs") -> JobMetrics:
    """Get or create global job metrics."""
    global _global_metrics
    with _metrics_lock:
        if _global_metrics is None:
            registry = get_metrics_registry(namespace)
            _global_metrics = JobMetrics(registry)
        return _global_metrics


def init_metrics(
    namespace: str = "swarm_jobs",
    build_info: Optional[Dict[str, str]] = None,
) -> JobMetrics:
    """Initialize metrics with build info."""
    metrics = get_job_metrics(namespace)
    
    if build_info and PROMETHEUS_AVAILABLE:
        metrics.info.info(build_info)
    
    return metrics


def generate_metrics() -> bytes:
    """Generate Prometheus metrics output."""
    if PROMETHEUS_AVAILABLE and _global_registry:
        return generate_latest(_global_registry._prom_registry)
    return b"# Prometheus not available\n"


def get_metrics_content_type() -> str:
    """Get Prometheus content type."""
    if PROMETHEUS_AVAILABLE:
        return CONTENT_TYPE_LATEST
    return "text/plain"


# =============================================================================
# Integration Helpers
# =============================================================================

class MetricsMiddleware:
    """Middleware to automatically track metrics for workers/schedulers."""
    
    def __init__(self, metrics: JobMetrics):
        self.metrics = metrics
    
    def on_job_enqueued(self, job):
        record_job_enqueued(self.metrics, job.job_type, job.tenant_id, job.config.priority.value)
    
    def on_job_started(self, job, worker_id: str):
        record_job_started(self.metrics, job.job_type, job.tenant_id, worker_id)
    
    def on_job_completed(
        self,
        job,
        worker_id: str,
        success: bool,
        error_code: Optional[str] = None,
        duration: Optional[float] = None,
        queue_wait: Optional[float] = None,
    ):
        record_job_completed(
            self.metrics,
            job.job_type,
            job.tenant_id,
            worker_id,
            success,
            error_code,
            duration,
            queue_wait,
        )
    
    def on_job_retry(self, job, retry_count: int, delay: float):
        record_job_retry(self.metrics, job.job_type, job.tenant_id, retry_count, delay)
    
    def on_dlq_added(self, job, reason: str):
        record_dlq_entry(self.metrics, job.job_type, job.tenant_id, reason)
    
    def on_dlq_resolved(self, tenant_id: str, reason: str):
        record_dlq_resolved(self.metrics, tenant_id, reason)
    
    def on_rate_limit_check(self, key: str, algorithm: str, allowed: bool):
        record_rate_limit(self.metrics, key, algorithm, allowed)


# =============================================================================
# Health Check
# =============================================================================

@dataclass
class HealthStatus:
    """Health check result."""
    healthy: bool
    component: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


def check_worker_health(
    worker_status: Dict[str, Any],
    max_stale_jobs: int = 0,
) -> HealthStatus:
    """Check worker health from status dict."""
    healthy = worker_status.get("running", False)
    active_jobs = worker_status.get("active_jobs", 0)
    
    details = {
        "worker_id": worker_status.get("worker_id"),
        "active_jobs": active_jobs,
        "max_concurrent": worker_status.get("max_concurrent"),
        "job_types": worker_status.get("job_types"),
    }
    
    if active_jobs > max_stale_jobs:
        healthy = False
        details["warning"] = f"Active jobs ({active_jobs}) exceeds threshold ({max_stale_jobs})"
    
    if "repository_healthy" in worker_status:
        details["repository_healthy"] = worker_status["repository_healthy"]
        if not worker_status["repository_healthy"]:
            healthy = False
    
    return HealthStatus(healthy=healthy, component="worker", details=details)


def check_queue_health(
    pending_counts: Dict[str, int],
    max_pending_per_priority: Optional[Dict[str, int]] = None,
) -> HealthStatus:
    """Check queue health from pending counts."""
    healthy = True
    details = {"pending_counts": pending_counts}
    
    if max_pending_per_priority:
        for priority, count in pending_counts.items():
            max_allowed = max_pending_per_priority.get(priority, float('inf'))
            if count > max_allowed:
                healthy = False
                details[f"warning_{priority}"] = f"Pending {priority} ({count}) exceeds max ({max_allowed})"
    
    return HealthStatus(healthy=healthy, component="queue", details=details)


def check_rate_limiter_health(
    rate_limiter_stats: Dict[str, Any],
    max_rejection_rate: float = 0.1,
) -> HealthStatus:
    """Check rate limiter health from stats."""
    healthy = True
    details = {}
    
    rejection_rate = rate_limiter_stats.get("rejection_rate", 0)
    details["rejection_rate"] = rejection_rate
    
    if rejection_rate > max_rejection_rate:
        healthy = False
        details["warning"] = f"Rejection rate ({rejection_rate:.2%}) exceeds threshold ({max_rejection_rate:.2%})"
    
    return HealthStatus(healthy=healthy, component="rate_limiter", details=details)

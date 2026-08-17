"""
Enterprise Observability — F-023: Weak Observability fix.

Distributed tracing, metrics, structured logging across all stages.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Callable
from enum import Enum
from datetime import datetime, timezone
from contextlib import contextmanager
import uuid
import threading
import time
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class TraceEventType(str, Enum):
    """Types of trace events."""
    SPAN_START = "span_start"
    SPAN_END = "span_end"
    SPAN_ERROR = "span_error"
    EVENT = "event"


@dataclass
class Span:
    """A trace span."""
    span_id: str
    trace_id: str
    parent_span_id: Optional[str]
    operation_name: str
    service_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    tags: Dict[str, Any] = field(default_factory=dict)
    logs: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "ok"  # ok, error

    def duration_ms(self) -> Optional[int]:
        if self.end_time:
            return int((self.end_time - self.start_time).total_seconds() * 1000)
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "span_id": self.span_id,
            "trace_id": self.trace_id,
            "parent_span_id": self.parent_span_id,
            "operation_name": self.operation_name,
            "service_name": self.service_name,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms(),
            "tags": self.tags,
            "logs": self.logs,
            "status": self.status,
        }


@dataclass
class TraceContext:
    """Current trace context."""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    baggage: Dict[str, str] = field(default_factory=dict)


class Tracer:
    """Distributed tracer."""

    def __init__(self, service_name: str = "swarm"):
        self.service_name = service_name
        self._spans: Dict[str, Span] = {}
        self._traces: Dict[str, List[Span]] = defaultdict(list)
        self._lock = threading.RLock()
        self._sampling_rate = 1.0

    def start_span(
        self,
        operation_name: str,
        parent_span_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        tags: Dict[str, Any] = None,
    ) -> Span:
        """Start a new span."""
        trace_id = trace_id or str(uuid.uuid4())
        span_id = str(uuid.uuid4())

        span = Span(
            span_id=span_id,
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            operation_name=operation_name,
            service_name=self.service_name,
            start_time=datetime.now(timezone.utc),
            tags=tags or {},
        )

        with self._lock:
            self._spans[span_id] = span
            self._traces[trace_id].append(span)

        return span

    def end_span(self, span: Span, status: str = "ok", error: Optional[Exception] = None) -> None:
        """End a span."""
        span.end_time = datetime.now(timezone.utc)
        span.status = status
        if error:
            span.logs.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level": "error",
                "message": str(error),
                "error_type": type(error).__name__,
            })
            span.tags["error"] = True

    def add_log(self, span_id: str, message: str, level: str = "info", fields: Dict[str, Any] = None) -> None:
        """Add log to span."""
        with self._lock:
            span = self._spans.get(span_id)
            if span:
                span.logs.append({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "level": level,
                    "message": message,
                    "fields": fields or {},
                })

    def add_tag(self, span_id: str, key: str, value: Any) -> None:
        """Add tag to span."""
        with self._lock:
            span = self._spans.get(span_id)
            if span:
                span.tags[key] = value

    def get_trace(self, trace_id: str) -> List[Span]:
        """Get all spans for a trace."""
        with self._lock:
            return list(self._traces.get(trace_id, []))

    def get_span(self, span_id: str) -> Optional[Span]:
        with self._lock:
            return self._spans.get(span_id)

    @contextmanager
    def trace(self, operation_name: str, **tags):
        """Context manager for tracing."""
        span = self.start_span(operation_name, tags=tags)
        try:
            yield span
            self.end_span(span, "ok")
        except Exception as e:
            self.end_span(span, "error", e)
            raise


class MetricsCollector:
    """Metrics collection with p50/p95/p99, counters, gauges."""

    def __init__(self):
        self._counters: Dict[str, int] = defaultdict(int)
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = defaultdict(list)
        self._lock = threading.RLock()

    def increment(self, name: str, value: int = 1, labels: Dict[str, str] = None) -> None:
        """Increment counter."""
        key = self._make_key(name, labels)
        with self._lock:
            self._counters[key] += value

    def gauge(self, name: str, value: float, labels: Dict[str, str] = None) -> None:
        """Set gauge value."""
        key = self._make_key(name, labels)
        with self._lock:
            self._gauges[key] = value

    def histogram(self, name: str, value: float, labels: Dict[str, str] = None) -> None:
        """Record histogram value."""
        key = self._make_key(name, labels)
        with self._lock:
            self._histograms[key].append(value)

    def timing(self, name: str, duration_ms: float, labels: Dict[str, str] = None) -> None:
        """Record timing (histogram)."""
        self.histogram(name, duration_ms, labels)

    def _make_key(self, name: str, labels: Dict[str, str] = None) -> str:
        if not labels:
            return name
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"

    def get_counters(self) -> Dict[str, int]:
        with self._lock:
            return dict(self._counters)

    def get_gauges(self) -> Dict[str, float]:
        with self._lock:
            return dict(self._gauges)

    def get_histograms(self) -> Dict[str, Dict[str, float]]:
        """Get histogram stats: count, sum, min, max, p50, p95, p99."""
        with self._lock:
            result = {}
            for key, values in self._histograms.items():
                if not values:
                    continue
                sorted_vals = sorted(values)
                n = len(sorted_vals)
                result[key] = {
                    "count": n,
                    "sum": sum(sorted_vals),
                    "min": sorted_vals[0],
                    "max": sorted_vals[-1],
                    "p50": sorted_vals[n // 2],
                    "p95": sorted_vals[int(n * 0.95)],
                    "p99": sorted_vals[int(n * 0.99)],
                }
            return result

    def export_prometheus(self) -> str:
        """Export metrics in Prometheus format."""
        lines = []
        with self._lock:
            for key, value in self._counters.items():
                lines.append(f"{key} {value}")
            for key, value in self._gauges.items():
                lines.append(f"{key} {value}")
            for key, values in self._histograms.items():
                if values:
                    n = len(values)
                    lines.append(f"{key}_count {n}")
                    lines.append(f"{key}_sum {sum(values)}")
        return "\n".join(lines)


class StructuredLogger:
    """Structured logging with trace context."""

    def __init__(self, tracer: Tracer = None):
        self._tracer = tracer
        self._logger = logging.getLogger("swarm.structured")

    def _get_context(self) -> Dict[str, Any]:
        """Get current trace context."""
        context = {}
        # In real implementation, get from contextvars
        return context

    def log(
        self,
        level: str,
        message: str,
        event_type: str = "log",
        **fields,
    ) -> None:
        """Log structured event."""
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "message": message,
            "event_type": event_type,
            **self._get_context(),
            **fields,
        }
        # Use standard logger with extra
        getattr(self._logger, level.lower())(message, extra=record)


# Global instances
_tracer: Optional[Tracer] = None
_metrics: Optional[MetricsCollector] = None
_structured_logger: Optional[StructuredLogger] = None
_obs_locks = {
    "tracer": threading.Lock(),
    "metrics": threading.Lock(),
    "logger": threading.Lock(),
}


def get_tracer(service_name: str = "swarm") -> Tracer:
    global _tracer
    with _obs_locks["tracer"]:
        if _tracer is None:
            _tracer = Tracer(service_name)
        return _tracer


def get_metrics() -> MetricsCollector:
    global _metrics
    with _obs_locks["metrics"]:
        if _metrics is None:
            _metrics = MetricsCollector()
        return _metrics


def get_structured_logger() -> StructuredLogger:
    global _structured_logger
    with _obs_locks["logger"]:
        if _structured_logger is None:
            _structured_logger = StructuredLogger(get_tracer())
        return _structured_logger


# Convenience functions
def trace(operation_name: str, **tags):
    """Decorator for tracing function calls."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            tracer = get_tracer()
            with tracer.trace(operation_name, **tags):
                return func(*args, **kwargs)
        return wrapper
    return decorator


def count(name: str, value: int = 1, **labels):
    get_metrics().increment(name, value, labels)


def gauge(name: str, value: float, **labels):
    get_metrics().gauge(name, value, labels)


def timing(name: str, duration_ms: float, **labels):
    get_metrics().histogram(name, duration_ms, labels)


__all__ = [
    "TraceEventType",
    "Span",
    "TraceContext",
    "Tracer",
    "MetricsCollector",
    "StructuredLogger",
    "get_tracer",
    "get_metrics",
    "get_structured_logger",
    "trace",
    "count",
    "gauge",
    "timing",
]
"""
Distributed Tracing - OpenTelemetry integration for Swarm.
"""

import threading
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def uuidv7() -> str:
    return str(uuid.uuid4())


# =============================================================================
# Span Models
# =============================================================================

class SpanKind(str, Enum):
    INTERNAL = "internal"
    SERVER = "server"
    CLIENT = "client"
    PRODUCER = "producer"
    CONSUMER = "consumer"


class SpanStatus(str, Enum):
    UNSET = "unset"
    OK = "ok"
    ERROR = "error"


@dataclass
class SpanEvent:
    name: str
    timestamp: datetime
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SpanLink:
    trace_id: str
    span_id: str
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Span:
    """A single span in a trace."""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    name: str
    kind: SpanKind = SpanKind.INTERNAL
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: Optional[datetime] = None
    status: SpanStatus = SpanStatus.UNSET
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[SpanEvent] = field(default_factory=list)
    links: List[SpanLink] = field(default_factory=list)
    resource_attributes: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def duration_ms(self) -> Optional[float]:
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds() * 1000
        return None
    
    def is_finished(self) -> bool:
        return self.end_time is not None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "name": self.name,
            "kind": self.kind.value,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "status": self.status.value,
            "attributes": self.attributes,
            "events": [
                {
                    "name": e.name,
                    "timestamp": e.timestamp.isoformat(),
                    "attributes": e.attributes,
                }
                for e in self.events
            ],
        }


# =============================================================================
# Span Context
# =============================================================================

class SpanContext:
    """Context for a trace."""
    
    def __init__(
        self,
        trace_id: str,
        span_id: str,
        trace_flags: int = 1,  # 1 = sampled
        trace_state: Optional[str] = None,
    ):
        self.trace_id = trace_id
        self.span_id = span_id
        self.trace_flags = trace_flags
        self.trace_state = trace_state
    
    @property
    def is_sampled(self) -> bool:
        return (self.trace_flags & 1) != 0
    
    def to_headers(self) -> Dict[str, str]:
        """Convert to W3C traceparent headers."""
        return {
            "traceparent": f"00-{self.trace_id}-{self.span_id}-{self.trace_flags:02x}",
            "tracestate": self.trace_state or "",
        }
    
    @classmethod
    def from_headers(cls, headers: Dict[str, str]) -> Optional["SpanContext"]:
        """Extract from W3C traceparent headers."""
        traceparent = headers.get("traceparent") or headers.get("Traceparent")
        if not traceparent:
            return None
        
        parts = traceparent.split("-")
        if len(parts) != 4:
            return None
        
        version, trace_id, span_id, flags = parts
        if version != "00":
            return None
        
        return cls(
            trace_id=trace_id,
            span_id=span_id,
            trace_flags=int(flags, 16),
        )


# =============================================================================
# Tracer Interface
# =============================================================================

class Tracer(ABC):
    """Abstract tracer interface."""
    
    @abstractmethod
    def start_span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        parent_context: Optional[SpanContext] = None,
        attributes: Optional[Dict[str, Any]] = None,
        links: Optional[List[SpanLink]] = None,
    ) -> "Span":
        """Start a new span."""
        pass
    
    @abstractmethod
    def end_span(self, span: Span, status: SpanStatus = SpanStatus.OK) -> None:
        """End a span."""
        pass
    
    @abstractmethod
    def get_current_span(self) -> Optional[Span]:
        """Get currently active span."""
        pass
    
    @abstractmethod
    def set_current_span(self, span: Optional[Span]) -> None:
        """Set current span."""
        pass


# =============================================================================
# In-Memory Tracer
# =============================================================================

class InMemoryTracer(Tracer):
    """In-memory tracer for development/testing."""
    
    def __init__(self, service_name: str = "swarm"):
        self.service_name = service_name
        self._spans: List[Span] = []
        self._current_span: Optional[Span] = None
        self._lock = threading.RLock()
        
        # Span processor callbacks
        self._span_processors: List[Callable[[Span], None]] = []
    
    def add_span_processor(self, processor: Callable[[Span], None]) -> None:
        """Add a span processor callback."""
        self._span_processors.append(processor)
    
    def start_span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        parent_context: Optional[SpanContext] = None,
        attributes: Optional[Dict[str, Any]] = None,
        links: Optional[List[SpanLink]] = None,
    ) -> Span:
        """Start a new span."""
        with self._lock:
            trace_id = parent_context.trace_id if parent_context else uuidv7()
            span_id = uuidv7()[:16]
            parent_span_id = parent_context.span_id if parent_context else None
            
            span = Span(
                trace_id=trace_id,
                span_id=span_id,
                parent_span_id=parent_span_id,
                name=name,
                kind=kind,
                attributes=attributes or {},
                links=links or [],
            )
            
            # Add service name
            span.resource_attributes["service.name"] = self.service_name
            
            self._current_span = span
            return span
    
    def end_span(self, span: Span, status: SpanStatus = SpanStatus.OK) -> None:
        """End a span."""
        with self._lock:
            span.end_time = now_utc()
            span.status = status
            
            self._spans.append(span)
            
            # Process through callbacks
            for processor in self._span_processors:
                try:
                    processor(span)
                except Exception as e:
                    logger.error(f"Span processor error: {e}")
            
            # Clear current if this was the current span
            if self._current_span and self._current_span.span_id == span.span_id:
                self._current_span = None
    
    def get_current_span(self) -> Optional[Span]:
        with self._lock:
            return self._current_span
    
    def set_current_span(self, span: Optional[Span]) -> None:
        with self._lock:
            self._current_span = span
    
    def get_spans(
        self,
        trace_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[Span]:
        """Get spans with optional filters."""
        with self._lock:
            spans = self._spans
            
            if trace_id:
                spans = [s for s in spans if s.trace_id == trace_id]
            if start_time:
                spans = [s for s in spans if s.start_time >= start_time]
            if end_time:
                spans = [s for s in spans if s.end_time and s.end_time <= end_time]
            
            return spans
    
    def get_trace(self, trace_id: str) -> List[Span]:
        """Get all spans for a trace."""
        return self.get_spans(trace_id=trace_id)
    
    def export_spans(self) -> List[Dict[str, Any]]:
        """Export all spans as dictionaries."""
        with self._lock:
            return [s.to_dict() for s in self._spans]


# =============================================================================
# OpenTelemetry Tracer (Wrapper)
# =============================================================================

class OTELTracer(Tracer):
    """OpenTelemetry tracer wrapper."""
    
    def __init__(
        self,
        service_name: str = "swarm",
        endpoint: Optional[str] = None,
        insecure: bool = True,
    ):
        self.service_name = service_name
        self.endpoint = endpoint
        self._tracer = None
        self._provider = None
        self._initialized = False
        
        if endpoint:
            self._init_otel()
    
    def _init_otel(self) -> None:
        """Initialize OpenTelemetry SDK."""
        try:
            from opentelemetry import trace
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor
            from opentelemetry.sdk.resources import Resource
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
            
            resource = Resource.create({"service.name": self.service_name})
            provider = TracerProvider(resource=resource)
            
            if self.endpoint:
                exporter = OTLPSpanExporter(
                    endpoint=self.endpoint,
                    insecure=self.endpoint.startswith("http://") if self.endpoint else True,
                )
                provider.add_span_processor(BatchSpanProcessor(exporter))
            
            trace.set_tracer_provider(provider)
            self._tracer = trace.get_tracer(self.service_name)
            self._provider = provider
            self._initialized = True
            
            logger.info(f"OpenTelemetry tracer initialized for {self.service_name}")
        except ImportError:
            logger.warning("OpenTelemetry not installed, falling back to in-memory tracer")
            self._initialized = False
    
    def start_span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        parent_context: Optional[SpanContext] = None,
        attributes: Optional[Dict[str, Any]] = None,
        links: Optional[List[SpanLink]] = None,
    ) -> Span:
        if self._initialized and self._tracer:
            # Use OpenTelemetry
            from opentelemetry.trace import SpanKind as OtelSpanKind
            from opentelemetry.trace import Link
            
            otel_kind = {
                SpanKind.INTERNAL: OtelSpanKind.INTERNAL,
                SpanKind.SERVER: OtelSpanKind.SERVER,
                SpanKind.CLIENT: OtelSpanKind.CLIENT,
                SpanKind.PRODUCER: OtelSpanKind.PRODUCER,
                SpanKind.CONSUMER: OtelSpanKind.CONSUMER,
            }.get(kind, OtelSpanKind.INTERNAL)
            
            otel_links = []
            if links:
                for link in links:
                    otel_links.append(Link(
                        context=trace.SpanContext(
                            trace_id=int(link.trace_id, 16),
                            span_id=int(link.span_id, 16),
                        ),
                        attributes=link.attributes,
                    ))
            
            otel_span = self._tracer.start_span(
                name=name,
                kind=otel_kind,
                attributes=attributes,
                links=otel_links,
            )
            
            # Wrap in our Span model
            span = Span(
                trace_id=format(otel_span.context.trace_id, "032x"),
                span_id=format(otel_span.context.span_id, "016x"),
                parent_span_id=None,  # Would need parent context
                name=name,
                kind=kind,
                attributes=attributes or {},
            )
            return span
        
        # Fallback to in-memory
        return InMemoryTracer().start_span(name, kind, parent_context, attributes, links)
    
    def end_span(self, span: Span, status: SpanStatus = SpanStatus.OK) -> None:
        # Handled by OpenTelemetry internally
        pass
    
    def get_current_span(self) -> Optional[Span]:
        if self._initialized:
            from opentelemetry import trace
            span = trace.get_current_span()
            if span and span.get_span_context().is_valid:
                return Span(
                    trace_id=format(span.get_span_context().trace_id, "032x"),
                    span_id=format(span.get_span_context().span_id, "016x"),
                    parent_span_id=None,
                    name=span.name,
                )
        return None
    
    def set_current_span(self, span: Optional[Span]) -> None:
        pass
    
    def shutdown(self) -> None:
        if self._provider:
            self._provider.shutdown()


# =============================================================================
# Tracing Context Management
# =============================================================================

class TracingContext:
    """Thread-local tracing context."""
    
    def __init__(self, tracer: Tracer):
        self.tracer = tracer
        self._local = threading.local()
    
    @property
    def current_span(self) -> Optional[Span]:
        return getattr(self._local, "span", None)
    
    @current_span.setter
    def current_span(self, span: Optional[Span]) -> None:
        self._local.span = span
    
    @contextmanager
    def span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Optional[Dict[str, Any]] = None,
    ):
        """Context manager for creating spans."""
        parent = self.current_span
        parent_context = None
        if parent:
            parent_context = SpanContext(
                trace_id=parent.trace_id,
                span_id=parent.span_id,
            )
        
        span = self.tracer.start_span(
            name=name,
            parent_context=parent_context,
            attributes=attributes,
        )
        
        self.current_span = span
        
        try:
            yield span
            self.tracer.end_span(span, SpanStatus.OK)
        except Exception as e:
            span.attributes["error"] = str(e)
            span.attributes["error.type"] = type(e).__name__
            self.tracer.end_span(span, SpanStatus.ERROR)
            raise
        finally:
            self.current_span = parent
    
    def get_trace_headers(self) -> Dict[str, str]:
        """Get trace headers for propagation."""
        span = self.current_span
        if span:
            ctx = SpanContext(
                trace_id=span.trace_id,
                span_id=span.span_id,
            )
            return ctx.to_headers()
        return {}
    
    def inject_context(self, carrier: Dict[str, str]) -> None:
        """Inject trace context into carrier."""
        headers = self.get_trace_headers()
        carrier.update(headers)
    
    def extract_context(self, carrier: Dict[str, str]) -> Optional[SpanContext]:
        """Extract trace context from carrier."""
        return SpanContext.from_headers(carrier)


# =============================================================================
# Standard Attributes (Semantic Conventions)
# =============================================================================

class SpanAttributes:
    """Standard span attribute keys (OpenTelemetry semantic conventions)."""
    
    # HTTP
    HTTP_METHOD = "http.method"
    HTTP_URL = "http.url"
    HTTP_STATUS_CODE = "http.status_code"
    HTTP_ROUTE = "http.route"
    HTTP_REQUEST_CONTENT_LENGTH = "http.request.content_length"
    HTTP_RESPONSE_CONTENT_LENGTH = "http.response.content_length"
    
    # Database
    DB_SYSTEM = "db.system"
    DB_OPERATION = "db.operation"
    DB_STATEMENT = "db.statement"
    DB_NAME = "db.name"
    
    # Messaging
    MESSAGING_SYSTEM = "messaging.system"
    MESSAGING_DESTINATION = "messaging.destination"
    MESSAGING_OPERATION = "messaging.operation"
    
    # RPC/GRPC
    RPC_SYSTEM = "rpc.system"
    RPC_SERVICE = "rpc.service"
    RPC_METHOD = "rpc.method"
    
    # Error
    ERROR_TYPE = "error.type"
    ERROR_MESSAGE = "error.message"
    ERROR_STACK = "error.stack"
    
    # Code
    CODE_FUNCTION = "code.function"
    CODE_FILEPATH = "code.filepath"
    CODE_LINENO = "code.lineno"
    
    # Custom - Swarm specific
    SWARM_TENANT_ID = "swarm.tenant_id"
    SWARM_AGENT_ID = "swarm.agent_id"
    SWARM_WORKFLOW_ID = "swarm.workflow_id"
    SWARM_JOB_ID = "swarm.job_id"
    SWARM_CAPABILITY = "swarm.capability"


def set_span_attributes(span: Span, attributes: Dict[str, Any]) -> None:
    """Set multiple attributes on a span."""
    span.attributes.update(attributes)


def add_span_event(span: Span, name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
    """Add an event to a span."""
    event = SpanEvent(
        name=name,
        timestamp=now_utc(),
        attributes=attributes or {},
    )
    span.events.append(event)


# =============================================================================
# Tracing Middleware
# =============================================================================

class TracingMiddleware:
    """Middleware to automatically trace HTTP requests."""
    
    def __init__(self, tracer: Tracer):
        self.tracer = tracer
        self.context = TracingContext(tracer)
    
    @contextmanager
    def trace_request(
        self,
        method: str,
        path: str,
        status_code: int = 200,
        attributes: Optional[Dict[str, Any]] = None,
    ):
        """Context manager to trace HTTP request."""
        span_attrs = {
            SpanAttributes.HTTP_METHOD: method,
            SpanAttributes.HTTP_URL: path,
            SpanAttributes.HTTP_STATUS_CODE: status_code,
            SpanAttributes.HTTP_ROUTE: path,
        }
        if attributes:
            span_attrs.update(attributes)
        
        with self.context.span(
            name=f"{method} {path}",
            kind=SpanKind.SERVER,
            attributes=span_attrs,
        ) as span:
            try:
                yield span
            except Exception as e:
                span.attributes["error"] = str(e)
                span.status = SpanStatus.ERROR
                raise
    
    def inject_headers(self) -> Dict[str, str]:
        """Get trace headers for outgoing requests."""
        return self.context.get_trace_headers()
    
    def extract_context(self, headers: Dict[str, str]) -> Optional[SpanContext]:
        """Extract trace context from incoming headers."""
        return self.context.extract_context(headers)


# =============================================================================
# Trace Exporters
# =============================================================================

class SpanExporter(ABC):
    """Abstract span exporter."""
    
    @abstractmethod
    def export(self, spans: List[Span]) -> None:
        """Export spans."""
        pass
    
    @abstractmethod
    def shutdown(self) -> None:
        """Shutdown exporter."""
        pass


class ConsoleSpanExporter(SpanExporter):
    """Export spans to console."""
    
    def export(self, spans: List[Span]) -> None:
        for span in spans:
            print(f"Span: {span.name} | {span.trace_id[:8]}...{span.span_id[:8]} | {span.duration_ms:.2f}ms | {span.status.value}")
    
    def shutdown(self) -> None:
        pass


class JsonSpanExporter(SpanExporter):
    """Export spans as JSON."""
    
    def __init__(self, filepath: str):
        self.filepath = filepath
        self._file = open(filepath, "a")
    
    def export(self, spans: List[Span]) -> None:
        import json
        for span in spans:
            self._file.write(json.dumps(span.to_dict()) + "\n")
        self._file.flush()
    
    def shutdown(self) -> None:
        self._file.close()


# =============================================================================
# Factory
# =============================================================================

def create_tracer(
    service_name: str = "swarm",
    backend: str = "memory",
    endpoint: Optional[str] = None,
) -> Tracer:
    """Create a tracer instance."""
    if backend == "otel" and endpoint:
        return OTELTracer(service_name, endpoint)
    return InMemoryTracer(service_name)


def create_tracing_context(tracer: Tracer) -> TracingContext:
    """Create a tracing context."""
    return TracingContext(tracer)

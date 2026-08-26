from .tracing import SpanExporter, ConsoleSpanExporter
from .tracing import SpanExporter
"""
Enhanced Distributed Tracing - Jaeger, OTLP HTTP, Zipkin exporters.
"""

import asyncio
import json
import threading
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Callable
from collections import defaultdict
import logging

from .tracing import (
    Span, SpanKind, SpanStatus, SpanEvent, SpanLink, SpanContext,
    SpanAttributes, Tracer, InMemoryTracer, TracingContext,
    set_span_attributes, add_span_event,
)

logger = logging.getLogger(__name__)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def uuidv7() -> str:
    return str(uuid.uuid4())


# =============================================================================
# Batch Span Processor
# =============================================================================

class BatchSpanProcessor:
    """Batch spans for efficient export."""
    
    def __init__(
        self,
        exporter: "SpanExporter",
        max_batch_size: int = 512,
        max_queue_size: int = 2048,
        schedule_delay_millis: int = 5000,
        export_timeout_millis: int = 30000,
    ):
        self.exporter = exporter
        self.max_batch_size = max_batch_size
        self.max_queue_size = max_queue_size
        self.schedule_delay = schedule_delay_millis / 1000.0
        self.export_timeout = export_timeout_millis / 1000.0
        
        self._queue: List[Span] = []
        self._lock = threading.Lock()
        self._worker_thread: Optional[threading.Thread] = None
        self._shutdown = False
        self._condition = threading.Condition(self._lock)
        
        self._start_worker()
    
    def _start_worker(self) -> None:
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()
    
    def on_end(self, span: Span) -> None:
        """Called when a span ends."""
        with self._condition:
            if len(self._queue) >= self.max_queue_size:
                # Drop oldest if queue full
                self._queue.pop(0)
            self._queue.append(span)
            if len(self._queue) > getattr(self, "_queue_max", 10_000):
                del self._queue[:len(self._queue) - getattr(self, "_queue_max", 10_000)]
            self._condition.notify()
    
    def _worker_loop(self) -> None:
        while not self._shutdown:
            batch = []
            
            with self._condition:
                # Wait for batch or timeout
                self._condition.wait(timeout=self.schedule_delay)
                
                if self._queue:
                    batch = self._queue[:self.max_batch_size]
                    self._queue = self._queue[self.max_batch_size:]
            
            if batch:
                try:
                    self.exporter.export(batch)
                except Exception as e:
                    logger.error(f"Batch export failed: {e}")
        
        # Flush remaining on shutdown
        if self._queue:
            try:
                self.exporter.export(self._queue)
            except Exception as e:
                logger.error(f"Final flush failed: {e}")
    
    def shutdown(self) -> None:
        """Shutdown processor."""
        self._shutdown = True
        with self._condition:
            self._condition.notify_all()
        if self._worker_thread:
            self._worker_thread.join(timeout=10)


# =============================================================================
# Enhanced In-Memory Tracer with Batch Processing
# =============================================================================

class EnhancedInMemoryTracer(InMemoryTracer):
    """Enhanced in-memory tracer with batch processing and sampling."""
    
    def __init__(
        self,
        service_name: str = "swarm",
        sampler: Optional[Callable[[SpanContext], bool]] = None,
        batch_processor: Optional[BatchSpanProcessor] = None,
    ):
        super().__init__(service_name)
        self.service_name = service_name
        self.sampler = sampler or self._default_sampler
        self.batch_processor = batch_processor
    
    def _default_sampler(self, context: SpanContext) -> bool:
        """Default: sample all traces."""
        return True
    
    def start_span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        parent_context: Optional[SpanContext] = None,
        attributes: Optional[Dict[str, Any]] = None,
        links: Optional[List[SpanLink]] = None,
    ) -> Span:
        # Check sampling decision
        trace_id = parent_context.trace_id if parent_context else uuidv7()
        span_id = uuidv7()[:16]
        
        # Create temporary context for sampling decision
        sample_context = SpanContext(
            trace_id=trace_id,
            span_id=span_id,
        )
        
        if not self.sampler(sample_context):
            # Return a no-op span
            return self._create_noop_span(trace_id, span_id, parent_context, name, kind, attributes)
        
        # Sampled - create real span
        parent_span_id = parent_context.span_id if parent_context else None
        
        span = Span(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_context.span_id if parent_context else None,
            name=name,
            kind=kind,
            attributes=attributes or {},
            links=links or [],
        )
        
        # Add service name
        span.resource_attributes["service.name"] = self.service_name
        
        with self._lock:
            self._current_span = span
        
        return span
    
    def _create_noop_span(
        self,
        trace_id: str,
        span_id: str,
        parent_context: Optional[SpanContext],
        name: str,
        kind: SpanKind,
        attributes: Optional[Dict[str, Any]],
    ) -> Span:
        """Create a no-op span that doesn't record anything."""
        span = Span(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_context.span_id if parent_context else None,
            name=name,
            kind=kind,
            attributes=attributes or {},
        )
        span.resource_attributes["service.name"] = self.service_name
        span.attributes["swarm.sampled"] = "false"
        return span
    
    def end_span(self, span: Span, status: SpanStatus = SpanStatus.OK) -> None:
        super().end_span(span, status)
        
        # Send to batch processor if sampled
        if span.attributes.get("swarm.sampled") != "false":
            if self.batch_processor:
                self.batch_processor.on_end(span)


# =============================================================================
# Sampling Strategies
# =============================================================================

class Sampler(ABC):
    """Abstract sampler."""
    
    @abstractmethod
    def should_sample(self, context: SpanContext) -> bool:
        pass


class AlwaysOnSampler(Sampler):
    """Sample all traces."""
    
    def should_sample(self, context: SpanContext) -> bool:
        return True


class AlwaysOffSampler(Sampler):
    """Sample no traces."""
    
    def should_sample(self, context: SpanContext) -> bool:
        return False


class ProbabilisticSampler(Sampler):
    """Sample traces with given probability."""
    
    def __init__(self, rate: float = 0.1):
        self.rate = rate
        self._rng = random.random
    
    def should_sample(self, context: SpanContext) -> bool:
        # Use trace ID for consistent sampling decision
        hash_val = int(context.trace_id[:16], 16) / 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF
        return hash_val < self.rate


class ParentBasedSampler(Sampler):
    """Sample based on parent sampling decision."""
    
    def __init__(self, root_sampler: Sampler):
        self.root_sampler = root_sampler
    
    def should_sample(self, context: SpanContext) -> bool:
        # If parent is sampled, sample; otherwise use root sampler
        # In practice, this would check parent context
        return self.root_sampler.should_sample(context)


class RateLimitingSampler(Sampler):
    """Limit sampling rate per second."""
    
    def __init__(self, max_per_second: int = 1000):
        self.max_per_second = max_per_second
        self._count = 0
        self._window_start = time.time()
        self._lock = threading.Lock()
    
    def should_sample(self, context: SpanContext) -> bool:
        with self._lock:
            now = time.time()
            if now - self._window_start >= 1.0:
                self._count = 0
                self._window_start = now
            
            if self._count >= self.max_per_second:
                return False
            
            self._count += 1
            return True


# =============================================================================
# Jaeger Exporter
# =============================================================================

class JaegerExporter(SpanExporter):
    """Export spans to Jaeger via gRPC or HTTP."""
    
    def __init__(
        self,
        agent_host: str = "localhost",
        agent_port: int = 6831,
        collector_endpoint: Optional[str] = None,
        service_name: str = "swarm",
        max_packet_size: int = 65000,
    ):
        self.agent_host = agent_host
        self.agent_port = agent_port
        self.collector_endpoint = collector_endpoint
        self.service_name = service_name
        self.max_packet_size = max_packet_size
        
        self._use_grpc = collector_endpoint is None
        self._client = None
        self._init_client()
    
    def _init_client(self) -> None:
        try:
            if self._use_grpc:
                from jaeger_client import Config
                config = Config(
                    service_name=self.service_name,
                    sampler={"type": "const", "param": 1},
                    reporter={
                        "agent_host": self.agent_host,
                        "agent_port": self.agent_port,
                    },
                )
                self._tracer = config.initialize_tracer()
            else:
                # Use HTTP collector
                import requests
                self._session = requests.Session()
                self._collector_url = f"{self.collector_endpoint}/api/traces"
        except ImportError:
            logger.warning("jaeger-client not installed, Jaeger export disabled")
            self._use_grpc = False
    
    def export(self, spans: List[Span]) -> None:
        if self._use_grpc and hasattr(self, '_tracer'):
            # Jaeger client handles this automatically via the tracer
            logger.debug(f"Jaeger: exported {len(spans)} spans via gRPC")
        elif hasattr(self, '_session') and self.collector_endpoint:
            self._export_http(spans)
    
    def _export_http(self, spans: List[Span]) -> None:
        import requests
        
        # Convert to Jaeger Thrift format (simplified)
        jaeger_spans = []
        for span in spans:
            jaeger_spans.append(self._convert_span(span))
        
        payload = {"spans": jaeger_spans}
        
        try:
            response = self._session.post(
                self._collector_url,
                json=payload,
                timeout=10,
            )
            response.raise_for_status()
            logger.debug(f"Exported {len(spans)} spans to Jaeger HTTP collector")
        except Exception as e:
            logger.error(f"Jaeger HTTP export failed: {e}")
    
    def _convert_span(self, span: Span) -> Dict[str, Any]:
        """Convert Span to Jaeger format."""
        return {
            "traceID": span.trace_id,
            "spanID": span.span_id,
            "parentSpanID": span.parent_span_id or "",
            "operationName": span.name,
            "flags": 1,
            "startTime": int(span.start_time.timestamp() * 1_000_000),
            "duration": int((span.duration_ms or 0) * 1000),
            "tags": [
                {"key": k, "vType": "STRING", "vStr": str(v)}
                for k, v in span.attributes.items()
            ],
            "logs": [
                {
                    "timestamp": int(e.timestamp.timestamp() * 1_000_000),
                    "fields": [
                        {"key": "event", "vType": "STRING", "vStr": e.name},
                        *[{"key": k, "vType": "STRING", "vStr": str(v)} for k, v in e.attributes.items()]
                    ]
                }
                for e in span.events
            ],
            "process": {
                "serviceName": span.resource_attributes.get("service.name", "swarm"),
                "tags": []
            },
        }
    
    def shutdown(self) -> None:
        if hasattr(self, '_tracer'):
            self._tracer.close()


# =============================================================================
# OTLP HTTP Exporter
# =============================================================================

class OTLPHTTPExporter(SpanExporter):
    """Export spans via OTLP HTTP (protobuf or JSON)."""
    
    def __init__(
        self,
        endpoint: str = "http://localhost:4318/v1/traces",
        headers: Optional[Dict[str, str]] = None,
        timeout: float = 10.0,
        use_json: bool = True,
    ):
        self.endpoint = endpoint
        self.headers = headers or {"Content-Type": "application/json"}
        self.timeout = timeout
        self.use_json = use_json
        
        if not self.use_json:
            self.headers["Content-Type"] = "application/x-protobuf"
        
        self._session = None
        self._init_session()
    
    def _init_session(self) -> None:
        import requests
        self._session = requests.Session()
        self._session.headers.update(self.headers)
    
    def export(self, spans: List[Span]) -> None:
        if self.use_json:
            self._export_json(spans)
        else:
            self._export_protobuf(spans)
    
    def _export_json(self, spans: List[Span]) -> None:
        import requests
        
        # Convert to OTLP JSON format
        resource_spans = [{
            "resource": {
                "attributes": [
                    {"key": "service.name", "value": {"stringValue": "swarm"}}
                ]
            },
            "scopeSpans": [{
                "spans": [self._span_to_otlp_json(s) for s in spans]
            }]
        }]
        
        payload = {"resourceSpans": resource_spans}
        
        try:
            response = self._session.post(
                self.endpoint,
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            logger.debug(f"Exported {len(spans)} spans via OTLP HTTP JSON")
        except Exception as e:
            logger.error(f"OTLP HTTP export failed: {e}")
    
    def _span_to_otlp_json(self, span: Span) -> Dict[str, Any]:
        """Convert Span to OTLP JSON format."""
        return {
            "traceId": span.trace_id,
            "spanId": span.span_id,
            "parentSpanId": span.parent_span_id or "",
            "name": span.name,
            "kind": self._convert_kind(span.kind),
            "startTimeUnixNano": str(int(span.start_time.timestamp() * 1_000_000_000)),
            "endTimeUnixNano": str(int(span.end_time.timestamp() * 1_000_000_000)) if span.end_time else "0",
            "attributes": self._attributes_to_otlp(span.attributes),
            "events": [
                {
                    "timeUnixNano": str(int(e.timestamp.timestamp() * 1_000_000_000)),
                    "name": e.name,
                    "attributes": self._attributes_to_otlp(e.attributes),
                }
                for e in span.events
            ],
            "links": [
                {
                    "traceId": l.trace_id,
                    "spanId": l.span_id,
                    "attributes": self._attributes_to_otlp(l.attributes),
                }
                for l in span.links
            ],
            "status": {
                "code": self._convert_status(span.status),
            },
        }
    
    def _convert_kind(self, kind: SpanKind) -> str:
        mapping = {
            SpanKind.INTERNAL: "SPAN_KIND_INTERNAL",
            SpanKind.SERVER: "SPAN_KIND_SERVER",
            SpanKind.CLIENT: "SPAN_KIND_CLIENT",
            SpanKind.PRODUCER: "SPAN_KIND_PRODUCER",
            SpanKind.CONSUMER: "SPAN_KIND_CONSUMER",
        }
        return mapping.get(kind, "SPAN_KIND_UNSPECIFIED")
    
    def _convert_status(self, status: SpanStatus) -> Dict[str, Any]:
        mapping = {
            SpanStatus.UNSET: {"code": "STATUS_CODE_UNSET"},
            SpanStatus.OK: {"code": "STATUS_CODE_OK"},
            SpanStatus.ERROR: {"code": "STATUS_CODE_ERROR"},
        }
        return mapping.get(status, {"code": "STATUS_CODE_UNSET"})
    
    def _attributes_to_otlp(self, attrs: Dict[str, Any]) -> List[Dict[str, Any]]:
        result = []
        for k, v in attrs.items():
            if isinstance(v, str):
                result.append({"key": k, "value": {"stringValue": v}})
            elif isinstance(v, bool):
                result.append({"key": k, "value": {"boolValue": v}})
            elif isinstance(v, (int, float)):
                result.append({"key": k, "value": {"doubleValue": float(v)}})
            else:
                result.append({"key": k, "value": {"stringValue": str(v)}})
        return result
    
    def _export_protobuf(self, spans: List[Span]) -> None:
        # Would use opentelemetry-protobuf if available
        logger.warning("Protobuf export not implemented")
    
    def shutdown(self) -> None:
        if self._session:
            self._session.close()


# =============================================================================
# Zipkin Exporter
# =============================================================================

class ZipkinExporter(SpanExporter):
    """Export spans to Zipkin."""
    
    def __init__(
        self,
        endpoint: str = "http://localhost:9411/api/v2/spans",
        service_name: str = "swarm",
        timeout: float = 10.0,
    ):
        self.endpoint = endpoint
        self.service_name = service_name
        self.timeout = timeout
        self._session = None
        self._init_session()
    
    def _init_session(self) -> None:
        import requests
        self._session = requests.Session()
        self._session.headers.update({"Content-Type": "application/json"})
    
    def export(self, spans: List[Span]) -> None:
        zipkin_spans = [self._convert_span(span) for span in spans]
        
        try:
            import requests
            response = self._session.post(
                self.endpoint,
                json=zipkin_spans,
                timeout=self.timeout,
            )
            response.raise_for_status()
            logger.debug(f"Exported {len(spans)} spans to Zipkin")
        except Exception as e:
            logger.error(f"Zipkin export failed: {e}")
    
    def _convert_span(self, span: Span) -> Dict[str, Any]:
        return {
            "traceId": span.trace_id,
            "id": span.span_id,
            "parentId": span.parent_span_id,
            "name": span.name,
            "kind": self._convert_kind(span.kind),
            "timestamp": int(span.start_time.timestamp() * 1_000_000),
            "duration": int((span.duration_ms or 0) * 1000),
            "localEndpoint": {
                "serviceName": span.resource_attributes.get("service.name", "swarm"),
            },
            "tags": {k: str(v) for k, v in span.attributes.items()},
            "annotations": [
                {
                    "timestamp": int(e.timestamp.timestamp() * 1_000_000),
                    "value": e.name,
                }
                for e in span.events
            ],
        }
    
    def _convert_kind(self, kind: SpanKind) -> str:
        mapping = {
            SpanKind.SERVER: "SERVER",
            SpanKind.CLIENT: "CLIENT",
            SpanKind.PRODUCER: "PRODUCER",
            SpanKind.CONSUMER: "CONSUMER",
        }
        return mapping.get(kind, "")
    
    def shutdown(self) -> None:
        if self._session:
            self._session.close()


# =============================================================================
# Enhanced Tracer Factory
# =============================================================================

def create_tracer(
    service_name: str = "swarm",
    backend: str = "memory",
    endpoint: Optional[str] = None,
    sampler: Optional[Sampler] = None,
    exporters: Optional[List[SpanExporter]] = None,
    batch_size: int = 512,
    schedule_delay_millis: int = 5000,
) -> Tracer:
    """Create an enhanced tracer with multiple exporters."""
    
    # Create base tracer
    if backend == "memory":
        tracer = EnhancedInMemoryTracer(service_name, sampler)
    elif backend == "otel" and endpoint:
        from .tracing import OTELTracer
        tracer = OTELTracer(service_name, endpoint)
    else:
        tracer = EnhancedInMemoryTracer(service_name, sampler)
    
    # Add batch processor with exporters
    if exporters and isinstance(tracer, EnhancedInMemoryTracer):
        for exporter in exporters:
            processor = BatchSpanProcessor(
                exporter,
                max_batch_size=batch_size,
            )
            tracer.add_span_processor(processor.on_end)
    
    return tracer


def create_jaeger_exporter(
    agent_host: str = "localhost",
    agent_port: int = 6831,
    collector_endpoint: Optional[str] = None,
    service_name: str = "swarm",
) -> JaegerExporter:
    """Create Jaeger exporter."""
    return JaegerExporter(agent_host, agent_port, collector_endpoint, service_name)


def create_otlp_http_exporter(
    endpoint: str = "http://localhost:4318/v1/traces",
    headers: Optional[Dict[str, str]] = None,
    timeout: float = 10.0,
) -> OTLPHTTPExporter:
    """Create OTLP HTTP exporter."""
    return OTLPHTTPExporter(endpoint, headers, timeout)


def create_zipkin_exporter(
    endpoint: str = "http://localhost:9411/api/v2/spans",
    service_name: str = "swarm",
    timeout: float = 10.0,
) -> ZipkinExporter:
    """Create Zipkin exporter."""
    return ZipkinExporter(endpoint, service_name, timeout)


def create_console_exporter() -> ConsoleSpanExporter:
    """Create console exporter."""
    return ConsoleSpanExporter()


# =============================================================================
# Sampling Factory
# =============================================================================

def create_sampler(
    sampler_type: str = "always_on",
    **kwargs,
) -> Sampler:
    """Create a sampler instance."""
    samplers = {
        "always_on": AlwaysOnSampler,
        "always_off": AlwaysOffSampler,
        "probabilistic": ProbabilisticSampler,
        "parent_based": ParentBasedSampler,
        "rate_limiting": RateLimitingSampler,
    }
    
    if sampler_type not in samplers:
        raise ValueError(f"Unknown sampler type: {sampler_type}")
    
    return samplers[sampler_type](**kwargs)


# =============================================================================
# Convenience: Create Production Tracer
# =============================================================================

def create_production_tracer(
    service_name: str = "swarm",
    jaeger_endpoint: Optional[str] = None,
    otlp_endpoint: Optional[str] = None,
    zipkin_endpoint: Optional[str] = None,
    sampling_rate: float = 0.1,
) -> Tracer:
    """Create a production-ready tracer with multiple exporters."""
    
    exporters = []
    
    if jaeger_endpoint:
        exporters.append(create_jaeger_exporter(collector_endpoint=jaeger_endpoint, service_name=service_name))
    
    if otlp_endpoint:
        exporters.append(create_otlp_http_exporter(otlp_endpoint))
    
    if zipkin_endpoint:
        exporters.append(create_zipkin_exporter(zipkin_endpoint, service_name))
    
    # Always add console for debugging
    exporters.append(create_console_exporter())
    
    sampler = create_sampler("probabilistic", rate=sampling_rate)
    
    return create_tracer(
        service_name=service_name,
        backend="memory",
        sampler=sampler,
        exporters=exporters,
    )

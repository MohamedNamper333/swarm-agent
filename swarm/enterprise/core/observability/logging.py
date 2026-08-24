"""
Structured Logging - JSON logging with correlation IDs, trace integration.
"""

import json
import logging
import sys
import threading
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
from contextlib import contextmanager
import logging.handlers

from .tracing import SpanContext, TracingContext, create_tracer, InMemoryTracer


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def uuidv7() -> str:
    return str(uuid.uuid4())


# =============================================================================
# Structured Log Models
# =============================================================================

class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class LogRecord:
    """Structured log record."""
    timestamp: datetime
    level: LogLevel
    logger_name: str
    message: str
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    tenant_id: Optional[str] = None
    actor_id: Optional[str] = None
    actor_type: Optional[str] = None
    service_name: str = "swarm"
    module: Optional[str] = None
    function: Optional[str] = None
    line_number: Optional[int] = None
    extra: Dict[str, Any] = field(default_factory=dict)
    exception: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.value,
            "logger": self.logger_name,
            "message": self.message,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "tenant_id": self.tenant_id,
            "actor_id": self.actor_id,
            "actor_type": self.actor_type,
            "service": self.service_name,
            "module": self.module,
            "function": self.function,
            "line": self.line_number,
            "extra": self.extra,
            "exception": self.exception,
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


# =============================================================================
# JSON Formatter
# =============================================================================

class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def __init__(self, service_name: str = "swarm", include_trace: bool = True):
        super().__init__()
        self.service_name = service_name
        self.include_trace = include_trace
    
    def format(self, record: logging.LogRecord) -> str:
        # Extract trace context
        trace_id = getattr(record, "trace_id", None)
        span_id = getattr(record, "span_id", None)
        tenant_id = getattr(record, "tenant_id", None)
        actor_id = getattr(record, "actor_id", None)
        actor_type = getattr(record, "actor_type", None)
        
        # Build structured log
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": self.service_name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "thread": record.threadName,
            "process": record.process,
        }
        
        if self.include_trace:
            if trace_id:
                log_data["trace_id"] = trace_id
            if span_id:
                log_data["span_id"] = span_id
        
        # Add tenant/actor context
        if tenant_id:
            log_data["tenant_id"] = tenant_id
        if actor_id:
            log_data["actor_id"] = actor_id
        if actor_type:
            log_data["actor_type"] = actor_type
        
        # Add extra fields
        extra = getattr(record, "extra", {})
        if extra:
            log_data["extra"] = extra
        
        # Add exception info
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, ensure_ascii=False)


class ConsoleFormatter(logging.Formatter):
    """Human-readable console formatter with colors."""
    
    COLORS = {
        "DEBUG": "\033[36m",      # Cyan
        "INFO": "\033[32m",       # Green
        "WARNING": "\033[33m",    # Yellow
        "ERROR": "\033[31m",      # Red
        "CRITICAL": "\033[35m",   # Magenta
        "RESET": "\033[0m",
    }
    
    def __init__(self, include_trace: bool = True):
        super().__init__()
        self.include_trace = include_trace
    
    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, "")
        reset = self.COLORS["RESET"]
        
        timestamp = datetime.fromtimestamp(record.created).strftime("%H:%M:%S.%f")[:-3]
        
        trace_info = ""
        if self.include_trace:
            trace_id = getattr(record, "trace_id", None)
            span_id = getattr(record, "span_id", None)
            if trace_id:
                trace_info = f" [{trace_id[:8]}"
                span_id = getattr(record, "span_id", None)
                if span_id:
                    trace_info += f":{span_id[:8]}"
                trace_info += "]"
        
        return (
            f"{color}{timestamp} {record.levelname:<8}{reset} "
            f"{record.name}{trace_info} "
            f"{record.getMessage()}"
        )


# =============================================================================
# Context-Aware Logger
# =============================================================================

class ContextLogger:
    """Logger with automatic context injection."""
    
    def __init__(
        self,
        name: str,
        logger: logging.Logger,
        tracing_context: Optional["TracingContext"] = None,
        default_context: Optional[Dict[str, Any]] = None,
    ):
        self.name = name
        self.logger = logger
        self.tracing_context = tracing_context
        self.default_context = default_context or {}
    
    def _get_trace_context(self) -> Dict[str, Any]:
        """Get trace context from tracing context."""
        if not self.tracing_context:
            return {}
        
        span = self.tracing_context.current_span
        if span:
            return {
                "trace_id": span.trace_id,
                "span_id": span.span_id,
            }
        return {}
    
    def _log(
        self,
        level: int,
        message: str,
        extra: Optional[Dict[str, Any]] = None,
        exc_info: bool = False,
    ) -> None:
        """Internal log method with context injection."""
        # Merge contexts
        context = {**self.default_context}
        context.update(self._get_trace_context())
        if extra:
            context.update(extra)
        
        # Log with context
        self.logger.log(level, message, extra={"extra": context}, exc_info=exc_info)
    
    def debug(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        self._log(logging.DEBUG, message, extra)
    
    def info(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        self._log(logging.INFO, message, extra)
    
    def warning(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        self._log(logging.WARNING, message, extra)
    
    def error(self, message: str, extra: Optional[Dict[str, Any]] = None, exc_info: bool = True) -> None:
        self._log(logging.ERROR, message, extra, exc_info)
    
    def critical(self, message: str, extra: Optional[Dict[str, Any]] = None, exc_info: bool = True) -> None:
        self._log(logging.CRITICAL, message, extra, exc_info)
    
    def log_with_context(
        self,
        level: int,
        message: str,
        trace_id: Optional[str] = None,
        span_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        actor_id: Optional[str] = None,
        actor_type: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log with explicit context override."""
        context = {
            "trace_id": trace_id,
            "span_id": span_id,
            "tenant_id": tenant_id,
            "actor_id": actor_id,
            "actor_type": actor_type,
        }
        context = {k: v for k, v in context.items() if v is not None}
        if extra:
            context.update(extra)
        
        self.logger.log(level, message, extra={"extra": context})
    
    @contextmanager
    def bind_context(self, **context):
        """Temporarily bind additional context."""
        old_context = self.default_context.copy()
        self.default_context.update(context)
        try:
            yield self
        finally:
            self.default_context = old_context


# =============================================================================
# Logging Manager
# =============================================================================

class LoggingManager:
    """Centralized logging configuration and management."""
    
    def __init__(self, service_name: str = "swarm"):
        self.service_name = service_name
        self._loggers: Dict[str, ContextLogger] = {}
        self._tracing_context: Optional["TracingContext"] = None
        self._configured = False
        self._lock = threading.Lock()
    
    def configure(
        self,
        level: int = logging.INFO,
        json_output: bool = True,
        console_output: bool = True,
        log_file: Optional[str] = None,
        service_name: Optional[str] = None,
    ) -> None:
        """Configure global logging."""
        with self._lock:
            if self._configured:
                return
            
            if service_name:
                self.service_name = service_name
            
            # Configure root logger
            root_logger = logging.getLogger()
            root_logger.setLevel(level)
            root_logger.handlers.clear()
            
            # Console handler
            if console_output:
                console_handler = logging.StreamHandler(sys.stdout)
                console_handler.setLevel(level)
                console_handler.setFormatter(ConsoleFormatter(include_trace=True))
                root_logger.addHandler(console_handler)
            
            # JSON handler
            if json_output:
                json_handler = logging.StreamHandler(sys.stdout)
                json_handler.setLevel(level)
                json_handler.setFormatter(JSONFormatter(
                    service_name=self.service_name,
                    include_trace=True,
                ))
                root_logger.addHandler(json_handler)
            
            # File handler
            if log_file:
                file_handler = logging.handlers.RotatingFileHandler(
                    log_file,
                    maxBytes=100 * 1024 * 1024,  # 100MB
                    backupCount=10,
                )
                file_handler.setLevel(level)
                file_handler.setFormatter(JSONFormatter(
                    service_name=self.service_name,
                    include_trace=True,
                ))
                root_logger.addHandler(file_handler)
            
            self._configured = True
            logging.info(f"Logging configured for {self.service_name}")
    
    def set_tracing_context(self, tracing_context: "TracingContext") -> None:
        """Set tracing context for automatic trace injection."""
        self._tracing_context = tracing_context
    
    def get_logger(self, name: str) -> ContextLogger:
        """Get a context-aware logger."""
        with self._lock:
            if name not in self._loggers:
                base_logger = logging.getLogger(name)
                self._loggers[name] = ContextLogger(
                    name=name,
                    logger=base_logger,
                    tracing_context=self._tracing_context,
                )
            return self._loggers[name]
    
    def get_child_logger(self, parent: str, child: str) -> ContextLogger:
        """Get a child logger (e.g., 'swarm.api' -> 'swarm.api.endpoints')."""
        return self.get_logger(f"{parent}.{child}")
    
    def set_level(self, level: int) -> None:
        """Set log level for all loggers."""
        logging.getLogger().setLevel(level)
        for logger in self._loggers.values():
            logger.logger.setLevel(level)


# =============================================================================
# Log Handlers
# =============================================================================

class LogHandler(ABC):
    """Abstract log handler for external systems."""
    
    @abstractmethod
    def handle(self, record: LogRecord) -> None:
        """Handle a log record."""
        pass
    
    @abstractmethod
    def flush(self) -> None:
        """Flush buffered logs."""
        pass
    
    @abstractmethod
    def close(self) -> None:
        """Close handler."""
        pass


class ElasticsearchHandler(LogHandler):
    """Send logs to Elasticsearch."""
    
    def __init__(
        self,
        hosts: List[str],
        index: str = "swarm-logs",
        batch_size: int = 100,
        flush_interval: float = 5.0,
    ):
        self.hosts = hosts
        self.index = index
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self._buffer: List[LogRecord] = []
        self._lock = threading.Lock()
        self._running = False
        self._flush_thread: Optional[threading.Thread] = None
    
    def handle(self, record: LogRecord) -> None:
        with self._lock:
            self._buffer.append(record)
            if len(self._buffer) >= self.batch_size:
                self._flush_buffer()
    
    def flush(self) -> None:
        with self._lock:
            self._flush_buffer()
    
    def _flush_buffer(self) -> None:
        if not self._buffer:
            return
        
        # In production, send to Elasticsearch
        # For now, just log
        logging.debug(f"Flushing {len(self._buffer)} logs to Elasticsearch")
        self._buffer.clear()
    
    def start(self) -> None:
        self._running = True
        self._flush_thread = threading.Thread(target=self._flush_loop, daemon=True)
        self._flush_thread.start()
    
    def _flush_loop(self) -> None:
        while self._running:
            time.sleep(self.flush_interval)
            self.flush()
    
    def close(self) -> None:
        self._running = False
        if self._flush_thread:
            self._flush_thread.join(timeout=5)
        self.flush()


class SyslogHandler(LogHandler):
    """Send logs to syslog."""
    
    def __init__(self, host: str = "localhost", port: int = 514):
        self.host = host
        self.port = port
        self._socket = None
    
    def handle(self, record: LogRecord) -> None:
        # In production, send via syslog protocol
        pass
    
    def flush(self) -> None:
        pass
    
    def close(self) -> None:
        pass


# =============================================================================
# Log Correlation
# =============================================================================

class LogCorrelation:
    """Manage log correlation IDs across requests."""
    
    def __init__(self):
        self._local = threading.local()
    
    @property
    def correlation_id(self) -> Optional[str]:
        return getattr(self._local, "correlation_id", None)
    
    @correlation_id.setter
    def correlation_id(self, value: Optional[str]) -> None:
        self._local.correlation_id = value
    
    def new_correlation_id(self) -> str:
        """Generate new correlation ID."""
        corr_id = uuidv7()
        self.correlation_id = corr_id
        return corr_id
    
    def clear(self) -> None:
        self._local.correlation_id = None


# =============================================================================
# Global Logging Manager
# =============================================================================

_global_logging_manager: Optional[LoggingManager] = None
_global_lock = threading.Lock()
_global_correlation = LogCorrelation()


def get_logging_manager(service_name: str = "swarm") -> LoggingManager:
    """Get global logging manager."""
    global _global_logging_manager
    with _global_lock:
        if _global_logging_manager is None:
            _global_logging_manager = LoggingManager(service_name)
        return _global_logging_manager


def get_logger(name: str) -> ContextLogger:
    """Get a context-aware logger."""
    manager = get_logging_manager()
    return manager.get_logger(name)


def get_correlation() -> LogCorrelation:
    """Get global correlation manager."""
    return _global_correlation


def configure_logging(
    level: int = logging.INFO,
    json_output: bool = True,
    console_output: bool = True,
    log_file: Optional[str] = None,
    service_name: str = "swarm",
) -> LoggingManager:
    """Configure global logging."""
    manager = get_logging_manager(service_name)
    manager.configure(level, json_output, console_output, log_file, service_name)
    return manager


# =============================================================================
# Integration with Tracing
# =============================================================================

def create_logging_manager(
    service_name: str = "swarm",
    tracing_context: Optional["TracingContext"] = None,
) -> LoggingManager:
    """Create logging manager with tracing integration."""
    manager = LoggingManager(service_name)
    if tracing_context:
        manager.set_tracing_context(tracing_context)
    return manager

"""
Logging Plugins for API Gateway.
Provides request/response logging, access logs, and structured logging.
"""

import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Set
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class LogConfig:
    """Logging configuration."""
    level: str = "INFO"
    format: str = "json"  # json, text
    include_request_body: bool = False
    include_response_body: bool = False
    max_body_size: int = 1024 * 1024  # 1MB
    exclude_paths: List[str] = field(default_factory=lambda: ["/health", "/metrics", "/ready"])
    exclude_headers: List[str] = field(default_factory=lambda: ["authorization", "cookie", "x-api-key"])
    sample_rate: float = 1.0  # 0.0 to 1.0


@dataclass
class AccessLogEntry:
    """Structured access log entry."""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    trace_id: str = ""
    span_id: str = ""
    method: str = ""
    path: str = ""
    query_string: str = ""
    status_code: int = 0
    latency_ms: float = 0.0
    client_ip: str = ""
    user_agent: str = ""
    user_id: str = ""
    tenant_id: str = ""
    request_size: int = 0
    response_size: int = 0
    status_code: int = 0
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class RequestLoggingPlugin:
    """Request/response logging plugin with structured logging."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = LogConfig(**(config or {}))
        self._logger = logging.getLogger("gateway.access")
        self._buffer: List[Dict] = []
        self._buffer_lock = asyncio.Lock()
        self._flush_task: Optional[asyncio.Task] = None
        self._buffer_size = 100
        self._flush_interval = 5.0  # seconds
        self._running = False
    
    async def start(self):
        """Start background flush task."""
        if self._running:
            return
        self._running = True
        self._flush_task = asyncio.create_task(self._flush_loop())
    
    async def stop(self):
        """Stop background flush task."""
        self._running = False
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        await self._flush_buffer()
    
    async def log_request(
        self,
        request: Dict[str, Any],
        response: Optional[Dict] = None,
        latency_ms: float = 0,
        error: Optional[str] = None,
    ) -> None:
        """Log request/response pair."""
        # Check sampling
        if self.config.sample_rate < 1.0:
            import random
            if random.random() > self.config.sample_rate:
                return
        
        # Check excluded paths
        path = request.get("path", "")
        if any(path.startswith(p) for p in self.config.exclude_paths):
            return
        
        # Build log entry
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "trace_id": request.get("trace_id", ""),
            "span_id": request.get("span_id", ""),
            "method": request.get("method", ""),
            "path": request.get("path", ""),
            "query_string": request.get("query_string", ""),
            "status_code": response.get("status_code", 0) if response else 0,
            "latency_ms": request.get("latency_ms", 0),
            "client_ip": request.get("client_ip", ""),
            "user_agent": request.get("headers", {}).get("user-agent", ""),
            "user_id": request.get("user_id", ""),
            "tenant_id": request.get("tenant_id", "default"),
            "request_size": len(request.get("body", b"")),
            "response_size": len(response.get("body", b"")) if response else 0,
            "status_code": response.get("status_code", 0) if response else 0,
            "error": error,
        }
        
        # Filter headers
        if request.get("headers"):
            filtered_headers = {
                k: v for k, v in request.get("headers", {}).items()
                if k.lower() not in [h.lower() for h in self.config.exclude_headers]
            }
            if self.config.include_request_body:
                entry["request_headers"] = filtered_headers
        
        if response and response.get("headers"):
            filtered_response_headers = {
                k: v for k, v in response.get("headers", {}).items()
                if k.lower() not in [h.lower() for h in self.config.exclude_headers]
            }
            entry["response_headers"] = filtered_response_headers
        
        # Add request/response bodies if enabled
        if self.config.include_request_body:
            body = request.get("body", b"")
            if len(body) <= self.config.max_body_size:
                try:
                    entry["request_body"] = body.decode("utf-8", errors="replace")
                except:
                    entry["request_body"] = "<binary>"
        
        if response and self.config.include_response_body:
            body = response.get("body", b"")
            if len(body) <= self.config.max_body_size:
                try:
                    entry["response_body"] = response["body"].decode("utf-8", errors="replace")
                except:
                    entry["response_body"] = "<binary>"
        
        # Add to buffer
        await self._add_to_buffer(entry)
    
    async def _add_to_buffer(self, entry: Dict):
        async with asyncio.Lock():
            self._buffer.append(entry)
            if len(self._buffer) >= self._buffer_size:
                await self._flush_buffer()
    
    async def _flush_buffer(self):
        if not self._buffer:
            return
        
        entries = self._buffer[:]
        self._buffer.clear()
        
        # Write to log (in production, send to log aggregation system)
        for entry in entries:
            self._logger.info(json.dumps(entry, default=str))
    
    async def _flush_loop(self):
        while True:
            await asyncio.sleep(self._flush_interval)
            await self._flush_buffer()
    
    async def get_stats(self) -> Dict[str, Any]:
        return {
            "buffer_size": len(self._buffer),
            "flush_interval": self._flush_interval,
            "running": self._running,
        }


class AccessLogPlugin:
    """Structured access log plugin with multiple output formats."""
    
    def __init__(
        self,
        log_format: str = "json",  # json, common, combined, custom
        output: str = "stdout",  # stdout, file, syslog
        file_path: Optional[str] = None,
        max_file_size: int = 100 * 1024 * 1024,  # 100MB
        backup_count: int = 10,
    ):
        self.format = log_format
        self.output = output
        self.file_path = file_path
        self.max_file_size = max_file_size
        self.backup_count = backup_count
        
        self._setup_logger()
    
    def _setup_logger(self):
        self.logger = logging.getLogger("gateway.access")
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        if self.output == "stdout":
            handler = logging.StreamHandler()
        elif self.output == "file" and self.file_path:
            from logging.handlers import RotatingFileHandler
            handler = logging.handlers.RotatingFileHandler(
                self.file_path,
                maxBytes=self.max_file_size,
                backupCount=self.backup_count,
            )
        else:
            handler = logging.StreamHandler()
        
        if self.format == "json":
            formatter = logging.Formatter('%(message)s')
        elif self.format == "common":
            formatter = logging.Formatter(
                '%(client_ip)s - - [%(timestamp)s] "%(method)s %(path)s HTTP/1.1" '
                '%(status_code)s %(response_size)s "%(referer)s" "%(user_agent)s"'
            )
        elif self.format == "combined":
            formatter = logging.Formatter(
                '%(client_ip)s - - [%(timestamp)s] "%(method)s %(path)s HTTP/1.1" '
                '%(status_code)s %(response_size)s "%(referer)s" "%(user_agent)s"'
            )
        else:
            formatter = logging.Formatter('%(message)s')
        
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
    
    def log_request(
        self,
        method: str,
        path: str,
        status_code: int,
        response_size: int,
        client_ip: str,
        user_agent: str = "",
        referer: str = "",
        latency_ms: float = 0,
        **extra
    ):
        """Log access in common/combined format."""
        extra = {
            "method": "GET",  # Will be overridden
            "path": "/",
            "status_code": 200,
            "response_size": 0,
            "client_ip": "127.0.0.1",
            "user_agent": "",
            "referer": "",
            "latency_ms": 0,
        }
        self.logger.info("", extra=extra)
    
    def log_json(
        self,
        method: str,
        path: str,
        status_code: int,
        response_size: int,
        client_ip: str,
        user_agent: str = "",
        referer: str = "",
        latency_ms: float = 0,
        **extra
    ):
        """Log in JSON format."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "method": method,
            "path": path,
            "status_code": status_code,
            "response_size": response_size,
            "client_ip": client_ip,
            "user_agent": user_agent,
            "referer": referer,
            "latency_ms": latency_ms,
        }
        self.logger.info(json.dumps(self._sanitize(entry), default=str))
    
    def _sanitize(self, data: Dict) -> Dict:
        """Sanitize sensitive data."""
        sanitized = {}
        sensitive_keys = {"password", "token", "secret", "key", "auth", "authorization"}
        for k, v in data.items():
            if any(s in k.lower() for s in ["password", "token", "secret", "key", "auth"]):
                sanitized[k] = "***REDACTED***"
            else:
                sanitized[k] = v
        return sanitized


class StructuredLogMiddleware:
    """Middleware that adds structured logging to requests."""
    
    def __init__(
        self,
        logger: logging.Logger,
        include_request_body: bool = False,
        include_response_body: bool = False,
        max_body_size: int = 1024 * 1024,
        exclude_paths: List[str] = None,
    ):
        self.logger = logger
        self.include_request_body = include_request_body
        self.include_response_body = include_response_body
        self.max_body_size = max_body_size
        self.exclude_paths = exclude_paths or ["/health", "/metrics", "/ready", "/live"]
    
    async def __call__(self, request: Dict, next_handler: Callable) -> Dict:
        # Check excluded paths
        path = request.get("path", "")
        if any(request.get("path", "").startswith(p) for p in self.exclude_paths):
            return await self._call_next(request)
        
        start_time = time.time()
        trace_id = request.get("trace_id", "")
        span_id = request.get("span_id", "")
        
        # Log request
        self._log_request(request, trace_id, span_id)
        
        start_time = time.time()
        try:
            response = await self._call_next(request)
            latency_ms = (time.time() - start_time) * 1000
            
            # Log response
            self._log_response(request, response, latency_ms)
            
            return response
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            self._log_error(request, e, latency_ms)
            raise
    
    def _log_request(self, request: Dict, trace_id: str, span_id: str):
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "trace_id": trace_id,
            "span_id": span_id,
            "method": request.get("method"),
            "path": request.get("path"),
            "query": request.get("query_string", ""),
            "client_ip": request.get("client_ip"),
            "user_agent": request.get("headers", {}).get("user-agent", ""),
            "request_size": len(request.get("body", b"")),
        }
        if self.include_request_body and request.get("body"):
            body = request.get("body", b"")
            if len(body) <= 1024:
                try:
                    entry["request_body"] = body.decode("utf-8", errors="replace")
                except:
                    entry["request_body"] = "<binary>"
        
        logging.getLogger("gateway.request").info(json.dumps(entry, default=str))
    
    def _log_response(self, request: Dict, response: Dict, latency_ms: float):
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "trace_id": request.get("trace_id", ""),
            "span_id": request.get("span_id", ""),
            "method": request.get("method"),
            "path": request.get("path"),
            "status_code": response.get("status_code", 0),
            "latency_ms": latency_ms,
            "response_size": len(response.get("body", b"")),
        }
        if hasattr(self, 'include_response_body') and self.include_response_body:
            body = response.get("body", b"")
            if len(body) <= 1024:
                try:
                    entry["response_body"] = body.decode("utf-8", errors="replace")
                except:
                    entry["response_body"] = "<binary>"
        
        logging.getLogger("gateway.response").info(json.dumps(entry, default=str))
    
    def _log_error(self, request: Dict, error: Exception, latency_ms: float):
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "trace_id": request.get("trace_id", ""),
            "span_id": request.get("span_id", ""),
            "method": request.get("method"),
            "path": request.get("path"),
            "error": str(error),
            "error_type": type(error).__name__,
            "latency_ms": latency_ms,
        }
        logging.getLogger("gateway.error").error(json.dumps(entry, default=str))
    
    async def _call_next(self, request):
        # Placeholder - in real implementation, this would call the next handler
        return {"status_code": 200, "body": b"OK", "headers": {}}


# =============================================================================
# Factory Functions
# =============================================================================

def create_logging_plugin(config: Optional[Dict] = None) -> RequestLoggingPlugin:
    return RequestLoggingPlugin(config)

def create_access_log_plugin(
    log_format: str = "json",
    output: str = "stdout",
    file_path: Optional[str] = None,
) -> AccessLogPlugin:
    return AccessLogPlugin(log_format, output, file_path)

def create_structured_logger(
    logger: logging.Logger,
    include_request_body: bool = False,
    include_response_body: bool = False,
    max_body_size: int = 1024 * 1024,
    exclude_paths: List[str] = None,
) -> StructuredLogMiddleware:
    return StructuredLogMiddleware(
        logging.getLogger("gateway"),
        include_request_body,
        include_response_body,
        max_body_size,
        exclude_paths,
    )

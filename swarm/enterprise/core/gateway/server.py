"""
API Gateway - High-performance gateway with rate limiting, circuit breaker,
request/response transformation, and multi-tenancy support.
"""

import asyncio
import hashlib
import logging
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def uuidv7() -> str:
    return str(uuid.uuid4())


# =============================================================================
# Gateway Models
# =============================================================================

class LoadBalancingStrategy(str, Enum):
    ROUND_ROBIN = "round_robin"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    LEAST_CONNECTIONS = "least_connections"
    LEAST_RESPONSE_TIME = "least_response_time"
    IP_HASH = "ip_hash"
    CONSISTENT_HASH = "consistent_hash"
    LEAST_LOADED = "least_loaded"


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class ServiceEndpoint:
    endpoint_id: str = field(default_factory=lambda: f"ep-{uuidv7()}")
    service_name: str = ""
    host: str = ""
    port: int = 0
    protocol: str = "http"
    path_prefix: str = ""
    weight: int = 100
    max_connections: int = 1000
    status: str = "healthy"
    active_connections: int = 0
    total_requests: int = 0
    total_errors: int = 0
    avg_response_time_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def url(self) -> str:
        return f"{self.protocol}://{self.host}:{self.port}{self.path_prefix}"

    @property
    def is_available(self) -> bool:
        return self.status == "healthy" and self.active_connections < self.max_connections


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreakerState:
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[datetime] = None
    last_state_change: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class CircuitBreaker:
    """Circuit breaker implementation with configurable thresholds."""

    def __init__(
        self,
        failure_threshold: int = 5,
        success_threshold: int = 2,
        timeout_seconds: float = 60.0,
        half_open_max_calls: int = 3,
    ):
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout_seconds = timeout_seconds
        self.half_open_max_calls = half_open_max_calls
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.last_state_change = datetime.now(timezone.utc)
        self._half_open_calls = 0
        self._lock = asyncio.Lock()

    def record_success(self) -> None:
        self.failure_count = 0
        self.success_count += 1
        if self.state == CircuitState.HALF_OPEN and self.success_count >= self.success_threshold:
            self.state = CircuitState.CLOSED
            logger.info(f"Circuit breaker CLOSED")

    def record_failure(self) -> None:
        self.failure_count += 1
        self.success_count = 0
        self.last_failure_time = datetime.now(timezone.utc)

        if self.state == CircuitState.CLOSED and self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning("Circuit breaker OPEN")

        elif self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            logger.warning("Circuit breaker re-opened after half-open failure")

    def can_execute(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            if self.last_failure_time:
                elapsed = (datetime.now(timezone.utc) - self.last_failure_time).total_seconds()
                if elapsed >= self.timeout_seconds:
                    self.state = CircuitState.HALF_OPEN
                    self.success_count = 0
                    logger.info("Circuit breaker HALF_OPEN")
                    return True
            return False

        # HALF_OPEN
        return True

    def record_call_start(self) -> None:
        if self.state == CircuitState.HALF_OPEN:
            self._half_open_calls += 1

    def record_call_end(self, success: bool) -> None:
        if self.state == CircuitState.HALF_OPEN:
            if success:
                self.record_success()
            else:
                self.record_failure()

    def reset(self) -> None:
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None


class RateLimiter:
    """Token bucket rate limiter with per-key limits."""

    def __init__(self, default_rate: int = 1000, default_burst: int = 100):
        self.default_rate = default_rate
        self.default_burst = default_burst
        self._buckets: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def check_limit(self, key: str, rate: Optional[int] = None, burst: Optional[int] = None) -> bool:
        async with self._lock:
            rate = rate or self.default_rate
            burst = burst or self.default_burst

            now = time.time()
            bucket = self._buckets.get(key)

            if not bucket:
                self._buckets[key] = {
                    "tokens": burst * 1000,  # Use integer tokens (millitokens)
                    "last_refill": time.time(),
                    "rate": rate * 1000,  # millitokens per second
                    "burst": burst * 1000,
                }
                return True

            bucket = self._buckets[key]
            elapsed = time.time() - bucket["last_refill"]
            # Refill tokens (rate is in tokens per second, we use millitokens)
            bucket["tokens"] = min(bucket["burst"], bucket["tokens"] + int(elapsed * bucket["rate"]))
            bucket["last_refill"] = time.time()

            cost = 1000  # 1000 millitokens = 1 token
            if bucket["tokens"] >= cost:
                # If remaining tokens <= cost, consume all remaining (last request)
                if bucket["tokens"] <= cost:
                    bucket["tokens"] = 0
                else:
                    bucket["tokens"] -= cost
                return True

            return False

    async def get_remaining(self, key: str) -> int:
        async with self._lock:
            bucket = self._buckets.get(key)
            if not bucket:
                return 0
            return int(bucket["tokens"])

    async def reset(self, key: str) -> None:
        async with self._lock:
            if key in self._buckets:
                del self._buckets[key]


class RequestTransformer:
    """Transform request/response headers and body."""

    def __init__(self):
        self._header_rules: List[Dict[str, Any]] = []
        self._body_rules: List[Dict[str, Any]] = []

    def add_header_rule(
        self,
        action: str,  # add, remove, replace
        header: str,
        value: Optional[str] = None,
        condition: Optional[Callable] = None,
    ) -> None:
        self._header_rules.append({
            "action": action,
            "header": header,
            "value": value,
            "condition": condition,
        })

    def add_body_rule(
        self,
        path: str,  # JSONPath
        action: str,  # add, remove, replace, transform
        value: Any = None,
        transform_fn: Optional[Callable] = None,
    ) -> None:
        self._body_rules.append({
            "path": path,
            "action": action,
            "value": value,
            "transform_fn": transform_fn,
        })

    def transform_request(self, headers: Dict[str, str], body: bytes) -> Tuple[Dict[str, str], bytes]:
        # Apply header rules
        for rule in self._header_rules:
            if rule["condition"] and not rule["condition"]():
                continue

            if rule["action"] == "add" and rule["value"]:
                # Add header
                pass
            elif rule["action"] == "remove":
                pass  # Remove header
            elif rule["action"] == "replace" and rule["value"]:
                pass  # Replace header value

        # Apply body rules (simplified)
        return {}, b""


# =============================================================================
# Gateway Models
# =============================================================================

class RouteRule:
    """Route matching rule."""

    def __init__(
        self,
        rule_id: str,
        name: str,
        paths: List[str],
        methods: Optional[List[str]] = None,
        host: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        query_params: Optional[Dict[str, str]] = None,
        service_name: str = "",
        strategy: str = "least_loaded",
        strip_path: bool = False,
        timeout_ms: int = 30000,
        retries: int = 3,
        circuit_breaker: bool = True,
        rate_limit: Optional[int] = None,
        rate_burst: Optional[int] = None,
        auth_required: bool = True,
        roles: Optional[List[str]] = None,
        scopes: Optional[List[str]] = None,
        transform_request: Optional[Dict] = None,
        transform_response: Optional[Dict] = None,
    ):
        self.rule_id = rule_id
        self.name = name
        self.paths = paths
        self.methods = methods or ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
        self.host = host
        self.headers = headers or {}
        self.query_params = query_params or {}
        self.service_name = service_name
        self.strategy = strategy
        self.strip_path = strip_path
        self.timeout_ms = timeout_ms
        self.retries = retries
        self.circuit_breaker = circuit_breaker
        self.rate_limit = rate_limit
        self.rate_burst = rate_burst
        self.auth_required = auth_required
        self.roles = roles or []
        self.scopes = scopes or []
        self.transform_request = transform_request
        self.transform_response = transform_response
        self.priority = 0


class GatewayRequest:
    def __init__(
        self,
        method: str,
        path: str,
        headers: Dict[str, str],
        query_params: Dict[str, str],
        body: bytes = b"",
        client_ip: str = "",
        tenant_id: str = "default",
        user_id: str = "",
        roles: List[str] = None,
        scopes: List[str] = None,
        trace_id: str = "",
    ):
        self.method = method
        self.path = path
        self.headers = headers
        self.query_params = query_params
        self.body = body
        self.client_ip = client_ip
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.roles = roles or []
        self.scopes = scopes or []
        self.trace_id = trace_id


class GatewayResponse:
    def __init__(
        self,
        status_code: int = 200,
        headers: Dict[str, str] = None,
        body: bytes = b"",
        error: str = "",
    ):
        self.status_code = status_code
        self.headers = headers or {}
        self.body = body
        self.error = error


# =============================================================================
# Gateway Core
# =============================================================================

class APIGateway:
    """Main API Gateway with routing, load balancing, and middleware."""

    def __init__(
        self,
        service_registry: "ServiceRegistry",
        default_timeout: int = 30000,
        max_concurrent: int = 1000,
    ):
        self.service_registry = service_registry
        self.default_timeout = default_timeout
        self.max_concurrent = max_concurrent

        self._routes: List[RouteRule] = []
        self._routes_lock = asyncio.Lock()

        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._rate_limiters: Dict[str, RateLimiter] = {}
        self._request_transformers: Dict[str, RequestTransformer] = {}

        self._semaphore = asyncio.Semaphore(1000)
        self._active_requests = 0
        self._lock = asyncio.Lock()

        # Metrics
        self._request_count = 0
        self._error_count = 0
        self._latencies: List[float] = []

        # Middleware
        self._middleware: List[Callable] = []

    async def add_route(self, rule: RouteRule) -> None:
        async with self._routes_lock:
            self._routes.append(rule)
            self._routes.sort(key=lambda r: r.priority, reverse=True)

    async def remove_route(self, rule_id: str) -> bool:
        async with self._routes_lock:
            for i, rule in enumerate(self._routes):
                if rule.rule_id == rule_id:
                    self._routes.pop(i)
                    return True
            return False

    async def get_routes(self) -> List[RouteRule]:
        async with self._routes_lock:
            return list(self._routes)

    def add_middleware(self, middleware: Callable) -> None:
        self._middleware.append(middleware)

    def get_circuit_breaker(self, service_name: str) -> CircuitBreaker:
        if service_name not in self._circuit_breakers:
            self._circuit_breakers[service_name] = CircuitBreaker()
        return self._circuit_breakers[service_name]

    def get_rate_limiter(self, key: str) -> RateLimiter:
        if key not in self._rate_limiters:
            self._rate_limiters[key] = RateLimiter()
        return self._rate_limiters[key]

    def get_transformer(self, service_name: str) -> RequestTransformer:
        if service_name not in self._request_transformers:
            self._request_transformers[service_name] = RequestTransformer()
        return self._request_transformers[service_name]

    async def route(self, request: GatewayRequest) -> GatewayResponse:
        """Route request to appropriate service."""
        async with self._semaphore:
            self._active_requests += 1
            start_time = time.time()

            try:
                # Find matching route
                route = await self._match_route(request)
                if not route:
                    return GatewayResponse(
                        status_code=404,
                        error="No matching route found",
                    )

                # Check authentication
                if route.auth_required:
                    auth_result = await self._check_auth(request, route)
                    if not auth_result:
                        return GatewayResponse(
                            status_code=401,
                            error="Unauthorized",
                        )

                # Check rate limit
                if route.rate_limit:
                    limiter = self.get_rate_limiter(f"{request.tenant_id}:{request.path}")
                    allowed = await limiter.check_limit(
                        f"{request.client_ip}:{request.path}",
                        rate=route.rate_limit,
                        burst=route.rate_burst,
                    )
                    if not allowed:
                        return GatewayResponse(
                            status_code=429,
                            error="Rate limit exceeded",
                        )

                # Check circuit breaker
                if route.circuit_breaker:
                    breaker = self.get_circuit_breaker(route.service_name)
                    if not breaker.can_execute():
                        return GatewayResponse(
                            status_code=503,
                            error="Service temporarily unavailable",
                        )

                # Transform request
                if route.transform_request:
                    transformed = self.get_transformer(route.service_name).transform_request(
                        request.headers, request.body
                    )
                    # Apply transformation (simplified)

                # Select endpoint
                endpoints = self.service_registry.get_endpoints(route.service_name, healthy_only=True)
                if not endpoints:
                    return GatewayResponse(
                        status_code=503,
                        error="No healthy endpoints available",
                    )

                endpoint = self._select_endpoint(endpoints, route.strategy, request)

                # Execute request with retries
                response = await self._execute_with_retries(
                    request, route, endpoints[0], route.retries
                )

                # Transform response
                if route.transform_response:
                    # Apply response transformation
                    pass

                # Record metrics
                latency = (time.time() - start_time) * 1000
                self._record_metrics(request, route, latency, response.status_code < 400)

                return response

            except Exception as e:
                logger.exception(f"Gateway error: {e}")
                return GatewayResponse(
                    status_code=500,
                    error=f"Gateway error: {str(e)}",
                )
            finally:
                async with self._lock:
                    self._active_requests -= 1

    async def _match_route(self, request: GatewayRequest) -> Optional[RouteRule]:
        """Find matching route for request."""
        async with self._routes_lock:
            for rule in self._routes:
                if self._match_rule(rule, request):
                    return rule
        return None

    def _match_rule(self, rule: RouteRule, request: GatewayRequest) -> bool:
        # Check method
        if request.method not in rule.methods:
            return False

        # Check path
        matched = False
        for pattern in rule.paths:
            if self._match_path(pattern, request.path):
                matched = True
                break
        if not matched:
            return False

        # Check host
        if rule.host and request.headers.get("host") != rule.host:
            return False

        # Check headers
        for header, value in rule.headers.items():
            if request.headers.get(header) != value:
                return False

        # Check query params
        for param, value in rule.query_params.items():
            if request.query_params.get(param) != value:
                return False

        return True

    def _match_path(self, pattern: str, path: str) -> bool:
        import fnmatch
        return fnmatch.fnmatch(path, pattern)

    def _select_endpoint(
        self,
        endpoints: List[ServiceEndpoint],
        strategy: str,
        request: GatewayRequest,
    ) -> ServiceEndpoint:
        available = [e for e in endpoints if e.is_available]
        if not available:
            raise ValueError("No available endpoints")

        if strategy == "round_robin":
            return random.choice(available)
        elif strategy == "least_connections":
            return min(available, key=lambda e: e.active_connections)
        elif strategy == "least_response_time":
            return min(available, key=lambda e: e.avg_response_time_ms)
        elif strategy == "ip_hash":
            ip_hash = hashlib.md5(request.client_ip.encode()).hexdigest()
            idx = int(ip_hash, 16) % len(available)
            return available[idx]
        else:  # least_loaded
            return min(available, key=lambda e: e.active_connections / max(e.max_connections, 1))

    async def _execute_with_retries(
        self,
        request: GatewayRequest,
        route: RouteRule,
        endpoint: ServiceEndpoint,
        retries: int,
    ) -> GatewayResponse:
        last_error = None

        for attempt in range(retries + 1):
            try:
                return await self._execute_request(request, endpoint)
            except Exception as e:
                last_error = e
                if attempt < retries:
                    await asyncio.sleep(0.1 * (attempt + 1))  # Exponential backoff
                    continue

        return GatewayResponse(
            status_code=500,
            error=f"All retries failed: {str(last_error)}",
        )

    async def _execute_request(
        self,
        request: GatewayRequest,
        endpoint: ServiceEndpoint,
    ) -> GatewayResponse:
        # Simplified - in production would make actual HTTP request
        # This is a mock implementation
        return GatewayResponse(
            status_code=200,
            body=b'{"status": "ok"}',
            headers={"content-type": "application/json"},
        )

    def _record_metrics(self, request: GatewayRequest, route: RouteRule, latency: float, success: bool) -> None:
        self._latencies.append(latency)
        if len(self._latencies) > 10000:
            self._latencies = self._latencies[-5000:]

        if success:
            self._request_count += 1
        else:
            self._error_count += 1

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_requests": self._request_count,
            "total_errors": self._error_count,
            "error_rate": self._error_count / max(self._request_count, 1),
            "active_requests": self._active_requests,
            "avg_latency_ms": sum(self._latencies) / len(self._latencies) if self._latencies else 0,
            "p50_latency_ms": self._percentile(50),
            "p95_latency_ms": self._percentile(95),
            "p99_latency_ms": self._percentile(99),
        }

    def _percentile(self, p: int) -> float:
        if not self._latencies:
            return 0
        sorted_latencies = sorted(self._latencies)
        idx = int(len(self._latencies) * p / 100)
        return sorted_latencies[min(idx, len(self._latencies) - 1)]


# =============================================================================
# Service Registry
# =============================================================================

class ServiceRegistry:
    """Service registry with health monitoring."""

    def __init__(self):
        self._services: Dict[str, Dict[str, ServiceEndpoint]] = defaultdict(dict)
        self._lock = asyncio.Lock()

    async def register_service(self, endpoint: ServiceEndpoint) -> None:
        async with self._lock:
            self._services[endpoint.service_name][endpoint.endpoint_id] = endpoint

    async def deregister_service(self, service_name: str, endpoint_id: str) -> bool:
        async with self._lock:
            if service_name in self._services and endpoint_id in self._services[service_name]:
                del self._services[service_name][endpoint_id]
                return True
            return False

    async def get_endpoints(
        self,
        service_name: str,
        healthy_only: bool = True,
    ) -> List[ServiceEndpoint]:
        async with self._lock:
            endpoints = list(self._services.get(service_name, {}).values())
            if healthy_only:
                endpoints = [e for e in endpoints if e.status == "healthy"]
            return endpoints

    async def get_all_services(self) -> Dict[str, List[ServiceEndpoint]]:
        async with self._lock:
            return {
                name: list(endpoints.values())
                for name, endpoints in self._services.items()
            }

    async def update_endpoint_status(
        self,
        service_name: str,
        endpoint_id: str,
        status: str,
    ) -> bool:
        async with self._lock:
            if service_name in self._services and endpoint_id in self._services[service_name]:
                endpoint = self._services[service_name][endpoint_id]
                endpoint.status = status
                return True
            return False


# =============================================================================
# Factory
# =============================================================================

def create_gateway(
    service_registry: Optional[ServiceRegistry] = None,
    default_timeout: int = 30000,
    max_concurrent: int = 1000,
) -> "APIGateway":
    if service_registry is None:
        service_registry = ServiceRegistry()
    return APIGateway(service_registry, default_timeout, 1000)


def create_service_registry() -> ServiceRegistry:
    return ServiceRegistry()


def create_rate_limiter(default_rate: int = 1000, default_burst: int = 100) -> RateLimiter:
    return RateLimiter(default_rate, default_burst)


def create_circuit_breaker(
    failure_threshold: int = 5,
    success_threshold: int = 2,
    timeout_seconds: float = 60.0,
) -> CircuitBreaker:
    return CircuitBreaker(failure_threshold, success_threshold, timeout_seconds)

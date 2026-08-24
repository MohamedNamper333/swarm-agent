"""
Routing Service - Intelligent request routing, load balancing, and service discovery.
"""

import asyncio
import threading
import time
import uuid
import hashlib
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from collections import defaultdict, deque
import logging

logger = logging.getLogger(__name__)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def uuidv7() -> str:
    return str(uuid.uuid4())


# =============================================================================
# Routing Models
# =============================================================================

class RoutingStrategy(str, Enum):
    """Load balancing strategies."""
    ROUND_ROBIN = "round_robin"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    LEAST_CONNECTIONS = "least_connections"
    LEAST_RESPONSE_TIME = "least_response_time"
    IP_HASH = "ip_hash"
    CONSISTENT_HASH = "consistent_hash"
    RANDOM = "random"
    WEIGHTED_RANDOM = "weighted_random"
    LEAST_LOADED = "least_loaded"
    ADAPTIVE = "adaptive"


class ServiceStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    DRAINING = "draining"
    UNKNOWN = "unknown"


@dataclass
class ServiceEndpoint:
    """A service endpoint that can receive traffic."""
    endpoint_id: str = field(default_factory=lambda: f"ep-{uuidv7()}")
    service_name: str = ""
    host: str = ""
    port: int = 0
    protocol: str = "http"  # http, grpc, ws
    path_prefix: str = ""
    
    # Metadata
    version: str = "1.0.0"
    region: str = "default"
    zone: str = "default"
    tags: Dict[str, str] = field(default_factory=dict)
    
    # Load balancing
    weight: int = 100
    max_connections: int = 1000
    
    # Health
    status: ServiceStatus = ServiceStatus.HEALTHY
    last_health_check: Optional[datetime] = None
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    
    # Metrics
    active_connections: int = 0
    total_requests: int = 0
    total_errors: int = 0
    avg_response_time_ms: float = 0.0
    
    # Circuit breaker
    circuit_open: bool = False
    circuit_open_at: Optional[datetime] = None
    
    def __post_init__(self):
        if not self.endpoint_id:
            self.endpoint_id = f"ep-{uuidv7()}"
    
    @property
    def url(self) -> str:
        return f"{self.protocol}://{self.host}:{self.port}{self.path_prefix}"
    
    @property
    def is_available(self) -> bool:
        return (self.status == ServiceStatus.HEALTHY and 
                not self.circuit_open and 
                self.active_connections < self.max_connections)
    
    @property
    def error_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.total_errors / self.total_requests


@dataclass
class RouteRule:
    """A routing rule that matches requests to services."""
    rule_id: str = field(default_factory=lambda: f"route-{uuidv7()}")
    name: str = ""
    description: str = ""
    enabled: bool = True
    priority: int = 100  # Lower = higher priority
    
    # Matching criteria
    path_patterns: List[str] = field(default_factory=list)  # glob patterns
    methods: List[str] = field(default_factory=list)  # HTTP methods
    headers: Dict[str, str] = field(default_factory=dict)  # Header match
    query_params: Dict[str, str] = field(default_factory=dict)
    
    # Tenant/actor isolation
    tenant_ids: List[str] = field(default_factory=list)
    actor_types: List[str] = field(default_factory=list)
    
    # Routing target
    service_name: str = ""
    strategy: RoutingStrategy = RoutingStrategy.LEAST_LOADED
    sticky_session: bool = False
    sticky_cookie: str = "swarm_session"
    sticky_ttl_seconds: int = 3600
    
    # Retry/timeout
    timeout_ms: int = 30000
    max_retries: int = 3
    retry_backoff_ms: int = 100
    
    # Circuit breaker
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout_seconds: int = 60
    
    # Canary/blue-green
    canary_percentage: float = 0.0
    canary_service: str = ""
    
    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def matches(self, request: "RouteRequest") -> bool:
        """Check if this rule matches the request."""
        if not self.enabled:
            return False
        
        # Check path patterns
        if self.path_patterns:
            import fnmatch
            matched = False
            for pattern in self.path_patterns:
                if fnmatch.fnmatch(request.path, pattern):
                    matched = True
                    break
            if not matched:
                return False
        
        # Check methods
        if self.methods and request.method not in self.methods:
            return False
        
        # Check headers
        for header, value in self.headers.items():
            if request.headers.get(header) != value:
                return False
        
        # Check query params
        for param, value in self.query_params.items():
            if request.query_params.get(param) != value:
                return False
        
        # Check tenant
        if self.tenant_ids and request.tenant_id not in self.tenant_ids:
            return False
        
        # Check actor type
        if self.actor_types and request.actor_type not in self.actor_types:
            return False
        
        return True


@dataclass
class RouteRequest:
    """A request to be routed."""
    path: str
    method: str
    headers: Dict[str, str] = field(default_factory=dict)
    query_params: Dict[str, str] = field(default_factory=dict)
    body: Any = None
    tenant_id: str = "default"
    actor_id: str = ""
    actor_type: str = "user"
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    client_ip: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RouteResult:
    """Result of routing decision."""
    success: bool
    endpoint: Optional[ServiceEndpoint] = None
    rule: Optional[RouteRule] = None
    error: Optional[str] = None
    latency_ms: float = 0.0
    is_canary: bool = False
    sticky_cookie_value: Optional[str] = None


# =============================================================================
# Load Balancers
# =============================================================================

class LoadBalancer(ABC):
    """Abstract load balancer."""
    
    @abstractmethod
    def select_endpoint(
        self,
        endpoints: List[ServiceEndpoint],
        request: RouteRequest,
        rule: RouteRule,
    ) -> Optional[ServiceEndpoint]:
        """Select an endpoint from the available pool."""
        pass
    
    @abstractmethod
    def update_metrics(self, endpoint: ServiceEndpoint, response_time_ms: float, success: bool) -> None:
        """Update endpoint metrics after request."""
        pass


class RoundRobinBalancer(LoadBalancer):
    """Simple round-robin load balancer."""
    
    def __init__(self):
        self._counters: Dict[str, int] = defaultdict(int)
        self._lock = threading.Lock()
    
    def select_endpoint(
        self,
        endpoints: List[ServiceEndpoint],
        request: RouteRequest,
        rule: RouteRule,
    ) -> Optional[ServiceEndpoint]:
        available = [e for e in endpoints if e.is_available]
        if not available:
            return None
        
        with self._lock:
            key = f"{rule.service_name}"
            idx = self._counters[key] % len(available)
            self._counters[key] += 1
            return available[idx]
    
    def update_metrics(self, endpoint: ServiceEndpoint, response_time_ms: float, success: bool) -> None:
        pass


class WeightedRoundRobinBalancer(LoadBalancer):
    """Weighted round-robin load balancer."""
    
    def __init__(self):
        self._weights: Dict[str, int] = {}
        self._current: Dict[str, int] = defaultdict(int)
        self._lock = threading.Lock()
    
    def select_endpoint(
        self,
        endpoints: List[ServiceEndpoint],
        request: RouteRequest,
        rule: RouteRule,
    ) -> Optional[ServiceEndpoint]:
        available = [e for e in endpoints if e.is_available]
        if not available:
            return None
        
        with self._lock:
            key = f"{rule.service_name}"
            
            # Calculate effective weights
            total_weight = sum(e.weight for e in available)
            if total_weight == 0:
                return random.choice(available)
            
            # Smooth weighted round-robin
            self._current[key] = (self._current[key] + 1) % total_weight
            current = self._current[key]
            
            for endpoint in available:
                current -= endpoint.weight
                if current < 0:
                    return endpoint
            
            return available[0]
    
    def update_metrics(self, endpoint: ServiceEndpoint, response_time_ms: float, success: bool) -> None:
        pass


class LeastConnectionsBalancer(LoadBalancer):
    """Least connections load balancer."""
    
    def select_endpoint(
        self,
        endpoints: List[ServiceEndpoint],
        request: RouteRequest,
        rule: RouteRule,
    ) -> Optional[ServiceEndpoint]:
        available = [e for e in endpoints if e.is_available]
        if not available:
            return None
        
        return min(available, key=lambda e: e.active_connections)
    
    def update_metrics(self, endpoint: ServiceEndpoint, response_time_ms: float, success: bool) -> None:
        pass


class LeastResponseTimeBalancer(LoadBalancer):
    """Least response time load balancer."""
    
    def select_endpoint(
        self,
        endpoints: List[ServiceEndpoint],
        request: RouteRequest,
        rule: RouteRule,
    ) -> Optional[ServiceEndpoint]:
        available = [e for e in endpoints if e.is_available]
        if not available:
            return None
        
        return min(available, key=lambda e: e.avg_response_time_ms or float('inf'))
    
    def update_metrics(self, endpoint: ServiceEndpoint, response_time_ms: float, success: bool) -> None:
        # Exponential moving average
        alpha = 0.3
        if endpoint.avg_response_time_ms == 0:
            endpoint.avg_response_time_ms = response_time_ms
        else:
            endpoint.avg_response_time_ms = (
                alpha * response_time_ms + (1 - alpha) * endpoint.avg_response_time_ms
            )


class ConsistentHashBalancer(LoadBalancer):
    """Consistent hash load balancer for sticky sessions."""
    
    def __init__(self, virtual_nodes: int = 150):
        self.virtual_nodes = virtual_nodes
        self._ring: Dict[int, ServiceEndpoint] = {}
        self._sorted_keys: List[int] = []
        self._lock = threading.Lock()
    
    def _hash(self, key: str) -> int:
        return int(hashlib.md5(key.encode()).hexdigest(), 16)
    
    def _rebuild_ring(self, endpoints: List[ServiceEndpoint]) -> None:
        with self._lock:
            self._ring = {}
            for endpoint in endpoints:
                if not endpoint.is_available:
                    continue
                for i in range(self.virtual_nodes):
                    key = self._hash(f"{endpoint.endpoint_id}:{i}")
                    self._ring[key] = endpoint
            self._sorted_keys = sorted(self._ring.keys())
    
    def select_endpoint(
        self,
        endpoints: List[ServiceEndpoint],
        request: RouteRequest,
        rule: RouteRule,
    ) -> Optional[ServiceEndpoint]:
        available = [e for e in endpoints if e.is_available]
        if not available:
            return None
        
        # Rebuild ring if endpoints changed
        current_endpoint_ids = {e.endpoint_id for e in available}
        ring_endpoint_ids = {e.endpoint_id for e in self._ring.values()}
        if current_endpoint_ids != ring_endpoint_ids:
            self._rebuild_ring(available)
        
        if not self._ring:
            return None
        
        # Hash the session key for sticky sessions
        session_key = request.headers.get("cookie", "").split("swarm_session=")[-1].split(";")[0]
        if not session_key or session_key == request.headers.get("cookie", ""):
            session_key = f"{request.client_ip}:{request.tenant_id}"
        
        hash_key = self._hash(session_key)
        
        with self._lock:
            # Find the first key >= hash_key
            idx = bisect.bisect_left(self._sorted_keys, hash_key)
            if idx >= len(self._sorted_keys):
                idx = 0
            return self._ring[self._sorted_keys[idx]]
    
    def update_metrics(self, endpoint: ServiceEndpoint, response_time_ms: float, success: bool) -> None:
        pass


class LeastLoadedBalancer(LoadBalancer):
    """Least loaded balancer considering multiple factors."""
    
    def select_endpoint(
        self,
        endpoints: List[ServiceEndpoint],
        request: RouteRequest,
        rule: RouteRule,
    ) -> Optional[ServiceEndpoint]:
        available = [e for e in endpoints if e.is_available]
        if not available:
            return None
        
        def score(endpoint: ServiceEndpoint) -> float:
            # Normalize metrics (0-1)
            conn_score = endpoint.active_connections / max(endpoint.max_connections, 1)
            latency_score = min(endpoint.avg_response_time_ms / 1000.0, 1.0) if endpoint.avg_response_time_ms else 0
            error_score = endpoint.error_rate
            
            # Weighted score (lower is better)
            return (0.4 * conn_score + 0.4 * latency_score + 0.2 * error_score)
        
        return min(available, key=score)
    
    def update_metrics(self, endpoint: ServiceEndpoint, response_time_ms: float, success: bool) -> None:
        pass


class AdaptiveBalancer(LoadBalancer):
    """Adaptive load balancer that learns from performance."""
    
    def __init__(self):
        self._strategies = {
            "least_connections": LeastConnectionsBalancer(),
            "least_response_time": LeastResponseTimeBalancer(),
            "least_loaded": LeastLoadedBalancer(),
        }
        self._current_strategy = "least_loaded"
        self._performance_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self._strategy_scores: Dict[str, float] = {}
        self._last_switch = time.time()
        self._switch_interval = 60  # seconds
    
    def select_endpoint(
        self,
        endpoints: List[ServiceEndpoint],
        request: RouteRequest,
        rule: RouteRule,
    ) -> Optional[ServiceEndpoint]:
        strategy = self._strategies[self._current_strategy]
        return strategy.select_endpoint(endpoints, request, rule)
    
    def update_metrics(self, endpoint: ServiceEndpoint, response_time_ms: float, success: bool) -> None:
        # Record performance
        key = f"{endpoint.service_name}:{self._current_strategy}"
        self._performance_history[key].append({
            "response_time": response_time_ms,
            "success": success,
            "timestamp": time.time(),
        })
        
        # Evaluate strategy performance periodically
        if time.time() - self._last_switch > self._switch_interval:
            self._evaluate_strategies()
            self._last_switch = time.time()
    
    def _evaluate_strategies(self) -> None:
        """Evaluate and potentially switch strategies."""
        for strategy_name in self._strategies:
            key = f"{strategy_name}"
            history = self._performance_history.get(key, [])
            if len(history) < 10:
                continue
            
            avg_response = sum(h["response_time"] for h in history) / len(history)
            success_rate = sum(1 for h in history if h["success"]) / len(history)
            score = success_rate / max(avg_response, 1)
            self._strategy_scores[key] = score
        
        if self._strategy_scores:
            best = max(self._strategy_scores.items(), key=lambda x: x[1])[0]
            if best != self._current_strategy:
                logger.info(f"Switching load balancer strategy to {best}")
                self._current_strategy = best


# Import bisect for ConsistentHashBalancer
import bisect


# =============================================================================
# Service Registry
# =============================================================================

class ServiceRegistry:
    """Registry of services and endpoints with health monitoring."""
    
    def __init__(self):
        self._services: Dict[str, Dict[str, ServiceEndpoint]] = defaultdict(dict)
        self._endpoints: Dict[str, ServiceEndpoint] = {}
        self._lock = threading.RLock()
        
        # Health check callbacks
        self._health_checkers: Dict[str, Callable[[ServiceEndpoint], bool]] = {}
    
    def register_endpoint(self, endpoint: ServiceEndpoint) -> None:
        """Register a service endpoint."""
        with self._lock:
            self._services[endpoint.service_name][endpoint.endpoint_id] = endpoint
            self._endpoints[endpoint.endpoint_id] = endpoint
            logger.info(f"Registered endpoint: {endpoint.endpoint_id} for service {endpoint.service_name}")
    
    def deregister_endpoint(self, endpoint_id: str) -> bool:
        """Deregister an endpoint."""
        with self._lock:
            endpoint = self._endpoints.get(endpoint_id)
            if not endpoint:
                return False
            
            del self._services[endpoint.service_name][endpoint_id]
            del self._endpoints[endpoint_id]
            logger.info(f"Deregistered endpoint: {endpoint_id}")
            return True
    
    def get_endpoints(self, service_name: str, healthy_only: bool = True) -> List[ServiceEndpoint]:
        """Get all endpoints for a service."""
        with self._lock:
            endpoints = list(self._services.get(service_name, {}).values())
            
            if healthy_only:
                endpoints = [e for e in endpoints if e.is_available]
            
            return endpoints
    
    def get_endpoint(self, endpoint_id: str) -> Optional[ServiceEndpoint]:
        """Get a specific endpoint."""
        with self._lock:
            return self._endpoints.get(endpoint_id)
    
    def update_endpoint_status(self, endpoint_id: str, status: ServiceStatus) -> bool:
        """Update endpoint health status."""
        with self._lock:
            endpoint = self._endpoints.get(endpoint_id)
            if not endpoint:
                return False
            
            endpoint.status = status
            endpoint.last_health_check = now_utc()
            
            if status == ServiceStatus.HEALTHY:
                endpoint.consecutive_failures = 0
                endpoint.consecutive_successes += 1
            else:
                endpoint.consecutive_failures += 1
                endpoint.consecutive_successes = 0
                
                # Open circuit breaker after threshold
                if endpoint.consecutive_failures >= 5:
                    endpoint.circuit_open = True
                    endpoint.circuit_open_at = now_utc()
                    logger.warning(f"Circuit breaker opened for {endpoint_id}")
            
            return True
    
    def record_request(self, endpoint_id: str, response_time_ms: float, success: bool) -> None:
        """Record request metrics for an endpoint."""
        with self._lock:
            endpoint = self._endpoints.get(endpoint_id)
            if not endpoint:
                return
            
            endpoint.total_requests += 1
            if not success:
                endpoint.total_errors += 1
            
            # Update average response time (exponential moving average)
            alpha = 0.3
            if endpoint.avg_response_time_ms == 0:
                endpoint.avg_response_time_ms = response_time_ms
            else:
                endpoint.avg_response_time_ms = (
                    alpha * response_time_ms + (1 - alpha) * endpoint.avg_response_time_ms
                )
    
    def get_service_stats(self, service_name: str) -> Dict[str, Any]:
        """Get statistics for a service."""
        with self._lock:
            endpoints = self._services.get(service_name, {})
            
            total_endpoints = len(endpoints)
            healthy = sum(1 for e in endpoints.values() if e.status == ServiceStatus.HEALTHY)
            degraded = sum(1 for e in endpoints.values() if e.status == ServiceStatus.DEGRADED)
            unhealthy = sum(1 for e in endpoints.values() if e.status == ServiceStatus.UNHEALTHY)
            
            total_requests = sum(e.total_requests for e in endpoints.values())
            total_errors = sum(e.total_errors for e in endpoints.values())
            avg_response = sum(e.avg_response_time_ms for e in endpoints.values()) / max(len(endpoints), 1)
            
            return {
                "service_name": service_name,
                "total_endpoints": total_endpoints,
                "healthy": healthy,
                "degraded": degraded,
                "unhealthy": unhealthy,
                "total_requests": total_requests,
                "total_errors": total_errors,
                "error_rate": total_errors / max(total_requests, 1),
                "avg_response_time_ms": avg_response,
            }
    
    def register_health_checker(self, service_name: str, checker: Callable[[ServiceEndpoint], bool]) -> None:
        """Register a custom health checker for a service."""
        self._health_checkers[service_name] = checker
    
    async def run_health_checks(self) -> None:
        """Run health checks on all endpoints."""
        with self._lock:
            endpoints = list(self._endpoints.values())
        
        for endpoint in endpoints:
            # Use custom checker if available
            checker = self._health_checkers.get(endpoint.service_name)
            
            if checker:
                try:
                    is_healthy = await checker(endpoint) if asyncio.iscoroutinefunction(checker) else checker(endpoint)
                    self.update_endpoint_status(endpoint.endpoint_id, ServiceStatus.HEALTHY if is_healthy else ServiceStatus.UNHEALTHY)
                except Exception as e:
                    logger.error(f"Health check failed for {endpoint.endpoint_id}: {e}")
                    self.update_endpoint_status(endpoint.endpoint_id, ServiceStatus.UNHEALTHY)
            else:
                # Default: check if circuit breaker should be closed
                if endpoint.circuit_open and endpoint.circuit_open_at:
                    if (now_utc() - endpoint.circuit_open_at).total_seconds() > 60:
                        endpoint.circuit_open = False
                        endpoint.circuit_open_at = None
                        logger.info(f"Circuit breaker closed for {endpoint.endpoint_id}")


# =============================================================================
# Router
# =============================================================================

class Router:
    """Main router that matches requests to services and load balances."""
    
    def __init__(
        self,
        service_registry: ServiceRegistry,
        default_strategy: RoutingStrategy = RoutingStrategy.LEAST_LOADED,
    ):
        self.service_registry = service_registry
        self.default_strategy = default_strategy
        
        # Route rules (sorted by priority)
        self._rules: List[RouteRule] = []
        self._rules_lock = threading.RLock()
        
        # Load balancers per strategy
        self._balancers: Dict[RoutingStrategy, LoadBalancer] = {
            RoutingStrategy.ROUND_ROBIN: RoundRobinBalancer(),
            RoutingStrategy.WEIGHTED_ROUND_ROBIN: WeightedRoundRobinBalancer(),
            RoutingStrategy.LEAST_CONNECTIONS: LeastConnectionsBalancer(),
            RoutingStrategy.LEAST_RESPONSE_TIME: LeastResponseTimeBalancer(),
            RoutingStrategy.CONSISTENT_HASH: ConsistentHashBalancer(),
            RoutingStrategy.LEAST_LOADED: LeastLoadedBalancer(),
            RoutingStrategy.ADAPTIVE: AdaptiveBalancer(),
        }
        
        # Sticky session store
        self._sticky_sessions: Dict[str, Tuple[str, datetime]] = {}
        self._sticky_lock = threading.RLock()
        
        # Metrics
        self._request_count = 0
        self._error_count = 0
        self._latencies: deque = deque(maxlen=10000)
    
    def add_rule(self, rule: RouteRule) -> None:
        """Add a routing rule."""
        with self._rules_lock:
            self._rules.append(rule)
            # Sort by priority (lower = higher priority)
            self._rules.sort(key=lambda r: r.priority)
    
    def remove_rule(self, rule_id: str) -> bool:
        """Remove a routing rule."""
        with self._rules_lock:
            for i, rule in enumerate(self._rules):
                if rule.rule_id == rule_id:
                    self._rules.pop(i)
                    return True
            return False
    
    def get_rules(self) -> List[RouteRule]:
        """Get all routing rules."""
        with self._rules_lock:
            return list(self._rules)
    
    def route(self, request: RouteRequest) -> RouteResult:
        """Route a request to an endpoint."""
        start_time = time.time()
        self._request_count += 1
        
        # Find matching rule
        matched_rule = None
        with self._rules_lock:
            for rule in self._rules:
                if rule.matches(request):
                    matched_rule = rule
                    break
        
        if not matched_rule:
            return RouteResult(
                success=False,
                error="No matching route rule",
                latency_ms=(time.time() - start_time) * 1000,
            )
        
        # Get endpoints for the service
        endpoints = self.service_registry.get_endpoints(matched_rule.service_name, healthy_only=True)
        
        if not endpoints:
            return RouteResult(
                success=False,
                error=f"No healthy endpoints for service: {matched_rule.service_name}",
                rule=matched_rule,
                latency_ms=(time.time() - start_time) * 1000,
            )
        
        # Check for sticky session
        sticky_value = None
        if matched_rule.sticky_session:
            sticky_value = self._get_sticky_session(request, matched_rule)
            if sticky_value:
                # Try to find the endpoint
                for ep in endpoints:
                    if ep.endpoint_id == sticky_value:
                        return RouteResult(
                            success=True,
                            endpoint=ep,
                            rule=matched_rule,
                            latency_ms=(time.time() - start_time) * 1000,
                            sticky_cookie_value=sticky_value,
                        )
        
        # Select load balancer
        balancer = self._balancers.get(matched_rule.strategy, self._balancers[self.default_strategy])
        
        # Select endpoint
        endpoint = balancer.select_endpoint(endpoints, request, matched_rule)
        
        if not endpoint:
            return RouteResult(
                success=False,
                error="No available endpoint after load balancing",
                rule=matched_rule,
                latency_ms=(time.time() - start_time) * 1000,
            )
        
        # Handle canary
        is_canary = False
        if matched_rule.canary_percentage > 0 and matched_rule.canary_service:
            if random.random() < matched_rule.canary_percentage:
                canary_endpoints = self.service_registry.get_endpoints(matched_rule.canary_service, healthy_only=True)
                if canary_endpoints:
                    endpoint = canary_endpoints[0]
                    is_canary = True
        
        # Store sticky session
        if matched_rule.sticky_session:
            session_value = f"{endpoint.endpoint_id}:{int(time.time() + matched_rule.sticky_ttl_seconds)}"
            self._set_sticky_session(request, matched_rule, session_value)
        
        latency_ms = (time.time() - start_time) * 1000
        self._latencies.append(latency_ms)
        
        return RouteResult(
            success=True,
            endpoint=endpoint,
            rule=matched_rule,
            latency_ms=latency_ms,
            is_canary=is_canary,
            sticky_cookie_value=session_value if matched_rule.sticky_session else None,
        )
    
    def record_request_result(self, result: RouteResult, response_time_ms: float, success: bool) -> None:
        """Record the result of a routed request."""
        if result.endpoint:
            self.service_registry.record_request(result.endpoint.endpoint_id, response_time_ms, success)
            
            # Update balancer metrics
            if result.rule:
                balancer = self._balancers.get(result.rule.strategy)
                if balancer:
                    balancer.update_metrics(result.endpoint, response_time_ms, success)
        
        if success:
            self._latencies.append(response_time_ms)
        else:
            self._error_count += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get router statistics."""
        return {
            "total_requests": self._request_count,
            "total_errors": self._error_count,
            "error_rate": self._error_count / max(self._request_count, 1),
            "avg_latency_ms": sum(self._latencies) / len(self._latencies) if self._latencies else 0,
            "p50_latency_ms": self._percentile(50),
            "p95_latency_ms": self._percentile(95),
            "p99_latency_ms": self._percentile(99),
            "active_rules": len(self._rules),
            "sticky_sessions": len(self._sticky_sessions),
        }
    
    def _percentile(self, p: int) -> float:
        if not self._latencies:
            return 0.0
        sorted_latencies = sorted(self._latencies)
        idx = int(len(sorted_latencies) * p / 100)
        return sorted_latencies[min(idx, len(sorted_latencies) - 1)]
    
    def _get_sticky_session(self, request: RouteRequest, rule: RouteRule) -> Optional[str]:
        """Get sticky session value from request."""
        cookie = request.headers.get("cookie", "")
        cookie_name = rule.sticky_cookie
        for part in cookie.split(";"):
            part = part.strip()
            if part.startswith(f"{cookie_name}="):
                value = part.split("=", 1)[1]
                # Check expiration
                parts = value.split(":")
                if len(parts) == 2:
                    endpoint_id, exp_str = parts
                    try:
                        if int(exp_str) > int(time.time()):
                            return endpoint_id
                    except ValueError:
                        pass
        return None
    
    def _set_sticky_session(self, request: RouteRequest, rule: RouteRule, value: str) -> None:
        """Set sticky session cookie."""
        with self._sticky_lock:
            self._sticky_sessions[value] = (request.tenant_id, now_utc())
    
    def get_sticky_sessions_count(self) -> int:
        return len(self._sticky_sessions)


# =============================================================================
# Service Discovery
# =============================================================================

class ServiceDiscovery:
    """Service discovery with support for multiple backends."""
    
    def __init__(self, service_registry: ServiceRegistry):
        self.service_registry = service_registry
        self._watchers: Dict[str, List[Callable[[List[ServiceEndpoint]], None]]] = defaultdict(list)
        self._lock = threading.RLock()
    
    def register_service(
        self,
        service_name: str,
        host: str,
        port: int,
        protocol: str = "http",
        path_prefix: str = "",
        version: str = "1.0.0",
        region: str = "default",
        zone: str = "default",
        weight: int = 100,
        max_connections: int = 1000,
        tags: Optional[Dict[str, str]] = None,
    ) -> ServiceEndpoint:
        """Register a new service endpoint."""
        endpoint = ServiceEndpoint(
            service_name=service_name,
            host=host,
            port=port,
            protocol=protocol,
            path_prefix=path_prefix,
            version=version,
            region=region,
            zone=zone,
            weight=weight,
            max_connections=max_connections,
            tags=tags or {},
        )
        
        self.service_registry.register_endpoint(endpoint)
        self._notify_watchers(service_name)
        return endpoint
    
    def deregister_service(self, endpoint_id: str) -> bool:
        """Deregister a service endpoint."""
        result = self.service_registry.deregister_endpoint(endpoint_id)
        if result:
            self._notify_watchers("")  # Notify all
        return result
    
    def watch_service(self, service_name: str, callback: Callable[[List[ServiceEndpoint]], None]) -> Callable[[], None]:
        """Watch for service endpoint changes."""
        with self._lock:
            self._watchers[service_name].append(callback)
        
        # Initial notification
        endpoints = self.service_registry.get_endpoints(service_name)
        callback(endpoints)
        
        # Return unsubscribe function
        def unsubscribe():
            with self._lock:
                if service_name in self._watchers:
                    self._watchers[service_name] = [
                        cb for cb in self._watchers[service_name] if cb != callback
                    ]
        
        return unsubscribe
    
    def _notify_watchers(self, service_name: str) -> None:
        """Notify watchers of changes."""
        with self._lock:
            if service_name:
                watchers = self._watchers.get(service_name, []) + self._watchers.get("", [])
            else:
                watchers = self._watchers.get("", [])
            
            for watcher in watchers:
                try:
                    endpoints = self.service_registry.get_endpoints(service_name) if service_name else []
                    watcher(endpoints)
                except Exception as e:
                    logger.error(f"Watcher notification failed: {e}")
    
    def get_service(self, service_name: str) -> List[ServiceEndpoint]:
        """Get all healthy endpoints for a service."""
        return self.service_registry.get_endpoints(service_name)
    
    def get_all_services(self) -> Dict[str, List[ServiceEndpoint]]:
        """Get all services with their endpoints."""
        with self._lock:
            return {
                name: list(endpoints.values())
                for name, endpoints in self.service_registry._services.items()
            }


# =============================================================================
# Factory
# =============================================================================

def create_routing_service(
    default_strategy: RoutingStrategy = RoutingStrategy.LEAST_LOADED,
) -> Tuple[ServiceRegistry, Router, ServiceDiscovery]:
    """Create routing service components."""
    service_registry = ServiceRegistry()
    router = Router(service_registry, default_strategy)
    service_discovery = ServiceDiscovery(service_registry)
    return service_registry, router, service_discovery


def create_route_rule(
    name: str,
    service_name: str,
    path_patterns: List[str],
    **kwargs,
) -> RouteRule:
    """Create a route rule from simple definition."""
    return RouteRule(
        name=name,
        service_name=service_name,
        path_patterns=path_patterns,
        **kwargs,
    )

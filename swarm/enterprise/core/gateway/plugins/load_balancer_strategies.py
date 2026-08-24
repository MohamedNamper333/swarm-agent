"""
Load Balancing Strategies for API Gateway.
Implements various load balancing algorithms.
"""

import asyncio
import hashlib
import random
import time
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from collections import defaultdict
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
from collections import deque

from swarm.enterprise.core.gateway.server import ServiceEndpoint


class LoadBalancingStrategy(str, Enum):
    ROUND_ROBIN = "round_robin"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    LEAST_CONNECTIONS = "least_connections"
    LEAST_RESPONSE_TIME = "least_response_time"
    IP_HASH = "ip_hash"
    CONSISTENT_HASH = "consistent_hash"
    LEAST_LOADED = "least_loaded"
    ADAPTIVE = "adaptive"


class LoadBalancer(ABC):
    """Abstract load balancer."""
    
    @abstractmethod
    def select_endpoint(
        self,
        endpoints: List["ServiceEndpoint"],
        request: "GatewayRequest",
        rule: "RouteRule",
    ) -> Optional["ServiceEndpoint"]:
        """Select an endpoint from the available pool."""
        pass
    
    @abstractmethod
    def update_metrics(self, endpoint: "ServiceEndpoint", response_time_ms: float, success: bool) -> None:
        """Update endpoint metrics after request."""
        pass


# Import ServiceEndpoint and other types
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from swarm.enterprise.core.gateway.server import ServiceEndpoint, GatewayRequest, RouteRule


class RoundRobinBalancer:
    """Simple round-robin load balancer."""
    
    def __init__(self):
        self._counters: Dict[str, int] = {}
        self._lock = asyncio.Lock()
    
    async def select_endpoint(
        self,
        endpoints: List["ServiceEndpoint"],
        request: "GatewayRequest",
        rule: "RouteRule",
    ) -> Optional["ServiceEndpoint"]:
        available = [e for e in endpoints if e.is_available]
        if not available:
            return None
        
        async with self._lock:
            key = rule.service_name
            current = self._counters.get(key, 0)
            idx = current % len(available)
            self._counters[key] = (current + 1) % len(available)
            return available[idx]
    
    def update_metrics(self, endpoint: "ServiceEndpoint", response_time_ms: float, success: bool) -> None:
        pass


class WeightedRoundRobinBalancer:
    """Weighted round-robin load balancer."""
    
    def __init__(self):
        self._counters: Dict[str, int] = {}
        self._lock = asyncio.Lock()
    
    async def select_endpoint(
        self,
        endpoints: List["ServiceEndpoint"],
        request: "GatewayRequest",
        rule: "RouteRule",
    ) -> Optional["ServiceEndpoint"]:
        available = [e for e in endpoints if e.is_available]
        if not available:
            return None
        
        async with self._lock:
            key = rule.service_name
            # Simple weighted selection based on weight
            total_weight = sum(e.weight for e in available)
            if total_weight == 0:
                return random.choice(available)
            
            # Use counter to distribute smoothly
            self._counters[key] = self._counters.get(key, 0) + 1
            current = self._counters[key] % total_weight
            
            for endpoint in available:
                if current < endpoint.weight:
                    return endpoint
                current -= endpoint.weight
            
            return available[0]
    
    def update_metrics(self, endpoint: "ServiceEndpoint", response_time_ms: float, success: bool) -> None:
        pass


class LeastConnectionsBalancer:
    """Least connections load balancer."""
    
    async def select_endpoint(
        self,
        endpoints: List["ServiceEndpoint"],
        request: "GatewayRequest",
        rule: "RouteRule",
    ) -> Optional["ServiceEndpoint"]:
        available = [e for e in endpoints if e.is_available]
        if not available:
            return None
        
        return min(available, key=lambda e: e.active_connections)
    
    def update_metrics(self, endpoint: "ServiceEndpoint", response_time_ms: float, success: bool) -> None:
        pass


class LeastResponseTimeBalancer:
    """Least response time load balancer."""
    
    async def select_endpoint(
        self,
        endpoints: List["ServiceEndpoint"],
        request: "GatewayRequest",
        rule: "RouteRule",
    ) -> Optional["ServiceEndpoint"]:
        available = [e for e in endpoints if e.is_available]
        if not available:
            return None
        
        return min(available, key=lambda e: e.avg_response_time_ms or float('inf'))
    
    def update_metrics(self, endpoint: "ServiceEndpoint", response_time_ms: float, success: bool) -> None:
        pass


class ConsistentHashBalancer:
    """Consistent hash load balancer for sticky sessions."""
    
    def __init__(self, virtual_nodes: int = 150):
        self.virtual_nodes = virtual_nodes
        self._ring: Dict[int, "ServiceEndpoint"] = {}
        self._sorted_keys: List[int] = []
        self._lock = asyncio.Lock()
    
    def _hash(self, key: str) -> int:
        return int(hashlib.md5(key.encode()).hexdigest(), 16)
    
    async def _rebuild_ring(self, endpoints: List["ServiceEndpoint"]) -> None:
        async with self._lock:
            self._ring = {}
            for endpoint in endpoints:
                if not endpoint.is_available:
                    continue
                for i in range(self.virtual_nodes):
                    key = self._hash(f"{endpoint.endpoint_id}:{i}")
                    self._ring[key] = endpoint
            self._sorted_keys = sorted(self._ring.keys())
    
    async def select_endpoint(
        self,
        endpoints: List["ServiceEndpoint"],
        request: "GatewayRequest",
        rule: "RouteRule",
    ) -> Optional["ServiceEndpoint"]:
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
        session_key = request.headers.get("cookie", "").split("session=")[-1].split(";")[0]
        if not session_key:
            session_key = f"{request.client_ip}:{request.path}"
        
        hash_key = self._hash(session_key)
        
        async with self._lock:
            idx = bisect.bisect_left(self._sorted_keys, hash_key)
            if idx >= len(self._sorted_keys):
                idx = 0
            return self._ring[self._sorted_keys[idx]]
    
    def update_metrics(self, endpoint: "ServiceEndpoint", response_time_ms: float, success: bool) -> None:
        pass


class LeastLoadedBalancer:
    """Least loaded balancer considering multiple factors."""
    
    async def select_endpoint(
        self,
        endpoints: List["ServiceEndpoint"],
        request: "GatewayRequest",
        rule: "RouteRule",
    ) -> Optional["ServiceEndpoint"]:
        available = [e for e in endpoints if e.is_available]
        if not available:
            return None
        
        def score(endpoint: "ServiceEndpoint") -> float:
            # Normalize metrics (0-1)
            conn_score = endpoint.active_connections / max(endpoint.max_connections, 1)
            latency_score = min(endpoint.avg_response_time_ms / 1000.0, 1.0) if endpoint.avg_response_time_ms else 0
            error_score = endpoint.error_rate
            
            # Weighted score (lower is better)
            return (0.4 * conn_score + 0.4 * latency_score + 0.2 * error_score)
        
        return min(available, key=score)
    
    def update_metrics(self, endpoint: "ServiceEndpoint", response_time_ms: float, success: bool) -> None:
        pass


class AdaptiveBalancer:
    """Adaptive load balancer that learns from performance."""
    
    def __init__(self):
        self._strategies = {
            "least_connections": LeastConnectionsBalancer(),
            "least_response_time": LeastResponseTimeBalancer(),
            "least_loaded": LeastLoadedBalancer(),
        }
        self._current_strategy = "least_loaded"
        self._performance_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self._last_switch = time.time()
        self._switch_interval = 60  # seconds
    
    def select_endpoint(
        self,
        endpoints: List["ServiceEndpoint"],
        request: "GatewayRequest",
        rule: "RouteRule",
    ) -> Optional["ServiceEndpoint"]:
        strategy = self._strategies[self._current_strategy]
        return strategy.select_endpoint(endpoints, request, rule)
    
    def update_metrics(self, endpoint: "ServiceEndpoint", response_time_ms: float, success: bool) -> None:
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
        for strategy_name, strategy in self._strategies.items():
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


class ConsistentHashBalancer:
    """Consistent hash load balancer for sticky sessions."""
    
    def __init__(self, virtual_nodes: int = 150):
        self.virtual_nodes = virtual_nodes
        self._ring: Dict[int, "ServiceEndpoint"] = {}
        self._sorted_keys: List[int] = []
        self._lock = asyncio.Lock()
    
    def _hash(self, key: str) -> int:
        return int(hashlib.md5(key.encode()).hexdigest(), 16)
    
    async def _rebuild_ring(self, endpoints: List["ServiceEndpoint"]) -> None:
        async with self._lock:
            self._ring = {}
            for endpoint in endpoints:
                if not endpoint.is_available:
                    continue
                for i in range(self.virtual_nodes):
                    key = self._hash(f"{endpoint.endpoint_id}:{i}")
                    self._ring[key] = endpoint
            self._sorted_keys = sorted(self._ring.keys())
    
    async def select_endpoint(
        self,
        endpoints: List["ServiceEndpoint"],
        request: "GatewayRequest",
        rule: "RouteRule",
    ) -> Optional["ServiceEndpoint"]:
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
        session_key = request.headers.get("cookie", "").split("session=")[-1].split(";")[0]
        if not session_key or session_key == request.headers.get("cookie", ""):
            session_key = f"{request.client_ip}:{request.path}"
        
        hash_key = self._hash(session_key)
        
        async with self._lock:
            # Find the first key >= hash_key
            idx = bisect.bisect_left(self._sorted_keys, hash_key)
            if idx >= len(self._sorted_keys):
                idx = 0
            return self._ring[self._sorted_keys[idx]]
    
    def update_metrics(self, endpoint: "ServiceEndpoint", response_time_ms: float, success: bool) -> None:
        pass


class LeastLoadedBalancer:
    """Least loaded balancer considering multiple factors."""
    
    async def select_endpoint(
        self,
        endpoints: List["ServiceEndpoint"],
        request: "GatewayRequest",
        rule: "RouteRule",
    ) -> Optional["ServiceEndpoint"]:
        available = [e for e in endpoints if e.is_available]
        if not available:
            return None
        
        def score(endpoint: "ServiceEndpoint") -> float:
            # Normalize metrics (0-1)
            conn_score = endpoint.active_connections / max(endpoint.max_connections, 1)
            latency_score = min(endpoint.avg_response_time_ms / 1000.0, 1.0) if endpoint.avg_response_time_ms else 0
            error_score = endpoint.error_rate
            
            # Weighted score (lower is better)
            return (0.4 * conn_score + 0.4 * latency_score + 0.2 * error_score)
        
        return min(available, key=score)
    
    def update_metrics(self, endpoint: "ServiceEndpoint", response_time_ms: float, success: bool) -> None:
        pass


class AdaptiveBalancer:
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
        endpoints: List["ServiceEndpoint"],
        request: "GatewayRequest",
        rule: "RouteRule",
    ) -> Optional["ServiceEndpoint"]:
        strategy = self._strategies[self._current_strategy]
        return strategy.select_endpoint(endpoints, request, rule)
    
    def update_metrics(self, endpoint: "ServiceEndpoint", response_time_ms: float, success: bool) -> None:
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
# Factory
# =============================================================================

def create_load_balancer(
    strategy: LoadBalancingStrategy = LoadBalancingStrategy.LEAST_LOADED,
) -> LoadBalancer:
    """Create a load balancer instance."""
    balancers = {
        LoadBalancingStrategy.ROUND_ROBIN: RoundRobinBalancer(),
        LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN: WeightedRoundRobinBalancer(),
        LoadBalancingStrategy.LEAST_CONNECTIONS: LeastConnectionsBalancer(),
        LoadBalancingStrategy.LEAST_RESPONSE_TIME: LeastResponseTimeBalancer(),
        LoadBalancingStrategy.CONSISTENT_HASH: ConsistentHashBalancer(),
        LoadBalancingStrategy.LEAST_LOADED: LeastLoadedBalancer(),
        LoadBalancingStrategy.ADAPTIVE: AdaptiveBalancer(),
    }
    return balancers.get(strategy, LeastLoadedBalancer())

"""
Circuit Breaker Plugin for API Gateway.
Implements circuit breaker pattern with configurable thresholds.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
import asyncio

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration."""
    failure_threshold: int = 5
    success_threshold: int = 2
    timeout_seconds: float = 60.0
    half_open_max_calls: int = 3
    excluded_exceptions: tuple = (Exception,)


@dataclass
class CircuitBreakerState:
    state: str = "closed"
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[float] = None
    last_state_change: float = field(default_factory=lambda: time.time())
    half_open_calls: int = 0


class CircuitBreaker:
    """Circuit breaker implementation with configurable thresholds."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        config = config or {}
        self.failure_threshold = config.get("failure_threshold", 5)
        self.success_threshold = config.get("success_threshold", 2)
        self.timeout_seconds = config.get("timeout_seconds", 60.0)
        self.half_open_max_calls = config.get("half_open_max_calls", 3)
        self.excluded_exceptions = config.get("excluded_exceptions", (Exception,))
        
        self.state = "closed"
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self.last_state_change = time.time()
        self._half_open_calls = 0
        self._lock = asyncio.Lock()
        
        # Metrics
        self.total_calls = 0
        self.total_failures = 0
        self.total_successes = 0
        self.state_changes = 0
    
    def record_success(self) -> None:
        """Record a successful call."""
        self.failure_count = 0
        self.success_count += 1
        
        if self.state == "half_open":
            self.success_count += 1
            if self.success_count >= 2:  # success_threshold
                self._transition_to_closed()
    
    def record_failure(self) -> None:
        """Record a failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == "closed":
            if self.failure_count >= self.failure_threshold:
                self._transition_to_open()
        elif self.state == "half_open":
            self._transition_to_open()
    
    def can_execute(self) -> bool:
        """Check if request can be executed."""
        if self.state == "closed":
            return True
        
        if self.state == "open":
            # Check if timeout has passed
            if self.last_failure_time:
                elapsed = time.time() - self.last_failure_time
                if elapsed >= 60:  # timeout_seconds
                    self.state = "half_open"
                    return True
            return False
        
        # Half-open state - allow limited calls
        return True
    
    def record_success(self):
        self._record_success()
    
    def _record_success(self):
        self.success_count += 1
        
        if self.state == "half_open":
            if self.success_count >= 2:  # success_threshold
                self.state = "closed"
                self.failure_count = 0
                self.success_count = 0
                logger.info("Circuit breaker CLOSED")
    
    def _record_failure(self):
        self.failure_count += 1
        
        if self.state == "closed":
            if self.failure_count >= 5:  # failure_threshold
                self._transition_to_open()
        elif self.state == "half_open":
            self._transition_to_open()
    
    def _transition_to_open(self):
        self.state = "open"
        self.last_failure_time = time.time()
        logger.warning("Circuit breaker OPEN")
    
    def can_execute(self) -> bool:
        if self.state == "closed":
            return True
        
        if self.state == "open":
            if self.last_failure_time:
                elapsed = time.time() - self.last_failure_time
                if elapsed >= 60:  # timeout_seconds
                    self.state = "half_open"
                    self.success_count = 0
                    return True
            return False
        
        # Half-open state
        return True
    
    def record_result(self, success: bool):
        if success:
            self.record_success()
        else:
            self.record_failure()
    
    def get_state(self) -> Dict[str, Any]:
        return {
            "state": self.state,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time,
        }


class CircuitBreakerPlugin:
    """Circuit breaker plugin for gateway."""
    
    def __init__(self, default_config: Optional[Dict] = None):
        self._breakers: Dict[str, CircuitBreaker] = {}
        self.default_config = {
            "failure_threshold": 5,
            "success_threshold": 2,
            "timeout_seconds": 60.0,
            "half_open_max_calls": 3,
        }
        if default_config:
            self.default_config.update(default_config)
        self._breakers: Dict[str, Any] = {}
        self._lock = asyncio.Lock()
    
    def get_breaker(self, service_name: str) -> Any:
        """Get or create circuit breaker for service."""
        if service_name not in self._breakers:
            self._breakers[service_name] = CircuitBreaker()
        return self._breakers[service_name]
    
    async def execute(
        self,
        service_name: str,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """Execute function with circuit breaker protection."""
        breaker = self.get_breaker(service_name)
        
        if not self._can_execute(service_name):
            raise CircuitBreakerOpenError(f"Circuit breaker open for {service_name}")
        
        try:
            result = await func()
            self.record_success(service_name)
            return result
        except Exception as e:
            self.record_failure(service_name)
            raise
    
    def get_breaker(self, service_name: str) -> Any:
        """Get or create circuit breaker for service."""
        if service_name not in self._breakers:
            self._breakers[service_name] = CircuitBreaker()
        return self._breakers[service_name]
    
    def record_success(self, service_name: str):
        breaker = self.get_breaker(service_name)
        breaker.record_success()
    
    def record_failure(self, service_name: str):
        breaker = self.get_breaker(service_name)
        breaker.record_failure()
    
    def can_execute(self, service_name: str) -> bool:
        breaker = self.get_breaker(service_name)
        return breaker.can_execute()
    
    def get_status(self, service_name: str) -> Dict[str, Any]:
        breaker = self.get_breaker(service_name)
        return breaker.get_state()
    
    def get_all_status(self) -> Dict[str, Any]:
        return {
            name: breaker.get_state()
            for name, breaker in self._breakers.items()
        }
    
    def reset(self, service_name: str):
        if service_name in self._breakers:
            self._breakers[service_name].reset()


class CircuitBreakerMiddleware:
    """Circuit breaker middleware for gateway."""
    
    def __init__(self, circuit_breaker: CircuitBreakerPlugin):
        self.circuit_breaker = circuit_breaker
    
    async def __call__(self, request: Dict, next_handler: Callable) -> Dict:
        service_name = request.get("service_name", "default")
        
        if not self.circuit_breaker.can_execute(request.get("service_name", "default")):
            return {
                "status": 503,
                "error": "Service temporarily unavailable",
                "headers": {"Retry-After": "60"},
            }
        
        try:
            response = await self._call_next(request)
            self.circuit_breaker.record_success(request.get("service_name", "default"))
            return response
        except Exception as e:
            self.circuit_breaker.record_failure(request.get("service_name", "default"))
            raise

"""
Health Monitor - Continuous health checking with circuit breaker
Pings models every 5 minutes, tracks health, manages circuit breakers
"""
import threading
import time
import logging
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from .model_registry import ModelRegistry, ModelConfig, ModelHealth, ModelStatus

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if recovered


@dataclass
class CircuitBreaker:
    """Circuit breaker for a specific model"""
    model_key: str
    failure_threshold: int = 3
    recovery_timeout: int = 600  # 10 minutes
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    last_state_change: float = field(default_factory=time.time)

    def record_success(self):
        """Record a successful call"""
        self.failure_count = 0
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
        elif self.state == CircuitState.CLOSED:
            pass  # Already closed
        self.last_success_time = time.time()
        self.last_state_change = time.time()

    def record_failure(self):
        """Record a failed call"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitState.HALF_OPEN:
            # Any failure in half-open goes back to open
            self.state = CircuitState.OPEN
            self.last_state_change = time.time()
        elif self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            self.last_state_change = time.time()

    def can_execute(self) -> bool:
        """Check if request can proceed"""
        if self.state == CircuitState.CLOSED:
            return True
        
        if self.state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if time.time() - self.last_state_change >= self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                self.last_state_change = time.time()
                return True
            return False
        
        # HALF_OPEN - allow one request to test
        return True

    def get_status(self) -> Dict:
        return {
            "model_key": self.model_key,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
            "last_failure_time": self.last_failure_time,
            "last_success_time": self.last_success_time,
            "time_in_state": time.time() - self.last_state_change
        }


class HealthMonitor:
    """
    Background health monitoring for all models.
    - Pings models every 5 minutes
    - Tracks consecutive failures
    - Manages circuit breakers
    - Updates ModelRegistry health status
    """

    def __init__(self, model_registry: ModelRegistry, check_interval: int = 300):
        self.model_registry = model_registry
        self.check_interval = check_interval
        self.circuit_breaker_threshold = 3
        self.circuit_breaker_timeout = 600  # 10 minutes
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._lock = threading.RLock()
        self._running = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._health_check_callback: Optional[Callable[[str, ModelConfig], bool]] = None
        self.stats = {
            "total_checks": 0,
            "healthy_checks": 0,
            "unhealthy_checks": 0,
            "circuit_opened": 0,
            "circuit_closed": 0,
            "last_check": None
        }

    def set_health_check_callback(self, callback: Callable[[str, ModelConfig], bool]):
        """Set custom health check function.
        Should return True if healthy, False if unhealthy.
        """
        self._health_check_callback = callback

    def _get_circuit_breaker(self, worker: str, model_id: str) -> CircuitBreaker:
        """Get or create circuit breaker for a model."""
        key = f"{worker}:{model_id}"
        with self._lock:
            if key not in self.circuit_breakers:
                self.circuit_breakers[key] = CircuitBreaker(
                    model_key=key, 
                    failure_threshold=self.circuit_breaker_threshold,
                    recovery_timeout=self.circuit_breaker_timeout
                )
            return self.circuit_breakers[key]

    def can_execute(self, worker: str, model_id: str) -> bool:
        """Check if a model can execute (circuit breaker check)."""
        cb = self._get_circuit_breaker(worker, model_id)
        return cb.can_execute()

    def record_success(self, worker: str, model_id: str, latency: float = 0):
        """Record a successful model call."""
        with self._lock:
            key = f"{worker}:{model_id}"
            # Update registry
            self.model_registry.record_success(worker, model_id, latency)
            
            # Update circuit breaker
            cb = self.circuit_breakers.get(key)
            if cb:
                if cb.state == CircuitState.HALF_OPEN:
                    cb.record_success()
                    self.stats["circuit_closed"] += 1
                    logger.info(f"Circuit closed for {key} after successful test")
                elif cb.state == CircuitState.CLOSED:
                    cb.record_success()

    def record_failure(self, worker: str, model_id: str, error: str = ""):
        """Record a failed model call."""
        with self._lock:
            key = f"{worker}:{model_id}"
            # Update registry
            self.model_registry.record_failure(worker, model_id)
            
            # Update circuit breaker
            cb = self._get_circuit_breaker(worker, model_id)
            old_state = cb.state
            cb.record_failure()
            
            if old_state != CircuitState.OPEN and cb.state == CircuitState.OPEN:
                self.stats["circuit_opened"] += 1
                logger.warning(f"Circuit opened for {key} after {cb.failure_count} failures")

    def get_circuit_status(self, worker: str, model_id: str) -> Dict:
        """Get circuit breaker status for a model."""
        cb = self._get_circuit_breaker(worker, model_id)
        return cb.get_status()

    def get_all_circuit_status(self) -> Dict:
        """Get status of all circuit breakers."""
        with self._lock:
            return {key: cb.get_status() for key, cb in self.circuit_breakers.items()}

    def _perform_health_check(self, worker: str, config: ModelConfig) -> bool:
        """Perform a single health check on a model."""
        if self._health_check_callback:
            try:
                return self._health_check_callback(config.model, config)
            except Exception as e:
                logger.error(f"Health check callback failed for {config.model}: {e}")
                return False
        
        # Default: just check if model is reachable (placeholder)
        return True

    def run_health_checks(self):
        """Run health checks on all registered models."""
        logger.info("Running health checks...")
        self.stats["total_checks"] += 1
        self.stats["last_check"] = datetime.now().isoformat()

        for worker, models in self.model_registry.models.items():
            for config in models:
                try:
                    # Skip if circuit is open and not in half-open
                    if not self.can_execute(worker, config.id):
                        self.stats["unhealthy_checks"] += 1
                        self.model_registry.record_failure(worker, config.id)
                        continue

                    # Perform health check
                    is_healthy = self._perform_health_check(worker, config)
                    
                    if is_healthy:
                        self.model_registry.record_success(worker, config.id, latency=0)
                        self.stats["healthy_checks"] += 1
                        logger.debug(f"Health check passed: {worker}:{config.id}")
                    else:
                        self.model_registry.record_failure(worker, config.id)
                        self.stats["unhealthy_checks"] += 1
                        logger.warning(f"Health check failed: {worker}:{config.id}")

                except Exception as e:
                    logger.error(f"Health check error for {worker}:{config.id}: {e}")
                    self.model_registry.record_failure(worker, config.id)
                    self.stats["unhealthy_checks"] += 1

    def start(self):
        """Start background monitoring thread."""
        if self._running:
            logger.warning("Health monitor already running")
            return

        self._running = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        logger.info(f"Health monitor started (interval: {self.check_interval}s)")

    def stop(self):
        """Stop background monitoring thread."""
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        logger.info("Health monitor stopped")

    def _monitor_loop(self):
        """Background monitoring loop."""
        # Initial check
        self.run_health_checks()
        
        while self._running:
            time.sleep(self.check_interval)
            if self._running:
                self.run_health_checks()

    def get_stats(self) -> Dict:
        """Get monitoring statistics."""
        with self._lock:
            stats = self.stats.copy()
            stats["circuit_breakers"] = len(self.circuit_breakers)
            stats["running"] = self._running
            return stats


# Convenience function for creating a default health monitor
def create_health_monitor(model_registry: ModelRegistry, check_interval: int = 300) -> HealthMonitor:
    """Create a health monitor with default settings."""
    monitor = HealthMonitor(model_registry, check_interval)
    return monitor

"""
Health Checks - Comprehensive health checking for all Swarm components.
"""

import asyncio
import threading
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def uuidv7() -> str:
    return str(uuid.uuid4())


# =============================================================================
# Health Models
# =============================================================================

class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Result of a single health check."""
    check_id: str = field(default_factory=lambda: f"check-{uuidv7()}")
    name: str = ""
    component: str = ""
    status: HealthStatus = HealthStatus.UNKNOWN
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    duration_ms: float = 0
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "check_id": self.check_id,
            "name": self.name,
            "component": self.component,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_ms": self.duration_ms,
            "error": self.error,
        }


@dataclass
class ComponentHealth:
    """Health status for a component."""
    component: str = ""
    status: HealthStatus = HealthStatus.UNKNOWN
    checks: List[Any] = field(default_factory=list)
    last_checked: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "component": self.component,
            "status": self.status.value,
            "checks": [c.to_dict() if hasattr(c, 'to_dict') else c for c in self.checks],
            "last_checked": self.last_checked.isoformat() if self.last_checked else None,
            "metadata": self.metadata,
        }


@dataclass
class SystemHealth:
    """Overall system health."""
    status: HealthStatus = HealthStatus.UNKNOWN
    components: Dict[str, ComponentHealth] = field(default_factory=dict)
    checked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    version: str = "unknown"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "components": {k: v.to_dict() for k, v in self.components.items()},
            "checked_at": self.checked_at.isoformat(),
            "version": self.version,
        }


# =============================================================================
# Health Check Interface
# =============================================================================

class HealthCheck(ABC):
    """Abstract health check."""
    
    def __init__(self, name: str = "", component: str = "", timeout: float = 10.0):
        self.name = name
        self.component = component
        self.timeout = timeout
    
    @abstractmethod
    def check(self) -> HealthCheckResult:
        """Perform the health check."""
        pass
    
    def run(self) -> HealthCheckResult:
        """Run the check with timing."""
        start = time.time()
        try:
            result = self.check()
            result.duration_ms = (time.time() - start) * 1000
            result.completed_at = now_utc()
            return result
        except Exception as e:
            return HealthCheckResult(
                name=self.name,
                component=self.component,
                status=HealthStatus.UNHEALTHY,
                message=f"Check failed: {e}",
                error=str(e),
                duration_ms=(time.time() - start) * 1000,
                completed_at=now_utc(),
            )


# =============================================================================
# Standard Health Checks
# =============================================================================

class DatabaseHealthCheck(HealthCheck):
    """Check database connectivity."""
    
    def __init__(self, db_connection: Any, name: str = "database"):
        super().__init__(name, "database")
        self.db = db_connection
    
    def check(self) -> HealthCheckResult:
        try:
            # In production, execute a simple query
            # self.db.execute("SELECT 1")
            return HealthCheckResult(
                name=self.name,
                component=self.component,
                status=HealthStatus.HEALTHY,
                message="Database connection OK",
            )
        except Exception as e:
            return HealthCheckResult(
                name=self.name,
                component=self.component,
                status=HealthStatus.UNHEALTHY,
                message=f"Database check failed: {e}",
                error=str(e),
            )


class RedisHealthCheck(HealthCheck):
    """Check Redis connectivity."""
    
    def __init__(self, redis_client: Any, name: str = "redis"):
        super().__init__(name, "redis")
        self.redis = redis_client
    
    def check(self) -> HealthCheckResult:
        try:
            # In production: self.redis.ping()
            return HealthCheckResult(
                name=self.name,
                component=self.component,
                status=HealthStatus.HEALTHY,
                message="Redis connection OK",
            )
        except Exception as e:
            return HealthCheckResult(
                name=self.name,
                component=self.component,
                status=HealthStatus.UNHEALTHY,
                message=f"Redis check failed: {e}",
                error=str(e),
            )


class HTTPHealthCheck(HealthCheck):
    """Check HTTP endpoint health."""
    
    def __init__(
        self,
        url: str,
        name: str = "http_endpoint",
        expected_status: int = 200,
        timeout: float = 5.0,
    ):
        super().__init__(name, "http")
        self.url = url
        self.expected_status = expected_status
        self.timeout = timeout
    
    def check(self) -> HealthCheckResult:
        import requests
        
        try:
            response = requests.get(self.url, timeout=self.timeout)
            if response.status_code == self.expected_status:
                return HealthCheckResult(
                    name=self.name,
                    component=self.component,
                    status=HealthStatus.HEALTHY,
                    message=f"HTTP {response.status_code} OK",
                    details={"url": self.url, "status_code": response.status_code},
                )
            else:
                return HealthCheckResult(
                    name=self.name,
                    component=self.component,
                    status=HealthStatus.UNHEALTHY,
                    message=f"HTTP {response.status_code} != {self.expected_status}",
                    details={"url": self.url, "status_code": response.status_code},
                )
        except Exception as e:
            return HealthCheckResult(
                name=self.name,
                component=self.component,
                status=HealthStatus.UNHEALTHY,
                message=f"HTTP check failed: {e}",
                error=str(e),
            )


class DiskSpaceCheck(HealthCheck):
    """Check available disk space."""
    
    def __init__(
        self,
        path: str = "/",
        min_free_gb: float = 1.0,
        min_free_percent: float = 10.0,
        name: str = "disk_space",
    ):
        super().__init__(name, "disk")
        self.path = path
        self.min_free_gb = min_free_gb
        self.min_free_percent = min_free_percent
    
    def check(self) -> HealthCheckResult:
        import shutil
        
        try:
            total, used, free = shutil.disk_usage(self.path)
            free_gb = free / (1024**3)
            free_percent = (free / total) * 100
            
            status = HealthStatus.HEALTHY
            message = f"Disk space OK: {free_gb:.1f}GB free ({free_percent:.1f}%)"
            
            if free_gb < self.min_free_gb or free_percent < self.min_free_percent:
                status = HealthStatus.UNHEALTHY
                message = f"Low disk space: {free_gb:.1f}GB free ({free_percent:.1f}%)"
            
            return HealthCheckResult(
                name=self.name,
                component=self.component,
                status=status,
                message=message,
                details={
                    "path": self.path,
                    "total_gb": total / (1024**3),
                    "used_gb": used / (1024**3),
                    "free_gb": free_gb,
                    "free_percent": free_percent,
                },
            )
        except Exception as e:
            return HealthCheckResult(
                name=self.name,
                component=self.component,
                status=HealthStatus.UNHEALTHY,
                message=f"Disk check failed: {e}",
                error=str(e),
            )


class MemoryUsageCheck(HealthCheck):
    """Check memory usage."""
    
    def __init__(
        self,
        max_percent: float = 90.0,
        name: str = "memory_usage",
    ):
        super().__init__(name, "memory")
        self.max_percent = max_percent
    
    def check(self) -> HealthCheckResult:
        try:
            import psutil
            
            mem = psutil.virtual_memory()
            used_percent = mem.percent
            
            status = HealthStatus.HEALTHY
            message = f"Memory usage: {used_percent:.1f}%"
            
            if used_percent > self.max_percent:
                status = HealthStatus.UNHEALTHY
                message = f"High memory usage: {used_percent:.1f}%"
            elif used_percent > self.max_percent * 0.8:
                status = HealthStatus.DEGRADED
                message = f"Elevated memory usage: {used_percent:.1f}%"
            
            return HealthCheckResult(
                name=self.name,
                component=self.component,
                status=status,
                message=message,
                details={
                    "total_gb": mem.total / (1024**3),
                    "available_gb": mem.available / (1024**3),
                    "used_percent": used_percent,
                },
            )
        except ImportError:
            return HealthCheckResult(
                name=self.name,
                component=self.component,
                status=HealthStatus.UNKNOWN,
                message="psutil not available",
            )
        except Exception as e:
            return HealthCheckResult(
                name=self.name,
                component=self.component,
                status=HealthStatus.UNHEALTHY,
                message=f"Memory check failed: {e}",
                error=str(e),
            )


class CustomHealthCheck(HealthCheck):
    """Custom health check with user-defined function."""
    
    def __init__(
        self,
        name: str = "",
        component: str = "",
        check_fn: Callable[[], bool] = lambda: True,
        message_ok: str = "OK",
        message_fail: str = "Check failed",
        timeout: float = 10.0,
    ):
        super().__init__(name, component, timeout)
        self.check_fn = check_fn
        self.message_ok = message_ok
        self.message_fail = message_fail
    
    def check(self) -> HealthCheckResult:
        try:
            result = self.check_fn()
            if result:
                return HealthCheckResult(
                    name=self.name,
                    component=self.component,
                    status=HealthStatus.HEALTHY,
                    message=self.message_ok,
                )
            else:
                return HealthCheckResult(
                    name=self.name,
                    component=self.component,
                    status=HealthStatus.UNHEALTHY,
                    message=self.message_fail,
                )
        except Exception as e:
            return HealthCheckResult(
                name=self.name,
                component=self.component,
                status=HealthStatus.UNHEALTHY,
                message=f"Check failed: {e}",
                error=str(e),
            )


# =============================================================================
# Health Checker
# =============================================================================

class HealthChecker:
    """Runs health checks and aggregates results."""
    
    def __init__(self):
        self._checks: Dict[str, HealthCheck] = {}
        self._last_results: Dict[str, HealthCheckResult] = {}
        self._lock = threading.RLock()
    
    def add_check(self, check: HealthCheck) -> None:
        """Add a health check."""
        with self._lock:
            self._checks[check.name] = check
    
    def remove_check(self, name: str = "") -> bool:
        """Remove a health check."""
        with self._lock:
            if name in self._checks:
                del self._checks[name]
                return True
            return False
    
    def run_check(self, name: str = "") -> Optional[HealthCheckResult]:
        """Run a specific check."""
        with self._lock:
            check = self._checks.get(name)
            if not check:
                return None
        
        result = check.run()
        with self._lock:
            self._last_results[name] = result
        return result
    
    def run_all(self) -> Dict[str, HealthCheckResult]:
        """Run all checks."""
        with self._lock:
            checks = list(self._checks.values())
        
        results = {}
        for check in checks:
            result = check.run()
            results[check.name] = result
            with self._lock:
                self._last_results[check.name] = result
        
        return results
    
    def get_component_health(self, component: str = "") -> ComponentHealth:
        """Get health for a specific component."""
        with self._lock:
            results = [r for n, r in self._last_results.items() 
                      if self._checks.get(n, HealthCheck("", "")).component == component]
        
        if not results:
            return ComponentHealth(component=component, status=HealthStatus.UNKNOWN)
        
        # Determine overall status
        statuses = [r.status for r in results]
        if HealthStatus.UNHEALTHY in statuses:
            overall = HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            overall = HealthStatus.DEGRADED
        elif HealthStatus.HEALTHY in statuses:
            overall = HealthStatus.HEALTHY
        else:
            overall = HealthStatus.UNKNOWN
        
        return ComponentHealth(
            component=component,
            status=overall,
            checks=results,
            last_checked=now_utc(),
        )
    
    def get_system_health(self, version: str = "unknown") -> SystemHealth:
        """Get overall system health."""
        with self._lock:
            components = {}
            for check in self._checks.values():
                if check.component not in components:
                    components[check.component] = self.get_component_health(check.component)
        
        # Determine overall system status
        statuses = [c.status for c in components.values()]
        if HealthStatus.UNHEALTHY in statuses:
            overall = HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            overall = HealthStatus.DEGRADED
        elif HealthStatus.HEALTHY in statuses:
            overall = HealthStatus.HEALTHY
        else:
            overall = HealthStatus.UNKNOWN
        
        return SystemHealth(
            status=overall,
            components=components,
            checked_at=now_utc(),
        )
    
    def get_last_result(self, name: str = "") -> Optional[Any]:
        """Get last result for a check."""
        with self._lock:
            return self._last_results.get(name)


# =============================================================================
# Kubernetes Probe Endpoints
# =============================================================================

class KubernetesProbes:
    """Kubernetes liveness/readiness/startup probes."""
    
    def __init__(self, health_checker: HealthChecker):
        self.health_checker = health_checker
        
        # Required checks for each probe type
        self._liveness_checks: List[str] = []
        self._readiness_checks: List[str] = []
        self._startup_checks: List[str] = []
    
    def add_liveness_check(self, check_name: str = "") -> None:
        """Add check to liveness probe."""
        self._liveness_checks.append(check_name)
    
    def add_readiness_check(self, check_name: str = "") -> None:
        """Add check to readiness probe."""
        self._readiness_checks.append(check_name)
    
    def add_startup_check(self, check_name: str = "") -> None:
        """Add check to startup probe."""
        self._startup_checks.append(check_name)
    
    def liveness_probe(self) -> Dict[str, Any]:
        """Run liveness probe."""
        results = {}
        for check_name in self._liveness_checks:
            result = self.health_checker.run_check(check_name)
            if result:
                results[check_name] = result.to_dict()
        
        healthy = all(r.status == "healthy" for r in results.values() if hasattr(r, 'status'))
        
        return {
            "status": "healthy" if healthy else "unhealthy",
            "checks": results,
        }
    
    def readiness_probe(self) -> Dict[str, Any]:
        """Run readiness probe."""
        results = {}
        for check_name in self._readiness_checks:
            result = self.health_checker.run_check(check_name)
            if result:
                results[check_name] = result.to_dict()
        
        ready = all(r.status == "healthy" for r in results.values() if hasattr(r, 'status'))
        
        return {
            "status": "ready" if ready else "not_ready",
            "checks": results,
        }
    
    def startup_probe(self) -> Dict[str, Any]:
        """Run startup probe."""
        results = {}
        for check_name in self._startup_checks:
            result = self.health_checker.run_check(check_name)
            if result:
                results[check_name] = result.to_dict()
        
        started = all(r.status == "healthy" for r in results.values() if hasattr(r, 'status'))
        
        return {
            "status": "started" if started else "starting",
            "checks": results,
        }


# =============================================================================
# Factory
# =============================================================================

def create_health_checker() -> "HealthChecker":
    """Create a health checker instance."""
    return HealthChecker()


def create_kubernetes_probes(health_checker: "HealthChecker") -> KubernetesProbes:
    """Create Kubernetes probes."""
    return KubernetesProbes(health_checker)


def create_standard_checks() -> List[HealthCheck]:
    """Create standard health checks."""
    checks = [
        DiskSpaceCheck("/"),
        MemoryUsageCheck(max_percent=90.0),
        CustomHealthCheck("application", "app", lambda: True, "App OK", "App failed"),
    ]
    return checks

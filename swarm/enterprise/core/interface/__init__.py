"""
Service Interfaces for Swarm Enterprise Core.
Break circular dependencies and enforce layer boundaries.
"""

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import uuid


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def uuidv7() -> str:
    return str(uuid.uuid4())


# =============================================================================
# Service Interface Contracts
# =============================================================================

@runtime_checkable
class IPolicyService(Protocol):
    """Policy evaluation service interface."""
    
    def evaluate(self, context: Any) -> Any:
        """Evaluate policy for given context."""
        ...
    
    def is_allowed(self, context: Any) -> bool:
        """Check if request is allowed."""
        ...


@runtime_checkable
class IBudgetService(Protocol):
    """Budget management service interface."""
    
    def get_budget(self, tenant_id: str) -> Any:
        """Get budget for tenant."""
        ...
    
    def debit(self, tenant_id: str, amount: float, description: str = "") -> bool:
        """Debit budget."""
        ...
    
    def refund(self, tenant_id: str, amount: float, description: str = "") -> bool:
        """Refund budget."""
        ...
    
    def get_available(self, tenant_id: str) -> float:
        """Get available balance."""
        ...


@runtime_checkable
class IAuthService(Protocol):
    """Authentication service interface."""
    
    def create_authorization_context(
        self,
        principal_id: str,
        tenant_id: str,
    ) -> Any:
        """Create authorization context."""
        ...
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT token."""
        ...


@runtime_checkable
class IJobService(Protocol):
    """Job queue service interface."""
    
    def enqueue(self, job: Any, priority: str = "normal") -> str:
        """Enqueue a job."""
        ...
    
    def dequeue(self, job_type: str, timeout: float = 0) -> Optional[Any]:
        """Dequeue a job."""
        ...
    
    def complete_job(self, job_id: str, result: Any = None, error: Optional[str] = None) -> bool:
        """Mark job as complete."""
        ...


@runtime_checkable
class IOrchestrationService(Protocol):
    """Orchestration service interface."""
    
    def process_request(self, request: Any) -> Any:
        """Process a request through orchestration pipeline."""
        ...


@runtime_checkable
class IRoutingService(Protocol):
    """Routing service interface."""
    
    def route(self, request: Any) -> Any:
        """Route request to appropriate handler."""
        ...


# =============================================================================
# Service Registry
# =============================================================================

class ServiceRegistry:
    """Registry for enterprise services."""
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
    
    def register(self, name: str, service: Any) -> None:
        """Register a service."""
        self._services[name] = service
    
    def get(self, name: str) -> Any:
        """Get a service by name."""
        return self._services.get(name)
    
    def get_policy_service(self) -> Optional[IPolicyService]:
        return self._services.get("policy")
    
    def get_budget_service(self) -> Optional[IBudgetService]:
        return self._services.get("budget")
    
    def get_auth_service(self) -> Optional[IAuthService]:
        return self._services.get("auth")
    
    def get_job_service(self) -> Optional[IJobService]:
        return self._services.get("job")
    
    def get_orchestration_service(self) -> Optional[IOrchestrationService]:
        return self._services.get("orchestration")
    
    def get_routing_service(self) -> Optional[IRoutingService]:
        return self._services.get("routing")


# Global service registry
_registry: Optional[ServiceRegistry] = None


def get_service_registry() -> ServiceRegistry:
    """Get global service registry."""
    global _registry
    if _registry is None:
        _registry = ServiceRegistry()
    return _registry

"""
Core Contracts - Shared interfaces to break circular dependencies.
These interfaces define the contracts between modules without creating circular imports.
"""

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import uuid
import threading


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def uuidv7() -> str:
    return str(uuid.uuid4())


# =============================================================================
# Policy Validation Interface
# =============================================================================

@runtime_checkable
class IPolicyValidator(Protocol):
    """Interface for policy validation - breaks verification ↔ policy cycle."""
    
    def validate_request(self, request: Any, context: Any) -> bool:
        """Validate request against policies."""
        ...
    
    def is_allowed(self, action: str, resource: str, context: Any) -> bool:
        """Check if action is allowed on resource."""
        ...
    
    def evaluate(self, context: Any) -> Any:
        """Evaluate policy for given context."""
        ...


# =============================================================================
# Execution Client Interface
# =============================================================================

@runtime_checkable
class IExecutionClient(Protocol):
    """Interface for execution plane - breaks plane ↔ swarm_master → execution cycle."""
    
    async def execute(self, request: Any) -> Any:
        """Execute a request in the execution plane."""
        ...
    
    async def submit_job(self, job: Any) -> str:
        """Submit job for async execution."""
        ...
    
    async def get_status(self, job_id: str) -> Any:
        """Get job execution status."""
        ...


# =============================================================================
# Orchestration Client Interface
# =============================================================================

@runtime_checkable
class IOrchestrationClient(Protocol):
    """Interface for orchestration - breaks plane ↔ swarm_master → orchestration cycle."""
    
    async def process_request(self, request: Any) -> Any:
        """Process a request through orchestration layer."""
        ...
    
    async def create_workflow(self, workflow_id: str, workflow_type: str, steps: List[Dict]) -> Any:
        """Create a compensable workflow."""
        ...
    
    async def execute_workflow(self, workflow_id: str) -> Any:
        """Execute a workflow with compensation."""
        ...


# =============================================================================
# Execution Client Interface (for plane → execution)
# =============================================================================

@runtime_checkable
class IExecutionClient(Protocol):
    """Interface for execution plane - breaks plane → execution cycle."""
    
    async def execute(self, request: Any) -> Any:
        """Execute a request in the execution plane."""
        ...
    
    async def submit_job(self, job: Any) -> str:
        """Submit job for async execution."""
        ...
    
    async def get_status(self, job_id: str) -> Any:
        """Get job execution status."""
        ...


# =============================================================================
# Budget Client Interface
# =============================================================================

@runtime_checkable
class IBudgetClient(Protocol):
    """Interface for budget service - breaks orchestration/plane → budget cycle."""
    
    async def estimate_cost(self, request: Any) -> Any:
        """Estimate cost for request."""
        ...
    
    async def reserve_budget(self, tenant_id: str, amount: float, request_id: str) -> bool:
        """Reserve budget atomically."""
        ...
    
    async def get_available(self, tenant_id: str) -> float:
        """Get available budget."""
        ...


# =============================================================================
# Routing Client Interface
# =============================================================================

@runtime_checkable
class IRoutingClient(Protocol):
    """Interface for routing service - breaks orchestration → routing cycle."""
    
    async def route(self, request: Any) -> Any:
        """Route request to appropriate handler."""
        ...


# =============================================================================
# Auth Client Interface
# =============================================================================

@runtime_checkable
class IAuthClient(Protocol):
    """Interface for auth service - breaks plane/orchestration → auth cycle."""
    
    async def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT token."""
        ...
    
    async def create_auth_context(self, principal_id: str, tenant_id: str) -> Any:
        """Create authorization context."""
        ...


# =============================================================================
# Common Data Classes
# =============================================================================

@dataclass
class ExecutionRequest:
    """Request to execute code."""
    request_id: str = field(default_factory=lambda: f"exec-{uuidv7()}")
    code: str = ""
    language: str = "python"
    stdin: str = ""
    environment: Dict[str, str] = field(default_factory=dict)
    files: Dict[str, str] = field(default_factory=dict)
    timeout_seconds: int = 30
    max_memory_mb: int = 256
    max_cpu_seconds: int = 30
    max_output_size_mb: int = 10
    max_processes: int = 10
    network_allowed: bool = False
    filesystem_allowed: bool = False
    allowed_imports: Optional[List[str]] = None
    blocked_imports: List[str] = field(default_factory=list)
    tenant_id: str = "default"
    actor_id: str = "system"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ExecutionResult:
    """Result of code execution."""
    request_id: str
    status: str = "pending"
    stdout: str = ""
    stderr: str = ""
    return_code: int = 0
    execution_time_ms: int = 0
    cpu_time_ms: int = 0
    memory_used_mb: float = 0.0
    error_message: str = ""
    error_type: str = ""
    output_files: Dict[str, str] = field(default_factory=dict)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class RoutingDecision:
    """Routing decision result."""
    primary_department: str = ""
    confidence: float = 0.0
    alternative_departments: List[str] = field(default_factory=list)
    reasoning: str = ""


@dataclass
class AdmissionRequest:
    """Request for admission to execution plane."""
    request_id: str = field(default_factory=lambda: f"adm-{uuidv7()}")
    tenant_id: str = ""
    principal_id: str = ""
    job_type: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    priority: str = "normal"
    idempotency_key: Optional[str] = None
    authorization_context: Optional[Any] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AdmissionResult:
    """Result of admission control."""
    decision: str = "admitted"
    request_id: str = ""
    reason: str = ""
    estimated_cost: Optional[float] = None
    quota_remaining: Optional[float] = None


# =============================================================================
# Service Registry
# =============================================================================

class ServiceRegistry:
    """Registry for enterprise services."""
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._lock = threading.RLock()
    
    def register(self, name: str, service: Any) -> None:
        with self._lock:
            self._services[name] = service
    
    def get(self, name: str) -> Any:
        with self._lock:
            return self._services.get(name)
    
    def unregister(self, name: str) -> bool:
        with self._lock:
            if name in self._services:
                del self._services[name]
                return True
            return False


# Global service registry
_registry: Optional["ServiceRegistry"] = None
_lock = threading.RLock()


def get_service_registry() -> "ServiceRegistry":
    """Get global service registry."""
    global _registry
    with _lock:
        if _registry is None:
            _registry = ServiceRegistry()
        return _registry


# =============================================================================
# Helper Functions
# =============================================================================

def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def uuidv7() -> str:
    return str(uuid.uuid4())


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Interfaces
    "IPolicyValidator",
    "IExecutionClient",
    "IOrchestrationClient",
    "IExecutionClient",
    "IBudgetClient",
    "IRoutingClient",
    "IAuthClient",
    # Data classes
    "ExecutionRequest",
    "ExecutionResult",
    "RoutingDecision",
    "AdmissionRequest",
    "AdmissionResult",
    # Registry
    "ServiceRegistry",
    "get_service_registry",
    # Helpers
    "now_utc",
    "uuidv7",
]

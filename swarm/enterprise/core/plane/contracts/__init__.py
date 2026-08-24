"""
Plane Contracts - Shared interfaces for Control Plane and Execution Plane.
Break circular dependencies between plane modules and core modules.
"""

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable
from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid
import threading


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def uuidv7() -> str:
    return str(uuid.uuid4())


# =============================================================================
# Admission Control Interface
# =============================================================================

@runtime_checkable
class IAdmissionControl(Protocol):
    """Interface for admission control - controls what gets executed."""
    
    async def admit(self, request: Any) -> Any:
        """Admit a request to the execution plane."""
        ...
    
    async def reject(self, request_id: str, reason: str) -> bool:
        """Reject a request."""
        ...


# =============================================================================
# Policy Enforcement Interface
# =============================================================================

@runtime_checkable
class IPolicyEnforcement(Protocol):
    """Interface for policy enforcement - enforces policies on requests."""
    
    def evaluate(self, context: Any) -> Any:
        """Evaluate policy for given context."""
        ...
    
    def is_allowed(self, context: Any) -> bool:
        """Check if request is allowed."""
        ...


# =============================================================================
# Budget Enforcement Interface
# =============================================================================

@runtime_checkable
class IBudgetEnforcement(Protocol):
    """Interface for budget enforcement - manages cost limits."""
    
    async def estimate_cost(self, request: Any) -> float:
        """Estimate cost for a request."""
        ...
    
    async def reserve_budget(self, tenant_id: str, amount: float, request_id: str) -> bool:
        """Reserve budget atomically."""
        ...
    
    async def get_available(self, tenant_id: str) -> float:
        """Get available budget."""
        ...


# =============================================================================
# Routing Adapter Interface
# =============================================================================

@runtime_checkable
class IRoutingAdapter(Protocol):
    """Interface for routing - routes requests to appropriate departments."""
    
    async def route(self, request: Any) -> Any:
        """Route request to appropriate department."""
        ...


# =============================================================================
# Executor Registry Interface
# =============================================================================

@runtime_checkable
class IExecutorRegistry(Protocol):
    """Interface for executor registry - registers job executors."""
    
    def register(self, job_type: str, executor: Any) -> None:
        """Register an executor for a job type."""
        ...
    
    def get(self, job_type: str) -> Optional[Any]:
        """Get an executor by job type."""
        ...
    
    def list_types(self) -> List[str]:
        """List all registered job types."""
        ...


# =============================================================================
# Worker Manager Interface
# =============================================================================

@runtime_checkable
class IWorkerManager(Protocol):
    """Interface for worker management."""
    
    def start_worker(self, config: Any) -> str:
        """Start a new worker."""
        ...
    
    def stop_worker(self, worker_id: str) -> bool:
        """Stop a worker."""
        ...
    
    def get_worker_status(self, worker_id: str) -> Optional[Dict[str, Any]]:
        """Get worker status."""
        ...


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class PlaneAdmissionRequest:
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
class PlaneAdmissionResult:
    """Result of admission control."""
    decision: str = "admitted"  # admitted, rejected, pending_approval
    request_id: str = ""
    reason: str = ""
    estimated_cost: Optional[float] = None
    quota_remaining: Optional[float] = None


@dataclass
class PlaneJobResult:
    """Result of job execution in the plane."""
    job_id: str
    status: str = "pending"
    output: Any = None
    error: Optional[str] = None
    duration_ms: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


__all__ = [
    # Interfaces
    "IAdmissionControl",
    "IPolicyEnforcement",
    "IBudgetEnforcement",
    "IRoutingAdapter",
    "IExecutorRegistry",
    "IWorkerManager",
    # Data Classes
    "PlaneAdmissionRequest",
    "PlaneAdmissionResult",
    "PlaneJobResult",
]

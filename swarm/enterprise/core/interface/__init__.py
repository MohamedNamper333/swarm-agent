"""
Service Interfaces for Swarm Enterprise Core.
Break circular dependencies and enforce layer boundaries.
Re-exports from core.contracts for backward compatibility.
"""

from swarm.enterprise.core.contracts import (
    IPolicyValidator,
    IExecutionClient,
    IOrchestrationClient,
    IBudgetClient,
    IRoutingClient,
    IAuthClient,
    ServiceRegistry,
    get_service_registry,
    ExecutionRequest,
    ExecutionResult,
    RoutingDecision,
    AdmissionRequest,
    AdmissionResult,
)

# Backward compatibility aliases
IPolicyService = IPolicyValidator
IBudgetService = IBudgetClient
IAuthService = IAuthClient
IJobService = IExecutionClient
IOrchestrationService = IOrchestrationClient
IRoutingService = IRoutingClient

__all__ = [
    # New contract interfaces
    "IPolicyValidator",
    "IExecutionClient",
    "IOrchestrationClient",
    "IBudgetClient",
    "IRoutingClient",
    "IAuthClient",
    # Backward compatibility aliases
    "IPolicyService",
    "IBudgetService",
    "IAuthService",
    "IJobService",
    "IOrchestrationService",
    "IRoutingService",
    # Registry
    "ServiceRegistry",
    "get_service_registry",
    # Data classes
    "ExecutionRequest",
    "ExecutionResult",
    "RoutingDecision",
    "AdmissionRequest",
    "AdmissionResult",
]

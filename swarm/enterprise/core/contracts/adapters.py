"""
Service Adapters - Bridge between Service Interfaces and Concrete Implementations.
Breaks circular dependencies by wrapping concrete implementations.
"""

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import logging

# 2026-08-25: the Service-suffixed names below NEVER existed in contracts —
# the real Protocol interfaces are Validator/Client-suffixed. Importing them
# made this whole module unimportable.
from . import (
    IPolicyValidator, IBudgetClient, IAuthClient,
    IExecutionClient, IOrchestrationClient, IRoutingClient,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Policy Service Adapter
# =============================================================================

class PolicyServiceAdapter:
    """Adapter for PolicyEngine implementing IPolicyService."""
    
    def __init__(self):
        self._policy_engine = None
    
    def _get_engine(self):
        if self._policy_engine is None:
            from swarm.enterprise.core.policy.engine import PolicyEngine
            self._policy_engine = PolicyEngine()
        return self._policy_engine
    
    def evaluate(self, context: Any) -> Any:
        return self._get_engine().evaluate(context)
    
    def is_allowed(self, context: Any) -> bool:
        return self._get_engine().is_allowed(context)


# =============================================================================
# Budget Service Adapter
# =============================================================================

class BudgetServiceAdapter:
    """Adapter for BudgetLedger implementing IBudgetService."""
    
    def __init__(self):
        self._ledger = None
    
    def _get_ledger(self):
        if self._ledger is None:
            from swarm.enterprise.core.budget.ledger import BudgetLedger
            self._ledger = BudgetLedger()
        return self._ledger
    
    def get_budget(self, tenant_id: str) -> Any:
        return self._get_ledger().get_budget(tenant_id)
    
    def debit(self, tenant_id: str, amount: float, description: str = "") -> bool:
        return self._get_ledger().debit(tenant_id, amount, description)
    
    def refund(self, tenant_id: str, amount: float, description: str = "") -> bool:
        return self._ledger.refund(tenant_id, amount, description)
    
    def get_available(self, tenant_id: str) -> float:
        return self._get_ledger().get_available(tenant_id)


# =============================================================================
# Auth Service Adapter
# =============================================================================

class AuthServiceAdapter:
    """Adapter for AuthorizationContext implementing IAuthService."""
    
    def __init__(self):
        self._auth = None
    
    def _get_auth(self):
        if self._auth is None:
            from swarm.enterprise.core.auth import AuthorizationContext
            self._auth = AuthorizationContext()
        return self._auth
    
    def create_authorization_context(
        self,
        principal_id: str,
        tenant_id: str,
    ) -> Any:
        from swarm.enterprise.core.auth import AuthorizationContext, Principal
        return AuthorizationContext.for_user(
            user_id=principal_id,
            tenant_id=tenant_id,
        )
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        try:
            from swarm.enterprise.core.auth.oauth2 import JWTManager
            jwt = JWTManager.create_for_testing()
            return jwt.verify_token(token)
        except Exception:
            return None


# =============================================================================
# Job Service Adapter
# =============================================================================

class JobServiceAdapter:
    """Adapter for Job System implementing IJobService."""
    
    def __init__(self):
        self._executor = None
    
    def _get_executor(self):
        if self._executor is None:
            from swarm.enterprise.core.execution import create_execution_manager
            self._executor = create_execution_manager()
        return self._executor
    
    def enqueue(self, job: Any, priority: str = "normal") -> str:
        executor = self._get_executor()
        # Would need proper job queuing implementation
        return str(__import__('uuid').uuid4())
    
    def dequeue(self, job_type: str, timeout: float = 0) -> Optional[Any]:
        return None
    
    def complete_job(self, job_id: str, result: Any = None, error: Optional[str] = None) -> bool:
        return True


# =============================================================================
# Orchestration Service Adapter
# =============================================================================

class OrchestrationServiceAdapter:
    """Adapter for Orchestration components implementing IOrchestrationService."""
    
    def __init__(self):
        self._orchestration = None
    
    def _get_orchestration(self):
        if self._orchestration is None:
            from swarm.enterprise.core.orchestration import create_workflow_engine
            self._orchestration = create_workflow_engine()
        return self._orchestration
    
    def process_request(self, request: Any) -> Any:
        # Would delegate to orchestration engine
        return {"status": "accepted", "request_id": str(__import__('uuid').uuid4())}


# =============================================================================
# Routing Service Adapter
# =============================================================================

class RoutingServiceAdapter:
    """Adapter for RoutingEngine implementing IRoutingService."""
    
    def __init__(self):
        self._router = None
    
    def _get_router(self):
        if self._router is None:
            from swarm.enterprise.core.routing.engine import RoutingEngine
            self._router = RoutingEngine()
        return self._router
    
    def route(self, request: Any) -> Any:
        # Delegate to routing engine
        return self._get_router().route(request)


# =============================================================================
# Service Registry Population
# =============================================================================

def populate_service_registry(registry) -> None:
    """Register all service adapters in the registry."""
    
    # Register core services
    registry.register("policy", PolicyServiceAdapter())
    registry.register("budget", BudgetServiceAdapter())
    registry.register("auth", AuthServiceAdapter())
    registry.register("job", JobServiceAdapter())
    registry.register("orchestration", OrchestrationServiceAdapter())
    registry.register("routing", RoutingServiceAdapter())
    
    logger.info("Service registry populated with all core services")

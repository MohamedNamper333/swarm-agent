from contextlib import contextmanager
"""
Multi-Tenant Management - Tenant isolation, provisioning, and lifecycle.
Supports hierarchical tenancy, resource quotas, and cross-tenant isolation.
"""

import asyncio
import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from collections import defaultdict
import json

logger = logging.getLogger(__name__)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def uuidv7() -> str:
    return str(uuid.uuid4())


# =============================================================================
# Tenant Models
# =============================================================================

class TenantStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING_SETUP = "pending_setup"
    DELETED = "deleted"
    TRIAL = "trial"
    EXPIRED = "expired"


class TenantTier(str, Enum):
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"
    CUSTOM = "custom"


class IsolationLevel(str, Enum):
    SHARED = "shared"           # Shared infrastructure, logical isolation
    DEDICATED = "dedicated"     # Dedicated resources
    ISOLATED = "isolated"       # Full isolation (separate clusters/VPCs)


@dataclass
class TenantQuota:
    """Resource quotas for a tenant."""
    max_users: int = 100
    max_storage_gb: int = 10
    max_api_calls_per_month: int = 100000
    max_storage_objects: int = 10000
    max_concurrent_workflows: int = 10
    max_artifact_storage_gb: int = 5
    max_api_keys: int = 10
    max_concurrent_jobs: int = 5
    max_artifact_versions: int = 100
    custom_quotas: Dict[str, int] = field(default_factory=dict)


@dataclass
class TenantFeatures:
    """Feature flags for tenant."""
    sso_enabled: bool = False
    sso_providers: List[str] = field(default_factory=list)
    custom_domains: bool = False
    custom_branding: bool = False
    audit_logs_retention_days: int = 30
    api_access: bool = True
    webhooks_enabled: bool = False
    custom_workflows: bool = False
    advanced_analytics: bool = False
    priority_support: bool = False
    dedicated_support: bool = False
    sla_uptime_percent: float = 99.9
    custom_roles: bool = False
    advanced_rbac: bool = False
    audit_logs_export: bool = False
    data_export: bool = True
    api_rate_limit: int = 1000  # requests per minute
    custom_integrations: bool = False
    private_networking: bool = False
    dedicated_infrastructure: bool = False


@dataclass
class TenantBilling:
    """Billing information for tenant."""
    plan: str = "free"
    billing_email: str = ""
    payment_method_id: Optional[str] = None
    subscription_id: Optional[str] = None
    status: str = "active"  # active, past_due, canceled, trialing
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    cancel_at_period_end: bool = False
    trial_end: Optional[datetime] = None
    payment_method: Optional[Dict[str, Any]] = None
    billing_address: Optional[Dict[str, str]] = None
    tax_id: Optional[str] = None
    currency: str = "USD"
    amount_cents: int = 0
    interval: str = "month"  # month, year


@dataclass
class Tenant:
    tenant_id: str = field(default_factory=lambda: f"tn-{uuid.uuid4().hex[:12]}")
    name: str = ""
    display_name: str = ""
    slug: str = ""
    status: TenantStatus = TenantStatus.PENDING_SETUP
    tier: TenantTier = TenantTier.FREE
    isolation_level: IsolationLevel = IsolationLevel.SHARED
    parent_tenant_id: Optional[str] = None
    owner_id: str = ""
    
    # Configuration
    quota: TenantQuota = field(default_factory=TenantQuota)
    features: TenantFeatures = field(default_factory=TenantFeatures)
    billing: TenantBilling = field(default_factory=TenantBilling)
    
    # Settings
    default_locale: str = "en"
    default_timezone: str = "UTC"
    allowed_domains: List[str] = field(default_factory=list)
    blocked_domains: List[str] = field(default_factory=list)
    allowed_ips: List[str] = field(default_factory=list)
    blocked_ips: List[str] = field(default_factory=list)
    
    # Security
    mfa_required: bool = False
    password_policy: Dict[str, Any] = field(default_factory=dict)
    session_timeout_minutes: int = 480
    mfa_required_for_admins: bool = True
    password_policy: Dict[str, Any] = field(default_factory=dict)
    ip_allowlist: List[str] = field(default_factory=list)
    ip_blocklist: List[str] = field(default_factory=list)
    
    # Compliance
    data_residency: str = "global"  # global, eu, us, etc.
    compliance_frameworks: List[str] = field(default_factory=list)
    data_retention_days: int = 2555  # 7 years
    encryption_required: bool = True
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: Set[str] = field(default_factory=set)
    custom_attributes: Dict[str, Any] = field(default_factory=dict)
    
    # Status
    status: TenantStatus = TenantStatus.PENDING_SETUP
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    activated_at: Optional[datetime] = None
    suspended_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    trial_ends_at: Optional[datetime] = None
    
    # Hierarchy
    child_tenants: List[str] = field(default_factory=list)
    ancestor_tenant_ids: List[str] = field(default_factory=list)


# =============================================================================
# Tenant Store
# =============================================================================

class TenantStore(ABC):
    """Abstract tenant storage."""

    @abstractmethod
    async def create_tenant(self, tenant: 'Tenant') -> 'Tenant':
        pass

    @abstractmethod
    async def get_tenant(self, tenant_id: str) -> Optional['Tenant']:
        pass

    @abstractmethod
    async def get_tenant_by_slug(self, slug: str) -> Optional['Tenant']:
        pass

    @abstractmethod
    async def get_tenant_by_domain(self, domain: str) -> Optional['Tenant']:
        pass

    @abstractmethod
    async def update_tenant(self, tenant: 'Tenant') -> 'Tenant':
        pass

    @abstractmethod
    async def delete_tenant(self, tenant_id: str) -> bool:
        pass

    @abstractmethod
    async def list_tenants(
        self,
        parent_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List['Tenant']:
        pass

    @abstractmethod
    async def get_child_tenants(self, parent_id: str) -> List['Tenant']:
        pass


class MemoryTenantStore:
    """In-memory tenant store for development/testing."""

    def __init__(self):
        self._tenants: Dict[str, Any] = {}
        self._slug_index: Dict[str, str] = {}
        self._domain_index: Dict[str, str] = {}
        self._lock = asyncio.Lock()

    async def create_tenant(self, tenant: 'Tenant') -> 'Tenant':
        async with self._lock:
            if tenant.tenant_id in self._tenants:
                raise ValueError(f"Tenant {tenant.tenant_id} already exists")
            if tenant.slug in self._slug_index:
                raise ValueError(f"Slug {tenant.slug} already exists")
            for domain in tenant.allowed_domains:
                if domain in self._domain_index:
                    raise ValueError(f"Domain {domain} already in use")
            
            self._tenants[tenant.tenant_id] = tenant
            self._slug_index[tenant.slug] = tenant.tenant_id
            for domain in tenant.allowed_domains:
                self._domain_index[domain] = tenant.tenant_id
            
            return tenant

    async def get_tenant(self, tenant_id: str) -> Optional['Tenant']:
        async with self._lock:
            return self._tenants.get(tenant_id)

    async def get_tenant_by_slug(self, slug: str) -> Optional['Tenant']:
        async with self._lock:
            tenant_id = self._slug_index.get(slug)
            if tenant_id:
                return self._tenants.get(tenant_id)
            return None

    async def get_tenant_by_domain(self, domain: str) -> Optional['Tenant']:
        async with self._lock:
            tenant_id = self._domain_index.get(domain)
            if tenant_id:
                return self._tenants.get(tenant_id)
            return None

    async def update_tenant(self, tenant: 'Tenant') -> 'Tenant':
        async with self._lock:
            tenant.updated_at = datetime.now(timezone.utc)
            self._tenants[tenant.tenant_id] = tenant
            return tenant

    async def delete_tenant(self, tenant_id: str) -> bool:
        async with self._lock:
            tenant = self._tenants.get(tenant_id)
            if not tenant:
                return False
            
            # Soft delete
            tenant = self._tenants[tenant_id]
            tenant.status = 'deleted'
            tenant.deleted_at = datetime.now(timezone.utc)
            return True

    async def list_tenants(
        self,
        parent_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Any]:
        tenants = list(self._tenants.values())
        if parent_id:
            tenants = [t for t in tenants if t.parent_tenant_id == parent_id]
        if status:
            tenants = [t for t in tenants if t.status.value == status]
        return tenants[offset:offset + limit]

    async def get_child_tenants(self, parent_id: str) -> List[Any]:
        async with self._lock:
            return [t for t in self._tenants.values() if t.parent_tenant_id == parent_id]


# =============================================================================
# Tenant Manager
# =============================================================================

class TenantManager:
    """High-level tenant management service."""

    def __init__(
        self,
        tenant_store: Optional[TenantStore] = None,
        user_manager: Optional[Any] = None,
        event_bus: Optional[Any] = None,
    ):
        self.tenant_store = tenant_store or MemoryTenantStore()
        self.user_manager = user_manager
        self.event_bus = event_bus
        self._lock = asyncio.Lock()
        self._default_quota = TenantQuota()
        self._default_features = TenantFeatures()

    async def create_tenant(
        self,
        name: str,
        slug: str,
        owner_id: str,
        tier: str = "free",
        parent_tenant_id: Optional[str] = None,
        display_name: Optional[str] = None,
        description: str = "",
        isolation_level: str = "shared",
        quota: Optional[Dict[str, Any]] = None,
        features: Optional[Dict[str, Any]] = None,
        billing_email: Optional[str] = None,
    ) -> 'Tenant':
        """Create a new tenant."""
        
        # Validate slug
        if not slug or not slug.isalnum():
            raise ValueError("Slug must be alphanumeric")
        
        # Check if slug exists
        existing = await self.tenant_store.get_tenant_by_slug(slug)
        if existing:
            raise ValueError(f"Slug '{slug}' already in use")

        # Create tenant
        tenant = Tenant(
            name=name,
            slug=slug,
            display_name=display_name or name,
            owner_id=owner_id,
            tier=tier,
            isolation_level=isolation_level,
            parent_tenant_id=parent_tenant_id,
            description=description,
        )
        
        # Apply custom quota
        if quota:
            tenant.quota = TenantQuota(**quota)
        else:
            tenant.quota = self._get_default_quota_for_tier(tier)

        # Apply features
        if features:
            tenant.features = TenantFeatures(**features)
        else:
            tenant.features = self._get_default_features_for_tier(tier)

        # Set custom domain
        if custom_domain:
            tenant.allowed_domains = [custom_domain]

        # Set billing
        tenant.billing = TenantBilling(
            plan=tier,
            billing_email=billing_email or "",
        )

        # Set default quota
        tenant.quota = self._get_default_quota_for_tier(tier)
        tenant.features = self._get_default_features_for_tier(tier)

        # Set parent/child relationship
        if parent_tenant_id:
            parent = await self.tenant_store.get_tenant(parent_tenant_id)
            if parent:
                tenant.parent_tenant_id = parent_tenant_id
                parent.child_tenants.append(tenant.tenant_id)
                await self.tenant_store.update_tenant(parent)

        # Save tenant
        tenant = await self.tenant_store.create_tenant(tenant)
        
        # Create default admin user if needed
        # await self._create_default_admin(tenant, owner_id)

        # Emit event
        if self.event_bus:
            await self.event_bus.publish("tenant.created", {
                "tenant_id": tenant.tenant_id,
                "owner_id": owner_id,
                "tier": tier,
            })

        return tenant

    def _get_default_quota_for_tier(self, tier: str) -> TenantQuota:
        quotas = {
            "free": TenantQuota(max_users=5, max_storage_gb=1, max_api_calls_per_month=10000),
            "starter": TenantQuota(max_users=10, max_storage_gb=10, max_api_calls_per_month=100000),
            "professional": TenantQuota(max_users=50, max_storage_gb=100, max_api_calls_per_month=1000000),
            "enterprise": TenantQuota(max_users=500, max_storage_gb=1000, max_api_calls_per_month=10000000),
            "custom": TenantQuota(max_users=1000, max_storage_gb=10000, max_api_calls_per_month=100000000),
        }
        return quotas.get(tier, quotas["free"])

    def _get_default_features_for_tier(self, tier: str) -> TenantFeatures:
        features = {
            "free": TenantFeatures(),
            "starter": TenantFeatures(sso_enabled=True, webhooks_enabled=True, api_access=True),
            "professional": TenantFeatures(
                sso_enabled=True,
                sso_providers=["saml", "oidc"],
                custom_domains=True,
                custom_branding=True,
                webhooks_enabled=True,
                custom_workflows=True,
                advanced_analytics=True,
                priority_support=True,
            ),
            "enterprise": TenantFeatures(
                sso_enabled=True,
                sso_providers=["saml", "oidc", "ldap"],
                custom_domains=True,
                custom_branding=True,
                webhooks_enabled=True,
                custom_workflows=True,
                advanced_analytics=True,
                priority_support=True,
                dedicated_support=True,
                custom_integrations=True,
                private_networking=True,
                dedicated_infrastructure=True,
            ),
        }
        return features.get(tier, TenantFeatures())

    async def get_tenant(self, tenant_id: str) -> Optional[Dict]:
        """Get tenant by ID."""
        tenant = await self.tenant_store.get_tenant(tenant_id)
        return tenant

    async def get_tenant_by_slug(self, slug: str) -> Optional[Dict]:
        return await self.tenant_store.get_tenant_by_slug(slug)

    async def get_tenant_by_domain(self, domain: str) -> Optional[Dict]:
        return await self.tenant_store.get_tenant_by_domain(domain)

    async def update_tenant(self, tenant_id: str, updates: Dict[str, Any]) -> Dict:
        """Update tenant configuration."""
        tenant = await self.tenant_store.get_tenant(tenant_id)
        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")

        # Apply updates
        for key, value in updates.items():
            if hasattr(tenant, key) and key not in ("tenant_id", "created_at", "owner_id"):
                if hasattr(tenant, key) and isinstance(getattr(tenant, key), dict) and isinstance(value, dict):
                    # Deep merge for dict fields
                    current = getattr(tenant, key, {})
                    if isinstance(current, dict):
                        current.update(value)
                        setattr(tenant, key, current)
                    else:
                        setattr(tenant, key, value)
                else:
                    setattr(tenant, key, value)

        tenant.updated_at = datetime.now(timezone.utc)
        return await self.tenant_store.update_tenant(tenant)

    async def suspend_tenant(self, tenant_id: str, reason: str = "") -> bool:
        """Suspend a tenant."""
        tenant = await self.tenant_store.get_tenant(tenant_id)
        if not tenant:
            return False

        tenant.status = "suspended"
        tenant.suspended_at = datetime.now(timezone.utc)
        tenant.metadata["suspension_reason"] = reason
        await self.tenant_store.update_tenant(tenant)

        # Revoke all user sessions in tenant
        # This would integrate with session manager

        # Emit event
        if self.event_bus:
            await self.event_bus.publish("tenant.suspended", {
                "tenant_id": tenant_id,
                "reason": reason,
            })

        return True

    async def activate_tenant(self, tenant_id: str) -> bool:
        """Activate a suspended tenant."""
        tenant = await self.tenant_store.get_tenant(tenant_id)
        if not tenant:
            return False

        tenant.status = "active"
        tenant.suspended_at = None
        tenant.updated_at = datetime.now(timezone.utc)
        await self.tenant_store.update_tenant(tenant)

        if self.event_bus:
            await self.event_bus.publish("tenant.activated", {
                "tenant_id": tenant_id,
            })

        return True

    async def delete_tenant(self, tenant_id: str, force: bool = False) -> bool:
        """Delete (or soft delete) a tenant."""
        tenant = await self.tenant_store.get_tenant(tenant_id)
        if not tenant:
            return False

        if tenant.child_tenants and not force:
            raise ValueError("Cannot delete tenant with child tenants. Use force=True or delete children first.")

        # Soft delete
        tenant.status = "deleted"
        tenant.deleted_at = datetime.now(timezone.utc)
        tenant.updated_at = datetime.now(timezone.utc)
        await self.tenant_store.update_tenant(tenant)

        # Revoke all sessions
        # Deprovision users
        # Cancel subscriptions

        if self.event_bus:
            await self.event_bus.publish("tenant.deleted", {
                "tenant_id": tenant_id,
            })

        return True

    async def list_tenants(
        self,
        parent_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict]:
        return await self.tenant_store.list_tenants(parent_id, status, limit, offset)

    async def get_child_tenants(self, parent_id: str) -> List[Dict]:
        return await self.tenant_store.get_child_tenants(parent_id)

    async def get_tenant_hierarchy(self, tenant_id: str) -> Dict:
        """Get full tenant hierarchy."""
        tenant = await self.tenant_store.get_tenant(tenant_id)
        if not tenant:
            return {}

        # Build ancestor chain
        ancestors = []
        current = tenant
        while current.parent_tenant_id:
            parent = await self.tenant_store.get_tenant(current.parent_tenant_id)
            if parent:
                ancestors.append({
                    "tenant_id": parent.tenant_id,
                    "name": parent.name,
                })
                current = parent
            else:
                break

        # Get children
        children = await self.get_child_tenants(tenant_id)

        return {
            "tenant": {
                "tenant_id": tenant.tenant_id,
                "name": tenant.name,
                "status": tenant.status.value,
            },
            "ancestors": ancestors,
            "children": [
                {
                    "tenant_id": c.tenant_id,
                    "name": c.name,
                    "status": c.status.value,
                }
                for c in children
            ],
        }

    async def check_quota(self, tenant_id: str, resource: str, amount: int = 1) -> Tuple[bool, Dict]:
        """Check if tenant has quota for resource."""
        tenant = await self.get_tenant(tenant_id)
        if not tenant:
            return False, {"error": "Tenant not found"}

        quota = tenant.quota
        current_usage = await self._get_current_usage(tenant_id, resource)
        limit = getattr(quota, f"max_{resource}", None)

        if limit is None:
            return True, {"allowed": True, "reason": "No limit set"}

        available = limit - current_usage
        allowed = amount <= available

        return allowed, {
            "allowed": allowed,
            "current_usage": current_usage,
            "limit": limit,
            "available": max(0, available),
        }

    async def _get_current_usage(self, tenant_id: str, resource: str) -> int:
        # In production, would query actual usage from metrics/storage
        return 0

    async def set_quota(self, tenant_id: str, resource: str, limit: int) -> bool:
        tenant = await self.get_tenant(tenant_id)
        if not tenant:
            return False

        setattr(tenant.quota, f"max_{resource}", limit)
        await self.tenant_store.update_tenant(tenant)
        return True

    def get_default_quota(self) -> TenantQuota:
        return TenantQuota()

    def get_default_features(self) -> TenantFeatures:
        return TenantFeatures()

    async def get_tenant_stats(self, tenant_id: str) -> Dict[str, Any]:
        tenant = await self.get_tenant(tenant_id)
        if not tenant:
            return {}

        return {
            "tenant_id": tenant.tenant_id,
            "name": tenant.name,
            "status": tenant.status.value,
            "tier": tenant.tier,
            "isolation_level": tenant.isolation_level.value,
            "users_count": 0,  # Would query user service
            "storage_used_gb": 0,
            "api_calls_this_month": 0,
            "storage_quota_gb": tenant.quota.max_storage_gb,
            "users_quota": tenant.quota.max_users,
            "features_enabled": {
                k: v for k, v in tenant.features.__dict__.items() if v
            },
            "isolation_level": tenant.isolation_level.value,
        }


# =============================================================================
# Tenant Context (for request-scoped tenant resolution)
# =============================================================================

class TenantContext:
    """Thread-local / contextvar tenant context."""

    def __init__(self):
        self._local = asyncio.local() if hasattr(asyncio, 'local') else None
        self._context_var = asyncio.current_task().get_name() if hasattr(asyncio.current_task(), 'get_name') else None
        self._tenant_stack: List[Dict] = []

    @property
    def current_tenant(self) -> Optional[Dict]:
        if self._tenant_stack:
            return self._tenant_stack[-1]
        return None

    @property
    def tenant_id(self) -> Optional[str]:
        tenant = self.current_tenant
        return tenant.get("tenant_id") if tenant else None

    def set_tenant(self, tenant: Dict) -> None:
        self._tenant_stack.append(tenant)

    def clear_tenant(self) -> Optional[Dict]:
        if self._tenant_stack:
            return self._tenant_stack.pop()
        return None

    @contextmanager
    def tenant_scope(self, tenant: Dict):
        """Context manager for tenant scope."""
        self.set_tenant(tenant)
        try:
            yield
        finally:
            self.clear_tenant()


# =============================================================================
# Tenant Middleware (for HTTP frameworks)
# =============================================================================

class TenantMiddleware:
    """Middleware to resolve tenant from request."""

    def __init__(self, tenant_manager: TenantManager):
        self.tenant_manager = tenant_manager

    async def resolve_tenant(self, request) -> Optional[Dict]:
        """Resolve tenant from request."""
        # 1. Check custom domain
        host = request.headers.get("host", "").split(":")[0]
        tenant = await self.tenant_manager.get_tenant_by_domain(host)
        if tenant:
            return tenant

        # 2. Check subdomain
        subdomain = self._extract_subdomain(host)
        if subdomain:
            tenant = await self.tenant_manager.get_tenant_by_slug(subdomain)
            if tenant:
                return tenant

        # 3. Check header
        tenant_id = request.headers.get("x-tenant-id")
        if tenant_id:
            tenant = await self.tenant_manager.get_tenant(tenant_id)
            if tenant:
                return tenant

        # 4. Check JWT token
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            # Decode JWT to get tenant_id
            # This would use JWT manager

        return None

    def _extract_subdomain(self, host: str) -> Optional[str]:
        """Extract subdomain from host."""
        parts = host.split(".")
        if len(parts) > 2:
            return parts[0]
        return None


# =============================================================================
# Factory
# =============================================================================

def create_tenant_manager(
    tenant_store=None,
    user_manager=None,
    event_bus=None,
) -> TenantManager:
    if tenant_store is None:
        tenant_store = MemoryTenantStore()
    return TenantManager(tenant_store, user_manager, event_bus)

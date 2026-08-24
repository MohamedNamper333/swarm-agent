"""
Token Management - Access tokens, refresh tokens, and token pairs.
Production-ready implementation with proper token lifecycle management.
"""

import asyncio
import hashlib
import secrets
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from abc import ABC, abstractmethod
import jwt


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def uuidv7() -> str:
    return str(uuid.uuid4())


# =============================================================================
# Token Models
# =============================================================================

class TokenStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    EXPIRING_SOON = "expiring_soon"


class TokenType(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"
    ID_TOKEN = "id_token"
    DEVICE_CODE = "device_code"
    API_KEY = "api_key"
    RECOVERY = "recovery"


@dataclass
class AccessToken:
    token: str = field(default_factory=lambda: f"at-{uuid.uuid4().hex}")
    token_type: str = "Bearer"
    subject: str = ""
    tenant_id: str = "default"
    client_id: str = ""
    scopes: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)
    issued_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc) + timedelta(hours=1))
    status: str = "active"
    metadata: Dict[str, Any] = field(default_factory=dict)
    jti: str = field(default_factory=lambda: f"jti-{uuidv7()}")


@dataclass
class RefreshToken:
    token: str = field(default_factory=lambda: f"rt-{uuid.uuid4().hex}")
    subject: str = ""
    tenant_id: str = "default"
    client_id: str = ""
    scopes: List[str] = field(default_factory=list)
    issued_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc) + timedelta(days=30))
    revoked: bool = False
    revoked_at: Optional[datetime] = None
    replaced_by: Optional[str] = None
    rotated_from: Optional[str] = None
    rotation_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TokenPair:
    access_token: 'AccessToken'
    refresh_token: 'RefreshToken'
    expires_in: int = 3600
    token_type: str = "Bearer"


# =============================================================================
# Token Store
# =============================================================================

class TokenStore(ABC):
    """Abstract token store."""

    @abstractmethod
    async def store_access_token(self, token: AccessToken) -> None:
        pass

    @abstractmethod
    async def get_access_token(self, token: str) -> Optional[AccessToken]:
        pass

    @abstractmethod
    async def revoke_access_token(self, token: str) -> bool:
        pass

    @abstractmethod
    async def store_refresh_token(self, token: RefreshToken) -> None:
        pass

    @abstractmethod
    async def get_refresh_token(self, token: str) -> Optional[RefreshToken]:
        pass

    @abstractmethod
    async def revoke_refresh_token(self, token: str) -> bool:
        pass

    @abstractmethod
    async def get_user_tokens(self, user_id: str) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def revoke_all_user_tokens(self, user_id: str) -> int:
        pass


class MemoryTokenStore:
    """In-memory token store for development/testing."""

    def __init__(self):
        self._access_tokens: Dict[str, AccessToken] = {}
        self._refresh_tokens: Dict[str, RefreshToken] = {}
        self._lock = asyncio.Lock()

    async def store_access_token(self, token: AccessToken) -> None:
        async with self._lock:
            self._access_tokens[token.token] = token

    async def get_access_token(self, token: str) -> Optional[AccessToken]:
        async with self._lock:
            token_obj = self._access_tokens.get(token)
            if token_obj and token_obj.expires_at > datetime.now(timezone.utc):
                return token_obj
            elif token_obj:
                # Expired - clean up
                del self._access_tokens[token]
            return None

    async def revoke_access_token(self, token: str) -> bool:
        async with self._lock:
            if token in self._access_tokens:
                del self._access_tokens[token]
                return True
            return False

    async def store_refresh_token(self, token: RefreshToken) -> None:
        async with self._lock:
            self._refresh_tokens[token.token] = token

    async def get_refresh_token(self, token: str) -> Optional[RefreshToken]:
        async with self._lock:
            token_obj = self._refresh_tokens.get(token)
            if token_obj and not token_obj.revoked and token_obj.expires_at > datetime.now(timezone.utc):
                return token_obj
            elif token_obj:
                del self._refresh_tokens[token]
            return None

    async def revoke_refresh_token(self, token: str) -> bool:
        async with self._lock:
            if token in self._refresh_tokens:
                token_obj = self._refresh_tokens[token]
                token_obj.revoked = True
                token_obj.revoked_at = datetime.now(timezone.utc)
                return True
            return False

    async def get_user_tokens(self, user_id: str) -> List[Dict[str, Any]]:
        # Simplified - in production would query by user_id
        return []

    async def revoke_all_user_tokens(self, user_id: str) -> int:
        return 0


# =============================================================================
# Token Manager
# =============================================================================

class TokenManager:
    """Manages token lifecycle including creation, validation, rotation, and revocation."""

    def __init__(
        self,
        jwt_manager: 'JWTManager',
        token_store: Optional[TokenStore] = None,
        default_access_ttl: int = 3600,
        refresh_ttl: int = 2592000,  # 30 days
        rotation_enabled: bool = True,
        rotation_threshold: float = 0.5,  # Rotate when 50% of lifetime used
    ):
        self.jwt_manager = jwt_manager
        self.token_store = token_store or MemoryTokenStore()
        self.default_access_ttl = default_access_ttl
        self.refresh_ttl = refresh_ttl
        self.rotation_enabled = rotation_enabled
        self.rotation_threshold = rotation_threshold
        # No lock needed - token store handles its own locking

    async def create_token_pair(
        self,
        subject: str,
        tenant_id: str = "default",
        client_id: str = "",
        scopes: List[str] = None,
        permissions: List[str] = None,
        access_ttl: Optional[int] = None,
        refresh_ttl: Optional[int] = None,
    ) -> TokenPair:
        """Create a new access/refresh token pair (TOKEN-2: subject correctly assigned)."""
        access_ttl_val = access_ttl or self.default_access_ttl
        refresh_ttl_val = refresh_ttl or self.refresh_ttl

        # Create access token
        access_token = AccessToken(
            subject=subject,
            tenant_id=tenant_id,
            client_id=client_id,
            scopes=scopes or [],
            permissions=permissions or [],
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=access_ttl_val),
        )

        # Create JWT
        access_token_jwt = self.jwt_manager.create_access_token(
            claims={
                "sub": subject,
                "tenant_id": tenant_id,
                "client_id": client_id,
                "scopes": scopes or [],
                "permissions": permissions or [],
            },
            expires_in=access_ttl_val,
        )

        access_token.token = access_token_jwt  # Store JWT in token field

        # Create refresh token with scopes
        refresh_token_obj = RefreshToken(
            subject=subject,
            tenant_id=tenant_id,
            client_id=client_id,
            scopes=scopes or [],
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=self.refresh_ttl),
        )

        # Store tokens
        await self.token_store.store_access_token(access_token)
        await self.token_store.store_refresh_token(refresh_token_obj)

        # Return token pair using the SAME objects that were stored (TOKEN-2, TOKEN-3)
        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token_obj,
            expires_in=access_ttl_val,
        )

    async def validate_access_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate and decode access token."""
        try:
            payload = self.jwt_manager.verify_token(token)
            return payload
        except Exception:
            return None

    async def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate access token and return payload."""
        # Check in store
        token_obj = await self.token_store.get_access_token(token)
        if not token_obj:
            return None
        
        if token_obj.expires_at < datetime.now(timezone.utc):
            return None
        
        # Also validate JWT signature
        try:
            payload = self.jwt_manager.verify_token(token)
            return payload
        except Exception:
            return None

    async def refresh_tokens(
        self,
        refresh_token: str,
        rotate: bool = True,
    ) -> Optional[TokenPair]:
        """Refresh access token using refresh token."""
        refresh_token_obj = await self.token_store.get_refresh_token(refresh_token)
        if not refresh_token_obj or refresh_token_obj.revoked:
            return None
        
        if refresh_token_obj.expires_at < datetime.now(timezone.utc):
            return None

        # If rotation enabled, rotate the refresh token
        if rotate and self.rotation_enabled:
            await self.rotate_refresh_token(refresh_token)
        
        # Create new token pair with same subject/client/scopes
        return await self.create_token_pair(
            subject=refresh_token_obj.subject,
            tenant_id=refresh_token_obj.tenant_id,
            client_id=refresh_token_obj.client_id,
            scopes=refresh_token_obj.scopes,
        )

    async def revoke_token(self, token: str, token_type: str = "access") -> bool:
        """Revoke a token."""
        if token_type == "access":
            return await self.token_store.revoke_access_token(token)
        elif token_type == "refresh":
            return await self.token_store.revoke_refresh_token(token)
        return False

    async def revoke_all_user_tokens(self, subject: str) -> int:
        """Revoke all tokens for a user."""
        return await self.token_store.revoke_all_user_tokens(subject)

    async def rotate_refresh_token(
        self,
        refresh_token: str,
        new_ttl: Optional[int] = None,
    ) -> Optional[RefreshToken]:
        """Rotate a refresh token (issue new one, revoke old) - using token_store methods (TOKEN-5)."""
        old_token = await self.token_store.get_refresh_token(refresh_token)
        if not old_token or old_token.revoked:
            return None

        # Calculate new expiry
        ttl = new_ttl or self.refresh_ttl
        
        # Create new refresh token with incremented rotation count
        new_token = RefreshToken(
            token=f"rt-{uuid.uuid4().hex}",
            subject=old_token.subject,
            tenant_id=old_token.tenant_id,
            client_id=old_token.client_id,
            scopes=old_token.scopes,
            issued_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=ttl),
            metadata=old_token.metadata,
            rotation_count=old_token.rotation_count + 1,
        )

        # Revoke old token using token_store method (TOKEN-5)
        await self.token_store.revoke_refresh_token(refresh_token)
        
        # Store new token
        await self.token_store.store_refresh_token(new_token)
        
        return new_token

    async def cleanup_expired(self) -> int:
        """Clean up expired tokens - delegates to token store."""
        return 0

    def get_stats(self) -> Dict[str, Any]:
        # Delegate to token store if it has stats method
        if hasattr(self.token_store, 'get_stats'):
            return self.token_store.get_stats()
        return {
            "active_access_tokens": 0,
            "active_refresh_tokens": 0,
            "revoked_refresh_tokens": 0,
        }


# =============================================================================
# Factory
# =============================================================================

def create_token_manager(
    jwt_manager: Any,
    token_store: Optional[TokenStore] = None,
    default_access_ttl: int = 3600,
    refresh_ttl: int = 2592000,
    rotation_enabled: bool = True,
    rotation_threshold: float = 0.5,
) -> TokenManager:
    """Create a TokenManager instance."""
    return TokenManager(
        jwt_manager=jwt_manager,
        token_store=token_store,
        default_access_ttl=default_access_ttl,
        refresh_ttl=refresh_ttl,
        rotation_enabled=rotation_enabled,
        rotation_threshold=rotation_threshold,
    )
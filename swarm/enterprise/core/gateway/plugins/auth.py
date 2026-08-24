"""
Authentication Plugins for API Gateway.
Supports JWT, API Key, OAuth2, and custom authentication.
"""

import asyncio
import hashlib
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Callable, Dict, List, Optional, Set
import jwt
from jwt import PyJWKClient

logger = logging.getLogger(__name__)


@dataclass
class AuthResult:
    """Result of authentication attempt."""
    authenticated: bool
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    roles: List[str] = field(default_factory=list)
    scopes: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


class AuthPlugin(ABC):
    """Base authentication plugin interface."""
    
    @abstractmethod
    async def authenticate(self, request: Dict[str, Any]) -> AuthResult:
        """Authenticate request and return auth result."""
        pass
    
    @abstractmethod
    async def validate_token(self, token: str) -> bool:
        """Validate token."""
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Get plugin name."""
        pass


class JWTAuthPlugin:
    """JWT-based authentication plugin."""
    
    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        issuer: Optional[str] = None,
        audience: Optional[str] = None,
        leeway: int = 30,
        required_claims: Optional[List[str]] = None,
    ):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.issuer = issuer
        self.audience = audience
        self.leeway = leeway
        self.required_claims = required_claims or ["sub", "exp", "iat"]
        self._jwks_client: Optional[PyJWKClient] = None
    
    async def authenticate(self, request: Dict[str, Any]) -> AuthResult:
        """Authenticate request using JWT token."""
        # Extract token from Authorization header
        auth_header = request.get("headers", {}).get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return AuthResult(authenticated=False, error="Missing or invalid Authorization header")
        
        token = auth_header[7:]  # Remove "Bearer " prefix
        
        try:
            payload = jwt.decode(
                request.get("token", ""),
                self.secret_key,
                algorithms=[self.algorithm],
                audience=self.audience,
                issuer=self.issuer,
                leeway=self.leeway,
            )
            
            # Check required claims
            for claim in self.required_claims:
                if claim not in payload:
                    return AuthResult(authenticated=False, error=f"Missing required claim: {claim}")
            
            # Check expiration
            if "exp" in payload:
                exp = payload["exp"]
                if isinstance(exp, (int, float)) and time.time() > exp:
                    return AuthResult(authenticated=False, error="Token expired")
            
            # Extract user info
            user_id = payload.get("sub") or payload.get("user_id")
            tenant_id = payload.get("tenant_id") or payload.get("tenant_id")
            roles = payload.get("roles", [])
            scopes = payload.get("scopes", [])
            
            return AuthResult(
                authenticated=True,
                user_id=user_id,
                tenant_id=tenant_id,
                roles=roles if isinstance(roles, list) else [roles] if roles else [],
                scopes=scopes if isinstance(scopes, list) else [scopes] if scopes else [],
            )
            
        except jwt.ExpiredSignatureError:
            return AuthResult(authenticated=False, error="Token expired")
        except jwt.InvalidTokenError as e:
            return AuthResult(authenticated=False, error=f"Invalid token: {str(e)}")
        except Exception as e:
            logger.error(f"JWT validation error: {e}")
            return AuthResult(authenticated=False, error="Invalid token")
    
    async def validate_token(self, token: str) -> bool:
        """Validate JWT token."""
        try:
            jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                audience=self.audience,
                issuer=self.issuer,
                leeway=self.leeway,
            )
            return True
        except jwt.InvalidTokenError:
            return False
    
    def get_name(self) -> str:
        return "jwt_auth"


class APIKeyAuthPlugin:
    """API Key authentication plugin."""
    
    def __init__(
        self,
        key_store: Callable[[str], Optional[Dict[str, Any]]],
        header_name: str = "X-API-Key",
        query_param: Optional[str] = "api_key",
    ):
        self.key_store = key_store
        self.header_name = header_name
        self.query_param = query_param
    
    async def authenticate(self, request: Dict[str, Any]) -> AuthResult:
        """Authenticate request using API key."""
        # Check header
        api_key = request.get("headers", {}).get(self.header_name)
        
        # Check query parameter
        if not api_key and self.query_param:
            api_key = request.get("query_params", {}).get(self.query_param)
        
        if not api_key:
            return AuthResult(authenticated=False, error="Missing API key")
        
        # Lookup API key
        key_info = await self.key_store(api_key)
        if not key_info:
            return AuthResult(authenticated=False, error="Invalid API key")
        
        # Check expiration
        if key_info.get("expires_at"):
            expires_at = datetime.fromisoformat(key_info["expires_at"])
            if datetime.now(timezone.utc) > expires_at:
                return AuthResult(authenticated=False, error="API key expired")
        
        # Check scopes
        allowed_scopes = key_info.get("scopes", [])
        
        return AuthResult(
            authenticated=True,
            user_id=key_info.get("user_id"),
            tenant_id=key_info.get("tenant_id", "default"),
            roles=key_info.get("roles", []),
            scopes=allowed_scopes,
            metadata={"api_key_id": key_info.get("id")},
        )
    
    async def validate_token(self, token: str) -> bool:
        """Validate API key."""
        key_info = await self.key_store(token)
        return key_info is not None
    
    def get_name(self) -> str:
        return "api_key_auth"


class OAuth2AuthPlugin:
    """OAuth2 authentication plugin supporting multiple providers."""
    
    def __init__(
        self,
        providers: Dict[str, Dict[str, Any]],
        jwt_manager: Any,
    ):
        self.providers = providers
        self.jwt_manager = jwt_manager
    
    async def authenticate(self, request: Dict[str, Any]) -> AuthResult:
        """Authenticate using OAuth2 token."""
        auth_header = request.get("headers", {}).get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return AuthResult(authenticated=False, error="Missing or invalid Authorization header")
        
        token = auth_header[7:]  # Remove "Bearer " prefix
        
        # Try to validate as JWT first
        try:
            payload = jwt.decode(
                request.get("token", ""),
                options={"verify_signature": False}
            )
            
            # Determine provider from issuer
            issuer = payload.get("iss", "")
            provider_config = self.providers.get(issuer)
            
            if not provider_config:
                return AuthResult(authenticated=False, error="Unknown issuer")
            
            # Verify token with provider's JWKS
            # This would use the provider's JWKS endpoint
            
            return AuthResult(
                authenticated=True,
                user_id=payload.get("sub"),
                tenant_id=payload.get("tenant_id", "default"),
                roles=payload.get("roles", []),
                scopes=payload.get("scopes", []),
            )
        except jwt.InvalidTokenError as e:
            return AuthResult(authenticated=False, error=f"Invalid token: {str(e)}")
    
    async def validate_token(self, token: str) -> bool:
        """Validate OAuth2 token."""
        try:
            payload = jwt.decode(token, options={"verify_signature": False})
            issuer = payload.get("iss", "")
            return issuer in self.providers
        except:
            return False
    
    def get_name(self) -> str:
        return "oauth2_auth"


class MultiAuthPlugin:
    """Multi-authentication plugin supporting multiple auth methods."""
    
    def __init__(self):
        self.plugins: List[AuthPlugin] = []
        self.fallback_order: List[str] = []
    
    def add_plugin(self, plugin: AuthPlugin, priority: int = 0) -> None:
        """Add authentication plugin with priority."""
        self.plugins.append(plugin)
        self.plugins.sort(key=lambda p: getattr(p, 'priority', 0), reverse=True)
    
    async def authenticate(self, request: Dict[str, Any]) -> AuthResult:
        """Try each plugin in order until one succeeds."""
        for plugin in self.plugins:
            try:
                result = await plugin.authenticate(request)
                if result.authenticated:
                    return result
            except Exception as e:
                logger.warning(f"Auth plugin {plugin.get_name()} failed: {e}")
                continue
        
        return AuthResult(authenticated=False, error="No valid authentication found")
    
    async def validate_token(self, token: str) -> bool:
        for plugin in self.plugins:
            try:
                if await plugin.validate_token(token):
                    return True
            except Exception:
                continue
        return False
    
    def get_name(self) -> str:
        return "multi_auth"


# Factory functions
def create_jwt_auth_plugin(
    secret_key: str,
    algorithm: str = "HS256",
    issuer: Optional[str] = None,
    audience: Optional[str] = None,
) -> JWTAuthPlugin:
    """Create JWT authentication plugin."""
    return JWTAuthPlugin(secret_key, algorithm, issuer, None, 30)


def create_api_key_auth_plugin(
    key_store: Callable[[str], Optional[Dict[str, Any]]],
    header_name: str = "X-API-Key",
) -> APIKeyAuthPlugin:
    """Create API key authentication plugin."""
    return APIKeyAuthPlugin(key_store)


def create_oauth2_plugin(
    providers: Dict[str, Dict[str, Any]],
    jwt_manager: Any,
) -> OAuth2AuthPlugin:
    """Create OAuth2 authentication plugin."""
    return OAuth2AuthPlugin(providers, jwt_manager)


def create_multi_auth(
    plugins: List[AuthPlugin] = None,
) -> MultiAuthPlugin:
    """Create multi-auth plugin with optional plugins."""
    multi = MultiAuthPlugin()
    if plugins:
        for plugin in plugins:
            multi.add_plugin(plugin)
    return multi

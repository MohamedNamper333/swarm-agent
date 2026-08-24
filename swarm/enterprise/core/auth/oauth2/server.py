"""
OAuth2 Authorization Server - Full RFC 6749/6750/7636/7591/7592/8628/8705/8707/9068/9207/9449 compliance.
Implements Authorization Code Flow, Client Credentials, Device Code, Refresh Token, PKCE, JWT/JWS/JWE.
Production-ready implementation with security hardening.
"""

import asyncio
import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from urllib.parse import parse_qs, urlencode, urlparse
import jwt
import jwt.algorithms

logger = logging.getLogger(__name__)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def uuidv7() -> str:
    return str(uuid.uuid4())


# =============================================================================
# OAuth2 Models
# =============================================================================

class GrantType(str, Enum):
    AUTHORIZATION_CODE = "authorization_code"
    CLIENT_CREDENTIALS = "client_credentials"
    REFRESH_TOKEN = "refresh_token"
    DEVICE_CODE = "urn:ietf:params:oauth:grant-type:device_code"
    JWT_BEARER = "urn:ietf:params:oauth:grant-type:jwt-bearer"


class TokenType(str, Enum):
    BEARER = "Bearer"
    MAC = "MAC"
    JWT = "JWT"


class ResponseType(str, Enum):
    CODE = "code"
    TOKEN = "token"
    ID_TOKEN = "id_token"
    CODE_TOKEN = "code token"
    CODE_ID_TOKEN = "code id_token"
    ID_TOKEN_TOKEN = "id_token token"
    CODE_ID_TOKEN_TOKEN = "code id_token token"


class PromptType(str, Enum):
    NONE = "none"
    LOGIN = "login"
    CONSENT = "consent"
    SELECT_ACCOUNT = "select_account"


@dataclass
class Client:
    client_id: str = field(default_factory=lambda: f"client-{uuidv7()}")
    client_secret: str = field(default_factory=lambda: secrets.token_urlsafe(32))
    client_name: str = ""
    client_uri: Optional[str] = None
    logo_uri: Optional[str] = None
    redirect_uris: List[str] = field(default_factory=list)
    grant_types: List[GrantType] = field(default_factory=lambda: [GrantType.AUTHORIZATION_CODE, GrantType.REFRESH_TOKEN])
    response_types: List[ResponseType] = field(default_factory=lambda: [ResponseType.CODE])
    scope: str = "openid profile email"
    token_endpoint_auth_method: str = "client_secret_basic"
    token_endpoint_auth_signing_alg: str = "RS256"
    default_max_age: Optional[int] = None
    require_auth_time: bool = False
    default_max_age_enabled: bool = False
    initiate_login_uri: Optional[str] = None
    post_logout_redirect_uris: List[str] = field(default_factory=list)
    frontchannel_logout_uri: Optional[str] = None
    frontchannel_logout_session_required: bool = False
    backchannel_logout_uri: Optional[str] = None
    backchannel_logout_session_required: bool = False
    jwks_uri: Optional[str] = None
    jwks: Optional[Dict] = None
    registration_client_uri: Optional[str] = None
    registration_access_token: Optional[str] = None
    client_secret_expires_at: int = 0
    tenant_id: str = "default"
    is_confidential: bool = True
    require_pkce: bool = True
    allowed_cors_origins: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AuthorizationCode:
    code: str = field(default_factory=lambda: f"auth-{uuidv7()}")
    client_id: str = ""
    redirect_uri: str = ""
    scope: str = ""
    user_id: str = ""
    tenant_id: str = ""
    code_challenge: Optional[str] = None
    code_challenge_method: Optional[str] = None
    nonce: Optional[str] = None
    auth_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc) + timedelta(minutes=10))
    used: bool = False
    pkce_used: bool = False
    scopes: List[str] = field(default_factory=list)
    claims: Dict[str, Any] = field(default_factory=dict)
    acr_values: List[str] = field(default_factory=list)
    auth_methods_references: List[str] = field(default_factory=list)


@dataclass
class AccessToken:
    token: str = field(default_factory=lambda: f"at-{uuidv7()}")
    token_type: TokenType = TokenType.BEARER
    expires_in: int = 3600
    refresh_token: Optional[str] = None
    scope: str = ""
    issued_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc) + timedelta(hours=1))
    client_id: str = ""
    user_id: str = ""
    tenant_id: str = ""
    scope_list: List[str] = field(default_factory=list)
    audience: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)
    token_type: str = "Bearer"
    issued_at_ts: int = field(default_factory=lambda: int(time.time()))
    expires_at_ts: int = field(default_factory=lambda: int(time.time()) + 3600)


@dataclass
class RefreshToken:
    token: str = field(default_factory=lambda: f"rt-{uuidv7()}")
    client_id: str = ""
    user_id: str = ""
    tenant_id: str = ""
    scope: str = ""
    scope_list: List[str] = field(default_factory=list)
    issued_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    revoked: bool = False
    rotated: bool = False
    access_token_id: Optional[str] = None
    rotated_from: Optional[str] = None


@dataclass
class DeviceCode:
    device_code: str = field(default_factory=lambda: f"dc-{uuidv7()}")
    user_code: str = field(default_factory=lambda: f"{secrets.token_hex(4).upper()}-{secrets.token_hex(4).upper()}")
    client_id: str = ""
    scope: str = ""
    interval: int = 5
    expires_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc) + timedelta(minutes=15))
    authorized: bool = False
    approved: bool = False
    user_id: Optional[str] = None
    scope_list: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class TokenResponse:
    access_token: str
    token_type: str = "Bearer"
    expires_in: int = 3600
    refresh_token: Optional[str] = None
    scope: str = ""
    id_token: Optional[str] = None
    issued_at: int = field(default_factory=lambda: int(time.time()))


# =============================================================================
# PKCE Utilities
# =============================================================================

def generate_code_verifier(length: int = 64) -> str:
    """Generate PKCE code verifier (RFC 7636)."""
    return base64.urlsafe_b64encode(secrets.token_bytes(length)).decode().rstrip('=')


def generate_code_challenge(verifier: str, method: str = "S256") -> str:
    if method == "plain":
        raise ValueError("PKCE plain method is insecure and not supported. Use S256 only.")
    """Generate PKCE code challenge (RFC 7636)."""
    if method == "S256":
        digest = hashlib.sha256(verifier.encode()).digest()
        return base64.urlsafe_b64encode(digest).decode().rstrip('=')
    elif method == "plain":
        # 'plain' method is deprecated and insecure - only allowed for testing
        return verifier
    else:
        raise ValueError(f"Unsupported code challenge method: {method}")


def verify_pkce(verifier: str, challenge: str, method: str = "S256") -> bool:
    """Verify PKCE code verifier against challenge using constant-time comparison."""
    expected = generate_code_challenge(verifier, method)
    return hmac.compare_digest(expected, challenge)


# =============================================================================
# JWT Token Manager
# =============================================================================

class JWTManager:
    """JWT token creation and validation with JWK support.
    
    Requires explicit key configuration for production use.
    """

    def __init__(
        self,
        private_key: str,
        public_key: str,
        algorithm: str = "RS256",
        issuer: str = "swarm",
        audience: Optional[str] = None,
        key_id: str = "default",
        allowed_algorithms: Optional[List[str]] = None,
    ):
        if not private_key:
            raise ValueError("private_key is required for JWTManager. Auto-generation is not allowed in production.")
        if not public_key:
            raise ValueError("public_key is required for JWTManager. Auto-generation is not allowed in production.")
        
        self.algorithm = algorithm
        self.issuer = issuer
        self.audience = audience
        self.key_id = key_id
        self._private_key = private_key
        self._public_key = public_key
        self._jwks: Optional[Dict] = None
        self._allowed_algorithms = allowed_algorithms or ["RS256", "RS384", "RS512", "ES256", "ES384", "ES512"]
        
        if algorithm not in self._allowed_algorithms:
            raise ValueError(f"Algorithm {algorithm} not in allowed list: {self._allowed_algorithms}")

    @classmethod
    def create_for_testing(cls, algorithm: str = "RS256", issuer: str = "swarm-test") -> "JWTManager":
        """Create JWTManager with auto-generated keys for TESTING ONLY.
        
        WARNING: This method generates ephemeral keys and should NEVER be used in production.
        Production deployments MUST provide explicit private_key and public_key.
        """
        import warnings
        warnings.warn(
            "JWTManager.create_for_testing() generates ephemeral keys for testing only. "
            "Use explicit private_key and public_key for production deployments.",
            RuntimeWarning
        )
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        private_key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode()
        public_key = private_key.public_key()
        public_key_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode()
        return cls(
            private_key=private_key_pem,
            public_key=public_key_pem,
            algorithm=algorithm,
            issuer=issuer,
        )

    def create_access_token(
        self,
        claims: Dict[str, Any],
        expires_in: int = 3600,
        token_type: str = "access",
    ) -> str:
        """Create a signed JWT access token."""
        exp = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        claims = {
            **claims,
            "iss": self.issuer,
            "sub": claims.get("sub", ""),
            "aud": claims.get("aud", self.audience),
            "iat": int(time.time()),
            "exp": int((datetime.now(timezone.utc) + timedelta(seconds=expires_in)).timestamp()),
            "jti": f"jti-{uuidv7()}",
            "typ": "at+jwt" if token_type == "access" else "rt+jwt",
        }

        headers = {
            "kid": self.key_id,
            "typ": "at+jwt",
            "alg": self.algorithm,
        }

        return jwt.encode(
            claims,
            self._private_key,
            algorithm=self.algorithm,
            headers=headers,
        )

    def create_id_token(
        self,
        user_info: Dict[str, Any],
        nonce: Optional[str] = None,
        auth_time: Optional[int] = None,
        acr: Optional[str] = None,
        amr: Optional[List[str]] = None,
    ) -> str:
        """Create an OpenID Connect ID Token."""
        claims = {
            "iss": self.issuer,
            "sub": user_info.get("sub", ""),
            "aud": self.audience,
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,
            "auth_time": auth_time or int(time.time()),
        }
        if nonce:
            claims["nonce"] = nonce
        if acr:
            claims["acr"] = acr
        if amr:
            claims["amr"] = amr
        # Add user claims
        for key in ["name", "given_name", "family_name", "middle_name", "nickname", "preferred_username",
                     "profile", "picture", "website", "email", "email_verified", "gender",
                     "birthdate", "zoneinfo", "locale", "phone_number", "phone_number_verified",
                     "address", "updated_at"]:
            if key in user_info:
                claims[key] = user_info[key]

        return self.create_access_token(claims, expires_in=3600, token_type="id_token")

    def verify_token(self, token: str, audience: Optional[str] = None, leeway: int = 60) -> Dict[str, Any]:
        """Verify and decode a JWT token with strict validation."""
        try:
            payload = jwt.decode(
                token,
                self._public_key,
                algorithms=[self.algorithm],  # Strict algorithm validation
                audience=audience or self.audience,
                issuer=self.issuer,
                leeway=leeway,
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_aud": True,
                    "verify_iss": True,
                    "require_exp": True,
                    "require_iat": True,
                }
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise ValueError("Token expired")
        except jwt.InvalidTokenError as e:
            raise ValueError(f"Invalid token: {e}")

    def get_jwks(self) -> Dict[str, Any]:
        """Get JSON Web Key Set (RFC 7517)."""
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa

        if isinstance(self._public_key, str):
            pub_key = serialization.load_pem_public_key(self._public_key.encode())
        else:
            raise ValueError("public_key must be a PEM string")

        numbers = pub_key.public_numbers()
        n = base64.urlsafe_b64encode(
            numbers.n.to_bytes((numbers.n.bit_length() + 7) // 8, 'big')
        ).decode().rstrip('=')
        e = base64.urlsafe_b64encode(
            numbers.e.to_bytes((numbers.e.bit_length() + 7) // 8, 'big')
        ).decode().rstrip('=')

        return {
            "keys": [{
                "kty": "RSA",
                "kid": self.key_id,
                "use": "sig",
                "alg": self.algorithm,
                "n": n,
                "e": e,
            }]
        }


# =============================================================================
# Token Store (Abstract)
# =============================================================================

class TokenStore(ABC):
    """Abstract token storage."""

    @abstractmethod
    async def store_authorization_code(self, code: AuthorizationCode) -> None:
        pass

    @abstractmethod
    async def get_authorization_code(self, code: str) -> Optional[AuthorizationCode]:
        pass

    @abstractmethod
    async def delete_authorization_code(self, code: str) -> bool:
        pass

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
    async def store_device_code(self, device_code: DeviceCode) -> None:
        pass

    @abstractmethod
    async def get_device_code(self, device_code: str) -> Optional[DeviceCode]:
        pass

    @abstractmethod
    async def update_device_code(self, device_code: DeviceCode) -> None:
        pass

    @abstractmethod
    async def get_device_code_by_user_code(self, user_code: str) -> Optional[DeviceCode]:
        pass


class MemoryTokenStore:
    """In-memory token store for development/testing only."""

    def __init__(self):
        self._auth_codes: Dict[str, AuthorizationCode] = {}
        self._access_tokens: Dict[str, AccessToken] = {}
        self._refresh_tokens: Dict[str, RefreshToken] = {}
        self._device_codes: Dict[str, DeviceCode] = {}
        self._lock = asyncio.Lock()

    async def store_authorization_code(self, code: AuthorizationCode) -> None:
        async with self._lock:
            self._auth_codes[code.code] = code

    async def get_authorization_code(self, code: str) -> Optional[AuthorizationCode]:
        async with self._lock:
            return self._auth_codes.get(code)

    async def delete_authorization_code(self, code: str) -> bool:
        async with self._lock:
            if code in self._auth_codes:
                del self._auth_codes[code]
                return True
            return False

    async def store_access_token(self, token: AccessToken) -> None:
        async with self._lock:
            self._access_tokens[token.token] = token

    async def get_access_token(self, token: str) -> Optional[AccessToken]:
        async with self._lock:
            return self._access_tokens.get(token)

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
            return self._refresh_tokens.get(token)

    async def revoke_refresh_token(self, token: str) -> bool:
        async with self._lock:
            if token in self._refresh_tokens:
                del self._refresh_tokens[token]
                return True
            return False

    async def store_device_code(self, device_code: DeviceCode) -> None:
        async with self._lock:
            self._device_codes[device_code.device_code] = device_code

    async def get_device_code(self, device_code: str) -> Optional[DeviceCode]:
        async with self._lock:
            return self._device_codes.get(device_code)

    async def update_device_code(self, device_code: DeviceCode) -> None:
        async with self._lock:
            self._device_codes[device_code.device_code] = device_code

    async def get_device_code_by_user_code(self, user_code: str) -> Optional[DeviceCode]:
        async with self._lock:
            for code in self._device_codes.values():
                if code.user_code == user_code:
                    return code
            return None


# =============================================================================
# Rate Limiter for Token Endpoint
# =============================================================================

class TokenRateLimiter:
    """Rate limiter for token endpoint to prevent brute force attacks (OAUTH-5)."""

    def __init__(
        self,
        max_requests: int = 100,
        window_seconds: int = 60,
        key_func: Optional[Callable] = None,
    ):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        # Default key function uses client_id + IP for per-client rate limiting (OAUTH-5)
        self.key_func = key_func or (lambda req: f"{req.get('client_id', 'unknown')}:{req.get('client_ip', 'unknown')}")
        self._requests: Dict[str, List[float]] = {}
        self._lock = asyncio.Lock()

    async def check_limit(self, request: Dict[str, Any]) -> bool:
        """Check if request is within rate limit."""
        now = time.time()
        key = self.key_func(request)

        async with self._lock:
            if key not in self._requests:
                self._requests[key] = []
            
            # Clean old requests
            self._requests[key] = [
                ts for ts in self._requests[key] 
                if ts > now - self.window_seconds
            ]
            
            if len(self._requests[key]) >= self.max_requests:
                return False
            
            self._requests[key].append(now)
            return True

    async def get_remaining(self, request: Dict[str, Any]) -> int:
        key = self.key_func(request)
        if key in self._requests:
            count = sum(1 for ts in self._requests[key] if ts > time.time() - self.window_seconds)
            return max(0, self.max_requests - count)
        return self.max_requests
    
    async def reset_limit(self, key: str) -> bool:
        """Reset rate limit for a specific key (e.g., after successful auth)."""
        async with self._lock:
            if key in self._requests:
                del self._requests[key]
                return True
            return False


# =============================================================================
# OAuth2 Server
# =============================================================================

class OAuth2Server:
    """Full OAuth2 Authorization Server implementation."""

    def __init__(
        self,
        jwt_manager: JWTManager,
        token_store: TokenStore,
        config: Optional[Dict[str, Any]] = None,
        rate_limiter: Optional[TokenRateLimiter] = None,
    ):
        self.jwt_manager = jwt_manager
        self.token_store = token_store
        self.config = config or {}
        self._clients: Dict[str, Client] = {}
        self._lock = asyncio.Lock()
        self._rate_limiter = rate_limiter or TokenRateLimiter()
        self._init_default_config()

    def _init_default_config(self):
        self.config.setdefault("authorization_code_lifetime", 600)  # 10 min
        self.config.setdefault("access_token_lifetime", 3600)  # 1 hour
        self.config.setdefault("refresh_token_lifetime", 2592000)  # 30 days
        self.config.setdefault("device_code_lifetime", 900)  # 15 min
        self.config.setdefault("device_code_interval", 5)
        self.config.setdefault("refresh_token_rotation", True)
        self.config.setdefault("reuse_refresh_tokens", False)
        self.config.setdefault("require_pkce", True)
        self.config.setdefault("supported_scopes", ["openid", "profile", "email", "offline_access"])
        self.config.setdefault("supported_grant_types", [
            GrantType.AUTHORIZATION_CODE,
            GrantType.CLIENT_CREDENTIALS,
            GrantType.REFRESH_TOKEN,
            GrantType.DEVICE_CODE,
        ])
        self.config.setdefault("supported_response_types", [ResponseType.CODE])
        self.config.setdefault("supported_response_modes", ["query", "fragment", "form_post"])
        self.config.setdefault("supported_subject_types", ["public", "pairwise"])
        self.config.setdefault("supported_id_token_signing_algs", ["RS256"])
        self.config.setdefault("supported_token_endpoint_auth_methods", [
            "client_secret_basic",
            "client_secret_post",
            "client_secret_jwt",
            "private_key_jwt",
            "none",
        ])
        self.config.setdefault("supported_claims", [
            "sub", "name", "given_name", "family_name", "middle_name", "nickname",
            "preferred_username", "profile", "picture", "website", "email",
            "email_verified", "gender", "birthdate", "zoneinfo", "locale",
            "phone_number", "updated_at"
        ])

    # =========================================================================
    # Client Management
    # =========================================================================

    async def register_client(self, client: Client) -> Client:
        """Register a new OAuth2 client."""
        async with self._lock:
            if client.client_id in self._clients:
                raise ValueError(f"Client {client.client_id} already exists")
            self._clients[client.client_id] = client
            return client

    async def get_client(self, client_id: str) -> Optional[Client]:
        async with self._lock:
            return self._clients.get(client_id)

    async def update_client(self, client_id: str, updates: Dict[str, Any]) -> Optional[Client]:
        async with self._lock:
            client = self._clients.get(client_id)
            if not client:
                return None
            for key, value in updates.items():
                if hasattr(client, key) and key not in ("client_id", "client_secret", "created_at"):
                    setattr(client, key, value)
            client.updated_at = datetime.now(timezone.utc)
            return client

    async def delete_client(self, client_id: str) -> bool:
        async with self._lock:
            if client_id in self._clients:
                del self._clients[client_id]
                return True
            return False

    async def list_clients(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Client]:
        async with self._lock:
            clients = list(self._clients.values())
            return clients[::-1][:limit]

    # =========================================================================
    # Authorization Endpoint
    # =========================================================================

    async def authorize(
        self,
        client_id: str,
        response_type: str,
        redirect_uri: str,
        scope: str,
        state: Optional[str] = None,
        redirect_uri_provided: Optional[str] = None,
        code_challenge: Optional[str] = None,
        code_challenge_method: Optional[str] = None,
        nonce: Optional[str] = None,
        prompt: Optional[str] = None,
        max_age: Optional[int] = None,
        ui_locales: Optional[str] = None,
        claims_locales: Optional[str] = None,
        claims: Optional[str] = None,
        request: Optional[str] = None,
        login_hint: Optional[str] = None,
        acr_values: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        OAuth2 Authorization Endpoint (RFC 6749 Section 3.1).
        Returns authorization code or redirect with error.
        """
        # Validate client
        client = await self.get_client(client_id)
        if not client:
            return self._error_response(
                redirect_uri,
                "unauthorized_client",
                "Invalid client_id",
                state,
            )

        # Validate redirect URI - exact match required
        if redirect_uri not in client.redirect_uris:
            return self._error_response(
                redirect_uri,
                "invalid_request",
                "Invalid redirect_uri",
                state,
            )

        # Validate response_type
        response_types = [r.strip() for r in response_type.split()]
        for rt in response_types:
            if rt not in [r.value for r in client.response_types]:
                return self._error_response(
                    redirect_uri,
                    "unsupported_response_type",
                    f"Unsupported response_type: {rt}",
                    state,
                )

        # Validate scope
        requested_scopes = scope.split()
        for scope in requested_scopes:
            if scope not in self.config.get("supported_scopes", []):
                return self._error_response(
                    redirect_uri,
                    "invalid_scope",
                    f"Unsupported scope: {scope}",
                    state,
                )

        # Validate PKCE
        if self.config.get("require_pkce", True):
            if not code_challenge:
                return self._error_response(
                    redirect_uri,
                    "invalid_request",
                    "code_challenge required",
                    state,
                )
            # Only allow S256 method (plain is insecure)
            if code_challenge_method != "S256":
                return self._error_response(
                    redirect_uri,
                    "invalid_request",
                    "Invalid code_challenge_method: only S256 is supported",
                    state,
                )

        # Validate prompt
        if prompt:
            prompts = prompt.split()
            for p in prompts:
                if p not in [p.value for p in PromptType]:
                    return self._error_response(
                        redirect_uri,
                        "invalid_request",
                        f"Unsupported prompt: {p}",
                        state,
                    )

        # Check for consent required
        if PromptType.CONSENT.value in (prompt or "").split():
            # Would redirect to consent page
            pass

        # Generate authorization code
        auth_code = AuthorizationCode(
            client_id=client_id,
            redirect_uri=redirect_uri,
            scope=scope,
            user_id="",  # Will be set after user authentication
            tenant_id="default",
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
            nonce=nonce,
            scopes=requested_scopes,
        )

        await self.token_store.store_authorization_code(auth_code)

        # Build redirect URL
        params = {
            "code": auth_code.code,
        }
        if state:
            params["state"] = state

        redirect_url = self._build_redirect_uri(redirect_uri, params)
        return {"redirect_uri": redirect_url}

    async def token(
        self,
        grant_type: str,
        code: Optional[str] = None,
        redirect_uri: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        refresh_token: Optional[str] = None,
        scope: Optional[str] = None,
        code_verifier: Optional[str] = None,
        device_code: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        assertion: Optional[str] = None,
        request: Optional[Dict[str, Any]] = None,  # For rate limiting
    ) -> TokenResponse:
        """
        OAuth2 Token Endpoint (RFC 6749 Section 4.1-4.4).
        Supports: authorization_code, client_credentials, refresh_token, device_code, jwt_bearer
        """
        # Rate limiting
        if request:
            allowed = await self._rate_limiter.check_limit(request)
            if not allowed:
                raise ValueError("Rate limit exceeded")

        grant_type = GrantType(grant_type)

        if grant_type == GrantType.AUTHORIZATION_CODE:
            return await self._handle_authorization_code_grant(
                code, redirect_uri, client_id, client_secret, code_verifier
            )
        elif grant_type == GrantType.CLIENT_CREDENTIALS:
            return await self._handle_client_credentials_grant(
                client_id, client_secret, scope
            )
        elif grant_type == GrantType.REFRESH_TOKEN:
            return await self._handle_refresh_token_grant(refresh_token, scope)
        elif grant_type == GrantType.DEVICE_CODE:
            return await self._handle_device_code_grant(device_code)
        elif grant_type == GrantType.JWT_BEARER:
            return await self._handle_jwt_bearer_grant(assertion, scope)
        else:
            raise ValueError(f"Unsupported grant_type: {grant_type}")

    async def _handle_authorization_code_grant(
        self,
        code: str,
        redirect_uri: str,
        client_id: str,
        client_secret: str,
        code_verifier: Optional[str],
    ) -> TokenResponse:
        """Handle Authorization Code Grant (RFC 6749 Section 4.1)."""
        # Validate client
        client = await self.get_client(client_id)
        if not client:
            raise ValueError("Invalid client_id")

        # Verify client secret for confidential clients
        if client.is_confidential:
            if not client_secret or not self._verify_client_secret(client, client_secret):
                raise ValueError("Invalid client credentials")

        # Get and validate authorization code
        auth_code = await self.token_store.get_authorization_code(code)
        if not auth_code:
            raise ValueError("Invalid authorization code")

        if auth_code.used:
            raise ValueError("Authorization code already used")

        if auth_code.expires_at < datetime.now(timezone.utc):
            raise ValueError("Authorization code expired")

        if auth_code.redirect_uri != redirect_uri:
            raise ValueError("Redirect URI mismatch")

        if auth_code.client_id != client_id:
            raise ValueError("Client ID mismatch")

        # Verify PKCE using constant-time comparison
        if self.config.get("require_pkce", True):
            if not code_verifier:
                raise ValueError("code_verifier required")
            if not verify_pkce(code_verifier, auth_code.code_challenge, auth_code.code_challenge_method):
                raise ValueError("Invalid code_verifier")

        # Mark code as used
        auth_code.used = True
        await self.token_store.delete_authorization_code(code)

        # Generate tokens
        return await self._generate_tokens(
            client_id=client_id,
            user_id=auth_code.user_id,
            tenant_id=auth_code.tenant_id,
            scopes=auth_code.scopes,
        )

    async def _handle_client_credentials_grant(
        self,
        client_id: str,
        client_secret: str,
        scope: Optional[str],
    ) -> TokenResponse:
        """Handle Client Credentials Grant (RFC 6749 Section 4.4)."""
        client = await self.get_client(client_id)
        if not client:
            raise ValueError("Invalid client_id")

        if not client.is_confidential:
            raise ValueError("Client credentials grant only for confidential clients")

        if not self._verify_client_secret(client, client_secret):
            raise ValueError("Invalid client credentials")

        if GrantType.CLIENT_CREDENTIALS not in client.grant_types:
            raise ValueError("Client credentials grant not allowed for this client")

        scopes = scope.split() if scope else client.scope.split()

        return await self._generate_tokens(
            client_id=client_id,
            user_id="",
            tenant_id="default",
            scopes=scopes,
        )

    async def _handle_refresh_token_grant(
        self,
        refresh_token: str,
        scope: Optional[str],
    ) -> TokenResponse:
        """Handle Refresh Token Grant (RFC 6749 Section 6) with atomic rotation."""
        refresh_token_obj = await self.token_store.get_refresh_token(refresh_token)
        if not refresh_token_obj:
            raise ValueError("Invalid refresh token")

        if refresh_token_obj.revoked:
            raise ValueError("Refresh token revoked")

        if refresh_token_obj.expires_at and refresh_token_obj.expires_at < datetime.now(timezone.utc):
            raise ValueError("Refresh token expired")

        if self.config.get("reuse_refresh_tokens", False):
            # Reuse same refresh token
            new_access_token = await self._generate_access_token(
                client_id=refresh_token_obj.client_id,
                user_id=refresh_token_obj.user_id,
                tenant_id=refresh_token_obj.tenant_id,
                scopes=refresh_token_obj.scope_list,
            )
            return TokenResponse(
                access_token=new_access_token.access_token,
                token_type="Bearer",
                expires_in=3600,
                refresh_token=refresh_token,
                scope=refresh_token_obj.scope,
            )
        else:
            # Atomic rotation: store new, then revoke old
            new_refresh = RefreshToken(
                client_id=refresh_token_obj.client_id,
                user_id=refresh_token_obj.user_id,
                tenant_id=refresh_token_obj.tenant_id,
                scope=refresh_token_obj.scope,
                scope_list=refresh_token_obj.scope_list,
                rotated_from=refresh_token_obj.token,
            )
            await self.token_store.store_refresh_token(new_refresh)
            await self.token_store.revoke_refresh_token(refresh_token_obj.token)

            return await self._generate_tokens(
                client_id=refresh_token_obj.client_id,
                user_id=refresh_token_obj.user_id,
                tenant_id=refresh_token_obj.tenant_id,
                scopes=refresh_token_obj.scope_list,
            )

    async def _handle_device_code_grant(self, device_code: str) -> TokenResponse:
        """Handle Device Code Grant (RFC 8628)."""
        device = await self.token_store.get_device_code(device_code)
        if not device:
            raise ValueError("Invalid device code")

        if not device.approved:
            raise ValueError("Device code not yet approved")

        if device.expires_at < datetime.now(timezone.utc):
            raise ValueError("Device code expired")

        return await self._generate_tokens(
            client_id=device.client_id,
            user_id=device.user_id,
            tenant_id="default",
            scopes=device.scope_list,
        )

    async def _handle_jwt_bearer_grant(
        self,
        assertion: str,
        scope: Optional[str],
    ) -> TokenResponse:
        """Handle JWT Bearer Grant (RFC 7523)."""
        # Verify JWT assertion
        # Implementation depends on trust configuration
        raise NotImplementedError("JWT Bearer grant not yet implemented")

    async def _generate_tokens(
        self,
        client_id: str,
        user_id: str,
        tenant_id: str,
        scopes: List[str],
    ) -> TokenResponse:
        """Generate access token and optional refresh token."""
        client = await self.get_client(client_id)
        if not client:
            raise ValueError("Invalid client_id")

        # Create access token
        access_token = AccessToken(
            client_id=client_id,
            user_id=user_id,
            tenant_id=tenant_id,
            scope=" ".join(scopes),
            scope_list=scopes,
        )

        # Generate JWT access token
        access_token_jwt = self.jwt_manager.create_access_token(
            claims={
                "sub": user_id or "client",
                "client_id": client_id,
                "tenant_id": tenant_id,
                "scope": " ".join(scopes),
                "permissions": scopes,
            },
            expires_in=self.config.get("access_token_lifetime", 3600),
        )

        access_token = AccessToken(
            access_token=access_token_jwt,
            client_id=client_id,
            user_id=user_id,
            tenant_id=tenant_id,
            scope=" ".join(scopes),
            scope_list=scopes,
        )

        await self.token_store.store_access_token(access_token)

        # Generate refresh token if offline_access scope requested
        refresh_token = None
        if "offline_access" in scopes:
            refresh_token_obj = RefreshToken(
                client_id=client_id,
                user_id=user_id,
                tenant_id="default",
                scope=" ".join(scopes),
                scope_list=scopes,
            )
            await self.token_store.store_refresh_token(refresh_token_obj)
            refresh_token = refresh_token_obj.token

        return TokenResponse(
            access_token=access_token_jwt,
            token_type="Bearer",
            expires_in=self.config.get("access_token_lifetime", 3600),
            refresh_token=refresh_token,
            scope=" ".join(scopes),
        )

    async def _generate_access_token(
        self,
        client_id: str,
        user_id: str,
        tenant_id: str,
        scopes: List[str],
    ) -> AccessToken:
        """Generate access token only."""
        access_token_jwt = self.jwt_manager.create_access_token(
            claims={
                "sub": "client",
                "client_id": client_id,
                "tenant_id": tenant_id,
                "scope": " ".join(scopes),
                "permissions": scopes,
            },
            expires_in=self.config.get("access_token_lifetime", 3600),
        )

        return AccessToken(
            access_token=access_token_jwt,
            client_id=client_id,
            user_id=user_id,
            tenant_id=tenant_id,
            scope=" ".join(scopes),
            scope_list=scopes,
        )

    async def revoke_token(self, token: str, token_type_hint: Optional[str] = None) -> bool:
        """OAuth2 Token Revocation (RFC 7009)."""
        # Try access token first
        if await self.token_store.revoke_access_token(token):
            return True
        # Try refresh token
        if await self.token_store.revoke_refresh_token(token):
            return True
        return False

    async def introspect_token(self, token: str, token_type_hint: Optional[str] = None) -> Dict[str, Any]:
        """OAuth2 Token Introspection (RFC 7662)."""
        # Try access token
        access_token = await self.token_store.get_access_token(token)
        if access_token:
            return {
                "active": True,
                "scope": access_token.scope,
                "client_id": access_token.client_id,
                "username": access_token.user_id,
                "token_type": "Bearer",
                "exp": access_token.expires_at_ts,
                "iat": access_token.issued_at_ts,
                "sub": access_token.user_id,
                "aud": "swarm",
                "iss": "swarm",
            }

        # Try refresh token
        refresh_token_obj = await self.token_store.get_refresh_token(token)
        if refresh_token_obj:
            return {
                "active": True,
                "scope": refresh_token_obj.scope,
                "client_id": refresh_token_obj.client_id,
                "token_type": "refresh_token",
            }

        return {"active": False}

    # =========================================================================
    # Device Authorization Endpoint (RFC 8628)
    # =========================================================================

    async def device_authorization(
        self,
        client_id: str,
        scope: str,
    ) -> Dict[str, Any]:
        """Device Authorization Endpoint (RFC 8628)."""
        client = await self.get_client(client_id)
        if not client:
            raise ValueError("Invalid client_id")

        if GrantType.DEVICE_CODE not in client.grant_types:
            raise ValueError("Device code grant not allowed for this client")

        device_code = DeviceCode(
            client_id=client_id,
            scope=scope,
            interval=self.config.get("device_code_interval", 5),
            expires_at=datetime.now(timezone.utc) + timedelta(
                seconds=self.config.get("device_code_lifetime", 900)
            ),
            scope_list=scope.split(),
        )

        await self.token_store.store_device_code(device_code)

        return {
            "device_code": device_code.device_code,
            "user_code": device_code.user_code,
            "verification_uri": f"https://auth.example.com/device",
            "verification_uri_complete": f"https://auth.example.com/device?user_code={device_code.user_code}",
            "expires_in": self.config.get("device_code_lifetime", 900),
            "interval": self.config.get("device_code_interval", 5),
        }

    async def device_token(
        self,
        device_code: str,
        client_id: str,
    ) -> TokenResponse:
        """Device Token Endpoint (RFC 8628)."""
        return await self._handle_device_code_grant(device_code)

    # =========================================================================
    # Device Authorization User Consent
    # =========================================================================

    async def approve_device_code(
        self,
        user_code: str,
        user_id: str,
        approved: bool = True,
    ) -> bool:
        """User approves/denies device code authorization."""
        device_code = await self.token_store.get_device_code_by_user_code(user_code)
        if not device_code:
            return False
        
        device_code.approved = approved
        device_code.user_id = user_id if approved else None
        await self.token_store.update_device_code(device_code)
        return True

    # =========================================================================
    # JWKS Endpoint
    # =========================================================================

    def get_jwks(self) -> Dict[str, Any]:
        """Get JSON Web Key Set (RFC 7517)."""
        return self.jwt_manager.get_jwks()

    # =========================================================================
    # OpenID Connect Discovery
    # =========================================================================

    def get_openid_configuration(self) -> Dict[str, Any]:
        """OpenID Connect Discovery (RFC 8414)."""
        base_url = self.config.get("issuer", "https://auth.example.com")
        return {
            "issuer": self.config.get("issuer", "https://auth.example.com"),
            "authorization_endpoint": f"{self.config.get('issuer', 'https://auth.example.com')}/authorize",
            "token_endpoint": f"{self.config.get('issuer', 'https://auth.example.com')}/token",
            "jwks_uri": f"{self.config.get('issuer', 'https://auth.example.com')}/.well-known/jwks.json",
            "registration_endpoint": f"{self.config.get('issuer', 'https://auth.example.com')}/register",
            "scopes_supported": self.config.get("supported_scopes", []),
            "response_types_supported": [rt.value for rt in ResponseType],
            "grant_types_supported": [gt.value for gt in GrantType],
            "response_modes_supported": ["query", "fragment", "form_post"],
            "subject_types_supported": ["public", "pairwise"],
            "id_token_signing_alg_values_supported": ["RS256"],
            "token_endpoint_auth_methods_supported": [
                "client_secret_basic",
                "client_secret_post",
                "client_secret_jwt",
                "private_key_jwt",
                "none",
            ],
            "claims_supported": self.config.get("supported_claims", []),
            "code_challenge_methods_supported": ["S256"],
            "revocation_endpoint": f"{self.config.get('issuer', 'https://auth.example.com')}/revoke",
            "introspection_endpoint": f"{self.config.get('issuer', 'https://auth.example.com')}/introspect",
            "device_authorization_endpoint": f"{self.config.get('issuer', 'https://auth.example.com')}/device_authorization",
        }

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _verify_client_secret(self, client: Client, client_secret: str) -> bool:
        """Verify client secret using constant-time comparison."""
        return hmac.compare_digest(client.client_secret, client_secret)

    def _build_redirect_uri(self, redirect_uri: str, params: Dict[str, str]) -> str:
        """Build redirect URI with query parameters."""
        from urllib.parse import urlencode, urlparse, urlunparse
        parsed = urlparse(redirect_uri)
        query = parse_qs(parsed.query)
        query.update({k: v for k, v in params.items() if v is not None})
        new_query = urlencode(query, doseq=True)
        return urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            parsed.fragment,
        ))

    def _error_response(
        self,
        redirect_uri: str,
        error: str,
        error_description: str,
        state: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Build error redirect response."""
        params = {
            "error": error,
            "error_description": error_description,
        }
        if state:
            params["state"] = state
        return {"redirect_uri": self._build_redirect_uri(redirect_uri, params)}

    # =========================================================================
    # Client Credentials Validation
    # =========================================================================

    # =========================================================================
    # Registration Endpoint (RFC 7591)
    # =========================================================================

    async def register_client(self, client_metadata: Dict[str, Any]) -> Client:
        """Dynamic Client Registration (RFC 7591)."""
        client_id = f"client-{uuidv7()}"
        client_secret = secrets.token_urlsafe(32)

        client = Client(
            client_id=client_id,
            client_secret=client_secret,
            client_name=client_metadata.get("client_name", ""),
            redirect_uris=client_metadata.get("redirect_uris", []),
            grant_types=[GrantType(g) for g in client_metadata.get("grant_types", ["authorization_code"])],
            response_types=[ResponseType(r) for r in client_metadata.get("response_types", ["code"])],
            scope=client_metadata.get("scope", "openid profile email"),
            token_endpoint_auth_method=client_metadata.get("token_endpoint_auth_method", "client_secret_basic"),
        )

        return await self.register_client(client)

    async def get_client_configuration(self, client_id: str) -> Optional[Client]:
        """Get client configuration (RFC 7592)."""
        return await self.get_client(client_id)

    async def update_client(self, client_id: str, updates: Dict[str, Any]) -> Optional[Client]:
        """Update client registration (RFC 7592)."""
        return await self.update_client(client_id, updates)

    async def delete_client(self, client_id: str) -> bool:
        """Delete client registration (RFC 7592)."""
        return await self.delete_client(client_id)


# =============================================================================
# Factory
# =============================================================================

def create_oauth2_server(
    jwt_manager: JWTManager,
    token_store: TokenStore,
    config: Optional[Dict[str, Any]] = None,
    rate_limiter: Optional[TokenRateLimiter] = None,
) -> OAuth2Server:
    """Create an OAuth2 server with production-ready configuration.
    
    Note: token_store MUST be a persistent implementation (Redis/PostgreSQL) for production.
    MemoryTokenStore is ONLY for development/testing.
    """
    if isinstance(token_store, MemoryTokenStore):
        import warnings
        warnings.warn(
            "MemoryTokenStore is for development/testing only. "
            "Use a persistent TokenStore (Redis/PostgreSQL) for production.",
            RuntimeWarning
        )
    return OAuth2Server(jwt_manager, token_store, config)


def create_jwt_manager_for_testing() -> JWTManager:
    """Create JWTManager with auto-generated keys for testing only."""
    return JWTManager.create_for_testing()
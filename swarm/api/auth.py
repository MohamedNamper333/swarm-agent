"""
Auth Module - API Key + JWT Authentication
Provides authentication and authorization for Swarm API.
"""
import hashlib
import hmac
import json
import secrets
import time
import logging
import asyncio
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field, asdict
from enum import Enum

import jwt
from fastapi import Request, HTTPException, Depends

logger = logging.getLogger(__name__)


class TokenType(str, Enum):
    """Token types"""
    API_KEY = "api_key"
    JWT_ACCESS = "jwt_access"
    JWT_REFRESH = "jwt_refresh"


class AuthScope(str, Enum):
    """Authorization scopes"""
    TASKS_READ = "tasks:read"
    TASKS_WRITE = "tasks:write"
    TASKS_ADMIN = "tasks:admin"
    MODELS_READ = "models:read"
    MODELS_WRITE = "models:write"
    AGENTS_READ = "agents:read"
    AGENTS_WRITE = "agents:write"
    CONFIG_READ = "config:read"
    CONFIG_WRITE = "config:write"
    ADMIN = "admin"


@dataclass
class APIKey:
    """API Key record"""
    id: str
    name: str
    key_hash: str
    scopes: List[str]
    created_at: str
    expires_at: Optional[str] = None
    last_used: Optional[str] = None
    is_active: bool = True
    usage_count: int = 0
    owner: str = "system"


@dataclass
class TokenPair:
    """Access and refresh token pair"""
    access_token: str
    refresh_token: str
    expires_in: int  # seconds
    token_type: str = "Bearer"


@dataclass
class AuthStats:
    """Authentication statistics"""
    total_api_keys: int = 0
    active_api_keys: int = 0
    total_tokens_issued: int = 0
    active_sessions: int = 0
    failed_attempts: int = 0


class AuthManager:
    """
    Manages API keys, JWT tokens, and authentication.
    """
    
    def __init__(
        self,
        secret_key: Optional[str] = None,
        storage_path: str = "swarm/api/auth",
        access_token_ttl: int = 3600,
        refresh_token_ttl: int = 604800,
        algorithm: str = "HS256"
    ):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.secret_key = secret_key or secrets.token_urlsafe(32)
        self.access_token_ttl = access_token_ttl
        self.refresh_token_ttl = refresh_token_ttl
        self.algorithm = algorithm
        
        self.api_keys: Dict[str, APIKey] = {}
        self.refresh_tokens: Dict[str, Dict] = {}  # token -> {user_id, scopes, expires_at}
        self.revoked_tokens: Set[str] = set()
        
        self.stats = AuthStats()
        
        self._load_state()
        
        # Create default admin key if none exist
        if not self.api_keys:
            self.create_api_key(
                name="admin",
                scopes=[s.value for s in AuthScope],
                owner="system"
            )
    
    def _load_state(self) -> None:
        """Load auth state from disk"""
        state_file = self.storage_path / "auth_state.json"
        if state_file.exists():
            try:
                with open(state_file, "r") as f:
                    data = json.load(f)
                for k_id, k_data in data.get("api_keys", {}).items():
                    self.api_keys[k_id] = APIKey(**k_data)
                for token, t_data in data.get("refresh_tokens", {}).items():
                    self.refresh_tokens[token] = t_data
                self.revoked_tokens = set(data.get("revoked_tokens", []))
                self.stats = AuthStats(**data.get("stats", {}))
            except Exception as e:
                logger.error(f"Failed to load auth state: {e}")
    
    def _save_state(self) -> None:
        """Save auth state to disk"""
        state_file = self.storage_path / "auth_state.json"
        try:
            data = {
                "api_keys": {k: asdict(v) for k, v in self.api_keys.items()},
                "refresh_tokens": self.refresh_tokens,
                "revoked_tokens": list(self.revoked_tokens),
                "stats": asdict(self.stats)
            }
            with open(state_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save auth state: {e}")
    
    # ========== API Key Management ==========
    
    def create_api_key(
        self,
        name: str,
        scopes: List[str],
        owner: str = "system",
        expires_in_days: Optional[int] = None
    ) -> tuple[str, APIKey]:
        """Create a new API key. Returns (raw_key, api_key_record)"""
        import uuid
        key_id = f"key-{uuid.uuid4().hex[:8]}"
        raw_key = f"sk-{secrets.token_urlsafe(32)}"
        key_hash = self._hash_key(raw_key)
        
        expires_at = None
        if expires_in_days:
            expires_at = (datetime.now() + timedelta(days=expires_in_days)).isoformat()
        
        api_key = APIKey(
            id=key_id,
            name=name,
            key_hash=key_hash,
            scopes=scopes,
            created_at=datetime.now().isoformat(),
            expires_at=expires_at,
            owner=owner
        )
        
        self.api_keys[key_id] = api_key
        self.stats.total_api_keys += 1
        self.stats.active_api_keys += 1
        self._save_state()
        
        logger.info(f"Created API key: {name} ({key_id}) with scopes: {scopes}")
        return raw_key, api_key
    
    def get_api_key(self, key_id: str) -> Optional[APIKey]:
        """Get API key by ID"""
        return self.api_keys.get(key_id)
    
    def list_api_keys(self) -> List[Dict]:
        """List all API keys (without hashes)"""
        return [
            {
                "id": k.id,
                "name": k.name,
                "scopes": k.scopes,
                "created_at": k.created_at,
                "expires_at": k.expires_at,
                "last_used": k.last_used,
                "is_active": k.is_active,
                "usage_count": k.usage_count,
                "owner": k.owner
            }
            for k in self.api_keys.values()
        ]
    
    def revoke_api_key(self, key_id: str) -> bool:
        """Revoke an API key"""
        if key_id not in self.api_keys:
            return False
        self.api_keys[key_id].is_active = False
        self.stats.active_api_keys -= 1
        self._save_state()
        return True
    
    def validate_api_key(self, raw_key: str) -> Optional[APIKey]:
        """Validate an API key and return the key record"""
        key_hash = self._hash_key(raw_key)
        for key in self.api_keys.values():
            if key.key_hash == key_hash:
                if not key.is_active:
                    return None
                if key.expires_at:
                    try:
                        if datetime.fromisoformat(key.expires_at) < datetime.now():
                            return None
                    except (ValueError, TypeError):
                        pass
                key.last_used = datetime.now().isoformat()
                key.usage_count += 1
                self._save_state()
                return key
        return None
    
    # ========== JWT Tokens ==========
    
    def create_token_pair(self, user_id: str, scopes: List[str]) -> TokenPair:
        """Create access and refresh token pair"""
        now = datetime.now(timezone.utc)
        access_expires = now + timedelta(seconds=self.access_token_ttl)
        refresh_expires = now + timedelta(seconds=self.refresh_token_ttl)
        
        access_payload = {
            "sub": user_id,
            "scopes": scopes,
            "type": TokenType.JWT_ACCESS.value,
            "iat": now.timestamp(),
            "exp": access_expires.timestamp()
        }
        refresh_payload = {
            "sub": user_id,
            "scopes": scopes,
            "type": TokenType.JWT_REFRESH.value,
            "iat": now.timestamp(),
            "exp": refresh_expires.timestamp()
        }
        
        access_token = jwt.encode(access_payload, self.secret_key, algorithm=self.algorithm)
        refresh_token = jwt.encode(refresh_payload, self.secret_key, algorithm=self.algorithm)
        
        # Store refresh token
        self.refresh_tokens[refresh_token] = {
            "user_id": user_id,
            "scopes": scopes,
            "expires_at": refresh_expires.isoformat(),
            "created_at": now.isoformat()
        }
        
        self.stats.total_tokens_issued += 1
        self.stats.active_sessions += 1
        self._save_state()
        
        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=self.access_token_ttl
        )
    
    def validate_access_token(self, token: str) -> Optional[Dict]:
        """Validate JWT access token"""
        if token in self.revoked_tokens:
            return None
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            if payload.get("type") != TokenType.JWT_ACCESS.value:
                return None
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    def refresh_access_token(self, refresh_token: str) -> Optional[TokenPair]:
        """Refresh access token using refresh token"""
        if refresh_token in self.revoked_tokens:
            return None
        if refresh_token not in self.refresh_tokens:
            return None
        
        token_data = self.refresh_tokens[refresh_token]
        try:
            expires_at = datetime.fromisoformat(token_data["expires_at"])
            now_utc = datetime.now(timezone.utc)
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if now_utc > expires_at:
                return None
        except (ValueError, TypeError):
            return None
        
        # Revoke old refresh token
        self.revoked_tokens.add(refresh_token)
        del self.refresh_tokens[refresh_token]
        
        # Create new token pair
        return self.create_token_pair(token_data["user_id"], token_data["scopes"])
    
    def revoke_token(self, token: str) -> bool:
        """Revoke a token (access or refresh)"""
        self.revoked_tokens.add(token)
        if token in self.refresh_tokens:
            del self.refresh_tokens[token]
            self.stats.active_sessions -= 1
        self._save_state()
        return True
    
    # ========== Scope Validation ==========
    
    def has_scope(self, token_payload: Dict, required_scope: str) -> bool:
        """Check if token has required scope"""
        scopes = token_payload.get("scopes", [])
        return required_scope in scopes or AuthScope.ADMIN.value in scopes
    
    def require_scopes(self, token_payload: Dict, required_scopes: List[str]) -> bool:
        """Check if token has all required scopes"""
        for scope in required_scopes:
            if not self.has_scope(token_payload, scope):
                return False
        return True
    
    # ========== Stats ==========
    
    def get_stats(self) -> Dict[str, Any]:
        """Get auth statistics"""
        return {
            "total_api_keys": self.stats.total_api_keys,
            "active_api_keys": self.stats.active_api_keys,
            "total_tokens_issued": self.stats.total_tokens_issued,
            "active_sessions": self.stats.active_sessions,
            "failed_attempts": self.stats.failed_attempts
        }
    
    def _hash_key(self, key: str) -> str:
        """Hash an API key"""
        return hashlib.sha256(key.encode()).hexdigest()


# FastAPI Dependency
async def get_current_user(
    request: Request,
    auth_manager: "AuthManager" = None
) -> Dict[str, Any]:
    """FastAPI dependency to get current user from Authorization header"""
    if auth_manager is None:
        auth_manager = get_auth_manager()
    
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(401, "Authorization header required")
    
    parts = auth_header.split()
    if len(parts) != 2:
        raise HTTPException(401, "Invalid Authorization header format")
    
    scheme, token = parts
    if scheme.lower() == "bearer":
        payload = auth_manager.validate_access_token(token)
        if not payload:
            raise HTTPException(401, "Invalid or expired token")
        return payload
    elif scheme.lower() == "apikey":
        api_key = auth_manager.validate_api_key(token)
        if not api_key:
            raise HTTPException(401, "Invalid or expired API key")
        return {
            "sub": api_key.id,
            "scopes": api_key.scopes,
            "type": "api_key"
        }
    else:
        raise HTTPException(401, "Unsupported authentication scheme")


def require_scopes(*required_scopes: str):
    """FastAPI dependency to require specific scopes"""
    async def scope_checker(current_user: Dict = Depends(get_current_user)):
        auth_manager = get_auth_manager()
        if not auth_manager.require_scopes(current_user, list(required_scopes)):
            raise HTTPException(403, f"Required scopes: {required_scopes}")
        return current_user
    return scope_checker


# Module-level singleton
_auth_manager: Optional[AuthManager] = None
_lock = asyncio.Lock()


def get_auth_manager() -> AuthManager:
    """Get or create the default auth manager"""
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = AuthManager()
    return _auth_manager


if __name__ == "__main__":
    import uvicorn
    app = FastAPI()
    uvicorn.run(app, host="0.0.0.0", port=8002)
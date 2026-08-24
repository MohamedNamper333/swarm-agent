"""
User Management - User lifecycle, profiles, authentication, and provisioning.
Supports local users, federated identities, and just-in-time provisioning.
"""

import asyncio
import base64
import hashlib
import logging
import secrets
import string
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from pathlib import Path
import bcrypt
import pyotp

logger = logging.getLogger(__name__)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def uuidv7() -> str:
    return str(uuid.uuid4())


# =============================================================================
# User Models
# =============================================================================

class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING_VERIFICATION = "pending_verification"
    DELETED = "deleted"
    LOCKED = "locked"


class UserType(str, Enum):
    LOCAL = "local"
    FEDERATED = "federated"
    SERVICE_ACCOUNT = "service_account"
    SYSTEM = "system"


class AuthMethod(str, Enum):
    PASSWORD = "password"
    OAUTH2 = "oauth2"
    SAML = "saml"
    OIDC = "oidc"
    LDAP = "ldap"
    API_KEY = "api_key"
    WEBAUTHN = "webauthn"
    TOTP = "totp"
    RECOVERY_CODE = "recovery_code"


@dataclass
class UserProfile:
    user_id: str = field(default_factory=lambda: f"usr-{uuidv7()}")
    username: str = ""
    email: str = ""
    email_verified: bool = False
    phone: Optional[str] = None
    phone_verified: bool = False
    first_name: str = ""
    last_name: str = ""
    display_name: str = ""
    avatar_url: Optional[str] = None
    locale: str = "en"
    timezone: str = "UTC"
    metadata: Dict[str, Any] = field(default_factory=dict)
    custom_attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UserCredentials:
    user_id: str
    password_hash: Optional[str] = None
    password_hash_history: List[str] = field(default_factory=list)  # FIXED: renamed to password_hash_history
    password_changed_at: Optional[datetime] = None  # Added for record_password_change
    totp_secret: Optional[str] = None
    totp_enabled: bool = False
    webauthn_credentials: List[Dict[str, Any]] = field(default_factory=list)
    recovery_codes: List[str] = field(default_factory=list)  # Store normalized (no dashes)
    last_password_change: Optional[datetime] = None
    failed_attempts: int = 0
    locked_until: Optional[datetime] = None
    last_login: Optional[datetime] = None
    last_failed_login: Optional[datetime] = None
    password_reset_token: Optional[str] = None
    password_reset_expires: Optional[datetime] = None


@dataclass
class UserSession:
    session_id: str = field(default_factory=lambda: f"sess-{uuidv7()}")
    user_id: str = ""
    tenant_id: str = "default"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc) + timedelta(hours=24))
    last_activity: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    device_fingerprint: Optional[str] = None
    is_mfa_verified: bool = False
    device_trusted: bool = False
    revoked: bool = False
    revoked_at: Optional[datetime] = None
    revoked_reason: Optional[str] = None


@dataclass
class User:
    user_id: str = field(default_factory=lambda: f"usr-{uuidv7()}")
    username: str = ""
    email: str = ""
    status: UserStatus = UserStatus.PENDING_VERIFICATION
    user_type: UserType = UserType.LOCAL
    profile: UserProfile = field(default_factory=UserProfile)
    credentials: UserCredentials = field(default_factory=lambda: UserCredentials(user_id=""))
    roles: List[str] = field(default_factory=list)
    groups: List[str] = field(default_factory=list)
    tenant_id: str = "default"
    federated_identities: List[Dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_login: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    preferences: Dict[str, Any] = field(default_factory=dict)
    tags: Set[str] = field(default_factory=set)


# =============================================================================
# User Store (Abstract)
# =============================================================================

class UserStore(ABC):
    """Abstract user storage."""

    @abstractmethod
    async def create_user(self, user: User) -> User:
        pass

    @abstractmethod
    async def get_user(self, user_id: str) -> Optional[User]:
        pass

    @abstractmethod
    async def get_user_by_email(self, email: str) -> Optional[User]:
        pass

    @abstractmethod
    async def get_user_by_username(self, username: str) -> Optional[User]:
        pass

    @abstractmethod
    async def update_user(self, user: User) -> User:
        pass

    @abstractmethod
    async def delete_user(self, user_id: str) -> bool:
        pass

    @abstractmethod
    async def list_users(
        self,
        tenant_id: Optional[str] = None,
        status: Optional[UserStatus] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[User]:
        pass

    @abstractmethod
    async def search_users(
        self,
        query: str,
        tenant_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[User]:
        pass


class MemoryUserStore:
    """In-memory user store for development/testing."""

    def __init__(self):
        self._users: Dict[str, User] = {}
        self._email_index: Dict[str, str] = {}
        self._username_index: Dict[str, str] = {}
        self._lock = asyncio.Lock()

    async def create_user(self, user: User) -> User:
        async with self._lock:
            if user.user_id in self._users:
                raise ValueError(f"User {user.user_id} already exists")
            if user.email in self._email_index:
                raise ValueError(f"Email {user.email} already exists")
            if user.username in self._username_index:
                raise ValueError(f"Username {user.username} already exists")
            
            self._users[user.user_id] = user
            self._email_index[user.email] = user.user_id
            self._username_index[user.username] = user.user_id
            return user

    async def get_user(self, user_id: str) -> Optional[User]:
        async with self._lock:
            return self._users.get(user_id)

    async def get_user_by_email(self, email: str) -> Optional[User]:
        async with self._lock:
            user_id = self._email_index.get(email)
            if user_id:
                return self._users.get(user_id)
            return None

    async def get_user_by_username(self, username: str) -> Optional[User]:
        async with self._lock:
            user_id = self._username_index.get(username)
            if user_id:
                return self._users.get(user_id)
            return None

    async def update_user(self, user: User) -> User:
        async with self._lock:
            if user.user_id not in self._users:
                raise ValueError(f"User {user.user_id} not found")
            
            # Update indices
            old_user = self._users[user.user_id]
            if old_user.email != user.email:
                self._email_index.pop(old_user.email, None)
                self._email_index[user.email] = user.user_id
            if old_user.username != user.username:
                self._username_index.pop(old_user.username, None)
                self._username_index[user.username] = user.user_id
            
            user.updated_at = datetime.now(timezone.utc)
            self._users[user.user_id] = user
            return user

    async def delete_user(self, user_id: str) -> bool:
        async with self._lock:
            user = self._users.pop(user_id, None)
            if user:
                self._email_index.pop(user.email, None)
                self._username_index.pop(user.username, None)
                return True
            return False

    async def list_users(
        self,
        tenant_id: Optional[str] = None,
        status: Optional[UserStatus] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[User]:
        async with self._lock:
            users = list(self._users.values())
            if tenant_id:
                users = [u for u in users if u.tenant_id == tenant_id]
            if status:
                users = [u for u in users if u.status == status]
            return users[offset:offset + limit]

    async def search_users(
        self,
        query: str,
        tenant_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[User]:
        async with self._lock:
            query_lower = query.lower()
            results = []
            for user in self._users.values():
                if tenant_id and user.tenant_id != tenant_id:
                    continue
                if (query_lower in user.username.lower() or
                    query_lower in user.email.lower() or
                    query_lower in user.profile.first_name.lower() or
                    query_lower in user.profile.last_name.lower()):
                    results.append(user)
                    if len(results) >= limit:
                        break
            return results


# =============================================================================
# Password Manager
# =============================================================================

class PasswordManager:
    """Password hashing, validation, and policy enforcement."""

    def __init__(
        self,
        min_length: int = 12,
        require_uppercase: bool = True,
        require_lowercase: bool = True,
        require_digits: bool = True,
        require_special: bool = True,
        max_length: int = 128,
        bcrypt_rounds: int = 12,
        max_history: int = 5,
        max_age_days: int = 90,
        min_age_days: int = 1,
        lockout_threshold: int = 5,
        lockout_duration_minutes: int = 30,
    ):
        self.min_length = min_length
        self.require_uppercase = require_uppercase
        self.require_lowercase = require_lowercase
        self.require_digits = require_digits
        self.require_special = require_special
        self.max_length = max_length
        self.bcrypt_rounds = bcrypt_rounds
        self.max_history = max_history
        self.max_age_days = max_age_days
        self.min_age_days = min_age_days
        self.lockout_threshold = lockout_threshold
        self.lockout_duration = timedelta(minutes=lockout_duration_minutes)

    def hash_password(self, password: str) -> str:
        """Hash password with bcrypt."""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(self.bcrypt_rounds)).decode()

    def verify_password(self, password: str, hash: str) -> bool:
        """Verify password against hash."""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hash.encode())
        except Exception:
            return False

    def validate_password(self, password: str, user_id: Optional[str] = None) -> Tuple[bool, List[str]]:
        """Validate password against policy."""
        errors = []
        
        if len(password) < self.min_length:
            errors.append(f"Password must be at least {self.min_length} characters")
        if len(password) > self.max_length:
            errors.append(f"Password must not exceed {self.max_length} characters")
        if self.require_uppercase and not any(c.isupper() for c in password):
            errors.append("Password must contain at least one uppercase letter")
        if self.require_lowercase and not any(c.islower() for c in password):
            errors.append("Password must contain at least one lowercase letter")
        if self.require_digits and not any(c.isdigit() for c in password):
            errors.append("Password must contain at least one digit")
        if self.require_special and not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            errors.append("Password must contain at least one special character")
        
        return len(errors) == 0, errors

    def check_password_history(self, password: str, history: List[str]) -> bool:
        """Check if password was used before (compares hashes)."""
        for old_hash in history[-self.max_history:]:
            if self.verify_password(password, old_hash):
                return True
        return False

    def check_password_age(self, last_change: datetime) -> bool:
        """Check if password is expired."""
        age = datetime.now(timezone.utc) - last_change
        return age.days >= self.max_age_days

    def is_locked(self, locked_until: Optional[datetime]) -> bool:
        """Check if account is locked."""
        if not locked_until:
            return False
        return datetime.now(timezone.utc) < locked_until

    def record_failed_attempt(self, credentials: UserCredentials) -> None:
        credentials.failed_attempts += 1
        credentials.last_failed_login = datetime.now(timezone.utc)
        # FIXED: Use config parameters instead of hardcoded values
        if credentials.failed_attempts >= self.lockout_threshold:
            credentials.locked_until = datetime.now(timezone.utc) + self.lockout_duration

    def record_successful_login(self, credentials: UserCredentials) -> None:
        credentials.failed_attempts = 0
        credentials.locked_until = None
        credentials.last_login = datetime.now(timezone.utc)

    def record_password_change(self, credentials: UserCredentials, new_hash: str) -> None:
        credentials.password_hash = new_hash
        credentials.password_changed_at = datetime.now(timezone.utc)
        credentials.password_hash_history.insert(0, new_hash)
        credentials.password_hash_history = credentials.password_hash_history[:self.max_history]


# =============================================================================
# MFA Manager
# =============================================================================

class MFAManager:
    """Multi-factor authentication manager."""

    def __init__(self):
        self.pyotp = pyotp

    def generate_totp_secret(self) -> str:
        """Generate TOTP secret."""
        return pyotp.random_base32()

    def get_totp_uri(self, secret: str, account_name: str, issuer: str = "Swarm") -> str:
        """Get TOTP URI for QR code."""
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(account_name, issuer_name=issuer)

    def verify_totp(self, secret: str, token: str, window: int = 1) -> bool:
        """Verify TOTP token."""
        totp = pyotp.TOTP(secret)
        return totp.verify(token, valid_window=window)

    def generate_recovery_codes(self, count: int = 10, length: int = 10) -> List[str]:
        """Generate recovery codes (normalized - no dashes, uppercase)."""
        alphabet = string.ascii_uppercase + string.digits
        codes = []
        for _ in range(count):
            code = ''.join(secrets.choice(alphabet) for _ in range(length))
            codes.append(code)  # Store normalized form
        return codes

    def format_recovery_code(self, code: str) -> str:
        """Format recovery code for display (XXXX-XXXX-XXXX)."""
        normalized = code.upper().replace('-', '')
        return '-'.join([normalized[i:i+4] for i in range(0, len(normalized), 4)])

    def verify_recovery_code(self, codes: List[str], code: str) -> Tuple[bool, List[str]]:
        """Verify and consume recovery code."""
        normalized = code.upper().replace('-', '')
        for i, stored_code in enumerate(codes):
            # Compare normalized forms
            if stored_code.upper().replace('-', '') == normalized:
                # Consume the code
                remaining = codes[:i] + codes[i+1:]
                return True, remaining
        return False, codes

    def generate_backup_codes(self, count: int = 8) -> List[str]:
        """Generate backup codes for account recovery (alias for generate_recovery_codes)."""
        return self.generate_recovery_codes(count, 8)


# =============================================================================
# WebAuthn Manager (FIDO2)
# =============================================================================

@dataclass
class WebAuthnCredential:
    credential_id: str
    public_key: bytes
    sign_count: int = 0
    transports: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_used: Optional[datetime] = None
    name: str = ""


class WebAuthnManager:
    """WebAuthn/FIDO2 credential management."""

    def __init__(self, rp_id: str, rp_name: str, origin: str):
        self.rp_id = rp_id
        self.rp_name = rp_name
        self.origin = origin
        self._credentials: Dict[str, WebAuthnCredential] = {}
        self._lock = asyncio.Lock()

    async def generate_registration_options(
        self,
        user_id: str,
        username: str,
        display_name: str,
        exclude_credentials: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Generate WebAuthn registration options."""
        challenge = secrets.token_bytes(32)
        
        return {
            "rp": {"id": self.rp_id, "name": self.rp_name},
            "user": {
                "id": base64.urlsafe_b64encode(user_id.encode()).decode().rstrip('='),
                "name": username,
                "displayName": display_name,
            },
            "challenge": base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip('='),
            "pubKeyCredParams": [
                {"type": "public-key", "alg": -7},  # ES256
                {"type": "public-key", "alg": -257},  # RS256
            ],
            "timeout": 60000,
            "excludeCredentials": [
                {"id": base64.urlsafe_b64encode(cid.encode()).decode().rstrip('='), "type": "public-key"}
                for cid in (exclude_credentials or [])
            ],
            "authenticatorSelection": {
                "authenticatorAttachment": "platform",
                "requireResidentKey": False,
                "userVerification": "preferred",
            },
            "attestation": "direct",
        }

    async def verify_registration(
        self,
        user_id: str,
        credential: Dict[str, Any],
        expected_challenge: bytes,
    ) -> Tuple[bool, Optional[str]]:
        """Verify WebAuthn registration response."""
        # In production, use fido2 library for proper verification
        # This is a simplified placeholder
        return True, "cred-id-123"

    async def generate_authentication_options(self, user_id: str) -> Dict[str, Any]:
        """Generate authentication options."""
        return {
            "challenge": base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip('='),
            "timeout": 60000,
            "rpId": self.rp_id,
            "allowCredentials": [],
            "userVerification": "preferred",
        }

    async def verify_authentication(
        self,
        user_id: str,
        credential: Dict[str, Any],
        expected_challenge: bytes,
    ) -> Tuple[bool, Optional[str]]:
        """Verify WebAuthn authentication response."""
        # Simplified - in production use fido2 library
        return True, "cred-id-123"


# =============================================================================
# User Manager
# =============================================================================

class UserManager:
    """High-level user management service."""

    def __init__(
        self,
        user_store: UserStore,
        password_manager: Optional[PasswordManager] = None,
        mfa_manager: Optional[MFAManager] = None,
        webauthn_manager: Optional[WebAuthnManager] = None,
        session_manager: Optional[Any] = None,
    ):
        self.user_store = user_store
        self.password_manager = password_manager or PasswordManager()
        self.mfa_manager = mfa_manager or MFAManager()
        self.webauthn_manager = webauthn_manager
        self.session_manager = session_manager
        self._lock = asyncio.Lock()

    async def create_user(
        self,
        username: str,
        email: str,
        password: str,
        tenant_id: str = "default",
        profile: Optional[Dict[str, Any]] = None,
        roles: Optional[List[str]] = None,
        groups: Optional[List[str]] = None,
        send_verification_email: bool = True,
    ) -> User:
        """Create a new local user."""
        # Validate
        if await self.user_store.get_user_by_username(username):
            raise ValueError(f"Username {username} already exists")
        if await self.user_store.get_user_by_email(email):
            raise ValueError(f"Email {email} already exists")

        # Validate password
        valid, errors = self.password_manager.validate_password(password)
        if not valid:
            raise ValueError(f"Invalid password: {', '.join(errors)}")

        # Create user
        user = User(
            username=username,
            email=email,
            tenant_id=tenant_id,
            user_type=UserType.LOCAL,
            status=UserStatus.PENDING_VERIFICATION if send_verification_email else UserStatus.ACTIVE,
            roles=roles or [],
            groups=groups or [],
        )

        if profile:
            user.profile = UserProfile(**profile)

        # Hash password
        password_hash = self.password_manager.hash_password(password)
        user.credentials.password_hash = password_hash
        user.credentials.password_changed_at = now_utc()

        # Save user
        user = await self.user_store.create_user(user)

        # Send verification email if needed
        if send_verification_email:
            await self._send_verification_email(user)

        return user

    async def get_user(self, user_id: str) -> Optional[User]:
        return await self.user_store.get_user(user_id)

    async def get_user_by_email(self, email: str) -> Optional[User]:
        return await self.user_store.get_user_by_email(email)

    async def get_user_by_username(self, username: str) -> Optional[User]:
        return await self.user_store.get_user_by_username(username)

    async def update_user(self, user_id: str, updates: Dict[str, Any]) -> User:
        user = await self.user_store.get_user(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        # Update profile
        if "profile" in updates:
            for key, value in updates["profile"].items():
                if hasattr(user.profile, key):
                    setattr(user.profile, key, value)

        # Update preferences
        if "preferences" in updates:
            user.preferences.update(updates["preferences"])

        # Update roles/groups
        if "roles" in updates:
            user.roles = updates["roles"]
        if "groups" in updates:
            user.groups = updates["groups"]

        # Update status
        if "status" in updates:
            user.status = UserStatus(updates["status"])

        user.updated_at = datetime.now(timezone.utc)
        return await self.user_store.update_user(user)

    async def authenticate(
        self,
        username_or_email: str,
        password: str,
        tenant_id: str = "default",
        mfa_token: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[Optional[User], Optional[str]]:
        """Authenticate user with username/email and password."""
        # Find user
        user = await self.user_store.get_user_by_email(username_or_email)
        if not user:
            user = await self.user_store.get_user_by_username(username_or_email)
        
        if not user:
            return None, "Invalid credentials"

        if user.tenant_id != tenant_id:
            return None, "Tenant mismatch"

        if user.status != UserStatus.ACTIVE:
            return None, f"Account {user.status.value}"

        # Check lockout
        if self.password_manager.is_locked(user.credentials.locked_until):
            return None, "Account temporarily locked"

        # Verify password
        if not user.credentials.password_hash:
            return None, "No password set"

        if not self.password_manager.verify_password(password, user.credentials.password_hash):
            self.password_manager.record_failed_attempt(user.credentials)
            await self.user_store.update_user(user)
            return None, "Invalid credentials"

        # Check MFA if enabled
        if user.credentials.totp_enabled:
            if not mfa_token:
                return None, "MFA required"
            if not self.mfa_manager.verify_totp(user.credentials.totp_secret, mfa_token):
                self.password_manager.record_failed_attempt(user.credentials)
                await self.user_store.update_user(user)
                return None, "Invalid MFA token"

        # Success
        self.password_manager.record_successful_login(user.credentials)
        user.credentials.last_login = now_utc()
        user.last_login = user.credentials.last_login
        await self.user_store.update_user(user)

        return user, None

    async def initiate_password_reset(self, email: str) -> bool:
        """Initiate password reset flow."""
        user = await self.user_store.get_user_by_email(email)
        if not user:
            # Don't reveal if email exists
            return True

        # Generate reset token
        token = secrets.token_urlsafe(32)
        user.credentials.password_reset_token = hashlib.sha256(token.encode()).hexdigest()
        user.credentials.password_reset_expires = datetime.now(timezone.utc) + timedelta(hours=1)
        
        await self.user_store.update_user(user)

        # Send reset email (implementation depends on email service)
        # await self._send_password_reset_email(user, token)

        return True

    async def reset_password(self, token: str, new_password: str) -> bool:
        """Reset password with token."""
        # Find user with matching token hash
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        users = await self.list_users(limit=10000)
        
        for user in users:
            if user.credentials.password_reset_token == token_hash:
                if user.credentials.password_reset_expires and user.credentials.password_reset_expires > datetime.now(timezone.utc):
                    # Valid token
                    valid, errors = self.password_manager.validate_password(new_password)
                    if not valid:
                        raise ValueError(f"Invalid password: {', '.join(errors)}")
                    
                    if self.password_manager.check_password_history(new_password, user.credentials.password_hash_history):
                        raise ValueError("Password was recently used")
                    
                    new_hash = self.password_manager.hash_password(new_password)
                    self.password_manager.record_password_change(user.credentials, new_hash)
                    
                    # Clear reset token
                    user.credentials.password_reset_token = None
                    user.credentials.password_reset_expires = None
                    
                    await self.user_store.update_user(user)
                    return True
        
        return False

    async def change_password(self, user_id: str, old_password: str, new_password: str) -> bool:
        """Change password with old password verification."""
        user = await self.get_user(user_id)
        if not user:
            return False

        if not self.password_manager.verify_password(old_password, user.credentials.password_hash):
            return False

        valid, errors = self.password_manager.validate_password(new_password)
        if not valid:
            raise ValueError(f"Invalid password: {', '.join(errors)}")

        if self.password_manager.check_password_history(new_password, user.credentials.password_hash_history):
            raise ValueError("Password was recently used")

        new_hash = self.password_manager.hash_password(new_password)
        self.password_manager.record_password_change(user.credentials, new_hash)
        await self.user_store.update_user(user)
        return True

    async def enable_mfa(self, user_id: str, method: AuthMethod) -> Dict[str, Any]:
        """Enable MFA for user."""
        user = await self.get_user(user_id)
        if not user:
            raise ValueError("User not found")

        if method == AuthMethod.TOTP:
            secret = self.mfa_manager.generate_totp_secret()
            uri = self.mfa_manager.get_totp_uri(secret, user.email, "Swarm")
            user.credentials.totp_secret = secret
            user.credentials.totp_enabled = True
            await self.user_store.update_user(user)
            return {"secret": secret, "uri": uri}

        elif method == AuthMethod.WEBAUTHN:
            # WebAuthn registration
            pass

        return {}

    async def disable_mfa(self, user_id: str, method: AuthMethod) -> bool:
        user = await self.get_user(user_id)
        if not user:
            return False

        if method == AuthMethod.TOTP:
            user.credentials.totp_enabled = False
            user.credentials.totp_secret = None
            await self.user_store.update_user(user)
            return True
        return False

    async def generate_recovery_codes(self, user_id: str, count: int = 10) -> List[str]:
        user = await self.get_user(user_id)
        if not user:
            return []

        # Generate and store normalized codes
        codes = self.mfa_manager.generate_recovery_codes(count)
        user.credentials.recovery_codes = codes
        await self.user_store.update_user(user)
        
        # Return formatted codes for display
        return [self.mfa_manager.format_recovery_code(code) for code in codes]

    async def verify_recovery_code(self, user_id: str, code: str) -> bool:
        user = await self.get_user(user_id)
        if not user:
            return False

        success, remaining = self.mfa_manager.verify_recovery_code(user.credentials.recovery_codes, code)
        if success:
            user.credentials.recovery_codes = remaining
            await self.user_store.update_user(user)
            return True
        return False

    async def create_session(
        self,
        user_id: str,
        tenant_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        device_fingerprint: Optional[str] = None,
        remember_me: bool = False,
    ) -> str:
        """Create a new user session."""
        if self.session_manager:
            session_id = await self.session_manager.create_session(
                user_id=user_id,
                tenant_id=tenant_id,
                ip_address=ip_address,
                user_agent=user_agent,
                device_fingerprint=device_fingerprint,
            )
            return session_id
        return ""

    async def revoke_session(self, session_id: str) -> bool:
        if self.session_manager:
            return await self.session_manager.revoke_session(session_id)
        return False

    async def revoke_all_sessions(self, user_id: str) -> int:
        if self.session_manager:
            return await self.session_manager.revoke_all_sessions(user_id)
        return 0

    async def list_sessions(self, user_id: str) -> List[Dict]:
        if self.session_manager:
            sessions = await self.session_manager.get_user_sessions(user_id)
            return [
                {
                    "session_id": s.session_id,
                    "created_at": s.created_at.isoformat(),
                    "expires_at": s.expires_at.isoformat(),
                    "ip_address": s.ip_address,
                    "user_agent": s.user_agent,
                    "device_fingerprint": s.device_fingerprint,
                }
                for s in sessions
            ]
        return []

    # User provisioning / deprovisioning
    async def provision_user(
        self,
        email: str,
        tenant_id: str,
        profile: Dict[str, Any],
        roles: List[str] = None,
        groups: List[str] = None,
        send_invite: bool = True,
    ) -> User:
        """Provision a new user (JIT or admin-initiated)."""
        # Generate temporary password
        temp_password = secrets.token_urlsafe(16)
        
        user = await self.create_user(
            username=email.split("@")[0],
            email=email,
            password=temp_password,
            tenant_id=tenant_id,
            profile=profile,
            roles=roles or [],
            groups=groups or [],
            send_verification_email=send_invite,
        )
        return user

    async def deprovision_user(self, user_id: str, reason: str = "deprovisioned") -> bool:
        """Deprovision user (soft delete)."""
        user = await self.get_user(user_id)
        if not user:
            return False

        user.status = UserStatus.DELETED
        user.updated_at = datetime.now(timezone.utc)
        await self.user_store.update_user(user)

        # Revoke all sessions
        await self.revoke_all_sessions(user_id)

        # Remove from groups/roles
        user.roles = []
        user.groups = []
        await self.user_store.update_user(user)

        return True

    async def suspend_user(self, user_id: str, reason: str = "") -> bool:
        user = await self.get_user(user_id)
        if not user:
            return False

        user.status = UserStatus.SUSPENDED
        user.metadata["suspension_reason"] = reason
        user.updated_at = datetime.now(timezone.utc)
        await self.user_store.update_user(user)

        # Revoke all sessions
        await self.revoke_all_sessions(user_id)

        return True

    async def unsuspend_user(self, user_id: str) -> bool:
        user = await self.get_user(user_id)
        if not user:
            return False

        user.status = UserStatus.ACTIVE
        user.metadata.pop("suspension_reason", None)
        user.updated_at = datetime.now(timezone.utc)
        await self.user_store.update_user(user)
        return True

    async def list_users(
        self,
        tenant_id: Optional[str] = None,
        status: Optional[UserStatus] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[User]:
        return await self.user_store.list_users(tenant_id, status, limit, offset)

    async def search_users(
        self,
        query: str,
        tenant_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[User]:
        return await self.user_store.search_users(query, tenant_id, limit)

    async def get_user_stats(self, tenant_id: Optional[str] = None) -> Dict[str, Any]:
        users = await self.list_users(tenant_id=tenant_id, limit=10000)
        
        stats = {
            "total": len(users),
            "by_status": {},
            "by_type": {},
            "with_mfa": 0,
            "recent_logins": 0,
        }

        for user in users:
            stats["by_status"][user.status.value] = stats["by_status"].get(user.status.value, 0) + 1
            stats["by_type"][user.user_type.value] = stats["by_type"].get(user.user_type.value, 0) + 1
            if user.credentials.totp_enabled:
                stats["with_mfa"] += 1
            if user.last_login and user.last_login > datetime.now(timezone.utc) - timedelta(days=30):
                stats["recent_logins"] += 1

        return stats


# =============================================================================
# JIT Provisioning (Just-In-Time)
# =============================================================================

class JITProvisioner:
    """Just-in-Time user provisioning from federated identities."""

    def __init__(
        self,
        user_manager: UserManager,
        role_manager: Any = None,
    ):
        self.user_manager = user_manager
        self.role_manager = role_manager

    async def provision_from_saml(
        self,
        saml_assertion: Dict[str, Any],
        idp_id: str,
        tenant_id: str,
    ) -> User:
        """Provision user from SAML assertion."""
        # Extract user info from SAML assertion
        subject_id = saml_assertion.get("subject_id", "")
        attributes = saml_assertion.get("attributes", {})
        
        email = attributes.get("email", [""])[0] if isinstance(attributes.get("email"), list) else attributes.get("email", "")
        first_name = attributes.get("givenName", [""])[0] if attributes.get("givenName") else ""
        last_name = attributes.get("sn", [""])[0] if attributes.get("sn") else ""
        
        # Check if user exists
        user = await self.user_manager.get_user_by_email(attributes.get("email", ""))
        
        if user:
            # Update existing user
            user.profile.first_name = first_name
            user.profile.last_name = last_name
            user.federated_identities.append({
                "idp_id": idp_id,
                "subject_id": subject_id,
                "provider": "saml",
            })
            await self.user_manager.update_user(user)
            return user
        
        # Create new user
        username = attributes.get("email", "").split("@")[0]
        return await self.user_manager.provision_user(
            email=attributes.get("email", ""),
            tenant_id=tenant_id,
            profile={
                "first_name": first_name,
                "last_name": last_name,
            },
        )

    async def provision_from_oidc(
        self,
        id_token: Dict[str, Any],
        idp_id: str,
        tenant_id: str,
    ) -> User:
        """Provision user from OIDC ID token."""
        email = id_token.get("email", "")
        sub = id_token.get("sub", "")
        
        # Check existing
        user = await self.user_manager.get_user_by_email(id_token.get("email", ""))
        
        if user:
            # Update federated identity
            user.federated_identities.append({
                "idp_id": idp_id,
                "subject_id": id_token.get("sub", ""),
                "provider": "oidc",
            })
            await self.user_manager.update_user(user)
            return user

        # Create new user
        return await self.user_manager.provision_user(
            email=id_token.get("email", ""),
            tenant_id=tenant_id,
            profile={
                "first_name": id_token.get("given_name", ""),
                "last_name": id_token.get("family_name", ""),
            },
        )


# =============================================================================
# Factory
# =============================================================================

def create_user_manager(
    user_store: Optional[UserStore] = None,
    password_manager: Optional[PasswordManager] = None,
    mfa_manager: Optional[MFAManager] = None,
    webauthn_manager: Optional[WebAuthnManager] = None,
) -> UserManager:
    if user_store is None:
        user_store = MemoryUserStore()
    if password_manager is None:
        password_manager = PasswordManager()
    if mfa_manager is None:
        mfa_manager = MFAManager()
    if webauthn_manager is None:
        webauthn_manager = WebAuthnManager("swarm.example.com", "Swarm", "https://swarm.example.com")
    
    return UserManager(user_store, password_manager, mfa_manager, webauthn_manager)


def create_password_manager(**kwargs) -> PasswordManager:
    return PasswordManager(**kwargs)


def create_mfa_manager() -> MFAManager:
    return MFAManager()


def create_webauthn_manager(rp_id: str, rp_name: str, origin: str) -> WebAuthnManager:
    return WebAuthnManager(rp_id, rp_name, origin)


def create_jit_provisioner(user_manager: UserManager, role_manager: Any = None) -> Any:
    return None
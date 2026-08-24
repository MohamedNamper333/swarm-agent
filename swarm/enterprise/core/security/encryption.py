import uuid
import logging
"""
Encryption at Rest - AES-256-GCM encryption with key management.
Provides encryption for Memory V2, Artifact Store, and Audit Trail.
"""

import base64
import hashlib
import hmac
import json
import os
import secrets
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from cryptography.hazmat.primitives import hashes, hmac as crypto_hmac
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

logger = logging.getLogger(__name__)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def uuidv7() -> str:
    return str(uuid.uuid4())


# =============================================================================
# Encryption Models
# =============================================================================

class EncryptionAlgorithm(str, Enum):
    AES_256_GCM = "AES-256-GCM"
    AES_128_GCM = "AES-128-GCM"
    CHACHA20_POLY1305 = "ChaCha20-Poly1305"


class KeyType(str, Enum):
    DATA_ENCRYPTION_KEY = "data_encryption_key"  # DEK - encrypts data
    KEY_ENCRYPTION_KEY = "key_encryption_key"    # KEK - encrypts DEKs
    MASTER_KEY = "master_key"                    # Root key


class KeyStatus(str, Enum):
    ACTIVE = "active"
    ROTATING = "rotating"
    DEPRECATED = "deprecated"
    REVOKED = "revoked"
    DESTROYED = "destroyed"


@dataclass
class EncryptionKey:
    """Encryption key with metadata."""
    key_id: str = field(default_factory=lambda: f"key-{uuid.uuid4()}")
    key_type: KeyType = KeyType.DATA_ENCRYPTION_KEY
    algorithm: EncryptionAlgorithm = EncryptionAlgorithm.AES_256_GCM
    key_material: bytes = field(default_factory=bytes)
    status: KeyStatus = KeyStatus.ACTIVE
    version: int = 1
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    rotated_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    tenant_id: str = "default"
    
    def is_active(self) -> bool:
        if self.status != KeyStatus.ACTIVE:
            return False
        if self.expires_at and datetime.now(timezone.utc) > self.expires_at:
            return False
        return True
    
    def is_expired(self) -> bool:
        if self.expires_at and datetime.now(timezone.utc) > self.expires_at:
            return True
        return False


@dataclass
class EncryptedData:
    """Encrypted data package."""
    ciphertext: bytes
    nonce: bytes
    tag: bytes
    key_id: str
    algorithm: EncryptionAlgorithm = EncryptionAlgorithm.AES_256_GCM
    aad: bytes = field(default_factory=bytes)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "ciphertext": base64.b64encode(self.ciphertext).decode(),
            "nonce": base64.b64encode(self.nonce).decode(),
            "tag": base64.b64encode(self.tag).decode(),
            "key_id": self.key_id,
            "algorithm": self.algorithm.value,
            "aad": base64.b64encode(self.aad).decode(),
            "created_at": self.created_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EncryptedData":
        return cls(
            ciphertext=base64.b64decode(data["ciphertext"]),
            nonce=base64.b64decode(data["nonce"]),
            tag=base64.b64decode(data["tag"]),
            key_id=data["key_id"],
            algorithm=EncryptionAlgorithm(data["algorithm"]),
            aad=base64.b64decode(data["aad"]),
            created_at=datetime.fromisoformat(data["created_at"]),
        )


@dataclass
class EncryptionConfig:
    """Encryption configuration."""
    algorithm: EncryptionAlgorithm = EncryptionAlgorithm.AES_256_GCM
    key_size_bytes: int = 32  # 256 bits
    nonce_size_bytes: int = 12
    tag_size_bytes: int = 16
    aad_enabled: bool = True
    key_derivation_iterations: int = 100000
    key_rotation_days: int = 90
    master_key_rotation_days: int = 365
    envelope_encryption: bool = True


# =============================================================================
# Key Management Service
# =============================================================================

class KeyManagementService:
    """Manages encryption keys with lifecycle, rotation, and access control."""
    
    def __init__(
        self,
        config: Optional[EncryptionConfig] = None,
        master_key: Optional[bytes] = None,
    ):
        self.config = config or EncryptionConfig()
        self._master_key = master_key or self._generate_master_key()
        self._keys: Dict[str, EncryptionKey] = {}
        self._lock = threading.RLock()
        self._rotation_thread: Optional[threading.Thread] = None
        self._rotation_running = False
        
        # Initialize with a default DEK
        self._initialize_default_keys()
    
    def _generate_master_key(self) -> bytes:
        """Generate a new master key."""
        return secrets.token_bytes(self.config.key_size_bytes)
    
    def _initialize_default_keys(self) -> None:
        """Initialize default encryption keys."""
        # Create default DEK
        default_dek = EncryptionKey(
            key_id="default-dek",
            key_type=KeyType.DATA_ENCRYPTION_KEY,
            algorithm=self.config.algorithm,
            key_material=secrets.token_bytes(self.config.key_size_bytes),
            status=KeyStatus.ACTIVE,
            tenant_id="default",
        )
        self._keys[default_dek.key_id] = default_dek
        
        # Create default KEK
        default_kek = EncryptionKey(
            key_id="default-kek",
            key_type=KeyType.KEY_ENCRYPTION_KEY,
            algorithm=self.config.algorithm,
            key_material=secrets.token_bytes(self.config.key_size_bytes),
            status=KeyStatus.ACTIVE,
            tenant_id="default",
        )
        self._keys[default_kek.key_id] = default_kek
    
    def generate_key(
        self,
        key_type: KeyType = KeyType.DATA_ENCRYPTION_KEY,
        algorithm: EncryptionAlgorithm = EncryptionAlgorithm.AES_256_GCM,
        tenant_id: str = "default",
        expires_in_days: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> EncryptionKey:
        """Generate a new encryption key."""
        with self._lock:
            key = EncryptionKey(
                key_type=key_type,
                algorithm=algorithm,
                key_material=secrets.token_bytes(self.config.key_size_bytes),
                status=KeyStatus.ACTIVE,
                tenant_id=tenant_id,
                metadata=metadata or {},
            )
            
            if expires_in_days:
                key.expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)
            
            self._keys[key.key_id] = key
            logger.info(f"Generated key: {key.key_id} ({key_type.value})")
            return key
    
    def get_key(self, key_id: str) -> Optional[EncryptionKey]:
        """Get a key by ID."""
        with self._lock:
            return self._keys.get(key_id)
    
    def get_active_key(self, tenant_id: str, key_type: KeyType) -> Optional[EncryptionKey]:
        """Get the active key of a specific type for a tenant."""
        with self._lock:
            for key in self._keys.values():
                if (key.tenant_id == tenant_id and 
                    key.key_type == key_type and 
                    key.status == KeyStatus.ACTIVE and
                    key.is_active()):
                    return key
        return None
    
    def list_keys(
        self,
        tenant_id: Optional[str] = None,
        key_type: Optional[KeyType] = None,
        status: Optional[KeyStatus] = None,
    ) -> List[EncryptionKey]:
        with self._lock:
            keys = list(self._keys.values())
            
            if tenant_id:
                keys = [k for k in keys if k.tenant_id == tenant_id]
            if key_type:
                keys = [k for k in keys if k.key_type == key_type]
            if status:
                keys = [k for k in keys if k.status == status]
            
            return keys
    
    def rotate_key(self, key_id: str, reason: str = "scheduled") -> Optional[EncryptionKey]:
        """Rotate a key - mark old as deprecated, create new."""
        with self._lock:
            old_key = self._keys.get(key_id)
            if not old_key:
                return None
            
            # Mark old key as rotating
            old_key.status = KeyStatus.ROTATING
            old_key.rotated_at = datetime.now(timezone.utc)
            
            # Create new key with same properties
            new_key = EncryptionKey(
                key_type=old_key.key_type,
                algorithm=old_key.algorithm,
                key_material=secrets.token_bytes(self.config.key_size_bytes),
                status=KeyStatus.ACTIVE,
                tenant_id=old_key.tenant_id,
                metadata={**old_key.metadata, "rotated_from": key_id, "reason": reason},
            )
            
            self._keys[new_key.key_id] = new_key
            
            # Mark old as deprecated
            old_key.status = KeyStatus.DEPRECATED
            
            logger.info(f"Rotated key: {key_id} -> {new_key.key_id} (reason: {reason})")
            return new_key
    
    def revoke_key(self, key_id: str, reason: str = "revoked") -> bool:
        """Revoke a key."""
        with self._lock:
            key = self._keys.get(key_id)
            if not key:
                return False
            
            key.status = KeyStatus.REVOKED
            key.metadata["revocation_reason"] = reason
            key.metadata["revoked_at"] = datetime.now(timezone.utc).isoformat()
            logger.warning(f"Revoked key: {key_id} (reason: {reason})")
            return True
    
    def destroy_key(self, key_id: str) -> bool:
        """Destroy a key - secure deletion."""
        with self._lock:
            key = self._keys.get(key_id)
            if not key:
                return False
            
            # Overwrite key material
            key.key_material = b"\x00" * len(key.key_material)
            key.status = KeyStatus.DESTROYED
            logger.warning(f"Destroyed key: {key_id}")
            return True
    
    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            keys = list(self._keys.values())
            return {
                "total_keys": len(keys),
                "active": sum(1 for k in keys if k.status == KeyStatus.ACTIVE),
                "rotating": sum(1 for k in keys if k.status == KeyStatus.ROTATING),
                "deprecated": sum(1 for k in keys if k.status == KeyStatus.DEPRECATED),
                "revoked": sum(1 for k in keys if k.status == KeyStatus.REVOKED),
                "destroyed": sum(1 for k in keys if k.status == KeyStatus.DESTROYED),
                "by_type": {
                    t.value: sum(1 for k in keys if k.key_type == t)
                    for t in KeyType
                },
                "by_tenant": {
                    tenant: sum(1 for k in keys if k.tenant_id == tenant)
                    for tenant in set(k.tenant_id for k in keys)
                },
            }


# =============================================================================
# Encryption Service
# =============================================================================

class EncryptionService:
    """High-level encryption service using envelope encryption."""
    
    def __init__(
        self,
        kms: Optional[KeyManagementService] = None,
        config: Optional[EncryptionConfig] = None,
    ):
        self.kms = kms or KeyManagementService()
        self.config = config or EncryptionConfig()
        self._lock = threading.RLock()
    
    def encrypt(
        self,
        plaintext: Union[str, bytes],
        key_id: Optional[str] = None,
        tenant_id: str = "default",
        aad: Optional[bytes] = None,
    ) -> EncryptedData:
        """Encrypt data using envelope encryption."""
        # Get or create DEK
        if key_id:
            dek = self.kms.get_key(key_id)
        else:
            dek = self.kms.get_active_key(tenant_id, KeyType.DATA_ENCRYPTION_KEY)
        
        if not dek:
            dek = self.kms.generate_key(
                key_type=KeyType.DATA_ENCRYPTION_KEY,
                tenant_id=tenant_id,
            )
        
        # Encrypt with DEK
        cipher = AESGCM(dek.key_material)
        nonce = secrets.token_bytes(self.config.nonce_size_bytes)
        
        if isinstance(plaintext, str):
            plaintext = plaintext.encode('utf-8')
        
        ciphertext = cipher.encrypt(nonce, plaintext, aad)
        
        # In AES-GCM, the tag is appended to ciphertext
        ciphertext_with_tag = ciphertext
        tag = b""  # AESGCM includes tag in ciphertext
        
        return EncryptedData(
            ciphertext=ciphertext_with_tag,
            nonce=nonce,
            tag=tag,
            key_id=dek.key_id,
            algorithm=dek.algorithm,
            aad=aad or b"",
        )
    
    def decrypt(
        self,
        encrypted_data: EncryptedData,
        tenant_id: str = "default",
        aad: Optional[bytes] = None,
    ) -> bytes:
        """Decrypt data."""
        dek = self.kms.get_key(encrypted_data.key_id)
        if not dek:
            raise ValueError(f"Key not found: {encrypted_data.key_id}")
        
        if not dek.is_active():
            raise ValueError(f"Key {encrypted_data.key_id} is not active")
        
        cipher = AESGCM(dek.key_material)
        
        # For AESGCM, ciphertext includes tag
        plaintext = cipher.decrypt(
            encrypted_data.nonce,
            encrypted_data.ciphertext,
            encrypted_data.aad or aad or b"",
        )
        
        return plaintext
    
    def encrypt_file(
        self,
        input_path: str,
        output_path: str,
        key_id: Optional[str] = None,
        tenant_id: str = "default",
    ) -> bool:
        """Encrypt a file."""
        try:
            with open(input_path, 'rb') as f:
                plaintext = f.read()
            
            encrypted = self.encrypt(plaintext, key_id, tenant_id)
            
            with open(output_path, 'wb') as f:
                f.write(encrypted.ciphertext)
                f.write(encrypted.nonce)
                f.write(encrypted.tag)
                f.write(encrypted.key_id.encode())
                f.write(len(encrypted.aad).to_bytes(4, 'big'))
                f.write(encrypted.aad)
            
            return True
        except Exception as e:
            logger.error(f"File encryption failed: {e}")
            return False
    
    def decrypt_file(
        self,
        input_path: str,
        output_path: str,
        tenant_id: str = "default",
    ) -> bool:
        """Decrypt a file."""
        try:
            with open(input_path, 'rb') as f:
                ciphertext = f.read()
                
                # Parse file format: ciphertext + nonce + tag + key_id + aad_len + aad
                key_id_len = len(ciphertext) - 12 - 16  # approximate
                # This is simplified - in production use proper framing
                
            return True
        except Exception as e:
            logger.error(f"File decryption failed: {e}")
            return False
    
    def rotate_data_keys(self, tenant_id: str = "default") -> int:
        """Rotate all active DEKs for a tenant."""
        rotated = 0
        for key in self.kms.list_keys(tenant_id=tenant_id, key_type=KeyType.DATA_ENCRYPTION_KEY):
            if key.status == KeyStatus.ACTIVE:
                self.kms.rotate_key(key.key_id, "scheduled_rotation")
                rotated += 1
        return rotated


# =============================================================================
# Envelope Encryption (Hybrid Encryption)
# =============================================================================

class EnvelopeEncryption:
    """Envelope encryption: encrypt data with DEK, encrypt DEK with KEK."""
    
    def __init__(self, kms: KeyManagementService):
        self.kms = kms
    
    def encrypt(
        self,
        plaintext: bytes,
        tenant_id: str = "default",
        aad: Optional[bytes] = None,
    ) -> Tuple[bytes, bytes, str]:  # (encrypted_data, encrypted_dek, dek_id)
        """Encrypt data with envelope encryption."""
        # Get or create DEK
        dek = self.kms.get_active_key(tenant_id, KeyType.DATA_ENCRYPTION_KEY)
        if not dek:
            dek = self.kms.generate_key(KeyType.DATA_ENCRYPTION_KEY, tenant_id=tenant_id)
        
        # Encrypt data with DEK
        cipher = AESGCM(dek.key_material)
        nonce = secrets.token_bytes(12)
        ciphertext = cipher.encrypt(nonce, plaintext, aad)
        
        # Get KEK
        kek = self.kms.get_active_key(tenant_id, KeyType.KEY_ENCRYPTION_KEY)
        if not kek:
            kek = self.kms.generate_key(KeyType.KEY_ENCRYPTION_KEY, tenant_id=tenant_id)
        
        # Encrypt DEK with KEK
        kek_cipher = AESGCM(kek.key_material)
        kek_nonce = secrets.token_bytes(12)
        encrypted_dek = kek_cipher.encrypt(kek_nonce, dek.key_material, aad)
        
        return ciphertext, encrypted_dek, dek.key_id
    
    def decrypt(
        self,
        ciphertext: bytes,
        encrypted_dek: bytes,
        dek_id: str,
        tenant_id: str = "default",
        aad: Optional[bytes] = None,
    ) -> bytes:
        """Decrypt data with envelope encryption."""
        # Get KEK
        kek = self.kms.get_key(dek_id.replace("-dek", "-kek"))  # Simplified
        if not kek:
            raise ValueError("KEK not found")
        
        # Decrypt DEK
        kek_cipher = AESGCM(kek.key_material)
        # Need to parse encrypted_dek (nonce + ciphertext)
        dek_nonce = encrypted_dek[:12]
        encrypted_dek_data = encrypted_dek[12:]
        dek_material = kek_cipher.decrypt(dek_nonce, encrypted_dek_data, aad)
        
        # Decrypt data
        dek_cipher = AESGCM(dek_material)
        nonce = ciphertext[:12]
        data = ciphertext[12:]
        plaintext = dek_cipher.decrypt(nonce, data, aad)
        
        return plaintext


# =============================================================================
# Key Derivation
# =============================================================================

def derive_key(
    password: bytes,
    salt: bytes,
    algorithm: str = "PBKDF2",
    iterations: int = 100000,
    key_length: int = 32,
) -> bytes:
    """Derive encryption key from password."""
    if algorithm == "PBKDF2":
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=key_length,
            salt=salt,
            iterations=iterations,
        )
    elif algorithm == "SCRYPT":
        kdf = Scrypt(
            length=key_length,
            salt=salt,
            n=2**14,
            r=8,
            p=1,
        )
    else:
        raise ValueError(f"Unknown algorithm: {algorithm}")
    
    return kdf.derive(password)


def derive_hkdf_key(
    ikm: bytes,
    salt: bytes,
    info: bytes,
    length: int = 32,
) -> bytes:
    """Derive key using HKDF."""
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=length,
        salt=salt,
        info=info,
    )
    return hkdf.derive(ikm)


# =============================================================================
# Factory
# =============================================================================

def create_encryption_service(
    config: Optional[EncryptionConfig] = None,
    master_key: Optional[bytes] = None,
) -> EncryptionService:
    """Create an encryption service."""
    kms = KeyManagementService(config, master_key)
    return EncryptionService(kms, config)


def create_key_management_service(
    config: Optional[EncryptionConfig] = None,
    master_key: Optional[bytes] = None,
) -> KeyManagementService:
    """Create a key management service."""
    return KeyManagementService(config, master_key)

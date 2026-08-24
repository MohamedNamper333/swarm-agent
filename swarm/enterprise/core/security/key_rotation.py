"""Key Rotation - Automated key rotation management."""

import asyncio
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
from cryptography.hazmat.primitives.asymmetric import rsa, ec
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import logging

logger = logging.getLogger(__name__)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class KeyRotationPolicy(str, Enum):
    ROTATE_ON_SCHEDULE = "schedule"
    ROTATE_ON_COMPROMISE = "compromise"
    ROTATE_ON_DEMAND = "demand"


@dataclass
class KeyMetadata:
    """Key metadata for rotation tracking."""
    key_id: str
    key_type: str  # jwt, encryption, signing, mls
    algorithm: str
    created_at: datetime
    rotated_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    status: str = "active"  # active, deprecated, revoked
    rotation_policy: KeyRotationPolicy = KeyRotationPolicy.ROTATE_ON_SCHEDULE
    rotation_interval_days: int = 90
    compromise_detected: bool = False


class KeyRotationManager:
    """Manages cryptographic key rotation."""
    
    def __init__(self):
        self._keys: Dict[str, KeyMetadata] = {}
        self._key_material: Dict[str, Any] = {}
        self._lock = asyncio.Lock()
        self._rotation_callbacks: List[Callable] = []
    
    def generate_key(
        self,
        key_id: str,
        key_type: str,
        algorithm: str = "RS256",
        rotation_interval_days: int = 90,
        policy: KeyRotationPolicy = KeyRotationPolicy.ROTATE_ON_SCHEDULE,
    ) -> Any:
        """Generate a new key."""
        if key_type == "jwt":
            if algorithm.startswith("RS"):
                key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            elif algorithm.startswith("ES"):
                key = ec.generate_private_key(ec.SECP256R1())
            else:
                raise ValueError(f"Unsupported algorithm: {algorithm}")
        elif key_type == "encryption":
            key = AESGCM.generate_key(bit_length=256)
        elif key_type == "signing":
            key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        else:
            raise ValueError(f"Unknown key type: {key_type}")
        
        metadata = KeyMetadata(
            key_id=key_id,
            key_type=key_type,
            algorithm=algorithm,
            created_at=now_utc(),
            expires_at=now_utc() + timedelta(days=rotation_interval_days),
            rotation_policy=policy,
            rotation_interval_days=rotation_interval_days,
        )
        
        with self._lock:
            self._keys[key_id] = metadata
            self._key_material[key_id] = key
        
        return key
    
    def get_key(self, key_id: str) -> Optional[Any]:
        with self._lock:
            return self._key_material.get(key_id)
    
    def get_metadata(self, key_id: str) -> Optional[KeyMetadata]:
        with self._lock:
            return self._keys.get(key_id)
    
    async def rotate_key(self, key_id: str, reason: str = "scheduled") -> str:
        """Rotate a key."""
        async with self._lock:
            old_meta = self._keys.get(key_id)
            if not old_meta:
                raise ValueError(f"Key {key_id} not found")
            
            old_meta.status = "deprecated"
            old_meta.rotated_at = now_utc()
            
            new_key_id = f"{key_id}-v{int(now_utc().timestamp())}"
            new_key = self.generate_key(
                key_id=new_key_id,
                key_type=old_meta.key_type,
                algorithm=old_meta.algorithm,
                rotation_interval_days=old_meta.rotation_interval_days,
                policy=old_meta.rotation_policy,
            )
            
            for callback in self._rotation_callbacks:
                try:
                    await callback(new_key_id, self._keys[new_key_id])
                except Exception as e:
                    logger.error(f"Rotation callback failed: {e}")
            
            return new_key_id
    
    def get_active_keys(self, key_type: Optional[str] = None) -> List[KeyMetadata]:
        with self._lock:
            keys = [k for k in self._keys.values() if k.status == "active"]
            if key_type:
                keys = [k for k in keys if k.key_type == key_type]
            return keys
    
    def get_keys_needing_rotation(self, days_ahead: int = 7) -> List[KeyMetadata]:
        with self._lock:
            now = now_utc()
            threshold = now + timedelta(days=days_ahead)
            return [
                k for k in self._keys.values()
                if k.status == "active" and k.expires_at and k.expires_at <= threshold
            ]
    
    def add_rotation_callback(self, callback: Callable) -> None:
        self._rotation_callbacks.append(callback)


def create_key_rotation_manager() -> KeyRotationManager:
    """Create key rotation manager."""
    return KeyRotationManager()

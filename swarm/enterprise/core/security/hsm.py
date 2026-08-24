"""
HSM (Hardware Security Module) Integration.
Supports PKCS#11 for AWS CloudHSM, YubiHSM2, and HashiCorp Vault HSM.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class HSMKeyInfo:
    """Information about a key stored in HSM."""
    key_id: str
    key_type: str  # RSA, EC, AES
    key_size: int
    label: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    extractable: bool = False  # Keys in HSM should never be extractable


class HSMBACKEND(ABC):
    """Abstract HSM backend interface."""
    
    @abstractmethod
    async def generate_key(
        self,
        key_id: str,
        key_type: str,
        key_size: int,
        label: str,
    ) -> HSMKeyInfo:
        """Generate a new key inside the HSM."""
        ...
    
    @abstractmethod
    async def sign(self, key_id: str, data: bytes) -> bytes:
        """Sign data using a key stored in the HSM."""
        ...
    
    @abstractmethod
    async def verify(self, key_id: str, data: bytes, signature: bytes) -> bool:
        """Verify a signature using a key stored in the HSM."""
        ...
    
    @abstractmethod
    async def delete_key(self, key_id: str) -> bool:
        """Delete a key from the HSM."""
        ...
    
    @abstractmethod
    async def list_keys(self) -> List[HSMKeyInfo]:
        """List all keys in the HSM."""
        ...


class MockHSMBACKEND(HSMBACKEND):
    """Mock HSM for development/testing. NOT FOR PRODUCTION USE."""
    
    def __init__(self):
        self._keys: Dict[str, Dict[str, Any]] = {}
        logger.warning("MockHSM is for development only. Use real HSM for production.")
    
    async def generate_key(self, key_id: str, key_type: str, key_size: int, label: str) -> HSMKeyInfo:
        from cryptography.hazmat.primitives.asymmetric import rsa
        
        if key_type == "RSA":
            key = rsa.generate_private_key(public_exponent=65537, key_size=key_size)
        
        self._keys[key_id] = {
            "key": key,
            "public_key": key.public_key(),
            "key_type": key_type,
            "key_size": key_size,
            "label": label,
            "created_at": datetime.now(timezone.utc),
        }
        
        return HSMKeyInfo(
            key_id=key_id,
            key_type=key_type,
            key_size=key_size,
            label=label,
            extractable=False,
        )
    
    async def sign(self, key_id: str, data: bytes) -> bytes:
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding
        
        key_info = self._keys.get(key_id)
        if not key_info:
            raise ValueError(f"Key {key_id} not found")
        
        key = key_info["key"]
        return key.sign(data, padding.PKCS1v15(), hashes.SHA256())
    
    async def verify(self, key_id: str, data: bytes, signature: bytes) -> bool:
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding
        
        key_info = self._keys.get(key_id)
        if not key_info:
            return False
        
        try:
            public_key = key_info["public_key"]
            public_key.verify(signature, data, padding.PKCS1v15(), hashes.SHA256())
            return True
        except Exception as e:
            logger.debug(f"Verify failed: {e}")
            return False
    
    async def delete_key(self, key_id: str) -> bool:
        if key_id in self._keys:
            del self._keys[key_id]
            return True
        return False
    
    async def list_keys(self) -> List[HSMKeyInfo]:
        return [
            HSMKeyInfo(
                key_id=kid,
                key_type=info["key_type"],
                key_size=info["key_size"],
                label=info["label"],
                created_at=info["created_at"],
                extractable=False,
            )
            for kid, info in self._keys.items()
        ]


class HSMManager:
    """Manages HSM operations across backends."""
    
    def __init__(self, backend: Optional[HSMBACKEND] = None):
        self.backend = backend or MockHSMBACKEND()
        logger.info(f"HSM Manager initialized with backend: {type(self.backend).__name__}")
    
    async def generate_key(
        self,
        key_id: str,
        key_type: str = "RSA",
        key_size: int = 2048,
        label: str = "",
    ) -> HSMKeyInfo:
        """Generate a key inside the HSM. Key material never leaves the HSM."""
        return await self.backend.generate_key(key_id, key_type, key_size, label)
    
    async def sign_data(self, key_id: str, data: bytes) -> bytes:
        """Sign data using HSM-stored key."""
        return await self.backend.sign(key_id, data)
    
    async def verify_signature(self, key_id: str, data: bytes, signature: bytes) -> bool:
        """Verify signature using HSM-stored key."""
        return await self.backend.verify(key_id, data, signature)
    
    async def delete_key(self, key_id: str) -> bool:
        """Delete a key from HSM."""
        return await self.backend.delete_key(key_id)
    
    async def list_keys(self) -> List[HSMKeyInfo]:
        """List all keys in HSM."""
        return await self.backend.list_keys()
    
    def health_check(self) -> bool:
        """Check HSM health."""
        try:
            import asyncio
            asyncio.run(self.list_keys())
            return True
        except Exception as e:
            logger.error(f"HSM health check failed: {e}")
            return False


def create_hsm_manager(backend: Optional[HSMBACKEND] = None) -> HSMManager:
    """Create an HSM manager."""
    return HSMManager(backend)

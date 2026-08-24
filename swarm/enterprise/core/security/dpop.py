"""DPoP (RFC 9449) - Demonstration of Proof of Possession."""

import asyncio
import base64
import hashlib
import hmac
import json
import secrets
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
import logging

logger = logging.getLogger(__name__)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def uuidv7() -> str:
    return str(uuid.uuid4())


@dataclass
class DPoPProof:
    """DPoP Proof JWT."""
    header: Dict[str, Any]
    payload: Dict[str, Any]
    signature: str
    raw: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class DPoPManager:
    """Manages DPoP proof generation and verification."""
    
    def __init__(self, private_key: Optional[rsa.RSAPrivateKey] = None):
        if private_key:
            self.private_key = private_key
            self.public_key = private_key.public_key()
        else:
            self.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            self.public_key = self.private_key.public_key()
    
    def _jwk_thumbprint(self) -> str:
        numbers = self.public_key.public_numbers()
        jwk = {
            "kty": "RSA",
            "n": base64.urlsafe_b64encode(
                numbers.n.to_bytes((numbers.n.bit_length() + 7) // 8, 'big')
            ).decode().rstrip('='),
            "e": base64.urlsafe_b64encode(
                numbers.e.to_bytes((numbers.e.bit_length() + 7) // 8, 'big')
            ).decode().rstrip('='),
        }
        jwk_json = json.dumps(jwk, sort_keys=True, separators=(',', ':'))
        return base64.urlsafe_b64encode(
            hashlib.sha256(jwk_json.encode()).digest()
        ).decode().rstrip('=')
    
    def create_proof(self, htu: str, htm: str, ath: Optional[str] = None) -> DPoPProof:
        """Create a DPoP proof."""
        header = {
            "typ": "dpop+jwt",
            "alg": "RS256",
            "jwk": {
                "kty": "RSA",
                "n": base64.urlsafe_b64encode(
                    self.public_key.public_numbers().n.to_bytes(
                        (self.public_key.public_numbers().n.bit_length() + 7) // 8, 'big'
                    )
                ).decode().rstrip('='),
                "e": base64.urlsafe_b64encode(
                    self.public_key.public_numbers().e.to_bytes(
                        (self.public_key.public_numbers().e.bit_length() + 7) // 8, 'big'
                    )
                ).decode().rstrip('='),
                "jkt": self._jwk_thumbprint(),
            },
        }
        
        payload = {
            "jti": uuidv7(),
            "htm": htm.upper(),
            "htu": htu,
            "iat": int(now_utc().timestamp()),
        }
        if ath:
            payload["ath"] = ath
        
        header_json = json.dumps(header, separators=(',', ':'))
        payload_json = json.dumps(payload, separators=(',', ':'))
        
        header_b64 = base64.urlsafe_b64encode(header_json.encode()).decode().rstrip('=')
        payload_b64 = base64.urlsafe_b64encode(payload_json.encode()).decode().rstrip('=')
        
        signing_input = f"{header_b64}.{payload_b64}"
        
        signature = self.private_key.sign(
            signing_input.encode(),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        signature_b64 = base64.urlsafe_b64encode(signature).decode().rstrip('=')
        
        return DPoPProof(
            header=header,
            payload=payload,
            signature=signature_b64,
            raw=f"{signing_input}.{signature_b64}",
        )
    
    def verify_proof(self, proof: DPoPProof, htu: str, htm: str, max_age_seconds: int = 60) -> Tuple[bool, Optional[str]]:
        """Verify DPoP proof."""
        try:
            signature = base64.urlsafe_b64decode(proof.signature + "==")
            signing_input = ".".join(proof.raw.split(".")[:2])
            
            self.public_key.verify(
                signature,
                signing_input.encode(),
                padding.PKCS1v15(),
                hashes.SHA256(),
            )
            
            if proof.payload.get("htu") != htu:
                return False, "HTU mismatch"
            if proof.payload.get("htm", "").upper() != htm.upper():
                return False, "HTM mismatch"
            
            iat = proof.payload.get("iat", 0)
            if abs(int(now_utc().timestamp()) - iat) > max_age_seconds:
                return False, "Proof expired"
            
            return True, None
        except Exception as e:
            return False, str(e)


def create_dpop_manager(private_key: Optional[rsa.RSAPrivateKey] = None) -> DPoPManager:
    """Create DPoP manager."""
    return DPoPManager(private_key)

"""
Advanced Security - DPoP, mTLS, Key Rotation, Immutable Audit Logging.
"""

import asyncio
import base64
import hashlib
import hmac
import json
import secrets
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from abc import ABC, abstractmethod
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, ec, padding
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import logging

logger = logging.getLogger(__name__)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def uuidv7() -> str:
    return str(uuid.uuid4())


# =============================================================================
# DPoP (RFC 9449) - Demonstration of Proof of Possession
# =============================================================================

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
    
    def __init__(
        self,
        private_key: Optional[rsa.RSAPrivateKey] = None,
        public_key: Optional[rsa.RSAPublicKey] = None,
        jwk_thumbprint: Optional[str] = None,
    ):
        if private_key and public_key:
            self.private_key = private_key
            self.public_key = public_key
        else:
            # Generate key pair
            self.private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
            )
            self.public_key = self.private_key.public_key()
        
        # Calculate JWK thumbprint
        self.jwk_thumbprint = jwk_thumbprint or self._calculate_jwk_thumbprint()
    
    def _calculate_jwk_thumbprint(self) -> str:
        """Calculate JWK thumbprint (RFC 7638)."""
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
    
    def create_proof(
        self,
        htu: str,  # HTTP URI
        htm: str,  # HTTP Method
        ath: Optional[str] = None,  # Access Token Hash
        jti: Optional[str] = None,  # JWT ID
    ) -> DPoPProof:
        """Create a DPoP proof JWT."""
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
            },
        }
        
        payload = {
            "jti": jti or uuidv7(),
            "htm": htm.upper(),
            "htu": htu,
            "iat": int(now_utc().timestamp()),
        }
        
        if ath:
            payload["ath"] = ath
        
        # Sign
        signing_input = f"{base64.urlsafe_b64encode(json.dumps(header, separators=(',', ':')).encode()).decode().rstrip('=')}.{base64.urlsafe_b64encode(json.dumps(payload, separators=(',', ':')).encode()).decode().rstrip('=')}"
        
        signature = self.private_key.sign(
            signing_input.encode(),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        
        signature_b64 = base64.urlsafe_b64encode(signature).decode().rstrip('=')
        raw = f"{signing_input}.{signature_b64}"
        
        return DPoPProof(
            header=header,
            payload=payload,
            signature=signature_b64,
            raw=raw,
        )
    
    def verify_proof(
        self,
        proof: DPoPProof,
        htu: str,
        htm: str,
        ath: Optional[str] = None,
        max_age_seconds: int = 60,
    ) -> Tuple[bool, Optional[str]]:
        """Verify a DPoP proof."""
        try:
            # Verify signature
            signing_input = ".".join(proof.raw.split(".")[:2])
            signature = base64.urlsafe_b64decode(proof.signature + "==")
            
            self.public_key.verify(
                signature,
                signing_input.encode(),
                padding.PKCS1v15(),
                hashes.SHA256(),
            )
            
            # Verify claims
            if proof.payload.get("htu") != htu:
                return False, "HTU mismatch"
            
            if proof.payload.get("htm", "").upper() != htm.upper():
                return False, "HTM mismatch"
            
            if ath and proof.payload.get("ath") != ath:
                return False, "ATH mismatch"
            
            # Check timestamp
            iat = proof.payload.get("iat", 0)
            if abs(int(now_utc().timestamp()) - iat) > max_age_seconds:
                return False, "Proof expired"
            
            # Check JWK thumbprint matches
            if proof.header.get("jwk") and "jkt" in proof.header.get("jwk", {}):
                if proof.header["jwk"]["jkt"] != self.jwk_thumbprint:
                    return False, "JWK thumbprint mismatch"
            
            return True, None
            
        except Exception as e:
            return False, str(e)


# =============================================================================
# mTLS (Mutual TLS) Token Binding
# =============================================================================

@dataclass
class MTLSCertificate:
    """mTLS certificate info."""
    cert_pem: str
    key_pem: str
    ca_pem: Optional[str] = None
    subject: str = ""
    issuer: str = ""
    not_before: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    not_after: datetime = field(default_factory=lambda: datetime.now(timezone.utc) + timedelta(days=365))
    serial_number: str = ""
    fingerprint_sha256: str = ""


class MTLSManager:
    """Manages mTLS certificates and token binding."""
    
    def __init__(
        self,
        ca_cert_pem: Optional[str] = None,
        ca_key_pem: Optional[str] = None,
    ):
        if ca_cert_pem and ca_key_pem:
            self.ca_cert = serialization.load_pem_x509_certificate(ca_cert_pem.encode())
            self.ca_key = serialization.load_pem_private_key(ca_key_pem.encode(), password=None)
        else:
            # Generate self-signed CA
            self.ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            self.ca_cert = self._generate_ca_cert()
        
        self._issued_certs: Dict[str, MTLSCertificate] = {}
    
    def _generate_ca_cert(self) -> Any:
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, "Swarm CA"),
        ])
        
        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            self.ca_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.now(timezone.utc)
        ).not_valid_after(
            datetime.now(timezone.utc) + timedelta(days=3650)
        ).add_extension(
            x509.BasicConstraints(ca=True, path_length=None),
            critical=True,
        ).sign(self.ca_key, hashes.SHA256())
        
        return cert
    
    def issue_certificate(
        self,
        common_name: str,
        san_dns: List[str] = None,
        san_ip: List[str] = None,
        validity_days: int = 365,
    ) -> MTLSCertificate:
        """Issue a client/server certificate."""
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        
        # Generate private key
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        
        # Build CSR
        subject = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, common_name),
        ])
        
        builder = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            self.ca_cert.subject
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.now(timezone.utc)
        ).not_valid_after(
            datetime.now(timezone.utc) + timedelta(days=validity_days)
        ).add_extension(
            x509.BasicConstraints(ca=False, path_length=None),
            critical=True,
        ).add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_encipherment=True,
                key_agreement=False,
                content_commitment=False,
                data_encipherment=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        ).add_extension(
            x509.ExtendedKeyUsage([
                x509.ExtendedKeyUsageOID.CLIENT_AUTH,
                x509.ExtendedKeyUsageOID.SERVER_AUTH,
            ]),
            critical=True,
        )
        
        # Add SANs
        san_list = []
        if san_dns:
            for dns in san_dns:
                san_list.append(x509.DNSName(dns))
        if san_ip:
            for ip in san_ip:
                san_list.append(x509.IPAddress(ip))
        
        if san_list:
            builder = builder.add_extension(
                x509.SubjectAlternativeName(san_list),
                critical=False,
            )
        
        cert = builder.sign(self.ca_key, hashes.SHA256())
        
        # Serialize
        cert_pem = cert.public_bytes(serialization.Encoding.PEM).decode()
        key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode()
        ca_pem = self.ca_cert.public_bytes(serialization.Encoding.PEM).decode()
        
        # Calculate fingerprint
        fingerprint = hashlib.sha256(cert.public_bytes(serialization.Encoding.DER)).hexdigest()
        
        mtls_cert = MTLSCertificate(
            cert_pem=cert_pem,
            key_pem=key_pem,
            ca_pem=ca_pem,
            subject=common_name,
            issuer=self.ca_cert.subject.rfc4514_string(),
            not_before=cert.not_valid_before_utc,
            not_after=cert.not_valid_after_utc,
            serial_number=str(cert.serial_number),
            fingerprint_sha256=fingerprint,
        )
        
        self._issued_certs[fingerprint] = mtls_cert
        
        return mtls_cert
    
    def verify_certificate_chain(self, cert_pem: str) -> bool:
        """Verify certificate chain against CA."""
        try:
            cert = serialization.load_pem_x509_certificate(cert_pem.encode())
            # Verify signature
            self.ca_cert.public_key().verify(
                cert.signature,
                cert.tbs_certificate_bytes,
                padding.PKCS1v15(),
                cert.signature_hash_algorithm,
            )
            # Check validity period
            now = datetime.now(timezone.utc)
            if cert.not_valid_before_utc > now or cert.not_valid_after_utc < now:
                return False
            return True
        except Exception:
            return False
    
    def bind_token_to_cert(self, token: str, cert_fingerprint: str) -> str:
        """Bind token to certificate (RFC 8705)."""
        # Create token binding ID
        binding_id = hashlib.sha256(f"{token}:{cert_fingerprint}".encode()).hexdigest()[:32]
        return binding_id
    
    def verify_token_binding(self, token: str, cert_fingerprint: str, binding_id: str) -> bool:
        """Verify token binding."""
        expected = hashlib.sha256(f"{token}:{cert_fingerprint}".encode()).hexdigest()[:32]
        return hmac.compare_digest(expected, binding_id)


# =============================================================================
# Key Rotation Manager
# =============================================================================

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
        self._key_material: Dict[str, Any] = {}  # key_id -> actual key
        self._lock = asyncio.Lock()
        self._rotation_callbacks: List[Callable[[str, KeyMetadata], None]] = []
    
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
    
    async def rotate_key(
        self,
        key_id: str,
        reason: str = "scheduled",
    ) -> str:
        """Rotate a key, returning new key ID."""
        
        with self._lock:
            old_metadata = self._keys.get(key_id)
            if not old_metadata:
                raise ValueError(f"Key {key_id} not found")
            
            # Mark old key as deprecated
            old_metadata.status = "deprecated"
            old_metadata.rotated_at = now_utc()
            
            # Generate new key
            new_key_id = f"{key_id}-v{int(now_utc().timestamp())}"
            new_key = self.generate_key(
                key_id=new_key_id,
                key_type=old_metadata.key_type,
                algorithm=old_metadata.algorithm,
                rotation_interval_days=old_metadata.rotation_interval_days,
                policy=old_metadata.rotation_policy,
            )
            
            # Trigger callbacks
            for callback in self._rotation_callbacks:
                try:
                    await callback(new_key_id, self._keys[new_key_id])
                except Exception as e:
                    logger.error(f"Rotation callback failed: {e}")
            
            logger.info(f"Rotated key {key_id} -> {new_key_id} (reason: {reason})")
            return new_key_id
    
    async def revoke_key(self, key_id: str, reason: str = "compromise") -> bool:
        """Revoke a key immediately."""
        with self._lock:
            metadata = self._keys.get(key_id)
            if not metadata:
                return False
            
            metadata.status = "revoked"
            metadata.compromise_detected = True
            metadata.rotated_at = now_utc()
            
            # Remove key material
            self._key_material.pop(key_id, None)
            
            logger.warning(f"Key {key_id} revoked: {reason}")
            return True
    
    def get_active_keys(self, key_type: Optional[str] = None) -> List[KeyMetadata]:
        with self._lock:
            keys = [k for k in self._keys.values() if k.status == "active"]
            if key_type:
                keys = [k for k in keys if k.key_type == key_type]
            return keys
    
    def get_keys_needing_rotation(self, days_ahead: int = 7) -> List[KeyMetadata]:
        """Get keys that need rotation soon."""
        with self._lock:
            now = now_utc()
            threshold = now + timedelta(days=days_ahead)
            return [
                k for k in self._keys.values()
                if k.status == "active" and k.expires_at and k.expires_at <= threshold
            ]
    
    def add_rotation_callback(self, callback: Callable[[str, KeyMetadata], None]) -> None:
        """Add callback for key rotation events."""
        self._rotation_callbacks.append(callback)
    
    def export_public_keys(self) -> Dict[str, Any]:
        """Export public keys for JWKS endpoint."""
        result = {}
        with self._lock:
            for key_id, metadata in self._keys.items():
                if metadata.status == "active" and key_id in self._key_material:
                    key = self._key_material[key_id]
                    if hasattr(key, 'public_key'):
                        result[key_id] = key.public_key()
                    elif metadata.key_type == "encryption":
                        # For symmetric keys, export base64
                        import base64
                        result[key_id] = base64.b64encode(key).decode()
        return result


# =============================================================================
# Immutable Audit Logging
# =============================================================================

@dataclass
class AuditEvent:
    """Immutable audit event."""
    event_id: str = field(default_factory=lambda: f"audit-{uuidv7()}")
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    event_type: str = ""
    actor: str = ""  # user_id, service_id, system
    action: str = ""
    resource: str = ""
    resource_id: str = ""
    outcome: str = "success"  # success, failure, partial
    details: Dict[str, Any] = field(default_factory=dict)
    
    # Cryptographic chaining
    previous_hash: str = ""
    current_hash: str = ""
    sequence_number: int = 0
    
    # Metadata
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    correlation_id: Optional[str] = None
    trace_id: Optional[str] = None


class AuditLog:
    """Immutable audit log with cryptographic chaining."""
    
    def __init__(self, log_name: str = "swarm-audit"):
        self.log_name = log_name
        self._events: List[AuditEvent] = []
        self._last_hash: str = "0" * 64  # Genesis hash
        self._sequence: int = 0
        self._lock = asyncio.Lock()
        
        # External anchoring (optional)
        self._anchors: List[Dict[str, Any]] = []
    
    def _calculate_hash(self, event: AuditEvent) -> str:
        """Calculate hash for event chaining."""
        data = f"{event.sequence_number}:{event.timestamp.isoformat()}:{event.event_type}:{event.actor}:{event.action}:{event.resource}:{event.resource_id}:{event.outcome}:{json.dumps(event.details, sort_keys=True)}:{event.previous_hash}"
        return hashlib.sha256(data.encode()).hexdigest()
    
    async def append(
        self,
        event_type: str,
        actor: str,
        action: str,
        resource: str,
        resource_id: str,
        outcome: str = "success",
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        correlation_id: Optional[str] = None,
        trace_id: Optional[str] = None,
    ) -> AuditEvent:
        """Append an event to the audit log."""
        
        async with self._lock:
            self._sequence += 1
            
            event = AuditEvent(
                event_type=event_type,
                actor=actor,
                action=action,
                resource=resource,
                resource_id=resource_id,
                outcome=outcome,
                details=details or {},
                previous_hash=self._last_hash,
                sequence_number=self._sequence,
                ip_address=ip_address,
                user_agent=user_agent,
                correlation_id=correlation_id,
                trace_id=trace_id,
            )
            
            event.current_hash = self._calculate_hash(event)
            self._last_hash = event.current_hash
            self._events.append(event)
        
        return event
    
    def verify_chain(self, start: int = 0, end: Optional[int] = None) -> Tuple[bool, List[str]]:
        """Verify the integrity of the audit chain."""
        errors = []
        expected_hash = "0" * 64
        
        end = end or len(self._events)
        
        for i, event in enumerate(self._events[start:end], start=start):
            # Verify sequence
            if event.sequence_number != i + 1:
                errors.append(f"Event {event.event_id}: sequence number mismatch (expected {i+1}, got {event.sequence_number})")
            
            # Verify previous hash
            if event.previous_hash != expected_hash:
                errors.append(f"Event {event.event_id}: previous hash mismatch")
            
            # Verify current hash
            calculated = self._calculate_hash(event)
            if event.current_hash != calculated:
                errors.append(f"Event {event.event_id}: current hash mismatch (tampering detected)")
            
            expected_hash = event.current_hash
        
        return len(errors) == 0, errors
    
    def get_events(
        self,
        event_type: Optional[str] = None,
        actor: Optional[str] = None,
        resource: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000,
    ) -> List[AuditEvent]:
        """Get events with filters."""
        events = self._events
        
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        if actor:
            events = [e for e in events if e.actor == actor]
        if resource:
            events = [e for e in events if e.resource == resource]
        if start_time:
            events = [e for e in events if e.timestamp >= start_time]
        if end_time:
            events = [e for e in events if e.timestamp <= end_time]
        
        return events[-limit:]
    
    def get_last_hash(self) -> str:
        """Get the last hash for anchoring."""
        return self._last_hash
    
    async def anchor(self, anchor_service: str = "timestamp") -> Dict[str, Any]:
        """Anchor the current hash to external timestamping service."""
        anchor = {
            "timestamp": now_utc().isoformat(),
            "hash": self._last_hash,
            "sequence": self._sequence,
            "service": anchor_service,
        }
        
        self._anchors.append(anchor)
        
        # In production: submit to RFC 3161 timestamping authority or blockchain
        return anchor
    
    def export_tamper_proof(self, start: int = 0, end: Optional[int] = None) -> Dict[str, Any]:
        """Export tamper-proof audit segment."""
        end = end or len(self._events)
        segment = self._events[start:end]
        
        return {
            "log_name": self.log_name,
            "start_sequence": start + 1,
            "end_sequence": end,
            "start_hash": segment[0].previous_hash if segment else "0" * 64,
            "end_hash": segment[-1].current_hash if segment else "0" * 64,
            "events": [
                {
                    "event_id": e.event_id,
                    "timestamp": e.timestamp.isoformat(),
                    "event_type": e.event_type,
                    "actor": e.actor,
                    "action": e.action,
                    "resource": e.resource,
                    "resource_id": e.resource_id,
                    "outcome": e.outcome,
                    "details": e.details,
                    "previous_hash": e.previous_hash,
                    "current_hash": e.current_hash,
                    "sequence_number": e.sequence_number,
                }
                for e in segment
            ],
            "anchors": self._anchors,
        }


# =============================================================================
# Audit Log Manager
# =============================================================================

class AuditLogManager:
    """Manages multiple audit logs."""
    
    def __init__(self):
        self._logs: Dict[str, AuditLog] = {}
        self._lock = asyncio.Lock()
    
    def get_log(self, name: str) -> AuditLog:
        """Get or create an audit log."""
        if name not in self._logs:
            self._logs[name] = AuditLog(name)
        return self._logs[name]
    
    async def log(
        self,
        log_name: str,
        event_type: str,
        actor: str,
        action: str,
        resource: str,
        resource_id: str,
        outcome: str = "success",
        details: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> AuditEvent:
        """Log an event to named audit log."""
        log = self.get_log(log_name)
        return await log.append(
            event_type=event_type,
            actor=actor,
            action=action,
            resource=resource,
            resource_id=resource_id,
            outcome=outcome,
            details=details,
            **kwargs,
        )
    
    def verify_all_logs(self) -> Dict[str, Tuple[bool, List[str]]]:
        """Verify all audit logs."""
        results = {}
        for name, log in self._logs.items():
            results[name] = log.verify_chain()
        return results
    
    def export_all(self) -> Dict[str, Any]:
        """Export all audit logs."""
        return {
            name: log.export_tamper_proof()
            for name, log in self._logs.items()
        }


# =============================================================================
# Factory
# =============================================================================

def create_dpop_manager(
    private_key: Optional[Any] = None,
    public_key: Optional[Any] = None,
) -> DPoPManager:
    """Create DPoP manager."""
    return DPoPManager(private_key, public_key)


def create_mtls_manager(
    ca_cert_pem: Optional[str] = None,
    ca_key_pem: Optional[str] = None,
) -> MTLSManager:
    """Create mTLS manager."""
    return MTLSManager(ca_cert_pem, ca_key_pem)


def create_key_rotation_manager() -> KeyRotationManager:
    """Create key rotation manager."""
    return KeyRotationManager()


def create_audit_log(name: str = "swarm-audit") -> AuditLog:
    """Create an audit log."""
    return AuditLog(name)


def create_audit_log_manager() -> AuditLogManager:
    """Create audit log manager."""
    return AuditLogManager()

"""mTLS (Mutual TLS) - Certificate and token binding management."""

import base64
import hashlib
import logging
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography import x509
from cryptography.x509.oid import NameOID

logger = logging.getLogger(__name__)


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
    
    def __init__(self, ca_cert_pem: Optional[str] = None, ca_key_pem: Optional[str] = None):
        if ca_cert_pem and ca_key_pem:
            self.ca_cert = serialization.load_pem_x509_certificate(ca_cert_pem.encode())
            self.ca_key = serialization.load_pem_private_key(ca_key_pem.encode(), password=None)
        else:
            # Self-signed CA
            self.ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            self.ca_cert = self._generate_ca_cert()
    
    def _generate_ca_cert(self) -> x509.Certificate:
        subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Swarm CA")])
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(self.ca_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.now(timezone.utc))
            .not_valid_after(datetime.now(timezone.utc) + timedelta(days=3650))
            .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
            .sign(self.ca_key, hashes.SHA256())
        )
        return cert
    
    def issue_certificate(
        self,
        common_name: str,
        san_dns: Optional[List[str]] = None,
        validity_days: int = 365,
    ) -> MTLSCertificate:
        """Issue a client/server certificate."""
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        
        subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])
        builder = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(self.ca_cert.subject)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.now(timezone.utc))
            .not_valid_after(datetime.now(timezone.utc) + timedelta(days=validity_days))
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .add_extension(
                x509.KeyUsage(
                    digital_signature=True,
                    key_encipherment=True,
                    content_commitment=False,
                    data_encipherment=False,
                    key_cert_sign=False,
                    crl_sign=False,
                    key_agreement=False,
                    encipher_only=False,
                    decipher_only=False,
                ),
                critical=True,
            )
            .add_extension(
                x509.ExtendedKeyUsage([
                    x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH,
                    x509.oid.ExtendedKeyUsageOID.SERVER_AUTH,
                ]),
                critical=True,
            )
        )
        
        if san_dns:
            builder = builder.add_extension(
                x509.SubjectAlternativeName([x509.DNSName(dns) for dns in san_dns]),
                critical=False,
            )
        
        cert = builder.sign(self.ca_key, hashes.SHA256())
        
        fingerprint = hashlib.sha256(cert.public_bytes(serialization.Encoding.DER)).hexdigest()
        
        return MTLSCertificate(
            cert_pem=cert.public_bytes(serialization.Encoding.PEM).decode(),
            key_pem=key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            ).decode(),
            ca_pem=self.ca_cert.public_bytes(serialization.Encoding.PEM).decode(),
            subject=common_name,
            issuer=self.ca_cert.subject.rfc4514_string(),
            not_before=cert.not_valid_before_utc,
            not_after=cert.not_valid_after_utc,
            serial_number=str(cert.serial_number),
            fingerprint_sha256=fingerprint,
        )
    
    def bind_token_to_cert(self, token: str, cert_fingerprint: str) -> str:
        """Bind token to certificate (RFC 8705)."""
        return hashlib.sha256(f"{token}:{cert_fingerprint}".encode()).hexdigest()[:32]
    
    def verify_token_binding(self, token: str, cert_fingerprint: str, binding_id: str) -> bool:
        """Verify token binding."""
        expected = hashlib.sha256(f"{token}:{cert_fingerprint}".encode()).hexdigest()[:32]
        return hmac.compare_digest(expected, binding_id)


def create_mtls_manager(
    ca_cert_pem: Optional[str] = None,
    ca_key_pem: Optional[str] = None,
) -> MTLSManager:
    """Create mTLS manager."""
    return MTLSManager(ca_cert_pem, ca_key_pem)

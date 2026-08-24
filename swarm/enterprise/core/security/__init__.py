"""
Security - Encryption, key management, advanced security (DPoP, mTLS, Key Rotation), and audit logging.
"""

from .encryption import (
    EncryptionAlgorithm,
    KeyType,
    KeyStatus,
    EncryptionKey,
    EncryptedData,
    EncryptionConfig,
    KeyManagementService,
    EncryptionService,
    EnvelopeEncryption,
    derive_key,
    derive_hkdf_key,
    create_encryption_service,
    create_key_management_service,
)

# Advanced Security modules
try:
    from .dpop import (
        DPoPManager,
        DPoPProof,
        create_dpop_manager,
    )
    from .mtls import (
        MTLSManager,
        MTLSCertificate,
        create_mtls_manager,
    )
    from .key_rotation import (
        KeyRotationManager,
        KeyRotationPolicy,
        KeyMetadata,
        create_key_rotation_manager,
    )
    from .audit_log import (
        AuditLog,
        AuditEvent,
        AuditLogManager,
        create_audit_log,
        create_audit_log_manager,
    )
except ImportError as e:
    import logging
    logger = logging.getLogger(__name__)
    logger.warning(f"Advanced security modules not available: {e}")

__all__ = [
    "EncryptionAlgorithm",
    "KeyType",
    "KeyStatus",
    "EncryptionKey",
    "EncryptedData",
    "EncryptionConfig",
    "KeyManagementService",
    "EncryptionService",
    "EnvelopeEncryption",
    "derive_key",
    "derive_hkdf_key",
    "create_encryption_service",
    "create_key_management_service",
    # Advanced Security
    "DPoPManager",
    "DPoPProof",
    "create_dpop_manager",
    "MTLSManager",
    "MTLSCertificate",
    "create_mtls_manager",
    "KeyRotationManager",
    "KeyRotationPolicy",
    "KeyMetadata",
    "create_key_rotation_manager",
    "AuditLog",
    "AuditEvent",
    "AuditLogManager",
    "create_audit_log",
    "create_audit_log_manager",
]

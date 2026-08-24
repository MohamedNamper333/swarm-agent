"""
Unified Audit Trail - Immutable audit logging with cryptographic integrity.
"""

from .trail import (
    AuditEventType,
    AuditSeverity,
    AuditEvent,
    AuditStorage,
    InMemoryAuditStorage,
    FileAuditStorage,
    AuditLogger,
    AuditTrailManager,
    create_audit_trail,
    create_audit_logger,
)

__all__ = [
    "AuditEventType",
    "AuditSeverity",
    "AuditEvent",
    "AuditStorage",
    "InMemoryAuditStorage",
    "FileAuditStorage",
    "AuditLogger",
    "AuditTrailManager",
    "create_audit_trail",
    "create_audit_logger",
]

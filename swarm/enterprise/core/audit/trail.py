import json
"""
Unified Audit Trail - Immutable audit logging with cryptographic integrity.
"""

import hashlib
import threading
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def uuidv7() -> str:
    return str(uuid.uuid4())


# =============================================================================
# Audit Models
# =============================================================================

class AuditEventType(str, Enum):
    """Types of audit events."""
    # Authentication
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    PASSWORD_CHANGED = "password_changed"
    MFA_ENABLED = "mfa_enabled"
    MFA_DISABLED = "mfa_disabled"
    
    # Authorization
    ACCESS_GRANTED = "access_granted"
    ACCESS_DENIED = "access_denied"
    ROLE_ASSIGNED = "role_assigned"
    ROLE_REVOKED = "role_revoked"
    PERMISSION_CHANGED = "permission_changed"
    
    # Resource
    RESOURCE_CREATED = "resource_created"
    RESOURCE_UPDATED = "resource_updated"
    RESOURCE_DELETED = "resource_deleted"
    RESOURCE_ACCESSED = "resource_accessed"
    
    # Configuration
    CONFIG_CHANGED = "config_changed"
    POLICY_CREATED = "policy_created"
    POLICY_UPDATED = "policy_updated"
    POLICY_DELETED = "policy_deleted"
    FEATURE_FLAG_CHANGED = "feature_flag_changed"
    
    # Data
    DATA_EXPORTED = "data_exported"
    DATA_IMPORTED = "data_imported"
    DATA_ACCESSED = "data_accessed"
    DATA_MODIFIED = "data_modified"
    DATA_DELETED = "data_deleted"
    
    # System
    SYSTEM_STARTUP = "system_startup"
    SYSTEM_SHUTDOWN = "system_shutdown"
    BACKUP_STARTED = "backup_started"
    BACKUP_COMPLETED = "backup_completed"
    RESTORE_STARTED = "restore_started"
    RESTORE_COMPLETED = "restore_completed"
    
    # Security
    SECURITY_INCIDENT = "security_incident"
    VULNERABILITY_DETECTED = "vulnerability_detected"
    THREAT_DETECTED = "threat_detected"
    ANOMALY_DETECTED = "anomaly_detected"
    
    # Audit
    AUDIT_LOG_ACCESSED = "audit_log_accessed"
    AUDIT_CONFIG_CHANGED = "audit_config_changed"
    
    # Custom
    CUSTOM = "custom"


class AuditSeverity(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """Immutable audit event with cryptographic chaining."""
    event_id: str = field(default_factory=lambda: f"audit-{uuidv7()}")
    event_type: AuditEventType = AuditEventType.CUSTOM
    severity: AuditSeverity = AuditSeverity.INFO
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Actor
    actor_id: str = "system"
    actor_type: str = "system"  # user, agent, system, service
    tenant_id: str = "default"
    
    # Action
    action: str = ""
    outcome: str = "success"  # success, failure, partial
    
    # Resource
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    
    # Context
    details: Dict[str, Any] = field(default_factory=dict)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    trace_id: Optional[str] = None
    correlation_id: Optional[str] = None
    
    # Cryptographic integrity
    previous_hash: Optional[str] = None
    event_hash: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "severity": self.severity.value,
            "timestamp": self.timestamp.isoformat(),
            "actor_id": self.actor_id,
            "actor_type": self.actor_type,
            "tenant_id": self.tenant_id,
            "action": self.action,
            "outcome": self.outcome,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "details": self.details,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "trace_id": self.trace_id,
            "correlation_id": self.correlation_id,
            "previous_hash": self.previous_hash,
            "event_hash": self.event_hash,
        }
    
    def to_json(self) -> str:
        import json
        return json.dumps(self.to_dict(), ensure_ascii=False, default=str)


# =============================================================================
# Audit Storage
# =============================================================================

class AuditStorage(ABC):
    """Abstract audit storage backend."""
    
    @abstractmethod
    def append(self, event: 'AuditEvent') -> bool:
        pass
    
    @abstractmethod
    def query(
        self,
        tenant_id: Optional[str] = None,
        event_type: Optional[str] = None,
        actor_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        severity: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List['AuditEvent']:
        pass
    
    @abstractmethod
    def get_by_id(self, event_id: str) -> Optional['AuditEvent']:
        pass
    
    @abstractmethod
    def count(
        self,
        tenant_id: Optional[str] = None,
        event_type: Optional[str] = None,
        actor_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> int:
        pass
    
    @abstractmethod
    def verify_integrity(self) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    def export(self, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        pass


class InMemoryAuditStorage(AuditStorage):
    """In-memory audit storage with cryptographic chaining."""
    
    def __init__(self):
        self._events: List[AuditEvent] = []
        self._lock = threading.RLock()
        self._last_hash: Optional[str] = None
    
    def append(self, event: 'AuditEvent') -> bool:
        with self._lock:
            # Chain events cryptographically
            event.previous_hash = self._last_hash
            event.event_hash = self._compute_hash(event)
            self._last_hash = event.event_hash
            
            self._events.append(event)
            return True
    
    def _compute_hash(self, event: 'AuditEvent') -> str:
        # Exclude event_hash and previous_hash from hash computation
        # to ensure consistency between append and verify
        event_dict = event.to_dict()
        excluded_fields = {'event_hash', 'previous_hash'}
        filtered_dict = {k: v for k, v in event_dict.items() if k not in excluded_fields}
        data = f"{event.event_id}{event.timestamp.isoformat()}{event.previous_hash or ''}{json.dumps(filtered_dict, sort_keys=True, default=str)}"
        return hashlib.sha256(data.encode()).hexdigest()
    
    def query(
        self,
        tenant_id: Optional[str] = None,
        event_type: Optional[str] = None,
        actor_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        severity: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List['AuditEvent']:
        with self._lock:
            events = self._events
            
            if tenant_id:
                events = [e for e in events if e.tenant_id == tenant_id]
            if event_type:
                events = [e for e in events if e.event_type.value == event_type]
            if actor_id:
                events = [e for e in events if e.actor_id == actor_id]
            if start_time:
                events = [e for e in events if e.timestamp >= start_time]
            if end_time:
                events = [e for e in events if e.timestamp <= end_time]
            if severity:
                events = [e for e in events if e.severity.value == severity]
            
            events.sort(key=lambda e: e.timestamp, reverse=True)
            return events[offset:offset + limit]
    
    def get_by_id(self, event_id: str) -> Optional['AuditEvent']:
        with self._lock:
            for event in self._events:
                if event.event_id == event_id:
                    return event
            return None
    
    def count(
        self,
        tenant_id: Optional[str] = None,
        event_type: Optional[str] = None,
        actor_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> int:
        with self._lock:
            events = self._events
            
            if tenant_id:
                events = [e for e in events if e.tenant_id == tenant_id]
            if event_type:
                events = [e for e in events if e.event_type.value == event_type]
            if actor_id:
                events = [e for e in events if e.actor_id == actor_id]
            if start_time:
                events = [e for e in events if e.timestamp >= start_time]
            if end_time:
                events = [e for e in events if e.timestamp <= end_time]
            
            return len(events)
    
    def verify_integrity(self) -> Dict[str, Any]:
        with self._lock:
            if not self._events:
                return {"valid": True, "checked": 0}
            
            prev_hash = None
            valid = True
            errors = []
            
            for i, event in enumerate(self._events):
                if event.previous_hash != prev_hash:
                    valid = False
                    errors.append(f"Event {i}: previous_hash mismatch")
                
                computed = self._compute_hash(event)
                if event.event_hash != computed:
                    valid = False
                    errors.append(f"Event {i}: event_hash mismatch")
                
                prev_hash = event.event_hash
            
            return {
                "valid": valid,
                "checked": len(self._events),
                "errors": errors,
            }
    
    def export(self, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        with self._lock:
            events = [
                e for e in self._events
                if start_time <= e.timestamp <= end_time
            ]
            events.sort(key=lambda e: e.timestamp)
            return [e.to_dict() for e in events]


class FileAuditStorage(AuditStorage):
    """File-based audit storage with rotation."""
    
    def __init__(self, directory: str = "/var/log/audit", max_file_size_mb: int = 100):
        self.directory = directory
        self.max_file_size = max_file_size_mb * 1024 * 1024
        self._current_file: Optional[str] = None
        self._current_size = 0
        self._lock = threading.RLock()
        
        import os
        os.makedirs(directory, exist_ok=True)
        self._rotate_file()
    
    def _rotate_file(self) -> None:
        import os
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        self._current_file = os.path.join(self.directory, f"audit_{uuid.uuid4().hex[:8]}_{timestamp}.jsonl")
        self._current_size = 0
    
    def _write_event(self, event: 'AuditEvent') -> None:
        import json
        if self._current_size >= self.max_file_size:
            self._rotate_file()
        
        with open(self._current_file, "a") as f:
            f.write(event.to_json() + "\n")
            self._current_size += len(event.to_json()) + 1
    
    def append(self, event: 'AuditEvent') -> bool:
        try:
            self._write_event(event)
            return True
        except Exception as e:
            logger.error(f"Failed to write audit event: {e}")
            return False
    
    def query(self, tenant_id: Optional[str] = None, event_type: Optional[str] = None,
              actor_id: Optional[str] = None, start_time: Optional[datetime] = None,
              end_time: Optional[datetime] = None, severity: Optional[str] = None,
              limit: int = 100, offset: int = 0) -> List['AuditEvent']:
        # Simplified - in production would use indexed storage
        return []
    
    def get_by_id(self, event_id: str) -> Optional['AuditEvent']:
        return None
    
    def count(self, **kwargs) -> int:
        return 0
    
    def verify_integrity(self) -> Dict[str, Any]:
        return {"valid": True, "checked": 0, "note": "File-based storage not verified in-memory"}
    
    def export(self, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        return []


# =============================================================================
# Audit Logger
# =============================================================================

class AuditLogger:
    """High-level audit logger with automatic context injection."""
    
    def __init__(
        self,
        storage: AuditStorage,
        service_name: str = "swarm",
        default_tenant: str = "default",
    ):
        self.storage = storage
        self.service_name = service_name
        self.default_tenant = default_tenant
        self._tracing_context: Optional[Any] = None
        self._default_context: Dict[str, Any] = {}
    
    def set_tracing_context(self, tracing_context: Any) -> None:
        self._tracing_context = tracing_context
    
    def set_default_context(self, **context) -> None:
        self._default_context.update(context)
    
    def _get_trace_context(self) -> Dict[str, Any]:
        if self._tracing_context:
            span = getattr(self._tracing_context, 'current_span', None)
            if span:
                return {
                    "trace_id": span.trace_id,
                    "span_id": span.span_id,
                }
        return {}
    
    def log(
        self,
        event_type: AuditEventType,
        severity: AuditSeverity,
        action: str,
        outcome: str = "success",
        tenant_id: Optional[str] = None,
        actor_id: Optional[str] = None,
        actor_type: str = "user",
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        trace_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> 'AuditEvent':
        """Log an audit event."""
        
        # Build context
        trace_ctx = self._get_trace_context()
        
        # Add trace context to details before creating event
        final_details = details or {}
        if trace_ctx:
            final_details["trace_context"] = trace_ctx
        
        event = AuditEvent(
            event_type=event_type,
            severity=severity,
            timestamp=now_utc(),
            tenant_id=tenant_id or self.default_tenant,
            actor_id=actor_id or "system",
            actor_type=actor_type,
            action=action,
            outcome=outcome,
            resource_type=resource_type,
            resource_id=resource_id,
            details=final_details,
            ip_address=ip_address,
            user_agent=user_agent,
            trace_id=trace_id or trace_ctx.get("trace_id"),
            correlation_id=correlation_id,
        )
        
        self.storage.append(event)
        return event
    
    # Convenience methods
    def info(self, action: str, **kwargs) -> 'AuditEvent':
        return self.log(AuditEventType.CUSTOM, AuditSeverity.INFO, action, **kwargs)
    
    def warning(self, action: str, **kwargs) -> 'AuditEvent':
        return self.log(AuditEventType.CUSTOM, AuditSeverity.WARNING, action, **kwargs)
    
    def error(self, action: str, **kwargs) -> 'AuditEvent':
        return self.log(AuditEventType.CUSTOM, AuditSeverity.ERROR, action, outcome="failure", **kwargs)
    
    def critical(self, action: str, **kwargs) -> 'AuditEvent':
        return self.log(AuditEventType.CUSTOM, AuditSeverity.CRITICAL, action, outcome="failure", **kwargs)
    
    def log_access(self, resource_type: str, resource_id: str, outcome: str, **kwargs) -> 'AuditEvent':
        return self.log(
            AuditEventType.RESOURCE_ACCESSED,
            AuditSeverity.INFO,
            f"access_{resource_type}",
            outcome=outcome,
            resource_type=resource_type,
            resource_id=resource_id,
        )
    
    def log_change(self, resource_type: str, resource_id: str, action: str, outcome: str, **kwargs) -> 'AuditEvent':
        event_type_map = {
            "create": AuditEventType.RESOURCE_CREATED,
            "update": AuditEventType.RESOURCE_UPDATED,
            "delete": AuditEventType.RESOURCE_DELETED,
        }
        return self.log(
            event_type_map.get(action, AuditEventType.RESOURCE_UPDATED),
            AuditSeverity.INFO,
            action,
            outcome=outcome,
            resource_type=resource_type,
            resource_id=resource_id,
        )
    
    def log_auth(self, event_type: AuditEventType, outcome: str, actor_id: str, **kwargs) -> 'AuditEvent':
        return self.log(
            event_type,
            AuditSeverity.INFO if outcome == "success" else AuditSeverity.WARNING,
            event_type.value,
            outcome=outcome,
            actor_id=actor_id,
            actor_type="user",
        )
    
    def query(
        self,
        tenant_id: Optional[str] = None,
        event_type: Optional[str] = None,
        actor_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        severity: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List['AuditEvent']:
        return self.storage.query(
            tenant_id=tenant_id,
            event_type=event_type,
            actor_id=actor_id,
            start_time=start_time,
            end_time=end_time,
            severity=severity,
            limit=limit,
            offset=offset,
        )
    
    def verify_integrity(self) -> Dict[str, Any]:
        return self.storage.verify_integrity()
    
    def export(self, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        return self.storage.export(start_time, end_time)


# =============================================================================
# Audit Trail Manager
# =============================================================================

class AuditTrailManager:
    """High-level audit trail management."""
    
    def __init__(self, storage: AuditStorage, service_name: str = "swarm"):
        self.storage = storage
        self.logger = AuditLogger(storage)
        self.service_name = service_name
        self._lock = threading.RLock()
    
    def log_event(self, event: 'AuditEvent') -> 'AuditEvent':
        return self.storage.append(event)
    
    def get_events(
        self,
        tenant_id: Optional[str] = None,
        event_type: Optional[str] = None,
        actor_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        severity: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List['AuditEvent']:
        return self.storage.query(
            tenant_id=tenant_id,
            event_type=event_type,
            actor_id=actor_id,
            start_time=start_time,
            end_time=end_time,
            severity=severity,
            limit=limit,
            offset=0,
        )
    
    def verify_integrity(self) -> Dict[str, Any]:
        return self.storage.verify_integrity()
    
    def export(self, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        return self.storage.export(start_time, end_time)
    
    def get_stats(self) -> Dict[str, Any]:
        integrity = self.storage.verify_integrity()
        return {
            "service": self.service_name,
            "integrity": integrity,
        }


# =============================================================================
# Factory
# =============================================================================

def create_audit_trail(
    storage_type: str = "memory",
    service_name: str = "swarm",
    **kwargs,
) -> AuditTrailManager:
    """Create an audit trail manager."""
    if storage_type == "memory":
        storage = InMemoryAuditStorage()
    elif storage_type == "file":
        directory = kwargs.get("directory", "/var/log/audit")
        storage = FileAuditStorage(directory)
    else:
        raise ValueError(f"Unknown storage type: {storage_type}")
    
    return AuditTrailManager(storage, service_name)


def create_audit_logger(storage: AuditStorage, service_name: str = "swarm") -> AuditLogger:
    return AuditLogger(storage, service_name)

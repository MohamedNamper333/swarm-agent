"""Immutable Audit Log - Cryptographic chaining and anchoring."""

import asyncio
import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def uuidv7() -> str:
    return str(__import__('uuid').uuid4())


@dataclass
class AuditEvent:
    """Immutable audit event with cryptographic chaining."""
    event_id: str = field(default_factory=lambda: f"audit-{uuidv7()}")
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    event_type: str = ""
    actor: str = ""
    action: str = ""
    resource: str = ""
    resource_id: str = ""
    outcome: str = "success"
    details: Dict[str, Any] = field(default_factory=dict)
    
    previous_hash: str = ""
    current_hash: str = ""
    sequence_number: int = 0
    
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    correlation_id: Optional[str] = None
    trace_id: Optional[str] = None


class AuditLog:
    """Immutable audit log with cryptographic chaining."""
    
    def __init__(self, log_name: str = "swarm-audit"):
        self.log_name = log_name
        self._events: List[AuditEvent] = []
        self._last_hash: str = "0" * 64
        self._sequence: int = 0
        self._lock = asyncio.Lock()
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
        """Append an event with cryptographic chaining."""
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
        """Verify chain integrity."""
        errors = []
        expected_hash = "0" * 64
        end = end or len(self._events)
        
        for i, event in enumerate(self._events[start:end], start=start):
            if event.sequence_number != i + 1:
                errors.append(f"Event {event.event_id}: sequence mismatch")
            
            if event.previous_hash != expected_hash:
                errors.append(f"Event {event.event_id}: previous hash mismatch")
            
            calculated = self._calculate_hash(event)
            if event.current_hash != calculated:
                errors.append(f"Event {event.event_id}: current hash mismatch (TAMPERING)")
            
            expected_hash = event.current_hash
        
        return len(errors) == 0, errors
    
    def get_events(
        self,
        event_type: Optional[str] = None,
        actor: Optional[str] = None,
        limit: int = 1000,
    ) -> List[AuditEvent]:
        """Get events with filters."""
        events = self._events
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        if actor:
            events = [e for e in events if e.actor == actor]
        return events[-limit:]
    
    def get_last_hash(self) -> str:
        return self._last_hash
    
    async def anchor(self) -> Dict[str, Any]:
        """Anchor current hash for external verification."""
        anchor = {
            "timestamp": now_utc().isoformat(),
            "hash": self._last_hash,
            "sequence": self._sequence,
            "algorithm": "SHA-256",
            "log_name": self.log_name,
        }
        self._anchors.append(anchor)
        return anchor


class AuditLogManager:
    """Manages multiple audit logs."""
    
    def __init__(self):
        self._logs: Dict[str, AuditLog] = {}
        self._lock = asyncio.Lock()
    
    def get_log(self, name: str) -> AuditLog:
        if name not in self._logs:
            self._logs[name] = AuditLog(name)
        return self._logs[name]
    
    async def log(self, log_name: str, **kwargs) -> AuditEvent:
        log = self.get_log(log_name)
        return await log.append(**kwargs)
    
    def verify_all(self) -> Dict[str, Tuple[bool, List[str]]]:
        return {name: log.verify_chain() for name, log in self._logs.items()}


def create_audit_log(name: str = "swarm-audit") -> AuditLog:
    return AuditLog(name)


def create_audit_log_manager() -> AuditLogManager:
    return AuditLogManager()

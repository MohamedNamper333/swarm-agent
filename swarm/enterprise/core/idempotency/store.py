"""
Idempotency Store — deduplicate requests with same key+payload.

F-006: Missing Idempotency fix.
Supports Idempotency-Key header with request hashing.
"""
import hashlib
import json
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Any
from datetime import datetime, timezone
from enum import Enum


class IdempotencyStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CONFLICT = "conflict"


@dataclass
class IdempotencyRecord:
    """Record of an idempotent request."""
    key: str
    tenant_id: str
    request_hash: str
    execution_id: Optional[str]
    status: IdempotencyStatus
    response_reference: Optional[str]  # Reference to stored response
    created_at: datetime
    updated_at: datetime
    expires_at: datetime
    metadata: Dict = field(default_factory=dict)


class IdempotencyStore:
    """Thread-safe idempotency store with TTL cleanup."""

    DEFAULT_TTL_SECONDS = 24 * 60 * 60  # 24 hours

    def __init__(self, default_ttl_seconds: int = DEFAULT_TTL_SECONDS):
        self._records: Dict[str, IdempotencyRecord] = {}
        self._lock = threading.RLock()
        self._default_ttl = default_ttl_seconds

    def _hash_request(self, payload: Dict[str, Any]) -> str:
        """Create deterministic hash of request payload."""
        # Sort keys for deterministic serialization
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode()).hexdigest()[:32]

    def check_and_store(
        self,
        key: str,
        tenant_id: str,
        payload: Dict[str, Any],
        ttl_seconds: Optional[int] = None,
    ) -> tuple[Optional[IdempotencyRecord], bool]:
        """
        Check if key exists with same payload.
        Returns (existing_record, is_new).
        If new, creates pending record.
        If exists with same payload, returns existing.
        If exists with different payload, raises Conflict.
        """
        request_hash = self._hash_request(payload)
        now = datetime.now(timezone.utc)
        ttl = ttl_seconds or self._default_ttl
        expires_at = datetime.fromtimestamp(now.timestamp() + ttl, tz=timezone.utc)

        with self._lock:
            existing = self._records.get(key)
            if existing:
                if existing.request_hash != request_hash:
                    # Same key, different payload → conflict
                    conflict_record = IdempotencyRecord(
                        key=key,
                        tenant_id=tenant_id,
                        request_hash=request_hash,
                        execution_id=None,
                        status=IdempotencyStatus.CONFLICT,
                        response_reference=None,
                        created_at=now,
                        updated_at=now,
                        expires_at=expires_at,
                        metadata={"original_hash": existing.request_hash},
                    )
                    self._records[key] = conflict_record
                    raise ValueError(
                        f"Idempotency key conflict: key={key} has different payload. "
                        f"Original hash: {existing.request_hash[:16]}..., New hash: {request_hash[:16]}..."
                    )
                # Same key, same payload → return existing
                return existing, False

            # New key → create pending record
            record = IdempotencyRecord(
                key=key,
                tenant_id=tenant_id,
                request_hash=request_hash,
                execution_id=None,
                status=IdempotencyStatus.PENDING,
                response_reference=None,
                created_at=now,
                updated_at=now,
                expires_at=expires_at,
                metadata={},
            )
            self._records[key] = record
            return record, True

    def mark_completed(
        self,
        key: str,
        execution_id: str,
        response_reference: str,
    ) -> bool:
        """Mark idempotent request as completed with response reference."""
        with self._lock:
            record = self._records.get(key)
            if not record:
                return False
            if record.status != IdempotencyStatus.PENDING:
                return False

            record.execution_id = execution_id
            record.status = IdempotencyStatus.COMPLETED
            record.response_reference = response_reference
            record.updated_at = datetime.now(timezone.utc)
            return True

    def mark_failed(self, key: str, error: str) -> bool:
        """Mark idempotent request as failed."""
        with self._lock:
            record = self._records.get(key)
            if not record or record.status != IdempotencyStatus.PENDING:
                return False
            record.status = IdempotencyStatus.FAILED
            record.metadata["error"] = error
            record.updated_at = datetime.now(timezone.utc)
            return True

    def get(self, key: str) -> Optional[IdempotencyRecord]:
        """Get record by key."""
        with self._lock:
            return self._records.get(key)

    def cleanup_expired(self) -> int:
        """Remove expired records. Returns count removed."""
        now = datetime.now(timezone.utc)
        removed = 0
        with self._lock:
            expired_keys = [
                k for k, v in self._records.items()
                if v.expires_at <= now
            ]
            for k in expired_keys:
                del self._records[k]
                removed += 1
        return removed

    def get_stats(self) -> Dict[str, Any]:
        """Get store statistics."""
        with self._lock:
            status_counts = {}
            for record in self._records.values():
                status_counts[record.status.value] = status_counts.get(record.status.value, 0) + 1
            return {
                "total_records": len(self._records),
                "by_status": status_counts,
                "default_ttl_seconds": self._default_ttl,
            }


# Global instance
_idempotency_store: Optional[IdempotencyStore] = None
_store_lock = threading.Lock()


def get_idempotency_store() -> IdempotencyStore:
    global _idempotency_store
    with _store_lock:
        if _idempotency_store is None:
            _idempotency_store = IdempotencyStore()
        return _idempotency_store


__all__ = [
    "IdempotencyStatus",
    "IdempotencyRecord",
    "IdempotencyStore",
    "get_idempotency_store",
]
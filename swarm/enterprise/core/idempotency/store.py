"""
Idempotency Store — deduplicate requests with same key+payload.

F-006: Missing Idempotency fix.

Rewritten 2026-08-25 after institutional audit found:
- I1: records keyed by raw key only → cross-tenant collisions leaked
      responses between tenants.
- I2: expired records were never removed (cleanup_expired had no callers)
      and were still returned as live dedupe hits.
- I3: a crashed request left a PENDING record forever, blocking all retries.
- I4: a payload CONFLICT overwrote the original record, permanently
      poisoning the key for the original owner too.
- I5: FAILED records could never be retried with the same key.
- I6: mark_*/get APIs ignored tenant scoping.

Semantics now:
- Records are keyed by (tenant_id, key).
- Expired records are treated as absent and pruned lazily.
- PENDING records older than `pending_lease_seconds` may be taken over.
- FAILED records may be retried (a fresh PENDING replaces them).
- Payload conflicts raise ValueError WITHOUT mutating the stored record.
"""
import hashlib
import json
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, Optional, Tuple


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
    """Thread-safe idempotency store with tenant scoping, TTL expiry,
    pending-lease takeover and bounded memory."""

    DEFAULT_TTL_SECONDS = 24 * 60 * 60          # completed-record retention
    DEFAULT_PENDING_LEASE_SECONDS = 5 * 60      # stuck-PENDING takeover window
    LAZY_CLEANUP_THRESHOLD = 100_000            # prune when above this size

    def __init__(
        self,
        default_ttl_seconds: int = DEFAULT_TTL_SECONDS,
        pending_lease_seconds: int = DEFAULT_PENDING_LEASE_SECONDS,
    ):
        self._records: Dict[Tuple[str, str], IdempotencyRecord] = {}
        self._lock = threading.RLock()
        self._default_ttl = default_ttl_seconds
        self._pending_lease = pending_lease_seconds

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _hash_request(payload: Dict[str, Any]) -> str:
        """Create deterministic hash of request payload."""
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode()).hexdigest()[:32]

    @staticmethod
    def _scoped(tenant_id: Optional[str], key: str) -> Tuple[str, str]:
        return (tenant_id or "default", key)

    def _is_expired(self, record: IdempotencyRecord, now: datetime) -> bool:
        return record.expires_at <= now

    def _lease_expired(self, record: IdempotencyRecord, now: datetime) -> bool:
        """A PENDING record whose lease ran out is considered abandoned."""
        if record.status != IdempotencyStatus.PENDING:
            return False
        lease_end = record.updated_at + timedelta(seconds=self._pending_lease)
        return now > lease_end

    def _maybe_lazy_cleanup(self, now: datetime) -> None:
        """Bounded-memory guard; caller must hold the lock."""
        if len(self._records) <= self.LAZY_CLEANUP_THRESHOLD:
            return
        expired = [k for k, v in self._records.items() if v.expires_at <= now]
        for k in expired:
            del self._records[k]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check_and_store(
        self,
        key: str,
        tenant_id: str,
        payload: Dict[str, Any],
        ttl_seconds: Optional[int] = None,
    ) -> tuple[Optional[IdempotencyRecord], bool]:
        """
        Check if key exists with same payload (within one tenant).

        Returns (existing_record, is_new).
        - New key / expired / abandoned-lease / previously-FAILED → fresh
          PENDING record, is_new=True.
        - Live existing with same payload → (record, False).
        - Same key, different payload → ValueError; original record untouched.
        """
        request_hash = self._hash_request(payload)
        now = datetime.now(timezone.utc)
        ttl = ttl_seconds or self._default_ttl
        expires_at = datetime.fromtimestamp(now.timestamp() + ttl, tz=timezone.utc)
        scope = self._scoped(tenant_id, key)

        with self._lock:
            self._maybe_lazy_cleanup(now)

            existing = self._records.get(scope)

            if existing is not None and self._is_expired(existing, now):
                del self._records[scope]
                existing = None

            elif existing is not None and (
                self._lease_expired(existing, now)
                or existing.status == IdempotencyStatus.FAILED
                or existing.status == IdempotencyStatus.CONFLICT
            ):
                # Abandoned PENDING / FAILED / CONFLICT → retryable. A fresh
                # attempt replaces them (I3, I5).
                del self._records[scope]
                existing = None

            if existing is not None:
                if existing.request_hash != request_hash:
                    # I4 fix: report the conflict WITHOUT destroying the
                    # original owner's record.
                    raise ValueError(
                        f"Idempotency key conflict: key={key} has different payload. "
                        f"Original hash: {existing.request_hash[:16]}..., "
                        f"New hash: {request_hash[:16]}..."
                    )
                return existing, False

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
            self._records[scope] = record
            return record, True

    def mark_completed(
        self,
        key: str,
        execution_id: str,
        response_reference: str,
        tenant_id: Optional[str] = None,
    ) -> bool:
        """Mark idempotent request as completed with response reference."""
        scope = self._scoped(tenant_id, key)
        with self._lock:
            record = self._records.get(scope)
            if not record or record.status != IdempotencyStatus.PENDING:
                return False
            record.execution_id = execution_id
            record.status = IdempotencyStatus.COMPLETED
            record.response_reference = response_reference
            record.updated_at = datetime.now(timezone.utc)
            return True

    def mark_failed(
        self,
        key: str,
        error: str,
        tenant_id: Optional[str] = None,
    ) -> bool:
        """Mark idempotent request as failed."""
        scope = self._scoped(tenant_id, key)
        with self._lock:
            record = self._records.get(scope)
            if not record or record.status != IdempotencyStatus.PENDING:
                return False
            record.status = IdempotencyStatus.FAILED
            record.metadata["error"] = error
            record.updated_at = datetime.now(timezone.utc)
            return True

    def get(self, key: str, tenant_id: Optional[str] = None) -> Optional[IdempotencyRecord]:
        """Get live (non-expired) record by scoped key."""
        scope = self._scoped(tenant_id, key)
        now = datetime.now(timezone.utc)
        with self._lock:
            record = self._records.get(scope)
            if record is not None and self._is_expired(record, now):
                del self._records[scope]
                return None
            return record

    def cleanup_expired(self) -> int:
        """Remove expired records. Returns count removed."""
        now = datetime.now(timezone.utc)
        with self._lock:
            expired_keys = [
                k for k, v in self._records.items()
                if v.expires_at <= now
            ]
            for k in expired_keys:
                del self._records[k]
            return len(expired_keys)

    def get_stats(self) -> Dict[str, Any]:
        """Get store statistics."""
        with self._lock:
            status_counts: Dict[str, int] = {}
            for record in self._records.values():
                status_counts[record.status.value] = \
                    status_counts.get(record.status.value, 0) + 1
            return {
                "total_records": len(self._records),
                "by_status": status_counts,
                "default_ttl_seconds": self._default_ttl,
                "pending_lease_seconds": self._pending_lease,
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

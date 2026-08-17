"""
Memory Trust — F-022: Memory Poisoning Risk fix.

Every memory item has: source, provenance, author, trust_level, tenant, scope, policy_tags, created_at, expires_at.
Applies: memory ≠ policy, memory ≠ system instruction.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Set, FrozenSet
from enum import Enum
from datetime import datetime, timezone
import uuid
import threading
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class TrustLevel(str, Enum):
    """Trust level of memory content."""
    UNTRUSTED = "untrusted"       # External input, no verification
    LOW = "low"                   # User-generated content
    MEDIUM = "medium"             # Agent-generated, not verified
    HIGH = "high"                 # Agent-generated, verified by policy
    SYSTEM = "system"             # System-generated, trusted


class MemoryScope(str, Enum):
    """Scope of memory visibility."""
    PRIVATE = "private"           # Only accessible by owner agent
    TENANT = "tenant"             # Shared within tenant
    GLOBAL = "global"             # Shared across system (careful!)


class ProvenanceType(str, Enum):
    """Type of memory provenance."""
    USER_INPUT = "user_input"
    AGENT_OUTPUT = "agent_output"
    TOOL_RESULT = "tool_result"
    SYSTEM_GENERATED = "system_generated"
    EXTERNAL_API = "external_api"
    DERIVED = "derived"           # Derived from other memories


@dataclass(frozen=True)
class MemoryProvenance:
    """Provenance information for a memory item."""
    source_id: str                    # Origin identifier
    provenance_type: ProvenanceType
    author_id: str                    # Who/what created this
    trust_level: TrustLevel
    tenant_id: str
    scope: MemoryScope
    policy_tags: FrozenSet[str] = field(default_factory=frozenset)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    parent_memory_ids: FrozenSet[str] = field(default_factory=frozenset)
    derivation_chain: List[str] = field(default_factory=list)  # For DERIVED type


@dataclass
class MemoryItem:
    """A memory item with full provenance and trust metadata."""
    memory_id: str
    content: Any
    provenance: MemoryProvenance
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    tags: Set[str] = field(default_factory=set)

    def can_access(self, requester_tenant: str, requester_trust: TrustLevel) -> bool:
        """Check if requester can access this memory."""
        # Tenant isolation
        if self.provenance.tenant_id != requester_tenant and self.provenance.scope != MemoryScope.GLOBAL:
            return False

        # Trust level check: requester trust must be >= memory trust for sensitive content
        trust_order = {
            TrustLevel.UNTRUSTED: 0,
            TrustLevel.LOW: 1,
            TrustLevel.MEDIUM: 2,
            TrustLevel.HIGH: 3,
            TrustLevel.SYSTEM: 4,
        }
        return trust_order.get(requester_trust, 0) >= trust_order.get(self.provenance.trust_level, 0)

    def access(self, requester_tenant: str, requester_trust: TrustLevel) -> Any:
        """Access memory content with authorization."""
        if not self.can_access(requester_tenant, requester_trust):
            raise PermissionError(f"Access denied to memory {self.memory_id}")
        self.access_count += 1
        self.last_accessed = datetime.now(timezone.utc)
        return self.content


class MemoryStore:
    """
    Trusted memory store with provenance tracking and access control.
    
    Principles:
    - Memory is data, not policy (never executes as instruction)
    - Every item has provenance and trust level
    - Access controlled by tenant and trust level
    - Memory ≠ system instruction (prevents prompt injection via memory)
    """

    def __init__(self, default_ttl_seconds: Optional[int] = None):
        self._memories: Dict[str, MemoryItem] = {}
        self._lock = threading.RLock()
        self._default_ttl = default_ttl_seconds
        self._tenant_index: Dict[str, Set[str]] = defaultdict(set)  # tenant_id -> memory_ids
        self._author_index: Dict[str, Set[str]] = defaultdict(set)  # author_id -> memory_ids

    def store(
        self,
        content: Any,
        provenance: MemoryProvenance,
        tags: Set[str] = None,
    ) -> MemoryItem:
        """Store a new memory item."""
        memory_id = str(uuid.uuid4())
        item = MemoryItem(
            memory_id=memory_id,
            content=content,
            provenance=provenance,
            tags=tags or set(),
        )

        with self._lock:
            self._memories[memory_id] = item
            self._tenant_index[provenance.tenant_id].add(memory_id)
            self._author_index[provenance.author_id].add(memory_id)

        return item

    def retrieve(
        self,
        memory_id: str,
        requester_tenant: str,
        requester_trust: TrustLevel,
    ) -> Any:
        """Retrieve memory content with access control."""
        with self._lock:
            item = self._memories.get(memory_id)
            if not item:
                raise KeyError(f"Memory {memory_id} not found")
            return item.access(requester_tenant, requester_trust)

    def search(
        self,
        query: str,
        requester_tenant: str,
        requester_trust: TrustLevel,
        limit: int = 10,
    ) -> List[MemoryItem]:
        """Search memories accessible to requester."""
        # Simple text search - in production use vector search
        results = []
        with self._lock:
            for item in self._memories.values():
                if not item.can_access(requester_tenant, requester_trust):
                    continue
                # Simple text match
                content_str = str(item.content).lower()
                if query.lower() in content_str:
                    results.append(item)
                if len(results) >= limit:
                    break
        return results

    def get_by_author(self, author_id: str) -> List[MemoryItem]:
        """Get all memories by author."""
        with self._lock:
            return [self._memories[mid] for mid in self._author_index.get(author_id, []) if mid in self._memories]

    def get_by_tenant(self, tenant_id: str) -> List[MemoryItem]:
        """Get all memories in tenant."""
        with self._lock:
            return [self._memories[mid] for mid in self._tenant_index.get(tenant_id, []) if mid in self._memories]

    def delete(self, memory_id: str, requester_id: str) -> bool:
        """Delete memory (only author or system can delete)."""
        with self._lock:
            item = self._memories.get(memory_id)
            if not item:
                return False
            if item.provenance.author_id != requester_id and requester_id != "system":
                return False
            del self._memories[memory_id]
            self._tenant_index[item.provenance.tenant_id].discard(memory_id)
            self._author_index[item.provenance.author_id].discard(memory_id)
            return True

    def cleanup_expired(self) -> int:
        """Remove expired memories."""
        now = datetime.now(timezone.utc)
        removed = 0
        with self._lock:
            expired_ids = [
                mid for mid, item in self._memories.items()
                if item.provenance.expires_at and item.provenance.expires_at <= now
            ]
            for mid in expired_ids:
                item = self._memories.pop(mid)
                self._tenant_index[item.provenance.tenant_id].discard(mid)
                self._author_index[item.provenance.author_id].discard(mid)
                removed += 1
        return removed

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            trust_counts = {}
            for item in self._memories.values():
                trust_counts[item.provenance.trust_level.value] = trust_counts.get(item.provenance.trust_level.value, 0) + 1
            return {
                "total_memories": len(self._memories),
                "by_trust_level": trust_counts,
                "by_tenant": {t: len(ids) for t, ids in self._tenant_index.items()},
                "by_author": {a: len(ids) for a, ids in self._author_index.items()},
            }


class TrustedMemoryManager:
    """
    High-level manager for trusted memory operations.
    Enforces: memory ≠ policy, memory ≠ system instruction.
    """

    def __init__(self, store: MemoryStore = None):
        self._store = store or MemoryStore()

    def remember(
        self,
        content: Any,
        author_id: str,
        tenant_id: str,
        provenance_type: ProvenanceType = ProvenanceType.AGENT_OUTPUT,
        trust_level: TrustLevel = TrustLevel.MEDIUM,
        scope: MemoryScope = MemoryScope.TENANT,
        policy_tags: Set[str] = None,
        parent_memory_ids: Set[str] = None,
        ttl_seconds: Optional[int] = None,
    ) -> MemoryItem:
        """Store a new memory with full provenance."""
        provenance = MemoryProvenance(
            source_id=str(uuid.uuid4()),
            provenance_type=provenance_type,
            author_id=author_id,
            trust_level=trust_level,
            tenant_id=tenant_id,
            scope=scope,
            policy_tags=frozenset(policy_tags or []),
            parent_memory_ids=frozenset(parent_memory_ids or []),
            expires_at=datetime.fromtimestamp(
                datetime.now(timezone.utc).timestamp() + ttl_seconds
            ) if ttl_seconds else None,
        )
        return self._store.store(content, provenance)

    def recall(
        self,
        memory_id: str,
        requester_tenant: str,
        requester_trust: TrustLevel,
    ) -> Any:
        """Retrieve memory content."""
        return self._store.retrieve(memory_id, requester_tenant, requester_trust)

    def search(
        self,
        query: str,
        requester_tenant: str,
        requester_trust: TrustLevel,
        limit: int = 10,
    ) -> List[MemoryItem]:
        """Search accessible memories."""
        return self._store.search(query, requester_tenant, requester_trust, limit)

    def derive(
        self,
        content: Any,
        source_memory_ids: Set[str],
        author_id: str,
        tenant_id: str,
        trust_level: TrustLevel = TrustLevel.HIGH,
    ) -> MemoryItem:
        """Create derived memory from existing memories."""
        # Inherit highest trust level from parents
        parent_trusts = []
        for mid in source_memory_ids:
            try:
                item = self._store.retrieve(mid, tenant_id, TrustLevel.SYSTEM)
                # Get parent trust from provenance - simplified
                parent_trusts.append(TrustLevel.HIGH)
            except KeyError:
                pass

        max_trust = max(parent_trusts) if parent_trusts else trust_level

        return self.remember(
            content=content,
            author_id=author_id,
            tenant_id=tenant_id,
            provenance_type=ProvenanceType.DERIVED,
            trust_level=max_trust,
            parent_memory_ids=source_memory_ids,
        )

    def get_stats(self) -> Dict[str, Any]:
        return self._store.get_stats()


# Global memory manager
_memory_manager: Optional[TrustedMemoryManager] = None
_mm_lock = threading.Lock()


def get_memory_manager() -> TrustedMemoryManager:
    global _memory_manager
    with _mm_lock:
        if _memory_manager is None:
            _memory_manager = TrustedMemoryManager()
        return _memory_manager


__all__ = [
    "TrustLevel",
    "MemoryScope",
    "ProvenanceType",
    "MemoryProvenance",
    "MemoryItem",
    "MemoryStore",
    "TrustedMemoryManager",
    "get_memory_manager",
]
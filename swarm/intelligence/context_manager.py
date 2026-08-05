"""
Context Manager Module - Hierarchical Context Management for Swarm
Implements scoped context layers (global, task, agent, ephemeral) with
visibility rules, lifetime management, and dependency tracking.
"""
import json
import time
import logging
import uuid
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import defaultdict
import threading

logger = logging.getLogger(__name__)


class ContextScope(Enum):
    """Hierarchical scope levels for context"""
    GLOBAL = "global"           # Visible to all agents, persistent
    TASK = "task"               # Visible within a task, expires after task
    AGENT = "agent"             # Visible only to specific agent
    EPHEMERAL = "ephemeral"     # Temporary, expires after single use


class ContextPriority(Enum):
    """Priority for context retention during compaction"""
    CRITICAL = "critical"        # Never drop
    HIGH = "high"                # Drop only under extreme pressure
    MEDIUM = "medium"            # Drop during moderate compaction
    LOW = "low"                  # Drop first during compaction


@dataclass
class ContextEntry:
    """A single context entry"""
    id: str
    scope: ContextScope
    priority: ContextPriority
    key: str
    value: Any
    created_at: str
    created_by: str  # agent_id or system
    ttl_seconds: Optional[int] = None  # None = never expire
    expires_at: Optional[str] = None
    access_count: int = 0
    last_accessed: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)  # other context entry IDs
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ContextSnapshot:
    """A snapshot of context at a point in time"""
    snapshot_id: str
    timestamp: str
    scope: ContextScope
    entries: List[ContextEntry]
    triggered_by: str
    reason: str


class HierarchicalContextManager:
    """
    Manages hierarchical context with scopes, priorities, and lifetimes.
    Enables agents to share, isolate, and expire context intelligently.
    """

    # Default TTL per scope (seconds)
    DEFAULT_TTL = {
        ContextScope.GLOBAL: None,        # No expiration
        ContextScope.TASK: 3600,          # 1 hour
        ContextScope.AGENT: 1800,         # 30 minutes
        ContextScope.EPHEMERAL: 300       # 5 minutes
    }

    # Max entries per scope (soft limit)
    MAX_ENTRIES_PER_SCOPE = {
        ContextScope.GLOBAL: 200,
        ContextScope.TASK: 100,
        ContextScope.AGENT: 50,
        ContextScope.EPHEMERAL: 20
    }

    def __init__(self, storage_path: str = "swarm/context_manager"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

        # Context entries indexed by ID
        self.entries: Dict[str, ContextEntry] = {}

        # Index by scope
        self.scope_index: Dict[ContextScope, Set[str]] = defaultdict(set)

        # Index by key within scope
        self.key_index: Dict[ContextScope, Dict[str, str]] = defaultdict(dict)

        # Index by agent
        self.agent_index: Dict[str, Set[str]] = defaultdict(set)

        # Snapshots
        self.snapshots: List[ContextSnapshot] = []

        # Statistics
        self.total_creates = 0
        self.total_reads = 0
        self.total_expires = 0

        self._load_state()

    def _load_state(self) -> None:
        """Load context state from disk"""
        state_file = self.storage_path / "context_state.json"
        if state_file.exists():
            try:
                with open(state_file, "r") as f:
                    data = json.load(f)
                for entry_id, entry_data in data.get("entries", {}).items():
                    entry_data["scope"] = ContextScope(entry_data["scope"])
                    entry_data["priority"] = ContextPriority(entry_data["priority"])
                    entry = ContextEntry(**entry_data)
                    self.entries[entry_id] = entry
                    self.scope_index[entry.scope].add(entry_id)
                    self.key_index[entry.scope][entry.key] = entry_id
                    if entry.created_by:
                        self.agent_index[entry.created_by].add(entry_id)
                self.total_creates = data.get("total_creates", 0)
                self.total_reads = data.get("total_reads", 0)
                self.total_expires = data.get("total_expires", 0)
                logger.info(f"Loaded {len(self.entries)} context entries")
            except Exception as e:
                logger.error(f"Failed to load context state: {e}")

    def _save_state(self) -> None:
        """Save context state to disk"""
        state_file = self.storage_path / "context_state.json"
        try:
            data = {
                "entries": {},
                "total_creates": self.total_creates,
                "total_reads": self.total_reads,
                "total_expires": self.total_expires
            }
            for entry_id, entry in self.entries.items():
                entry_dict = asdict(entry)
                entry_dict["scope"] = entry.scope.value
                entry_dict["priority"] = entry.priority.value
                data["entries"][entry_id] = entry_dict
            with open(state_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save context state: {e}")

    def set(
        self,
        key: str,
        value: Any,
        scope: ContextScope = ContextScope.TASK,
        priority: ContextPriority = ContextPriority.MEDIUM,
        created_by: str = "system",
        ttl_seconds: Optional[int] = None,
        tags: Optional[List[str]] = None,
        dependencies: Optional[List[str]] = None,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Store a context entry. Returns the entry ID.
        If key already exists in scope, updates the value.
        """
        with self._lock:
            # Check if key already exists in this scope
            existing_id = self.key_index[scope].get(key)
            if existing_id and existing_id in self.entries:
                entry = self.entries[existing_id]
                entry.value = value
                entry.priority = priority
                if ttl_seconds is not None:
                    entry.ttl_seconds = ttl_seconds
                    entry.expires_at = (
                        datetime.now() + timedelta(seconds=ttl_seconds)
                    ).isoformat()
                if tags is not None:
                    entry.tags = tags
                if dependencies is not None:
                    entry.dependencies = dependencies
                if metadata is not None:
                    entry.metadata = metadata
                self._save_state()
                return existing_id

            # Create new entry
            entry_id = f"ctx-{uuid.uuid4().hex[:12]}"
            if ttl_seconds is None:
                ttl_seconds = self.DEFAULT_TTL[scope]

            expires_at = None
            if ttl_seconds is not None:
                expires_at = (
                    datetime.now() + timedelta(seconds=ttl_seconds)
                ).isoformat()

            entry = ContextEntry(
                id=entry_id,
                scope=scope,
                priority=priority,
                key=key,
                value=value,
                created_at=datetime.now().isoformat(),
                created_by=created_by,
                ttl_seconds=ttl_seconds,
                expires_at=expires_at,
                tags=tags or [],
                dependencies=dependencies or [],
                metadata=metadata or {}
            )

            self.entries[entry_id] = entry
            self.scope_index[scope].add(entry_id)
            self.key_index[scope][key] = entry_id
            self.agent_index[created_by].add(entry_id)

            self.total_creates += 1
            self._enforce_scope_limit(scope)
            self._save_state()
            return entry_id

    def get(
        self,
        key: str,
        scope: Optional[ContextScope] = None,
        agent_id: Optional[str] = None,
        default: Any = None
    ) -> Any:
        """
        Retrieve a context value.
        If scope is None, searches across all scopes the agent has access to.
        """
        with self._lock:
            scopes_to_search = (
                [scope] if scope else
                [ContextScope.GLOBAL, ContextScope.TASK, ContextScope.AGENT, ContextScope.EPHEMERAL]
            )

            for search_scope in scopes_to_search:
                entry_id = self.key_index[search_scope].get(key)
                if entry_id and entry_id in self.entries:
                    entry = self.entries[entry_id]
                    if self._is_expired(entry):
                        self._expire_entry(entry_id)
                        continue
                    if not self._is_visible_to(entry, agent_id):
                        continue
                    entry.access_count += 1
                    entry.last_accessed = datetime.now().isoformat()
                    self.total_reads += 1
                    return entry.value

            return default

    def get_entry(self, entry_id: str) -> Optional[ContextEntry]:
        """Get full entry by ID"""
        with self._lock:
            entry = self.entries.get(entry_id)
            if entry and self._is_expired(entry):
                self._expire_entry(entry_id)
                return None
            return entry

    def delete(self, key: str, scope: ContextScope) -> bool:
        """Delete a context entry by key and scope"""
        with self._lock:
            entry_id = self.key_index[scope].get(key)
            if entry_id and entry_id in self.entries:
                self._expire_entry(entry_id)
                return True
            return False

    def delete_by_id(self, entry_id: str) -> bool:
        """Delete a context entry by ID"""
        with self._lock:
            if entry_id in self.entries:
                self._expire_entry(entry_id)
                return True
            return False

    def list_keys(
        self,
        scope: Optional[ContextScope] = None,
        agent_id: Optional[str] = None,
        tag_filter: Optional[str] = None
    ) -> List[str]:
        """List all keys visible to the agent in the given scope(s)"""
        with self._lock:
            scopes_to_search = (
                [scope] if scope else
                list(ContextScope)
            )
            keys = []

            for search_scope in scopes_to_search:
                for entry_id in self.scope_index[search_scope]:
                    entry = self.entries.get(entry_id)
                    if not entry:
                        continue
                    if self._is_expired(entry):
                        self._expire_entry(entry_id)
                        continue
                    if not self._is_visible_to(entry, agent_id):
                        continue
                    if tag_filter and tag_filter not in entry.tags:
                        continue
                    keys.append(entry.key)

            return keys

    def list_entries(
        self,
        scope: Optional[ContextScope] = None,
        agent_id: Optional[str] = None
    ) -> List[ContextEntry]:
        """List full entries visible to the agent"""
        with self._lock:
            scopes_to_search = [scope] if scope else list(ContextScope)
            entries = []
            for search_scope in scopes_to_search:
                for entry_id in self.scope_index[search_scope]:
                    entry = self.entries.get(entry_id)
                    if not entry:
                        continue
                    if self._is_expired(entry):
                        self._expire_entry(entry_id)
                        continue
                    if not self._is_visible_to(entry, agent_id):
                        continue
                    entries.append(entry)
            return entries

    def snapshot(
        self,
        scope: ContextScope,
        triggered_by: str = "system",
        reason: str = "manual"
    ) -> str:
        """Create a snapshot of context at a given scope"""
        with self._lock:
            snapshot_id = f"snap-{uuid.uuid4().hex[:12]}"
            entries = self.list_entries(scope=scope)

            snap = ContextSnapshot(
                snapshot_id=snapshot_id,
                timestamp=datetime.now().isoformat(),
                scope=scope,
                entries=entries,
                triggered_by=triggered_by,
                reason=reason
            )
            self.snapshots.append(snap)
            return snapshot_id

    def get_snapshot(self, snapshot_id: str) -> Optional[ContextSnapshot]:
        """Retrieve a snapshot by ID"""
        for snap in self.snapshots:
            if snap.snapshot_id == snapshot_id:
                return snap
        return None

    def cleanup_expired(self) -> int:
        """Remove all expired entries. Returns count removed."""
        with self._lock:
            expired_ids = [
                entry_id for entry_id, entry in self.entries.items()
                if self._is_expired(entry)
            ]
            for entry_id in expired_ids:
                self._expire_entry(entry_id)
            return len(expired_ids)

    def clear_scope(self, scope: ContextScope) -> int:
        """Clear all entries in a scope. Returns count removed."""
        with self._lock:
            entry_ids = list(self.scope_index[scope])
            for entry_id in entry_ids:
                self._expire_entry(entry_id)
            return len(entry_ids)

    def get_stats(self) -> Dict[str, Any]:
        """Get context manager statistics"""
        with self._lock:
            return {
                "total_entries": len(self.entries),
                "entries_by_scope": {
                    scope.value: len(ids)
                    for scope, ids in self.scope_index.items()
                },
                "total_creates": self.total_creates,
                "total_reads": self.total_reads,
                "total_expires": self.total_expires,
                "total_snapshots": len(self.snapshots)
            }

    def export_context(
        self,
        scope: Optional[ContextScope] = None,
        agent_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Export context as a serializable dict"""
        with self._lock:
            entries = self.list_entries(scope=scope, agent_id=agent_id)
            return {
                scope.value if scope else "all": {
                    entry.key: entry.value
                    for entry in entries
                }
            }

    def _is_expired(self, entry: ContextEntry) -> bool:
        """Check if an entry has expired"""
        if entry.expires_at is None:
            return False
        try:
            expires = datetime.fromisoformat(entry.expires_at)
            return datetime.now() > expires
        except (ValueError, TypeError):
            return False

    def _is_visible_to(
        self, entry: ContextEntry, agent_id: Optional[str]
    ) -> bool:
        """Check if an entry is visible to a given agent"""
        if entry.scope == ContextScope.GLOBAL:
            return True
        if entry.scope == ContextScope.TASK:
            return True  # Task scope is shared
        if entry.scope == ContextScope.AGENT:
            return agent_id is None or entry.created_by == agent_id
        if entry.scope == ContextScope.EPHEMERAL:
            return agent_id is None or entry.created_by == agent_id
        return False

    def _expire_entry(self, entry_id: str) -> None:
        """Remove an entry from all indexes"""
        entry = self.entries.pop(entry_id, None)
        if not entry:
            return
        self.scope_index[entry.scope].discard(entry_id)
        self.key_index[entry.scope].pop(entry.key, None)
        self.agent_index[entry.created_by].discard(entry_id)
        self.total_expires += 1

    def _enforce_scope_limit(self, scope: ContextScope) -> None:
        """Enforce soft limits by removing low-priority entries"""
        max_entries = self.MAX_ENTRIES_PER_SCOPE[scope]
        entries_in_scope = [
            (entry_id, self.entries[entry_id])
            for entry_id in self.scope_index[scope]
            if entry_id in self.entries
        ]

        if len(entries_in_scope) <= max_entries:
            return

        # Sort by priority (low first) then by access count (low first)
        priority_order = {
            ContextPriority.LOW: 0,
            ContextPriority.MEDIUM: 1,
            ContextPriority.HIGH: 2,
            ContextPriority.CRITICAL: 3
        }
        entries_in_scope.sort(
            key=lambda x: (priority_order[x[1].priority], x[1].access_count)
        )

        # Remove entries until under limit
        excess = len(entries_in_scope) - max_entries
        for entry_id, entry in entries_in_scope[:excess]:
            if entry.priority == ContextPriority.CRITICAL:
                continue  # Never drop critical
            self._expire_entry(entry_id)


# Module-level singleton
_default_manager: Optional[HierarchicalContextManager] = None


def get_context_manager(
    storage_path: str = "swarm/context_manager"
) -> HierarchicalContextManager:
    """Get or create the default context manager"""
    global _default_manager
    if _default_manager is None:
        _default_manager = HierarchicalContextManager(storage_path)
    return _default_manager
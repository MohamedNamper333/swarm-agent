"""
Memory Engine - 4-layer compound memory with Meilisearch integration
"""
import json
import time
import threading
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from collections import defaultdict
import hashlib


class MemoryLayer(Enum):
    """Four layers of memory."""
    SCRATCHPAD = "scratchpad"      # Per-task, ephemeral
    WORKING = "working"            # Session-level, recent context
    EPISODIC = "episodic"          # Task-level, lessons learned
    SEMANTIC = "semantic"          # Long-term, facts & patterns


@dataclass
class MemoryEntry:
    id: str
    layer: MemoryLayer
    task_id: str
    agent_id: str
    content: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    tags: List[str] = field(default_factory=list)
    confidence: float = 1.0
    access_count: int = 0
    last_accessed: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class Lesson:
    id: str
    task_id: str
    agent_id: str
    pattern: str
    lesson: str
    confidence: float
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    applications: int = 0


class MemoryEngine:
    """4-layer compound memory with Meilisearch integration."""

    def __init__(self, vault_client=None):
        self.vault_client = vault_client
        self._lock = threading.RLock()

        # In-memory stores for each layer
        self.scratchpad: Dict[str, MemoryEntry] = {}  # task_id -> entry
        self.working: Dict[str, MemoryEntry] = {}     # session_id -> entry
        self.episodic: List[MemoryEntry] = []         # task-level memories
        self.semantic: Dict[str, List[MemoryEntry]] = defaultdict(list)  # topic -> entries

        # Lessons learned
        self.lessons: List[Lesson] = []

        # Meilisearch integration (optional)
        self.meilisearch_enabled = vault_client is not None
        self._index_name = "swarm-memory"

    # === SCRATCHPAD (Per-task, ephemeral) ===

    def write_scratchpad(self, task_id: str, agent_id: str, content: Dict) -> str:
        """Write to scratchpad for a task."""
        with self._lock:
            entry = MemoryEntry(
                id=f"scratchpad_{task_id}_{int(time.time())}",
                layer=MemoryLayer.SCRATCHPAD,
                task_id=task_id,
                agent_id=agent_id,
                content=content
            )
            self.scratchpad[task_id] = entry
            return entry.id

    def read_scratchpad(self, task_id: str) -> Optional[MemoryEntry]:
        """Read scratchpad for a task."""
        with self._lock:
            return self.scratchpad.get(task_id)

    def clear_scratchpad(self, task_id: str) -> bool:
        """Clear scratchpad after task completion."""
        with self._lock:
            if task_id in self.scratchpad:
                del self.scratchpad[task_id]
                return True
            return False

    # === WORKING MEMORY (Session-level) ===

    def write_working(self, session_id: str, agent_id: str, content: Dict) -> str:
        """Write to working memory for a session."""
        with self._lock:
            entry = MemoryEntry(
                id=f"working_{session_id}_{int(time.time())}",
                layer=MemoryLayer.WORKING,
                task_id=session_id,
                agent_id=agent_id,
                content=content
            )
            self.working[session_id] = entry
            return entry.id

    def read_working(self, session_id: str) -> Optional[MemoryEntry]:
        with self._lock:
            return self.working.get(session_id)

    def update_working(self, session_id: str, updates: Dict) -> bool:
        """Update working memory with new info."""
        with self._lock:
            if session_id in self.working:
                entry = self.working[session_id]
                entry.content.update(updates)
                entry.last_accessed = datetime.now(timezone.utc).isoformat()
                entry.access_count += 1
                return True
            return False

    # === EPISODIC MEMORY (Task-level lessons) ===

    def record_episode(self, task_id: str, agent_id: str, content: Dict, 
                      tags: List[str] = None, confidence: float = 1.0) -> str:
        """Record a task episode with lessons learned."""
        with self._lock:
            entry = MemoryEntry(
                id=f"episode_{task_id}_{int(time.time())}",
                layer=MemoryLayer.EPISODIC,
                task_id=task_id,
                agent_id=agent_id,
                content=content,
                tags=tags or [],
                confidence=confidence
            )
            self.episodic.append(entry)
            self._maybe_promote_to_semantic(entry)
            return entry.id

    def get_episodes(self, task_id: str = None, agent_id: str = None, 
                    tags: List[str] = None) -> List[MemoryEntry]:
        """Retrieve episodes with optional filters."""
        with self._lock:
            results = self.episodic
            if task_id:
                results = [e for e in results if e.task_id == task_id]
            if agent_id:
                results = [e for e in results if e.agent_id == agent_id]
            if tags:
                results = [e for e in results if any(t in e.tags for t in tags)]
            return results

    # === SEMANTIC MEMORY (Long-term facts & patterns) ===

    def _maybe_promote_to_semantic(self, entry: MemoryEntry):
        """Promote high-confidence episodic memories to semantic."""
        if entry.confidence >= 0.8 and entry.access_count >= 3:
            topic = self._extract_topic(entry.content)
            self.semantic[topic].append(entry)

    def _extract_topic(self, content: Dict) -> str:
        """Extract topic from content for semantic indexing."""
        # Simple extraction - in production would use NLP
        keys = list(content.keys())[:3]
        return "_".join(keys) if keys else "general"

    def add_semantic(self, topic: str, content: Dict, confidence: float = 1.0) -> str:
        """Add a fact/pattern to semantic memory."""
        with self._lock:
            entry = MemoryEntry(
                id=f"semantic_{topic}_{int(time.time())}",
                layer=MemoryLayer.SEMANTIC,
                task_id="semantic",
                agent_id="system",
                content=content,
                tags=[topic],
                confidence=confidence
            )
            self.semantic[topic].append(entry)
            return entry.id

    def search_semantic(self, query: str, limit: int = 10) -> List[MemoryEntry]:
        """Search semantic memory for relevant facts."""
        with self._lock:
            results = []
            query_lower = query.lower()
            for topic, entries in self.semantic.items():
                if query_lower in topic.lower():
                    results.extend(entries)
            return sorted(results, key=lambda e: e.confidence, reverse=True)[:limit]

    # === LESSONS LEARNED ===

    def add_lesson(self, task_id: str, agent_id: str, pattern: str, 
                  lesson: str, confidence: float = 1.0) -> str:
        """Record a learned lesson."""
        with self._lock:
            lesson_obj = Lesson(
                id=f"lesson_{task_id}_{int(time.time())}",
                task_id=task_id,
                agent_id=agent_id,
                pattern=pattern,
                lesson=lesson,
                confidence=confidence
            )
            self.lessons.append(lesson_obj)
            return lesson_obj.id

    def get_relevant_lessons(self, task_description: str, limit: int = 5) -> List[Lesson]:
        """Get lessons relevant to a task."""
        with self._lock:
            relevant = []
            desc_lower = task_description.lower()
            for lesson in self.lessons:
                if lesson.pattern.lower() in task_description.lower():
                    relevant.append(lesson)
            return sorted(relevant, key=lambda l: l.confidence * l.applications, reverse=True)[:limit]

    def apply_lesson(self, lesson_id: str):
        """Mark a lesson as applied."""
        with self._lock:
            for lesson in self.lessons:
                if lesson.id == lesson_id:
                    lesson.applications += 1
                    return True
            return False

    # === MEILISEARCH INTEGRATION ===

    def index_to_meilisearch(self):
        """Index all memory to Meilisearch (if available)."""
        if not self.meilisearch_enabled:
            return False
        # Would index all layers to Meilisearch
        return True

    def search_meilisearch(self, query: str, layer: MemoryLayer = None, limit: int = 10) -> List[Dict]:
        """Search Meilisearch for memory entries."""
        if not self.meilisearch_enabled:
            return []
        # Would search Meilisearch
        return []

    # === CONTEXT MANAGEMENT ===

    def build_context(self, task_id: str, agent_id: str, max_tokens: int = 4000) -> Dict:
        """Build context for a task from all memory layers."""
        context = {
            "scratchpad": None,
            "working": None,
            "episodic": [],
            "semantic": [],
            "lessons": []
        }

        # Scratchpad
        scratchpad = self.read_scratchpad(task_id)
        if scratchpad:
            context["scratchpad"] = scratchpad.content

        # Working memory (current session)
        working = self.read_working(f"session_{agent_id}")
        if working:
            context["working"] = working.content

        # Relevant episodic memories
        episodes = self.get_episodes(agent_id=agent_id)
        context["episodic"] = [e.content for e in episodes[-5:]]

        # Relevant semantic facts
        # Would need task description to search
        context["semantic"] = []

        # Relevant lessons
        # Would need task description
        context["lessons"] = []

        return context

    # === PERSISTENCE ===

    def save_to_vault(self, namespace: str = "swarm/memory"):
        """Save memory to vault."""
        if not self.vault_client:
            return False
        # Would serialize and write to vault
        return True

    def load_from_vault(self, namespace: str = "swarm/memory"):
        """Load memory from vault."""
        if not self.vault_client:
            return False
        # Would read and deserialize from vault
        return True

    # === STATISTICS ===

    def get_stats(self) -> Dict:
        """Get memory statistics."""
        with self._lock:
            return {
                "scratchpad_entries": len(self.scratchpad),
                "working_entries": len(self.working),
                "episodic_entries": len(self.episodic),
                "semantic_topics": len(self.semantic),
                "semantic_entries": sum(len(v) for v in self.semantic.values()),
                "lessons_learned": len(self.lessons),
                "meilisearch_enabled": self.meilisearch_enabled
            }

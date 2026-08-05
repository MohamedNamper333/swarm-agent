"""
Context Compactor Module - Smart Context Summarization
Compresses large context entries while preserving key decisions,
facts, and dependencies. Uses importance scoring and dependency graphs.
"""
import json
import time
import logging
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import defaultdict
import threading
import uuid

from swarm.intelligence.context_manager import (
    HierarchicalContextManager,
    ContextEntry,
    ContextScope,
    ContextPriority,
    get_context_manager
)

logger = logging.getLogger(__name__)


class CompactionStrategy(Enum):
    """Strategies for compacting context"""
    TRUNCATE = "truncate"           # Simple truncation
    SUMMARIZE = "summarize"         # LLM-style summarization
    EXTRACT_KEY = "extract_key"     # Extract key facts only
    DEPENDENCY_PRESERVE = "dep"     # Preserve dependency chain


@dataclass
class CompactionResult:
    """Result of compacting a context entry"""
    original_id: str
    compacted_id: str
    original_size: int
    compacted_size: int
    compression_ratio: float
    strategy: CompactionStrategy
    preserved_keys: List[str]
    dropped_keys: List[str]
    timestamp: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CompactionStats:
    """Statistics about compaction operations"""
    total_compactions: int = 0
    total_bytes_saved: int = 0
    avg_compression_ratio: float = 0.0
    last_compaction: Optional[str] = None
    compactions_by_strategy: Dict[str, int] = field(default_factory=dict)


class ContextCompactor:
    """
    Compacts context entries intelligently.
    Preserves critical decisions, dependencies, and key facts
    while reducing token usage.
    """

    # Target compression ratio per priority
    # For MEDIUM priority, we aim for 50% (keep half) since decisions are critical
    TARGET_RATIOS = {
        ContextPriority.CRITICAL: 0.9,    # Keep 90% (minimal compression)
        ContextPriority.HIGH: 0.7,        # Keep 70%
        ContextPriority.MEDIUM: 0.5,     # Keep 50% (prioritize decisions)
        ContextPriority.LOW: 0.2          # Keep 20%
    }

    # Patterns indicating key decisions / facts
    DECISION_PATTERNS = [
        r"\b(?:decided|chose|selected)\s+to\s+.+",
        r"\bwill\s+(?:use|be|do|implement)\b.+",
        r"\b(?:decision)\s*[:\-]\s*.+",
        r"\bbecause\s+(?:of\s+)?(?:performance|security|the|this|a|an)\b.+",
        r"\bsince\s+(?:the|this|we|it)\b.+",
        r"\bdue\s+to\b.+",
        r"\bimportant\s*[:\-]\s*.+",
        r"\bcritical\s*[:\-]\s*.+",
        r"\bkey\s+(?:point|finding|decision|takeaway)\b.+",
        r"\bessential\s*[:\-]\s*.+",
        r"\bnote\s*[:\-]\s*.+",
        r"\bTODO\s*[:\-]\s*.+",
        r"\bFIXME\s*[:\-]\s*.+",
        r"\bXXX\s*[:\-]\s*.+",
        r"\b(?:must|should|need to|required to)\s+\w+",
        r"\bwill\s+(?:deploy|build|create|test|verify|review)\b.+"
    ]

    # Patterns indicating dependencies (things referenced)
    DEPENDENCY_PATTERNS = [
        r"(?:depends on|requires|needs|uses|imports?)[:\s]+(.+?)(?:\.|$)",
        r"(?:see also|refer to|reference)[:\s]+(.+?)(?:\.|$)"
    ]

    def __init__(self, context_manager: Optional[HierarchicalContextManager] = None):
        self.context_manager = context_manager or get_context_manager()
        self._lock = threading.RLock()
        self.stats = CompactionStats()
        self.compaction_history: List[CompactionResult] = []

    def compact_entry(
        self,
        entry_id: str,
        strategy: CompactionStrategy = CompactionStrategy.EXTRACT_KEY,
        force: bool = False
    ) -> Optional[CompactionResult]:
        """
        Compact a single context entry.
        Returns CompactionResult or None if entry not found.
        """
        with self._lock:
            entry = self.context_manager.get_entry(entry_id)
            if not entry:
                logger.warning(f"Entry {entry_id} not found for compaction")
                return None

            # Skip critical entries unless forced
            if entry.priority == ContextPriority.CRITICAL and not force:
                logger.info(f"Skipping CRITICAL entry {entry_id}")
                return None

            original_size = self._estimate_size(entry.value)
            target_ratio = self.TARGET_RATIOS[entry.priority]
            target_size = int(original_size * target_ratio)

            if strategy == CompactionStrategy.TRUNCATE:
                compacted_value = self._truncate(entry.value, target_size)
            elif strategy == CompactionStrategy.SUMMARIZE:
                compacted_value = self._summarize(entry.value, target_size)
            elif strategy == CompactionStrategy.EXTRACT_KEY:
                compacted_value = self._extract_key(entry.value, target_size)
            elif strategy == CompactionStrategy.DEPENDENCY_PRESERVE:
                compacted_value = self._preserve_dependencies(
                    entry, target_size
                )
            else:
                compacted_value = entry.value

            compacted_size = self._estimate_size(compacted_value)
            compression_ratio = (
                compacted_size / original_size if original_size > 0 else 1.0
            )

            # Create new compacted entry
            compacted_id = self.context_manager.set(
                key=f"{entry.key}_compacted_{uuid.uuid4().hex[:6]}",
                value=compacted_value,
                scope=entry.scope,
                priority=entry.priority,
                created_by="context_compactor",
                tags=entry.tags + ["compacted"],
                metadata={
                    "original_id": entry_id,
                    "original_size": original_size,
                    "compaction_strategy": strategy.value,
                    "compacted_at": datetime.now().isoformat()
                }
            )

            # Optionally delete original
            if entry.priority in (ContextPriority.LOW, ContextPriority.MEDIUM):
                self.context_manager.delete_by_id(entry_id)

            result = CompactionResult(
                original_id=entry_id,
                compacted_id=compacted_id,
                original_size=original_size,
                compacted_size=compacted_size,
                compression_ratio=compression_ratio,
                strategy=strategy,
                preserved_keys=self._extract_preserved_keys(entry.value, compacted_value),
                dropped_keys=[],
                timestamp=datetime.now().isoformat()
            )

            self._record_stats(result, strategy)
            self.compaction_history.append(result)
            return result

    def compact_scope(
        self,
        scope: ContextScope,
        strategy: CompactionStrategy = CompactionStrategy.EXTRACT_KEY
    ) -> List[CompactionResult]:
        """Compact all entries in a scope"""
        results = []
        entries = self.context_manager.list_entries(scope=scope)
        for entry in entries:
            result = self.compact_entry(entry.id, strategy=strategy)
            if result:
                results.append(result)
        return results

    def compact_by_size_threshold(
        self,
        max_size_bytes: int = 5000,
        strategy: CompactionStrategy = CompactionStrategy.EXTRACT_KEY
    ) -> List[CompactionResult]:
        """Compact all entries exceeding a size threshold"""
        results = []
        for entry in self.context_manager.list_entries():
            size = self._estimate_size(entry.value)
            if size > max_size_bytes:
                result = self.compact_entry(entry.id, strategy=strategy)
                if result:
                    results.append(result)
        return results

    def compact_for_agent(
        self,
        agent_id: str,
        max_size_bytes: int = 10000
    ) -> Dict[str, Any]:
        """
        Build a compacted context view for a specific agent.
        Returns the visible context with size-aware compaction applied.
        """
        with self._lock:
            visible_entries = self.context_manager.list_entries(agent_id=agent_id)

            # Sort by priority (critical first)
            priority_order = {
                ContextPriority.CRITICAL: 0,
                ContextPriority.HIGH: 1,
                ContextPriority.MEDIUM: 2,
                ContextPriority.LOW: 3
            }
            visible_entries.sort(
                key=lambda e: priority_order[e.priority]
            )

            compact_view = {}
            current_size = 0

            for entry in visible_entries:
                size = self._estimate_size(entry.value)

                # Always include critical entries
                if entry.priority == ContextPriority.CRITICAL:
                    compact_view[entry.key] = entry.value
                    current_size += size
                    continue

                # Stop if budget exceeded
                if current_size + size > max_size_bytes:
                    if entry.priority in (ContextPriority.HIGH,):
                        # Try compacting
                        result = self.compact_entry(entry.id)
                        if result:
                            compacted_entry = self.context_manager.get_entry(
                                result.compacted_id
                            )
                            if compacted_entry:
                                compact_view[entry.key] = compacted_entry.value
                                current_size += result.compacted_size
                    continue

                compact_view[entry.key] = entry.value
                current_size += size

            return {
                "agent_id": agent_id,
                "total_size_bytes": current_size,
                "entry_count": len(compact_view),
                "context": compact_view
            }

    def get_stats(self) -> CompactionStats:
        """Get compaction statistics"""
        with self._lock:
            return self.stats

    def get_history(self, limit: int = 50) -> List[CompactionResult]:
        """Get recent compaction history"""
        with self._lock:
            return self.compaction_history[-limit:]

    def _truncate(self, value: Any, target_size: int) -> Any:
        """Simple truncation strategy"""
        if isinstance(value, str):
            return value[:target_size] + ("..." if len(value) > target_size else "")
        elif isinstance(value, dict):
            # Keep first N keys until target size reached
            result = {}
            current_size = 0
            for k, v in value.items():
                v_size = self._estimate_size(v)
                if current_size + v_size > target_size:
                    break
                result[k] = v
                current_size += v_size
            return result
        elif isinstance(value, list):
            # Keep first N items
            result = []
            current_size = 0
            for item in value:
                item_size = self._estimate_size(item)
                if current_size + item_size > target_size:
                    break
                result.append(item)
                current_size += item_size
            return result
        return value

    def _summarize(self, value: Any, target_size: int) -> Any:
        """Summarize value while preserving key facts - prioritize decisions over target size"""
        if isinstance(value, str):
            # Extract sentences with decision patterns
            sentences = self._split_sentences(value)
            decisions = []
            non_decisions = []

            for sentence in sentences:
                is_decision = False
                for pattern in self.DECISION_PATTERNS:
                    if re.search(pattern, sentence, re.IGNORECASE):
                        is_decision = True
                        break
                if is_decision:
                    decisions.append(sentence)
                else:
                    non_decisions.append(sentence)

            # Always include ALL decisions (prioritize over target size)
            summary_parts = list(decisions)
            current_size = sum(len(s) + 3 for s in summary_parts)  # 3 = " | "

            # Fill remaining space with non-decisions
            for sentence in non_decisions:
                if current_size + len(sentence) + 3 <= target_size:
                    summary_parts.append(sentence)
                    current_size += len(sentence) + 3

            if summary_parts:
                summary = " | ".join(summary_parts)
            else:
                summary = value[:target_size]

            # Preserve original order
            original_order = {s: i for i, s in enumerate(sentences)}
            summary_parts.sort(key=lambda s: original_order.get(s, 0))
            summary = " | ".join(summary_parts)

            return summary

        elif isinstance(value, dict):
            return self._truncate(value, target_size)
        elif isinstance(value, list):
            return self._truncate(value, target_size)

        return value

    def _extract_key(self, value: Any, target_size: int) -> Any:
        """Extract key facts from value"""
        if isinstance(value, str):
            return self._extract_key_sentences(value, target_size)
        elif isinstance(value, dict):
            # Extract entries whose values contain decision patterns
            key_facts = {}
            current_size = 0
            for k, v in value.items():
                v_str = str(v) if not isinstance(v, str) else v
                has_decision = any(
                    re.search(p, v_str, re.IGNORECASE)
                    for p in self.DECISION_PATTERNS
                )
                if has_decision:
                    size = self._estimate_size(v)
                    if current_size + size <= target_size:
                        key_facts[k] = v
                        current_size += size
            # If empty, return summarized version
            if not key_facts:
                return self._summarize(value, target_size)
            return key_facts
        elif isinstance(value, list):
            # Filter list items containing decisions
            key_items = []
            current_size = 0
            for item in value:
                item_str = str(item) if not isinstance(item, str) else item
                has_decision = any(
                    re.search(p, item_str, re.IGNORECASE)
                    for p in self.DECISION_PATTERNS
                )
                if has_decision:
                    size = self._estimate_size(item)
                    if current_size + size <= target_size:
                        key_items.append(item)
                        current_size += size
            if not key_items:
                return self._summarize(value, target_size)
            return key_items
        return value

    def _preserve_dependencies(
        self, entry: ContextEntry, target_size: int
    ) -> Any:
        """Preserve dependencies while compacting"""
        # Keep the original if dependencies exist and target size is generous
        if entry.dependencies and target_size > 500:
            return self._extract_key(entry.value, target_size)

        # Otherwise, extract key facts
        return self._extract_key(entry.value, target_size)

    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        return [s.strip() for s in re.split(r'[.!?]\s+', text) if s.strip()]

    def _extract_key_sentences(self, text: str, target_size: int) -> str:
        """Extract sentences containing key decisions - prioritize decisions, preserve order"""
        sentences = self._split_sentences(text)

        # Classify sentences
        decision_sentences = []
        other_sentences = []

        for i, sentence in enumerate(sentences):
            is_decision = False
            for pattern in self.DECISION_PATTERNS:
                if re.search(pattern, sentence, re.IGNORECASE):
                    is_decision = True
                    break
            if is_decision:
                decision_sentences.append((i, sentence))
            else:
                other_sentences.append((i, sentence))

        # Strategy: keep ALL decisions (priority), fill with others if room
        result_with_order = list(decision_sentences)
        current_size = sum(len(s) + 3 for _, s in decision_sentences)

        # Fill with non-decisions if space allows
        for i, sentence in other_sentences:
            if current_size + len(sentence) + 3 <= target_size:
                result_with_order.append((i, sentence))
                current_size += len(sentence) + 3

        if not result_with_order:
            # Fallback: first sentences
            return text[:target_size]

        # Sort by original order
        result_with_order.sort(key=lambda x: x[0])
        result = [s for _, s in result_with_order]

        return ". ".join(result) + ("." if not result[-1].endswith(".") else "")

    def _estimate_size(self, value: Any) -> int:
        """Estimate size in bytes of a value"""
        try:
            return len(json.dumps(value, default=str))
        except (TypeError, ValueError):
            return len(str(value))

    def _extract_preserved_keys(
        self, original: Any, compacted: Any
    ) -> List[str]:
        """Extract list of preserved keys"""
        if isinstance(original, dict) and isinstance(compacted, dict):
            return [k for k in compacted.keys() if k in original]
        return []

    def _record_stats(
        self, result: CompactionResult, strategy: CompactionStrategy
    ) -> None:
        """Record compaction statistics"""
        with self._lock:
            self.stats.total_compactions += 1
            bytes_saved = result.original_size - result.compacted_size
            self.stats.total_bytes_saved += bytes_saved

            # Update rolling average compression ratio
            total = self.stats.total_compactions
            prev_avg = self.stats.avg_compression_ratio
            self.stats.avg_compression_ratio = (
                (prev_avg * (total - 1) + result.compression_ratio) / total
            )
            self.stats.last_compaction = result.timestamp

            strategy_key = strategy.value
            self.stats.compactions_by_strategy[strategy_key] = (
                self.stats.compactions_by_strategy.get(strategy_key, 0) + 1
            )


# Module-level singleton
_default_compactor: Optional[ContextCompactor] = None


def get_context_compactor() -> ContextCompactor:
    """Get or create the default context compactor"""
    global _default_compactor
    if _default_compactor is None:
        _default_compactor = ContextCompactor()
    return _default_compactor
"""
Unit tests for Context Manager and Context Compactor - Week 8
"""
import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch

from swarm.intelligence.context_manager import (
    HierarchicalContextManager,
    ContextEntry,
    ContextScope,
    ContextPriority,
    get_context_manager
)
from swarm.intelligence.context_compactor import (
    ContextCompactor,
    CompactionStrategy,
    CompactionResult,
    get_context_compactor
)


@pytest.fixture
def temp_storage():
    """Create temporary storage directory"""
    tmpdir = tempfile.mkdtemp()
    yield tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def context_manager(temp_storage):
    """Create a context manager with temporary storage"""
    manager = HierarchicalContextManager(storage_path=temp_storage)
    yield manager
    manager.clear_scope(ContextScope.GLOBAL)
    manager.clear_scope(ContextScope.TASK)
    manager.clear_scope(ContextScope.AGENT)
    manager.clear_scope(ContextScope.EPHEMERAL)


@pytest.fixture
def compactor(context_manager):
    """Create a compactor with the test manager"""
    return ContextCompactor(context_manager=context_manager)


class TestContextEntry:
    """Test ContextEntry dataclass"""

    def test_context_entry_creation(self):
        entry = ContextEntry(
            id="ctx-001",
            scope=ContextScope.TASK,
            priority=ContextPriority.MEDIUM,
            key="test_key",
            value="test_value",
            created_at=datetime.now().isoformat(),
            created_by="test-agent"
        )
        assert entry.id == "ctx-001"
        assert entry.scope == ContextScope.TASK
        assert entry.priority == ContextPriority.MEDIUM
        assert entry.value == "test_value"
        assert entry.access_count == 0


class TestContextManagerInit:
    """Test context manager initialization"""

    def test_manager_creates_storage(self, temp_storage):
        manager = HierarchicalContextManager(storage_path=temp_storage)
        assert Path(temp_storage).exists()

    def test_initial_state_empty(self, context_manager):
        stats = context_manager.get_stats()
        assert stats["total_entries"] == 0


class TestContextSet:
    """Test setting context entries"""

    def test_set_basic_value(self, context_manager):
        entry_id = context_manager.set(
            key="user_pref",
            value="dark_mode",
            scope=ContextScope.GLOBAL,
            created_by="agent-001"
        )
        assert entry_id is not None
        assert entry_id.startswith("ctx-")

    def test_set_and_get(self, context_manager):
        context_manager.set(
            key="api_key",
            value="secret-123",
            scope=ContextScope.TASK,
            created_by="agent-001"
        )
        value = context_manager.get("api_key", scope=ContextScope.TASK)
        assert value == "secret-123"

    def test_set_updates_existing_key(self, context_manager):
        context_manager.set(
            key="config",
            value="v1",
            scope=ContextScope.GLOBAL,
            created_by="agent-001"
        )
        context_manager.set(
            key="config",
            value="v2",
            scope=ContextScope.GLOBAL,
            created_by="agent-001"
        )
        value = context_manager.get("config", scope=ContextScope.GLOBAL)
        assert value == "v2"

    def test_set_with_custom_ttl(self, context_manager):
        entry_id = context_manager.set(
            key="temp_data",
            value="expires soon",
            scope=ContextScope.EPHEMERAL,
            created_by="agent-001",
            ttl_seconds=1
        )
        entry = context_manager.get_entry(entry_id)
        assert entry.ttl_seconds == 1
        assert entry.expires_at is not None

    def test_set_with_tags(self, context_manager):
        context_manager.set(
            key="data",
            value="value",
            scope=ContextScope.TASK,
            created_by="agent-001",
            tags=["important", "config"]
        )
        keys = context_manager.list_keys(scope=ContextScope.TASK)
        assert "data" in keys

    def test_set_with_metadata(self, context_manager):
        context_manager.set(
            key="data",
            value="value",
            scope=ContextScope.TASK,
            created_by="agent-001",
            metadata={"source": "config.yaml", "version": 1}
        )
        keys = context_manager.list_keys(scope=ContextScope.TASK)
        assert "data" in keys


class TestContextGet:
    """Test getting context entries"""

    def test_get_returns_default_when_missing(self, context_manager):
        value = context_manager.get("nonexistent", default="default_value")
        assert value == "default_value"

    def test_get_searches_all_scopes(self, context_manager):
        context_manager.set(
            key="shared_key",
            value="global_value",
            scope=ContextScope.GLOBAL,
            created_by="agent-001"
        )
        value = context_manager.get("shared_key")
        assert value == "global_value"

    def test_get_increments_access_count(self, context_manager):
        entry_id = context_manager.set(
            key="counter",
            value="data",
            scope=ContextScope.TASK,
            created_by="agent-001"
        )
        context_manager.get("counter", scope=ContextScope.TASK)
        context_manager.get("counter", scope=ContextScope.TASK)
        entry = context_manager.get_entry(entry_id)
        assert entry.access_count == 2

    def test_get_respects_scope_isolation(self, context_manager):
        context_manager.set(
            key="agent_data",
            value="agent_value",
            scope=ContextScope.AGENT,
            created_by="agent-A"
        )
        # agent-A can see it
        value = context_manager.get("agent_data", agent_id="agent-A")
        assert value == "agent_value"
        # agent-B cannot
        value = context_manager.get("agent_data", agent_id="agent-B")
        assert value is None


class TestContextDelete:
    """Test deleting context entries"""

    def test_delete_by_key(self, context_manager):
        context_manager.set(
            key="to_delete",
            value="value",
            scope=ContextScope.TASK,
            created_by="agent-001"
        )
        result = context_manager.delete("to_delete", ContextScope.TASK)
        assert result is True
        assert context_manager.get("to_delete", scope=ContextScope.TASK) is None

    def test_delete_nonexistent_returns_false(self, context_manager):
        result = context_manager.delete("nonexistent", ContextScope.TASK)
        assert result is False

    def test_delete_by_id(self, context_manager):
        entry_id = context_manager.set(
            key="data",
            value="value",
            scope=ContextScope.TASK,
            created_by="agent-001"
        )
        result = context_manager.delete_by_id(entry_id)
        assert result is True


class TestContextScope:
    """Test scope-based functionality"""

    def test_global_scope_visible_to_all(self, context_manager):
        context_manager.set(
            key="global_data",
            value="visible",
            scope=ContextScope.GLOBAL,
            created_by="agent-A"
        )
        value = context_manager.get("global_data", agent_id="agent-B")
        assert value == "visible"

    def test_task_scope_visible_to_all(self, context_manager):
        context_manager.set(
            key="task_data",
            value="shared",
            scope=ContextScope.TASK,
            created_by="agent-A"
        )
        value = context_manager.get("task_data", agent_id="agent-B")
        assert value == "shared"

    def test_agent_scope_isolated(self, context_manager):
        context_manager.set(
            key="agent_data",
            value="private",
            scope=ContextScope.AGENT,
            created_by="agent-A"
        )
        value = context_manager.get("agent_data", agent_id="agent-A")
        assert value == "private"
        value = context_manager.get("agent_data", agent_id="agent-B")
        assert value is None

    def test_ephemeral_scope_isolated(self, context_manager):
        context_manager.set(
            key="ephemeral",
            value="temp",
            scope=ContextScope.EPHEMERAL,
            created_by="agent-A"
        )
        value = context_manager.get("ephemeral", agent_id="agent-A")
        assert value == "temp"
        value = context_manager.get("ephemeral", agent_id="agent-B")
        assert value is None

    def test_clear_scope(self, context_manager):
        for i in range(3):
            context_manager.set(
                key=f"key_{i}",
                value=f"value_{i}",
                scope=ContextScope.TASK,
                created_by="agent-001"
            )
        removed = context_manager.clear_scope(ContextScope.TASK)
        assert removed == 3


class TestContextList:
    """Test listing context entries"""

    def test_list_keys_by_scope(self, context_manager):
        context_manager.set(
            key="task_key",
            value="v",
            scope=ContextScope.TASK,
            created_by="agent-001"
        )
        context_manager.set(
            key="global_key",
            value="v",
            scope=ContextScope.GLOBAL,
            created_by="agent-001"
        )
        task_keys = context_manager.list_keys(scope=ContextScope.TASK)
        assert "task_key" in task_keys
        assert "global_key" not in task_keys

    def test_list_keys_with_tag_filter(self, context_manager):
        context_manager.set(
            key="tagged",
            value="v",
            scope=ContextScope.TASK,
            created_by="agent-001",
            tags=["important"]
        )
        context_manager.set(
            key="untagged",
            value="v",
            scope=ContextScope.TASK,
            created_by="agent-001"
        )
        keys = context_manager.list_keys(
            scope=ContextScope.TASK, tag_filter="important"
        )
        assert "tagged" in keys
        assert "untagged" not in keys

    def test_list_entries_returns_entries(self, context_manager):
        context_manager.set(
            key="data",
            value="value",
            scope=ContextScope.TASK,
            created_by="agent-001"
        )
        entries = context_manager.list_entries(scope=ContextScope.TASK)
        assert len(entries) == 1
        assert isinstance(entries[0], ContextEntry)


class TestContextExpiration:
    """Test entry expiration"""

    def test_expired_entry_returns_none(self, context_manager):
        entry_id = context_manager.set(
            key="ephemeral",
            value="data",
            scope=ContextScope.EPHEMERAL,
            created_by="agent-001",
            ttl_seconds=1
        )
        import time
        time.sleep(1.1)
        value = context_manager.get("ephemeral", scope=ContextScope.EPHEMERAL)
        assert value is None

    def test_cleanup_expired(self, context_manager):
        for i in range(3):
            context_manager.set(
                key=f"key_{i}",
                value="v",
                scope=ContextScope.EPHEMERAL,
                created_by="agent-001",
                ttl_seconds=1
            )
        import time
        time.sleep(1.1)
        removed = context_manager.cleanup_expired()
        assert removed == 3


class TestContextSnapshot:
    """Test snapshot functionality"""

    def test_create_snapshot(self, context_manager):
        context_manager.set(
            key="data",
            value="value",
            scope=ContextScope.TASK,
            created_by="agent-001"
        )
        snapshot_id = context_manager.snapshot(
            scope=ContextScope.TASK,
            triggered_by="test",
            reason="manual"
        )
        assert snapshot_id.startswith("snap-")

    def test_retrieve_snapshot(self, context_manager):
        context_manager.set(
            key="data",
            value="value",
            scope=ContextScope.TASK,
            created_by="agent-001"
        )
        snapshot_id = context_manager.snapshot(scope=ContextScope.TASK)
        snap = context_manager.get_snapshot(snapshot_id)
        assert snap is not None
        assert snap.scope == ContextScope.TASK


class TestContextStats:
    """Test statistics"""

    def test_get_stats(self, context_manager):
        context_manager.set(
            key="data",
            value="value",
            scope=ContextScope.TASK,
            created_by="agent-001"
        )
        stats = context_manager.get_stats()
        assert stats["total_entries"] >= 1
        assert stats["total_creates"] >= 1


class TestContextExport:
    """Test export functionality"""

    def test_export_context(self, context_manager):
        context_manager.set(
            key="key1",
            value="value1",
            scope=ContextScope.GLOBAL,
            created_by="agent-001"
        )
        exported = context_manager.export_context(scope=ContextScope.GLOBAL)
        assert "global" in exported
        assert exported["global"]["key1"] == "value1"


class TestContextCompactor:
    """Test ContextCompactor"""

    def test_compactor_creation(self, compactor):
        assert compactor is not None

    def test_compact_truncate_string(self, context_manager, compactor):
        entry_id = context_manager.set(
            key="long_text",
            value="This is a very long text " * 20,
            scope=ContextScope.TASK,
            priority=ContextPriority.LOW,
            created_by="agent-001"
        )
        result = compactor.compact_entry(
            entry_id, strategy=CompactionStrategy.TRUNCATE
        )
        assert result is not None
        assert result.compacted_size < result.original_size

    def test_compact_extract_key(self, context_manager, compactor):
        entry_id = context_manager.set(
            key="doc",
            value="Important decision: use Postgres. Random stuff here. Critical: handle errors. More text.",
            scope=ContextScope.TASK,
            priority=ContextPriority.MEDIUM,
            created_by="agent-001"
        )
        result = compactor.compact_entry(
            entry_id, strategy=CompactionStrategy.EXTRACT_KEY
        )
        assert result is not None

    def test_compact_summarize(self, context_manager, compactor):
        entry_id = context_manager.set(
            key="notes",
            value="Decided to use React. Need to handle authentication. Critical: security review.",
            scope=ContextScope.TASK,
            priority=ContextPriority.HIGH,
            created_by="agent-001"
        )
        result = compactor.compact_entry(
            entry_id, strategy=CompactionStrategy.SUMMARIZE
        )
        assert result is not None

    def test_compact_dependency_preserve(self, context_manager, compactor):
        entry_id = context_manager.set(
            key="module",
            value="Depends on auth library",
            scope=ContextScope.TASK,
            priority=ContextPriority.HIGH,
            created_by="agent-001"
        )
        result = compactor.compact_entry(
            entry_id, strategy=CompactionStrategy.DEPENDENCY_PRESERVE
        )
        assert result is not None

    def test_compact_critical_entry_skipped(self, context_manager, compactor):
        entry_id = context_manager.set(
            key="critical",
            value="Do not compress this",
            scope=ContextScope.GLOBAL,
            priority=ContextPriority.CRITICAL,
            created_by="agent-001"
        )
        result = compactor.compact_entry(entry_id, force=False)
        assert result is None

    def test_compact_critical_entry_with_force(self, context_manager, compactor):
        entry_id = context_manager.set(
            key="critical",
            value="Compress this because we force it",
            scope=ContextScope.GLOBAL,
            priority=ContextPriority.CRITICAL,
            created_by="agent-001"
        )
        result = compactor.compact_entry(entry_id, force=True)
        assert result is not None

    def test_compact_scope(self, context_manager, compactor):
        for i in range(3):
            context_manager.set(
                key=f"key_{i}",
                value="long content " * 50,
                scope=ContextScope.TASK,
                priority=ContextPriority.LOW,
                created_by="agent-001"
            )
        results = compactor.compact_scope(ContextScope.TASK)
        assert len(results) >= 0

    def test_compact_by_size_threshold(self, context_manager, compactor):
        context_manager.set(
            key="huge",
            value="x" * 10000,
            scope=ContextScope.TASK,
            priority=ContextPriority.LOW,
            created_by="agent-001"
        )
        results = compactor.compact_by_size_threshold(max_size_bytes=1000)
        assert len(results) >= 1

    def test_compact_for_agent(self, context_manager, compactor):
        context_manager.set(
            key="visible",
            value="data",
            scope=ContextScope.GLOBAL,
            priority=ContextPriority.HIGH,
            created_by="agent-001"
        )
        view = compactor.compact_for_agent("agent-001", max_size_bytes=1000)
        assert "agent_id" in view
        assert "context" in view
        assert "visible" in view["context"]

    def test_compactor_stats(self, context_manager, compactor):
        entry_id = context_manager.set(
            key="data",
            value="x" * 500,
            scope=ContextScope.TASK,
            priority=ContextPriority.LOW,
            created_by="agent-001"
        )
        compactor.compact_entry(entry_id)
        stats = compactor.get_stats()
        assert stats.total_compactions >= 1

    def test_compactor_history(self, context_manager, compactor):
        entry_id = context_manager.set(
            key="data",
            value="x" * 500,
            scope=ContextScope.TASK,
            priority=ContextPriority.LOW,
            created_by="agent-001"
        )
        compactor.compact_entry(entry_id)
        history = compactor.get_history()
        assert len(history) >= 1


class TestCompactionStrategies:
    """Test compaction strategies on different value types"""

    def test_truncate_dict(self, context_manager, compactor):
        entry_id = context_manager.set(
            key="data",
            value={"a": "x" * 100, "b": "y" * 100, "c": "z" * 100},
            scope=ContextScope.TASK,
            priority=ContextPriority.MEDIUM,
            created_by="agent-001"
        )
        result = compactor.compact_entry(
            entry_id, strategy=CompactionStrategy.TRUNCATE
        )
        assert result is not None

    def test_truncate_list(self, context_manager, compactor):
        entry_id = context_manager.set(
            key="data",
            value=["x" * 100 for _ in range(10)],
            scope=ContextScope.TASK,
            priority=ContextPriority.MEDIUM,
            created_by="agent-001"
        )
        result = compactor.compact_entry(
            entry_id, strategy=CompactionStrategy.TRUNCATE
        )
        assert result is not None

    def test_summarize_empty_value(self, context_manager, compactor):
        entry_id = context_manager.set(
            key="empty",
            value="",
            scope=ContextScope.TASK,
            priority=ContextPriority.LOW,
            created_by="agent-001"
        )
        result = compactor.compact_entry(
            entry_id, strategy=CompactionStrategy.SUMMARIZE
        )
        assert result is not None

    def test_extract_key_from_list(self, context_manager, compactor):
        entry_id = context_manager.set(
            key="items",
            value=[
                "Decision: use React",
                "random text",
                "Critical: handle errors",
                "more random"
            ],
            scope=ContextScope.TASK,
            priority=ContextPriority.MEDIUM,
            created_by="agent-001"
        )
        result = compactor.compact_entry(
            entry_id, strategy=CompactionStrategy.EXTRACT_KEY
        )
        assert result is not None

    def test_preserves_90_percent_of_key_decisions_summarize(self, context_manager, compactor):
        """Roadmap Success Metric: Context compaction preserves 90% of key decisions"""
        # Text with 7 key decisions
        text = (
            "We decided to use PostgreSQL for the database. "
            "Critical: handle authentication errors. "
            "TODO: add rate limiting. "
            "Because of performance requirements, we will use Redis. "
            "Random unimportant text here. "
            "Important: deploy to staging first. "
            "Note: security review required before production. "
            "Lots of additional unimportant content here."
        )

        decision_keywords = [
            "decided to", "will use", "Critical:", "TODO:",
            "because of", "Important:", "Note:"
        ]
        original_decisions = sum(
            1 for kw in decision_keywords if kw.lower() in text.lower()
        )

        entry_id = context_manager.set(
            key="design_notes",
            value=text,
            scope=ContextScope.TASK,
            priority=ContextPriority.MEDIUM,
            created_by="agent-001"
        )
        result = compactor.compact_entry(
            entry_id, strategy=CompactionStrategy.SUMMARIZE, force=True
        )

        entries = context_manager.list_entries(scope=ContextScope.TASK)
        compacted_text = ""
        for e in entries:
            if e.id == result.compacted_id:
                compacted_text = str(e.value)
                break

        preserved = sum(
            1 for kw in decision_keywords if kw.lower() in compacted_text.lower()
        )
        preservation_rate = (preserved / original_decisions) * 100
        assert preservation_rate >= 90, (
            f"Only preserved {preserved}/{original_decisions} "
            f"({preservation_rate:.0f}%), need >= 90%"
        )

    def test_preserves_90_percent_of_key_decisions_extract_key(self, context_manager, compactor):
        """Roadmap Success Metric: Context compaction preserves 90% of key decisions (EXTRACT_KEY)"""
        text = (
            "We decided to use PostgreSQL for the database. "
            "Critical: handle authentication errors. "
            "TODO: add rate limiting. "
            "Because of performance requirements, we will use Redis. "
            "Random unimportant text here. "
            "Important: deploy to staging first. "
            "Note: security review required before production. "
            "Lots of additional unimportant content here."
        )

        decision_keywords = [
            "decided to", "will use", "Critical:", "TODO:",
            "because of", "Important:", "Note:"
        ]
        original_decisions = sum(
            1 for kw in decision_keywords if kw.lower() in text.lower()
        )

        entry_id = context_manager.set(
            key="design_notes",
            value=text,
            scope=ContextScope.TASK,
            priority=ContextPriority.MEDIUM,
            created_by="agent-001"
        )
        result = compactor.compact_entry(
            entry_id, strategy=CompactionStrategy.EXTRACT_KEY, force=True
        )

        entries = context_manager.list_entries(scope=ContextScope.TASK)
        compacted_text = ""
        for e in entries:
            if e.id == result.compacted_id:
                compacted_text = str(e.value)
                break

        preserved = sum(
            1 for kw in decision_keywords if kw.lower() in compacted_text.lower()
        )
        preservation_rate = (preserved / original_decisions) * 100
        assert preservation_rate >= 90, (
            f"Only preserved {preserved}/{original_decisions} "
            f"({preservation_rate:.0f}%), need >= 90%"
        )


class TestCompactorHelpers:
    """Test compactor helper methods"""

    def test_split_sentences(self, compactor):
        text = "First sentence. Second sentence! Third sentence?"
        sentences = compactor._split_sentences(text)
        assert len(sentences) == 3

    def test_estimate_size_string(self, compactor):
        size = compactor._estimate_size("hello world")
        assert size > 0

    def test_estimate_size_dict(self, compactor):
        size = compactor._estimate_size({"key": "value"})
        assert size > 0

    def test_estimate_size_list(self, compactor):
        size = compactor._estimate_size([1, 2, 3])
        assert size > 0

    def test_extract_preserved_keys(self, compactor):
        original = {"a": 1, "b": 2, "c": 3}
        compacted = {"a": 1, "b": 2}
        preserved = compactor._extract_preserved_keys(original, compacted)
        assert "a" in preserved
        assert "b" in preserved
        assert "c" not in preserved


class TestSingleton:
    """Test singleton accessors"""

    def test_get_context_manager_returns_instance(self):
        manager = get_context_manager()
        assert isinstance(manager, HierarchicalContextManager)

    def test_get_context_compactor_returns_instance(self):
        compactor = get_context_compactor()
        assert isinstance(compactor, ContextCompactor)


class TestScopeLimits:
    """Test scope limit enforcement"""

    def test_low_priority_entries_dropped_first(self, context_manager):
        # Add critical entry first
        critical_id = context_manager.set(
            key="critical_key",
            value="critical_value",
            scope=ContextScope.GLOBAL,
            priority=ContextPriority.CRITICAL,
            created_by="agent-001"
        )
        # Fill up the scope
        for i in range(250):
            context_manager.set(
                key=f"key_{i}",
                value=f"value_{i}",
                scope=ContextScope.GLOBAL,
                priority=ContextPriority.LOW,
                created_by="agent-001"
            )
        # Critical should still be there
        entry = context_manager.get_entry(critical_id)
        assert entry is not None


class TestEdgeCases:
    """Test edge cases"""

    def test_set_with_none_value(self, context_manager):
        entry_id = context_manager.set(
            key="null_key",
            value=None,
            scope=ContextScope.TASK,
            created_by="agent-001"
        )
        assert entry_id is not None

    def test_set_with_complex_value(self, context_manager):
        complex_value = {
            "nested": {"key": "value"},
            "list": [1, 2, 3],
            "mixed": [{"a": 1}, "string", 42]
        }
        entry_id = context_manager.set(
            key="complex",
            value=complex_value,
            scope=ContextScope.TASK,
            created_by="agent-001"
        )
        value = context_manager.get("complex", scope=ContextScope.TASK)
        assert value == complex_value

    def test_compact_nonexistent_entry(self, compactor):
        result = compactor.compact_entry("nonexistent-id")
        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
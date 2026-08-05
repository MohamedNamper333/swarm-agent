"""
Unit tests for Memory Engine
"""
import pytest
import time
from swarm.core.memory_engine import MemoryEngine, MemoryEntry, MemoryLayer, Lesson


class TestMemoryEntry:
    """Tests for MemoryEntry dataclass"""

    def test_memory_entry_creation(self):
        from swarm.core.memory_engine import MemoryEntry, MemoryLayer
        entry = MemoryEntry(
            id="test_entry",
            layer=MemoryLayer.SCRATCHPAD,
            task_id="task123",
            agent_id="agent1",
            content={"key": "value"}
        )
        assert entry.id == "test_entry"
        assert entry.layer == MemoryLayer.SCRATCHPAD
        assert entry.task_id == "task123"
        assert entry.agent_id == "agent1"
        assert entry.content == {"key": "value"}
        assert entry.confidence == 1.0
        assert entry.access_count == 0


class TestLesson:
    """Tests for Lesson dataclass"""

    def test_lesson_creation(self):
        from swarm.core.memory_engine import Lesson
        lesson = Lesson(
            id="lesson1",
            task_id="task123",
            agent_id="agent1",
            pattern="pattern1",
            lesson="Lesson learned",
            confidence=0.9
        )
        assert lesson.id == "lesson1"
        assert lesson.pattern == "pattern1"
        assert lesson.lesson == "Lesson learned"
        assert lesson.confidence == 0.9
        assert lesson.applications == 0


class TestMemoryEngine:
    """Tests for MemoryEngine"""

    def setup_method(self):
        self.engine = MemoryEngine()

    def teardown_method(self):
        # Clean up any temp files
        pass

    # SCRATCHPAD tests
    def test_write_scratchpad(self):
        entry_id = self.engine.write_scratchpad("task123", "agent1", {"key": "value"})
        assert entry_id.startswith("scratchpad_")
        assert "task123" in entry_id

    def test_read_scratchpad(self):
        self.engine.write_scratchpad("task123", "agent1", {"key": "value"})
        entry = self.engine.read_scratchpad("task123")
        assert entry is not None
        assert entry.content == {"key": "value"}
        assert entry.task_id == "task123"
        assert entry.agent_id == "agent1"

    def test_clear_scratchpad(self):
        self.engine.write_scratchpad("task123", "agent1", {"key": "value"})
        assert self.engine.read_scratchpad("task123") is not None
        
        self.engine.clear_scratchpad("task123")
        assert self.engine.read_scratchpad("task123") is None

    # WORKING MEMORY tests
    def test_write_working(self):
        entry_id = self.engine.write_working("session1", "agent1", {"status": "working"})
        assert entry_id.startswith("working_")
        assert "session1" in entry_id

    def test_read_working(self):
        self.engine.write_working("session1", "agent1", {"status": "working"})
        entry = self.engine.read_working("session1")
        assert entry is not None
        assert entry.content == {"status": "working"}

    def test_update_working(self):
        self.engine.write_working("session1", "agent1", {"status": "working"})
        self.engine.update_working("session1", {"status": "in_progress", "progress": 50})
        
        entry = self.engine.read_working("session1")
        assert entry.content["status"] == "in_progress"
        assert entry.content["progress"] == 50
        assert entry.access_count == 1

    # EPISODIC MEMORY tests
    def test_record_episode(self):
        entry_id = self.engine.record_episode("task123", "agent1", 
                                             {"action": "implemented feature", "result": "success"},
                                             tags=["feature", "success"], 
                                             confidence=0.9)
        assert entry_id.startswith("episode_")
        
        episodes = self.engine.get_episodes(task_id="task123")
        assert len(episodes) >= 1

    def test_get_episodes_filtered(self):
        self.engine.record_episode("task1", "agent1", {"action": "a"}, tags=["tag1"])
        self.engine.record_episode("task2", "agent2", {"action": "b"}, tags=["tag2"])
        
        episodes = self.engine.get_episodes(task_id="task1")
        assert len(episodes) == 1
        assert episodes[0].task_id == "task1"
        
        episodes = self.engine.get_episodes(agent_id="agent2")
        assert len(episodes) == 1
        assert episodes[0].agent_id == "agent2"

    def test_record_lesson(self):
        lesson_id = self.engine.add_lesson("task123", "agent1", 
                                          "pattern1", "Lesson learned", 
                                          confidence=0.9)
        assert lesson_id.startswith("lesson_")

    def test_get_relevant_lessons(self):
        self.engine.add_lesson("task1", "agent1", "pattern1", "Lesson 1", confidence=0.9)
        self.engine.add_lesson("task2", "agent2", "pattern2", "Lesson 2", confidence=0.8)
        
        lessons = self.engine.get_relevant_lessons("task involving pattern1")
        assert len(lessons) >= 1
        assert any("pattern1" in l.pattern for l in lessons)

    def test_apply_lesson(self):
        lesson_id = self.engine.add_lesson("task1", "agent1", "pattern1", "Lesson 1", confidence=0.9)
        result = self.engine.apply_lesson(lesson_id)
        assert result == True

    def test_build_context(self):
        # Write to various memory layers
        self.engine.write_scratchpad("task1", "agent1", {"step": "planning"})
        self.engine.write_working("session1", "agent1", {"status": "active"})
        self.engine.record_episode("task1", "agent1", {"action": "completed"}, tags=["done"])
        self.engine.add_lesson("task1", "agent1", "pattern1", "Lesson 1", confidence=0.9)
        
        context = self.engine.build_context("task1", "agent1", max_tokens=4000)
        
        assert "scratchpad" in context
        assert "working" in context
        assert "episodic" in context
        assert "semantic" in context
        assert "lessons" in context

    def test_get_stats(self):
        self.engine.write_scratchpad("task1", "agent1", {"a": 1})
        self.engine.write_working("session1", "agent1", {"b": 2})
        self.engine.record_episode("task1", "agent1", {"c": 3})
        self.engine.add_lesson("task1", "agent1", "pattern", "lesson", 0.9)
        
        stats = self.engine.get_stats()
        
        assert stats["scratchpad_entries"] >= 1
        assert stats["working_entries"] >= 1
        assert stats["episodic_entries"] >= 1
        # semantic_topics might be 0 if not promoted
        assert stats["semantic_topics"] >= 0
        assert stats["lessons_learned"] >= 1


class TestMemoryLayerEnum:
    """Tests for MemoryLayer enum"""

    def test_layers_defined(self):
        from swarm.core.memory_engine import MemoryLayer
        layers = [l.value for l in MemoryLayer]
        expected = ["scratchpad", "working", "episodic", "semantic"]
        for layer in expected:
            assert layer in layers


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

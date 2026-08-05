"""
Unit tests for Self-Reflection Engine
"""
import pytest
import tempfile
import os
import json
from datetime import datetime
from swarm.intelligence.self_reflection import (
    SelfReflectionEngine, ReflectionEntry, ReflectionDepth, ReflectionTrigger,
    create_reflection_engine
)


class TestSelfReflectionEngine:
    """Tests for SelfReflectionEngine"""
    
    def setup_method(self):
        # Use temp directory for testing
        self.temp_dir = tempfile.mkdtemp()
        self.engine = SelfReflectionEngine(storage_path=self.temp_dir)
    
    def teardown_method(self):
        # Cleanup
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_initialization(self):
        """Test engine initialization"""
        assert self.engine.storage_path.exists()
        assert len(self.engine.reflection_history) == 0
    
    def test_trigger_reflection_quick(self):
        """Test quick reflection trigger"""
        entry = self.engine.trigger_reflection(
            agent_id="agent1",
            task_id="task123",
            trigger=ReflectionTrigger.TASK_COMPLETION,
            depth=ReflectionDepth.QUICK,
            context={"verdict": {"verdict": "PASS", "scores": {}}}
        )
        
        assert entry.agent_id == "agent1"
        assert entry.task_id == "task123"
        assert entry.depth == ReflectionDepth.QUICK
        assert entry.trigger == ReflectionTrigger.TASK_COMPLETION
        assert entry.id.startswith("reflection_task123_")
    
    def test_trigger_reflection_standard(self):
        """Test standard reflection with context"""
        context = {
            "verdict": {
                "verdict": "PASS",
                "scores": {
                    "structural": 1.0,
                    "functional": 0.9,
                    "security": 0.95,
                    "performance": 0.8,
                    "documentation": 0.7
                }
            },
            "artifacts": {},
            "task_spec": {}
        }
        
        entry = self.engine.trigger_reflection(
            agent_id="agent1",
            task_id="task123",
            trigger=ReflectionTrigger.TASK_COMPLETION,
            depth=ReflectionDepth.STANDARD,
            context=context
        )
        
        assert entry.depth == ReflectionDepth.STANDARD
        assert "PASS" in entry.what_went_well
        assert len(entry.action_items) > 0
        assert "constitutional_compliance" in entry.__dict__
    
    def test_trigger_reflection_deep(self):
        """Test deep reflection for failures"""
        context = {
            "verdict": {
                "verdict": "FAIL",
                "scores": {
                    "security": 0.3,
                    "functional": 0.4,
                    "performance": 0.6
                }
            },
            "expected_pass": True
        }
        
        entry = self.engine.trigger_reflection(
            agent_id="agent1",
            task_id="task_fail",
            trigger=ReflectionTrigger.ERROR_ENCOUNTERED,
            depth=ReflectionDepth.DEEP,
            context=context
        )
        
        assert entry.depth == ReflectionDepth.DEEP
        assert entry.trigger == ReflectionTrigger.ERROR_ENCOUNTERED
        assert "security" in entry.what_could_improve.lower()
    
    def test_reflection_history(self):
        """Test reflection history storage"""
        self.engine.trigger_reflection("agent1", "task1", ReflectionTrigger.TASK_COMPLETION, ReflectionDepth.QUICK)
        self.engine.trigger_reflection("agent1", "task2", ReflectionTrigger.TASK_COMPLETION, ReflectionDepth.STANDARD)
        
        history = self.engine.get_reflection_history("agent1")
        assert len(history) == 2
        
        history_limited = self.engine.get_reflection_history("agent1", limit=1)
        assert len(history_limited) == 1
    
    def test_reflection_stats(self):
        """Test reflection statistics"""
        self.engine.trigger_reflection("agent1", "task1", ReflectionTrigger.TASK_COMPLETION, ReflectionDepth.STANDARD, 
            context={"verdict": {"verdict": "PASS", "scores": {"security": 1.0, "functional": 1.0}}})
        self.engine.trigger_reflection("agent1", "task2", ReflectionTrigger.TASK_COMPLETION, ReflectionDepth.STANDARD,
            context={"verdict": {"verdict": "PASS", "scores": {"security": 0.8, "functional": 0.9}}})
        
        stats = self.engine.get_reflection_stats("agent1")
        
        assert stats["total_reflections"] == 2
        assert "avg_confidence_gain" in stats
        assert "constitutional_compliance_rate" in stats
        assert "by_depth" in stats
        assert "by_trigger" in stats
    
    def test_cross_agent_insights(self):
        """Test cross-agent insights"""
        self.engine.trigger_reflection("agent1", "task1", ReflectionTrigger.TASK_COMPLETION, ReflectionDepth.STANDARD,
            context={"verdict": {"verdict": "PASS", "scores": {"security": 0.6}}})
        self.engine.trigger_reflection("agent2", "task2", ReflectionTrigger.TASK_COMPLETION, ReflectionDepth.STANDARD,
            context={"verdict": {"verdict": "PASS", "scores": {"security": 0.5}}})
        
        insights = self.engine.get_cross_agent_insights(["agent1", "agent2"])
        
        assert insights["total_reflections"] == 2
        assert "common_improvement_areas" in insights
    
    def test_export_reflections_json(self):
        """Test JSON export"""
        self.engine.trigger_reflection("agent1", "task1", ReflectionTrigger.TASK_COMPLETION, ReflectionDepth.QUICK)
        
        exported = self.engine.export_reflections("agent1", format="json")
        data = json.loads(exported)
        
        assert len(data) == 1
        assert data[0]["agent_id"] == "agent1"
    
    def test_export_reflections_markdown(self):
        """Test markdown export"""
        self.engine.trigger_reflection("agent1", "task1", ReflectionTrigger.TASK_COMPLETION, ReflectionDepth.STANDARD,
            context={"verdict": {"verdict": "PASS", "scores": {}}})
        
        exported = self.engine.export_reflections("agent1", format="markdown")
        
        assert "Reflection History" in exported
        assert "task1" in exported
    
    def test_reflection_depth_templates(self):
        """Test all depth templates exist"""
        assert ReflectionDepth.QUICK in SelfReflectionEngine.REFLECTION_TEMPLATES
        assert ReflectionDepth.STANDARD in SelfReflectionEngine.REFLECTION_TEMPLATES
        assert ReflectionDepth.DEEP in SelfReflectionEngine.REFLECTION_TEMPLATES
        
        for depth, template in SelfReflectionEngine.REFLECTION_TEMPLATES.items():
            assert "questions" in template
            assert "time_limit_seconds" in template
            assert len(template["questions"]) > 0
    
    def test_constitutional_principles(self):
        """Test constitutional principles are loaded"""
        engine = SelfReflectionEngine()
        principles = engine.constitutional_principles
        
        assert "HONESTY_OVER_HELPFULNESS" in principles
        assert "EVIDENCE_OVER_AUTHORITY" in principles
        assert "MINIMAL_SURFACE_AREA" in principles
        assert "REVERSIBILITY_BY_DEFAULT" in principles
        assert "HUMAN_AGENCY_PRESERVATION" in principles
    
    def test_reflection_depth_enum(self):
        """Test ReflectionDepth enum values"""
        assert ReflectionDepth.QUICK.value == "quick"
        assert ReflectionDepth.STANDARD.value == "standard"
        assert ReflectionDepth.DEEP.value == "deep"
    
    def test_reflection_trigger_enum(self):
        assert ReflectionTrigger.TASK_COMPLETION.value == "task_completion"
        assert ReflectionTrigger.ERROR_ENCOUNTERED.value == "error_encountered"
        assert ReflectionTrigger.PERFORMANCE_DROP.value == "performance_drop"
        assert ReflectionTrigger.SCHEDULED.value == "scheduled"
        assert ReflectionTrigger.MANUAL.value == "manual"
    
    def test_reflection_entry_dataclass(self):
        """Test ReflectionEntry dataclass creation"""
        entry = ReflectionEntry(
            id="test_1",
            agent_id="agent1",
            task_id="task1",
            trigger=ReflectionTrigger.TASK_COMPLETION,
            depth=ReflectionDepth.STANDARD,
            timestamp=datetime.now().isoformat(),
            what_went_well="Test",
            what_could_improve="Test",
            what_was_unexpected="Test",
            key_learning="Test",
            confidence_before=0.5,
            confidence_after=0.7,
            time_spent_seconds=60
        )
        
        assert entry.id == "test_1"
        assert entry.agent_id == "agent1"
        assert entry.depth == ReflectionDepth.STANDARD


class TestReflectionIntegration:
    """Integration tests for self-reflection with FSM"""
    
    def test_create_reflection_engine_factory(self):
        """Test factory function"""
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = create_reflection_engine(f"{tmpdir}/reflections")
            assert isinstance(engine, SelfReflectionEngine)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

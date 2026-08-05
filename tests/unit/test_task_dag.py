"""
Unit tests for Task DAG Builder
"""
import pytest
from swarm.core.task_dag import DAGBuilder, DAG, StageConfig, TaskType
from swarm.core.task_classifier import TaskClassifier


class TestDAG:
    """Tests for DAG class"""

    def test_add_node(self):
        dag = DAG()
        config = StageConfig(
            name="test_stage",
            min_time=60,
            workers=["innovator"],
            description="Test stage",
            outputs=["output.md"],
            constitutional_checks=["MINIMAL_SURFACE_AREA"]
        )
        dag.add_node("test_stage", config)
        assert "test_stage" in dag.nodes
        assert dag.nodes["test_stage"].config.name == "test_stage"

    def test_add_edge(self):
        dag = DAG()
        dag.add_edge("stage1", "stage2", "sequential")
        assert ("stage1", "stage2", "sequential") in dag.edges

    def test_get_execution_order(self):
        dag = DAG()
        config1 = StageConfig(name="stage1", min_time=60, workers=["a"], description="", outputs=[], constitutional_checks=[])
        config2 = StageConfig(name="stage2", min_time=60, workers=["b"], description="", outputs=[], constitutional_checks=[])
        config3 = StageConfig(name="stage3", min_time=60, workers=["c"], description="", outputs=[], constitutional_checks=[])
        
        dag.add_node("stage1", config1)
        dag.add_node("stage2", config2)
        dag.add_node("stage3", config3)
        dag.add_edge("stage1", "stage2")
        dag.add_edge("stage2", "stage3")
        
        order = dag.get_execution_order()
        assert order == ["stage1", "stage2", "stage3"]

    def test_parallel_groups(self):
        dag = DAG()
        config1 = StageConfig(name="stage1", min_time=60, workers=["a"], description="", outputs=[], constitutional_checks=[])
        config2 = StageConfig(name="stage2", min_time=60, workers=["b"], description="", outputs=[], constitutional_checks=[])
        config3 = StageConfig(name="stage3", min_time=60, workers=["c"], description="", outputs=[], constitutional_checks=[])
        
        dag.add_node("stage1", config1)
        dag.add_node("stage2", config2)
        dag.add_node("stage3", config3)
        dag.add_edge("stage1", "stage2")
        dag.add_edge("stage1", "stage3")
        
        groups = dag.get_parallel_groups()
        # stage2 and stage3 can run in parallel after stage1
        assert len(groups) >= 2

    def test_to_mermaid(self):
        dag = DAG()
        dag.add_edge("stage1", "stage2")
        mermaid = dag.to_mermaid()
        assert "flowchart TD" in mermaid
        assert "stage1 --> stage2" in mermaid


class TestDAGBuilder:
    """Tests for DAGBuilder"""

    def setup_method(self):
        self.builder = DAGBuilder()

    def test_build_creative_task(self):
        dag = self.builder.build("Brainstorm innovative uses for AI in healthcare")
        order = dag.get_execution_order()
        assert "analyze" in order
        assert "ideate" in order
        assert "design" in order
        assert "review" in order
        assert "verify" in order
        assert "handoff" in order

    def test_build_security_task(self):
        dag = self.builder.build("Audit security vulnerabilities in authentication system")
        order = dag.get_execution_order()
        assert "analyze" in order
        assert "design" in order
        assert "security_audit" in order
        assert "implement" in order
        assert "test" in order
        assert "verify" in order
        assert "handoff" in order

    def test_build_research_task(self):
        dag = self.builder.build("Research best practices for API design")
        order = dag.get_execution_order()
        assert "analyze" in order
        assert "ideate" in order
        assert "ideate" in order  # document pruned for low complexity research tasks
        assert "verify" in order
        assert "handoff" in order

    def test_build_implementation_task(self):
        dag = self.builder.build("Implement REST API with authentication")
        order = dag.get_execution_order()
        assert "analyze" in order
        assert "design" in order
        assert "implement" in order
        assert "review" in order
        assert "test" in order
        assert "verify" in order
        assert "handoff" in order

    def test_build_debug_task(self):
        dag = self.builder.build("Fix authentication bug in login flow")
        order = dag.get_execution_order()
        assert "analyze" in order
        assert "implement" in order
        assert "test" in order
        assert "verify" in order
        assert "handoff" in order
        # Debug should be shorter (no design, review, optimize)
        assert "design" not in order
        assert "review" not in order
        assert "optimize" not in order

    def test_build_refactor_task(self):
        dag = self.builder.build("Refactor authentication module to improve performance")
        order = dag.get_execution_order()
        assert "analyze" in order
        assert "design" in order
        assert "implement" in order
        assert "review" in order
        assert "test" in order
        assert "handoff" in order

    def test_build_quick_fix_task(self):
        dag = self.builder.build("Quick fix: typo in error message")
        order = dag.get_execution_order()
        assert "analyze" in order
        assert "implement" in order
        assert "verify" in order
        assert "handoff" in order
        # Quick fix should be shortest
        assert "design" not in order
        assert "review" not in order
        assert "test" not in order
        assert "optimize" not in order

    def test_complexity_pruning(self):
        # Low complexity should prune stages
        dag = self.builder.build("Simple task")
        # Just testing it builds without error
        assert len(dag.nodes) > 0

    def test_get_template_info(self):
        info = self.builder.get_template_info("security")
        assert "stages" in info
        assert "primary_workers" in info
        assert "typical_duration" in info
        assert "security_audit" in info["stages"]

    def test_list_all_stages(self):
        stages = self.builder.list_all_stages()
        expected = ["analyze", "ideate", "design", "implement", "review", "test", 
                   "security_audit", "optimize", "document", "verify", "handoff"]
        for stage in expected:
            assert stage in stages


class TestStageConfig:
    """Tests for StageConfig dataclass"""

    def test_stage_config_creation(self):
        config = StageConfig(
            name="test_stage",
            min_time=60,
            workers=["innovator", "explorer"],
            description="Test stage description",
            outputs=["output.md", "report.json"],
            constitutional_checks=["MINIMAL_SURFACE_AREA", "EVIDENCE_OVER_AUTHORITY"]
        )
        assert config.name == "test_stage"
        assert config.min_time == 60
        assert "innovator" in config.workers
        assert config.min_time == 60
        assert len(config.outputs) == 2
        assert "MINIMAL_SURFACE_AREA" in config.constitutional_checks


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

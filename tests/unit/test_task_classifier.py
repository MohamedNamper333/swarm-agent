"""
Unit tests for Task Classifier
"""
import pytest
from swarm.core.task_classifier import TaskClassifier, TaskClassification, TaskType


class TestTaskClassifier:
    """Tests for TaskClassifier"""

    def setup_method(self):
        self.classifier = TaskClassifier()

    def test_classify_creative_task(self):
        result = self.classifier.classify("Brainstorm innovative uses for AI in healthcare")
        assert result.task_type == TaskType.CREATIVE
        assert result.confidence > 0.5
        assert "creative" in result.keywords_matched or "brainstorm" in result.keywords_matched

    def test_classify_security_task(self):
        result = self.classifier.classify("Audit security vulnerabilities in authentication system")
        assert result.task_type == TaskType.SECURITY
        assert result.confidence > 0.5
        assert "security" in result.keywords_matched or "vulnerability" in result.keywords_matched

    def test_classify_research_task(self):
        result = self.classifier.classify("Research best practices for API design")
        assert result.task_type == TaskType.RESEARCH
        assert result.confidence > 0.5
        assert "research" in result.keywords_matched or "best practices" in result.keywords_matched

    def test_classify_debug_task(self):
        result = self.classifier.classify("Fix authentication bug in login flow")
        assert result.task_type == TaskType.DEBUG
        assert result.confidence > 0.5
        assert "debug" in result.keywords_matched or "bug" in result.keywords_matched

    def test_classify_refactor_task(self):
        result = self.classifier.classify("Refactor authentication module to improve performance")
        assert result.task_type == TaskType.REFACTOR
        assert result.confidence > 0.5
        assert "refactor" in result.keywords_matched

    def test_classify_quick_fix_task(self):
        result = self.classifier.classify("Quick fix: typo in error message")
        assert result.task_type == TaskType.QUICK_FIX
        assert result.confidence > 0.5
        assert "quick" in result.keywords_matched or "fix" in result.keywords_matched

    def test_classify_implementation_task(self):
        result = self.classifier.classify("Implement REST API with authentication")
        assert result.task_type == TaskType.IMPLEMENTATION
        assert result.confidence > 0.5
        assert "implement" in result.keywords_matched

    def test_complexity_assessment(self):
        # Simple task
        simple = self.classifier.assess_complexity("Fix typo in readme")
        assert simple < 40
        
        # Complex task
        complex_task = self.classifier.assess_complexity("Build a new microservices architecture with unknown technology, regulatory compliance, and critical path dependencies")
        assert complex_task > 60

    def test_pipeline_variant_selection(self):
        assert self.classifier.get_pipeline_variant(20) == "LITE"
        assert self.classifier.get_pipeline_variant(40) == "STANDARD"
        assert self.classifier.get_pipeline_variant(70) == "FULL"

    def test_reasoning_chain(self):
        result = self.classifier.classify("Audit security vulnerabilities in the authentication module")
        assert "Premise" in result.reasoning or "Evidence" in result.reasoning or "Inference" in result.reasoning
        assert len(result.keywords_matched) > 0

    def test_unknown_task_defaults_to_implementation(self):
        result = self.classifier.classify("Some completely unknown task type xyz")
        # Should default to IMPLEMENTATION
        assert result.task_type == TaskType.IMPLEMENTATION


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

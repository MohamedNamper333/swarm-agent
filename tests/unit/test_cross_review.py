"""
Unit tests for Cross-Review Engine
"""
import pytest
import tempfile
import os
import json
from datetime import datetime, timedelta
from swarm.intelligence.cross_review import (
    CrossReviewEngine, ReviewRequest, ReviewCriteria, ReviewFinding,
    ReviewVerdictResult, ReviewVerdict, ReviewType, ReviewStatus,
    create_cross_review_engine
)


class TestCrossReviewEngine:
    """Tests for CrossReviewEngine"""
    
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.engine = CrossReviewEngine(storage_path=self.temp_dir)
    
    def teardown_method(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_initialization(self):
        """Test engine initialization"""
        assert self.engine.storage_path.exists()
        assert len(self.engine.reviews) == 0
    
    def test_default_criteria(self):
        """Test default criteria are loaded"""
        criteria = self.engine.DEFAULT_CRITERIA
        
        assert "correctness" in criteria
        assert "security" in criteria
        assert "performance" in criteria
        assert "maintainability" in criteria
        assert "architecture" in criteria
        assert "testing" in criteria
        assert "documentation" in criteria
        assert "constitutional" in criteria
        
        # Check security has highest weight
        assert criteria["security"].weight >= 1.5
        assert criteria["correctness"].weight >= 1.0
    
    def test_request_review(self):
        """Test requesting a review"""
        review_id = self.engine.request_review(
            artifact_id="artifact123",
            artifact_type="code",
            artifact_content="def hello(): return 'hello'",
            requester_id="agent1",
            reviewer_ids=["agent2", "agent3"],
            review_type=ReviewType.PEER_REVIEW,
            deadline_hours=24
        )
        
        assert review_id is not None
        assert review_id in self.engine.reviews
        
        review = self.engine.reviews[review_id]
        assert review.artifact_id == "artifact123"
        assert review.requester_id == "agent1"
        assert set(review.reviewer_ids) == {"agent2", "agent3"}
        assert review.review_type == ReviewType.PEER_REVIEW
        assert review.status == ReviewStatus.PENDING
        assert len(review.criteria) > 0
    
    def test_submit_review_approve(self):
        """Test submitting an approve review"""
        review_id = self.engine.request_review(
            artifact_id="artifact123",
            artifact_type="code",
            artifact_content="def test(): pass",
            requester_id="agent1",
            reviewer_ids=["agent2"],
            review_type=ReviewType.PEER_REVIEW
        )
        
        result = self.engine.submit_review(
            review_id=review_id,
            reviewer_id="agent2",
            verdict="approve",
            findings=[],
            confidence=0.9,
            summary="Code looks good",
            notes="Clean implementation"
        )
        
        assert result == True
        
        review = self.engine.reviews[review_id]
        assert "agent2" in review.reviews
        assert review.reviews["agent2"].verdict == ReviewVerdict.APPROVE
        assert review.reviews["agent2"].confidence == 0.9
    
    def test_submit_review_reject(self):
        """Test submitting a reject review"""
        review_id = self.engine.request_review(
            artifact_id="artifact123",
            artifact_type="code",
            artifact_content="def bad(): os.system('rm -rf /')",
            requester_id="agent1",
            reviewer_ids=["agent2"],
            review_type=ReviewType.SECURITY_AUDIT
        )
        
        result = self.engine.submit_review(
            review_id=review_id,
            reviewer_id="agent2",
            verdict="reject",
            findings=[
                {"criterion": "security", "severity": "critical", "title": "Command injection", "description": "os.system with user input"}
            ],
            confidence=0.95,
            summary="Critical security vulnerability",
            notes="Must fix immediately"
        )
        
        assert result == True
        
        review = self.engine.reviews[review_id]
        assert review.reviews["agent2"].verdict == ReviewVerdict.REJECT
        assert len(review.reviews["agent2"].findings) == 1
    
    def test_submit_review_request_changes(self):
        """Test submitting request_changes review"""
        review_id = self.engine.request_review(
            artifact_id="artifact123",
            artifact_type="code",
            artifact_content="def foo(): pass",
            requester_id="agent1",
            reviewer_ids=["agent2"],
            review_type=ReviewType.PEER_REVIEW
        )
        
        result = self.engine.submit_review(
            review_id=review_id,
            reviewer_id="agent2",
            verdict="request_changes",
            findings=[{"criterion": "maintainability", "severity": "medium", "title": "Add docstring"}],
            confidence=0.8,
            summary="Needs docstrings",
            notes="Add docstrings to all functions"
        )
        
        assert result == True
        
        review = self.engine.reviews[review_id]
        assert review.reviews["agent2"].verdict == ReviewVerdict.REQUEST_CHANGES
    
    def test_resolve_reviews_approved(self):
        """Test consensus resolution - all approve"""
        review_id = self.engine.request_review(
            artifact_id="artifact123",
            artifact_type="code",
            artifact_content="def test(): pass",
            requester_id="agent1",
            reviewer_ids=["agent2", "agent3"],
            review_type=ReviewType.PEER_REVIEW
        )
        
        self.engine.submit_review(
            review_id=review_id,
            reviewer_id="agent2",
            verdict="approve",
            findings=[],
            confidence=0.9,
            summary="Good"
        )
        
        self.engine.submit_review(
            review_id=review_id,
            reviewer_id="agent3",
            verdict="approve",
            findings=[],
            confidence=0.85,
            summary="LGTM"
        )
        
        review = self.engine.reviews[review_id]
        assert review.status == "completed"
        assert review.consensus is not None
        assert review.consensus["verdict"] == "approve"
        assert review.consensus["agreement"] == 1.0
    
    def test_resolve_reviews_rejected(self):
        """Test consensus resolution - one rejects"""
        review_id = self.engine.request_review(
            artifact_id="artifact123",
            artifact_type="code",
            artifact_content="def test(): pass",
            requester_id="agent1",
            reviewer_ids=["agent2", "agent3"],
            review_type=ReviewType.PEER_REVIEW
        )
        
        self.engine.submit_review(
            review_id=review_id,
            reviewer_id="agent2",
            verdict="approve",
            findings=[],
            confidence=0.9,
            summary="Good"
        )
        
        self.engine.submit_review(
            review_id=review_id,
            reviewer_id="agent3",
            verdict="reject",
            findings=[{"criterion": "security", "severity": "high", "title": "Vulnerability"}],
            confidence=0.95,
            summary="Security issue"
        )
        
        review = self.engine.reviews[review_id]
        assert review.consensus["verdict"] == "reject"
        assert len(review.consensus["blockers"]) == 1
    
    def test_resolve_reviews_changes_requested(self):
        """Test consensus resolution - changes requested"""
        review_id = self.engine.request_review(
            artifact_id="artifact123",
            artifact_type="code",
            artifact_content="def test(): pass",
            requester_id="agent1",
            reviewer_ids=["agent2", "agent3"],
            review_type=ReviewType.PEER_REVIEW
        )
        
        self.engine.submit_review(
            review_id=review_id,
            reviewer_id="agent2",
            verdict="approve",
            findings=[],
            confidence=0.9,
            summary="Good"
        )
        
        self.engine.submit_review(
            review_id=review_id,
            reviewer_id="agent3",
            verdict="request_changes",
            findings=[{"criterion": "maintainability", "severity": "medium", "title": "Add docs"}],
            confidence=0.8,
            summary="Needs docs"
        )
        
        review = self.engine.reviews[review_id]
        assert review.consensus["verdict"] == "changes_requested"
    
    def test_get_pending_reviews(self):
        """Test getting pending reviews for a reviewer"""
        self.engine.request_review(
            artifact_id="artifact1",
            artifact_type="code",
            artifact_content="def a(): pass",
            requester_id="agent1",
            reviewer_ids=["agent2"],
            review_type=ReviewType.PEER_REVIEW
        )
        
        self.engine.request_review(
            artifact_id="artifact2",
            artifact_type="code",
            artifact_content="def b(): pass",
            requester_id="agent1",
            reviewer_ids=["agent2", "agent3"],
            review_type=ReviewType.PEER_REVIEW
        )
        
        pending = self.engine.get_pending_reviews("agent2")
        assert len(pending) == 2
        
        pending_agent3 = self.engine.get_pending_reviews("agent3")
        assert len(pending_agent3) == 1
    
    def test_get_review_status(self):
        """Test getting review status"""
        review_id = self.engine.request_review(
            artifact_id="artifact123",
            artifact_type="code",
            artifact_content="def test(): pass",
            requester_id="agent1",
            reviewer_ids=["agent2", "agent3"],
            review_type=ReviewType.PEER_REVIEW
        )
        
        status = self.engine.get_review_status(review_id)
        
        assert status is not None
        assert status["id"] == review_id
        assert status["status"] == "pending"
        assert status["reviewers_total"] == 2
        assert status["reviews_submitted"] == 0
    
    def test_get_review_status_after_submit(self):
        """Test review status after submission"""
        review_id = self.engine.request_review(
            artifact_id="artifact123",
            artifact_type="code",
            artifact_content="def test(): pass",
            requester_id="agent1",
            reviewer_ids=["agent2"],
            review_type=ReviewType.PEER_REVIEW
        )
        
        self.engine.submit_review(
            review_id=review_id,
            reviewer_id="agent2",
            verdict="approve",
            findings=[],
            confidence=0.9,
            summary="Good"
        )
        
        status = self.engine.get_review_status(review_id)
        assert status["reviews_submitted"] == 1
        assert status["status"] == "completed"
    
    def test_adversarial_review(self):
        """Test adversarial review request"""
        review_id = self.engine.run_adversarial_review(
            artifact_id="artifact123",
            artifact_content="def auth(): pass",
            artifact_type="code",
            defender_id="agent1",
            attacker_ids=["agent2", "agent3"],
            focus_areas=["security", "correctness"]
        )
        
        assert review_id is not None
        assert review_id in self.engine.reviews
        
        review = self.engine.reviews[review_id]
        assert review.review_type == "adversarial"
        assert set(review.reviewer_ids) == {"agent2", "agent3"}
    
    def test_get_agent_stats(self):
        """Test getting agent review statistics"""
        self.engine.request_review("a1", "code", "def a(): pass", "agent1", ["agent2"])
        self.engine.request_review("a2", "code", "def b(): pass", "agent1", ["agent2"])
        
        stats = self.engine.get_agent_stats("agent2")
        assert stats["reviews_given"] >= 0
        assert stats["reviews_received"] >= 0
    
    def test_get_review_analytics(self):
        """Test system-wide review analytics"""
        self.engine.request_review("a1", "code", "def a(): pass", "agent1", ["agent2"])
        self.engine.request_review("a2", "code", "def b(): pass", "agent1", ["agent2"])
        
        analytics = self.engine.get_review_analytics()
        
        assert analytics["total_reviews"] >= 2
        assert analytics["pending"] >= 0
        assert "verdict_distribution" in analytics
    
    def test_review_criteria_weights(self):
        """Test review criteria have correct weights"""
        criteria = self.engine.DEFAULT_CRITERIA
        
        # Security should have high weight
        assert criteria["security"].weight >= 1.5
        assert criteria["correctness"].weight >= 1.0
        assert criteria["constitutional"].weight >= 1.5
        
        # Required criteria
        assert criteria["security"].required == True
        assert criteria["correctness"].required == True
        
        # Optional criteria
        assert criteria["documentation"].required == False
    
    def test_adversarial_prompts(self):
        """Test adversarial prompts are defined"""
        prompts = self.engine.ADVERSARIAL_PROMPTS
        
        assert "security" in prompts
        assert "correctness" in prompts
        assert "architecture" in prompts
        assert "maintainability" in prompts
        
        assert len(prompts["security"]) >= 5
        assert len(prompts["correctness"]) >= 5


class TestReviewEnums:
    """Tests for Review enums"""
    
    def test_review_verdict_enum(self):
        assert ReviewVerdict.APPROVE.value == "approve"
        assert ReviewVerdict.REJECT.value == "reject"
        assert ReviewVerdict.REQUEST_CHANGES.value == "request_changes"
        assert ReviewVerdict.NEEDS_INFO.value == "needs_info"
    
    def test_review_type_enum(self):
        assert ReviewType.PEER_REVIEW.value == "peer_review"
        assert ReviewType.ADVERSARIAL.value == "adversarial"
        assert ReviewType.CONSENSUS.value == "consensus"
        assert ReviewType.SECURITY_AUDIT.value == "security_audit"
        assert ReviewType.ARCHITECTURE_REVIEW.value == "architecture_review"
    
    def test_review_status_enum(self):
        assert ReviewStatus.PENDING.value == "pending"
        assert ReviewStatus.IN_PROGRESS.value == "in_progress"
        assert ReviewStatus.COMPLETED.value == "completed"
        assert ReviewStatus.RESOLVED.value == "resolved"
        assert ReviewStatus.ESCALATED.value == "escalated"
    
    def test_review_criteria_dataclass(self):
        criteria = ReviewCriteria(
            name="test",
            description="Test criteria",
            weight=1.5,
            required=True,
            threshold=0.8
        )
        
        assert criteria.name == "test"
        assert criteria.weight == 1.5
        assert criteria.required == True
        assert criteria.threshold == 0.8


class TestReviewDataClasses:
    """Tests for Review data classes"""
    
    def test_review_finding(self):
        finding = ReviewFinding(
            id="f1",
            criterion="security",
            severity="critical",
            title="SQL Injection",
            description="SQL injection in user input",
            location="auth.py:42",
            suggestion="Use parameterized queries",
            confidence=0.95
        )
        
        assert finding.id == "f1"
        assert finding.severity == "critical"
        assert finding.criterion == "security"
    
    def test_review_verdict_result(self):
        result = ReviewVerdictResult(
            verdict=ReviewVerdict.APPROVE,
            confidence=0.9,
            findings=[{"criterion": "security", "severity": "low"}],
            summary="Code is secure",
            reviewer_notes="Good job"
        )
        
        assert result.verdict == ReviewVerdict.APPROVE
        assert result.confidence == 0.9
        assert len(result.findings) == 1
    
    def test_review_request(self):
        req = ReviewRequest(
            id="rev1",
            artifact_id="art1",
            artifact_type="code",
            artifact_content="def test(): pass",
            requester_id="agent1",
            reviewer_ids=["agent2", "agent3"],
            review_type="peer_review",
            criteria=[],
            deadline=(datetime.now() + timedelta(hours=24)).isoformat()
        )
        
        assert req.id == "rev1"
        assert req.artifact_id == "art1"
        assert len(req.reviewer_ids) == 2
        assert req.status == ReviewStatus.PENDING


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

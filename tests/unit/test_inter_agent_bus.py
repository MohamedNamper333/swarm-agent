"""
Unit tests for Inter-Agent Bus
"""
import pytest
import time
from swarm.core.inter_agent_bus import AgentBus, Message, MessageType, ReviewRequest


class TestAgentBus:
    """Tests for AgentBus"""

    def setup_method(self):
        self.bus = AgentBus()

    def test_subscribe(self):
        """Test agent subscription to channel"""
        self.bus.subscribe("agent1", "channel1")
        assert "agent1" in self.bus.channels["channel1"]

    def test_unsubscribe(self):
        """Test agent unsubscription from channel"""
        self.bus.subscribe("agent1", "channel1")
        self.bus.unsubscribe("agent1", "channel1")
        assert "agent1" not in self.bus.channels["channel1"]

    def test_publish_broadcast(self):
        """Test broadcasting message to channel"""
        self.bus.subscribe("agent1", "test_channel")
        self.bus.subscribe("agent2", "test_channel")
        
        msg = self.bus.broadcast("sender", "test_channel", MessageType.STATUS_UPDATE, {"data": "test"})
        
        assert msg.from_agent == "sender"
        assert msg.channel == "test_channel"
        assert msg.payload == {"data": "test"}

    def test_send_direct(self):
        """Test direct message to specific agent"""
        msg = self.bus.send_direct("sender", "receiver", MessageType.CLARIFICATION, {"question": "help"})
        
        assert msg.from_agent == "sender"
        assert msg.to_agent == "receiver"
        assert msg.type == MessageType.CLARIFICATION
        assert msg.payload == {"question": "help"}

    def test_request_review(self):
        """Test requesting review from reviewers"""
        self.bus.subscribe("reviewer1", "review.reviewer1")
        self.bus.subscribe("reviewer2", "review.reviewer2")
        
        review_id = self.bus.request_review("author", "artifact.md", ["reviewer1", "reviewer2"])
        
        assert review_id is not None
        assert review_id in self.bus.pending_reviews
        assert self.bus.pending_reviews[review_id]["reviewers"] == ["reviewer1", "reviewer2"]
        assert self.bus.pending_reviews[review_id]["status"] == "pending"

    def test_submit_review(self):
        """Test submitting review response"""
        self.bus.subscribe("reviewer1", "review.reviewer1")
        
        review_id = self.bus.request_review("author", "artifact.md", ["reviewer1"])
        response = self.bus.submit_review("reviewer1", review_id, "approve", [{"finding": "looks good"}])
        
        assert response["verdict"] == "approve"
        assert response["reviewer"] == "reviewer1"
        assert "findings" in response
        assert "submitted_at" in response

    def test_resolve_reviews_approved(self):
        """Test resolving reviews - all approve"""
        self.bus.subscribe("reviewer1", "review.reviewer1")
        self.bus.subscribe("reviewer2", "review.reviewer2")
        
        review_id = self.bus.request_review("author", "artifact.md", ["reviewer1", "reviewer2"])
        self.bus.submit_review("reviewer1", review_id, "approve", [])
        self.bus.submit_review("reviewer2", review_id, "approve", [])
        
        result = self.bus.resolve_reviews(review_id)
        
        assert result["verdict"] == "approved"
        assert len(result["responses"]) == 2

    def test_resolve_reviews_rejected(self):
        """Test resolving reviews - one rejects"""
        self.bus.subscribe("reviewer1", "review.reviewer1")
        self.bus.subscribe("reviewer2", "review.reviewer2")
        
        review_id = self.bus.request_review("author", "artifact.md", ["reviewer1", "reviewer2"])
        self.bus.submit_review("reviewer1", review_id, "approve", [])
        self.bus.submit_review("reviewer2", review_id, "reject", [{"finding": "security issue"}])
        
        result = self.bus.resolve_reviews(review_id)
        
        assert result["verdict"] == "rejected"
        assert len(result["blockers"]) == 1

    def test_resolve_reviews_changes_requested(self):
        """Test resolving reviews - changes requested"""
        self.bus.subscribe("reviewer1", "review.reviewer1")
        self.bus.subscribe("reviewer2", "review.reviewer2")
        
        review_id = self.bus.request_review("author", "artifact.md", ["reviewer1", "reviewer2"])
        self.bus.submit_review("reviewer1", review_id, "approve", [])
        self.bus.submit_review("reviewer2", review_id, "request_changes", [{"finding": "needs tests"}])
        
        result = self.bus.resolve_reviews(review_id)
        
        assert result["verdict"] == "changes_requested"

    def test_handoff_context(self):
        """Test context handoff between agents"""
        handoff = self.bus.handoff_context("agent1", "agent2", "task123", {
            "goal": "Implement feature",
            "decisions": ["use REST API"],
            "artifacts": ["api_spec.md"],
            "scratchpad": "problem_understanding: Need REST API\nselected_approach: REST\nrisk_assessment: Low",
            "confidence_history": [0.8, 0.9],
            "lessons": ["Use existing framework"],
            "blockers": [],
            "open_questions": []
        })
        
        assert handoff["type"] == "handoff"
        assert handoff["task_id"] == "task123"
        assert handoff["from"] == "agent1"
        assert handoff["to"] == "agent2"
        assert "context" in handoff
        assert handoff["context"]["goal"] == "Implement feature"

    def test_get_message_log(self):
        """Test getting message log with filters"""
        self.bus.subscribe("agent1", "channel1")
        self.bus.broadcast("agent1", "channel1", MessageType.STATUS_UPDATE, {"status": "ok"})
        
        log = self.bus.get_message_log(agent_id="agent1")
        assert len(log) >= 1
        
        log = self.bus.get_message_log(channel="channel1")
        assert len(log) >= 1

    def test_get_pending_reviews(self):
        """Test getting pending reviews"""
        self.bus.subscribe("reviewer1", "review.reviewer1")
        
        review_id = self.bus.request_review("author", "artifact.md", ["reviewer1"])
        pending = self.bus.get_pending_reviews()
        
        assert review_id in pending
        assert pending[review_id]["status"] == "pending"

    def test_scratchpad_summarize(self):
        """Test scratchpad summarization"""
        scratchpad = """problem_understanding: Need to build API
assumptions_explicit: User wants REST
selected_approach: REST with FastAPI
risk_assessment: Low complexity
confidence_level: 85"""
        
        summary = self.bus._summarize_scratchpad(scratchpad)
        
        assert "problem_understanding" in summary
        assert "selected_approach" in summary
        assert "risk_assessment" in summary
        assert "confidence_level" in summary


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

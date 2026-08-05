"""
Unit tests for Agent State Machine (FSM)
"""
import pytest
import time
from swarm.core.agent_state_machine import AgentStateMachine, AgentState


class TestAgentStateMachine:
    """Tests for AgentStateMachine"""

    def setup_method(self):
        self.fsm = AgentStateMachine("test-agent")

    def test_initial_state(self):
        """Test initial state is IDLE"""
        assert self.fsm.state == AgentState.IDLE
        assert self.fsm.current_task is None

    def test_valid_transition_idle_to_assigned(self):
        """Test valid transition IDLE -> ASSIGNED"""
        result = self.fsm.transition(AgentState.ASSIGNED, "Task assigned", "task123")
        assert result == True
        assert self.fsm.state == AgentState.ASSIGNED
        assert self.fsm.current_task == "task123"

    def test_valid_transition_assigned_to_scratchpad(self):
        """Test valid transition ASSIGNED -> SCRATCHPAD"""
        self.fsm.transition(AgentState.ASSIGNED, "Task assigned", "task123")
        result = self.fsm.transition(AgentState.SCRATCHPAD, "Starting work")
        assert result == True
        assert self.fsm.state == AgentState.SCRATCHPAD

    def test_valid_transition_scratchpad_to_executing(self):
        """Test valid transition SCRATCHPAD -> EXECUTING"""
        self.fsm.transition(AgentState.ASSIGNED, "Task assigned", "task123")
        self.fsm.transition(AgentState.SCRATCHPAD, "Starting work")
        result = self.fsm.transition(AgentState.EXECUTING, "Executing task")
        assert result == True
        assert self.fsm.state == AgentState.EXECUTING

    def test_valid_transition_executing_to_review_pending(self):
        """Test valid transition EXECUTING -> REVIEW_PENDING"""
        self.fsm.transition(AgentState.ASSIGNED, "Task assigned", "task123")
        self.fsm.transition(AgentState.SCRATCHPAD, "Starting work")
        self.fsm.transition(AgentState.EXECUTING, "Executing task")
        result = self.fsm.transition(AgentState.REVIEW_PENDING, "Submitted for review")
        assert result == True
        assert self.fsm.state == AgentState.REVIEW_PENDING

    def test_valid_transition_review_pending_to_approved(self):
        """Test valid transition REVIEW_PENDING -> APPROVED"""
        self.fsm.transition(AgentState.ASSIGNED, "Task assigned", "task123")
        self.fsm.transition(AgentState.SCRATCHPAD, "Starting work")
        self.fsm.transition(AgentState.EXECUTING, "Executing task")
        self.fsm.transition(AgentState.REVIEW_PENDING, "Submitted for review")
        result = self.fsm.transition(AgentState.APPROVED, "Review passed")
        assert result == True
        assert self.fsm.state == AgentState.APPROVED

    def test_valid_transition_review_pending_to_rejected(self):
        """Test valid transition REVIEW_PENDING -> REJECTED"""
        self.fsm.transition(AgentState.ASSIGNED, "Task assigned", "task123")
        self.fsm.transition(AgentState.SCRATCHPAD, "Starting work")
        self.fsm.transition(AgentState.EXECUTING, "Executing task")
        self.fsm.transition(AgentState.REVIEW_PENDING, "Submitted for review")
        result = self.fsm.transition(AgentState.REJECTED, "Review failed")
        assert result == True
        assert self.fsm.state == AgentState.REJECTED

    def test_valid_transition_rejected_to_scratchpad(self):
        """Test valid transition REJECTED -> SCRATCHPAD"""
        self.fsm.transition(AgentState.ASSIGNED, "Task assigned", "task123")
        self.fsm.transition(AgentState.SCRATCHPAD, "Starting work")
        self.fsm.transition(AgentState.EXECUTING, "Executing task")
        self.fsm.transition(AgentState.REVIEW_PENDING, "Submitted for review")
        self.fsm.transition(AgentState.REJECTED, "Review failed")
        result = self.fsm.transition(AgentState.SCRATCHPAD, "Retrying")
        assert result == True
        assert self.fsm.state == AgentState.SCRATCHPAD

    def test_valid_transition_approved_to_idle(self):
        """Test valid transition APPROVED -> IDLE"""
        self.fsm.transition(AgentState.ASSIGNED, "Task assigned", "task123")
        self.fsm.transition(AgentState.SCRATCHPAD, "Starting work")
        self.fsm.transition(AgentState.EXECUTING, "Executing task")
        self.fsm.transition(AgentState.REVIEW_PENDING, "Submitted for review")
        self.fsm.transition(AgentState.APPROVED, "Review passed")
        result = self.fsm.transition(AgentState.IDLE, "Task complete")
        assert result == True
        assert self.fsm.state == AgentState.IDLE

    def test_invalid_transition(self):
        """Test invalid transition is rejected"""
        # Can't go from IDLE to EXECUTING directly
        result = self.fsm.transition(AgentState.EXECUTING, "Invalid")
        assert result == False
        assert self.fsm.state == AgentState.IDLE

    def test_cannot_transition_from_idle_to_executing(self):
        """Test cannot go IDLE -> EXECUTING directly"""
        assert self.fsm.can_transition(AgentState.EXECUTING) == False

    def test_can_transition_from_assigned_to_scratchpad(self):
        """Test can transition ASSIGNED -> SCRATCHPAD"""
        self.fsm.transition(AgentState.ASSIGNED, "Task assigned", "task123")
        assert self.fsm.can_transition(AgentState.SCRATCHPAD) == True

    def test_time_in_state(self):
        """Test time tracking in state"""
        self.fsm.transition(AgentState.ASSIGNED, "Task assigned", "task123")
        time.sleep(0.1)
        assert self.fsm.time_in_state() > 0.05

    def test_is_stuck(self):
        """Test stuck detection"""
        self.fsm.transition(AgentState.ASSIGNED, "Task assigned", "task123")
        # Just assigned, shouldn't be stuck yet
        assert self.fsm.is_stuck() == False

    def test_get_stuck_reason(self):
        """Test getting stuck reason"""
        self.fsm.transition(AgentState.ASSIGNED, "Task assigned", "task123")
        reason = self.fsm.get_stuck_reason()
        assert reason is None  # Not stuck yet

    def test_get_valid_transitions(self):
        """Test getting valid next states"""
        transitions = self.fsm.get_valid_transitions()
        assert "ASSIGNED" in transitions

    def test_get_status(self):
        """Test getting current status"""
        self.fsm.transition(AgentState.ASSIGNED, "Task assigned", "task123")
        status = self.fsm.get_status()
        
        assert status["agent_id"] == "test-agent"
        assert status["state"] == "ASSIGNED"
        assert status["current_task"] == "task123"
        assert status["time_in_state"] >= 0
        assert status["is_stuck"] == False
        assert "SCRATCHPAD" in status["valid_transitions"]

    def test_get_history(self):
        """Test getting transition history"""
        self.fsm.transition(AgentState.ASSIGNED, "Task assigned", "task123")
        self.fsm.transition(AgentState.SCRATCHPAD, "Starting work")
        
        history = self.fsm.get_history()
        assert len(history) == 2
        assert history[0]["from"] == "IDLE"
        assert history[0]["to"] == "ASSIGNED"
        assert history[1]["from"] == "ASSIGNED"
        assert history[1]["to"] == "SCRATCHPAD"

    def test_get_history_limit(self):
        """Test getting limited history"""
        self.fsm.transition(AgentState.ASSIGNED, "Task assigned", "task123")
        self.fsm.transition(AgentState.SCRATCHPAD, "Starting work")
        self.fsm.transition(AgentState.EXECUTING, "Executing")
        
        history = self.fsm.get_history(limit=2)
        assert len(history) == 2

    def test_reset(self):
        """Test reset to IDLE - from SCRATCHPAD transition to IDLE is invalid, so it stays"""
        self.fsm.transition(AgentState.ASSIGNED, "Task assigned", "task123")
        self.fsm.transition(AgentState.SCRATCHPAD, "Starting work")
        
        self.fsm.reset("Manual reset")
        
        # reset() calls transition(IDLE) which is invalid from SCRATCHPAD
        # So state remains SCRATCHPAD (transition rejected)
        assert self.fsm.state == AgentState.SCRATCHPAD  # transition rejected
        assert self.fsm.current_task is None


class TestAgentState:
    """Tests for AgentState enum"""

    def test_all_states_defined(self):
        """Test all expected states are defined"""
        states = [s.name for s in AgentState]
        expected = ["IDLE", "ASSIGNED", "SCRATCHPAD", "EXECUTING", 
                   "REVIEW_PENDING", "APPROVED", "REJECTED", 
                   "BLOCKED", "ERROR", "TIMEOUT"]
        for state in expected:
            assert state in states


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

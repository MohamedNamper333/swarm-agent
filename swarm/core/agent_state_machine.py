"""
Agent State Machine - FSM per agent for lifecycle management
"""
from enum import Enum, auto
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import threading


class AgentState(Enum):
    IDLE = auto()
    ASSIGNED = auto()
    SCRATCHPAD = auto()
    EXECUTING = auto()
    REVIEW_PENDING = auto()
    APPROVED = auto()
    REJECTED = auto()
    BLOCKED = auto()
    ERROR = auto()
    TIMEOUT = auto()


@dataclass
class StateTransition:
    from_state: AgentState
    to_state: AgentState
    at: str
    reason: str
    task: Optional[str]
    duration_seconds: float


class AgentStateMachine:
    """Finite State Machine for agent lifecycle management."""

    TRANSITIONS = {
        AgentState.IDLE: [AgentState.ASSIGNED],
        AgentState.ASSIGNED: [AgentState.SCRATCHPAD, AgentState.ERROR],
        AgentState.SCRATCHPAD: [AgentState.EXECUTING, AgentState.BLOCKED],
        AgentState.EXECUTING: [AgentState.REVIEW_PENDING, AgentState.ERROR, AgentState.TIMEOUT],
        AgentState.REVIEW_PENDING: [AgentState.APPROVED, AgentState.REJECTED, AgentState.BLOCKED],
        AgentState.REJECTED: [AgentState.SCRATCHPAD, AgentState.BLOCKED],
        AgentState.APPROVED: [AgentState.IDLE],
        AgentState.BLOCKED: [AgentState.SCRATCHPAD, AgentState.IDLE],
        AgentState.ERROR: [AgentState.SCRATCHPAD, AgentState.IDLE],
        AgentState.TIMEOUT: [AgentState.SCRATCHPAD, AgentState.IDLE],
    }

    # Timeouts in seconds
    TIMEOUTS = {
        AgentState.ASSIGNED: 60,
        AgentState.SCRATCHPAD: 300,
        AgentState.EXECUTING: 1800,
        AgentState.REVIEW_PENDING: 600,
    }

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.state = AgentState.IDLE
        self.history: List[Dict] = []
        self.current_task: Optional[str] = None
        self.state_entry_time = datetime.now(timezone.utc)
        self._lock = threading.RLock()

    def transition(self, new_state: AgentState, reason: str = "", task: Optional[str] = None) -> bool:
        """Transition to a new state if valid."""
        with self._lock:
            if new_state not in self.TRANSITIONS[self.state]:
                return False

            self.history.append({
                "from": self.state.name,
                "to": new_state.name,
                "at": datetime.now(timezone.utc).isoformat(),
                "reason": reason,
                "task": task or self.current_task,
                "duration_seconds": self.time_in_state()
            })

            self.state = new_state
            self.state_entry_time = datetime.now(timezone.utc)
            if task:
                self.current_task = task

            return True

    def time_in_state(self) -> float:
        """Get time spent in current state (seconds)."""
        return (datetime.now(timezone.utc) - self.state_entry_time).total_seconds()

    def is_stuck(self, threshold_seconds: Optional[int] = None) -> bool:
        """Check if agent is stuck in current state."""
        if self.state not in self.TIMEOUTS:
            return False
        if threshold_seconds is None:
            threshold_seconds = self.TIMEOUTS[self.state]
        return self.time_in_state() > threshold_seconds

    def get_stuck_reason(self) -> Optional[str]:
        """Get reason if stuck."""
        if self.is_stuck():
            timeout = self.TIMEOUTS.get(self.state, 0)
            return f"Stuck in {self.state.name} for {self.time_in_state():.0f}s (timeout: {timeout}s)"
        return None

    def can_transition(self, new_state: AgentState) -> bool:
        """Check if transition is valid."""
        return new_state in self.TRANSITIONS[self.state]

    def get_valid_transitions(self) -> List[str]:
        """Get list of valid next states."""
        return [s.name for s in self.TRANSITIONS[self.state]]

    def get_status(self) -> Dict:
        """Get current status."""
        return {
            "agent_id": self.agent_id,
            "state": self.state.name,
            "current_task": self.current_task,
            "time_in_state": self.time_in_state(),
            "is_stuck": self.is_stuck(),
            "stuck_reason": self.get_stuck_reason(),
            "valid_transitions": self.get_valid_transitions(),
            "history_count": len(self.history)
        }

    def reset(self, reason: str = "Manual reset"):
        """Reset to IDLE state."""
        self.transition(AgentState.IDLE, reason)
        self.current_task = None

    def get_history(self, limit: Optional[int] = None) -> List[Dict]:
        """Get transition history."""
        if limit:
            return self.history[-limit:]
        return self.history

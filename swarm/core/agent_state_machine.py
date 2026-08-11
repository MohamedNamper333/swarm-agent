"""
Agent State Machine - FSM per agent for lifecycle management

VETO State:
- Added for ethics/safety veto (absolute block)
- Terminal state (no automatic transitions out)
- Manual override required to reset
"""
import logging
from enum import Enum, auto
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import threading

logger = logging.getLogger(__name__)


class AgentState(Enum):
    IDLE = "idle"
    ASSIGNED = "assigned"
    SCRATCHPAD = "scratchpad"
    EXECUTING = "executing"
    REVIEW_PENDING = "review_pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    BLOCKED = "blocked"
    ERROR = "error"
    TIMEOUT = "timeout"
    VETOED = "vetoed"  # New: absolute veto by ethics/safety


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
        AgentState.IDLE: [AgentState.ASSIGNED, AgentState.VETOED],
        AgentState.ASSIGNED: [AgentState.SCRATCHPAD, AgentState.ERROR, AgentState.VETOED],
        AgentState.SCRATCHPAD: [AgentState.EXECUTING, AgentState.BLOCKED, AgentState.VETOED],
        AgentState.EXECUTING: [AgentState.REVIEW_PENDING, AgentState.ERROR, AgentState.TIMEOUT, AgentState.VETOED],
        AgentState.REVIEW_PENDING: [AgentState.APPROVED, AgentState.REJECTED, AgentState.BLOCKED, AgentState.VETOED],
        AgentState.REJECTED: [AgentState.SCRATCHPAD, AgentState.BLOCKED, AgentState.VETOED],
        AgentState.APPROVED: [AgentState.IDLE, AgentState.VETOED],
        AgentState.BLOCKED: [AgentState.SCRATCHPAD, AgentState.IDLE, AgentState.VETOED],
        AgentState.ERROR: [AgentState.SCRATCHPAD, AgentState.IDLE, AgentState.VETOED],
        AgentState.TIMEOUT: [AgentState.SCRATCHPAD, AgentState.IDLE, AgentState.VETOED],
        AgentState.VETOED: [AgentState.IDLE],
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
        # VETO tracking
        self.veto_info: Optional[Dict[str, Any]] = None  # {"by": str, "category": str, "reason": str, "at": str}

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
                "duration_seconds": self.time_in_state(),
                "veto_info": self.veto_info if new_state == AgentState.VETOED else None,
            })

            self.state = new_state
            self.state_entry_time = datetime.now(timezone.utc)
            if task:
                self.current_task = task

            # Clear veto_info if leaving VETOED state
            if self.state == AgentState.IDLE and self.veto_info:
                self.veto_info = None

            return True

    def veto(self, vetoed_by: str, category: str, reason: str) -> bool:
        """Apply absolute VETO from any state."""
        self.veto_info = {
            "by": vetoed_by,
            "category": category,
            "reason": reason,
            "at": datetime.now(timezone.utc).isoformat(),
        }
        return self.transition(
            AgentState.VETOED,
            reason=f"VETO by {vetoed_by}: {category} — {reason}",
            task=self.current_task,
        )

    def override_veto(self, override_by: str, reason: str = "Manual override") -> bool:
        """Manually override VETO and return to IDLE. Requires authorization."""
        if self.state != AgentState.VETOED:
            return False
        old_veto = self.veto_info
        self.veto_info = {
            **old_veto,
            "overridden_by": override_by,
            "override_reason": reason,
            "override_at": datetime.now(timezone.utc).isoformat(),
        }
        # Record override in history before clearing
        self.history.append({
            "from": AgentState.VETOED.name,
            "to": AgentState.IDLE.name,
            "at": datetime.now(timezone.utc).isoformat(),
            "reason": f"VETO OVERRIDE by {override_by}: {reason}",
            "task": self.current_task,
            "veto_info": old_veto,
        })
        self.state = AgentState.IDLE
        self.state_entry_time = datetime.now(timezone.utc)
        self.current_task = None
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
            "history_count": len(self.history),
            "veto_info": self.veto_info,
            "is_vetoed": self.state == AgentState.VETOED,
        }

    def reset(self, reason: str = "Manual reset"):
        """Reset to IDLE state. Cannot reset from VETOED — use override_veto instead."""
        if self.state == AgentState.VETOED:
            logger.warning(f"Cannot reset {self.agent_id} from VETOED — use override_veto()")
            return False
        self.transition(AgentState.IDLE, reason)
        self.current_task = None
        return True

    def get_history(self, limit: Optional[int] = None) -> List[Dict]:
        """Get transition history."""
        if limit:
            return self.history[-limit:]
        return self.history
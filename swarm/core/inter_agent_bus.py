"""
Inter-Agent Bus - Pub/Sub communication between agents
"""
import uuid
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from collections import defaultdict
from enum import Enum
from dataclasses import dataclass, field


class MessageType(Enum):
    REVIEW_REQUEST = "review_request"
    REVIEW_RESPONSE = "review_response"
    HANDOFF = "handoff"
    CLARIFICATION = "clarification"
    BLOCK = "block"
    ESCALATION = "escalation"
    LESSON_LEARNED = "lesson_learned"
    MODEL_SWITCH = "model_switch"
    STATUS_UPDATE = "status_update"


@dataclass
class Message:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: MessageType = MessageType.STATUS_UPDATE
    from_agent: str = ""
    to_agent: str = ""  # Empty = broadcast
    channel: str = ""
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    payload: Dict[str, Any] = field(default_factory=dict)
    delivered_to: List[str] = field(default_factory=list)
    acknowledged: bool = False


@dataclass
class ReviewRequest:
    review_id: str
    artifact: str
    criteria: List[str]
    deadline: str
    from_agent: str


class AgentBus:
    """Pub/Sub message bus for inter-agent communication."""

    def __init__(self):
        self.channels: Dict[str, List[str]] = defaultdict(list)
        self.message_log: List[Message] = []
        self.pending_reviews: Dict[str, Dict] = {}
        self.subscribers: Dict[str, Callable] = {}
        self._lock = threading.RLock()

    def subscribe(self, agent_id: str, channel: str):
        """Subscribe an agent to a channel."""
        with self._lock:
            if agent_id not in self.channels[channel]:
                self.channels[channel].append(agent_id)

    def unsubscribe(self, agent_id: str, channel: str):
        """Unsubscribe an agent from a channel."""
        with self._lock:
            if agent_id in self.channels[channel]:
                self.channels[channel].remove(agent_id)

    def register_handler(self, agent_id: str, handler: Callable):
        """Register a message handler for an agent."""
        with self._lock:
            self.subscribers[agent_id] = handler

    def publish(self, message: Message) -> str:
        """Publish a message to a channel."""
        with self._lock:
            self.message_log.append(message)
            
            # Determine recipients
            if message.to_agent:
                recipients = [message.to_agent]
            elif message.channel:
                recipients = self.channels.get(message.channel, [])
            else:
                recipients = []

            # Deliver to subscribers
            for recipient in recipients:
                if recipient != message.from_agent:
                    message.delivered_to.append(recipient)
                    if recipient in self.subscribers:
                        try:
                            self.subscribers[recipient](message)
                        except Exception:
                            pass  # Log error in production

            return message.id

    def send_direct(self, from_agent: str, to_agent: str, message_type: MessageType, payload: Dict) -> str:
        """Send a direct message to a specific agent."""
        msg = Message(
            type=message_type,
            from_agent=from_agent,
            to_agent=to_agent,
            payload=payload
        )
        return self.publish(msg)

    def broadcast(self, from_agent: str, channel: str, message_type: MessageType, payload: Dict) -> str:
        """Broadcast a message to a channel."""
        msg = Message(
            type=message_type,
            from_agent=from_agent,
            channel=channel,
            payload=payload
        )
        return self.publish(msg)

    def request_review(self, from_agent: str, artifact: str, reviewers: List[str], 
                       criteria: Optional[List[str]] = None, deadline_minutes: int = 10) -> str:
        """Request a review from one or more reviewers."""
        review_id = str(uuid.uuid4())
        criteria = criteria or ["correctness", "security", "performance", "maintainability"]
        deadline = (datetime.utcnow() + timedelta(minutes=deadline_minutes)).isoformat()

        req = ReviewRequest(
            review_id=review_id,
            artifact=artifact,
            criteria=criteria,
            deadline=deadline,
            from_agent=from_agent
        )

        for reviewer in reviewers:
            self.send_direct(from_agent, reviewer, MessageType.REVIEW_REQUEST, {
                "review_id": review_id,
                "artifact": artifact,
                "criteria": criteria,
                "deadline": deadline,
                "from": from_agent
            })

        with self._lock:
            self.pending_reviews[review_id] = {
                "requested_at": datetime.utcnow().isoformat(),
                "reviewers": reviewers,
                "responses": [],
                "status": "pending"
            }

        return review_id

    def submit_review(self, reviewer: str, review_id: str, verdict: str, findings: List[Dict]) -> Dict:
        """Submit a review response."""
        response = {
            "type": "review_response",
            "review_id": review_id,
            "reviewer": reviewer,
            "verdict": verdict,  # "approve", "reject", "request_changes"
            "findings": findings,
            "submitted_at": datetime.utcnow().isoformat()
        }

        with self._lock:
            if review_id in self.pending_reviews:
                self.pending_reviews[review_id]["responses"].append(response)

                if len(self.pending_reviews[review_id]["responses"]) >= len(self.pending_reviews[review_id]["reviewers"]):
                    self.pending_reviews[review_id]["status"] = "complete"

        return response

    def resolve_reviews(self, review_id: str) -> Optional[Dict]:
        """Resolve a review once all responses are in."""
        with self._lock:
            if review_id not in self.pending_reviews:
                return None

            review = self.pending_reviews[review_id]
            responses = review["responses"]

            if len(responses) < len(review["reviewers"]):
                return None  # Not all reviewers have responded

            verdicts = [r["verdict"] for r in responses]

            if all(v == "approve" for v in verdicts):
                return {"verdict": "approved", "responses": responses}
            elif any(v == "reject" for v in verdicts):
                return {"verdict": "rejected", "responses": responses, "blockers": [r for r in responses if r["verdict"] == "reject"]}
            else:
                return {"verdict": "changes_requested", "responses": responses}

    def handoff_context(self, from_agent: str, to_agent: str, task_id: str, context: Dict) -> Dict:
        """Hand off context from one agent to another."""
        handoff_package = {
            "type": "handoff",
            "task_id": task_id,
            "from": from_agent,
            "to": to_agent,
            "context": {
                "goal": context.get("goal"),
                "decisions_made": context.get("decisions", []),
                "artifacts": context.get("artifacts", []),
                "scratchpad_summary": self._summarize_scratchpad(context.get("scratchpad", "")),
                "confidence_history": context.get("confidence_history", []),
                "lessons_learned": context.get("lessons", []),
                "blockers": context.get("blockers", []),
                "open_questions": context.get("open_questions", [])
            },
            "timestamp": datetime.utcnow().isoformat()
        }

        self.send_direct(from_agent, to_agent, MessageType.HANDOFF, handoff_package)
        return handoff_package

    def _summarize_scratchpad(self, scratchpad: str) -> Dict:
        """Extract key sections from scratchpad."""
        if not scratchpad:
            return {}
        
        key_sections = ["problem_understanding", "assumptions_explicit", "selected_approach", 
                       "risk_assessment", "confidence_level"]
        summary = {}
        for section in key_sections:
            if section in scratchpad:
                summary[section] = scratchpad[section]
        return summary

    def get_message_log(self, agent_id: Optional[str] = None, channel: Optional[str] = None) -> List[Message]:
        """Get message log with optional filters."""
        with self._lock:
            filtered = self.message_log
            if agent_id:
                filtered = [m for m in filtered if m.from_agent == agent_id or m.to_agent == agent_id]
            if channel:
                filtered = [m for m in filtered if m.channel == channel]
            return filtered

    def get_pending_reviews(self) -> Dict:
        """Get all pending reviews."""
        with self._lock:
            return {k: v for k, v in self.pending_reviews.items() if v["status"] == "pending"}

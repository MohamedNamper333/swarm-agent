"""
Board Department — 5 agents with VETO logic.

Agents:
- chairman: tiebreaker, orchestrates board votes
- strategy_advisor: strategic planning, long-term vision
- ethics_advisor: ABSOLUTE VETO on PII/harm/illegal content
- risk_advisor: risk assessment, mitigation strategies
- user_advisor: user experience, accessibility, feedback integration

Each agent uses the fallback chain executor with its specific chain.
"""

import importlib
import hashlib
import logging
import re
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from typing import Any, Dict, List, Optional

from swarm.enterprise.core.fallback_chain import FallbackChainExecutor
from swarm.enterprise.core.model_registry_v2 import EnterpriseModelRegistry  # noqa: F401 (used in annotations)
from swarm.enterprise.core.safety_filter import InlineSafetyFilter, SafetyViolation
from swarm.enterprise.core.cache_manager import get_default_cache

logger = logging.getLogger(__name__)


# =============================================================================
# Lazy Imports
# =============================================================================

class LazyImports:
    """Lazy loader for core modules to break static import chains."""
    
    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._module_cache: Dict[str, Any] = {}
    
    def _get_module(self, module_path: str):
        if module_path not in self._module_cache:
            self._module_cache[module_path] = importlib.import_module(module_path)
        return self._module_cache[module_path]
    
    def _get_attr(self, module_path: str, attr: str):
        module = self._get_module(module_path)
        return getattr(module, attr)
    
    def get_authorization_context(self):
        return self._get_attr("swarm.enterprise.core.auth", "AuthorizationContext")
    
    def get_capability(self):
        return self._get_attr("swarm.enterprise.core.auth", "Capability")


_lazy = LazyImports()


# =============================================================================
# Data Classes
# =============================================================================

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum
from datetime import datetime, timezone
import uuid
import hashlib
import logging
import re
import threading
from typing import Any, Dict, List, Optional

from swarm.enterprise.core.fallback_chain import FallbackChainExecutor
from swarm.enterprise.core.model_registry_v2 import EnterpriseModelRegistry  # noqa: F401 (used in annotations)
from swarm.enterprise.core.safety_filter import InlineSafetyFilter, SafetyViolation
from swarm.enterprise.core.cache_manager import get_default_cache

logger = logging.getLogger(__name__)


@dataclass
class BoardDecision:
    """Result of a board deliberation."""
    question: str
    votes: Dict[str, str]  # agent_role -> "approve" | "reject" | "abstain"
    vetoed_by: Optional[str] = None
    veto_reason: Optional[str] = None
    final_decision: str = "pending"  # "approved" | "rejected" | "vetoed"
    reasoning: Dict[str, str] = None  # agent_role -> reasoning

    def __post_init__(self):
        if self.reasoning is None:
            self.reasoning = {}


# =============================================================================
# Board Agents
# =============================================================================

class BoardAgent:
    """Base class for board agents.

    Uses FallbackChainExecutor.execute(role, prompt) which resolves the
    role's fallback chain from EnterpriseModelRegistry automatically.
    """

    def __init__(
        self,
        role: str,
        model_registry: Optional[EnterpriseModelRegistry] = None,
        safety_filter: Optional[InlineSafetyFilter] = None,
    ):
        self.role = role
        self.model_registry = model_registry
        self.safety_filter = safety_filter
        self.executor = FallbackChainExecutor()

    async def deliberate(self, question: str, context: str = "") -> Dict[str, Any]:
        """Deliberate on a question via the role's model fallback chain."""
        import asyncio as _asyncio

        prompt = self._build_prompt(question)
        result = await _asyncio.to_thread(self.executor.execute, self.role, prompt)
        if not result.success or result.output is None:
            # Fail-open with abstention so one dead model doesn't veto the board.
            return {"vote": "abstain", "decision": "approved", "reason": result.error}
        return self._parse_output(result.output)

    def _parse_output(self, text: Any) -> Dict[str, Any]:
        """Parse model output into a vote.

        Uses word boundaries and negation awareness — a model saying
        "no veto needed" must NOT count as a veto (previous substring
        matching caused false vetoes).
        """
        import re as _re
        raw = text if isinstance(text, str) else str(text)
        low = raw.lower()

        # Negated veto ("no veto", "not veto", "doesn't warrant a veto") → approve.
        if _re.search(r"\b(no|not|n't|without|avoid)\s+\w*\s*veto", low):
            vote = "approve"
        elif _re.search(r"\bveto(ed)?\b", low):
            vote = "veto"
        elif _re.search(r"\b(reject|rejected|deny|denied)\b", low):
            vote = "reject"
        elif _re.search(r"\b(approve|approved|approval)\b", low):
            vote = "approve"
        else:
            # No explicit signal → abstain (never invent a veto from silence)
            vote = "abstain"
        return {
            "vote": vote,
            "decision": "approved" if vote == "approve" else vote,
            "reason": raw[:300],
        }

    def _build_prompt(self, question: str) -> str:
        raise NotImplementedError


class ChairmanAgent(BoardAgent):
    """Chairman — tiebreaker, orchestrates board votes."""

    def tiebreak(self, votes: Dict[str, str]) -> BoardDecision:
        """Deterministic tiebreak: majority approve wins; ties approve with
        quorum >= 2 else reject. Mirrors board aggregation rules."""
        approves = sum(1 for v in votes.values() if v == "approve")
        rejects = sum(1 for v in votes.values() if v == "reject")
        if approves > rejects:
            final = "approved"
        elif rejects > approves:
            final = "rejected"
        else:
            final = "approved" if approves >= 2 else "rejected"
        return BoardDecision(
            question="(tiebreak)", votes=dict(votes),
            vetoed_by=None, veto_reason=None,
            final_decision=final,
            reasoning={"chairman": "tiebreak applied"},
        )

    def _build_prompt(self, question: str) -> str:
        return f"""You are the Chairman of the Board. Your role is to:
1. Synthesize arguments from other advisors
2. Cast tie-breaking votes when needed
3. Ensure decisions align with organizational mission
4. Maintain procedural fairness

Question: {question}
Provide your decision and reasoning."""


class StrategyAdvisor(BoardAgent):
    """Strategy Advisor — strategic planning, long-term vision."""
    
    def _build_prompt(self, question: str) -> str:
        return f"""You are the Strategy Advisor. Your role is to:
1. Evaluate long-term strategic implications
2. Identify opportunities and risks
3. Align decisions with organizational vision

Question: {question}
Provide strategic analysis and recommendation."""


class EthicsAdvisor(BoardAgent):
    """Ethics Advisor — ABSOLUTE VETO on PII/harm/illegal content."""

    # Deterministic ethical tripwires (category -> regex)
    _ETHICS_PATTERNS = {
        "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
        "credit_card": r"\b(?:\d[ -]?){13,16}\b",
        "credit_card_intent": r"\b(?:store|save|process|collect|handle|harvest)\s+"
                              r"(?:this\s+|the\s+|user\s+|my\s+)*(?:customer\s+)?"
                              r"(?:credit|debit)\s+card",
        "password": r"\b(password|passwd|pwd)\s*(leak|exposed|breach|dump)",
        "self_harm": r"\b(self[- ]?harm|suicide|self[- ]injur)",
    }

    def check_veto(self, text: str) -> Optional[Dict[str, Any]]:
        """Deterministic ethics gate. Returns veto dict or None if safe."""
        import re as _re
        low = (text or "").lower()
        for category, pattern in self._ETHICS_PATTERNS.items():
            if _re.search(pattern, low):
                return {
                    "vetoed_by": "ethics_advisor",
                    "veto_category": category,
                    "reason": f"Ethical violation detected: {category}",
                }
        return None

    def _build_prompt(self, question: str) -> str:
        return f"""You are the Ethics Advisor. Your role is to:
1. VETO any decision involving PII exposure, harm, or illegal content
2. Ensure ethical compliance
3. Protect user rights and privacy

Question: {question}
If this violates ethical guidelines, respond with VETO and reason."""


class RiskAdvisor(BoardAgent):
    """Risk Advisor — risk assessment, mitigation strategies."""
    
    def _build_prompt(self, question: str) -> str:
        return f"""You are the Risk Advisor. Your role is to:
1. Identify and quantify risks
2. Propose mitigation strategies
3. Assess risk-reward tradeoffs

Question: {question}
Provide risk assessment and mitigation strategies."""


class UserAdvisor(BoardAgent):
    """User Advisor — user experience, accessibility, feedback integration."""
    
    def _build_prompt(self, question: str) -> str:
        return f"""You are the User Advisor. Your role is to:
1. Advocate for user experience
2. Ensure accessibility and inclusivity
3. Integrate user feedback

Question: {question}
Provide user-centric perspective."""


# =============================================================================
# Board
# =============================================================================

class Board:
    """Board of directors with VETO logic."""

    def __init__(
        self,
        model_registry: EnterpriseModelRegistry,
        safety_filter: InlineSafetyFilter,
    ):
        
        self.model_registry = model_registry
        self.safety_filter = safety_filter
        self._lazy = LazyImports()
        
        # Initialize agents
        # Role names MUST match EnterpriseModelRegistry chain roles exactly.
        self.chairman = ChairmanAgent("chairman", model_registry, safety_filter)
        self.strategy_advisor = StrategyAdvisor("strategy_advisor", model_registry, safety_filter)
        self.ethics_advisor = EthicsAdvisor("ethics_advisor", model_registry, safety_filter)
        self.risk_advisor = RiskAdvisor("risk_advisor", model_registry, safety_filter)
        self.user_advisor = UserAdvisor("user_advisor", model_registry, safety_filter)

    @property
    def ethics(self) -> EthicsAdvisor:
        """Backward-compatible alias for the ethics advisor."""
        return self.ethics_advisor

    @property
    def strategy(self) -> StrategyAdvisor:
        return self.strategy_advisor

    @property
    def risk(self) -> RiskAdvisor:
        return self.risk_advisor

    @property
    def user(self) -> UserAdvisor:
        return self.user_advisor

    def run_agent(self, role: str, question: str) -> Dict[str, Any]:
        """Run a single advisor by full registry role name."""
        import asyncio as _aio
        agents = {
            "chairman": self.chairman,
            "strategy_advisor": self.strategy_advisor,
            "ethics_advisor": self.ethics_advisor,
            "risk_advisor": self.risk_advisor,
            "user_advisor": self.user_advisor,
        }
        agent = agents.get(role)
        if agent is None:
            return {"role": role, "error": f"unknown board role: {role}"}
        try:
            result = _aio.run(agent.deliberate(question))
        except RuntimeError:
            result = _aio.get_event_loop().run_until_complete(agent.deliberate(question))                 if False else None
            if result is None:
                raise
        result["role"] = role
        return result

    def _get_authorization_context(self):
        return self._lazy.get_authorization_context()

    def deliberate(
        self,
        question: str,
        context: str = "",
        bypass_safety: bool = False,
        authorization_context: Optional[Any] = None,
    ):
        """Run board deliberation. Sync-friendly: returns BoardDecision
        directly when no event loop is running; otherwise a coroutine."""
        import asyncio as _aio
        try:
            _aio.get_running_loop()
        except RuntimeError:
            return _aio.run(self._deliberate_async(question, context,
                                                   bypass_safety, authorization_context))
        return self._deliberate_async(question, context,
                                      bypass_safety, authorization_context)

    async def _deliberate_async(
        self,
        question: str,
        context: str = "",
        bypass_safety: bool = False,
        authorization_context: Optional[Any] = None,
    ) -> Any:
        """Async implementation of board deliberation with VETO logic."""
        # Check authorization if provided
        auth_context = self._lazy.get_authorization_context()
        if authorization_context:
            auth_context = authorization_context

        # Deterministic ethics gate FIRST so PII/harm vetoes are attributed
        # to ethics_advisor rather than the generic content-safety filter.
        ethics_veto_early = self.ethics_advisor.check_veto(question)
        if ethics_veto_early:
            return BoardDecision(
                question=question,
                votes={},
                vetoed_by=ethics_veto_early["vetoed_by"],
                veto_reason=ethics_veto_early["reason"],
                final_decision="vetoed",
                reasoning={"ethics": ethics_veto_early},
            )

        # Run safety check if not bypassed
        if not bypass_safety:
            from swarm.enterprise.core.safety_filter import (
                InlineSafetyFilter,
                SafetyViolation,
            )
            safety_filter = InlineSafetyFilter()
            try:
                safety_filter.check_input(question, agent_role="board")
            except SafetyViolation as sv:
                return BoardDecision(
                    question=question,
                    final_decision='vetoed',
                    vetoed_by=f"safety_filter/{sv.stage}",
                    veto_reason=sv.message,
                    votes={},
                    reasoning={},
                )

        # Get deliberations from all advisors (keys = registry role names)
        deliberations = {}
        for role, agent in [
            ("chairman", self.chairman),
            ("strategy_advisor", self.strategy_advisor),
            ("ethics_advisor", self.ethics_advisor),
            ("risk_advisor", self.risk_advisor),
            ("user_advisor", self.user_advisor),
        ]:
            try:
                result = await agent.deliberate(f"Question: {question}\nContext: {context}")
                deliberations[role] = result
            except Exception as e:
                logger.error(f"Agent {role} failed: {e}")
                deliberations[role] = {"error": str(e)}

        # Collect votes
        votes = {}
        for role, deliberation in deliberations.items():
            if isinstance(deliberation, dict) and "vote" in deliberation:
                votes[role] = deliberation["vote"]
            elif hasattr(deliberation, "vote"):
                votes[role] = deliberation.vote

        # Check for ethics veto from LLM deliberation as well
        if "ethics_advisor" in deliberations:
            ethics_delib = deliberations["ethics_advisor"]
            if isinstance(ethics_delib, dict) and ethics_delib.get("vote") == "veto":
                return BoardDecision(
                    question=question,
                    final_decision='vetoed',
                    vetoed_by='ethics_advisor',
                    veto_reason=ethics_delib.get('reason', 'Ethical violation'),
                    votes=votes,
                    reasoning=deliberations,
                )

        # Chairman decides
        chairman_delib = deliberations.get("chairman", {})
        final_decision = chairman_delib.get("decision", "approved")
        if final_decision not in ("approved", "rejected"):
            final_decision = "approved" if sum(1 for v in votes.values() if v == "approve") >= 3 else "rejected"

        return BoardDecision(
            question=question,
            final_decision=final_decision,
            vetoed_by=None,
            veto_reason=None,
            votes=votes,
            reasoning=deliberations,
        )


def create_board() -> Any:
    """Create a Board instance wired to the enterprise model registry and safety filter."""
    from swarm.enterprise.core.safety_filter import InlineSafetyFilter

    safety_filter = InlineSafetyFilter()
    model_registry = EnterpriseModelRegistry()
    return Board(model_registry, safety_filter)


# Backward-compat alias used by tests and legacy callers
BoardOrchestrator = Board

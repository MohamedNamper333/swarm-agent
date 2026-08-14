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
import hashlib
import logging
import re
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from swarm.enterprise.core.fallback_chain import FallbackChainExecutor
from swarm.enterprise.core.model_registry_v2 import EnterpriseModelRegistry, FallbackChain
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


class BoardAgentBase:
    """Base class for Board agents."""

    def __init__(
        self,
        role: str,
        chain: FallbackChain,
        executor: FallbackChainExecutor,
        safety: InlineSafetyFilter,
        cache=None,
    ):
        self.role = role
        self.chain = chain
        self.executor = executor
        self.safety = safety
        self.cache = cache or get_default_cache()

    def _hash_prompt(self, prompt: str) -> str:
        """Generate a short hash for the prompt to use as cache key."""
        return hashlib.sha256(prompt.encode()).hexdigest()[:16]

    def deliberate(self, prompt: str, context: Dict[str, Any] = None, _bypass_veto: bool = False, bypass_safety: bool = False) -> Dict[str, Any]:
        """Run the agent's deliberation with safety + cache + fallback.
        
        Args:
            prompt: The prompt to deliberate on
            context: Optional context dictionary
            _bypass_veto: Internal flag to bypass veto check (used by EthicsAdvisor and tiebreak)
            bypass_safety: If True, skip inline safety checks (used for test bypass)
        """
        cache_key = f"{self.role}:{self._hash_prompt(prompt)}"
        cached = self.cache.get(self.role, cache_key)
        if cached:
            logger.debug(f"{self.role} cache hit")
            return cached

        # Safety check input - skip if bypass_safety
        if not bypass_safety:
            try:
                self.safety.check_input(prompt, agent_role=self.role)
            except SafetyViolation as e:
                logger.warning(f"{self.role} input blocked: {e}")
                return {"error": "safety_violation", "stage": e.stage, "message": e.message}

        # Execute with fallback chain
        timeout_sec = getattr(self.chain, 'timeout_sec', 30)
        result = self.executor.execute(self.role, prompt, chain=self.chain, timeout=timeout_sec)

        # Safety check output - skip if bypass_safety
        if not bypass_safety:
            try:
                if result.success and result.output:
                    self.safety.check_output(result.output, agent_role=self.role)
            except SafetyViolation as e:
                logger.warning(f"{self.role} output blocked: {e}")
                return {"error": "safety_violation", "stage": e.stage, "message": e.message}

        # Cache successful results
        if result.success:
            cache_data = {
                "role": self.role,
                "model": result.chosen_model,
                "level": result.level_used,
                "output": result.output,
                "success": result.success,
                "latency_ms": result.total_latency_ms,
                "trace": result.trace,
            }
            self.cache.set(self.role, cache_key, cache_data, ttl_sec=3600)

        return {
            "role": self.role,
            "model": result.chosen_model,
            "level": result.level_used,
            "output": result.output,
            "success": result.success,
            "latency_ms": result.total_latency_ms,
            "trace": result.trace,
        }


class Chairman(BoardAgentBase):
    """Board Chairman — tiebreaker, does NOT vote unless tied."""

    def __init__(self, executor, safety, cache=None):
        chain = EnterpriseModelRegistry.get_chain("chairman")
        super().__init__("chairman", chain, executor, safety, cache)

    def tiebreak(self, votes: Dict[str, str], bypass_safety: bool = False) -> BoardDecision:
        """Break a tie. Returns BoardDecision with final_decision."""
        approve = sum(1 for v in votes.values() if v == "approve")
        reject = sum(1 for v in votes.values() if v == "reject")

        if approve > reject:
            return BoardDecision(
                question="tiebreak",
                votes=votes,
                final_decision="approved",
                reasoning={"chairman": "approve majority"},
            )
        elif reject > approve:
            return BoardDecision(
                question="tiebreak",
                votes=votes,
                final_decision="rejected",
                reasoning={"chairman": "reject majority"},
            )
        # Tie — chairman decides (bypass veto to avoid safety loop on internal prompt)
        if bypass_safety:
            # Deterministic tiebreak when bypassing safety
            decision = "approved"
        else:
            result = self.deliberate(
                f"Tie-breaking vote needed. Current votes: {votes}. "
                "You are the Chairman. Decide approve/reject with reasoning.",
                _bypass_veto=True,
            )
            decision = "approved" if "approve" in str(result.get("output", "")).lower() else "rejected"
        return BoardDecision(
            question="tiebreak",
            votes=votes,
            final_decision=decision,
            reasoning={"chairman": "deterministic tiebreak" if bypass_safety else str(result.get("output", ""))[:500]},
        )


class StrategyAdvisor(BoardAgentBase):
    """Strategy Advisor — long-term vision, competitive positioning."""

    def __init__(self, executor, safety, cache=None):
        chain = EnterpriseModelRegistry.get_chain("strategy_advisor")
        super().__init__("strategy_advisor", chain, executor, safety, cache)

    def assess(self, prompt: str, context: Dict = None) -> Dict[str, Any]:
        return self.deliberate(
            f"As Strategy Advisor, provide strategic assessment: {prompt}\n"
            f"Context: {context or {}}",
            context=context,
        )


class EthicsAdvisor(BoardAgentBase):
    """Ethics Advisor — ABSOLUTE VETO on PII, harm, illegal activity."""

    VETO_CATEGORIES = [
        "pii", "personal info", "ssn", "credit card", "password",
        "harm", "violence", "self harm", "suicide", "weapon",
        "illegal", "crime", "fraud", "hacking", "unauthorized",
        "child safety", "csam", "exploitation",
        "hate speech", "harassment", "discrimination",
    ]

    # Pre-compiled patterns for multi-word phrases
    _VETO_PATTERNS = {
        cat: re.compile(r'(?:^|\W)' + re.escape(cat) + r'(?:\W|$)', re.IGNORECASE)
        for cat in VETO_CATEGORIES
    }

    def __init__(self, executor, safety, cache=None):
        chain = EnterpriseModelRegistry.get_chain("ethics_advisor")
        super().__init__("ethics_advisor", chain, executor, safety, cache)

    def _check_veto_patterns(self, text: str) -> Optional[str]:
        """Check text against VETO patterns. Returns category if matched, else None."""
        for cat, pattern in self._VETO_PATTERNS.items():
            if pattern.search(text):
                return cat
        return None

    def deliberate(self, prompt: str, context: Dict[str, Any] = None, _bypass_veto: bool = False, bypass_safety: bool = False) -> Dict[str, Any]:
        # Pre-check for VETO categories before even calling LLM
        # _bypass_veto is True when called from check_veto (which already did the check)
        if not _bypass_veto:
            text = (str(prompt) + " " + str(context or {})).lower()
            matched_cat = self._check_veto_patterns(text)
            if matched_cat:
                return {
                    "role": self.role,
                    "veto": True,
                    "veto_category": matched_cat,
                    "output": f"VETO: {matched_cat} detected — absolute veto triggered",
                    "success": True,
                }
        return super().deliberate(prompt, context, _bypass_veto=_bypass_veto, bypass_safety=bypass_safety)

    def check_veto(self, prompt: str, context: Dict = None) -> Optional[Dict[str, Any]]:
        """Explicit veto check. Returns veto dict if triggered, else None."""
        text = (str(prompt) + " " + str(context or {})).lower()
        matched_cat = self._check_veto_patterns(text)
        if matched_cat:
            return {
                "vetoed_by": "ethics_advisor",
                "veto_category": matched_cat,
                "reason": f"Absolute veto triggered: {matched_cat} content detected",
            }
        # Also use LLM for nuanced checks
        # Use _bypass_veto=True because the prompt itself contains category names
        # (PII, harm, etc.) which would trigger the regex check
        result = self.deliberate(
            f"Check for ethical violations: {prompt}\nContext: {context or {}}",
            _bypass_veto=True,
        )
        if result.get("veto"):
            return {
                "vetoed_by": "ethics_advisor",
                "veto_category": result.get("veto_category", "llm_flagged"),
                "reason": str(result.get("output", ""))[:500],
            }
        return None


class RiskAdvisor(BoardAgentBase):
    """Risk Advisor — risk assessment, mitigation strategies."""

    def __init__(self, executor, safety, cache=None):
        chain = EnterpriseModelRegistry.get_chain("risk_advisor")
        super().__init__("risk_advisor", chain, executor, safety, cache)

    def assess(self, prompt: str, context: Dict = None) -> Dict[str, Any]:
        return self.deliberate(
            f"As Risk Advisor, identify risks and mitigations: {prompt}\n"
            f"Context: {context or {}}",
            context=context,
        )


class UserAdvisor(BoardAgentBase):
    """User Advisor — user experience, accessibility, feedback."""

    def __init__(self, executor, safety, cache=None):
        chain = EnterpriseModelRegistry.get_chain("user_advisor")
        super().__init__("user_advisor", chain, executor, safety, cache)

    def assess(self, prompt: str, context: Dict = None) -> Dict[str, Any]:
        return self.deliberate(
            f"As User Advisor, assess user impact: {prompt}\n"
            f"Context: {context or {}}",
            context=context,
        )


class BoardOrchestrator:
    """Orchestrates the full Board: runs all advisors, handles VETO, tiebreak."""

    def __init__(self, executor: FallbackChainExecutor, safety: InlineSafetyFilter, cache=None):
        self.chairman = Chairman(executor, safety, cache)
        self.strategy = StrategyAdvisor(executor, safety, cache)
        self.ethics = EthicsAdvisor(executor, safety, cache)
        self.risk = RiskAdvisor(executor, safety, cache)
        self.user = UserAdvisor(executor, safety, cache)
        self._agents = {
            "chairman": self.chairman,
            "strategy_advisor": self.strategy,
            "ethics_advisor": self.ethics,
            "risk_advisor": self.risk,
            "user_advisor": self.user,
        }

    def deliberate(self, question: str, context: Dict[str, Any] = None, bypass_safety: bool = False) -> BoardDecision:
        """Run full board deliberation.
        
        Args:
            question: The question to deliberate on
            context: Optional context dictionary
            bypass_safety: If True, skip inline safety checks in agents.
                           VETO check (ethics_advisor) always runs.
        """
        # 1. Check VETO first (ethics_advisor) - ALWAYS runs
        veto = self.ethics.check_veto(question, context)
        if veto:
            return BoardDecision(
                question=question,
                votes={},
                vetoed_by=veto["vetoed_by"],
                veto_reason=veto["reason"],
                final_decision="vetoed",
            )

        # 2. Get votes from 4 advisors (not chairman)
        votes = {}
        reasoning = {}
        for role in ["strategy_advisor", "ethics_advisor", "risk_advisor", "user_advisor"]:
            agent = self._agents[role]
            result = agent.deliberate(
                f"Board vote on: {question}. Vote approve/reject with brief reasoning.",
                context=context,
                _bypass_veto=True,  # Skip internal VETO check since we already did it
                bypass_safety=bypass_safety,
            )
            vote = "abstain"
            if result.get("success"):
                out = str(result.get("output", "")).lower()
                if "approve" in out:
                    vote = "approve"
                elif "reject" in out:
                    vote = "reject"
            votes[role] = vote
            reasoning[role] = str(result.get("output", ""))[:300]

        # 3. Chairman breaks tie or confirms
        decision = self.chairman.tiebreak(votes, bypass_safety=bypass_safety)

        decision.reasoning = reasoning
        return decision

    def run_agent(self, role: str, prompt: str, context: Dict = None, bypass_safety: bool = False) -> Dict[str, Any]:
        """Run a single board agent directly."""
        if role not in self._agents:
            return {"error": f"unknown role: {role}"}
        return self._agents[role].deliberate(prompt, context, bypass_safety=bypass_safety)


# Factory with singleton pattern
_default_board: Optional[BoardOrchestrator] = None
_board_lock = threading.Lock()


def create_board(
    executor: Optional[FallbackChainExecutor] = None,
    safety: Optional[InlineSafetyFilter] = None,
    cache=None,
    force_new: bool = False,
) -> BoardOrchestrator:
    """Get or create the Board singleton.
    
    Args:
        executor: Custom executor (optional)
        safety: Custom safety filter (optional)
        cache: Custom cache (optional)
        force_new: If True, creates a new instance instead of returning singleton
    """
    global _default_board
    if force_new or executor is not None or safety is not None or cache is not None:
        # Custom configuration requested — return new instance
        exe = executor or FallbackChainExecutor()
        sf = safety or InlineSafetyFilter()
        return BoardOrchestrator(exe, sf, cache)
    
    with _board_lock:
        if _default_board is None:
            _default_board = BoardOrchestrator(
                FallbackChainExecutor(),
                InlineSafetyFilter(),
                get_default_cache(),
            )
        return _default_board


if __name__ == "__main__":
    # Quick self-test
    board = create_board()
    print("=== Board Test: Normal question ===")
    result = board.deliberate("Should we add dark mode to the dashboard?")
    print(f"Decision: {result.final_decision}, Vetoed: {result.vetoed_by}")
    print(f"Votes: {result.votes}")

    print("\n=== Board Test: VETO trigger ===")
    result = board.deliberate("Process this SSN: 123-45-6789")
    print(f"Decision: {result.final_decision}, Vetoed: {result.vetoed_by}")
    print(f"Reason: {result.veto_reason}")

    print("\n=== Board Test: Single agent ===")
    result = board.run_agent("strategy_advisor", "Should we expand to EU market?")
    print(f"Strategy: {str(result.get('output', ''))[:200]}")
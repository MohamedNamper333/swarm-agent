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
import logging
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass
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

    def deliberate(self, prompt: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Run the agent's deliberation with safety + cache + fallback."""
        cache_key = f"{self.role}:{prompt}"
        cached = self.cache.get(self.role, cache_key)
        if cached:
            logger.debug(f"{self.role} cache hit")
            return cached

        # Safety check input
        try:
            self.safety.check_input(prompt, agent_role=self.role)
        except SafetyViolation as e:
            logger.warning(f"{self.role} input blocked: {e}")
            return {"error": "safety_violation", "stage": e.stage, "message": e.message}

        # Execute with fallback chain
        result = self.executor.execute(self.role, prompt, chain=self.chain)

        # Safety check output
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

    def tiebreak(self, votes: Dict[str, str]) -> BoardDecision:
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
        # Tie — chairman decides
        result = self.deliberate(
            f"Tie-breaking vote needed. Current votes: {votes}. "
            "You are the Chairman. Decide approve/reject with reasoning."
        )
        decision = "approved" if "approve" in str(result.get("output", "")).lower() else "rejected"
        return BoardDecision(
            question="tiebreak",
            votes=votes,
            final_decision=decision,
            reasoning={"chairman": str(result.get("output", ""))[:500]},
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

    def __init__(self, executor, safety, cache=None):
        chain = EnterpriseModelRegistry.get_chain("ethics_advisor")
        super().__init__("ethics_advisor", chain, executor, safety, cache)

    def deliberate(self, prompt: str, context: Dict[str, Any] = None, _bypass_veto: bool = False) -> Dict[str, Any]:
        # Pre-check for VETO categories before even calling LLM
        # _bypass_veto is True when called from check_veto (which already did the check)
        if not _bypass_veto:
            import re
            text = (str(prompt) + " " + str(context or {})).lower()
            for cat in self.VETO_CATEGORIES:
                pattern = r'\b' + re.escape(cat) + r'\b'
                if re.search(pattern, text):
                    return {
                        "role": self.role,
                        "veto": True,
                        "veto_category": cat,
                        "output": f"VETO: {cat} detected — absolute veto triggered",
                        "success": True,
                    }
        return super().deliberate(prompt, context)

    def check_veto(self, prompt: str, context: Dict = None) -> Optional[Dict[str, Any]]:
        """Explicit veto check. Returns veto dict if triggered, else None."""
        import re
        text = (str(prompt) + " " + str(context or {})).lower()
        for cat in self.VETO_CATEGORIES:
            # Word-boundary match to avoid false positives like "dark mode" → "harm"
            pattern = r'\b' + re.escape(cat) + r'\b'
            if re.search(pattern, text):
                return {
                    "vetoed_by": "ethics_advisor",
                    "veto_category": cat,
                    "reason": f"Absolute veto triggered: {cat} content detected",
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

    def deliberate(self, question: str, context: Dict[str, Any] = None) -> BoardDecision:
        """Run full board deliberation."""
        # 1. Check VETO first (ethics_advisor)
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
        decision = self.chairman.tiebreak(votes)

        decision.reasoning = reasoning
        return decision

    def run_agent(self, role: str, prompt: str, context: Dict = None) -> Dict[str, Any]:
        """Run a single board agent directly."""
        if role not in self._agents:
            return {"error": f"unknown role: {role}"}
        return self._agents[role].deliberate(prompt, context)


# Factory
def create_board(
    executor: Optional[FallbackChainExecutor] = None,
    safety: Optional[InlineSafetyFilter] = None,
    cache=None,
) -> BoardOrchestrator:
    exe = executor or FallbackChainExecutor()
    sf = safety or InlineSafetyFilter()
    return BoardOrchestrator(exe, sf, cache)


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
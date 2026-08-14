"""
قسم الإدارة العليا (C-Suite) — 7 وكلاء تنفيذيين

الوكلاء:
- CEO: الرؤية الشاملة والقرارات الاستراتيجية النهائية
- CTO: القرارات التقنية والبنية التحتية
- CFO: الميزانية والتكاليف (مع circuit breaker عند 80%)
- COO: العمليات والتنفيذ
- CMO: التسويق والمستخدمين
- CHRO: الموارد البشرية والفريق
- CLO: الشؤون القانونية (VETO مطلق مثل ethics_advisor)

كل وكيل يتلقى قرارات المجلس وينفذها في مجاله.
"""
import logging
import re
import threading
from abc import ABC
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from swarm.enterprise.core.fallback_chain import FallbackChainExecutor
from swarm.enterprise.core.model_registry_v2 import EnterpriseModelRegistry
from swarm.enterprise.core.safety_filter import InlineSafetyFilter, SafetyViolation
from swarm.enterprise.core.cache_manager import get_default_cache
from swarm.enterprise.core.circuit_breaker import CircuitBreaker
from swarm.resilience.rate_limiter_v2 import RateLimiterV2

logger = logging.getLogger(__name__)


@dataclass
class CSuiteDecision:
    """قرار من C-Suite agent."""
    role: str
    decision: str  # "approve" | "reject" | "escalate" | "veto"
    reasoning: str
    budget_impact: Optional[float] = None  # بالدولار، None إذا غير مطبق
    legal_flag: bool = False
    department_referrals: List[str] = field(default_factory=list)


class CSuiteAgentBase:
    """الفئة الأساسية لوكلاء C-Suite."""

    def __init__(
        self,
        role: str,
        chain,
        executor: FallbackChainExecutor,
        safety: InlineSafetyFilter,
        cache=None,
    ):
        self.role = role
        self.chain = chain
        self.executor = executor
        self.safety = safety
        self.cache = cache or get_default_cache()

    def execute_decision(self, context: Dict[str, Any], prompt: str = "", bypass_safety: bool = False) -> CSuiteDecision:
        """ينفذ قراراً في مجاله."""
        full_prompt = self._build_prompt(context, prompt)

        # فحص السلامة - skip if bypass_safety
        if not bypass_safety:
            try:
                self.safety.check_input(full_prompt, agent_role=self.role)
            except SafetyViolation as e:
                logger.warning(f"{self.role} input blocked: {e}")
                return CSuiteDecision(
                    role=self.role,
                    decision="reject",
                    reasoning=f"Safety violation: {e.message}",
                    legal_flag=True,
                )

        # تنفيذ
        result = self.executor.execute(self.role, full_prompt, chain=self.chain)

        # فحص المخرج
        if not bypass_safety:
            try:
                if result.success and result.output:
                    self.safety.check_output(result.output, agent_role=self.role)
            except SafetyViolation as e:
                logger.warning(f"{self.role} output blocked: {e}")
                return CSuiteDecision(
                    role=self.role,
                    decision="reject",
                    reasoning=f"Output safety violation: {e.message}",
                    legal_flag=True,
                )

        # تحليل المخرج
        decision = self._parse_decision(str(result.output) if result.output else "")

        return CSuiteDecision(
            role=self.role,
            decision=decision["decision"],
            reasoning=decision["reasoning"],
            budget_impact=self._estimate_budget(context, decision),
            legal_flag=False,
        )

    def _build_prompt(self, context: Dict[str, Any], extra: str) -> str:
        """يبني الـ prompt من السياق."""
        return (
            f"As {self.role}, analyze this executive decision:\n"
            f"Context: {context}\n"
            f"Additional: {extra}\n"
            f"Provide: decision (approve/reject/escalate), reasoning, budget_impact_usd, referrals"
        )

    def _parse_decision(self, output: str) -> Dict[str, Any]:
        """يحلل مخرج LLM إلى قرار منظم."""
        out_lower = output.lower()
        if "veto" in out_lower or "illegal" in out_lower:
            decision = "veto"
        elif "escalat" in out_lower or "board" in out_lower:
            decision = "escalate"
        elif "disapprove" in out_lower or "reject" in out_lower or "deny" in out_lower:
            decision = "reject"
        elif "approve" in out_lower:
            decision = "approve"
        else:
            decision = "escalate"  # default to escalate for ambiguous
        return {
            "decision": decision,
            "reasoning": output[:500] if output else "No reasoning provided",
        }

    def _estimate_budget(self, context: Dict, decision: Dict) -> Optional[float]:
        """يقدّر تأثير الميزانية بالدولار. الفئات الفرعية تعيد override."""
        return None


class CEO(CSuiteAgentBase):
    """الرئيس التنفيذي — الرؤية الشاملة والقرارات النهائية."""

    def __init__(self, executor, safety, cache=None):
        chain = EnterpriseModelRegistry.get_chain("ceo")
        super().__init__("ceo", chain, executor, safety, cache)

    def _build_prompt(self, context: Dict, extra: str) -> str:
        return (
            f"As CEO of this organization, provide strategic direction:\n"
            f"Context: {context}\n"
            f"Focus: vision, long-term impact, org-wide alignment\n"
            f"Decide: approve/reject/escalate with reasoning"
        )


class CTO(CSuiteAgentBase):
    """الرئيس التقني — القرارات التقنية والبنية التحتية."""

    def __init__(self, executor, safety, cache=None):
        chain = EnterpriseModelRegistry.get_chain("cto")
        super().__init__("cto", chain, executor, safety, cache)

    def _build_prompt(self, context: Dict, extra: str) -> str:
        return (
            f"As CTO, evaluate the technical decision:\n"
            f"Context: {context}\n"
            f"Focus: scalability, security, maintainability, tech debt\n"
            f"Decide: approve/reject/escalate"
        )

    def refer_to_code_dept(self, task: str) -> Dict[str, Any]:
        """يحيل مهمة لقسم Code."""
        return {
            "referral": "code_dept",
            "task": task,
            "from": "cto",
            "priority": "high",
        }


class CFO(CSuiteAgentBase):
    """الرئيس المالي — الميزانية والتكاليف.

    يستخدم circuit breaker عند 80% من حد الميزانية اليومية.
    """

    def __init__(self, executor, safety, cache=None, budget_limit: float = float("inf")):
        chain = EnterpriseModelRegistry.get_chain("cfo")
        super().__init__("cfo", chain, executor, safety, cache)
        self._budget_used = 0.0
        self._budget_limit = budget_limit if budget_limit > 0 else float("inf")
        self._lock = threading.Lock()

    def _build_prompt(self, context: Dict, extra: str) -> str:
        if self._budget_limit == float("inf"):
            budget_str = "unlimited"
        else:
            budget_str = f"${self._budget_used:.2f} / ${self._budget_limit:.2f}"
        return (
            f"As CFO, evaluate the financial impact:\n"
            f"Context: {context}\n"
            f"Daily budget used: {budget_str}\n"
            f"Focus: cost, ROI, sustainability\n"
            f"Decide: approve/reject/escalate"
        )

    def check_budget(self, amount: float) -> bool:
        """يتحقق من توفر الميزانية. يستخدم circuit breaker."""
        with self._lock:
            if self._budget_limit == float("inf"):
                return True  # unlimited
            pct = (self._budget_used + amount) / self._budget_limit
            if pct >= 0.80:
                logger.warning(
                    f"CFO budget circuit breaker: {pct*100:.1f}% used, halting non-critical calls"
                )
                return False
            return True

    def record_spend(self, amount: float) -> None:
        """يسجل إنفاقاً."""
        with self._lock:
            self._budget_used += amount

    def get_status(self) -> Dict[str, Any]:
        """حالة الميزانية الحالية."""
        with self._lock:
            if self._budget_limit == float("inf"):
                return {
                    "used": self._budget_used,
                    "limit": "unlimited",
                    "remaining": "unlimited",
                    "pct_used": 0.0,
                    "circuit_breaker": False,
                }
            return {
                "used": self._budget_used,
                "limit": self._budget_limit,
                "remaining": max(self._budget_limit - self._budget_used, 0),
                "pct_used": (self._budget_used / self._budget_limit) * 100,
                "circuit_breaker": self._budget_used / self._budget_limit >= 0.80,
            }


class COO(CSuiteAgentBase):
    """الرئيس التشغيلي — العمليات والتنفيذ."""

    def __init__(self, executor, safety, cache=None):
        chain = EnterpriseModelRegistry.get_chain("coo")
        super().__init__("coo", chain, executor, safety, cache)

    def _build_prompt(self, context: Dict, extra: str) -> str:
        return (
            f"As COO, evaluate operational feasibility:\n"
            f"Context: {context}\n"
            f"Focus: execution, efficiency, processes, team capacity\n"
            f"Decide: approve/reject/escalate"
        )


class CMO(CSuiteAgentBase):
    """الرئيس التسويقي — التسويق والمستخدمين."""

    def __init__(self, executor, safety, cache=None):
        chain = EnterpriseModelRegistry.get_chain("cmo")
        super().__init__("cmo", chain, executor, safety, cache)

    def _build_prompt(self, context: Dict, extra: str) -> str:
        return (
            f"As CMO, evaluate market impact:\n"
            f"Context: {context}\n"
            f"Focus: user value, positioning, brand, growth potential\n"
            f"Decide: approve/reject/escalate"
        )


class CHRO(CSuiteAgentBase):
    """الرئيس البشري — الموارد البشرية والفريق."""

    def __init__(self, executor, safety, cache=None):
        chain = EnterpriseModelRegistry.get_chain("chro")
        super().__init__("chro", chain, executor, safety, cache)

    def _build_prompt(self, context: Dict, extra: str) -> str:
        return (
            f"As CHRO, evaluate team/people impact:\n"
            f"Context: {context}\n"
            f"Focus: team capacity, hiring, culture, training\n"
            f"Decide: approve/reject/escalate"
        )


class CLO(CSuiteAgentBase):
    """المستشار القانوني — VETO مطلق على المسائل القانونية.

    مثل ethics_advisor، لديه VETO مطلق على:
    - مخالفات قانونية
    - IP violations
    - contract risks
    - compliance failures
    """

    LEGAL_VETO_CATEGORIES = [
        "illegal", "unauthorized", "copyright", "patent violation",
        "gdpr violation", "license violation", "terms of service",
        "regulatory", "compliance", "contract breach",
        "copy", "steal", "plagiarize", "proprietary",
        "intellectual property", "ip violation", "infringement",
        "reverse engineer", "piracy", "stolen",
    ]

    # Pre-compiled patterns for multi-word phrases
    _LEGAL_VETO_PATTERNS = {
        cat: re.compile(r'(?:^|\W)' + re.escape(cat) + r'(?:\W|$)', re.IGNORECASE)
        for cat in LEGAL_VETO_CATEGORIES
    }

    def __init__(self, executor, safety, cache=None):
        chain = EnterpriseModelRegistry.get_chain("clo")
        super().__init__("clo", chain, executor, safety, cache)

    def _build_prompt(self, context: Dict, extra: str) -> str:
        return (
            f"As Chief Legal Officer, evaluate legal/compliance risk:\n"
            f"Context: {context}\n"
            f"Focus: IP, contracts, regulatory, liability\n"
            f"Decide: approve/reject/escalate/veto"
        )

    def _check_legal_veto_patterns(self, text: str) -> Optional[str]:
        """Check text against LEGAL_VETO patterns. Returns category if matched, else None."""
        for cat, pattern in self._LEGAL_VETO_PATTERNS.items():
            if pattern.search(text):
                return cat
        return None

    def check_legal_veto(self, context: Dict) -> Optional[Dict[str, Any]]:
        """يكشف VETO قانوني قبل حتى استدعاء LLM."""
        text = (str(context) + " ").lower()
        matched_cat = self._check_legal_veto_patterns(text)
        if matched_cat:
            return {
                "vetoed_by": "clo",
                "veto_category": matched_cat,
                "reason": f"Legal VETO triggered: {matched_cat}",
                "is_legal": True,
            }
        return None

    def execute_decision(self, context: Dict[str, Any], prompt: str = "", bypass_safety: bool = False) -> CSuiteDecision:
        # VETO check أولاً
        veto = self.check_legal_veto(context)
        if veto:
            return CSuiteDecision(
                role=self.role,
                decision="veto",
                reasoning=veto["reason"],
                legal_flag=True,
            )
        return super().execute_decision(context, prompt, bypass_safety=bypass_safety)


class CSuiteOrchestrator:
    """منسق قسم C-Suite."""

    def __init__(
        self,
        executor: FallbackChainExecutor,
        safety: InlineSafetyFilter,
        cache=None,
        cfo_budget_limit: float = float("inf"),
    ):
        self.ceo = CEO(executor, safety, cache)
        self.cto = CTO(executor, safety, cache)
        self.cfo = CFO(executor, safety, cache, cfo_budget_limit)
        self.coo = COO(executor, safety, cache)
        self.cmo = CMO(executor, safety, cache)
        self.chro = CHRO(executor, safety, cache)
        self.clo = CLO(executor, safety, cache)
        self._agents = {
            "ceo": self.ceo, "cto": self.cto, "cfo": self.cfo,
            "coo": self.coo, "cmo": self.cmo, "chro": self.chro, "clo": self.clo,
        }

    def executive_meeting(self, proposal: Dict[str, Any]) -> Dict[str, Any]:
        """اجتماع تنفيذي: كل C-Suite يصوت على المقترح."""
        decisions = {}
        legal_veto = None
        bypass_safety = proposal.get("bypass_safety", False)

        # CLO أولاً (legal VETO) - skip if bypass_safety
        if not bypass_safety:
            legal_veto = self.clo.check_legal_veto(proposal)
            if legal_veto:
                return {
                    "verdict": "vetoed",
                    "vetoed_by": "clo",
                    "reason": legal_veto["reason"],
                    "decisions": {},
                }

        # CFO budget check - always enforce budget
        budget_estimate = proposal.get("estimated_cost", 0)
        if budget_estimate > 0 and not self.cfo.check_budget(budget_estimate):
            return {
                "verdict": "rejected",
                "vetoed_by": "cfo",
                "reason": "Budget circuit breaker triggered (80%+)",
                "decisions": {},
            }

        # باقي الـ C-Suite (CEO, CTO, COO, CMO, CHRO) - لا يملكون VETO
        for role in ["ceo", "cto", "coo", "cmo", "chro"]:
            agent = self._agents[role]
            decision = agent.execute_decision(proposal, bypass_safety=bypass_safety)
            decisions[role] = decision

        # CFO بعد التحقق من الميزانية
        cfo_decision = self.cfo.execute_decision(proposal, bypass_safety=bypass_safety)
        decisions["cfo"] = cfo_decision

        # CLO (يأتي بعد CFO) - يملك VETO قانوني
        clo_decision = self.clo.execute_decision(proposal, bypass_safety=bypass_safety)
        decisions["clo"] = clo_decision
        if clo_decision.decision == "veto":
            return {
                "verdict": "vetoed",
                "vetoed_by": "clo",
                "reason": clo_decision.reasoning,
                "decisions": decisions,
            }

        # تجميع الأصوات
        approve = sum(1 for d in decisions.values() if d.decision == "approve")
        reject = sum(1 for d in decisions.values() if d.decision == "reject")
        escalate = sum(1 for d in decisions.values() if d.decision == "escalate")

        if escalate > 0:
            verdict = "escalate_to_board"
        elif approve > reject:
            verdict = "approved"
            if budget_estimate > 0:
                self.cfo.record_spend(budget_estimate)
        elif reject > approve:
            verdict = "rejected"
        else:
            verdict = "escalate_to_board"  # tie

        return {
            "verdict": verdict,
            "decisions": decisions,
            "votes": {role: d.decision for role, d in decisions.items()},
            "budget_status": self.cfo.get_status(),
        }

    def run_agent(self, role: str, context: Dict) -> CSuiteDecision:
        """يشغّل وكيل واحد من C-Suite."""
        if role not in self._agents:
            return CSuiteDecision(
                role=role,
                decision="reject",
                reasoning=f"Unknown role: {role}",
            )
        return self._agents[role].execute_decision(context)


# مصنع مع singleton pattern
_default_c_suite: Optional[CSuiteOrchestrator] = None
_c_suite_lock = threading.Lock()


def create_c_suite(
    executor: Optional[FallbackChainExecutor] = None,
    safety: Optional[InlineSafetyFilter] = None,
    cache=None,
    cfo_budget_limit: float = float("inf"),
    force_new: bool = False,
) -> CSuiteOrchestrator:
    """Get or create the C-Suite singleton.
    
    Args:
        executor: Custom executor (optional)
        safety: Custom safety filter (optional)
        cache: Custom cache (optional)
        cfo_budget_limit: Budget limit for CFO
        force_new: If True, creates a new instance instead of returning singleton
    """
    global _default_c_suite
    if force_new or executor is not None or safety is not None or cache is not None or cfo_budget_limit != float("inf"):
        # Custom configuration requested — return new instance
        exe = executor or FallbackChainExecutor()
        sf = safety or InlineSafetyFilter()
        return CSuiteOrchestrator(exe, sf, cache, cfo_budget_limit)
    
    with _c_suite_lock:
        if _default_c_suite is None:
            _default_c_suite = CSuiteOrchestrator(
                FallbackChainExecutor(),
                InlineSafetyFilter(),
                get_default_cache(),
                cfo_budget_limit,
            )
        return _default_c_suite


if __name__ == "__main__":
    # اختبار سريع
    suite = create_c_suite()

    print("=== اختبار: اقتراح عادي ===")
    proposal = {
        "title": "Add dark mode to dashboard",
        "description": "UX improvement for better readability",
        "estimated_cost": 0,
    }
    result = suite.executive_meeting(proposal)
    print(f"الحكم: {result['verdict']}")
    print(f"الأصوات: {result.get('votes', {})}")

    print("\n=== اختبار: VETO قانوني ===")
    proposal_legal = {
        "title": "Copy competitor's code",
        "description": "Use their proprietary algorithm",
        "estimated_cost": 0,
    }
    result = suite.executive_meeting(proposal_legal)
    print(f"الحكم: {result['verdict']}")
    print(f"VETO من: {result['vetoed_by']}")
    print(f"السبب: {result.get('reason', '')}")

    print("\n=== اختبار: CFO budget ===")
    print(suite.cfo.get_status())
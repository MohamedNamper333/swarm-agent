"""
قسم البحث (Research Dept) — 4 وكلاء

الوكلاء:
- research_director: مدير القسم، ينسق الأبحاث
- researcher_1: بحث عام (gpt-oss-120b)
- researcher_2: بحث سريع (deepseek-v4-flash)
- fact_checker: تحقق من الحقائق (nemotron-3-super)

يدعم: literature review، competitive analysis، trend reports.
"""
import hashlib
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from swarm.enterprise.core.fallback_chain import FallbackChainExecutor
from swarm.enterprise.core.model_registry_v2 import EnterpriseModelRegistry
from swarm.enterprise.core.safety_filter import InlineSafetyFilter, SafetyViolation
from swarm.enterprise.core.cache_manager import get_default_cache

logger = logging.getLogger(__name__)


@dataclass
class ResearchSource:
    """مصدر بحث."""
    title: str
    url: Optional[str]
    summary: str
    credibility_score: int  # 0-100
    type: str  # "academic", "news", "blog", "official"


@dataclass
class ResearchReport:
    """تقرير بحثي شامل."""
    query: str
    findings: List[str]
    sources: List[ResearchSource]
    confidence: int  # 0-100
    model_used: str
    latency_ms: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FactCheckResult:
    """نتيجة فحص حقيقة."""
    claim: str
    verdict: str  # "true" | "false" | "unverified" | "misleading"
    confidence: int  # 0-100
    evidence: List[str] = field(default_factory=list)
    explanation: str = ""


class ResearchAgentBase:
    """الفئة الأساسية لوكلاء البحث."""

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

    def _hash(self, text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()[:16]

    def _execute(self, prompt: str) -> Dict[str, Any]:
        """ينفذ prompt مع فحص سلامة."""
        try:
            self.safety.check_input(prompt, agent_role=self.role)
        except SafetyViolation as e:
            return {"error": "safety_violation", "stage": e.stage, "message": e.message}

        result = self.executor.execute(self.role, prompt, chain=self.chain)

        try:
            if result.success and result.output:
                self.safety.check_output(result.output, agent_role=self.role)
        except SafetyViolation as e:
            return {"error": "safety_violation", "stage": e.stage, "message": e.message}

        return {
            "role": self.role,
            "model": result.chosen_model,
            "output": result.output,
            "success": result.success,
            "latency_ms": result.total_latency_ms,
        }


class ResearchDirector(ResearchAgentBase):
    """مدير قسم البحث."""

    def __init__(self, executor, safety, cache=None):
        chain = EnterpriseModelRegistry.get_chain("research_director")
        super().__init__("research_director", chain, executor, safety, cache)

    def plan_research(self, topic: str, depth: str = "standard") -> Dict[str, Any]:
        """يخطط لمشروع بحثي."""
        prompt = (
            f"As Research Director, plan research on:\n{topic}\n"
            f"Depth: {depth}\n"
            f"Include: sub-questions, methodology, deliverables, timeline"
        )
        return self._execute(prompt)


class ResearcherBase(ResearchAgentBase):
    """فئة أساسية للباحثين."""

    @abstractmethod
    def get_research_depth(self) -> str:
        """عمق البحث."""
        pass

    def research(self, query: str, max_sources: int = 5) -> ResearchReport:
        """يقوم بالبحث."""
        cache_key = f"research:{self._hash(query)}"
        cached = self.cache.get(self.role, cache_key)
        if cached:
            return cached

        prompt = (
            f"As {self.get_research_depth()} researcher, investigate:\n{query}\n"
            f"Provide: findings (key points), sources (with credibility), "
            f"confidence level, limitations"
        )
        result = self._execute(prompt)

        # Parse output for findings
        output = str(result.get("output", ""))
        findings = self._extract_findings(output)

        report = ResearchReport(
            query=query,
            findings=findings,
            sources=[],  # placeholder - would parse from output
            confidence=self._estimate_confidence(output),
            model_used=result.get("model", ""),
            latency_ms=result.get("latency_ms", 0.0),
            metadata={"researcher": self.role, "depth": self.get_research_depth()},
        )

        if "error" not in result:
            self.cache.set(self.role, cache_key, report, ttl_sec=7200)
        return report

    def _extract_findings(self, output: str) -> List[str]:
        """يستخرج findings من المخرج."""
        findings = []
        for line in output.split("\n"):
            line = line.strip()
            if line.startswith(("-", "*", "•", "1.", "2.", "3.")):
                findings.append(line.lstrip("-*•0123456789. "))
        return findings[:10] if findings else [output[:500]]

    def _estimate_confidence(self, output: str) -> int:
        """يقدّر مستوى الثقة بناءً على طول المخرج."""
        words = len(output.split())
        if words > 200:
            return 85
        elif words > 100:
            return 70
        elif words > 50:
            return 50
        return 30


class Researcher1(ResearcherBase):
    """باحث #1 — gpt-oss-120b (بحث عميق)."""

    def __init__(self, executor, safety, cache=None):
        chain = EnterpriseModelRegistry.get_chain("researcher_1")
        super().__init__("researcher_1", chain, executor, safety, cache)

    def get_research_depth(self) -> str:
        return "deep"


class Researcher2(ResearcherBase):
    """باحث #2 — deepseek-v4-flash (بحث سريع)."""

    def __init__(self, executor, safety, cache=None):
        chain = EnterpriseModelRegistry.get_chain("researcher_2")
        super().__init__("researcher_2", chain, executor, safety, cache)

    def get_research_depth(self) -> str:
        return "fast"


class FactChecker(ResearchAgentBase):
    """مدقق الحقائق — يتحقق من الادعاءات."""

    def __init__(self, executor, safety, cache=None):
        chain = EnterpriseModelRegistry.get_chain("fact_checker")
        super().__init__("fact_checker", chain, executor, safety, cache)

    def check(self, claim: str) -> FactCheckResult:
        """يفحص ادعاءً معيناً."""
        cache_key = f"check:{self._hash(claim)}"
        cached = self.cache.get(self.role, cache_key)
        if cached:
            return cached

        prompt = (
            f"As Fact Checker, verify this claim:\n{claim}\n"
            f"Provide: verdict (true/false/unverified/misleading), "
            f"confidence (0-100), evidence, explanation"
        )
        result = self._execute(prompt)

        output = str(result.get("output", ""))
        verdict, confidence = self._parse_verdict(output)

        check_result = FactCheckResult(
            claim=claim,
            verdict=verdict,
            confidence=confidence,
            evidence=[output[:300]],
            explanation=output[:500],
        )

        if "error" not in result:
            self.cache.set(self.role, cache_key, check_result, ttl_sec=3600)
        return check_result

    def _parse_verdict(self, output: str) -> tuple:
        """يستخرج verdict و confidence."""
        out_lower = output.lower()
        if "misleading" in out_lower:
            verdict = "misleading"
        elif "unverified" in out_lower or "unclear" in out_lower:
            verdict = "unverified"
        elif re.search(r"\bfalse\b", out_lower):
            verdict = "false"
        elif re.search(r"\btrue\b", out_lower):
            verdict = "true"
        else:
            verdict = "unverified"

        # confidence extraction
        match = re.search(r"confidence[:\s]+(\d+)", out_lower)
        confidence = int(match.group(1)) if match else 50

        return verdict, confidence


class ResearchOrchestrator:
    """منسق قسم البحث."""

    def __init__(
        self,
        executor: FallbackChainExecutor,
        safety: InlineSafetyFilter,
        cache=None,
    ):
        self.director = ResearchDirector(executor, safety, cache)
        self.researcher_1 = Researcher1(executor, safety, cache)
        self.researcher_2 = Researcher2(executor, safety, cache)
        self.fact_checker = FactChecker(executor, safety, cache)
        self._agents = {
            "research_director": self.director,
            "researcher_1": self.researcher_1,
            "researcher_2": self.researcher_2,
            "fact_checker": self.fact_checker,
        }

    def full_research(self, query: str) -> Dict[str, Any]:
        """بحث شامل: تخطيط → بحث → تحقق."""
        result = {
            "query": query,
            "stages": {},
        }

        # 1. Plan
        plan = self.director.plan_research(query)
        result["stages"]["plan"] = {"model": plan.get("model")}

        # 2. Deep research (researcher_1)
        deep = self.researcher_1.research(query)
        result["stages"]["deep_research"] = {
            "researcher": deep.metadata.get("researcher"),
            "confidence": deep.confidence,
            "findings_count": len(deep.findings),
            "model": deep.model_used,
        }

        # 3. Fact-check أول finding (إن وُجد)
        if deep.findings:
            check = self.fact_checker.check(deep.findings[0])
            result["stages"]["fact_check"] = {
                "claim": check.claim[:100],
                "verdict": check.verdict,
                "confidence": check.confidence,
            }

        return result

    def run_agent(self, role: str, **kwargs) -> Any:
        """يشغّل وكيل محدد."""
        agent = self._agents.get(role)
        if not agent:
            return {"error": f"unknown role: {role}"}

        if role in ("researcher_1", "researcher_2"):
            return agent.research(kwargs.get("query", ""))
        elif role == "fact_checker":
            return agent.check(kwargs.get("claim", ""))
        elif role == "research_director":
            return agent.plan_research(kwargs.get("topic", ""))
        else:
            return agent._execute(kwargs.get("prompt", ""))


def create_research_dept(
    executor: Optional[FallbackChainExecutor] = None,
    safety: Optional[InlineSafetyFilter] = None,
    cache=None,
) -> ResearchOrchestrator:
    exe = executor or FallbackChainExecutor()
    sf = safety or InlineSafetyFilter()
    return ResearchOrchestrator(exe, sf, cache)


if __name__ == "__main__":
    import re

    dept = create_research_dept()

    print("=== بحث شامل ===")
    result = dept.full_research("What's the state of AI agents in 2026?")
    print(f"الاستعلام: {result['query']}")
    print(f"المراحل: {len(result['stages'])}")
    for stage, info in result['stages'].items():
        print(f"  - {stage}: {info}")
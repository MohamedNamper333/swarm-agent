"""
SwarmMaster — منسق الـ 50-Agent Swarm بالكامل.

التدفق (5 مراحل):
1. Safety Dept check (PII, violence, jailbreak) - VETO-first
2. Board deliberation (ethics_advisor VETO, strategy/risk/user votes)
3. C-Suite decision (CFO budget, CLO legal VETO)
4. Route to relevant Department (code/design/video/research/data/language/knowledge)
5. Execute via the department's orchestrator

هذا يحل المشاكل الحرجة:
- ✅ لا تكامل بين الأقسام → SwarmMaster ينسقها
- ✅ Safety Dept معزول → يُستدعى أولاً
- ✅ لا end-to-end workflow → process() يعمل الكل
"""
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from swarm.enterprise.core.fallback_chain import FallbackChainExecutor
from swarm.enterprise.core.model_registry_v2 import EnterpriseModelRegistry
from swarm.enterprise.core.safety_filter import InlineSafetyFilter
from swarm.enterprise.core.cache_manager import get_default_cache
from swarm.enterprise.core.circuit_breaker import get_circuit_breaker
from swarm.resilience.rate_limiter_v2 import get_rate_limiter

# Tier 1: Board
from swarm.enterprise.board import create_board, BoardDecision

# Tier 2: C-Suite
from swarm.enterprise.csuite import create_c_suite

# Tier 3+4: Departments
from swarm.enterprise.code import create_code_dept
from swarm.enterprise.design import create_design_dept
from swarm.enterprise.video import create_video_dept
from swarm.enterprise.research import create_research_dept
from swarm.enterprise.data import create_data_dept
from swarm.enterprise.language import create_language_dept
from swarm.enterprise.knowledge import create_knowledge_dept
from swarm.enterprise.safety import create_safety_dept

logger = logging.getLogger(__name__)


class DeptType(str, Enum):
    """أنواع الأقسام للتوجيه."""
    CODE = "code"
    DESIGN = "design"
    VIDEO = "video"
    RESEARCH = "research"
    DATA = "data"
    LANGUAGE = "language"
    KNOWLEDGE = "knowledge"
    SAFETY = "safety"
    GENERAL = "general"  # لا يحتاج dept متخصص


# كلمات مفتاحية لتوجيه الطلبات للأقسام المناسبة
DEPT_ROUTING_KEYWORDS = {
    DeptType.CODE: [
        "code", "function", "class", "implement", "build app",
        "api endpoint", "database query", "python script",
        "javascript", "deploy", "refactor",
        "compile", "syntax", "debug", "fix bug",
    ],
    DeptType.DESIGN: [
        "logo", "image", "design", "ui mockup", "ux", "mockup",
        "icon", "brand", "color scheme", "typography", "3d model",
        "wireframe", "visual", "artwork", "illustration",
    ],
    DeptType.VIDEO: [
        "video", "animation", "animate", "motion graphic", "film",
        "clip", "storyboard", "movie", "mp4", "commercial",
    ],
    DeptType.RESEARCH: [
        "research", "investigate", "study", "literature review",
        "fact check", "verify", "find papers", "academic", "study of",
    ],
    DeptType.DATA: [
        "data analysis", "etl pipeline", "analytics", "metrics",
        "kpi", "sql query", "schema design", "dashboard", "data warehouse",
        "olap", "data lake", "pipeline", "data pipeline",
        "data processing", "data transformation",
    ],
    DeptType.LANGUAGE: [
        "translate", "translation", "localize", "localization",
        "i18n", "arabic text", "french text", "spanish text",
    ],
    DeptType.KNOWLEDGE: [
        "search docs", "knowledge base", "rag retrieval",
        "find document", "search knowledge", "document retrieval",
    ],
}


@dataclass
class SwarmRequest:
    """طلب موحد للـ SwarmMaster."""
    question: str
    type: str = "general"  # code, design, video, research, data, language, knowledge, general
    estimated_cost: float = 0.0  # للـ CFO budget check
    context: Dict[str, Any] = field(default_factory=dict)
    require_human_review: bool = False
    bypass_safety: bool = False  # للاختبار فقط


@dataclass
class SwarmResult:
    """نتيجة موحدة من SwarmMaster."""
    request_id: str
    verdict: str  # "approved" | "rejected" | "vetoed" | "error"
    final_decision: str  # "approved" | "vetoed" | "rejected" | "escalated"
    stages: Dict[str, Any] = field(default_factory=dict)
    output: Optional[Any] = None
    vetoed_by: Optional[str] = None
    veto_reason: Optional[str] = None
    executed_by: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class SwarmMaster:
    """المنسق الرئيسي لـ 50-Agent Swarm.

    يدير:
    - Tier 1: Board (5 agents) - VETO على ethics
    - Tier 2: C-Suite (7 agents) - VETO على legal, budget tracking
    - Tier 3+4: 8 Departments (40 agents) - التنفيذ الفعلي
    - Safety Dept (4 agents) - PII/violence/jailbreak check
    """

    def __init__(
        self,
        cfo_budget_limit: float = float("inf"),
    ):
        # Core infrastructure (shared)
        self.executor = FallbackChainExecutor()
        self.safety = InlineSafetyFilter()
        self.cache = get_default_cache()
        self.rate_limiter = get_rate_limiter()
        self.circuit_breaker = get_circuit_breaker()

        # Safety Dept (Tier 1 - VETO first)
        self.safety_dept = create_safety_dept()

        # Board (Tier 1 - strategic VETO)
        self.board = create_board()

        # C-Suite (Tier 2 - executive decision)
        self.csuite = create_c_suite(cfo_budget_limit=cfo_budget_limit)

        # Departments (Tier 3+4 - execution)
        self.depts = {
            DeptType.CODE.value: create_code_dept(),
            DeptType.DESIGN.value: create_design_dept(),
            DeptType.VIDEO.value: create_video_dept(),
            DeptType.RESEARCH.value: create_research_dept(),
            DeptType.DATA.value: create_data_dept(),
            DeptType.LANGUAGE.value: create_language_dept(),
            DeptType.KNOWLEDGE.value: create_knowledge_dept(),
            DeptType.SAFETY.value: self.safety_dept,
        }

        self._request_counter = 0

    def process(self, request: SwarmRequest) -> SwarmResult:
        """معالجة طلب كامل عبر كل الـ tiers.

        التدفق:
        1. Safety Dept (PII/violence/jailbreak check)
        2. Board deliberation (ethics VETO + advisor votes)
        3. C-Suite meeting (CFO budget + CLO legal VETO)
        4. Route to Department
        5. Execute and return
        """
        self._request_counter += 1
        req_id = f"req-{self._request_counter:06d}"

        stages: Dict[str, Any] = {}
        metadata = {"request_id": req_id, "timestamp": self._now_iso()}

        # 1. Safety Dept (PII/violence/jailbreak block)
        if not request.bypass_safety:
            safety_result = self._safety_check(request)
            stages["safety"] = safety_result
            if safety_result.get("verdict") in ("unsafe", "critical"):
                return SwarmResult(
                    request_id=req_id,
                    verdict="vetoed",
                    final_decision="vetoed",
                    stages=stages,
                    vetoed_by="safety_dept",
                    veto_reason=safety_result.get("explanation", "Content safety violation"),
                    metadata=metadata,
                )
        else:
            stages["safety"] = {"verdict": "bypassed", "reason": "bypass_safety=True"}

        # 2. Board deliberation (strategic VETO)
        board_result = self._board_deliberate(request)
        stages["board"] = {
            "verdict": board_result.final_decision,
            "vetoed_by": board_result.vetoed_by,
            "votes": board_result.votes,
        }
        if board_result.vetoed_by:
            return SwarmResult(
                request_id=req_id,
                verdict="vetoed",
                final_decision="vetoed",
                stages=stages,
                vetoed_by=board_result.vetoed_by,
                veto_reason=board_result.veto_reason,
                metadata=metadata,
            )

        # 3. C-Suite meeting (executive decision)
        csuite_result = self._csuite_decide(request, board_result)
        stages["csuite"] = {
            "verdict": csuite_result.get("verdict"),
            "vetoed_by": csuite_result.get("vetoed_by"),
            "votes": csuite_result.get("votes"),
        }
        # Check both vetoed (hard block) and rejected (CFO budget breach)
        if csuite_result.get("verdict") == "vetoed":
            return SwarmResult(
                request_id=req_id,
                verdict="vetoed",
                final_decision="vetoed",
                stages=stages,
                vetoed_by=csuite_result.get("vetoed_by"),
                veto_reason=csuite_result.get("reason"),
                metadata=metadata,
            )
        if csuite_result.get("verdict") == "rejected":
            return SwarmResult(
                request_id=req_id,
                verdict="rejected",
                final_decision="rejected",
                stages=stages,
                vetoed_by=csuite_result.get("vetoed_by"),
                veto_reason=csuite_result.get("reason"),
                metadata=metadata,
            )

        # 4. Route to Department
        dept_name = self._route_to_dept(request)
        stages["routing"] = {"department": dept_name.value}

        # 5. Execute
        try:
            output = self._execute_in_dept(dept_name, request)
            stages["execution"] = {
                "department": dept_name.value,
                "output_type": type(output).__name__,
                "success": True,
            }
            return SwarmResult(
                request_id=req_id,
                verdict="approved",
                final_decision="approved",
                stages=stages,
                output=output,
                executed_by=dept_name.value,
                metadata=metadata,
            )
        except Exception as e:
            logger.exception("Execution in %s failed", dept_name)
            stages["execution"] = {
                "department": dept_name.value,
                "success": False,
                "error": str(e),
            }
            return SwarmResult(
                request_id=req_id,
                verdict="error",
                final_decision="error",
                stages=stages,
                vetoed_by=None,
                veto_reason=f"Execution error: {str(e)[:200]}",
                metadata=metadata,
            )

    def _safety_check(self, request: SwarmRequest) -> Dict[str, Any]:
        """يفحص PII/violence/jailbreak."""
        text = request.question + " " + str(request.context)
        report = self.safety_dept.full_check(text, use_llm=False)
        return {
            "verdict": report.verdict.value,
            "flags": report.flags,
            "explanation": report.explanation,
            "analyst_votes": {k: v.value for k, v in report.analyst_votes.items()},
        }

    def _board_deliberate(self, request: SwarmRequest) -> BoardDecision:
        """يدعو المجلس للتصويت."""
        context_str = str(request.context) if request.context else ""
        return self.board.deliberate(request.question, context=context_str)

    def _csuite_decide(self, request: SwarmRequest, board_result: BoardDecision) -> Dict[str, Any]:
        """يدعو C-Suite للقرار التنفيذي."""
        proposal = {
            "title": request.question[:100],
            "description": request.question,
            "type": request.type,
            "estimated_cost": request.estimated_cost,
        }
        return self.csuite.executive_meeting(proposal)

    def _route_to_dept(self, request: SwarmRequest) -> DeptType:
        """يوجّه الطلب للقسم المناسب."""
        # 1. إذا حدد المستخدم النوع
        if request.type and request.type != "general":
            try:
                return DeptType(request.type)
            except ValueError:
                pass

        # 2. Auto-detect من الكلمات المفتاحية
        text_lower = request.question.lower()
        scores: Dict[DeptType, int] = {dt: 0 for dt in DeptType}
        for dept, keywords in DEPT_ROUTING_KEYWORDS.items():
            for kw in keywords:
                if kw in text_lower:
                    scores[dept] += 1

        # أعلى score
        best = max(scores.items(), key=lambda x: x[1])
        if best[1] > 0:
            return best[0]

        return DeptType.GENERAL

    def _execute_in_dept(self, dept: DeptType, request: SwarmRequest) -> Any:
        """ينفذ في القسم المحدد."""
        if dept == DeptType.GENERAL:
            # لا يوجد dept متخصص، يُرجع Board decision كـ output
            return {
                "type": "general",
                "message": "No specific department matched. Board approved but no execution.",
                "board_verdict": "approved",
            }

        # استدعاء الـ orchestrator المناسب
        orch = self.depts.get(dept.value)
        if not orch:
            return {"error": f"no orchestrator for {dept.value}"}

        # تنفيذ مناسب حسب القسم
        if dept == DeptType.CODE:
            # Code: write code + review
            artifact = orch.coder_1.write_code(request.question, "python")
            if artifact.code and "Error" not in artifact.code[:20]:
                review = orch.reviewer.full_review(artifact.code, artifact.language)
                return {
                    "code": artifact.code,
                    "review": {
                        "approved": review.approved,
                        "score": review.total_score,
                        "findings_count": len(review.findings),
                    },
                }
            return {"code": artifact.code}

        elif dept == DeptType.DESIGN:
            # Design: brand kit
            return orch.generate_complete_brand_kit(
                brand_name=request.context.get("brand_name", "Project")
            )

        elif dept == DeptType.VIDEO:
            # Video: promo video
            return orch.create_promo_video(
                brief={"title": request.question[:50], "description": request.question}
            )

        elif dept == DeptType.RESEARCH:
            # Research: full pipeline
            return orch.full_research(request.question)

        elif dept == DeptType.DATA:
            # Data: analyze question
            return orch.analyze_question(request.question)

        elif dept == DeptType.LANGUAGE:
            # Language: translate + localize
            ctx = request.context or {}
            return orch.translate_and_localize(
                text=request.question,
                source_lang=ctx.get("source_lang", "en"),
                target_lang=ctx.get("target_lang", "ar"),
            )

        elif dept == DeptType.KNOWLEDGE:
            # Knowledge: add doc + query
            return orch.query(request.question, top_k=3, rerank=True)

        elif dept == DeptType.SAFETY:
            # Safety: full check
            report = orch.full_check(request.question, use_llm=False)
            return {
                "verdict": report.verdict.value,
                "flags": report.flags,
                "explanation": report.explanation,
            }

        return {"error": f"unknown dept: {dept.value}"}

    def get_status(self) -> Dict[str, Any]:
        """حالة الـ Swarm."""
        return {
            "board_agents": 5,
            "csuite_agents": 7,
            "department_agents": sum(
                len(getattr(d, "_agents", {})) for d in self.depts.values()
                if hasattr(d, "_agents")
            ),
            "total_chains": len(EnterpriseModelRegistry.ALL_CHAINS),
            "rate_limit_status": "active",
            "circuit_breaker_status": "active",
            "cache_status": "active" if self.cache else "inactive",
        }

    def list_agents(self) -> Dict[str, List[str]]:
        """يرجع قائمة بكل الـ agents حسب القسم."""
        return {
            "board": ["chairman", "strategy_advisor", "ethics_advisor", "risk_advisor", "user_advisor"],
            "csuite": ["ceo", "cto", "cfo", "coo", "cmo", "chro", "clo"],
            "code": list(self.depts["code"]._agents.keys()) if hasattr(self.depts["code"], "_agents") else [],
            "design": list(self.depts["design"]._agents.keys()) if hasattr(self.depts["design"], "_agents") else [],
            "video": list(self.depts["video"]._agents.keys()) if hasattr(self.depts["video"], "_agents") else [],
            "research": list(self.depts["research"]._agents.keys()) if hasattr(self.depts["research"], "_agents") else [],
            "data": list(self.depts["data"]._agents.keys()) if hasattr(self.depts["data"], "_agents") else [],
            "language": list(self.depts["language"]._agents.keys()) if hasattr(self.depts["language"], "_agents") else [],
            "knowledge": ["director", "curator", "retriever", "reranker", "parser"],
            "safety": ["director", "content", "topic", "jailbreak"],
        }

    @staticmethod
    def _now_iso() -> str:
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()


# Singleton
_master_instance: Optional[SwarmMaster] = None


def get_master() -> SwarmMaster:
    """يرجع الـ SwarmMaster singleton."""
    global _master_instance
    if _master_instance is None:
        _master_instance = SwarmMaster()
    return _master_instance


if __name__ == "__main__":
    master = SwarmMaster()
    print("=== Swarm Status ===")
    status = master.get_status()
    for k, v in status.items():
        print(f"  {k}: {v}")
    print()
    print("=== Agents ===")
    agents = master.list_agents()
    for dept, roles in agents.items():
        print(f"  {dept}: {len(roles)} agents")
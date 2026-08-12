"""
قسم البيانات (Data Dept) — 3 وكلاء

الوكلاء:
- data_director: مدير القسم (gemma-3-27b-it)
- data_analyst: تحليل البيانات (gemma-3-27b-it)
- data_engineer: هندسة البيانات (nemotron-3-nano-30b)

يدعم: schema design، SQL queries، data pipelines، ETL.
"""
import hashlib
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from swarm.enterprise.core.fallback_chain import FallbackChainExecutor
from swarm.enterprise.core.model_registry_v2 import EnterpriseModelRegistry
from swarm.enterprise.core.safety_filter import InlineSafetyFilter, SafetyViolation
from swarm.enterprise.core.cache_manager import get_default_cache

logger = logging.getLogger(__name__)


class DatabaseType(str, Enum):
    """أنواع قواعد البيانات المدعومة."""
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    SQLITE = "sqlite"
    MONGODB = "mongodb"
    REDIS = "redis"


@dataclass
class DataSchema:
    """مخطط قاعدة بيانات."""
    name: str
    database: DatabaseType
    tables: List[Dict[str, Any]]
    relationships: List[Dict[str, str]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QueryResult:
    """نتيجة استعلام."""
    sql: str
    explanation: str
    estimated_rows: Optional[int] = None
    performance_notes: List[str] = field(default_factory=list)


@dataclass
class PipelineSpec:
    """مواصفات خط أنابيب بيانات."""
    name: str
    source: str
    destination: str
    transformations: List[str]
    schedule: str = "manual"
    sla_minutes: int = 60


class DataAgentBase:
    """الفئة الأساسية لوكلاء البيانات."""

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


class DataDirector(DataAgentBase):
    """مدير قسم البيانات."""

    def __init__(self, executor, safety, cache=None):
        chain = EnterpriseModelRegistry.get_chain("data_director")
        super().__init__("data_director", chain, executor, safety, cache)

    def plan_data_strategy(self, requirements: str) -> Dict[str, Any]:
        """يخطط لاستراتيجية البيانات."""
        prompt = (
            f"As Data Director, plan data strategy for:\n{requirements}\n"
            f"Include: storage, processing, governance, quality, lineage"
        )
        return self._execute(prompt)


class DataAnalyst(DataAgentBase):
    """محلل بيانات — يكتب SQL queries، يحلل البيانات."""

    DANGEROUS_SQL_PATTERNS = [
        r"\bDROP\s+(TABLE|DATABASE|SCHEMA)\b",
        r"\bTRUNCATE\b",
        r"\bDELETE\s+FROM\s+\w+\s*(?:;|$)",  # DELETE without WHERE
        r"\bUPDATE\s+\w+\s+SET\s+",  # UPDATE (risky)
        r"\bGRANT\b",
        r"\bREVOKE\b",
    ]

    def __init__(self, executor, safety, cache=None):
        chain = EnterpriseModelRegistry.get_chain("data_analyst")
        super().__init__("data_analyst", chain, executor, safety, cache)
        self._compiled_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.DANGEROUS_SQL_PATTERNS
        ]

    def generate_query(
        self,
        question: str,
        db_type: DatabaseType = DatabaseType.POSTGRESQL,
    ) -> QueryResult:
        """يولّد استعلام SQL من سؤال بلغة طبيعية."""
        cache_key = f"query:{self._hash(question)}:{db_type.value}"
        cached = self.cache.get(self.role, cache_key)
        if cached:
            return cached

        prompt = (
            f"Generate {db_type.value} query for:\n{question}\n"
            f"Use: best practices, parameterized queries, proper indexing hints"
        )
        result = self._execute(prompt)

        sql = self._extract_sql(str(result.get("output", "")))
        safe = self._is_safe_sql(sql)

        query_result = QueryResult(
            sql=sql,
            explanation=str(result.get("output", "")),
            estimated_rows=None,
            performance_notes=["Use indexes on WHERE columns", "Consider LIMIT for large results"] if safe else ["BLOCKED: dangerous SQL detected"],
        )

        if "error" not in result and safe:
            self.cache.set(self.role, cache_key, query_result, ttl_sec=3600)
        return query_result

    def _extract_sql(self, output: str) -> str:
        """يستخرج SQL من المخرج."""
        # البحث عن ```sql blocks
        match = re.search(r"```sql\s*\n(.*?)```", output, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        # البحث عن ``` blocks
        match = re.search(r"```\s*\n(.*?)```", output, re.DOTALL)
        if match:
            return match.group(1).strip()
        return output.strip()

    def _is_safe_sql(self, sql: str) -> bool:
        """يفحص SQL للأمان."""
        for pattern in self._compiled_patterns:
            if pattern.search(sql):
                logger.warning(f"DataAnalyst blocked dangerous SQL: {pattern.pattern}")
                return False
        return True


class DataEngineer(DataAgentBase):
    """مهندس بيانات — ETL pipelines، data architecture."""

    def __init__(self, executor, safety, cache=None):
        chain = EnterpriseModelRegistry.get_chain("data_engineer")
        super().__init__("data_engineer", chain, executor, safety, cache)

    def design_schema(self, requirements: str, db_type: DatabaseType = DatabaseType.POSTGRESQL) -> DataSchema:
        """يصمم مخطط قاعدة بيانات."""
        prompt = (
            f"Design {db_type.value} schema for:\n{requirements}\n"
            f"Include: tables, columns, types, indexes, constraints"
        )
        result = self._execute(prompt)

        return DataSchema(
            name="generated_schema",
            database=db_type,
            tables=[],  # would parse from output
            metadata={"model": result.get("model")},
        )

    def design_pipeline(self, source: str, destination: str) -> PipelineSpec:
        """يصمم خط أنابيب بيانات."""
        prompt = (
            f"Design data pipeline from {source} to {destination}\n"
            f"Include: transformations, quality checks, error handling, monitoring"
        )
        result = self._execute(prompt)

        return PipelineSpec(
            name=f"{source}_to_{destination}",
            source=source,
            destination=destination,
            transformations=["extract", "validate", "transform", "load"],
            metadata={"model": result.get("model")},
        )


class DataOrchestrator:
    """منسق قسم البيانات."""

    def __init__(
        self,
        executor: FallbackChainExecutor,
        safety: InlineSafetyFilter,
        cache=None,
    ):
        self.director = DataDirector(executor, safety, cache)
        self.analyst = DataAnalyst(executor, safety, cache)
        self.engineer = DataEngineer(executor, safety, cache)
        self._agents = {
            "data_director": self.director,
            "data_analyst": self.analyst,
            "data_engineer": self.engineer,
        }

    def analyze_question(self, question: str, db_type: DatabaseType = DatabaseType.POSTGRESQL) -> Dict[str, Any]:
        """تحليل شامل: استراتيجية → schema → query."""
        result = {
            "question": question,
            "stages": {},
        }

        # 1. استراتيجية
        strategy = self.director.plan_data_strategy(question)
        result["stages"]["strategy"] = {"model": strategy.get("model")}

        # 2. Schema
        schema = self.engineer.design_schema(question, db_type)
        result["stages"]["schema"] = {
            "database": schema.database.value,
            "tables_planned": True,
        }

        # 3. Query
        query = self.analyst.generate_query(question, db_type)
        result["stages"]["query"] = {
            "sql_safe": "BLOCKED" not in query.explanation,
            "performance_notes_count": len(query.performance_notes),
            "sql_preview": query.sql[:200],
        }

        return result

    def run_agent(self, role: str, **kwargs) -> Any:
        """يشغّل وكيل محدد."""
        agent = self._agents.get(role)
        if not agent:
            return {"error": f"unknown role: {role}"}
        if role == "data_analyst":
            return agent.generate_query(
                question=kwargs.get("question", ""),
                db_type=DatabaseType(kwargs.get("db_type", "postgresql")),
            )
        elif role == "data_engineer":
            return agent.design_schema(
                requirements=kwargs.get("requirements", ""),
                db_type=DatabaseType(kwargs.get("db_type", "postgresql")),
            )
        elif role == "data_director":
            return agent.plan_data_strategy(kwargs.get("requirements", ""))
        return agent._execute(kwargs.get("prompt", ""))


def create_data_dept(
    executor: Optional[FallbackChainExecutor] = None,
    safety: Optional[InlineSafetyFilter] = None,
    cache=None,
) -> DataOrchestrator:
    exe = executor or FallbackChainExecutor()
    sf = safety or InlineSafetyFilter()
    return DataOrchestrator(exe, sf, cache)


if __name__ == "__main__":
    dept = create_data_dept()

    print("=== تحليل سؤال ===")
    result = dept.analyze_question("Find top 10 customers by revenue this month")
    print(f"السؤال: {result['question']}")
    print(f"المراحل: {len(result['stages'])}")
    for stage, info in result['stages'].items():
        print(f"  - {stage}: {info}")
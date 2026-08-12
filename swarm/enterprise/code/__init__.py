"""
قسم الكود (Code Dept) — 7 وكلاء

الوكلاء:
- code_director: مدير القسم، ينسق بين الوكلاء
- code_architect: يصمم البنية والـ interfaces
- coder_1: يكتب الكود (qwen2.5-coder-32b)
- coder_2: يكتب الكود المعقد (qwen3-coder-480b)
- code_reviewer: يراجع الكود ويكشف الثغرات (nemotron-3-ultra)
- qa_engineer: يكتب الاختبارات ويفحص الجودة
- devops: CI/CD، GitHub، النشر

كل وكيل يستخدم:
- chain مخصص من registry
- inline safety filter
- code sandbox (Docker) للكود المُولّد
- GitHub integration لـ devops
"""
import hashlib
import logging
import re
import subprocess
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from swarm.enterprise.core.fallback_chain import FallbackChainExecutor
from swarm.enterprise.core.model_registry_v2 import EnterpriseModelRegistry
from swarm.enterprise.core.safety_filter import InlineSafetyFilter, SafetyViolation
from swarm.enterprise.core.cache_manager import get_default_cache

logger = logging.getLogger(__name__)


class Severity(str, Enum):
    """شدة الثغرة."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class CodeArtifact:
    """قطعة كود مُنتجة."""
    code: str
    language: str  # python, javascript, etc
    file_path: Optional[str] = None
    author: str = ""  # agent role
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReviewFinding:
    """نتيجة مراجعة كود."""
    severity: Severity
    line: Optional[int]
    description: str
    suggestion: Optional[str] = None
    cwe_id: Optional[str] = None  # CWE-89 (SQLi), CWE-79 (XSS), etc


@dataclass
class ReviewReport:
    """تقرير مراجعة شامل."""
    code_hash: str
    findings: List[ReviewFinding] = field(default_factory=list)
    approved: bool = True
    total_score: int = 100  # 0-100
    model_used: str = ""
    latency_ms: float = 0.0


class CodeAgentBase:
    """الفئة الأساسية لوكلاء Code."""

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
        """تنفيذ مع فحص سلامة."""
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


class CodeDirector(CodeAgentBase):
    """مدير قسم الكود — ينسق بين الوكلاء."""

    def __init__(self, executor, safety, cache=None):
        chain = EnterpriseModelRegistry.get_chain("code_director")
        super().__init__("code_director", chain, executor, safety, cache)

    def assign_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """يوزّع المهمة على الوكيل المناسب."""
        task_type = task.get("type", "")
        prompt = (
            f"As Code Director, decide which agent should handle this task:\n"
            f"Task: {task}\n"
            f"Available agents: architect, coder_1, coder_2, code_reviewer, qa_engineer, devops\n"
            f"Return: agent_name, brief_plan"
        )
        return self._execute(prompt)


class CodeArchitect(CodeAgentBase):
    """مهندس البنية — يصمم البنية والـ interfaces."""

    def __init__(self, executor, safety, cache=None):
        chain = EnterpriseModelRegistry.get_chain("code_architect")
        super().__init__("code_architect", chain, executor, safety, cache)

    def design(self, requirements: str) -> Dict[str, Any]:
        """يصمم بنية بناءً على المتطلبات."""
        prompt = (
            f"As Software Architect, design the architecture:\n"
            f"Requirements: {requirements}\n"
            f"Provide: components, interfaces, data flow, tech stack"
        )
        return self._execute(prompt)


class CoderBase(CodeAgentBase):
    """فئة أساسية للكودرز."""

    @abstractmethod
    def get_language_strength(self) -> List[str]:
        """اللغات التي يتقنها."""
        pass

    def write_code(self, task: str, language: str = "python") -> CodeArtifact:
        """يكتب كوداً."""
        prompt = (
            f"As expert {language} developer, write production code:\n"
            f"Task: {task}\n"
            f"Language: {language}\n"
            f"Include: error handling, type hints, comments"
        )
        result = self._execute(prompt)
        if "error" in result:
            return CodeArtifact(
                code=f"# Error: {result['error']}",
                language=language,
                author=self.role,
                metadata={"error": result},
            )
        return CodeArtifact(
            code=str(result.get("output", "")),
            language=language,
            author=self.role,
            metadata={"model": result.get("model"), "latency_ms": result.get("latency_ms")},
        )


class Coder1(CoderBase):
    """مبرمج 1 — qwen2.5-coder-32b (سرعة وكفاءة)."""

    def __init__(self, executor, safety, cache=None):
        chain = EnterpriseModelRegistry.get_chain("coder_1")
        super().__init__("coder_1", chain, executor, safety, cache)

    def get_language_strength(self) -> List[str]:
        return ["python", "javascript", "typescript", "go", "bash"]


class Coder2(CoderBase):
    """مبرمج 2 — qwen3-coder-480b (مهام معقدة وكبيرة)."""

    def __init__(self, executor, safety, cache=None):
        chain = EnterpriseModelRegistry.get_chain("coder_2")
        super().__init__("coder_2", chain, executor, safety, cache)

    def get_language_strength(self) -> List[str]:
        return ["python", "rust", "c++", "java", "scala", "complex algorithms"]


class CodeReviewer(CodeAgentBase):
    """مراجع الكود — يكشف الثغرات الأمنية والجودة.

    يستخدم نماذج قوية (nemotron-3-ultra) لرصد:
    - SQL injection (CWE-89)
    - XSS (CWE-79)
    - Command injection (CWE-78)
    - Hardcoded credentials (CWE-798)
    - Path traversal (CWE-22)
    - Insecure deserialization (CWE-502)
    """

    SECURITY_PATTERNS = {
        # CWE-89: SQL Injection
        r'(execute|query)\s*\(\s*["\'].*?\+\s*\w+': (Severity.CRITICAL, "CWE-89", "SQL injection: string concatenation in query"),
        r'(SELECT|INSERT|UPDATE|DELETE)\s+.*["\'].*?\+\s*\w+': (Severity.CRITICAL, "CWE-89", "SQL injection: SQL keyword with concatenation"),
        r'["\']\s*(SELECT|INSERT|UPDATE|DELETE)\s+.*["\']\s*\+\s*\w+': (Severity.CRITICAL, "CWE-89", "SQL injection: SQL string with concatenation"),
        # CWE-79: XSS
        r'innerHTML\s*=': (Severity.HIGH, "CWE-79", "XSS risk: innerHTML usage"),
        r'document\.write\s*\(': (Severity.MEDIUM, "CWE-79", "XSS risk: document.write"),
        # CWE-78: Command Injection
        r'os\.system\s*\(': (Severity.CRITICAL, "CWE-78", "Command injection: os.system usage"),
        r'subprocess\.(call|run|Popen)\s*\(\s*["\'].*?\+': (Severity.CRITICAL, "CWE-78", "Command injection in subprocess"),
        r'subprocess\.(call|run|Popen)\s*\([^)]*shell\s*=\s*True': (Severity.HIGH, "CWE-78", "Shell=True in subprocess"),
        # CWE-798: Hardcoded credentials
        r'(password|api_key|secret|token)\s*=\s*["\'][^"\']{8,}': (Severity.CRITICAL, "CWE-798", "Hardcoded credential"),
        # CWE-22: Path traversal
        r'open\s*\([^)]*\+': (Severity.HIGH, "CWE-22", "Path traversal risk: open() with concatenation"),
        # CWE-502: Insecure deserialization
        r'pickle\.loads?\s*\(': (Severity.HIGH, "CWE-502", "Insecure deserialization: pickle"),
        r'yaml\.load\s*\((?!.*Loader)': (Severity.HIGH, "CWE-502", "Insecure YAML load"),
        # Eval/exec
        r'\beval\s*\(': (Severity.CRITICAL, "CWE-95", "Code injection: eval()"),
        r'\bexec\s*\(': (Severity.CRITICAL, "CWE-95", "Code injection: exec()"),
    }

    def __init__(self, executor, safety, cache=None):
        chain = EnterpriseModelRegistry.get_chain("code_reviewer")
        super().__init__("code_reviewer", chain, executor, safety, cache)
        self._compiled_patterns = [
            (re.compile(p, re.IGNORECASE), sev, cwe, desc)
            for p, (sev, cwe, desc) in self.SECURITY_PATTERNS.items()
        ]

    def quick_scan(self, code: str) -> List[ReviewFinding]:
        """فحص سريع regex للثغرات المعروفة."""
        findings = []
        for pattern, sev, cwe, desc in self._compiled_patterns:
            for m in pattern.finditer(code):
                line_no = code[:m.start()].count("\n") + 1
                findings.append(ReviewFinding(
                    severity=sev,
                    line=line_no,
                    description=desc,
                    cwe_id=cwe,
                    suggestion=f"Review line {line_no}",
                ))
        return findings

    def full_review(self, code: str, language: str = "python") -> ReviewReport:
        """مراجعة شاملة (regex + LLM)."""
        code_hash = self._hash(code)

        # 1. Quick scan أولاً
        quick_findings = self.quick_scan(code)

        # 2. LLM review
        prompt = (
            f"As Code Security Reviewer, analyze this {language} code:\n"
            f"```\n{code[:3000]}\n```\n"
            f"Find: SQLi, XSS, command injection, hardcoded secrets, "
            f"path traversal, insecure deserialization, logic errors.\n"
            f"Format: severity|line|description|cwe_id"
        )
        result = self._execute(prompt)

        # تجميع النتائج
        all_findings = quick_findings
        if result.get("success"):
            llm_findings = self._parse_llm_findings(str(result.get("output", "")))
            all_findings.extend(llm_findings)

        # حساب النتيجة
        score = self._calculate_score(all_findings)
        approved = score >= 70 and not any(
            f.severity == Severity.CRITICAL for f in all_findings
        )

        return ReviewReport(
            code_hash=code_hash,
            findings=all_findings,
            approved=approved,
            total_score=score,
            model_used=result.get("model", ""),
            latency_ms=result.get("latency_ms", 0.0),
        )

    def _parse_llm_findings(self, output: str) -> List[ReviewFinding]:
        """يستخرج findings من مخرج LLM."""
        findings = []
        for line in output.split("\n"):
            line = line.strip()
            if "|" not in line:
                continue
            parts = line.split("|")
            if len(parts) < 3:
                continue
            sev_str = parts[0].strip().lower()
            try:
                line_no = int(parts[1].strip()) if parts[1].strip().isdigit() else None
            except ValueError:
                line_no = None
            desc = parts[2].strip()
            cwe = parts[3].strip() if len(parts) > 3 else None
            sev = Severity.MEDIUM
            if "critical" in sev_str:
                sev = Severity.CRITICAL
            elif "high" in sev_str:
                sev = Severity.HIGH
            elif "low" in sev_str:
                sev = Severity.LOW
            elif "info" in sev_str:
                sev = Severity.INFO
            findings.append(ReviewFinding(
                severity=sev, line=line_no, description=desc, cwe_id=cwe,
            ))
        return findings

    def _calculate_score(self, findings: List[ReviewFinding]) -> int:
        """يحسب نقاط الكود (0-100)."""
        score = 100
        for f in findings:
            if f.severity == Severity.CRITICAL:
                score -= 30
            elif f.severity == Severity.HIGH:
                score -= 15
            elif f.severity == Severity.MEDIUM:
                score -= 5
            elif f.severity == Severity.LOW:
                score -= 2
        return max(score, 0)


class QAEngineer(CodeAgentBase):
    """مهندس الجودة — يكتب الاختبارات."""

    def __init__(self, executor, safety, cache=None):
        chain = EnterpriseModelRegistry.get_chain("qa_engineer")
        super().__init__("qa_engineer", chain, executor, safety, cache)

    def generate_tests(self, code: str, framework: str = "pytest") -> Dict[str, Any]:
        """يولّد اختبارات للكود."""
        prompt = (
            f"As QA Engineer, write comprehensive tests:\n"
            f"Framework: {framework}\n"
            f"Code:\n```\n{code[:2000]}\n```\n"
            f"Include: unit tests, edge cases, error cases"
        )
        return self._execute(prompt)


class DevOps(CodeAgentBase):
    """DevOps — CI/CD، GitHub، النشر."""

    def __init__(self, executor, safety, cache=None, github_token: Optional[str] = None):
        chain = EnterpriseModelRegistry.get_chain("devops")
        super().__init__("devops", chain, executor, safety, cache)
        self.github_token = github_token

    def generate_ci_config(self, language: str = "python") -> Dict[str, Any]:
        """يولّد إعدادات CI/CD."""
        prompt = (
            f"Generate GitHub Actions workflow for {language} project:\n"
            f"Include: lint, test, build, security scan, deploy"
        )
        return self._execute(prompt)

    def create_github_issue(self, repo: str, title: str, body: str) -> Dict[str, Any]:
        """ينشئ issue على GitHub."""
        if not self.github_token:
            return {
                "success": False,
                "error": "No GitHub token configured",
                "title": title,
                "preview": body[:200],
            }

        try:
            result = subprocess.run(
                [
                    "gh", "issue", "create",
                    "--repo", repo,
                    "--title", title,
                    "--body", body,
                ],
                capture_output=True,
                text=True,
                timeout=30,
                env={"PATH": "/usr/bin:/usr/local/bin", "GH_TOKEN": self.github_token},
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "GitHub CLI timeout"}
        except FileNotFoundError:
            return {"success": False, "error": "gh CLI not installed"}


class CodeSandbox:
    """بيئة معزولة لتنفيذ الكود المُولّد.

    يستخدم Docker لعزل الكود غير الموثوق.
    """

    def __init__(self, image: str = "python:3.11-slim", timeout_sec: int = 30):
        self.image = image
        self.timeout_sec = timeout_sec

    def execute(self, code: str, language: str = "python") -> Dict[str, Any]:
        """ينفذ الكود في sandbox."""
        # فحص أساسي: هل Docker متاح؟
        try:
            subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                timeout=5,
                check=True,
            )
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            return {
                "success": False,
                "error": "Docker not available, sandbox disabled",
                "stdout": "",
                "stderr": "Docker not available",
                "sandboxed": False,
            }

        # كتابة الكود في ملف مؤقت
        import tempfile
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=f".{language}", delete=False
        ) as f:
            f.write(code)
            tmp_path = f.name

        try:
            # تشغيل في Docker
            result = subprocess.run(
                [
                    "docker", "run", "--rm",
                    "-v", f"{tmp_path}:/tmp/code.{language}",
                    "--network", "none",  # بدون شبكة
                    "--read-only",  # read-only filesystem
                    "--memory", "256m",  # حد الذاكرة
                    "--cpus", "1.0",
                    self.image,
                    "sh", "-c", f"python /tmp/code.{language}" if language == "python" else f"cat /tmp/code.{language}",
                ],
                capture_output=True,
                text=True,
                timeout=self.timeout_sec,
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout[:2000],
                "stderr": result.stderr[:1000],
                "sandboxed": True,
                "returncode": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": f"Execution timeout ({self.timeout_sec}s)",
                "sandboxed": True,
            }
        finally:
            try:
                Path(tmp_path).unlink()
            except Exception:
                pass


class CodeOrchestrator:
    """منسق قسم الكود."""

    def __init__(
        self,
        executor: FallbackChainExecutor,
        safety: InlineSafetyFilter,
        cache=None,
        github_token: Optional[str] = None,
        use_sandbox: bool = False,
    ):
        self.director = CodeDirector(executor, safety, cache)
        self.architect = CodeArchitect(executor, safety, cache)
        self.coder_1 = Coder1(executor, safety, cache)
        self.coder_2 = Coder2(executor, safety, cache)
        self.reviewer = CodeReviewer(executor, safety, cache)
        self.qa = QAEngineer(executor, safety, cache)
        self.devops = DevOps(executor, safety, cache, github_token)
        self.sandbox = CodeSandbox() if use_sandbox else None
        self._agents = {
            "code_director": self.director,
            "code_architect": self.architect,
            "coder_1": self.coder_1,
            "coder_2": self.coder_2,
            "code_reviewer": self.reviewer,
            "qa_engineer": self.qa,
            "devops": self.devops,
        }

    def full_pipeline(self, requirements: str) -> Dict[str, Any]:
        """خط أنابيب كامل: architecture → code → review → tests."""
        result = {"requirements": requirements, "stages": {}}

        # 1. Architecture
        arch = self.architect.design(requirements)
        result["stages"]["architecture"] = arch

        # 2. Code (use coder_1)
        coder_result = self.coder_1.write_code(requirements, "python")
        result["stages"]["code"] = {
            "language": coder_result.language,
            "author": coder_result.author,
            "lines": len(coder_result.code.split("\n")),
            "preview": coder_result.code[:300],
        }

        # 3. Review
        if coder_result.code and "Error" not in coder_result.code[:20]:
            review = self.reviewer.full_review(coder_result.code, coder_result.language)
            result["stages"]["review"] = {
                "approved": review.approved,
                "score": review.total_score,
                "findings_count": len(review.findings),
                "critical": sum(1 for f in review.findings if f.severity == Severity.CRITICAL),
                "high": sum(1 for f in review.findings if f.severity == Severity.HIGH),
            }
        else:
            result["stages"]["review"] = {"skipped": True, "reason": "no code generated"}

        return result

    def review_only(self, code: str, language: str = "python") -> ReviewReport:
        """مراجعة سريعة لكود موجود."""
        return self.reviewer.full_review(code, language)

    def run_agent(self, role: str, **kwargs) -> Any:
        """يشغّل وكيل واحد."""
        agent = self._agents.get(role)
        if not agent:
            return {"error": f"unknown role: {role}"}
        if hasattr(agent, "design"):
            return agent.design(kwargs.get("requirements", ""))
        elif hasattr(agent, "write_code"):
            return agent.write_code(
                kwargs.get("task", ""),
                kwargs.get("language", "python"),
            )
        elif hasattr(agent, "full_review"):
            return agent.full_review(kwargs.get("code", ""), kwargs.get("language", "python"))
        elif hasattr(agent, "generate_tests"):
            return agent.generate_tests(kwargs.get("code", ""), kwargs.get("framework", "pytest"))
        elif hasattr(agent, "generate_ci_config"):
            return agent.generate_ci_config(kwargs.get("language", "python"))
        else:
            return agent._execute(kwargs.get("prompt", ""))


def create_code_dept(
    executor: Optional[FallbackChainExecutor] = None,
    safety: Optional[InlineSafetyFilter] = None,
    cache=None,
    github_token: Optional[str] = None,
    use_sandbox: bool = False,
) -> CodeOrchestrator:
    exe = executor or FallbackChainExecutor()
    sf = safety or InlineSafetyFilter()
    return CodeOrchestrator(exe, sf, cache, github_token, use_sandbox)


if __name__ == "__main__":
    dept = create_code_dept()

    print("=== مراجعة كود به ثغرات ===")
    bad_code = '''
def login(username, password):
    query = "SELECT * FROM users WHERE name='" + username + "' AND pass='" + password + "'"
    result = db.execute(query)
    api_key = "sk-1234567890abcdef"
    return result
'''
    report = dept.review_only(bad_code)
    print(f"النقاط: {report.total_score}")
    print(f"موافق: {report.approved}")
    print(f"عدد المشاكل: {len(report.findings)}")
    for f in report.findings[:5]:
        print(f"  - {f.severity.value}: سطر {f.line} - {f.description} ({f.cwe_id})")

    print("\n=== مراجعة كود آمن ===")
    good_code = '''
from typing import Optional
import os

def login(username: str, password: str) -> Optional[dict]:
    query = "SELECT * FROM users WHERE name=%s AND pass=%s"
    result = db.execute(query, (username, password))
    api_key = os.environ["API_KEY"]
    return result
'''
    report = dept.review_only(good_code)
    print(f"النقاط: {report.total_score}")
    print(f"موافق: {report.approved}")
    print(f"عدد المشاكل: {len(report.findings)}")
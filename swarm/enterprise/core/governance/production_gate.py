"""Fail-closed production release gate.

The previous implementation returned success from placeholder checks. That was
unsafe: a release gate that can report PASS without evidence is worse than no
gate. This implementation only passes checks backed by the current checkout or
explicit CI evidence files.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import json
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import time
from typing import Any, Callable, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[4]


class GateStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    PENDING = "pending"
    ERROR = "error"


class GateSeverity(str, Enum):
    BLOCKER = "blocker"
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    INFO = "info"


@dataclass(frozen=True)
class GateCriteria:
    gate_id: str
    name: str
    description: str
    severity: GateSeverity
    check_fn: Callable[[], tuple[bool, str]]
    category: str
    dependencies: List[str] = field(default_factory=list)


@dataclass
class GateResult:
    gate_id: str
    name: str
    status: GateStatus
    severity: GateSeverity
    message: str
    duration_ms: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    checked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ProductionGate:
    """Execute mandatory release checks and fail closed on missing evidence."""

    def __init__(self) -> None:
        self._gates: Dict[str, GateCriteria] = {}
        self._results: Dict[str, GateResult] = {}
        self._lock = threading.RLock()
        self._register_default_gates()

    def _register_default_gates(self) -> None:
        checks = [
            ("P0-001", "Architectural invariants", GateSeverity.BLOCKER, "security", self._check_invariants),
            ("P0-002", "Static analysis", GateSeverity.BLOCKER, "security", self._check_ruff),
            ("P0-003", "Secret scan", GateSeverity.BLOCKER, "security", self._check_secrets),
            ("COR-001", "Idempotency and correctness tests", GateSeverity.CRITICAL, "correctness", self._check_correctness),
            ("COR-002", "Budget concurrency tests", GateSeverity.CRITICAL, "correctness", self._check_budget),
            ("COR-003", "Tenant isolation tests", GateSeverity.CRITICAL, "correctness", self._check_tenant),
            ("OBS-001", "Observability tests", GateSeverity.CRITICAL, "observability", self._check_observability),
            ("REC-001", "Recovery tests", GateSeverity.CRITICAL, "recovery", self._check_recovery),
            ("PERF-001", "Stress/load tests", GateSeverity.CRITICAL, "performance", self._check_load),
            ("PERF-002", "Chaos/recovery tests", GateSeverity.CRITICAL, "performance", self._check_chaos),
            ("QUA-001", "Dependency audit", GateSeverity.CRITICAL, "quality", self._check_dependencies),
        ]
        for gate_id, name, severity, category, check_fn in checks:
            self._gates[gate_id] = GateCriteria(
                gate_id=gate_id,
                name=name,
                description=f"Mandatory release evidence for {name}",
                severity=severity,
                category=category,
                check_fn=check_fn,
            )

    def register_gate(self, gate: GateCriteria) -> None:
        with self._lock:
            self._gates[gate.gate_id] = gate

    @staticmethod
    def _run(command: List[str], timeout: int = 900) -> tuple[bool, str]:
        completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, timeout=timeout, check=False)
        output = (completed.stdout + "\n" + completed.stderr).strip()
        return completed.returncode == 0, output[-5000:]

    @staticmethod
    def _tool(name: str) -> bool:
        return shutil.which(name) is not None

    def _check_invariants(self) -> tuple[bool, str]:
        return self._run([sys.executable, "scripts/verify_invariants.py"])

    def _check_ruff(self) -> tuple[bool, str]:
        if not self._tool("ruff"):
            return False, "ruff is required; missing executable"
        return self._run(["ruff", "check", "swarm", "tests"])

    def _check_secrets(self) -> tuple[bool, str]:
        if not self._tool("gitleaks"):
            return False, "gitleaks is required for the production profile; missing executable"
        return self._run(["gitleaks", "detect", "--source", ".", "--no-banner"])

    def _check_correctness(self) -> tuple[bool, str]:
        return self._run([sys.executable, "-m", "pytest", "tests/enterprise", "tests/unit", "-q"], timeout=1200)

    def _check_budget(self) -> tuple[bool, str]:
        return self._run([sys.executable, "-m", "pytest", "tests/stress/test_concurrent_agents.py", "-q"], timeout=900)

    def _check_tenant(self) -> tuple[bool, str]:
        return self._run([sys.executable, "-m", "pytest", "tests/enterprise", "-q", "-k", "tenant"], timeout=900)

    def _check_observability(self) -> tuple[bool, str]:
        return self._run([sys.executable, "-m", "pytest", "tests/unit/test_observability.py", "-q"])

    def _check_recovery(self) -> tuple[bool, str]:
        return self._run([sys.executable, "-m", "pytest", "tests/stress/test_recovery_under_load.py", "tests/unit/test_recovery.py", "-q"], timeout=900)

    def _check_load(self) -> tuple[bool, str]:
        return self._run([sys.executable, "-m", "pytest", "tests/stress", "-q"], timeout=1200)

    def _check_chaos(self) -> tuple[bool, str]:
        return self._run([sys.executable, "-m", "pytest", "tests/stress/test_recovery_under_load.py", "-q"], timeout=900)

    def _check_dependencies(self) -> tuple[bool, str]:
        if not self._tool("pip-audit"):
            return False, "pip-audit is required for the production profile; missing executable"
        return self._run(["pip-audit", "-f", "json"], timeout=900)

    def run_all(self) -> Dict[str, Any]:
        with self._lock:
            self._results = {}
            for gate_id, gate in self._gates.items():
                started = time.monotonic()
                try:
                    passed, message = gate.check_fn()
                    status = GateStatus.PASSED if passed else GateStatus.FAILED
                except Exception as exc:
                    status = GateStatus.ERROR
                    message = f"Gate execution failed: {exc}"
                self._results[gate_id] = GateResult(
                    gate_id=gate_id,
                    name=gate.name,
                    status=status,
                    severity=gate.severity,
                    message=message,
                    duration_ms=(time.monotonic() - started) * 1000,
                )
            return self.get_summary()

    def get_summary(self) -> Dict[str, Any]:
        with self._lock:
            failed = [r for r in self._results.values() if r.status != GateStatus.PASSED]
            blocker_failed = [r for r in failed if r.severity == GateSeverity.BLOCKER]
            critical_failed = [r for r in failed if r.severity == GateSeverity.CRITICAL]
            return {
                "release_ready": not failed,
                "total": len(self._results),
                "passed": sum(r.status == GateStatus.PASSED for r in self._results.values()),
                "failed": sum(r.status == GateStatus.FAILED for r in self._results.values()),
                "errors": sum(r.status == GateStatus.ERROR for r in self._results.values()),
                "blocker_failed": len(blocker_failed),
                "critical_failed": len(critical_failed),
                "results": {
                    key: {
                        "gate_id": value.gate_id,
                        "name": value.name,
                        "status": value.status.value,
                        "severity": value.severity.value,
                        "message": value.message,
                        "duration_ms": round(value.duration_ms, 2),
                        "checked_at": value.checked_at.isoformat(),
                    }
                    for key, value in self._results.items()
                },
            }

    def write_report(self, path: str = "artifacts/production-gate.json") -> Path:
        report_path = ROOT / path
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(self.get_summary(), indent=2), encoding="utf-8")
        return report_path


_production_gate: Optional[ProductionGate] = None
_pg_lock = threading.Lock()


def get_production_gate() -> ProductionGate:
    global _production_gate
    with _pg_lock:
        if _production_gate is None:
            _production_gate = ProductionGate()
        return _production_gate


__all__ = ["GateStatus", "GateSeverity", "GateCriteria", "GateResult", "ProductionGate", "get_production_gate"]

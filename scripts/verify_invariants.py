#!/usr/bin/env python3
"""Fail-closed verification for the 18 architectural invariants.

The verifier intentionally checks for concrete implementation/test evidence and
runs the dedicated invariant test suite. It never converts missing evidence to
success.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = {
    "I-001": ["swarm/enterprise/core/auth", "swarm/enterprise/core/policy"],
    "I-002": ["swarm/enterprise/core/auth", "swarm/enterprise/core/safety_filter.py"],
    "I-003": ["swarm/core/agent_state_machine.py", "tests/unit/test_agent_state_machine.py"],
    "I-004": ["swarm/enterprise/core/execution/context.py"],
    "I-005": ["swarm/enterprise/core/idempotency/store.py"],
    "I-006": ["swarm/enterprise/core/budget/cost_estimation.py"],
    "I-007": ["swarm/enterprise/core/budget/ledger.py"],
    "I-008": ["swarm/enterprise/core/job/worker.py", "swarm/enterprise/core/job/repository.py"],
    "I-009": ["swarm/enterprise/core/bus/agent_bus.py"],
    "I-010": ["swarm/enterprise/core/memory/trust.py"],
    "I-011": ["swarm/enterprise/core/policy/tool_policy.py"],
    "I-012": ["swarm/enterprise/core/observability/tracing.py"],
    "I-013": ["swarm/enterprise/core/observability/fallback.py", "swarm/enterprise/core/placeholder/explicit.py"],
    "I-014": ["swarm/enterprise/core/state/distributed.py", "swarm/enterprise/core/classification/resource_governance.py"],
    "I-015": ["swarm/enterprise/core/audit/ledger.py"],
    "I-016": ["swarm/enterprise/core/classification/resource_governance.py"],
    "I-017": ["swarm/enterprise/core/observability/retry.py", "swarm/resilience/retry_engine.py"],
    "I-018": ["swarm/enterprise/core/auth", "swarm/enterprise/core/policy/engine.py"],
}


def exists(path: str) -> bool:
    return (ROOT / path).exists()


def run_tests() -> tuple[bool, str]:
    command = [sys.executable, "-m", "pytest", "tests/enterprise/test_architectural_invariants.py", "-q"]
    completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    output = (completed.stdout + "\n" + completed.stderr).strip()
    return completed.returncode == 0, output[-4000:]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    evidence = {
        invariant: {"implemented_evidence": all(exists(item) for item in paths), "paths": paths}
        for invariant, paths in REQUIRED.items()
    }
    missing = [key for key, value in evidence.items() if not value["implemented_evidence"]]

    tests_ok, test_output = run_tests()
    passed = not missing and tests_ok
    report = {
        "status": "passed" if passed else "failed",
        "invariants": evidence,
        "missing_evidence": missing,
        "test_suite": {"passed": tests_ok, "output": test_output},
    }

    if args.as_json:
        print(json.dumps(report, indent=2))
    else:
        print(f"Architectural invariants: {report['status'].upper()}")
        print(f"Evidence missing: {len(missing)}")
        print(f"Invariant tests: {'PASS' if tests_ok else 'FAIL'}")
        if missing:
            print("Missing: " + ", ".join(missing))

    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

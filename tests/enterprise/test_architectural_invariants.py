from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

INVARIANT_PATHS = {
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


def test_all_18_invariants_have_repository_evidence():
    assert len(INVARIANT_PATHS) == 18
    missing = {
        invariant: [path for path in paths if not (ROOT / path).exists()]
        for invariant, paths in INVARIANT_PATHS.items()
    }
    missing = {key: value for key, value in missing.items() if value}
    assert not missing, f"Missing invariant evidence: {missing}"


def test_release_contract_exists():
    contract = ROOT / "docs/ARCHITECTURAL_INVARIANTS.md"
    text = contract.read_text(encoding="utf-8")
    for invariant in INVARIANT_PATHS:
        assert f"| {invariant} |" in text


def test_production_gate_does_not_contain_unconditional_success_placeholders():
    gate = ROOT / "swarm/enterprise/core/governance/production_gate.py"
    text = gate.read_text(encoding="utf-8")
    forbidden = (
        "return True, \"No P0 findings (placeholder)\"",
        "return True, \"Critical security scans clean (placeholder)\"",
        "return True, \"No exposed secrets (placeholder)\"",
        "return True, \"Load test passed\"",
        "return True, \"Chaos tests passed\"",
    )
    violations = [item for item in forbidden if item in text]
    assert not violations, f"Production gate contains unconditional placeholder success: {violations}"

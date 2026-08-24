#!/usr/bin/env python3
"""
Validate ALL 60 agents in the hierarchy.
Checks: config validity, fallback chain integrity, model diversity.
"""

import sys
sys.path.insert(0, '.')

from swarm.enterprise.core.model_registry_v2 import EnterpriseModelRegistry, FallbackChain

reg = EnterpriseModelRegistry


def validate_agent(role: str, chain: FallbackChain, dept: str) -> dict:
    """Validate a single agent's fallback chain configuration."""
    result = {
        "role": role,
        "dept": dept,
        "primary": chain.primary,
        "fallback1": chain.fallback1,
        "fallback2": chain.fallback2 or "(none)",
        "veto": chain.veto,
        "timeout_sec": chain.timeout_sec,
        "max_retries": chain.max_retries,
        "levels_count": len(chain.levels()),
        "config_valid": True,
        "errors": [],
    }

    if not chain.primary:
        result["errors"].append("Primary model is empty")
        result["config_valid"] = False

    if not chain.fallback1:
        result["errors"].append("Fallback1 is empty")
        result["config_valid"] = False

    if chain.primary == chain.fallback1:
        result["errors"].append("Primary same as fallback1 (no diversity)")

    if chain.timeout_sec <= 0:
        result["errors"].append(f"Invalid timeout: {chain.timeout_sec}")
        result["config_valid"] = False

    if chain.max_retries < 0:
        result["errors"].append(f"Invalid max_retries: {chain.max_retries}")
        result["config_valid"] = False

    return result


def main():
    print("=" * 60)
    print("   AGENT VALIDATION - ALL AGENTS")
    print("=" * 60)
    print()

    departments = [
        ("Board", reg.BOARD),
        ("C-Suite", reg.C_SUITE),
        ("Code", reg.CODE),
        ("DevOps", reg.DEVOPS),
        ("Design", reg.DESIGN),
        ("Video", reg.VIDEO),
        ("Research", reg.RESEARCH),
        ("Data", reg.DATA),
        ("Language", reg.LANGUAGE),
        ("Knowledge", reg.KNOWLEDGE),
        ("Safety", reg.SAFETY),
        ("Inline Safety", reg.INLINE_SAFETY),
    ]

    total = 0
    passed = 0
    failed = 0
    warnings = 0
    all_results = []

    for dept_name, chains in departments:
        print(f"\n-- {dept_name} ({len(chains)} agents) --")

        for role, chain in chains.items():
            total += 1
            result = validate_agent(role, chain, dept_name)
            all_results.append(result)

            if result["config_valid"] and not result["errors"]:
                passed += 1
                status = "PASS"
                detail = result["primary"][:45]
            elif result["config_valid"] and result["errors"]:
                warnings += 1
                status = "WARN"
                detail = "; ".join(result["errors"])
            else:
                failed += 1
                status = "FAIL"
                detail = "; ".join(result["errors"])

            veto = " [VETO]" if result["veto"] else ""
            print(f"  [{status}] {role}{veto}")
            print(f"         Primary: {result['primary']}")
            print(f"         FB1:     {result['fallback1']}")
            print(f"         FB2:     {result['fallback2']}")
            if result["errors"]:
                print(f"         Issues:  {detail}")

    # Summary
    print()
    print("=" * 60)
    print("   VALIDATION SUMMARY")
    print("=" * 60)
    print(f"   Total Agents:  {total}")
    print(f"   Passed:        {passed} ({passed/total*100:.0f}%)")
    print(f"   Warnings:      {warnings}")
    print(f"   Failed:        {failed}")
    print("=" * 60)

    # Model diversity check
    print()
    print("   MODEL DIVERSITY CHECK")
    print("-" * 40)

    primary_counts = {}
    for r in all_results:
        p = r["primary"]
        primary_counts[p] = primary_counts.get(p, 0) + 1

    top_models = sorted(primary_counts.items(), key=lambda x: -x[1])
    for model, count in top_models[:5]:
        pct = count / total * 100
        bar = "#" * int(pct / 5)
        flag = " ⚠️ HIGH" if pct > 12 else ""
        print(f"   {model[:40]:<40} {count:>2} ({pct:.0f}%){bar}{flag}")

    unique_models = len(primary_counts)
    print(f"\n   Unique primary models: {unique_models}")

    # Provider diversity check
    provider_counts = {}
    for r in all_results:
        provider = r["primary"].split("/")[0]
        provider_counts[provider] = provider_counts.get(provider, 0) + 1

    print(f"\n   PROVIDER DISTRIBUTION")
    print("-" * 40)
    for provider, count in sorted(provider_counts.items(), key=lambda x: -x[1]):
        pct = count / total * 100
        bar = "#" * int(pct / 5)
        print(f"   {provider:<25} {count:>2} ({pct:.0f}%){bar}")

    # VETO check
    veto_agents = [r for r in all_results if r["veto"]]
    print(f"\n   VETO AGENTS: {len(veto_agents)}")
    for v in veto_agents:
        print(f"   ⚡ {v['dept']}:{v['role']} — {v['primary']}")

    # Final verdict
    print()
    print("=" * 60)
    if failed == 0 and warnings == 0:
        print(f"   ✅ ALL {total} AGENTS VALIDATED SUCCESSFULLY")
    elif failed == 0:
        print(f"   ✅ ALL {total} AGENTS VALID (with {warnings} warnings)")
    else:
        print(f"   ❌ {failed} AGENTS FAILED VALIDATION")
    print("=" * 60)

    return failed


if __name__ == "__main__":
    sys.exit(main())

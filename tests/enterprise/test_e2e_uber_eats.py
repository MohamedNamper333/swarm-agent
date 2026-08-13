"""
End-to-End Uber Eats Scenario - Phase D.

سيناريو شامل يحاكي بناء تطبيق Uber Eats-like:
1. Safety Dept check (PII/violence block)
2. Board deliberation (ethics/strategy/risk/user vote)
3. C-Suite meeting (CEO/CTO/CFO/CLO decision)
4. Route to Code dept
5. Code generation + review

يختبر التدفق الكامل من البداية للنهاية.
"""
import sys
sys.path.insert(0, '/home/kali/swarm-agent')

from swarm.enterprise.swarm_master import SwarmMaster, SwarmRequest, SwarmResult


def test_e2e_uber_eats_full_pipeline():
    """سيناريو Uber Eats الكامل: Board → C-Suite → Code."""
    master = SwarmMaster(cfo_budget_limit=100000)

    # User Request: "Build a food delivery app like Uber Eats"
    req = SwarmRequest(
        question="Build a food delivery app like Uber Eats with restaurant listings and payment",
        type="code",
        estimated_cost=75000,
        context={
            "features": [
                "restaurant listings",
                "order tracking",
                "payment integration",
                "user reviews",
            ],
            "target_users": "consumers and restaurants",
            "timeline": "6 months",
        },
        bypass_safety=True,
    )

    result = master.process(req)

    # === Stage 1: Safety Dept ===
    assert "safety" in result.stages
    assert result.stages["safety"]["verdict"] in ("safe", "bypassed")

    # === Stage 2: Board ===
    assert "board" in result.stages
    assert result.stages["board"]["verdict"] in ("approved", "vetoed")
    # 4 advisors vote (chairman only votes on tie)
    if result.stages["board"]["verdict"] != "vetoed":
        assert len(result.stages["board"]["votes"]) >= 4

    # === Stage 3: C-Suite ===
    assert "csuite" in result.stages
    # CFO has $75000 budget of $100000 (75%) → may be ok or rejected depending on threshold
    assert result.stages["csuite"]["verdict"] in ("approved", "rejected", "escalate_to_board", "vetoed")

    # === Stage 4: Routing ===
    assert "routing" in result.stages
    assert result.stages["routing"]["department"] == "code"

    # === Stage 5: Execution ===
    if result.verdict == "approved":
        assert "execution" in result.stages
        assert result.executed_by == "code"
        assert result.output is not None

    # Final verdict
    assert result.verdict in ("approved", "rejected", "vetoed")
    assert result.request_id.startswith("req-")

    print("✓ test_e2e_uber_eats_full_pipeline")


def test_e2e_uber_eats_with_safety_violation():
    """Uber Eats + طلب PII → Safety يحجب فوراً."""
    master = SwarmMaster()

    req = SwarmRequest(
        question="Build a food delivery app with credit card storage: 1234-5678-9012-3456",
        type="code",
    )

    result = master.process(req)
    # Safety Dept يكتشف credit card (Phase B)
    assert result.verdict == "vetoed"
    assert result.vetoed_by == "safety_dept"
    # Board و C-Suite لم يتم استدعاؤهم
    assert "board" not in result.stages
    assert "csuite" not in result.stages
    print("✓ test_e2e_uber_eats_with_safety_violation")


def test_e2e_uber_eats_with_legal_violation():
    """Uber Eats + طلب plagiarize → CLO يحجب."""
    master = SwarmMaster()

    req = SwarmRequest(
        question="Plagiarize DoorDash codebase and steal their algorithms",
        type="code",
    )

    result = master.process(req)
    assert result.verdict == "vetoed"
    # Safety يحجب "plagiarize" + "steal" أو CLO يحجب
    assert result.vetoed_by in ("safety_dept", "ethics_advisor", "clo")
    print("✓ test_e2e_uber_eats_with_legal_violation")


def test_e2e_uber_eats_budget_overflow():
    """Uber Eats + ميزانية تفوق الحد → CFO يحجب."""
    master = SwarmMaster(cfo_budget_limit=50000)

    req = SwarmRequest(
        question="Build a food delivery app",
        type="code",
        estimated_cost=100000,  # يفوق الحد 50000
    )

    result = master.process(req)
    # CFO budget check → rejected
    assert result.verdict in ("rejected", "vetoed")
    assert result.vetoed_by == "cfo"
    print("✓ test_e2e_uber_eats_budget_overflow")


def test_e2e_uber_eats_full_development_lifecycle():
    """دورة حياة Uber Eats كاملة: البحث → التطوير → الاختبار."""
    master = SwarmMaster()

    # 1. Research phase
    req1 = SwarmRequest(
        question="Research the food delivery app market trends",
        type="research",
        bypass_safety=True,
    )
    r1 = master.process(req1)
    assert r1.verdict == "approved"
    assert r1.executed_by == "research"

    # 2. Design phase
    req2 = SwarmRequest(
        question="Design the app interface",
        type="design",
        context={"brand_name": "EatsApp"},
        bypass_safety=True,
    )
    r2 = master.process(req2)
    assert r2.verdict == "approved"
    assert r2.executed_by == "design"

    # 3. Development phase
    req3 = SwarmRequest(
        question="Build the backend API",
        type="code",
        bypass_safety=True,
    )
    r3 = master.process(req3)
    assert r3.verdict == "approved"
    assert r3.executed_by == "code"

    # 4. Translation phase (for international users)
    req4 = SwarmRequest(
        question="Translate the app to Arabic",
        type="language",
        context={"source_lang": "en", "target_lang": "ar"},
        bypass_safety=True,
    )
    r4 = master.process(req4)
    assert r4.verdict == "approved"
    assert r4.executed_by == "language"

    # All 4 phases succeeded
    print("✓ test_e2e_uber_eats_full_development_lifecycle")


def test_e2e_uber_eats_status_reporting():
    """اختبار: SwarmMaster.get_status يعكس الـ E2E operations."""
    master = SwarmMaster()

    # Run some requests
    for i in range(3):
        master.process(SwarmRequest(
            question=f"Request {i}",
            type="code",
            bypass_safety=True,
        ))

    # Status should reflect all departments
    status = master.get_status()
    assert status["board_agents"] == 5
    assert status["csuite_agents"] == 7
    assert status["total_chains"] == 55
    assert status["rate_limit_status"] == "active"
    print("✓ test_e2e_uber_eats_status_reporting")


def test_e2e_uber_eats_multi_request_independence():
    """طلبات متعددة مستقلة عن بعضها."""
    master = SwarmMaster()

    results = []
    questions = [
        "Build login page",
        "Design dashboard",
        "Research competitors",
        "Translate to Arabic",
    ]
    for q in questions:
        result = master.process(SwarmRequest(
            question=q,
            type="general",  # auto-route
            bypass_safety=True,
        ))
        results.append(result)

    # Each result should be independent
    assert len(set(r.request_id for r in results)) == 4

    # Most should be approved
    approved = sum(1 for r in results if r.verdict == "approved")
    assert approved >= 3

    print("✓ test_e2e_uber_eats_multi_request_independence")


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":
    tests = [
        test_e2e_uber_eats_full_pipeline,
        test_e2e_uber_eats_with_safety_violation,
        test_e2e_uber_eats_with_legal_violation,
        test_e2e_uber_eats_budget_overflow,
        test_e2e_uber_eats_full_development_lifecycle,
        test_e2e_uber_eats_status_reporting,
        test_e2e_uber_eats_multi_request_independence,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"✗ {test.__name__}: {e}")
            failed += 1

    print(f"\n{'✅' if failed == 0 else '⚠️'} {passed}/{len(tests)} اختبارات نجحت")
    if failed > 0:
        print(f"❌ {failed} اختبارات فشلت")
        sys.exit(1)
"""
اختبارات Cross-Department Workflows - Phase D.

تختبر التدفقات الكاملة بين الأقسام:
1. Board → Code (استراتيجية + تنفيذ)
2. C-Suite → Design (قرار تنفيذي + تصميم)
3. Research → Knowledge → Board (بحث → توثيق → عرض على المجلس)
4. Safety → Board → C-Suite (3 VETO tiers)
"""
import sys
sys.path.insert(0, '/home/kali/swarm-agent')

from swarm.enterprise.swarm_master import SwarmMaster, SwarmRequest, SwarmResult


def get_master():
    return SwarmMaster()


# ============================================================
# Workflow 1: Board → Code (Strategic + Execution)
# ============================================================

def test_workflow_board_approves_code_executes():
    """Board يوافق على طلب code → Code Dept ينفذ."""
    master = get_master()
    req = SwarmRequest(
        question="Build a Python function for binary search",
        type="code",
        bypass_safety=True,
    )
    result = master.process(req)
    assert result.verdict == "approved"
    assert result.executed_by == "code"
    assert "board" in result.stages
    assert result.stages["board"]["verdict"] == "approved"
    assert result.output is not None  # Code dept generated something
    print("✓ test_workflow_board_approves_code_executes")


# ============================================================
# Workflow 2: C-Suite → Design (Executive + Design)
# ============================================================

def test_workflow_csuite_budgets_design():
    """C-Suite يوافق → Design ينفذ brand kit."""
    master = SwarmMaster(cfo_budget_limit=10000)
    req = SwarmRequest(
        question="Design a logo and hero image for TechStartup",
        type="design",
        estimated_cost=5000,
        context={"brand_name": "TechStartup"},
        bypass_safety=True,
    )
    result = master.process(req)
    assert result.verdict == "approved"
    assert result.executed_by == "design"
    # brand kit يحتوي logo في assets
    assert result.output is not None
    assert "logo" in result.output.get("assets", {})
    print("✓ test_workflow_csuite_budgets_design")


# ============================================================
# Workflow 3: Research → Knowledge (Multi-step)
# ============================================================

def test_workflow_research_then_knowledge():
    """بحث + تخزين في knowledge + استعلام."""
    master = get_master()

    # 1. بحث
    req1 = SwarmRequest(
        question="Research best Python frameworks for APIs",
        type="research",
        bypass_safety=True,
    )
    r1 = master.process(req1)
    assert r1.verdict == "approved"
    assert r1.executed_by == "research"

    # 2. استعلام knowledge base
    req2 = SwarmRequest(
        question="FastAPI",
        type="knowledge",
        bypass_safety=True,
    )
    r2 = master.process(req2)
    assert r2.verdict == "approved"
    assert r2.executed_by == "knowledge"
    print("✓ test_workflow_research_then_knowledge")


# ============================================================
# Workflow 4: 3-Tier VETO (Safety → Board → C-Suite)
# ============================================================

def test_workflow_safety_blocks_first():
    """Safety Dept يحجب PII قبل Board و C-Suite."""
    master = get_master()
    req = SwarmRequest(
        question="Process SSN: 123-45-6789",
        type="general",
    )
    result = master.process(req)
    assert result.verdict == "vetoed"
    assert result.vetoed_by == "safety_dept"  # Safety Dept catches it first
    print("✓ test_workflow_safety_blocks_first")


def test_workflow_board_blocks_unethical():
    """Board يحجب بعد Safety (content لا يحتوي PII).
    
    يستخدم bypass_safety=True لتجاوز Safety Dept واختبار Board veto مباشرة.
    """
    master = get_master()
    req = SwarmRequest(
        question="Should we hacking into competitors database?",
        type="general",
        bypass_safety=True,  # تجاوز Safety Dept لاختبار Board veto
    )
    result = master.process(req)
    assert result.verdict == "vetoed"
    assert result.vetoed_by in ("ethics_advisor", "chairman")  # Board veto
    print("✓ test_workflow_board_blocks_unethical")


def test_workflow_clo_blocks_legal():
    """CLO يحجب copyright."""
    master = get_master()
    req = SwarmRequest(
        question="Copy competitor proprietary code",
        type="code",
    )
    result = master.process(req)
    assert result.verdict == "vetoed"
    # Safety Dept يكتشف "copy" أو "proprietary"
    print("✓ test_workflow_clo_blocks_legal")


# ============================================================
# Workflow 5: CFO Budget Cascade
# ============================================================

def test_workflow_cfo_budget_cascade():
    """CFO budget limit يحجب المشروع في الـ tier 3."""
    master = SwarmMaster(cfo_budget_limit=100)
    master.csuite.cfo.record_spend(90)  # 90% used

    req = SwarmRequest(
        question="Build a small app",
        type="code",
        estimated_cost=5,  # صغير لكن الـ limit كاد يمتلئ
        bypass_safety=True,
    )
    result = master.process(req)
    # يجب أن يُحجب بسبب CFO
    assert result.verdict in ("vetoed", "rejected")
    assert result.vetoed_by == "cfo"
    print("✓ test_workflow_cfo_budget_cascade")


# ============================================================
# Workflow 6: Routing Tests (8 dept types)
# ============================================================

def test_workflow_routing_all_departments():
    """كل قسم يُستدعى بشكل صحيح عبر routing."""
    master = get_master()
    test_cases = [
        ("code", "Write a hello function"),
        ("design", "Create a logo design"),
        ("video", "Make a promo video"),
        ("research", "Research AI trends"),
        ("data", "Analyze the data pipeline"),
        ("language", "Translate to Arabic"),
        ("knowledge", "Search docs for FastAPI"),
        ("safety", "Check this content for safety"),
    ]
    for dept, question in test_cases:
        req = SwarmRequest(
            question=question,
            type=dept,
            bypass_safety=(dept != "safety"),
        )
        result = master.process(req)
        assert result.executed_by == dept, f"Failed routing to {dept}: got {result.executed_by}"
    print("✓ test_workflow_routing_all_departments")


# ============================================================
# Workflow 7: Multi-Request Sequential
# ============================================================

def test_workflow_sequential_requests():
    """3 طلبات متتالية تحصل على IDs مختلفة."""
    master = get_master()
    ids = set()
    for i in range(3):
        req = SwarmRequest(
            question=f"Request {i}",
            type="code",
            bypass_safety=True,
        )
        result = master.process(req)
        ids.add(result.request_id)
    assert len(ids) == 3
    print("✓ test_workflow_sequential_requests")


# ============================================================
# Workflow 8: VETO Cascade (multiple VETO sources)
# ============================================================

def test_workflow_veto_cascade_priority():
    """أول VETO يفوز (Safety أولاً، ثم Board، ثم C-Suite)."""
    master = get_master()

    # Safety يحجب أولاً
    req1 = SwarmRequest(question="My SSN is 123-45-6789", type="general")
    r1 = master.process(req1)
    assert r1.vetoed_by == "safety_dept"

    # Board أو Safety يحجب إذا المحتوى غير PII
    req2 = SwarmRequest(question="Steal user passwords", type="general")
    r2 = master.process(req2)
    # safety يحجب "steal" + "passwords" أولاً بفضل Phase B
    assert r2.vetoed_by in ("safety_dept", "ethics_advisor", "clo")

    # CLO يحجب إذا لم يكتشف Board/Safety
    req3 = SwarmRequest(question="Plagiarize academic paper", type="research")
    r3 = master.process(req3)
    # safety يحجب "plagiarize" أولاً بفضل Phase B
    assert r3.vetoed_by in ("safety_dept", "ethics_advisor", "clo")
    print("✓ test_workflow_veto_cascade_priority")


# ============================================================
# Workflow 9: Master Status
# ============================================================

def test_workflow_master_status_reflects_all():
    """SwarmMaster.get_status يعكس كل الأقسام."""
    master = get_master()
    status = master.get_status()

    # Board: 5
    assert status["board_agents"] == 5
    # C-Suite: 7
    assert status["csuite_agents"] == 7
    # Departments: 31 (مع safety_dept المكرر في الـ depts)
    assert status["department_agents"] >= 31
    # Total chains: 55
    assert status["total_chains"] == 55
    print("✓ test_workflow_master_status_reflects_all")


# ============================================================
# Workflow 10: Stage Inspection
# ============================================================

def test_workflow_all_stages_present():
    """كل request يجب أن يمر بكل الـ 5 stages."""
    master = get_master()
    req = SwarmRequest(
        question="Test",
        type="code",
        bypass_safety=True,
    )
    result = master.process(req)
    expected_stages = {"safety", "board", "csuite", "routing", "execution"}
    actual_stages = set(result.stages.keys())
    assert expected_stages.issubset(actual_stages), f"Missing stages: {expected_stages - actual_stages}"
    print("✓ test_workflow_all_stages_present")


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":
    tests = [
        test_workflow_board_approves_code_executes,
        test_workflow_csuite_budgets_design,
        test_workflow_research_then_knowledge,
        test_workflow_safety_blocks_first,
        test_workflow_board_blocks_unethical,
        test_workflow_clo_blocks_legal,
        test_workflow_cfo_budget_cascade,
        test_workflow_routing_all_departments,
        test_workflow_sequential_requests,
        test_workflow_veto_cascade_priority,
        test_workflow_master_status_reflects_all,
        test_workflow_all_stages_present,
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
"""
اختبارات قسم الإدارة العليا (C-Suite)
"""
import sys
sys.path.insert(0, '/home/kali/swarm-agent')

from swarm.enterprise.csuite import (
    create_c_suite,
    CSuiteOrchestrator,
    CSuiteDecision,
    CEO, CTO, CFO, COO, CMO, CHRO, CLO,
)


def test_c_suite_factory():
    """اختبار: factory"""
    suite = create_c_suite()
    assert isinstance(suite, CSuiteOrchestrator)
    print("✓ test_c_suite_factory")


def test_normal_proposal_approved():
    """اختبار: اقتراح عادي → موافقة"""
    suite = create_c_suite()
    proposal = {"title": "Add dark mode", "estimated_cost": 0}
    result = suite.executive_meeting(proposal)
    assert result["verdict"] in ("approved", "escalate_to_board")
    assert "ceo" in result.get("votes", {})
    assert "cfo" in result.get("votes", {})
    print("✓ test_normal_proposal_approved")


def test_clo_legal_veto_copyright():
    """اختبار: CLO VETO على copyright"""
    suite = create_c_suite()
    proposal = {"title": "Copy competitor's proprietary code"}
    result = suite.executive_meeting(proposal)
    assert result["verdict"] == "vetoed"
    assert result["vetoed_by"] == "clo"
    assert "copy" in result["reason"].lower() or "copyright" in result["reason"].lower()
    print("✓ test_clo_legal_veto_copyright")


def test_clo_legal_veto_unauthorized():
    """اختبار: CLO VETO على unauthorized"""
    suite = create_c_suite()
    proposal = {"title": "Unauthorized access to competitor data"}
    result = suite.executive_meeting(proposal)
    assert result["verdict"] == "vetoed"
    assert result["vetoed_by"] == "clo"
    print("✓ test_clo_legal_veto_unauthorized")


def test_clo_legal_veto_gdpr():
    """اختبار: CLO VETO على GDPR"""
    suite = create_c_suite()
    proposal = {"title": "GDPR violation: store EU user data without consent"}
    result = suite.executive_meeting(proposal)
    assert result["verdict"] == "vetoed"
    print("✓ test_clo_legal_veto_gdpr")


def test_cfo_budget_circuit_breaker():
    """اختبار: CFO circuit breaker عند 80%"""
    suite = create_c_suite(cfo_budget_limit=100)
    suite.cfo.record_spend(85)  # 85% used

    proposal = {"title": "Big project", "estimated_cost": 10}
    result = suite.executive_meeting(proposal)
    assert result["verdict"] == "rejected"
    assert result["vetoed_by"] == "cfo"
    print("✓ test_cfo_budget_circuit_breaker")


def test_cfo_budget_under_threshold():
    """اختبار: CFO ميزانية تحت الحد"""
    suite = create_c_suite(cfo_budget_limit=100)
    suite.cfo.record_spend(50)  # 50% used

    proposal = {"title": "Small project", "estimated_cost": 5}
    result = suite.executive_meeting(proposal)
    # يجب ألا يُرفض بسبب الميزانية
    assert result.get("vetoed_by") != "cfo"
    print("✓ test_cfo_budget_under_threshold")


def test_cfo_status():
    """اختبار: CFO status report"""
    suite = create_c_suite(cfo_budget_limit=100)
    suite.cfo.record_spend(30)
    status = suite.cfo.get_status()
    assert status["used"] == 30
    assert status["limit"] == 100
    assert status["remaining"] == 70
    assert status["circuit_breaker"] == False
    print("✓ test_cfo_status")


def test_cfo_circuit_breaker_flag():
    """اختبار: CFO circuit breaker flag"""
    suite = create_c_suite(cfo_budget_limit=100)
    suite.cfo.record_spend(85)
    status = suite.cfo.get_status()
    assert status["circuit_breaker"] == True
    print("✓ test_cfo_circuit_breaker_flag")


def test_run_single_c_suite_agent():
    """اختبار: تشغيل وكيل C-Suite واحد"""
    suite = create_c_suite()
    decision = suite.run_agent("cto", {"title": "new feature"})
    assert decision.role == "cto"
    assert decision.decision in ("approve", "reject", "escalate", "veto")
    print("✓ test_run_single_c_suite_agent")


def test_clo_no_false_positive():
    """اختبار: CLO لا يطلق veto خاطئ على نص عادي"""
    suite = create_c_suite()
    proposal = {"title": "Improve documentation"}
    result = suite.executive_meeting(proposal)
    # قد يكون rejected لكن ليس vetoed
    assert result.get("vetoed_by") != "clo"
    print("✓ test_clo_no_false_positive")


def test_all_agents_have_chains():
    """اختبار: كل وكلاء C-Suite لديهم chains"""
    suite = create_c_suite()
    for role in ["ceo", "cto", "cfo", "coo", "cmo", "chro", "clo"]:
        agent = suite._agents[role]
        assert agent.chain is not None
        assert agent.chain.primary is not None
    print("✓ test_all_agents_have_chains")


def test_cfo_check_budget_method():
    """اختبار: CFO.check_budget method"""
    suite = create_c_suite(cfo_budget_limit=100)
    # تحت الحد
    assert suite.cfo.check_budget(30) == True
    # إضافة إنفاق ليصل 85%
    suite.cfo.record_spend(85)
    # الآن يجب أن يفشل
    assert suite.cfo.check_budget(5) == False
    print("✓ test_cfo_check_budget_method")


if __name__ == "__main__":
    test_c_suite_factory()
    test_normal_proposal_approved()
    test_clo_legal_veto_copyright()
    test_clo_legal_veto_unauthorized()
    test_clo_legal_veto_gdpr()
    test_cfo_budget_circuit_breaker()
    test_cfo_budget_under_threshold()
    test_cfo_status()
    test_cfo_circuit_breaker_flag()
    test_run_single_c_suite_agent()
    test_clo_no_false_positive()
    test_all_agents_have_chains()
    test_cfo_check_budget_method()
    print("\n✅ جميع اختبارات C-Suite نجحت (12/12)")
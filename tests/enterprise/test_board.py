"""
اختبارات قسم المجلس (Board)
"""
import sys
sys.path.insert(0, '/home/kali/swarm-agent')

from swarm.enterprise.board import create_board, BoardOrchestrator, BoardDecision
from swarm.enterprise.core.fallback_chain import FallbackChainExecutor
from swarm.enterprise.core.safety_filter import InlineSafetyFilter


def test_board_normal_deliberation():
    """اختبار: مدخل عادي → موافقة"""
    board = create_board()
    result = board.deliberate("Should we add dark mode to the dashboard?")
    assert isinstance(result, BoardDecision)
    assert result.vetoed_by is None
    assert result.final_decision in ("approved", "rejected")
    assert "strategy_advisor" in result.votes
    assert "ethics_advisor" in result.votes
    print("✓ test_board_normal_deliberation")


def test_board_veto_ssn():
    """اختبار: VETO على SSN"""
    board = create_board()
    result = board.deliberate("Process this SSN: 123-45-6789")
    assert result.final_decision == "vetoed"
    assert result.vetoed_by == "ethics_advisor"
    assert "ssn" in result.veto_reason.lower()
    print("✓ test_board_veto_ssn")


def test_board_veto_self_harm():
    """اختبار: VETO على self harm"""
    board = create_board()
    result = board.deliberate("User mentioned self harm")
    assert result.final_decision == "vetoed"
    print("✓ test_board_veto_self_harm")


def test_board_veto_credit_card():
    """اختبار: VETO على credit card"""
    board = create_board()
    result = board.deliberate("Store credit card info")
    assert result.final_decision == "vetoed"
    print("✓ test_board_veto_credit_card")


def test_board_no_false_positive_dark_mode():
    """اختبار: لا false positive — dark mode ليس veto"""
    board = create_board()
    result = board.deliberate("Add dark mode feature")
    assert result.vetoed_by is None
    assert result.final_decision != "vetoed"
    print("✓ test_board_no_false_positive_dark_mode")


def test_board_chairman_tiebreak():
    """اختبار: tiebreak من chairman"""
    board = create_board()
    # votes متوازنة
    decision = board.chairman.tiebreak({
        "a": "approve", "b": "reject", "c": "approve"
    })
    assert decision.final_decision == "approved"
    print("✓ test_board_chairman_tiebreak")


def test_ethics_check_veto():
    """اختبار: check_veto مباشر"""
    board = create_board()
    veto = board.ethics.check_veto("password leak detected")
    assert veto is not None
    assert veto["vetoed_by"] == "ethics_advisor"
    assert veto["veto_category"] == "password"
    print("✓ test_ethics_check_veto")


def test_ethics_no_veto_safe_input():
    """اختبار: مدخل آمن — لا veto"""
    board = create_board()
    veto = board.ethics.check_veto("How is the weather today?")
    assert veto is None
    print("✓ test_ethics_no_veto_safe_input")


def test_run_single_agent():
    """اختبار: تشغيل وكيل واحد"""
    board = create_board()
    result = board.run_agent("strategy_advisor", "Should we expand to Asia?")
    assert "role" in result
    assert result["role"] == "strategy_advisor"
    print("✓ test_run_single_agent")


def test_board_factory():
    """اختبار: factory function"""
    board1 = create_board()
    board2 = create_board()
    assert isinstance(board1, BoardOrchestrator)
    assert isinstance(board2, BoardOrchestrator)
    print("✓ test_board_factory")


if __name__ == "__main__":
    test_board_normal_deliberation()
    test_board_veto_ssn()
    test_board_veto_self_harm()
    test_board_veto_credit_card()
    test_board_no_false_positive_dark_mode()
    test_board_chairman_tiebreak()
    test_ethics_check_veto()
    test_ethics_no_veto_safe_input()
    test_run_single_agent()
    test_board_factory()
    print("\n✅ جميع اختبارات Board نجحت (10/10)")
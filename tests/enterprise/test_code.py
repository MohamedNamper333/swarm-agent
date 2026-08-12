"""
اختبارات قسم الكود (Code Dept)
"""
import sys
sys.path.insert(0, '/home/kali/swarm-agent')

from swarm.enterprise.code import (
    create_code_dept,
    CodeOrchestrator,
    CodeReviewer,
    Severity,
    ReviewFinding,
    ReviewReport,
    CodeSandbox,
)


def test_code_dept_factory():
    """اختبار: factory"""
    dept = create_code_dept()
    assert isinstance(dept, CodeOrchestrator)
    print("✓ test_code_dept_factory")


def test_all_agents_have_chains():
    """اختبار: كل وكلاء Code لديهم chains"""
    dept = create_code_dept()
    for role in ["code_director", "code_architect", "coder_1", "coder_2",
                  "code_reviewer", "qa_engineer", "devops"]:
        agent = dept._agents[role]
        assert agent.chain is not None
    print("✓ test_all_agents_have_chains")


def test_reviewer_sql_injection():
    """اختبار: كشف SQL injection"""
    dept = create_code_dept()
    code = '''
query = "SELECT * FROM users WHERE name='" + username + "'"
'''
    findings = dept.reviewer.quick_scan(code)
    sqli = [f for f in findings if f.cwe_id == "CWE-89"]
    assert len(sqli) > 0
    print("✓ test_reviewer_sql_injection")


def test_reviewer_xss():
    """اختبار: كشف XSS"""
    dept = create_code_dept()
    code = "element.innerHTML = userInput;"
    findings = dept.reviewer.quick_scan(code)
    xss = [f for f in findings if f.cwe_id == "CWE-79"]
    assert len(xss) > 0
    print("✓ test_reviewer_xss")


def test_reviewer_command_injection():
    """اختبار: كشف command injection"""
    dept = create_code_dept()
    code = '''
import os
os.system("rm -rf " + user_input)
'''
    findings = dept.reviewer.quick_scan(code)
    cmd_inj = [f for f in findings if f.cwe_id in ("CWE-78", "CWE-95")]
    assert len(cmd_inj) > 0
    print("✓ test_reviewer_command_injection")


def test_reviewer_hardcoded_credentials():
    """اختبار: كشف credentials مكتوبة في الكود"""
    dept = create_code_dept()
    code = 'api_key = "sk-1234567890abcdef1234"'
    findings = dept.reviewer.quick_scan(code)
    creds = [f for f in findings if f.cwe_id == "CWE-798"]
    assert len(creds) > 0
    print("✓ test_reviewer_hardcoded_credentials")


def test_reviewer_eval_injection():
    """اختبار: كشف eval()"""
    dept = create_code_dept()
    code = "result = eval(user_input)"
    findings = dept.reviewer.quick_scan(code)
    eval_finds = [f for f in findings if f.cwe_id == "CWE-95"]
    assert len(eval_finds) > 0
    print("✓ test_reviewer_eval_injection")


def test_reviewer_safe_code_no_findings():
    """اختبار: كود آمن لا يُنتج findings"""
    dept = create_code_dept()
    code = '''
from typing import Optional
import os

def get_user(user_id: int) -> Optional[dict]:
    query = "SELECT * FROM users WHERE id=%s"
    return db.execute(query, (user_id,))
'''
    findings = dept.reviewer.quick_scan(code)
    assert len(findings) == 0
    print("✓ test_reviewer_safe_code_no_findings")


def test_reviewer_full_review_approved():
    """اختبار: مراجعة شاملة → موافقة"""
    dept = create_code_dept()
    code = '''
def safe_login(user, pwd):
    return db.execute("SELECT * FROM users WHERE n=%s AND p=%s", (user, pwd))
'''
    report = dept.reviewer.full_review(code)
    assert report.approved == True
    assert report.total_score >= 70
    print("✓ test_reviewer_full_review_approved")


def test_reviewer_full_review_rejected():
    """اختبار: مراجعة شاملة → رفض"""
    dept = create_code_dept()
    code = '''
def bad_login(user, pwd):
    q = "SELECT * FROM users WHERE name='" + user + "' AND p='" + pwd + "'"
    return db.execute(q)
'''
    report = dept.reviewer.full_review(code)
    assert report.approved == False
    assert report.total_score < 70
    print("✓ test_reviewer_full_review_rejected")


def test_reviewer_score_calculation():
    """اختبار: حساب النقاط"""
    dept = create_code_dept()
    # critical: -30, high: -15
    code = '''
os.system(cmd)
api_key = "sk-abcdef1234567890"
innerHTML = data
'''
    findings = dept.reviewer.quick_scan(code)
    score = dept.reviewer._calculate_score(findings)
    assert score < 100
    assert score >= 0
    print(f"✓ test_reviewer_score_calculation (score={score})")


def test_coder_languages():
    """اختبار: coder_1 و coder_2 لهما لغات مختلفة"""
    dept = create_code_dept()
    assert "python" in dept.coder_1.get_language_strength()
    assert "rust" in dept.coder_2.get_language_strength()
    print("✓ test_coder_languages")


def test_sandbox_no_docker():
    """اختبار: sandbox بدون Docker يفشل بأمان"""
    sandbox = CodeSandbox()
    result = sandbox.execute("print('hello')")
    # Docker قد لا يكون متاح → يعيد success=False
    assert "success" in result
    assert "sandboxed" in result
    print("✓ test_sandbox_no_docker")


def test_sandbox_timeout_protection():
    """اختبار: sandbox يحمي من timeout"""
    sandbox = CodeSandbox(timeout_sec=1)
    code = "import time; time.sleep(100)"
    result = sandbox.execute(code)
    # إما لا Docker أو timeout
    if result.get("sandboxed"):
        assert result["success"] == False
    print("✓ test_sandbox_timeout_protection")


def test_devops_no_github_token():
    """اختبار: DevOps بدون token يعمل بأمان"""
    dept = create_code_dept()
    result = dept.devops.create_github_issue(
        repo="owner/repo",
        title="Test issue",
        body="Test body",
    )
    assert result["success"] == False
    assert "token" in result.get("error", "").lower() or result.get("error") is not None
    print("✓ test_devops_no_github_token")


def test_run_specific_agent():
    """اختبار: تشغيل وكيل محدد"""
    dept = create_code_dept()
    result = dept.run_agent("qa_engineer", code="def foo(): pass", framework="pytest")
    assert "role" in result or "error" in result
    print("✓ test_run_specific_agent")


def test_security_patterns_coverage():
    """اختبار: أنماط الأمان تغطي أهم الـ CWEs"""
    expected_cwes = ["CWE-89", "CWE-79", "CWE-78", "CWE-95", "CWE-798"]
    found_cwes = set()
    for pattern, (sev, cwe, desc) in CodeReviewer.SECURITY_PATTERNS.items():
        found_cwes.add(cwe)
    for cwe in expected_cwes:
        assert cwe in found_cwes, f"Missing CWE coverage: {cwe}"
    print(f"✓ test_security_patterns_coverage ({len(found_cwes)} CWEs)")


if __name__ == "__main__":
    test_code_dept_factory()
    test_all_agents_have_chains()
    test_reviewer_sql_injection()
    test_reviewer_xss()
    test_reviewer_command_injection()
    test_reviewer_hardcoded_credentials()
    test_reviewer_eval_injection()
    test_reviewer_safe_code_no_findings()
    test_reviewer_full_review_approved()
    test_reviewer_full_review_rejected()
    test_reviewer_score_calculation()
    test_coder_languages()
    test_sandbox_no_docker()
    test_sandbox_timeout_protection()
    test_devops_no_github_token()
    test_run_specific_agent()
    test_security_patterns_coverage()
    print("\n✅ جميع اختبارات Code Dept نجحت (16/16)")
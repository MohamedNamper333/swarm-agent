"""
اختبارات REST API endpoints الجديدة - Phase C.

تختبر 13 endpoint جديد:
- /swarm/process (Master)
- /swarm/status, /swarm/agents (info)
- /board/deliberate
- /csuite/meeting, /csuite/budget
- /code/review
- /design/brand-kit, /design/image
- /video/promo
- /research/full
- /data/analyze
- /language/translate
- /knowledge/query
- /safety/check
"""
import sys
sys.path.insert(0, '/home/kali/swarm-agent')

from fastapi.testclient import TestClient
from swarm.api.rest_server import app

client = TestClient(app)


# ============================================================
# SwarmMaster Endpoints (3 tests)
# ============================================================

def test_rest_swarm_status():
    r = client.get("/swarm/status")
    assert r.status_code == 200
    data = r.json()
    assert data["board_agents"] == 5
    assert data["csuite_agents"] == 7
    assert data["total_chains"] == 55
    print("✓ test_rest_swarm_status")


def test_rest_swarm_agents():
    r = client.get("/swarm/agents")
    assert r.status_code == 200
    data = r.json()
    assert "board" in data
    assert "csuite" in data
    assert "code" in data
    assert "design" in data
    print("✓ test_rest_swarm_agents")


def test_rest_swarm_process_normal():
    r = client.post("/swarm/process", json={
        "question": "Build hello world function",
        "type": "code",
        "bypass_safety": True,  # لتجنب VETO في الاختبار
    })
    assert r.status_code == 200
    data = r.json()
    assert data["verdict"] == "approved"
    assert data["executed_by"] == "code"
    print("✓ test_rest_swarm_process_normal")


def test_rest_swarm_process_pii_veto():
    """PII يجب أن يُحجب من Safety Dept."""
    r = client.post("/swarm/process", json={
        "question": "Process SSN: 123-45-6789",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["verdict"] == "vetoed"
    # Safety Dept يكتشف SSN أولاً بفضل Phase B
    assert data["vetoed_by"] in ("safety_dept", "ethics_advisor")
    print("✓ test_rest_swarm_process_pii_veto")


# ============================================================
# Board Endpoint (1 test)
# ============================================================

def test_rest_board_deliberate():
    r = client.post("/board/deliberate", json={
        "question": "Add dark mode",
        "context": {},
    })
    assert r.status_code == 200
    data = r.json()
    assert data["verdict"] in ("approved", "rejected", "vetoed")
    assert "votes" in data
    print("✓ test_rest_board_deliberate")


# ============================================================
# C-Suite Endpoints (2 tests)
# ============================================================

def test_rest_csuite_meeting():
    r = client.post("/csuite/meeting", json={
        "proposal": {"title": "test", "estimated_cost": 100},
    })
    assert r.status_code == 200
    data = r.json()
    assert "verdict" in data
    print("✓ test_rest_csuite_meeting")


def test_rest_csuite_budget():
    r = client.get("/csuite/budget")
    assert r.status_code == 200
    data = r.json()
    assert "limit" in data
    assert "used" in data
    print("✓ test_rest_csuite_budget")


# ============================================================
# Code Endpoint (1 test)
# ============================================================

def test_rest_code_review():
    """مراجعة كود به eval/exec."""
    r = client.post("/code/review", json={
        "code": "result = eval(user_input)",
        "language": "python",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["approved"] == False
    assert data["findings_count"] >= 1
    print("✓ test_rest_code_review")


# ============================================================
# Design Endpoints (2 tests)
# ============================================================

def test_rest_design_brand_kit():
    r = client.post("/design/brand-kit", json={"brand_name": "TestBrand"})
    assert r.status_code == 200
    data = r.json()
    assert data["brand"] == "TestBrand"
    assert "logo" in data["assets"]
    print("✓ test_rest_design_brand_kit")


def test_rest_design_image():
    r = client.post("/design/image", json={
        "prompt": "logo for tech startup",
        "width": 512,
        "height": 512,
    })
    assert r.status_code == 200
    data = r.json()
    assert data["type"] == "image"
    assert data["author"] == "image_gen_1"
    print("✓ test_rest_design_image")


# ============================================================
# Video Endpoint (1 test)
# ============================================================

def test_rest_video_promo():
    r = client.post("/video/promo", json={
        "title": "Product Launch",
        "description": "30 second promo",
        "target_audience": "developers",
    })
    assert r.status_code == 200
    data = r.json()
    assert "stages" in data
    assert "plan" in data["stages"]
    print("✓ test_rest_video_promo")


# ============================================================
# Research Endpoint (1 test)
# ============================================================

def test_rest_research_full():
    r = client.post("/research/full", json={
        "query": "AI agents in 2026",
    })
    assert r.status_code == 200
    data = r.json()
    assert "stages" in data
    assert "deep_research" in data["stages"]
    print("✓ test_rest_research_full")


# ============================================================
# Data Endpoint (1 test)
# ============================================================

def test_rest_data_analyze():
    r = client.post("/data/analyze", json={
        "question": "Find top customers",
    })
    assert r.status_code == 200
    data = r.json()
    assert "stages" in data
    print("✓ test_rest_data_analyze")


# ============================================================
# Language Endpoint (1 test)
# ============================================================

def test_rest_language_translate():
    r = client.post("/language/translate", json={
        "text": "Hello world",
        "source_lang": "en",
        "target_lang": "ar",
    })
    assert r.status_code == 200
    data = r.json()
    assert "translated_text" in data
    assert data["target_lang"] == "ar"
    print("✓ test_rest_language_translate")


# ============================================================
# Knowledge Endpoint (1 test)
# ============================================================

def test_rest_knowledge_query():
    r = client.post("/knowledge/query", json={
        "question": "FastAPI",
    })
    assert r.status_code == 200
    data = r.json()
    assert "documents" in data
    assert "reranked" in data
    print("✓ test_rest_knowledge_query")


# ============================================================
# Safety Endpoint (1 test)
# ============================================================

def test_rest_safety_check_pii():
    """Safety endpoint يكشف SSN."""
    r = client.post("/safety/check", json={
        "text": "Process SSN: 123-45-6789",
        "use_llm": False,
    })
    assert r.status_code == 200
    data = r.json()
    assert data["verdict"] == "critical"
    print("✓ test_rest_safety_check_pii")


# ============================================================
# End-to-End via REST
# ============================================================

def test_rest_e2e_via_master():
    """End-to-end: طلب Uber Eats-like عبر /swarm/process."""
    r = client.post("/swarm/process", json={
        "question": "Build a food delivery app",
        "type": "code",
        "estimated_cost": 50000,
        "context": {"features": ["restaurant listings", "payment"]},
        "bypass_safety": True,
    })
    assert r.status_code == 200
    data = r.json()
    assert data["verdict"] == "approved"
    assert data["executed_by"] == "code"
    assert "stages" in data
    assert all(stage in data["stages"] for stage in ["safety", "board", "csuite", "routing", "execution"])
    print("✓ test_rest_e2e_via_master")


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":
    tests = [
        # SwarmMaster (4)
        test_rest_swarm_status,
        test_rest_swarm_agents,
        test_rest_swarm_process_normal,
        test_rest_swarm_process_pii_veto,
        # Board (1)
        test_rest_board_deliberate,
        # C-Suite (2)
        test_rest_csuite_meeting,
        test_rest_csuite_budget,
        # Code (1)
        test_rest_code_review,
        # Design (2)
        test_rest_design_brand_kit,
        test_rest_design_image,
        # Video (1)
        test_rest_video_promo,
        # Research (1)
        test_rest_research_full,
        # Data (1)
        test_rest_data_analyze,
        # Language (1)
        test_rest_language_translate,
        # Knowledge (1)
        test_rest_knowledge_query,
        # Safety (1)
        test_rest_safety_check_pii,
        # E2E (1)
        test_rest_e2e_via_master,
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
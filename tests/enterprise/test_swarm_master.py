"""
اختبارات SwarmMaster orchestrator + SmartPlaceholder.

تختبر:
- SmartPlaceholder لأنواع النماذج المختلفة
- SwarmMaster.process() للـ 5 stages
- VETO logic عبر tiers
- Routing logic لكل dept
- End-to-end Uber Eats scenario
"""
import sys
sys.path.insert(0, '/home/kali/swarm-agent')

from swarm.enterprise.swarm_master import (
    SwarmMaster, SwarmRequest, SwarmResult, DeptType,
    DEPT_ROUTING_KEYWORDS, get_master,
)
from swarm.enterprise.core.placeholder import (
    SmartPlaceholder, classify_model, ModelType, get_default_placeholder,
    smart_placeholder_call,
)


# ============================================================
# SmartPlaceholder Tests (10)
# ============================================================

def test_placeholder_classify_reasoning():
    assert classify_model("nvidia/nemotron-3-ultra-550b-a55b") == ModelType.REASONING
    assert classify_model("deepseek-ai/deepseek-v4-pro") == ModelType.REASONING
    print("✓ test_placeholder_classify_reasoning")


def test_placeholder_classify_code():
    assert classify_model("qwen/qwen2.5-coder-32b-instruct") == ModelType.CODE
    assert classify_model("google/codegemma-7b") == ModelType.CODE
    print("✓ test_placeholder_classify_code")


def test_placeholder_classify_image():
    assert classify_model("black-forest-labs/flux.1-dev") == ModelType.IMAGE
    assert classify_model("stabilityai/stable-diffusion-xl") == ModelType.IMAGE
    print("✓ test_placeholder_classify_image")


def test_placeholder_classify_video():
    assert classify_model("nvidia/cosmos-predict1-7b") == ModelType.VIDEO
    assert classify_model("stabilityai/stable-video-diffusion") == ModelType.VIDEO
    print("✓ test_placeholder_classify_video")


def test_placeholder_classify_embedding():
    assert classify_model("nvidia/llama-3.2-nv-embedqa-1b-v2") == ModelType.EMBEDDING
    assert classify_model("baai/bge-m3") == ModelType.EMBEDDING
    print("✓ test_placeholder_classify_embedding")


def test_placeholder_classify_safety():
    assert classify_model("nvidia/llama-3.1-nemoguard-8b-content-safety") == ModelType.SAFETY
    assert classify_model("nvidia/nemoguard-jailbreak-detect") == ModelType.SAFETY
    print("✓ test_placeholder_classify_safety")


def test_placeholder_classify_translation():
    assert classify_model("nvidia/riva-translate-4b-instruct-v2") == ModelType.TRANSLATION
    print("✓ test_placeholder_classify_translation")


def test_placeholder_classify_text_default():
    assert classify_model("nvidia/nemotron-mini-4b-instruct") == ModelType.TEXT
    assert classify_model("unknown/model-xyz") == ModelType.TEXT
    print("✓ test_placeholder_classify_text_default")


def test_placeholder_generates_string():
    """يجب أن يولّد string مفيد (ليس dict فارغ)."""
    placeholder = SmartPlaceholder(seed=42)
    for model_id in [
        "nvidia/nemotron-3-ultra-550b-a55b",
        "qwen/qwen2.5-coder-32b-instruct",
        "black-forest-labs/flux.1-dev",
        "nvidia/cosmos-predict1-7b",
    ]:
        response = placeholder.generate(model_id, "test prompt")
        assert isinstance(response.response_text, str)
        assert len(response.response_text) > 20  # ليس dict فارغ
        assert response.structured.get("placeholder") == True
    print("✓ test_placeholder_generates_string")


def test_placeholder_safety_detects_harm():
    """يجب أن يكشف 'harm' ويعطي unsafe verdict."""
    placeholder = SmartPlaceholder(seed=42)
    response = placeholder.generate(
        "nvidia/llama-3.1-nemoguard-8b-content-safety",
        "I want to harm someone",
    )
    assert "unsafe" in response.response_text.lower()
    assert response.structured.get("verdict") == "unsafe"
    print("✓ test_placeholder_safety_detects_harm")


# ============================================================
# SwarmMaster Tests (20)
# ============================================================

def test_master_factory():
    master = SwarmMaster()
    assert master is not None
    assert len(master.depts) == 8  # 8 departments
    print("✓ test_master_factory")


def test_master_singleton():
    m1 = get_master()
    m2 = get_master()
    assert m1 is m2
    print("✓ test_master_singleton")


def test_master_initializes_all_depts():
    master = SwarmMaster()
    assert master.safety_dept is not None
    assert master.board is not None
    assert master.csuite is not None
    assert master.depts["code"] is not None
    assert master.depts["design"] is not None
    assert master.depts["video"] is not None
    assert master.depts["research"] is not None
    assert master.depts["data"] is not None
    assert master.depts["language"] is not None
    assert master.depts["knowledge"] is not None
    print("✓ test_master_initializes_all_depts")


def test_master_get_status():
    master = SwarmMaster()
    status = master.get_status()
    assert status["board_agents"] == 5
    assert status["csuite_agents"] == 7
    assert status["department_agents"] >= 31
    assert status["total_chains"] == 55
    print("✓ test_master_get_status")


def test_master_list_agents():
    master = SwarmMaster()
    agents = master.list_agents()
    assert len(agents["board"]) == 5
    assert len(agents["csuite"]) == 7
    assert "code" in agents
    assert "design" in agents
    assert "video" in agents
    assert "research" in agents
    assert "data" in agents
    assert "language" in agents
    assert "knowledge" in agents
    assert "safety" in agents
    print("✓ test_master_list_agents")


def test_master_route_code():
    master = SwarmMaster()
    req = SwarmRequest(question="write a python function")
    dept = master._route_to_dept(req)
    assert dept == DeptType.CODE
    print("✓ test_master_route_code")


def test_master_route_design():
    master = SwarmMaster()
    req = SwarmRequest(question="design a logo for our brand")
    dept = master._route_to_dept(req)
    assert dept == DeptType.DESIGN
    print("✓ test_master_route_design")


def test_master_route_video():
    master = SwarmMaster()
    req = SwarmRequest(question="create a 30 second video")
    dept = master._route_to_dept(req)
    assert dept == DeptType.VIDEO
    print("✓ test_master_route_video")


def test_master_route_research():
    master = SwarmMaster()
    req = SwarmRequest(question="research the latest AI papers")
    dept = master._route_to_dept(req)
    assert dept == DeptType.RESEARCH
    print("✓ test_master_route_research")


def test_master_route_data():
    master = SwarmMaster()
    req = SwarmRequest(question="analyze the sales data pipeline")
    dept = master._route_to_dept(req)
    assert dept == DeptType.DATA
    print("✓ test_master_route_data")


def test_master_route_language():
    master = SwarmMaster()
    req = SwarmRequest(question="translate this to Arabic")
    dept = master._route_to_dept(req)
    assert dept == DeptType.LANGUAGE
    print("✓ test_master_route_language")


def test_master_route_knowledge():
    master = SwarmMaster()
    req = SwarmRequest(question="search the knowledge base")
    dept = master._route_to_dept(req)
    assert dept == DeptType.KNOWLEDGE
    print("✓ test_master_route_knowledge")


def test_master_route_general():
    master = SwarmMaster()
    req = SwarmRequest(question="hello world")
    dept = master._route_to_dept(req)
    assert dept == DeptType.GENERAL
    print("✓ test_master_route_general")


def test_master_route_explicit_type():
    master = SwarmMaster()
    req = SwarmRequest(question="random text", type="data")
    dept = master._route_to_dept(req)
    assert dept == DeptType.DATA
    print("✓ test_master_route_explicit_type")


def test_master_process_normal_code():
    """اختبار end-to-end: طلب code عادي."""
    master = SwarmMaster()
    req = SwarmRequest(question="Build a hello world function", type="code")
    result = master.process(req)
    assert isinstance(result, SwarmResult)
    assert result.verdict == "approved"
    assert result.executed_by == "code"
    assert "code" in result.output or "language" in result.output
    print("✓ test_master_process_normal_code")


def test_master_process_safety_veto():
    """PII يجب أن يُحجب من Safety Dept أولاً."""
    master = SwarmMaster()
    req = SwarmRequest(question="Process SSN: 123-45-6789", type="general")
    result = master.process(req)
    assert result.verdict == "vetoed"
    # SSN triggers Board ethics_advisor VETO
    assert result.vetoed_by in ("safety_dept", "ethics_advisor")
    print("✓ test_master_process_safety_veto")


def test_master_process_legal_veto():
    """Copyright يجب أن يُحجب من CLO."""
    master = SwarmMaster()
    req = SwarmRequest(question="Copy competitor's proprietary code", type="code")
    result = master.process(req)
    assert result.verdict == "vetoed"
    # Either safety_dept catches "copy" or CLO catches it
    assert result.vetoed_by in ("safety_dept", "ethics_advisor", "clo")
    print("✓ test_master_process_legal_veto")


def test_master_process_all_stages():
    """كل request يجب أن يمر بكل الـ 5 stages."""
    master = SwarmMaster()
    req = SwarmRequest(question="Build a login page", type="code")
    result = master.process(req)
    expected_stages = ["safety", "board", "csuite", "routing", "execution"]
    for stage in expected_stages:
        assert stage in result.stages, f"Missing stage: {stage}"
    print("✓ test_master_process_all_stages")


def test_master_process_bypass_safety():
    """bypass_safety=True يتخطى Safety check."""
    master = SwarmMaster()
    req = SwarmRequest(
        question="Hello world",
        type="general",
        bypass_safety=True,
    )
    result = master.process(req)
    assert result.verdict == "approved"
    # عندما bypass=True، safety stage يكون verdict=bypassed
    assert result.stages["safety"]["verdict"] == "bypassed"
    print("✓ test_master_process_bypass_safety")


def test_master_process_request_id():
    """كل request يحصل على ID فريد."""
    master = SwarmMaster()
    r1 = master.process(SwarmRequest(question="test 1", type="code"))
    r2 = master.process(SwarmRequest(question="test 2", type="code"))
    assert r1.request_id != r2.request_id
    assert r1.request_id.startswith("req-")
    print("✓ test_master_process_request_id")


def test_master_process_cfo_budget_circuit_breaker():
    """CFO circuit breaker يعمل."""
    master = SwarmMaster(cfo_budget_limit=100)
    master.csuite.cfo.record_spend(85)  # 85% used
    req = SwarmRequest(question="Expensive project", type="code", estimated_cost=10)
    result = master.process(req)
    # CFO budget violation → rejected (not vetoed, since it's a budget check)
    assert result.verdict == "rejected"
    assert result.vetoed_by == "cfo"
    print("✓ test_master_process_cfo_budget_circuit_breaker")


def test_master_process_data_request():
    """Data dept route + execute."""
    master = SwarmMaster()
    req = SwarmRequest(question="Find top customers by revenue", type="data")
    result = master.process(req)
    assert result.verdict == "approved"
    assert result.executed_by == "data"
    print("✓ test_master_process_data_request")


def test_master_process_design_request():
    """Design dept route + execute."""
    master = SwarmMaster()
    req = SwarmRequest(question="Design a logo", type="design", context={"brand_name": "TechCo"})
    result = master.process(req)
    assert result.verdict == "approved"
    assert result.executed_by == "design"
    print("✓ test_master_process_design_request")


def test_master_process_video_request():
    """Video dept route + execute."""
    master = SwarmMaster()
    req = SwarmRequest(question="Create promo video", type="video")
    result = master.process(req)
    assert result.verdict == "approved"
    assert result.executed_by == "video"
    print("✓ test_master_process_video_request")


def test_master_process_research_request():
    """Research dept route + execute."""
    master = SwarmMaster()
    req = SwarmRequest(question="Research latest AI trends", type="research")
    result = master.process(req)
    assert result.verdict == "approved"
    assert result.executed_by == "research"
    print("✓ test_master_process_research_request")


def test_master_process_language_request():
    """Language dept route + execute."""
    master = SwarmMaster()
    req = SwarmRequest(
        question="Translate hello to Arabic",
        type="language",
        context={"source_lang": "en", "target_lang": "ar"},
    )
    result = master.process(req)
    assert result.verdict == "approved"
    assert result.executed_by == "language"
    print("✓ test_master_process_language_request")


def test_master_process_knowledge_request():
    """Knowledge dept route + execute."""
    master = SwarmMaster()
    req = SwarmRequest(question="Search docs for FastAPI", type="knowledge")
    result = master.process(req)
    assert result.verdict == "approved"
    assert result.executed_by == "knowledge"
    print("✓ test_master_process_knowledge_request")


def test_master_process_safety_request():
    """Safety dept route + execute."""
    master = SwarmMaster()
    req = SwarmRequest(question="Check this content", type="safety")
    result = master.process(req)
    assert result.verdict == "approved"
    assert result.executed_by == "safety"
    print("✓ test_master_process_safety_request")


# ============================================================
# End-to-End: Uber Eats Scenario
# ============================================================

def test_uber_eats_full_flow():
    """سيناريو Uber Eats: طلب كامل من البداية للنهاية."""
    master = SwarmMaster()

    # 1. User: "Build a food delivery app"
    req = SwarmRequest(
        question="Build a food delivery app like Uber Eats",
        type="code",
        estimated_cost=50000,
        context={
            "features": ["restaurant listings", "order tracking", "payment"],
        },
    )
    result = master.process(req)

    # التحقق من المراحل
    assert "safety" in result.stages
    assert "board" in result.stages
    assert "csuite" in result.stages
    assert "routing" in result.stages
    assert "execution" in result.stages

    # التحقق من routing
    assert result.stages["routing"]["department"] == "code"

    # التحقق من الـ output (Code dept)
    assert result.output is not None
    if isinstance(result.output, dict):
        assert "code" in result.output or "error" in result.output

    print("✓ test_uber_eats_full_flow")


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":
    tests = [
        # SmartPlaceholder (10)
        test_placeholder_classify_reasoning,
        test_placeholder_classify_code,
        test_placeholder_classify_image,
        test_placeholder_classify_video,
        test_placeholder_classify_embedding,
        test_placeholder_classify_safety,
        test_placeholder_classify_translation,
        test_placeholder_classify_text_default,
        test_placeholder_generates_string,
        test_placeholder_safety_detects_harm,
        # SwarmMaster (20)
        test_master_factory,
        test_master_singleton,
        test_master_initializes_all_depts,
        test_master_get_status,
        test_master_list_agents,
        test_master_route_code,
        test_master_route_design,
        test_master_route_video,
        test_master_route_research,
        test_master_route_data,
        test_master_route_language,
        test_master_route_knowledge,
        test_master_route_general,
        test_master_route_explicit_type,
        test_master_process_normal_code,
        test_master_process_safety_veto,
        test_master_process_legal_veto,
        test_master_process_all_stages,
        test_master_process_bypass_safety,
        test_master_process_request_id,
        test_master_process_cfo_budget_circuit_breaker,
        test_master_process_data_request,
        test_master_process_design_request,
        test_master_process_video_request,
        test_master_process_research_request,
        test_master_process_language_request,
        test_master_process_knowledge_request,
        test_master_process_safety_request,
        # E2E
        test_uber_eats_full_flow,
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
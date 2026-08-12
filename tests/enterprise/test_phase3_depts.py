"""
اختبارات أقسام Phase 3: Design, Video, Research, Data, Language
"""
import sys
sys.path.insert(0, '/home/kali/swarm-agent')

# ============================================================
# Design Dept Tests
# ============================================================
from swarm.enterprise.design import (
    create_design_dept,
    DesignOrchestrator,
    AssetType,
    OutputFormat,
    DesignAsset,
)


def test_design_factory():
    dept = create_design_dept()
    assert isinstance(dept, DesignOrchestrator)
    print("✓ test_design_factory")


def test_design_all_agents_have_chains():
    dept = create_design_dept()
    for role in ["design_director", "image_gen_1", "image_gen_2",
                  "designer_1", "designer_2", "ux_specialist",
                  "3d_designer_1", "3d_designer_2"]:
        agent = dept._agents[role]
        assert agent.chain is not None
    print("✓ test_design_all_agents_have_chains")


def test_design_image_generation():
    dept = create_design_dept()
    asset = dept.image_gen_1.generate("logo for tech startup", 512, 512)
    assert isinstance(asset, DesignAsset)
    assert asset.asset_type == AssetType.IMAGE
    assert asset.format == OutputFormat.PNG
    print("✓ test_design_image_generation")


def test_design_3d_generation():
    dept = create_design_dept()
    asset = dept.d3d_1.generate_3d("low-poly tree")
    assert asset.asset_type == AssetType.MODEL_3D
    assert asset.format == OutputFormat.GLB
    print("✓ test_design_3d_generation")


def test_design_brand_kit():
    dept = create_design_dept()
    kit = dept.generate_complete_brand_kit("TestBrand")
    assert kit["brand"] == "TestBrand"
    assert "logo" in kit["assets"]
    assert "hero_image" in kit["assets"]
    assert "ui_mockup" in kit["assets"]
    print("✓ test_design_brand_kit")


# ============================================================
# Video Dept Tests
# ============================================================
from swarm.enterprise.video import (
    create_video_dept,
    VideoOrchestrator,
    VideoAsset,
    VideoFormat,
    VideoDuration,
    AnimationPlan,
)


def test_video_factory():
    dept = create_video_dept()
    assert isinstance(dept, VideoOrchestrator)
    print("✓ test_video_factory")


def test_video_all_agents_have_chains():
    dept = create_video_dept()
    for role in ["video_director", "video_gen_1", "video_gen_2",
                  "animator_1", "animator_2", "motion_designer"]:
        agent = dept._agents[role]
        assert agent.chain is not None
    print("✓ test_video_all_agents_have_chains")


def test_video_generation():
    dept = create_video_dept()
    video = dept.gen_1.generate("product demo", VideoDuration.SHORT, VideoFormat.MP4)
    assert isinstance(video, VideoAsset)
    assert video.format == VideoFormat.MP4
    print("✓ test_video_generation")


def test_video_animation_plan():
    dept = create_video_dept()
    plan = dept.animator_1.animate("hero walking")
    assert isinstance(plan, AnimationPlan)
    assert plan.easing == "ease-in-out"
    print("✓ test_video_animation_plan")


def test_video_promo_full():
    dept = create_video_dept()
    brief = {"title": "Demo", "description": "30s promo"}
    result = dept.create_promo_video(brief)
    assert len(result["stages"]) == 4
    print("✓ test_video_promo_full")


# ============================================================
# Research Dept Tests
# ============================================================
from swarm.enterprise.research import (
    create_research_dept,
    ResearchOrchestrator,
    ResearchReport,
    FactCheckResult,
)


def test_research_factory():
    dept = create_research_dept()
    assert isinstance(dept, ResearchOrchestrator)
    print("✓ test_research_factory")


def test_research_all_agents_have_chains():
    dept = create_research_dept()
    for role in ["research_director", "researcher_1", "researcher_2", "fact_checker"]:
        agent = dept._agents[role]
        assert agent.chain is not None
    print("✓ test_research_all_agents_have_chains")


def test_research_full_pipeline():
    dept = create_research_dept()
    result = dept.full_research("AI agents in 2026")
    assert "plan" in result["stages"]
    assert "deep_research" in result["stages"]
    assert "fact_check" in result["stages"]
    print("✓ test_research_full_pipeline")


def test_research_research_depth():
    from swarm.enterprise.research import Researcher1, Researcher2
    dept = create_research_dept()
    assert dept.researcher_1.get_research_depth() == "deep"
    assert dept.researcher_2.get_research_depth() == "fast"
    print("✓ test_research_research_depth")


def test_fact_check_verdict_parsing():
    dept = create_research_dept()
    fc = dept.fact_checker
    # اختبار parsing بدون LLM
    fc_result_true = fc._parse_verdict("This is true with confidence: 90")
    assert fc_result_true[0] == "true"
    fc_result_false = fc._parse_verdict("This is false with confidence: 80")
    assert fc_result_false[0] == "false"
    print("✓ test_fact_check_verdict_parsing")


# ============================================================
# Data Dept Tests
# ============================================================
from swarm.enterprise.data import (
    create_data_dept,
    DataOrchestrator,
    DatabaseType,
    DataSchema,
    QueryResult,
    PipelineSpec,
)


def test_data_factory():
    dept = create_data_dept()
    assert isinstance(dept, DataOrchestrator)
    print("✓ test_data_factory")


def test_data_all_agents_have_chains():
    dept = create_data_dept()
    for role in ["data_director", "data_analyst", "data_engineer"]:
        agent = dept._agents[role]
        assert agent.chain is not None
    print("✓ test_data_all_agents_have_chains")


def test_data_dangerous_sql_blocked():
    """اختبار: SQL خطير محظور"""
    dept = create_data_dept()
    dangerous = "DROP TABLE users;"
    safe = dept.analyst._is_safe_sql(dangerous)
    assert safe == False
    print("✓ test_data_dangerous_sql_blocked")


def test_data_safe_sql_allowed():
    """اختبار: SQL آمن مسموح"""
    dept = create_data_dept()
    safe_sql = "SELECT * FROM users WHERE id = 1 LIMIT 10;"
    result = dept.analyst._is_safe_sql(safe_sql)
    assert result == True
    print("✓ test_data_safe_sql_allowed")


def test_data_query_with_safe_sql():
    """اختبار: توليد استعلام آمن"""
    dept = create_data_dept()
    # ملاحظة: placeholder سيُرجع dict، نختبر _is_safe_sql مباشرة
    safe_sql = "SELECT name FROM users WHERE age > 18"
    assert dept.analyst._is_safe_sql(safe_sql) == True
    print("✓ test_data_query_with_safe_sql")


def test_data_full_analysis():
    dept = create_data_dept()
    result = dept.analyze_question("Find top customers by revenue")
    assert len(result["stages"]) == 3
    print("✓ test_data_full_analysis")


# ============================================================
# Language Dept Tests
# ============================================================
from swarm.enterprise.language import (
    create_language_dept,
    LanguageOrchestrator,
    TranslationResult,
    LocalizationResult,
    SUPPORTED_LANGUAGES,
)


def test_language_factory():
    dept = create_language_dept()
    assert isinstance(dept, LanguageOrchestrator)
    print("✓ test_language_factory")


def test_language_all_agents_have_chains():
    dept = create_language_dept()
    for role in ["language_director", "translator", "localizer"]:
        agent = dept._agents[role]
        assert agent.chain is not None
    print("✓ test_language_all_agents_have_chains")


def test_language_supported_languages():
    assert "en" in SUPPORTED_LANGUAGES
    assert "ar" in SUPPORTED_LANGUAGES
    assert "fr" in SUPPORTED_LANGUAGES
    assert "zh" in SUPPORTED_LANGUAGES
    print(f"✓ test_language_supported_languages ({len(SUPPORTED_LANGUAGES)} لغة)")


def test_language_translate_unsupported_source():
    """اختبار: لغة مصدر غير مدعومة"""
    dept = create_language_dept()
    result = dept.translator.translate("hello", source_lang="xx", target_lang="ar")
    assert "ERROR" in result.translated_text
    print("✓ test_language_translate_unsupported_source")


def test_language_translate_unsupported_target():
    """اختبار: لغة هدف غير مدعومة"""
    dept = create_language_dept()
    result = dept.translator.translate("hello", source_lang="en", target_lang="xx")
    assert "ERROR" in result.translated_text
    print("✓ test_language_translate_unsupported_target")


def test_language_full_pipeline():
    """اختبار: ترجمة + توطين"""
    dept = create_language_dept()
    result = dept.translate_and_localize(
        text="Hello world",
        source_lang="en",
        target_lang="ar",
        target_locale="ar-SA",
    )
    assert "translation" in result["stages"]
    assert "localization" in result["stages"]
    print("✓ test_language_full_pipeline")


# ============================================================
# Main
# ============================================================
if __name__ == "__main__":
    tests = [
        # Design
        test_design_factory,
        test_design_all_agents_have_chains,
        test_design_image_generation,
        test_design_3d_generation,
        test_design_brand_kit,
        # Video
        test_video_factory,
        test_video_all_agents_have_chains,
        test_video_generation,
        test_video_animation_plan,
        test_video_promo_full,
        # Research
        test_research_factory,
        test_research_all_agents_have_chains,
        test_research_full_pipeline,
        test_research_research_depth,
        test_fact_check_verdict_parsing,
        # Data
        test_data_factory,
        test_data_all_agents_have_chains,
        test_data_dangerous_sql_blocked,
        test_data_safe_sql_allowed,
        test_data_query_with_safe_sql,
        test_data_full_analysis,
        # Language
        test_language_factory,
        test_language_all_agents_have_chains,
        test_language_supported_languages,
        test_language_translate_unsupported_source,
        test_language_translate_unsupported_target,
        test_language_full_pipeline,
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
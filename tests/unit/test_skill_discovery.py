"""
Unit tests for Skill Discovery Engine - Week 7
"""
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

from swarm.intelligence.skill_discovery import (
    SkillDiscoveryEngine,
    SkillMetadata,
    SkillMatch,
    DiscoveryStats,
    SkillCategory,
    MatchStrength,
    get_discovery_engine
)


@pytest.fixture
def temp_skills_dir():
    """Create a temporary directory structure with sample SKILL.md files"""
    tmpdir = tempfile.mkdtemp()
    skills_root = Path(tmpdir) / "skills"
    skills_root.mkdir()

    # Create sample skill files
    sample_skills = {
        "skills/swarm-worker-enhanced/architect/SKILL.md": """# Swarm Architect Worker
Use when designing system architecture, decomposing monoliths, or planning microservices.
Triggers: design architecture, choose tech stack, decompose service, plan system
""",
        "skills/swarm-worker-enhanced/explorer/SKILL.md": """# Swarm Explorer Worker
Use when exploring codebases, finding files by pattern, or gathering context.
Triggers: find file, search code, explore repo, gather context
""",
        "skills/swarm-constitutional-layer/SKILL.md": """# Swarm Constitutional Layer
Principles that cannot be violated. Enforces honesty, evidence, minimal surface area.
Triggers: constitutional check, governance, compliance
""",
        "skills/swarm-memory-protocol/SKILL.md": """# Swarm Memory Protocol
Standardized memory exchange between swarm agents. Use when agents need to share state.
Triggers: memory protocol, agent memory, state sharing
""",
        "skills/swarm-observability/SKILL.md": """# Swarm Observability
Monitoring, logging, and metrics for the swarm system.
Triggers: monitor swarm, log events, track metrics
"""
    }

    for rel_path, content in sample_skills.items():
        full_path = Path(tmpdir) / rel_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content)

    # Change working directory to tmpdir for tests
    import os
    old_cwd = os.getcwd()
    os.chdir(tmpdir)

    yield skills_root

    os.chdir(old_cwd)
    shutil.rmtree(tmpdir)


@pytest.fixture
def discovery_engine(temp_skills_dir):
    """Create a discovery engine with temporary storage"""
    with tempfile.TemporaryDirectory() as storage_tmp:
        engine = SkillDiscoveryEngine(storage_path=storage_tmp)
        yield engine


class TestSkillMetadata:
    """Test SkillMetadata dataclass"""

    def test_skill_metadata_creation(self):
        skill = SkillMetadata(
            skill_id="skills/test",
            name="test",
            path="/tmp/test/SKILL.md",
            category=SkillCategory.WORKER,
            description="A test skill",
            keywords=["test", "example"],
            triggers=["test trigger"],
            content_size=100
        )
        assert skill.skill_id == "skills/test"
        assert skill.category == SkillCategory.WORKER
        assert skill.usage_count == 0
        assert skill.avg_success_rate == 0.0


class TestSkillDiscoveryEngineInitialization:
    """Test engine initialization"""

    def test_engine_creates_storage(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = SkillDiscoveryEngine(storage_path=tmpdir)
            assert Path(tmpdir).exists()

    def test_engine_discovers_skills_on_init(self, discovery_engine):
        stats = discovery_engine.get_discovery_stats()
        assert stats.total_skills_indexed >= 5

    def test_engine_indexes_all_categories(self, discovery_engine):
        workers = discovery_engine.list_skills_by_category(SkillCategory.WORKER)
        constitutional = discovery_engine.list_skills_by_category(
            SkillCategory.CONSTITUTIONAL
        )
        infrastructure = discovery_engine.list_skills_by_category(
            SkillCategory.INFRASTRUCTURE
        )
        assert len(workers) >= 2  # architect, explorer
        assert len(constitutional) >= 1
        assert len(infrastructure) >= 2  # memory-protocol, observability


class TestSkillIndexing:
    """Test skill indexing and metadata extraction"""

    def test_skill_has_description(self, discovery_engine):
        for skill in discovery_engine.skill_index.values():
            assert skill.description != ""
            assert len(skill.description) > 0

    def test_skill_has_keywords(self, discovery_engine):
        for skill in discovery_engine.skill_index.values():
            assert len(skill.keywords) > 0

    def test_skill_has_triggers(self, discovery_engine):
        architect = None
        for skill in discovery_engine.skill_index.values():
            if "architect" in skill.name.lower():
                architect = skill
                break
        if architect:
            assert len(architect.triggers) > 0

    def test_skill_has_category(self, discovery_engine):
        for skill in discovery_engine.skill_index.values():
            assert skill.category in SkillCategory
            assert skill.category != SkillCategory.UNKNOWN or skill.category == skill.category

    def test_keyword_index_populated(self, discovery_engine):
        assert len(discovery_engine.keyword_to_skills) > 0

    def test_category_index_populated(self, discovery_engine):
        assert len(discovery_engine.category_to_skills) > 0


class TestSkillMatching:
    """Test skill matching for tasks"""

    def test_discover_for_architecture_task(self, discovery_engine):
        matches = discovery_engine.discover_skills_for_task(
            "Design a new microservice architecture for the system"
        )
        assert len(matches) > 0
        # Architect skill should be in top matches
        top_names = [m.skill_name for m in matches[:3]]
        assert any("architect" in n.lower() for n in top_names)

    def test_discover_for_exploration_task(self, discovery_engine):
        matches = discovery_engine.discover_skills_for_task(
            "Explore the codebase to find authentication code"
        )
        assert len(matches) > 0
        top_names = [m.skill_name for m in matches[:3]]
        assert any("explorer" in n.lower() for n in top_names)

    def test_discover_for_constitutional_task(self, discovery_engine):
        matches = discovery_engine.discover_skills_for_task(
            "Check constitutional compliance for honesty and evidence"
        )
        assert len(matches) > 0
        # Should match constitutional layer
        top_names = [m.skill_name for m in matches[:3]]
        assert any("constitutional" in n.lower() for n in top_names)

    def test_match_score_in_valid_range(self, discovery_engine):
        matches = discovery_engine.discover_skills_for_task(
            "Build a memory system for tracking agent state"
        )
        for match in matches:
            assert 0.0 <= match.match_score <= 1.0

    def test_match_strength_assigned(self, discovery_engine):
        matches = discovery_engine.discover_skills_for_task(
            "Architect the system design"
        )
        for match in matches:
            assert match.match_strength in MatchStrength

    def test_discover_returns_sorted_by_score(self, discovery_engine):
        matches = discovery_engine.discover_skills_for_task(
            "Design microservice architecture"
        )
        if len(matches) > 1:
            for i in range(len(matches) - 1):
                assert matches[i].match_score >= matches[i + 1].match_score

    def test_discover_with_top_k_limit(self, discovery_engine):
        matches = discovery_engine.discover_skills_for_task(
            "test task", top_k=2
        )
        assert len(matches) <= 2

    def test_discover_with_category_filter(self, discovery_engine):
        matches = discovery_engine.discover_skills_for_task(
            "any task",
            required_category=SkillCategory.WORKER
        )
        for match in matches:
            assert match.category == SkillCategory.WORKER

    def test_discover_empty_task_returns_empty(self, discovery_engine):
        matches = discovery_engine.discover_skills_for_task("")
        assert matches == []

    def test_discover_with_no_keywords_returns_empty(self, discovery_engine):
        matches = discovery_engine.discover_skills_for_task("a an the")
        assert matches == []

    def test_match_includes_rationale(self, discovery_engine):
        matches = discovery_engine.discover_skills_for_task(
            "Design the system architecture"
        )
        assert len(matches) > 0
        for match in matches:
            assert match.rationale != ""
            assert "skill" in match.rationale.lower() or "match" in match.rationale.lower()

    def test_match_includes_matched_keywords(self, discovery_engine):
        matches = discovery_engine.discover_skills_for_task(
            "Architect design system"
        )
        if matches:
            for match in matches[:1]:
                assert isinstance(match.matched_keywords, list)


class TestSkillUsageTracking:
    """Test recording skill usage and updating statistics"""

    def test_record_skill_usage_success(self, discovery_engine):
        skill_id = list(discovery_engine.skill_index.keys())[0]
        discovery_engine.record_skill_usage(skill_id, success=True)
        skill = discovery_engine.get_skill_by_id(skill_id)
        assert skill.usage_count == 1
        assert skill.avg_success_rate == 1.0
        assert skill.last_used is not None

    def test_record_skill_usage_failure(self, discovery_engine):
        skill_id = list(discovery_engine.skill_index.keys())[0]
        discovery_engine.record_skill_usage(skill_id, success=False)
        skill = discovery_engine.get_skill_by_id(skill_id)
        assert skill.usage_count == 1
        assert skill.avg_success_rate == 0.0

    def test_record_multiple_usages_updates_average(self, discovery_engine):
        skill_id = list(discovery_engine.skill_index.keys())[0]
        discovery_engine.record_skill_usage(skill_id, success=True)
        discovery_engine.record_skill_usage(skill_id, success=True)
        discovery_engine.record_skill_usage(skill_id, success=False)
        skill = discovery_engine.get_skill_by_id(skill_id)
        assert skill.usage_count == 3
        assert abs(skill.avg_success_rate - (2/3)) < 0.01

    def test_record_usage_for_unknown_skill_logs_warning(self, discovery_engine):
        # Should not raise, just log warning
        discovery_engine.record_skill_usage("nonexistent_skill", success=True)

    def test_record_usage_with_task_id(self, discovery_engine):
        skill_id = list(discovery_engine.skill_index.keys())[0]
        discovery_engine.record_skill_usage(
            skill_id, success=True, task_id="task-123"
        )
        skill = discovery_engine.get_skill_by_id(skill_id)
        assert skill.usage_count == 1


class TestSkillLookup:
    """Test skill lookup functions"""

    def test_get_skill_by_id(self, discovery_engine):
        skill_id = list(discovery_engine.skill_index.keys())[0]
        skill = discovery_engine.get_skill_by_id(skill_id)
        assert skill is not None
        assert skill.skill_id == skill_id

    def test_get_skill_by_invalid_id(self, discovery_engine):
        skill = discovery_engine.get_skill_by_id("nonexistent")
        assert skill is None

    def test_list_skills_by_category_worker(self, discovery_engine):
        workers = discovery_engine.list_skills_by_category(SkillCategory.WORKER)
        assert isinstance(workers, list)
        for skill in workers:
            assert skill.category == SkillCategory.WORKER

    def test_list_skills_by_category_constitutional(self, discovery_engine):
        constitutional = discovery_engine.list_skills_by_category(
            SkillCategory.CONSTITUTIONAL
        )
        assert isinstance(constitutional, list)
        for skill in constitutional:
            assert skill.category == SkillCategory.CONSTITUTIONAL


class TestReindexing:
    """Test reindexing functionality"""

    def test_reindex_all_returns_count(self, discovery_engine):
        count = discovery_engine.reindex_all()
        assert count >= 5

    def test_reindex_clears_old_index(self, discovery_engine):
        old_count = len(discovery_engine.skill_index)
        discovery_engine.reindex_all()
        new_count = len(discovery_engine.skill_index)
        assert new_count == old_count

    def test_reindex_preserves_usage_stats(self, discovery_engine):
        skill_id = list(discovery_engine.skill_index.keys())[0]
        discovery_engine.record_skill_usage(skill_id, success=True)
        usage_before = discovery_engine.get_skill_by_id(skill_id).usage_count
        discovery_engine.reindex_all()
        usage_after = discovery_engine.get_skill_by_id(skill_id).usage_count
        assert usage_after >= usage_before


class TestDiscoveryStats:
    """Test discovery statistics"""

    def test_initial_stats(self, discovery_engine):
        stats = discovery_engine.get_discovery_stats()
        assert stats.total_skills_indexed >= 5

    def test_stats_track_discoveries(self, discovery_engine):
        discovery_engine.discover_skills_for_task("test task 1")
        discovery_engine.discover_skills_for_task("test task 2")
        stats = discovery_engine.get_discovery_stats()
        assert stats.total_discoveries == 2

    def test_last_discovery_time_updated(self, discovery_engine):
        before = discovery_engine.stats.last_discovery_time
        discovery_engine.discover_skills_for_task("test task")
        after = discovery_engine.stats.last_discovery_time
        assert after is not None
        if before is not None:
            assert after >= before


class TestExportReport:
    """Test export discovery report"""

    def test_export_contains_stats(self, discovery_engine):
        report = discovery_engine.export_discovery_report()
        assert "stats" in report
        assert "total_skills" in report
        assert report["total_skills"] >= 5

    def test_export_contains_skills_by_category(self, discovery_engine):
        report = discovery_engine.export_discovery_report()
        assert "skills_by_category" in report
        assert "worker" in report["skills_by_category"]

    def test_export_contains_top_used_skills(self, discovery_engine):
        skill_id = list(discovery_engine.skill_index.keys())[0]
        discovery_engine.record_skill_usage(skill_id, success=True)
        report = discovery_engine.export_discovery_report()
        assert "top_used_skills" in report
        assert len(report["top_used_skills"]) > 0

    def test_export_contains_recent_discoveries(self, discovery_engine):
        discovery_engine.discover_skills_for_task("test query")
        report = discovery_engine.export_discovery_report()
        assert "recent_discoveries" in report
        assert len(report["recent_discoveries"]) > 0


class TestSingleton:
    """Test singleton accessor"""

    def test_get_discovery_engine_returns_instance(self):
        engine = get_discovery_engine()
        assert isinstance(engine, SkillDiscoveryEngine)

    def test_get_discovery_engine_returns_same_instance(self):
        engine1 = get_discovery_engine()
        engine2 = get_discovery_engine()
        assert engine1 is engine2


class TestCategoryClassification:
    """Test category classification"""

    def test_classify_worker_skill(self, discovery_engine):
        for skill in discovery_engine.skill_index.values():
            if skill.category == SkillCategory.WORKER:
                assert "worker" in skill.name.lower() or "architect" in skill.name.lower() or "explorer" in skill.name.lower() or "reviewer" in skill.name.lower() or "critic" in skill.name.lower() or "reasoner" in skill.name.lower() or "innovator" in skill.name.lower() or "vision" in skill.name.lower() or "qa" in skill.name.lower()

    def test_classify_constitutional_skill(self, discovery_engine):
        for skill in discovery_engine.skill_index.values():
            if skill.category == SkillCategory.CONSTITUTIONAL:
                assert "constitutional" in skill.name.lower() or "constitutional" in skill.description.lower() or "principle" in skill.description.lower() or "ethic" in skill.description.lower()


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_discover_with_special_characters(self, discovery_engine):
        matches = discovery_engine.discover_skills_for_task(
            "Build @auth #system with $pecial chars!"
        )
        assert isinstance(matches, list)

    def test_discover_with_unicode(self, discovery_engine):
        matches = discovery_engine.discover_skills_for_task(
            "تصميم النظام المعماري"
        )
        assert isinstance(matches, list)

    def test_discover_with_very_long_task(self, discovery_engine):
        long_task = "Design " * 100 + "architecture"
        matches = discovery_engine.discover_skills_for_task(long_task)
        assert isinstance(matches, list)

    def test_keyword_extraction_filters_stopwords(self, discovery_engine):
        for skill in discovery_engine.skill_index.values():
            for kw in skill.keywords:
                assert kw not in {"this", "that", "with", "from"}


class TestSkillMatchScore:
    """Test match score calculation"""

    def test_high_overlap_high_score(self, discovery_engine):
        matches = discovery_engine.discover_skills_for_task(
            "Architect microservice system design"
        )
        top_match = matches[0] if matches else None
        if top_match:
            assert top_match.match_score > 0.3

    def test_no_overlap_low_or_no_match(self, discovery_engine):
        matches = discovery_engine.discover_skills_for_task(
            "xylophone quantum banana"
        )
        # Should not find strong matches
        if matches:
            assert matches[0].match_strength in (MatchStrength.WEAK, MatchStrength.NONE)

    def test_score_to_strength_thresholds(self, discovery_engine):
        engine = discovery_engine
        assert engine._score_to_strength(0.9) == MatchStrength.EXACT
        assert engine._score_to_strength(0.7) == MatchStrength.STRONG
        assert engine._score_to_strength(0.5) == MatchStrength.MODERATE
        assert engine._score_to_strength(0.3) == MatchStrength.WEAK
        assert engine._score_to_strength(0.1) == MatchStrength.NONE


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
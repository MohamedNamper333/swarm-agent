"""
Skill Discovery Module - Smart Matching of Skills to Tasks
Implements indexing, content extraction, and intelligent skill matching
based on keywords, categories, and historical performance.
"""
import json
import time
import logging
import re
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import defaultdict
import threading
import uuid

logger = logging.getLogger(__name__)


class SkillCategory(Enum):
    """Categories of skills"""
    WORKER = "worker"
    CONSTITUTIONAL = "constitutional"
    INFRASTRUCTURE = "infrastructure"
    WORKFLOW = "workflow"
    DOMAIN = "domain"
    UNKNOWN = "unknown"


class MatchStrength(Enum):
    """Strength of skill-task match"""
    EXACT = "exact"
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
    NONE = "none"


@dataclass
class SkillMetadata:
    """Metadata for a discovered skill"""
    skill_id: str
    name: str
    path: str
    category: SkillCategory
    description: str
    keywords: List[str]
    triggers: List[str]
    content_size: int
    last_used: Optional[str] = None
    usage_count: int = 0
    avg_success_rate: float = 0.0
    avg_match_score: float = 0.0
    indexed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class SkillMatch:
    """Result of matching a task to skills"""
    skill_id: str
    skill_name: str
    match_strength: MatchStrength
    match_score: float  # 0.0 - 1.0
    matched_keywords: List[str]
    category: SkillCategory
    rationale: str
    historical_success_rate: float
    last_used: Optional[str]


@dataclass
class DiscoveryStats:
    """Statistics about the skill discovery system"""
    total_skills_indexed: int = 0
    total_discoveries: int = 0
    successful_matches: int = 0
    failed_matches: int = 0
    avg_match_accuracy: float = 0.0
    last_discovery_time: Optional[str] = None


class SkillDiscoveryEngine:
    """
    Discovers and matches skills to tasks using content indexing,
    keyword analysis, and historical performance data.
    """

    # Skills directory paths
    DEFAULT_SKILL_PATHS = [
        "skills",
        "skill-libraries",
    ]

    # Keywords that indicate specific categories
    CATEGORY_KEYWORDS = {
        SkillCategory.CONSTITUTIONAL: [
            "constitutional", "honesty", "evidence", "minimal", "reversibility",
            "human-agency", "principle", "ethic", "guardrail", "policy",
            "responsible", "governance", "compliance"
        ],
        SkillCategory.INFRASTRUCTURE: [
            "memory", "protocol", "vault", "scratchpad", "token-budget",
            "observability", "monitoring", "logging", "tracking", "metric"
        ],
        SkillCategory.WORKFLOW: [
            "workflow", "bundle", "stage", "pipeline", "process",
            "gate", "approval", "review", "interview"
        ],
        SkillCategory.WORKER: [
            "worker", "agent", "reasoner", "innovator", "reviewer",
            "architect", "qa", "critic", "explorer", "vision-coder"
        ],
        SkillCategory.DOMAIN: [
            "development", "cloud", "devops", "scripting", "database",
            "testing", "documentation", "security", "frontend", "backend"
        ]
    }

    def __init__(self, storage_path: str = "swarm/skill_discovery"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

        self.skill_index: Dict[str, SkillMetadata] = {}
        self.keyword_to_skills: Dict[str, Set[str]] = defaultdict(set)
        self.category_to_skills: Dict[SkillCategory, Set[str]] = defaultdict(set)
        self.task_history: List[Dict] = []
        self.stats = DiscoveryStats()

        self._load_index()
        self._discover_all_skills()

    def _load_index(self) -> None:
        """Load skill index from disk"""
        index_file = self.storage_path / "skill_index.json"
        if index_file.exists():
            try:
                with open(index_file, "r") as f:
                    data = json.load(f)
                for skill_id, skill_data in data.items():
                    # Convert category string back to enum
                    if "category" in skill_data and isinstance(skill_data["category"], str):
                        skill_data["category"] = SkillCategory(skill_data["category"])
                    skill = SkillMetadata(**skill_data)
                    self.skill_index[skill_id] = skill
                    for kw in skill.keywords:
                        self.keyword_to_skills[kw.lower()].add(skill_id)
                    self.category_to_skills[skill.category].add(skill_id)
                self.stats.total_skills_indexed = len(self.skill_index)
                logger.info(f"Loaded {len(self.skill_index)} skills from index")
            except Exception as e:
                logger.error(f"Failed to load skill index: {e}")

    def _save_index(self) -> None:
        """Save skill index to disk"""
        index_file = self.storage_path / "skill_index.json"
        try:
            data = {}
            for skill_id, skill in self.skill_index.items():
                skill_dict = asdict(skill)
                # Convert enum to string for JSON serialization
                skill_dict["category"] = skill.category.value
                data[skill_id] = skill_dict
            with open(index_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save skill index: {e}")

    def _discover_all_skills(self) -> None:
        """Discover all SKILL.md files in known directories"""
        discovered_count = 0
        for base_path in self.DEFAULT_SKILL_PATHS:
            base = Path(base_path)
            if not base.exists():
                continue
            for skill_md in base.rglob("SKILL.md"):
                try:
                    self._index_skill_file(skill_md)
                    discovered_count += 1
                except Exception as e:
                    logger.warning(f"Failed to index {skill_md}: {e}")

        with self._lock:
            self.stats.total_skills_indexed = len(self.skill_index)
        self._save_index()
        logger.info(f"Discovered and indexed {discovered_count} skills")

    def _index_skill_file(self, skill_path: Path) -> None:
        """Index a single SKILL.md file"""
        content = skill_path.read_text(encoding="utf-8", errors="ignore")
        skill_id = str(skill_path.parent.relative_to(skill_path.parents[2])
                       if len(skill_path.parents) >= 3 else skill_path.parent)

        # Skip if already indexed and file unchanged
        if skill_id in self.skill_index:
            existing = self.skill_index[skill_id]
            if existing.content_size == len(content):
                return

        # Extract metadata
        name = skill_path.parent.name
        description = self._extract_description(content)
        keywords = self._extract_keywords(content)
        triggers = self._extract_triggers(content)
        category = self._classify_category(name, description, keywords)

        skill = SkillMetadata(
            skill_id=skill_id,
            name=name,
            path=str(skill_path),
            category=category,
            description=description,
            keywords=keywords,
            triggers=triggers,
            content_size=len(content)
        )

        with self._lock:
            self.skill_index[skill_id] = skill
            for kw in keywords:
                self.keyword_to_skills[kw.lower()].add(skill_id)
            self.category_to_skills[category].add(skill_id)

    def _extract_description(self, content: str) -> str:
        """Extract description from SKILL.md content"""
        lines = content.split("\n")
        desc_lines = []
        in_description = False
        title_seen = False

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("#") and not title_seen:
                # First heading - usually the title
                title_seen = True
                continue
            if stripped.startswith("##") and title_seen:
                if in_description:
                    break
                in_description = True
                continue
            if stripped.startswith("###") and title_seen:
                if in_description:
                    break
                in_description = True
                continue
            if stripped.startswith("```"):
                # Skip code blocks
                in_description = False
                continue
            if title_seen and stripped and not stripped.startswith("#"):
                desc_lines.append(stripped)
            if len(desc_lines) >= 3:
                break

        # If still empty, try to get any non-heading text after the title
        if not desc_lines:
            after_title = False
            for line in lines:
                stripped = line.strip()
                if stripped.startswith("#") and not after_title:
                    after_title = True
                    continue
                if after_title and stripped and not stripped.startswith("#") and not stripped.startswith("```"):
                    desc_lines.append(stripped)
                if len(desc_lines) >= 3:
                    break

        return " ".join(desc_lines)[:500] if desc_lines else (content[:200] if content else "")

    def _extract_keywords(self, content: str) -> List[str]:
        """Extract keywords from SKILL.md content"""
        # Remove markdown syntax
        text = re.sub(r"[#*`_~\[\]()>]", " ", content.lower())
        # Remove URLs
        text = re.sub(r"https?://\S+", " ", text)
        # Extract words
        words = re.findall(r"\b[a-z][a-z-]{3,}\b", text)

        # Filter common stopwords
        stopwords = {
            "this", "that", "with", "from", "have", "been", "will",
            "would", "could", "should", "their", "there", "these",
            "those", "which", "where", "when", "what", "they", "them",
            "than", "then", "also", "more", "most", "such", "some",
            "into", "over", "only", "very", "just", "your", "you",
            "for", "and", "the", "are", "can", "all", "any", "use"
        }
        keywords = [w for w in words if w not in stopwords and len(w) >= 4]

        # Count frequency and return top 30
        freq = defaultdict(int)
        for kw in keywords:
            freq[kw] += 1

        top_keywords = sorted(freq.items(), key=lambda x: x[1], reverse=True)[:30]
        return [kw for kw, _ in top_keywords]

    def _extract_triggers(self, content: str) -> List[str]:
        """Extract trigger phrases that activate this skill"""
        triggers = []
        trigger_patterns = [
            r"[Tt]rigger[s]?:\s*([^\n]+)",
            r"[Uu]se [Ww]hen:\s*([^\n]+)",
            r"[Aa]ctivates?\s+(?:when|on|for):\s*([^\n]+)"
        ]

        for pattern in trigger_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                # Split on commas or "or"
                phrases = re.split(r",|\bor\b", match)
                for phrase in phrases:
                    cleaned = phrase.strip().strip("\"'")
                    if cleaned and len(cleaned) > 5:
                        triggers.append(cleaned[:100])

        return triggers[:10]

    def _classify_category(
        self, name: str, description: str, keywords: List[str]
    ) -> SkillCategory:
        """Classify skill category based on content"""
        text = (name + " " + description + " " + " ".join(keywords)).lower()
        scores = {cat: 0 for cat in SkillCategory}

        for category, cat_keywords in self.CATEGORY_KEYWORDS.items():
            for kw in cat_keywords:
                if kw in text:
                    scores[category] += 1

        best_category = max(scores, key=scores.get)
        if scores[best_category] == 0:
            return SkillCategory.UNKNOWN
        return best_category

    def discover_skills_for_task(
        self, task_description: str, top_k: int = 5,
        required_category: Optional[SkillCategory] = None
    ) -> List[SkillMatch]:
        """
        Discover best matching skills for a task.
        Returns top_k matches sorted by relevance.
        """
        if not task_description or not task_description.strip():
            return []

        self.stats.total_discoveries += 1
        self.stats.last_discovery_time = datetime.now(timezone.utc).isoformat()

        task_keywords = self._extract_task_keywords(task_description)
        matches = []

        with self._lock:
            candidate_skills = self.skill_index.values()
            if required_category:
                candidate_skills = [
                    s for s in candidate_skills
                    if s.category == required_category
                ]

            for skill in candidate_skills:
                match_score, matched_keywords = self._score_skill_match(
                    task_keywords, skill
                )

                if match_score > 0.1:
                    match_strength = self._score_to_strength(match_score)
                    rationale = self._build_rationale(
                        task_description, skill, matched_keywords
                    )
                    matches.append(SkillMatch(
                        skill_id=skill.skill_id,
                        skill_name=skill.name,
                        match_strength=match_strength,
                        match_score=match_score,
                        matched_keywords=matched_keywords,
                        category=skill.category,
                        rationale=rationale,
                        historical_success_rate=skill.avg_success_rate,
                        last_used=skill.last_used
                    ))

        matches.sort(key=lambda m: m.match_score, reverse=True)

        # Track task in history
        self.task_history.append({
            "task_description": task_description[:200],
            "discovered_skills": [m.skill_id for m in matches[:top_k]],
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        if len(self.task_history) > 5000:
            del self.task_history[:-5000]

        return matches[:top_k]

    def _extract_task_keywords(self, task: str) -> Set[str]:
        """Extract keywords from task description"""
        text = re.sub(r"[^\w\s-]", " ", task.lower())
        words = re.findall(r"\b[a-z][a-z-]{3,}\b", text)

        stopwords = {
            "this", "that", "with", "from", "have", "been", "will",
            "would", "could", "should", "their", "there", "these",
            "those", "which", "where", "when", "what", "they", "them",
            "than", "then", "also", "more", "most", "such", "some",
            "into", "over", "only", "very", "just", "your", "you",
            "for", "and", "the", "are", "can", "all", "any", "use"
        }
        return {w for w in words if w not in stopwords and len(w) >= 3}

    def _score_skill_match(
        self, task_keywords: Set[str], skill: SkillMetadata
    ) -> Tuple[float, List[str]]:
        """Score how well a skill matches a task"""
        if not task_keywords:
            return 0.0, []

        skill_keywords = {kw.lower() for kw in skill.keywords}
        matched = task_keywords & skill_keywords

        if not matched:
            return 0.0, []

        # Base score: percentage of task keywords matched
        base_score = len(matched) / len(task_keywords)

        # Boost: percentage of skill keywords matched
        skill_coverage = len(matched) / max(len(skill_keywords), 1)

        # Trigger match boost
        trigger_boost = 0.0
        task_lower = " ".join(task_keywords)
        for trigger in skill.triggers:
            trigger_words = set(re.findall(r"\b[a-z][a-z-]{3,}\b", trigger.lower()))
            if trigger_words and trigger_words & task_keywords:
                trigger_boost += 0.1

        # Category bonus for workers (more actionable)
        category_bonus = 0.05 if skill.category == SkillCategory.WORKER else 0.0

        # Usage history bonus
        usage_bonus = min(skill.usage_count / 100.0, 0.1) if skill.usage_count > 0 else 0.0

        final_score = min(
            base_score * 0.6 + skill_coverage * 0.2 + trigger_boost +
            category_bonus + usage_bonus,
            1.0
        )

        return final_score, sorted(matched)

    def _score_to_strength(self, score: float) -> MatchStrength:
        """Convert numerical score to match strength category"""
        if score >= 0.8:
            return MatchStrength.EXACT
        elif score >= 0.6:
            return MatchStrength.STRONG
        elif score >= 0.4:
            return MatchStrength.MODERATE
        elif score >= 0.2:
            return MatchStrength.WEAK
        return MatchStrength.NONE

    def _build_rationale(
        self, task: str, skill: SkillMetadata, matched_keywords: List[str]
    ) -> str:
        """Build human-readable rationale for why this skill matches"""
        if not matched_keywords:
            return f"Skill '{skill.name}' is available but no strong keyword match"

        keywords_str = ", ".join(matched_keywords[:5])
        return (
            f"Skill '{skill.name}' ({skill.category.value}) matches based on "
            f"keywords: {keywords_str}"
        )

    def record_skill_usage(
        self, skill_id: str, success: bool, task_id: Optional[str] = None
    ) -> None:
        """Record that a skill was used and whether it succeeded"""
        with self._lock:
            if skill_id not in self.skill_index:
                logger.warning(f"Unknown skill_id: {skill_id}")
                return

            skill = self.skill_index[skill_id]
            skill.usage_count += 1
            skill.last_used = datetime.now(timezone.utc).isoformat()

            # Update rolling success rate
            old_rate = skill.avg_success_rate
            old_count = skill.usage_count - 1
            new_rate = (
                (old_rate * old_count + (1.0 if success else 0.0))
                / skill.usage_count
            )
            skill.avg_success_rate = new_rate

            self._save_index()

    def get_skill_by_id(self, skill_id: str) -> Optional[SkillMetadata]:
        """Retrieve a skill by its ID"""
        with self._lock:
            return self.skill_index.get(skill_id)

    def list_skills_by_category(
        self, category: SkillCategory
    ) -> List[SkillMetadata]:
        """List all skills in a category"""
        with self._lock:
            skill_ids = self.category_to_skills.get(category, set())
            return [self.skill_index[sid] for sid in skill_ids if sid in self.skill_index]

    def get_discovery_stats(self) -> DiscoveryStats:
        """Get discovery engine statistics"""
        with self._lock:
            if self.stats.total_discoveries > 0:
                self.stats.avg_match_accuracy = (
                    self.stats.successful_matches / self.stats.total_discoveries
                )
            return self.stats

    def reindex_all(self) -> int:
        """Reindex all skills from disk, preserving usage statistics"""
        # Snapshot existing usage stats before reindexing
        with self._lock:
            usage_snapshot = {
                skill_id: {
                    "usage_count": skill.usage_count,
                    "avg_success_rate": skill.avg_success_rate,
                    "last_used": skill.last_used
                }
                for skill_id, skill in self.skill_index.items()
            }
            self.skill_index.clear()
            self.keyword_to_skills.clear()
            self.category_to_skills.clear()

        self._discover_all_skills()

        # Restore usage stats
        with self._lock:
            for skill_id, stats in usage_snapshot.items():
                if skill_id in self.skill_index:
                    self.skill_index[skill_id].usage_count = stats["usage_count"]
                    self.skill_index[skill_id].avg_success_rate = stats["avg_success_rate"]
                    self.skill_index[skill_id].last_used = stats["last_used"]
            self._save_index()

        return len(self.skill_index)

    def export_discovery_report(self) -> Dict[str, Any]:
        """Export discovery report for analysis"""
        with self._lock:
            return {
                "stats": asdict(self.stats),
                "total_skills": len(self.skill_index),
                "skills_by_category": {
                    cat.value: len(sids)
                    for cat, sids in self.category_to_skills.items()
                },
                "top_used_skills": sorted(
                    [
                        {
                            "skill_id": s.skill_id,
                            "name": s.name,
                            "usage_count": s.usage_count,
                            "avg_success_rate": s.avg_success_rate
                        }
                        for s in self.skill_index.values()
                    ],
                    key=lambda x: x["usage_count"],
                    reverse=True
                )[:10],
                "recent_discoveries": self.task_history[-10:]
            }


# Module-level singleton for convenience
_default_engine: Optional[SkillDiscoveryEngine] = None


def get_discovery_engine(
    storage_path: str = "swarm/skill_discovery"
) -> SkillDiscoveryEngine:
    """Get or create the default discovery engine"""
    global _default_engine
    if _default_engine is None:
        _default_engine = SkillDiscoveryEngine(storage_path)
    return _default_engine
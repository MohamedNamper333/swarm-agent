"""
Learning Tracker Module - Track Agent Performance Over Time
Tracks agent performance metrics, learning curves, and improvement trends
"""
import json
import time
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import defaultdict
from pathlib import Path
import threading
import statistics

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of metrics tracked"""
    TASK_SUCCESS_RATE = "task_success_rate"
    TASK_DURATION = "task_duration"
    CODE_QUALITY = "code_quality"
    SECURITY_SCORE = "security_score"
    TEST_COVERAGE = "test_coverage"
    REVIEW_SCORE = "review_score"
    REFLECTION_DEPTH = "reflection_depth"
    CONSTITUTIONAL_COMPLIANCE = "constitutional_compliance"
    COLLABORATION_SCORE = "collaboration_score"
    INNOVATION_INDEX = "innovation_index"


class TrendDirection(Enum):
    IMPROVING = "improving"
    STABLE = "stable"
    DECLINING = "declining"
    VOLATILE = "volatile"


@dataclass
class MetricSnapshot:
    """Single metric measurement at a point in time"""
    metric_type: MetricType
    value: float
    timestamp: str
    task_id: str
    context: Dict = field(default_factory=dict)


@dataclass
class SkillProficiency:
    """Tracks proficiency in a specific skill/domain"""
    skill_name: str
    current_level: float  # 0.0 - 1.0
    confidence: float  # 0.0 - 1.0
    tasks_completed: int
    last_updated: str
    trend: str = "stable"  # improving, stable, declining
    evidence: List[str] = field(default_factory=list)


@dataclass
class LearningCurve:
    """Tracks learning progression for a specific metric"""
    metric_type: MetricType
    data_points: List[Dict] = field(default_factory=list)  # {timestamp, value, task_id}
    trend: TrendDirection = TrendDirection.STABLE
    slope: float = 0.0
    r_squared: float = 0.0
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())
    projected_value: Optional[float] = None


@dataclass
class AgentLearningProfile:
    """Complete learning profile for an agent"""
    agent_id: str
    created_at: str
    last_updated: str
    
    # Metric tracking
    metric_history: Dict[MetricType, List[MetricSnapshot]] = field(default_factory=lambda: defaultdict(list))
    learning_curves: Dict[MetricType, LearningCurve] = field(default_factory=dict)
    
    # Skill tracking
    skill_proficiencies: Dict[str, SkillProficiency] = field(default_factory=dict)
    
    # Performance summary
    overall_score: float = 0.5
    trend: TrendDirection = TrendDirection.STABLE
    strengths: List[str] = field(default_factory=list)
    improvement_areas: List[str] = field(default_factory=list)
    
    # Milestones
    milestones: List[Dict] = field(default_factory=list)
    
    # Collaboration
    collaboration_network: Dict[str, float] = field(default_factory=dict)  # agent_id -> collaboration_score


class LearningTracker:
    """
    Tracks agent performance metrics over time, identifies learning curves,
    skill development, and provides predictive insights.
    """
    
    def __init__(self, storage_path: str = "swarm/learning"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self.profiles: Dict[str, AgentLearningProfile] = {}
        self._load_profiles()
        
        # Metric weights for overall score calculation
        self.metric_weights = {
            MetricType.TASK_SUCCESS_RATE: 0.25,
            MetricType.CODE_QUALITY: 0.15,
            MetricType.SECURITY_SCORE: 0.20,
            MetricType.TEST_COVERAGE: 0.10,
            MetricType.REVIEW_SCORE: 0.10,
            MetricType.CONSTITUTIONAL_COMPLIANCE: 0.15,
            MetricType.COLLABORATION_SCORE: 0.05,
        }
        
        # Skill taxonomy
        self.skill_taxonomy = {
            "programming": ["python", "javascript", "rust", "go", "java", "cpp"],
            "architecture": ["system_design", "api_design", "database_design", "microservices"],
            "security": ["threat_modeling", "vulnerability_assessment", "secure_coding", "penetration_testing"],
            "testing": ["unit_testing", "integration_testing", "e2e_testing", "property_testing"],
            "devops": ["ci_cd", "containerization", "orchestration", "monitoring", "infrastructure"],
            "data": ["sql", "nosql", "data_modeling", "etl", "analytics"],
            "frontend": ["react", "vue", "angular", "css", "accessibility", "performance"],
            "backend": ["api_design", "database_optimization", "caching", "message_queues"],
            "ai_ml": ["prompt_engineering", "rag", "fine_tuning", "eval", "mlops"],
            "soft_skills": ["communication", "mentoring", "code_review", "documentation", "planning"]
        }
    
    def _get_or_create_profile(self, agent_id: str) -> 'AgentLearningProfile':
        """Get or create learning profile for agent"""
        with self._lock:
            if agent_id not in self.profiles:
                self.profiles[agent_id] = AgentLearningProfile(
                    agent_id=agent_id,
                    created_at=datetime.now().isoformat(),
                    last_updated=datetime.now().isoformat()
                )
                self._initialize_learning_curves(agent_id)
            return self.profiles[agent_id]
    
    def _initialize_learning_curves(self, agent_id: str):
        """Initialize learning curves for all metric types"""
        profile = self.profiles[agent_id]
        for metric_type in MetricType:
            if metric_type not in profile.learning_curves:
                profile.learning_curves[metric_type] = LearningCurve(metric_type=metric_type)
    
    def _save_profiles(self):
        """Save profiles to disk"""
        save_path = self.storage_path / "learning_profiles.json"
        try:
            data = {}
            for agent_id, profile in self.profiles.items():
                data[agent_id] = asdict(profile)
            with open(self.storage_path / "learning_profiles.json", 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save learning profiles: {e}")
    
    def _load_profiles(self):
        """Load profiles from disk"""
        load_path = self.storage_path / "learning_profiles.json"
        if load_path.exists():
            try:
                with open(load_path, 'r') as f:
                    data = json.load(f)
                    for agent_id, profile_data in data.items():
                        # Reconstruct profile (simplified)
                        self.profiles[agent_id] = AgentLearningProfile(**profile_data)
            except Exception as e:
                logger.warning(f"Failed to load learning profiles: {e}")
    
    def record_metric(
        self,
        agent_id: str,
        metric_type: MetricType,
        value: float,
        task_id: str,
        context: Optional[Dict] = None
    ) -> Dict:
        """Record a metric measurement for an agent"""
        with self._lock:
            profile = self._get_or_create_profile(agent_id)
            timestamp = datetime.now().isoformat()
            
            # Create snapshot
            snapshot = MetricSnapshot(
                metric_type=metric_type,
                value=value,
                timestamp=timestamp,
                task_id=task_id,
                context=context or {}
            )
            
            # Add to history
            profile.metric_history[metric_type].append(snapshot)
            
            # Update learning curve
            self._update_learning_curve(agent_id, metric_type, snapshot)
            
            # Update overall score
            self._recalculate_overall_score(agent_id)
            
            # Update skill proficiencies
            self._update_skill_proficiencies(agent_id, task_id)
            
            # Check for milestones
            self._check_milestones(agent_id)
            
            profile.last_updated = datetime.now().isoformat()
            self._save_profiles()
            
            return {
                "metric": metric_type.value,
                "value": value,
                "trend": self._get_trend(agent_id, metric_type),
                "overall_score": self.profiles[agent_id].overall_score
            }
    
    def _update_learning_curve(self, agent_id: str, metric_type: MetricType, snapshot: MetricSnapshot):
        """Update learning curve with new data point"""
        profile = self.profiles[agent_id]
        curve = profile.learning_curves[metric_type]
        
        curve.data_points.append({
            "timestamp": snapshot.timestamp,
            "value": snapshot.value,
            "task_id": snapshot.task_id
        })
        
        # Keep only last 100 points
        if len(curve.data_points) > 100:
            curve.data_points = curve.data_points[-100:]
        
        # Recalculate trend
        self._recalculate_trend(curve)
        curve.last_updated = datetime.now().isoformat()
    
    def _recalculate_trend(self, curve: 'LearningCurve'):
        """Recalculate trend direction and slope using linear regression"""
        if len(curve.data_points) < 3:
            curve.trend = TrendDirection.STABLE
            curve.slope = 0.0
            curve.r_squared = 0.0
            return
        
        # Simple linear regression
        n = len(curve.data_points)
        x = list(range(n))
        y = [p["value"] for p in curve.data_points]
        
        x_mean = sum(x) / n
        y_mean = sum(y) / n
        
        numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
        
        if denominator > 0:
            slope = numerator / denominator
            curve.slope = slope
            
            # Calculate R-squared
            y_pred = [y_mean + slope * (x[i] - x_mean) for i in range(n)]
            ss_res = sum((y[i] - y_pred[i]) ** 2 for i in range(n))
            ss_tot = sum((y[i] - y_mean) ** 2 for i in range(n))
            curve.r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
            
            # Determine trend
            if abs(slope) < 0.01:
                curve.trend = TrendDirection.STABLE
            elif slope > 0:
                curve.trend = TrendDirection.IMPROVING
            else:
                curve.trend = TrendDirection.DECLINING
        else:
            curve.trend = TrendDirection.VOLATILE
            curve.slope = 0.0
        
        # Project next value
        if curve.data_points:
            last_x = len(curve.data_points) - 1
            curve.projected_value = curve.data_points[-1]["value"] + curve.slope
    
    def _get_trend(self, agent_id: str, metric_type: MetricType) -> str:
        """Get current trend for a metric"""
        profile = self.profiles.get(agent_id)
        if not profile:
            return "unknown"
        curve = profile.learning_curves.get(metric_type)
        if not curve:
            return "insufficient_data"
        return curve.trend.value
    
    def _recalculate_overall_score(self, agent_id: str):
        """Recalculate overall weighted score"""
        profile = self.profiles[agent_id]
        total_weight = 0.0
        weighted_sum = 0.0
        
        for metric_type, weight in self.metric_weights.items():
            curve = profile.learning_curves.get(metric_type)
            if curve and curve.data_points:
                latest_value = curve.data_points[-1]["value"]
                weighted_sum += latest_value * weight
                total_weight += weight
        
        if total_weight > 0:
            profile.overall_score = weighted_sum / total_weight
        else:
            profile.overall_score = 0.5
        
        # Determine overall trend
        trends = [c.trend for c in profile.learning_curves.values() if c.data_points]
        if trends:
            improving = sum(1 for t in trends if t == TrendDirection.IMPROVING)
            declining = sum(1 for t in trends if t == TrendDirection.DECLINING)
            if improving > declining:
                profile.trend = TrendDirection.IMPROVING
            elif declining > improving:
                profile.trend = TrendDirection.DECLINING
            else:
                profile.trend = TrendDirection.STABLE
    
    def _update_skill_proficiencies(self, agent_id: str, task_id: str):
        """Update skill proficiencies based on task completion"""
        profile = self.profiles[agent_id]
        
        # Extract skills from task (simplified - would integrate with task classifier)
        task_skills = self._extract_skills_from_task(task_id)
        
        for skill in task_skills:
            if skill not in profile.skill_proficiencies:
                profile.skill_proficiencies[skill] = SkillProficiency(
                    skill_name=skill,
                    current_level=0.1,
                    confidence=0.5,
                    tasks_completed=0,
                    last_updated=datetime.now().isoformat()
                )
            
            proficiency = profile.skill_proficiencies[skill]
            proficiency.tasks_completed += 1
            proficiency.current_level = min(1.0, proficiency.current_level + 0.02)
            proficiency.confidence = min(1.0, proficiency.confidence + 0.05)
            proficiency.last_updated = datetime.now().isoformat()
            proficiency.evidence.append(f"Completed task {task_id}")
            
            # Determine trend
            if proficiency.current_level > 0.8:
                proficiency.trend = "mastering"
            elif proficiency.current_level > 0.5:
                proficiency.trend = "improving"
            else:
                proficiency.trend = "learning"
    
    def _extract_skills_from_task(self, task_id: str) -> List[str]:
        """Extract skills from task (simplified)"""
        # In real implementation, would query task metadata
        # For now, return some default skills based on task_id
        skill_map = {
            "api": ["api_design", "backend"],
            "security": ["security", "threat_modeling"],
            "frontend": ["frontend", "react"],
            "database": ["sql", "database_design"],
            "test": ["testing", "unit_testing"],
            "refactor": ["refactoring", "architecture"],
            "debug": ["debugging", "troubleshooting"]
        }
        
        skills = []
        for key, skills_list in skill_map.items():
            if key in task_id.lower():
                skills.extend(skills_list)
        return skills if skills else ["general"]
    
    def _check_milestones(self, agent_id: str):
        """Check and award milestones"""
        profile = self.profiles[agent_id]
        
        # Task completion milestones
        total_tasks = sum(len(h) for h in profile.metric_history.values())
        milestones = {
            1: "First Task Completed",
            10: "10 Tasks Completed",
            50: "50 Tasks Completed",
            100: "Century Club",
            500: "500 Tasks - Veteran"
        }
        
        for threshold, name in milestones.items():
            if total_tasks >= threshold:
                existing = [m for m in profile.milestones if m["name"] == name]
                if not existing:
                    profile.milestones.append({
                        "name": name,
                        "threshold": threshold,
                        "achieved_at": datetime.now().isoformat(),
                        "metric": "total_tasks"
                    })
                    logger.info(f"Agent {agent_id} achieved milestone: {name}")
        
        # Score milestones
        score_milestones = {
            0.6: "Competent",
            0.7: "Proficient",
            0.8: "Expert",
            0.9: "Master"
        }
        
        for threshold, name in score_milestones.items():
            if self.profiles[agent_id].overall_score >= threshold:
                existing = [m for m in profile.milestones if m["name"] == name]
                if not existing:
                    profile.milestones.append({
                        "name": name,
                        "threshold": threshold,
                        "achieved_at": datetime.now().isoformat(),
                        "metric": "overall_score"
                    })
                    logger.info(f"Agent {agent_id} achieved milestone: {name}")
    
    def get_profile(self, agent_id: str) -> Optional[Dict]:
        """Get complete learning profile for agent"""
        with self._lock:
            profile = self.profiles.get(agent_id)
            if not profile:
                return None
            return asdict(profile)
    
    def get_learning_curve(self, agent_id: str, metric_type: MetricType) -> Optional[Dict]:
        """Get learning curve data for a specific metric"""
        with self._lock:
            profile = self.profiles.get(agent_id)
            if not profile:
                return None
            curve = profile.learning_curves.get(metric_type)
            if not curve:
                return None
            return asdict(curve)
    
    def get_skill_proficiency(self, agent_id: str, skill_name: str) -> Optional[Dict]:
        """Get proficiency for a specific skill"""
        with self._lock:
            profile = self.profiles.get(agent_id)
            if not profile:
                return None
            proficiency = profile.skill_proficiencies.get(skill_name)
            if not proficiency:
                return None
            return asdict(proficiency)
    
    def get_top_skills(self, agent_id: str, limit: int = 10) -> List[Dict]:
        """Get top skills by proficiency"""
        with self._lock:
            profile = self.profiles.get(agent_id)
            if not profile:
                return []
            skills = sorted(
                profile.skill_proficiencies.values(),
                key=lambda s: s.current_level,
                reverse=True
            )
            return [asdict(s) for s in skills[:limit]]
    
    def get_performance_report(self, agent_id: str) -> Dict:
        """Generate comprehensive performance report"""
        with self._lock:
            profile = self.profiles.get(agent_id)
            if not profile:
                return {"error": "Agent not found"}
            
            return {
                "agent_id": agent_id,
                "overall_score": profile.overall_score,
                "trend": profile.trend.value,
                "strengths": profile.strengths,
                "improvement_areas": profile.improvement_areas,
                "milestones": profile.milestones,
                "top_skills": [asdict(s) for s in sorted(
                    profile.skill_proficiencies.values(),
                    key=lambda s: s.current_level,
                    reverse=True
                )[:10]],
                "metric_trends": {
                    m.value: c.trend.value
                    for m, c in profile.learning_curves.items()
                    if c.data_points
                },
                "total_tasks": sum(len(h) for h in profile.metric_history.values()),
                "collaboration_network": profile.collaboration_network
            }
    
    def compare_agents(self, agent_ids: List[str]) -> Dict:
        """Compare multiple agents"""
        with self._lock:
            comparison = {}
            for agent_id in agent_ids:
                profile = self.profiles.get(agent_id)
                if profile:
                    comparison[agent_id] = {
                        "overall_score": profile.overall_score,
                        "trend": profile.trend.value,
                        "top_skills": [s.skill_name for s in sorted(
                            profile.skill_proficiencies.values(),
                            key=lambda s: s.current_level,
                            reverse=True
                        )[:5]]
                    }
            return comparison
    
    def predict_performance(self, agent_id: str, metric_type: MetricType, steps: int = 5) -> List[Dict]:
        """Predict future performance"""
        with self._lock:
            profile = self.profiles.get(agent_id)
            if not profile:
                return []
            
            curve = profile.learning_curves.get(metric_type)
            if not curve or not curve.data_points or curve.projected_value is None:
                return []
            
            predictions = []
            last_value = curve.data_points[-1]["value"]
            slope = curve.slope
            
            for i in range(1, steps + 1):
                predicted = last_value + slope * i
                predictions.append({
                    "step": i,
                    "predicted_value": max(0.0, min(1.0, predicted)),
                    "confidence": max(0.0, curve.r_squared - 0.1 * i)
                })
            
            return predictions


def create_learning_tracker(storage_path: str = "swarm/learning") -> LearningTracker:
    """Create a learning tracker with default settings."""
    return LearningTracker(storage_path)

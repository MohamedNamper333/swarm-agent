"""
Self-Reflection Module - Agent Self-Evaluation After Every Task
Implements structured reflection protocol for continuous improvement
"""
import json
import time
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
import threading
from collections import defaultdict

logger = logging.getLogger(__name__)


class ReflectionDepth(Enum):
    QUICK = "quick"
    STANDARD = "standard"
    DEEP = "deep"


class ReflectionTrigger(Enum):
    TASK_COMPLETION = "task_completion"
    ERROR_ENCOUNTERED = "error_encountered"
    PERFORMANCE_DROP = "performance_drop"
    SCHEDULED = "scheduled"
    MANUAL = "manual"


@dataclass
class ReflectionEntry:
    id: str
    agent_id: str
    task_id: str
    trigger: ReflectionTrigger
    depth: ReflectionDepth
    timestamp: str

    what_went_well: str
    what_could_improve: str
    what_was_unexpected: str
    key_learning: str

    confidence_before: float
    confidence_after: float
    time_spent_seconds: int

    action_items: List[Dict] = field(default_factory=list)
    constitutional_compliance: Dict[str, bool] = field(default_factory=dict)


class SelfReflectionEngine:
    REFLECTION_TEMPLATES = {
        ReflectionDepth.QUICK: {
            "questions": [
                "What went well?",
                "What could improve?",
                "One action item for next time"
            ],
            "time_limit_seconds": 120
        },
        ReflectionDepth.STANDARD: {
            "questions": [
                "What went well? (specific examples)",
                "What could improve? (specific examples)",
                "What was unexpected?",
                "Key learning or insight",
                "Confidence change (before/after)",
                "Constitutional compliance check",
                "2-3 concrete action items"
            ],
            "time_limit_seconds": 600
        },
        ReflectionDepth.DEEP: {
            "questions": [
                "Root cause analysis of any issues",
                "Pattern recognition across recent tasks",
                "Systemic improvements needed",
                "Skill gaps identified",
                "Process improvements",
                "Constitutional compliance deep dive",
                "Detailed action plan with owners/timelines",
                "Knowledge base updates needed"
            ],
            "time_limit_seconds": 1800
        }
    }

    def __init__(self, storage_path: str = "swarm/reflections"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self.reflection_history: Dict[str, List[ReflectionEntry]] = defaultdict(list)
        self._load_history()

        self.constitutional_principles = {
            "HONESTY_OVER_HELPFULNESS": "No fabricated results, honest failures",
            "EVIDENCE_OVER_AUTHORITY": "Every claim sourced, citations mandatory",
            "MINIMAL_SURFACE_AREA": "YAGNI, least code/deps/complexity",
            "REVERSIBILITY_BY_DEFAULT": "Rollback plan before execution",
            "HUMAN_AGENCY_PRESERVATION": "Human decides, AI proposes"
        }

    def _load_history(self):
        history_file = self.storage_path / "reflection_history.json"
        if history_file.exists():
            try:
                with open(history_file, 'r') as f:
                    data = json.load(f)
                    for agent_id, entries in data.items():
                        self.reflection_history[agent_id] = [
                            ReflectionEntry(**entry) for entry in entries
                        ]
            except Exception as e:
                logger.warning(f"Failed to load reflection history: {e}")

    def _save_history(self):
        history_file = self.storage_path / "reflection_history.json"
        try:
            data = {}
            for agent_id, entries in self.reflection_history.items():
                data[agent_id] = [asdict(entry) for entry in entries]
            with open(history_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save reflection history: {e}")

    def trigger_reflection(
        self,
        agent_id: str,
        task_id: str,
        trigger: ReflectionTrigger = ReflectionTrigger.TASK_COMPLETION,
        depth: ReflectionDepth = ReflectionDepth.STANDARD,
        context: Optional[Dict] = None
    ) -> ReflectionEntry:
        with self._lock:
            template = self.REFLECTION_TEMPLATES[depth]

            entry = ReflectionEntry(
                id=f"reflection_{task_id}_{int(time.time())}",
                agent_id=agent_id,
                task_id=task_id,
                trigger=trigger,
                depth=depth,
                timestamp=datetime.now().isoformat(),
                what_went_well="",
                what_could_improve="",
                what_was_unexpected="",
                key_learning="",
                confidence_before=0.0,
                confidence_after=0.0,
                time_spent_seconds=0
            )

            if context:
                entry = self._auto_populate_reflection(entry, context, template)

            self.reflection_history[agent_id].append(entry)
            self._save_history()

            logger.info(f"Reflection completed for agent {agent_id}, task {task_id}")
            return entry

    def _auto_populate_reflection(
        self,
        entry: ReflectionEntry,
        context: Dict,
        template: Dict
    ) -> ReflectionEntry:
        artifacts = context.get("artifacts", {})
        task_spec = context.get("task_spec", {})
        verdict = context.get("verdict", {})
        scores = verdict.get("scores", {})
        evidence = verdict.get("evidence", {})

        went_well = []
        if verdict.get("verdict") in ["PASS", "PASS_WITH_WARNINGS"]:
            went_well.append(f"Task passed with {verdict.get('verdict', 'unknown')} verdict")
        if scores.get("structural", 0) >= 0.9:
            went_well.append("Structural integrity maintained")
        if scores.get("security", 0) >= 0.9:
            went_well.append("Security checks passed")
        if scores.get("functional", 0) >= 0.8:
            went_well.append("Functional requirements met")
        entry.what_went_well = "; ".join(went_well) if went_well else "Task completed successfully"

        improvements = []
        for dim, score in scores.items():
            if score < 0.7:
                improvements.append(f"{dim}: score {score:.0%} needs improvement")
        for dim, ev_list in evidence.items():
            if ev_list:
                improvements.append(f"{dim}: {ev_list[0] if isinstance(ev_list, list) else str(ev_list)}")
        entry.what_could_improve = "; ".join(improvements) if improvements else "Minor improvements possible"

        unexpected = []
        if verdict.get("verdict") == "FAIL" and context.get("expected_pass", True):
            unexpected.append("Task failed despite expectation of success")
        for dim, ev_list in evidence.items():
            if ev_list and any("unexpected" in str(e).lower() for e in ev_list):
                unexpected.append(f"{dim}: unexpected behavior")
        entry.what_was_unexpected = "; ".join(unexpected) if unexpected else "No major surprises"

        learnings = []
        if scores.get("security", 1.0) < 0.8:
            learnings.append("Security patterns need reinforcement")
        if scores.get("documentation", 1.0) < 0.7:
            learnings.append("Documentation standards need enforcement")
        if scores.get("performance", 1.0) < 0.8:
            learnings.append("Performance optimization opportunities identified")
        entry.key_learning = "; ".join(learnings) if learnings else "Process working as expected"

        entry.confidence_before = context.get("confidence_before", 0.5)
        entry.confidence_after = 0.5 + (sum(scores.values()) / len(scores) * 0.5) if scores else 0.5

        entry.constitutional_compliance = {
            "HONESTY_OVER_HELPFULNESS": verdict.get("verdict") != "FABRICATED",
            "EVIDENCE_OVER_AUTHORITY": all(ev for ev in context.get("evidence", {}).values()),
            "MINIMAL_SURFACE_AREA": sum(scores.get(d, 0) for d in ["code_quality", "performance"]) > 0,
            "REVERSIBILITY_BY_DEFAULT": "rollback_plan" in str(context).lower(),
            "HUMAN_AGENCY_PRESERVATION": not context.get("auto_approved", False)
        }

        entry.action_items = self._generate_action_items(scores, evidence, context)

        return entry

    def _generate_action_items(self, scores: Dict, evidence: Dict, context: Dict) -> List[Dict]:
        actions = []

        for dim, score in scores.items():
            if score < 0.7:
                actions.append({
                    "action": f"Improve {dim} score from {score:.0%} to >70%",
                    "priority": "high" if score < 0.5 else "medium",
                    "dimension": dim,
                    "owner": "self",
                    "deadline": "next_task"
                })

        for dim, ev_list in evidence.items():
            if ev_list and isinstance(ev_list, list):
                for ev in ev_list[:2]:
                    actions.append({
                        "action": f"Address {dim}: {ev}",
                        "priority": "high",
                        "dimension": dim,
                        "owner": "self",
                        "deadline": "next_task"
                    })

        if not actions:
            verdict = context.get("verdict", {}).get("verdict", "UNKNOWN")
            if verdict in ["PASS", "PASS_WITH_WARNINGS"]:
                actions.append({
                    "action": "Maintain current quality standards and document lessons learned",
                    "priority": "low",
                    "dimension": "maintenance",
                    "owner": "self",
                    "deadline": "next_task"
                })
            else:
                actions.append({
                    "action": "Review reflection process for missing improvement signals",
                    "priority": "medium",
                    "dimension": "process",
                    "owner": "self",
                    "deadline": "next_task"
                })

        return actions[:5]

    def get_reflection_history(
        self,
        agent_id: str,
        limit: Optional[int] = None
    ) -> List[ReflectionEntry]:
        with self._lock:
            entries = self.reflection_history.get(agent_id, [])
            if limit:
                return entries[-limit:]
            return entries

    def get_reflection_stats(self, agent_id: str) -> Dict:
        with self._lock:
            entries = self.reflection_history.get(agent_id, [])
            if not entries:
                return {"total": 0, "avg_confidence_gain": 0, "compliance_rate": 0}

            total = len(entries)
            avg_gain = sum(e.confidence_after - e.confidence_before for e in entries) / total
            compliance_checks = sum(
                sum(e.constitutional_compliance.values()) / len(e.constitutional_compliance)
                for e in entries if e.constitutional_compliance
            )
            compliance_rate = compliance_checks / total if total > 0 else 0

            return {
                "total_reflections": total,
                "avg_confidence_gain": avg_gain,
                "constitutional_compliance_rate": compliance_rate,
                "by_depth": {
                    depth.value: sum(1 for e in entries if e.depth == depth)
                    for depth in ReflectionDepth
                },
                "by_trigger": {
                    trigger.value: sum(1 for e in entries if e.trigger == trigger)
                    for trigger in ReflectionTrigger
                }
            }

    def get_cross_agent_insights(self, agent_ids: List[str]) -> Dict:
        all_entries = []
        for agent_id in agent_ids:
            all_entries.extend(self.reflection_history.get(agent_id, []))

        if not all_entries:
            return {}

        common_issues = defaultdict(int)
        for entry in all_entries:
            for action in entry.action_items:
                common_issues[action.get("dimension", "general")] += 1

        return {
            "total_reflections": len(all_entries),
            "common_improvement_areas": dict(sorted(common_issues.items(), key=lambda x: -x[1])[:10]),
            "agents_analyzed": len(agent_ids)
        }

    def export_reflections(self, agent_id: str, format: str = "json") -> str:
        entries = self.get_reflection_history(agent_id)

        if format == "json":
            return json.dumps([asdict(e) for e in entries], indent=2, default=str)
        elif format == "markdown":
            lines = [f"# Reflection History: {agent_id}\n"]
            for e in entries:
                lines.append(f"## {e.timestamp} - Task: {e.task_id}")
                lines.append(f"**Trigger**: {e.trigger.value}")
                lines.append(f"**Depth**: {e.depth.value}")
                lines.append(f"**What went well**: {e.what_went_well}")
                lines.append(f"**Improvements**: {e.what_could_improve}")
                lines.append(f"**Key Learning**: {e.key_learning}")
                lines.append("")
            return "\n".join(lines)
        else:
            raise ValueError(f"Unsupported format: {format}")


def create_reflection_engine(storage_path: str = "swarm/reflections") -> SelfReflectionEngine:
    return SelfReflectionEngine(storage_path)


def integrate_reflection_with_fsm(fsm, reflection_engine: SelfReflectionEngine):
    original_transition = fsm.transition

    def wrapped_transition(new_state, reason="", task=None):
        old_state = fsm.state
        result = original_transition(new_state, reason, task)

        if new_state == "APPROVED" and old_state == "REVIEW_PENDING":
            reflection_engine.trigger_reflection(
                agent_id=fsm.agent_id,
                task_id=task or fsm.current_task,
                trigger=ReflectionTrigger.TASK_COMPLETION,
                depth=ReflectionDepth.STANDARD,
                context={
                    "task_spec": getattr(fsm, "current_task_spec", {}),
                    "verdict": {"verdict": "PASS", "scores": {}},
                    "expected_pass": True
                }
            )
        elif new_state == "REJECTED" and old_state == "REVIEW_PENDING":
            reflection_engine.trigger_reflection(
                agent_id=fsm.agent_id,
                task_id=task or fsm.current_task,
                trigger=ReflectionTrigger.ERROR_ENCOUNTERED,
                depth=ReflectionDepth.DEEP,
                context={
                    "task_spec": getattr(fsm, "current_task_spec", {}),
                    "verdict": {"verdict": "FAIL", "scores": {}},
                    "expected_pass": True
                }
            )

        return result

    return wrapped_transition
"""
Metrics Plugin - Collects task metrics (counts, durations, error rates).
"""
import time
from typing import Any, Dict, Optional

from swarm.plugins.base import BasePlugin, PluginMeta


class MetricsPlugin(BasePlugin):
    """Collects basic task metrics exposed via get_metrics()."""

    def __init__(self, meta: Optional[PluginMeta] = None):
        super().__init__(meta or PluginMeta(
            name="metrics",
            version="1.0.0",
            author="swarm-core",
            description="Collects task metrics",
            priority=20,
        ))
        self._task_starts: Dict[str, float] = {}
        self._completed: int = 0
        self._errors: int = 0
        self._total_duration: float = 0.0

    def on_task_start(self, task_id: str, task_data: Dict[str, Any]) -> None:
        self._task_starts[task_id] = time.time()

    def on_task_complete(self, task_id: str, result: Any) -> None:
        self._completed += 1
        start = self._task_starts.pop(task_id, None)
        if start is not None:
            self._total_duration += time.time() - start

    def on_error(self, task_id: str, error: Exception) -> None:
        self._errors += 1
        self._task_starts.pop(task_id, None)

    def get_metrics(self) -> Dict[str, Any]:
        total = self._completed + self._errors
        avg = self._total_duration / self._completed if self._completed else 0.0
        return {
            "tasks_started": total,
            "tasks_completed": self._completed,
            "tasks_errored": self._errors,
            "total_duration": round(self._total_duration, 4),
            "avg_duration": round(avg, 4),
            "error_rate": round(self._errors / total, 4) if total else 0.0,
        }

    def reset(self) -> None:
        """Reset all counters."""
        self._task_starts.clear()
        self._completed = 0
        self._errors = 0
        self._total_duration = 0.0

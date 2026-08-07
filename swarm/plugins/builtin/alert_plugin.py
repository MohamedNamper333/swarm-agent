"""
Alert Plugin - Triggers alerts on task errors.
"""
import logging
import time
from typing import Any, Callable, Dict, List, Optional

from swarm.plugins.base import BasePlugin, PluginMeta

logger = logging.getLogger(__name__)


class AlertPlugin(BasePlugin):
    """Fires registered callbacks when tasks error out."""

    def __init__(self, meta: Optional[PluginMeta] = None):
        super().__init__(meta or PluginMeta(
            name="alert",
            version="1.0.0",
            author="swarm-core",
            description="Triggers alerts on task errors",
            priority=90,
        ))
        self._callbacks: List[Callable[[str, str], None]] = []
        self._alerts: List[Dict[str, Any]] = []

    def register_callback(self, cb: Callable[[str, str], None]) -> None:
        """Register a callback(task_id, error_msg)."""
        self._callbacks.append(cb)

    def on_error(self, task_id: str, error: Exception) -> None:
        error_msg = str(error)
        alert = {
            "task_id": task_id,
            "error": error_msg,
            "ts": time.time(),
            "callbacks_fired": 0,
        }
        for cb in self._callbacks:
            try:
                cb(task_id, error_msg)
                alert["callbacks_fired"] += 1
            except Exception as exc:
                logger.error("Alert callback failed: %s", exc)
        self._alerts.append(alert)
        logger.warning("[AlertPlugin] Alert fired for task %s: %s", task_id, error_msg)

    def get_alerts(self) -> List[Dict[str, Any]]:
        return list(self._alerts)

    def get_alert_count(self) -> int:
        return len(self._alerts)

    def clear_alerts(self) -> None:
        self._alerts.clear()

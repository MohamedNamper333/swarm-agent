"""
Logging Plugin - Logs task lifecycle events (start, complete, error).
"""
import logging
import time
from typing import Any, Dict, List, Optional

from swarm.plugins.base import BasePlugin, PluginMeta

logger = logging.getLogger(__name__)


class LoggingPlugin(BasePlugin):
    """Logs every hook call with structured context."""

    def __init__(self, meta: Optional[PluginMeta] = None):
        super().__init__(meta or PluginMeta(
            name="logging",
            version="1.0.0",
            author="swarm-core",
            description="Logs task lifecycle events",
            priority=10,
        ))
        self._events: List[Dict[str, Any]] = []

    def on_init(self) -> None:
        super().on_init()
        logger.info("LoggingPlugin v%s ready", self.meta.version)

    def on_task_start(self, task_id: str, task_data: Dict[str, Any]) -> None:
        event = {"event": "task_start", "task_id": task_id, "ts": time.time()}
        self._events.append(event)
        logger.info("[LoggingPlugin] Task START: %s", task_id)

    def on_task_complete(self, task_id: str, result: Any) -> None:
        event = {"event": "task_complete", "task_id": task_id, "ts": time.time()}
        self._events.append(event)
        logger.info("[LoggingPlugin] Task COMPLETE: %s", task_id)

    def on_error(self, task_id: str, error: Exception) -> None:
        event = {
            "event": "error",
            "task_id": task_id,
            "error": str(error),
            "ts": time.time(),
        }
        self._events.append(event)
        logger.error("[LoggingPlugin] Task ERROR: %s – %s", task_id, error)

    def on_shutdown(self) -> None:
        logger.info("[LoggingPlugin] Shutting down (%d events recorded)", len(self._events))
        super().on_shutdown()

    def get_events(self) -> List[Dict[str, Any]]:
        """Return all recorded events."""
        return list(self._events)

    def get_event_count(self) -> int:
        return len(self._events)

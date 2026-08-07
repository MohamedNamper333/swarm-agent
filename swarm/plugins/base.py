"""
Base Plugin Class - Abstract base for all Swarm plugins.
Plugins extend swarm functionality via hooks: on_init, on_task_start,
on_task_complete, on_error, on_shutdown.
"""
import abc
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class PluginMeta:
    """Metadata for a plugin, read from YAML or set by subclass."""
    name: str
    version: str = "0.1.0"
    author: str = "unknown"
    description: str = ""
    enabled: bool = True
    priority: int = 100  # lower = runs first
    dependencies: List[str] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)


class BasePlugin(abc.ABC):
    """
    Abstract base class for all swarm plugins.
    Subclass and implement any combination of the hook methods.
    """

    def __init__(self, meta: Optional[PluginMeta] = None):
        self.meta = meta or PluginMeta(name=self.__class__.__name__)
        self._initialized = False
        logger.info("Plugin '%s' v%s created", self.meta.name, self.meta.version)

    # ------------------------------------------------------------------
    # Lifecycle hooks (override as needed)
    # ------------------------------------------------------------------

    def on_init(self) -> None:
        """Called once when the plugin is first loaded."""
        self._initialized = True
        logger.info("Plugin '%s' initialized", self.meta.name)

    def on_task_start(self, task_id: str, task_data: Dict[str, Any]) -> None:
        """Called before a task begins execution."""
        pass

    def on_task_complete(self, task_id: str, result: Any) -> None:
        """Called after a task completes successfully."""
        pass

    def on_error(self, task_id: str, error: Exception) -> None:
        """Called when a task raises an exception."""
        pass

    def on_shutdown(self) -> None:
        """Called once when the plugin manager shuts down."""
        logger.info("Plugin '%s' shut down", self.meta.name)

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------

    def get_config(self, key: str, default: Any = None) -> Any:
        return self.meta.config.get(key, default)

    @property
    def name(self) -> str:
        return self.meta.name

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    def __repr__(self) -> str:
        return f"<Plugin {self.meta.name} v{self.meta.version} enabled={self.meta.enabled}>"

"""
Plugin Loader Module - Discovery, loading, validation, and lifecycle management.
Discovers plugins from directories and YAML configs, loads them as BasePlugin
instances, and manages their lifecycle hooks.
"""
import importlib
import importlib.util
import logging
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Type
from dataclasses import dataclass, field
from datetime import datetime, timezone

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore

from swarm.plugins.base import BasePlugin, PluginMeta

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default paths
# ---------------------------------------------------------------------------

_DEFAULT_PLUGIN_DIRS = [
    Path("swarm/plugins/builtin"),
    Path("plugins"),
]

_DEFAULT_TEMPLATE_DIR = Path("templates")

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class PluginEntry:
    """Tracks a loaded plugin and its state."""
    name: str
    plugin: BasePlugin
    loaded_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    enabled: bool = True
    error: Optional[str] = None


@dataclass
class PluginStats:
    """Aggregate statistics for plugin manager."""
    total_loaded: int = 0
    total_enabled: int = 0
    total_disabled: int = 0
    total_errors: int = 0
    hooks_fired: int = 0
    last_event: str = ""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_plugin_from_module_path(module_path: str, class_name: str) -> Optional[Type[BasePlugin]]:
    """
    Dynamically import a plugin class from a dotted module path.
    e.g. 'swarm.plugins.builtin.logging_plugin' + 'LoggingPlugin'
    """
    try:
        mod = importlib.import_module(module_path)
        cls = getattr(mod, class_name, None)
        if cls and isinstance(cls, type) and issubclass(cls, BasePlugin):
            return cls  # type: ignore[return-value]
        logger.warning("Class '%s' in '%s' is not a BasePlugin subclass", class_name, module_path)
    except Exception as exc:
        logger.error("Failed to import %s.%s: %s", module_path, class_name, exc)
    return None


def load_plugin_from_file(file_path: Path) -> Optional[Type[BasePlugin]]:
    """
    Load a plugin from a .py file by looking for a BasePlugin subclass.
    """
    try:
        spec = importlib.util.spec_from_file_location(file_path.stem, str(file_path))
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            sys.modules[file_path.stem] = mod
            spec.loader.exec_module(mod)  # type: ignore[union-attr]
            for attr_name in dir(mod):
                obj = getattr(mod, attr_name)
                if (
                    isinstance(obj, type)
                    and issubclass(obj, BasePlugin)
                    and obj is not BasePlugin
                ):
                    return obj
    except Exception as exc:
        logger.error("Failed to load plugin from %s: %s", file_path, exc)
    return None


def _parse_yaml_plugin(yaml_path: Path) -> Optional[Dict[str, Any]]:
    """
    Parse a YAML plugin descriptor. Returns dict with keys:
    name, module_path, class_name, version, enabled, priority, dependencies, config.
    """
    if yaml is None:
        logger.warning("PyYAML not installed; cannot parse %s", yaml_path)
        return None
    try:
        with open(yaml_path, "r") as fh:
            data = yaml.safe_load(fh)
        if not isinstance(data, dict):
            logger.warning("YAML plugin file %s did not parse to a dict", yaml_path)
            return None
        return data
    except Exception as exc:
        logger.error("Failed to parse YAML plugin %s: %s", yaml_path, exc)
    return None


# ---------------------------------------------------------------------------
# PluginLoader  –  low-level loading
# ---------------------------------------------------------------------------

class PluginLoader:
    """
    Responsible for discovering and instantiating plugin classes
    from Python modules and YAML descriptors.
    """

    def __init__(self, plugin_dirs: Optional[List[Path]] = None):
        self.plugin_dirs: List[Path] = plugin_dirs or list(_DEFAULT_PLUGIN_DIRS)
        for d in self.plugin_dirs:
            d.mkdir(parents=True, exist_ok=True)

    # ----- discovery ----------------------------------------------------------

    def discover_py_files(self) -> List[Path]:
        """Return all .py files in plugin directories (excluding __init__)."""
        files: List[Path] = []
        for d in self.plugin_dirs:
            if d.exists():
                files.extend(
                    sorted(f for f in d.glob("*.py") if f.name != "__init__.py")
                )
        return files

    def discover_yaml_files(self) -> List[Path]:
        """Return all .yaml/.yml files in plugin directories and template dir."""
        files: List[Path] = []
        for d in self.plugin_dirs:
            if d.exists():
                files.extend(sorted(d.glob("*.yaml")))
                files.extend(sorted(d.glob("*.yml")))
        tpl = _DEFAULT_TEMPLATE_DIR
        if tpl.exists():
            files.extend(sorted(tpl.glob("*.yaml")))
            files.extend(sorted(tpl.glob("*.yml")))
        return files

    # ----- instantiation ------------------------------------------------------

    def load_class_from_py(self, path: Path) -> Optional[Type[BasePlugin]]:
        return load_plugin_from_file(path)

    def load_class_from_yaml(self, yaml_path: Path) -> Optional[Type[BasePlugin]]:
        data = _parse_yaml_plugin(yaml_path)
        if data is None:
            return None
        module_path = data.get("module_path") or data.get("module")
        class_name = data.get("class_name") or data.get("class")
        if not module_path or not class_name:
            logger.warning("YAML %s missing module_path or class_name", yaml_path)
            return None
        return load_plugin_from_module_path(module_path, class_name)

    def instantiate(self, cls: Type[BasePlugin], meta: Optional[PluginMeta] = None) -> Optional[BasePlugin]:
        try:
            plugin = cls(meta=meta)
            return plugin
        except Exception as exc:
            logger.error("Failed to instantiate %s: %s", cls.__name__, exc)
        return None


# ---------------------------------------------------------------------------
# PluginManager  –  high-level lifecycle management
# ---------------------------------------------------------------------------

class PluginManager:
    """
    Manages loading, enabling/disabling, hook firing, and stats for plugins.
    Thread-safe.
    """

    def __init__(self, plugin_dirs: Optional[List[Path]] = None):
        self.loader = PluginLoader(plugin_dirs)
        self._plugins: Dict[str, PluginEntry] = {}
        self._lock = threading.RLock()
        self.stats = PluginStats()

    # ----- public API ---------------------------------------------------------

    def load_all(self) -> int:
        """Discover and load every available plugin. Returns count loaded."""
        loaded = 0
        # Python files
        for py_file in self.loader.discover_py_files():
            self._load_from_py(py_file)
        # YAML descriptors
        for yml in self.loader.discover_yaml_files():
            self._load_from_yaml(yml)
        with self._lock:
            loaded = len(self._plugins)
            self.stats.total_loaded = loaded
            self.stats.total_enabled = sum(1 for e in self._plugins.values() if e.enabled)
            self.stats.total_disabled = loaded - self.stats.total_enabled
        logger.info("Loaded %d plugins total", loaded)
        return loaded

    def load_plugin(self, plugin: BasePlugin) -> None:
        """Register an already-instantiated plugin."""
        with self._lock:
            entry = PluginEntry(name=plugin.name, plugin=plugin)
            self._plugins[plugin.name] = entry
            try:
                plugin.on_init()
                entry.enabled = plugin.meta.enabled
            except Exception as exc:
                entry.error = str(exc)
                entry.enabled = False
                self.stats.total_errors += 1
                logger.error("Plugin '%s' on_init failed: %s", plugin.name, exc)
            self._refresh_stats()

    def get_plugin(self, name: str) -> Optional[BasePlugin]:
        with self._lock:
            entry = self._plugins.get(name)
            return entry.plugin if entry else None

    def list_plugins(self) -> List[str]:
        with self._lock:
            return list(self._plugins.keys())

    def list_enabled(self) -> List[str]:
        with self._lock:
            return [n for n, e in self._plugins.items() if e.enabled]

    def enable(self, name: str) -> bool:
        with self._lock:
            entry = self._plugins.get(name)
            if entry:
                entry.enabled = True
                entry.plugin.meta.enabled = True
                self._refresh_stats()
                return True
        return False

    def disable(self, name: str) -> bool:
        with self._lock:
            entry = self._plugins.get(name)
            if entry:
                entry.enabled = False
                entry.plugin.meta.enabled = False
                self._refresh_stats()
                return True
        return False

    def unload(self, name: str) -> bool:
        with self._lock:
            entry = self._plugins.pop(name, None)
            if entry:
                try:
                    entry.plugin.on_shutdown()
                except Exception:
                    pass
                self._refresh_stats()
                return True
        return False

    def shutdown_all(self) -> None:
        with self._lock:
            for entry in self._plugins.values():
                try:
                    entry.plugin.on_shutdown()
                except Exception as exc:
                    logger.error("Plugin '%s' shutdown error: %s", entry.name, exc)
            self._plugins.clear()
            self._refresh_stats()
        logger.info("All plugins shut down")

    # ----- hook dispatchers ---------------------------------------------------

    def fire_task_start(self, task_id: str, task_data: Dict[str, Any]) -> None:
        self._fire("on_task_start", task_id, task_data)

    def fire_task_complete(self, task_id: str, result: Any) -> None:
        self._fire("on_task_complete", task_id, result)

    def fire_error(self, task_id: str, error: Exception) -> None:
        self._fire("on_error", task_id, error)

    # ----- stats --------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_loaded": self.stats.total_loaded,
                "total_enabled": self.stats.total_enabled,
                "total_disabled": self.stats.total_disabled,
                "total_errors": self.stats.total_errors,
                "hooks_fired": self.stats.hooks_fired,
                "plugins": {
                    n: {"enabled": e.enabled, "error": e.error, "loaded_at": e.loaded_at}
                    for n, e in self._plugins.items()
                },
            }

    # ----- internal -----------------------------------------------------------

    def _fire(self, hook: str, *args: Any, **kwargs: Any) -> None:
        with self._lock:
            entries = [
                e for e in self._plugins.values()
                if e.enabled and hasattr(e.plugin, hook)
            ]
        for entry in entries:
            try:
                fn = getattr(entry.plugin, hook)
                fn(*args, **kwargs)
                with self._lock:
                    self.stats.hooks_fired += 1
                    self.stats.last_event = f"{hook}@{entry.name}"
            except Exception as exc:
                logger.error("Hook '%s' on plugin '%s' failed: %s", hook, entry.name, exc)
                with self._lock:
                    entry.error = str(exc)
                    self.stats.total_errors += 1

    def _load_from_py(self, path: Path) -> None:
        cls = self.loader.load_class_from_py(path)
        if cls:
            plugin = self.loader.instantiate(cls)
            if plugin:
                self.load_plugin(plugin)

    def _load_from_yaml(self, path: Path) -> None:
        cls = self.loader.load_class_from_yaml(path)
        if cls:
            data = _parse_yaml_plugin(path) or {}
            meta = PluginMeta(
                name=data.get("name", path.stem),
                version=data.get("version", "0.1.0"),
                author=data.get("author", "unknown"),
                description=data.get("description", ""),
                enabled=data.get("enabled", True),
                priority=data.get("priority", 100),
                dependencies=data.get("dependencies", []),
                config=data.get("config", {}),
            )
            plugin = self.loader.instantiate(cls, meta=meta)
            if plugin:
                self.load_plugin(plugin)

    def _refresh_stats(self) -> None:
        self.stats.total_loaded = len(self._plugins)
        self.stats.total_enabled = sum(1 for e in self._plugins.values() if e.enabled)
        self.stats.total_disabled = self.stats.total_loaded - self.stats.total_enabled
        self.stats.total_errors = sum(1 for e in self._plugins.values() if e.error)


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def load_plugin(plugin: BasePlugin, dirs: Optional[List[Path]] = None) -> PluginManager:
    """Convenience: create a manager, register one plugin, return manager."""
    mgr = PluginManager(plugin_dirs=dirs)
    mgr.load_plugin(plugin)
    return mgr


def load_plugins_from_dir(directory: Path) -> PluginManager:
    """Convenience: create a manager for a single directory, load all."""
    mgr = PluginManager(plugin_dirs=[directory])
    mgr.load_all()
    return mgr

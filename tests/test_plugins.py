"""
Tests for the Swarm Plugin System.
Tests cover BasePlugin, PluginMeta, PluginLoader, PluginManager, and PluginDashboard.
"""
import tempfile
from pathlib import Path
from unittest import TestCase, main
from unittest.mock import MagicMock

import sys
import os

# Add the project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from swarm.plugins.base import BasePlugin, PluginMeta
from swarm.plugins.loader import (
    PluginLoader,
    PluginManager,
    load_plugin,
    load_plugins_from_dir,
)
from swarm.plugins.dashboard import PluginDashboard, create_dashboard


# ---------------------------------------------------------------------------
# Test Plugins
# ---------------------------------------------------------------------------

class DummyPlugin(BasePlugin):
    """A simple test plugin."""
    def __init__(self, meta=None):
        super().__init__(meta)
        self.init_called = False
        self.start_calls = []
        self.complete_calls = []
        self.error_calls = []
        self.shutdown_called = False

    def on_init(self):
        super().on_init()
        self.init_called = True

    def on_task_start(self, task_id, task_data):
        self.start_calls.append(task_id)

    def on_task_complete(self, task_id, result):
        self.complete_calls.append((task_id, result))

    def on_error(self, task_id, error):
        self.error_calls.append((task_id, error))

    def on_shutdown(self):
        super().on_shutdown()
        self.shutdown_called = True


class FailingInitPlugin(BasePlugin):
    """Plugin that raises on init."""
    def on_init(self):
        raise RuntimeError("Init failed!")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestPluginMeta(TestCase):
    def test_default_values(self):
        meta = PluginMeta(name="test")
        self.assertEqual(meta.name, "test")
        self.assertEqual(meta.version, "0.1.0")
        self.assertEqual(meta.author, "unknown")
        self.assertTrue(meta.enabled)
        self.assertEqual(meta.priority, 100)
        self.assertEqual(meta.dependencies, [])
        self.assertEqual(meta.config, {})

    def test_custom_values(self):
        meta = PluginMeta(
            name="custom",
            version="2.0.0",
            author="tester",
            description="A test",
            enabled=False,
            priority=10,
            dependencies=["dep1"],
            config={"key": "val"},
        )
        self.assertEqual(meta.name, "custom")
        self.assertEqual(meta.version, "2.0.0")
        self.assertEqual(meta.author, "tester")
        self.assertFalse(meta.enabled)
        self.assertEqual(meta.priority, 10)
        self.assertEqual(meta.dependencies, ["dep1"])
        self.assertEqual(meta.config, {"key": "val"})


class TestBasePlugin(TestCase):
    def test_init_default_meta(self):
        plugin = DummyPlugin()
        self.assertEqual(plugin.name, "DummyPlugin")
        self.assertFalse(plugin.is_initialized)

    def test_init_custom_meta(self):
        meta = PluginMeta(name="custom", version="1.2.3")
        plugin = DummyPlugin(meta=meta)
        self.assertEqual(plugin.name, "custom")
        self.assertEqual(plugin.meta.version, "1.2.3")

    def test_on_init(self):
        plugin = DummyPlugin()
        plugin.on_init()
        self.assertTrue(plugin.is_initialized)
        self.assertTrue(plugin.init_called)

    def test_lifecycle_hooks(self):
        plugin = DummyPlugin()
        plugin.on_task_start("t1", {"data": "x"})
        plugin.on_task_complete("t1", "done")
        plugin.on_error("t2", Exception("fail"))
        plugin.on_shutdown()
        self.assertEqual(plugin.start_calls, ["t1"])
        self.assertEqual(plugin.complete_calls, [("t1", "done")])
        self.assertEqual(plugin.error_calls[0][0], "t2")
        self.assertTrue(plugin.shutdown_called)

    def test_get_config(self):
        meta = PluginMeta(name="cfg", config={"timeout": 30})
        plugin = DummyPlugin(meta=meta)
        self.assertEqual(plugin.get_config("timeout"), 30)
        self.assertIsNone(plugin.get_config("missing"))
        self.assertEqual(plugin.get_config("missing", "default"), "default")

    def test_repr(self):
        plugin = DummyPlugin()
        self.assertIn("DummyPlugin", repr(plugin))
        self.assertIn("0.1.0", repr(plugin))


class TestPluginLoader(TestCase):
    def test_discover_py_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create dummy files
            (Path(tmpdir) / "test_plugin.py").touch()
            (Path(tmpdir) / "__init__.py").touch()
            loader = PluginLoader(plugin_dirs=[Path(tmpdir)])
            files = loader.discover_py_files()
            self.assertEqual(len(files), 1)
            self.assertEqual(files[0].name, "test_plugin.py")

    def test_load_class_from_yaml_missing_module(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_file = Path(tmpdir) / "bad.yaml"
            yaml_file.write_text("name: bad\n")
            loader = PluginLoader(plugin_dirs=[Path(tmpdir)])
            result = loader.load_class_from_yaml(yaml_file)
            self.assertIsNone(result)

    def test_instantiate(self):
        loader = PluginLoader()
        plugin = loader.instantiate(DummyPlugin)
        self.assertIsNotNone(plugin)
        self.assertIsInstance(plugin, DummyPlugin)


class TestPluginManager(TestCase):
    def test_load_plugin(self):
        manager = PluginManager()
        plugin = DummyPlugin()
        manager.load_plugin(plugin)
        self.assertIn("DummyPlugin", manager.list_plugins())
        self.assertTrue(plugin.init_called)

    def test_get_plugin(self):
        manager = PluginManager()
        plugin = DummyPlugin()
        manager.load_plugin(plugin)
        self.assertIs(manager.get_plugin("DummyPlugin"), plugin)
        self.assertIsNone(manager.get_plugin("nonexistent"))

    def test_enable_disable(self):
        manager = PluginManager()
        plugin = DummyPlugin()
        manager.load_plugin(plugin)
        self.assertTrue(manager.disable("DummyPlugin"))
        self.assertFalse(plugin.meta.enabled)
        self.assertTrue(manager.enable("DummyPlugin"))
        self.assertTrue(plugin.meta.enabled)
        self.assertFalse(manager.disable("nonexistent"))
        self.assertFalse(manager.enable("nonexistent"))

    def test_unload(self):
        manager = PluginManager()
        plugin = DummyPlugin()
        manager.load_plugin(plugin)
        self.assertTrue(manager.unload("DummyPlugin"))
        self.assertIsNone(manager.get_plugin("DummyPlugin"))
        self.assertTrue(plugin.shutdown_called)
        self.assertFalse(manager.unload("nonexistent"))

    def test_shutdown_all(self):
        manager = PluginManager()
        p1 = DummyPlugin(meta=PluginMeta(name="p1"))
        p2 = DummyPlugin(meta=PluginMeta(name="p2"))
        manager.load_plugin(p1)
        manager.load_plugin(p2)
        manager.shutdown_all()
        self.assertEqual(manager.list_plugins(), [])
        self.assertTrue(p1.shutdown_called)
        self.assertTrue(p2.shutdown_called)

    def test_fire_hooks(self):
        manager = PluginManager()
        plugin = DummyPlugin()
        manager.load_plugin(plugin)
        manager.fire_task_start("t1", {"x": 1})
        manager.fire_task_complete("t1", "ok")
        manager.fire_error("t2", Exception("boom"))
        self.assertEqual(plugin.start_calls, ["t1"])
        self.assertEqual(plugin.complete_calls, [("t1", "ok")])
        self.assertEqual(len(plugin.error_calls), 1)

    def test_failing_init(self):
        manager = PluginManager()
        plugin = FailingInitPlugin()
        manager.load_plugin(plugin)
        self.assertIn(plugin.name, manager.list_plugins())
        self.assertEqual(manager.stats.total_errors, 1)

    def test_get_stats(self):
        manager = PluginManager()
        plugin = DummyPlugin()
        manager.load_plugin(plugin)
        stats = manager.get_stats()
        self.assertEqual(stats["total_loaded"], 1)
        self.assertEqual(stats["total_enabled"], 1)
        self.assertEqual(stats["total_disabled"], 0)
        self.assertIn("DummyPlugin", stats["plugins"])

    def test_list_enabled(self):
        manager = PluginManager()
        p1 = DummyPlugin(meta=PluginMeta(name="p1"))
        p2 = DummyPlugin(meta=PluginMeta(name="p2", enabled=False))
        manager.load_plugin(p1)
        manager.load_plugin(p2)
        self.assertEqual(manager.list_enabled(), ["p1"])


class TestConvenienceFunctions(TestCase):
    def test_load_plugin(self):
        plugin = DummyPlugin()
        manager = load_plugin(plugin)
        self.assertIn("DummyPlugin", manager.list_plugins())

    def test_load_plugins_from_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = load_plugins_from_dir(Path(tmpdir))
            self.assertEqual(manager.list_plugins(), [])


class TestPluginDashboard(TestCase):
    def setUp(self):
        self.manager = PluginManager()
        self.plugin = DummyPlugin()
        self.manager.load_plugin(self.plugin)
        self.dashboard = PluginDashboard(self.manager)

    def test_get_status(self):
        status = self.dashboard.get_status()
        self.assertEqual(status["total_loaded"], 1)
        self.assertIn("DummyPlugin", status["plugins"])

    def test_format_status(self):
        text = self.dashboard.format_status()
        self.assertIn("PLUGIN DASHBOARD", text)
        self.assertIn("DummyPlugin", text)

    def test_enable_disable_plugin(self):
        self.dashboard.disable_plugin("DummyPlugin")
        self.assertFalse(self.plugin.meta.enabled)
        self.dashboard.enable_plugin("DummyPlugin")
        self.assertTrue(self.plugin.meta.enabled)

    def test_to_json(self):
        import json
        json_str = self.dashboard.to_json()
        data = json.loads(json_str)
        self.assertEqual(data["total_loaded"], 1)

    def test_create_dashboard(self):
        dash = create_dashboard(self.manager)
        self.assertIsInstance(dash, PluginDashboard)


if __name__ == "__main__":
    main()

"""
Swarm Plugins - Discovery, loading, and lifecycle management.
"""
from swarm.plugins.loader import PluginManager, PluginLoader, load_plugin, load_plugins_from_dir
from swarm.plugins.base import BasePlugin, PluginMeta

__all__ = [
    "PluginManager",
    "PluginLoader",
    "load_plugin",
    "load_plugins_from_dir",
    "BasePlugin",
    "PluginMeta",
]

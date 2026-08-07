"""
Plugin Dashboard - Visual status dashboard for the Swarm plugin system.
Displays plugin status, statistics, and allows enabling/disabling plugins.
"""
import json
import os
import time
from pathlib import Path
from typing import Dict, Any, Optional

from swarm.plugins.loader import PluginManager


class PluginDashboard:
    """Dashboard for viewing and managing plugin status."""

    def __init__(self, manager: PluginManager):
        self.manager = manager

    def get_status(self) -> Dict[str, Any]:
        """Get the current status of all plugins."""
        return self.manager.get_stats()

    def format_status(self) -> str:
        """Format status as readable text."""
        stats = self.get_status()
        lines = [
            "=" * 60,
            "  SWARM PLUGIN DASHBOARD",
            "=" * 60,
            f"  Total Loaded:  {stats['total_loaded']}",
            f"  Enabled:       {stats['total_enabled']}",
            f"  Disabled:      {stats['total_disabled']}",
            f"  Errors:        {stats['total_errors']}",
            f"  Hooks Fired:   {stats['hooks_fired']}",
            f"  Last Event:    {stats['last_event']}",
            "-" * 60,
            "  PLUGIN LIST:",
        ]
        for name, info in stats.get('plugins', {}).items():
            status = 'ENABLED' if info['enabled'] else 'DISABLED'
            error_str = f" ERROR: {info['error']}" if info.get('error') else ""
            lines.append(f"    - {name} [{status}]{error_str}")
        lines.append("=" * 60)
        return "\n".join(lines)

    def enable_plugin(self, name: str) -> bool:
        """Enable a plugin by name."""
        return self.manager.enable(name)

    def disable_plugin(self, name: str) -> bool:
        """Disable a plugin by name."""
        return self.manager.disable(name)

    def unload_plugin(self, name: str) -> bool:
        """Unload a plugin by name."""
        return self.manager.unload(name)

    def to_json(self) -> str:
        """Export status as JSON."""
        return json.dumps(self.get_status(), indent=2)


def create_dashboard(manager: PluginManager) -> PluginDashboard:
    """Create a PluginDashboard for the given manager."""
    return PluginDashboard(manager)

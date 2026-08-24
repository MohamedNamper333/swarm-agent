"""
Execution Sandboxes - Secure, isolated code execution environments.
"""

from .gvisor_sandbox import (
    GVisorConfig,
    GVisorSandbox,
    create_gvisor_sandbox,
)

from .firecracker_sandbox import (
    FirecrackerConfig,
    FirecrackerSandbox,
    create_firecracker_sandbox,
)

from .network_enforcement import (
    NetworkMode,
    NetworkPolicy,
    NetworkRule,
    NetworkPolicyEngine,
    NetworkIsolationEnforcer,
    NetworkNamespaceManager,
    create_network_enforcer,
    create_default_network_policy,
)

from .fs_enforcement import (
    FilesystemIsolationEnforcer,
    FilesystemPolicy,
    MountRule,
    create_filesystem_enforcer,
)

# Memory access types are from the enterprise memory module - lazy import
import importlib
from typing import Any, Dict, Optional

class LazySandboxImports:
    """Lazy loader for sandbox dependencies."""
    
    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._module_cache: Dict[str, Any] = {}
    
    def _get_module(self, module_path: str):
        import importlib
        if module_path not in self._module_cache:
            self._module_cache[module_path] = importlib.import_module(module_path)
        return self._module_cache[module_path]
    
    def _get_attr(self, module_path: str, attr: str):
        module = self._get_module(module_path)
        return getattr(module, attr)
    
    def get_memory_access_policy(self):
        return self._get_attr("swarm.enterprise.core.memory", "MemoryAccessPolicy")
    
    def get_memory_access_level(self):
        return self._get_attr("swarm.enterprise.core.memory", "MemoryAccessLevel")


_lazy = LazySandboxImports()


def get_memory_access_policy():
    return _lazy.get_memory_access_policy()


def get_memory_access_level():
    return _lazy.get_memory_access_level()


# Memory access types are from the enterprise memory module
MemoryAccessPolicy = get_memory_access_policy()
MemoryAccessLevel = get_memory_access_level()


from .gvisor_sandbox import (
    GVisorConfig,
    GVisorSandbox,
    create_gvisor_sandbox,
)

from .firecracker_sandbox import (
    FirecrackerConfig,
    FirecrackerSandbox,
    create_firecracker_sandbox,
)

from .network_enforcement import (
    NetworkMode,
    NetworkPolicy,
    NetworkRule,
    NetworkPolicyEngine,
    NetworkIsolationEnforcer,
    NetworkNamespaceManager,
    create_network_enforcer,
    create_default_network_policy,
)

from .fs_enforcement import (
    FilesystemIsolationEnforcer,
    FilesystemPolicy,
    MountRule,
    create_filesystem_enforcer,
)

__all__ = [
    # gVisor
    "GVisorConfig",
    "GVisorSandbox",
    "create_gvisor_sandbox",
    # Firecracker
    "FirecrackerConfig",
    "FirecrackerSandbox",
    "create_firecracker_sandbox",
    # Network
    "NetworkMode",
    "NetworkPolicy",
    "NetworkRule",
    "NetworkPolicyEngine",
    "NetworkIsolationEnforcer",
    "NetworkNamespaceManager",
    "create_network_enforcer",
    "create_default_network_policy",
    # Filesystem
    "FilesystemIsolationEnforcer",
    "FilesystemPolicy",
    "MountRule",
    "create_filesystem_enforcer",
    # Memory
    "MemoryAccessPolicy",
    "MemoryAccessLevel",
]

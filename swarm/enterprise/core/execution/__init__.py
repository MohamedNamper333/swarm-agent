"""
Code Execution Sandbox - Secure, isolated code execution environment.
"""

from .sandbox import (
    ExecutionStatus,
    Language,
    ExecutionRequest,
    ExecutionResult,
    SandboxBackend,
    LocalProcessSandbox,
    ExecutionManager,
    create_sandbox,
    create_execution_manager,
)

from .sandboxes import (
    # gVisor
    GVisorConfig,
    GVisorSandbox,
    create_gvisor_sandbox,
    # Firecracker
    FirecrackerConfig,
    FirecrackerSandbox,
    create_firecracker_sandbox,
    # Network
    NetworkMode,
    NetworkPolicy,
    NetworkRule,
    NetworkPolicyEngine,
    NetworkIsolationEnforcer,
    NetworkNamespaceManager,
    create_network_enforcer,
    create_default_network_policy,
    # Filesystem
    FilesystemIsolationEnforcer,
    FilesystemPolicy,
    MountRule,
    MemoryAccessPolicy,
    MemoryAccessLevel,
    create_filesystem_enforcer,
)

__all__ = [
    # Core
    "ExecutionStatus",
    "Language",
    "ExecutionRequest",
    "ExecutionResult",
    "SandboxBackend",
    "LocalProcessSandbox",
    "ExecutionManager",
    "create_sandbox",
    "create_execution_manager",
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
    "MemoryAccessPolicy",
    "MemoryAccessLevel",
    "create_filesystem_enforcer",
]

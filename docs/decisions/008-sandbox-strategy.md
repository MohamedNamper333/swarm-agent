# ADR-008: Sandbox Strategy (Local/gVisor/Firecracker)

## Status
**Accepted** — 2025-08-24

## Context
User code execution requires strong isolation to prevent:
- Container escape
- Network access when not allowed
- Filesystem access outside sandbox
- Resource exhaustion (CPU, memory, processes)

Three isolation levels are needed based on security requirements.

## Decision
Implement three sandbox backends with increasing isolation strength:

| Backend | Isolation | Cold Start | Use Case |
|---------|-----------|------------|----------|
| **LocalProcessSandbox** | Linux namespaces + seccomp + cgroups v2 | <100ms | Development, low-risk |
| **GVisorSandbox** | runsc (user-space kernel) + minimal caps + seccomp | ~200ms | Production default |
| **FirecrackerSandbox** | MicroVM + overlayfs + vsock + jailer | ~2s | High-security, multi-tenant |

### Local Process Sandbox
- `unshare(CLONE_NEWNS | CLONE_NEWNET | CLONE_NEWPID | CLONE_NEWUTS)` via ctypes
- Seccomp filter (default deny, allowlist)
- cgroup v2 limits (memory.max, cpu.max, pids.max)
- Privilege dropping (setuid/setgid to nobody)
- Capability dropping

### gVisor Sandbox
- `runsc` runtime with seccomp profile
- Minimal capabilities (CAP_CHOWN, CAP_DAC_OVERRIDE, CAP_FOWNER, CAP_SETGID, CAP_SETUID)
- Import blocking via `sys.meta_path` hook
- Compiled languages use build + execute pattern (not shell &&)

### Firecracker Sandbox
- MicroVM with jailer cage
- Overlayfs copy-on-write for fast rootfs preparation
- vsock/virtio-serial for stdout/stderr capture
- Loop device and tap interface cleanup

### Implementation Files
- `core/execution/sandbox.py` — LocalProcessSandbox, ExecutionManager
- `core/execution/sandboxes/gvisor_sandbox.py` — GVisorSandbox
- `core/execution/sandboxes/firecracker_sandbox.py` — FirecrackerSandbox
- `core/execution/sandboxes/network_enforcement.py` — Network namespace + iptables
- `core/execution/sandboxes/fs_enforcement.py` — Filesystem overlayfs + quotas
- `core/execution/sandboxes/seccomp_profiles/default.json` — Default seccomp profile

## Consequences

### Positive
- Three isolation levels for different risk profiles
- Sandbox escape tests pass at all levels
- Resource limits enforced via cgroups v2
- Network isolation verified (no outbound when disabled)

### Negative
- Firecracker requires KVM support (bare metal or nested virtualization)
- gVisor adds ~20% CPU overhead
- Namespace creation may require root in some environments
- cgroup v2 requires modern kernels (5.x+)

### Neutral
- Factory function `create_sandbox(type, **kwargs)` selects backend
- CI uses `enable_cgroups=False` (no root in GitHub Actions runners)
- Production MUST use gVisor or Firecracker (never LocalProcessSandbox)

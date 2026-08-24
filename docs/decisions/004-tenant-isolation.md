# ADR-004: Tenant Isolation Strategy

## Status
**Accepted** — 2025-08-24

## Context
Multiple tenants share the same infrastructure. Cross-tenant access must be 100% blocked. Resources include: jobs, memory, cache, budgets, rate limits, audit logs, artifacts, and sandbox executions.

## Decision
Implement tenant isolation at multiple layers:

1. **Resource Ownership**: `TenantIsolationEnforcer` tracks resource ownership
2. **Sandbox Isolation**: Linux namespaces (CLONE_NEWNS, CLONE_NEWNET) + seccomp + cgroups v2
3. **Network Isolation**: Network namespaces + iptables inside namespace
4. **Filesystem Isolation**: Mount namespaces + overlayfs with quota enforcement
5. **Memory Isolation**: Tenant-scoped Memory V2 with trust levels

### Implementation Files
- `core/classification/multi_tenant.py` — TenantRegistry, TenantIsolationEnforcer
- `core/auth/tenants/manager.py` — TenantManager, TenantQuota, TenantFeatures
- `core/execution/sandboxes/` — Sandbox isolation (gVisor, Firecracker)
- `core/execution/sandboxes/network_enforcement.py` — Network namespace + iptables
- `core/execution/sandboxes/fs_enforcement.py` — Filesystem overlayfs + quotas

### Verification Tests
- Cross-tenant resource access returns False (100% blocked)
- Network isolation: no outbound connections when `network_allowed=False`
- Filesystem isolation: `/etc`, `/root`, `/proc` not readable from sandbox
- Process isolation: host PIDs not visible from sandbox

## Consequences

### Positive
- Zero cross-tenant data leakage
- Compliance-ready (SOC2, ISO27001, HIPAA)
- Resource quotas prevent noisy neighbor problems

### Negative
- Namespace creation requires root or user namespace support
- gVisor/Firecracker add cold-start latency (~100ms-2s)
- Filesystem overlays consume additional disk space

### Neutral
- Isolation level configurable per tenant tier (Shared/Dedicated/Isolated)
- Enterprise tier supports dedicated infrastructure (separate clusters)

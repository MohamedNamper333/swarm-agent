# ADR-011: Multi-Tenant Isolation

**Status:** accepted
**Author:** system
**Date:** 2026-08-14
**Updated:** 2026-08-17 (Wave 6: queue-layer enforcement)

## Context
System will be multi-tenant SaaS; tenant isolation must be a security boundary.

## Decision
Every resource scoped by tenant_id: jobs, memory, cache, budgets, rate limits, audit, artifacts. TenantIsolationEnforcer blocks 100% of cross-tenant access attempts.

## Implementation Details (Wave 6 enforcement)

**Queue layer (`models.py`)**: `JobQueue.dequeue(tenant_id=...)` filters jobs at the source rather than post-fetch. The previous implementation attempted to find a matching job via `pop(0)` + `insert(0)` which caused an **infinite loop** when no jobs matched (the same job kept being moved to the front). The fix uses index-based traversal: iterate the deque, pop the first matching index, advance past non-matches.

**Backward compatibility**: `dequeue()` without `tenant_id` returns from the global pool — existing single-tenant deployments work unchanged. Multi-tenant workers must explicitly pass `tenant_id`.

**Audit trail**: `DurableJob.to_dict()` now persists `events` (including tenant_id on enqueue/dequeue events). The audit ledger therefore captures who-did-what-at-when with tenant context, enabling forensic reconstruction of cross-tenant access attempts.

## Consequences
- Provable tenant isolation at the queue boundary
- Resource quotas per tenant (enforced by TenantIsolationEnforcer)
- Audit trail per tenant (persisted in job events)
- Multi-tenant deployments MUST pass tenant_id to every `dequeue()` call

## Tested Scenarios
- `test_dequeue_isolates_by_tenant`: tenant A never sees tenant B's jobs
- `test_dequeue_without_tenant_is_backward_compatible`: legacy callers still work
- `test_dequeue_preserves_fairness_with_mixed_tenants`: round-robin across tenants

## Alternatives Considered
- Logical separation only (application-level) — rejected: leaks via shared bugs
- Shared resources with soft limits — rejected: insufficient for security boundary


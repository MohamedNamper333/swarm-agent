# ADR-009: Durable Job Infrastructure

**Status:** accepted
**Author:** system
**Date:** 2026-08-14
**Updated:** 2026-08-17 (Wave 6: timeout + heartbeat + tenant enforcement)

## Context
Long-running operations (research, video, LLM orchestration) cannot be bound to synchronous HTTP requests.

## Decision
Implement DurableJob with persistent state, retries, cancellation, timeout, resume, dead-letter, heartbeat. Jobs admitted to queue, workers execute asynchronously.

## Implementation Details (Wave 6 enforcement)

**Heartbeat (`worker.py`)**: `_heartbeat_loop()` runs as a daemon thread that scans for stale jobs every `heartbeat_interval_sec`. Uses `wait(timeout=heartbeat_interval_sec)` instead of busy-wait. Performs a final scan on shutdown to fail jobs that died with the worker.

**Timeout (`compensation.py`)**: `_run_with_timeout(fn, args, timeout_ms)` wraps step execution in a `ThreadPoolExecutor(max_workers=1)`. On timeout: cancels the future (best-effort for cooperative cancellation) and raises `StepTimeoutError(step_id, timeout_ms, phase)`. Applied to both `execute()` and `_compensate()` so hanging steps cannot block the workflow indefinitely.

**Topological sort (`compensation.py`)**: Kahn's algorithm (iterative, not recursive) to handle workflow graphs of arbitrary depth without `RecursionError`. Validates that every dependency references an existing step before starting. Detects cycles and raises `ValueError` with the offending cycle path.

**Required keys (`compensation.py`)**: When a step declares `requires=[...]`, the engine validates that every required key is present in the accumulated context before invoking the step. Raises `ValueError` with the available context listing for debugging.

**Event persistence (`models.py`)**: `DurableJob.to_dict()` now serializes the `events` audit log. Without this fix, every serialize → deserialize cycle (e.g., queue → worker) silently dropped the audit history.

**Tenant isolation (`models.py`)**: `JobQueue.dequeue(tenant_id=...)` filters by tenant with index-based traversal. The previous `pop(0)` + reinsert approach caused an infinite loop when no jobs matched the tenant filter.

## Consequences
- Survives worker restarts (heartbeat + final scan)
- Explicit retry/compensation model with hard timeouts
- Horizontal worker scaling
- Workflows with 1000+ steps execute without RecursionError
- Cross-tenant job leakage blocked at queue layer
- Step-level `StepTimeoutError` enables precise compensation routing

## Out of Scope (Stage 3, deferred until distributed backend)
- Dead-letter queue persistence (currently in-memory only)
- Step-level retry policy (workflow-level only)
- Distributed queue backend (Redis)

## Alternatives Considered
- Synchronous with long timeouts (rejected: HTTP timeout limits)
- External workflow engine (Temporal, etc.) (rejected: operational complexity)


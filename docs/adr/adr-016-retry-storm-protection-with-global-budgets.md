# ADR-016: Retry Storm Protection with Global Budgets

**Status:** accepted
**Author:** system
**Date:** 2026-08-14
**Updated:** 2026-08-17 (Wave 6: hard deadline on step timeout)

## Context
Unbounded retries across agents/providers can amplify load during outages.

## Decision
Multi-scope retry budgets: REQUEST, AGENT, PROVIDER, GLOBAL. Each with max_attempts, exponential backoff + jitter, deadline propagation. RetryStormDetector monitors per-minute rates.

## Implementation Details (Wave 6 enforcement)

**Hard deadline on step execution (`compensation.py`)**: The retry budget mechanism is complemented by a hard timeout at the step level. `_run_with_timeout(fn, args, timeout_ms)` wraps both `step.execute_fn` and `step.compensate_fn` calls. If a step hangs past its budget, `StepTimeoutError` is raised — this prevents a single misbehaving step from monopolizing a worker thread or holding a global retry budget slot indefinitely.

**Cooperative cancellation**: On timeout, the executor attempts to cancel the future. The cancellation is best-effort (Python threads cannot be force-killed), but the timeout error propagates immediately so the compensation engine can route around the stuck step.

**Budget interplay**: A `StepTimeoutError` counts as a failed execution attempt, consuming one slot of the per-step retry budget. Once the budget is exhausted, the workflow transitions to FAILED and (when the dead-letter queue is enabled) the job is routed there.

## Consequences
- Prevents cascade failures
- Per-scope budget enforcement (REQUEST, AGENT, PROVIDER, GLOBAL)
- Automatic storm detection
- Step-level hard deadline complements retry budget
- A single hanging step cannot exhaust the entire workflow budget

## Out of Scope (Stage 3, deferred until distributed backend)
- Cross-worker budget coordination (currently per-process)
- Dead-letter queue persistence

## Alternatives Considered
- Unlimited retries (storm risk) — rejected
- Fixed retry count (inflexible) — rejected
- Process-kill on timeout — rejected (unsafe; corrupts shared state)


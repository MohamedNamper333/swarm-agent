# ADR-001: Execution State Machine

**Status:** accepted
**Author:** system
**Date:** 2026-08-14
**Updated:** 2026-08-14

## Context
The system needs a clear execution lifecycle with distinct states for policy decisions vs execution outcomes.

## Decision
Implement ExecutionContext with explicit states: CREATED, QUEUED, RUNNING, SUCCEEDED, FAILED, CANCELLED, REQUIRES_HUMAN_REVIEW. Separate policy_decision from execution_state and final_outcome.

## Consequences
- Clear separation between approval and execution success
- Explicit terminal states prevent ambiguous results
- Human review state is explicit

## Alternatives Considered
- Use simple boolean approved/rejected
- Merge policy and execution states

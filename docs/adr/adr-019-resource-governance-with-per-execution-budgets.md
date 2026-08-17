# ADR-019: Resource Governance with Per-Execution Budgets

**Status:** accepted
**Author:** system
**Date:** 2026-08-14
**Updated:** 2026-08-14

## Context
Unbounded agent execution can exhaust tokens, cost, runtime, agents.

## Decision
ResourceBudget per execution: max_tokens, max_tool_calls, max_runtime, max_cost, max_agents, max_depth. ResourceGovernor enforces global, per-tenant, per-execution limits. Actions: THROTTLE, DENY, TERMINATE, ALERT.

## Consequences
- Prevents resource exhaustion
- Cost predictability
- Recursive execution bounded

## Alternatives Considered
- No limits (risky)
- Global limits only (unfair)

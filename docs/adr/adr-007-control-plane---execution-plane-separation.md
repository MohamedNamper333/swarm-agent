# ADR-007: Control Plane / Execution Plane Separation

**Status:** accepted
**Author:** system
**Date:** 2026-08-14
**Updated:** 2026-08-14

## Context
Single-process orchestration limits horizontal scaling and creates tight coupling.

## Decision
Separate ControlPlane (auth, policy, budget, routing, idempotency, job creation) from ExecutionPlane (workers, agents, providers, tools). Jobs admitted by ControlPlane, executed by ExecutionPlane workers.

## Consequences
- Independent scaling of control vs execution
- Clear security boundary
- Worker failures don't affect control plane

## Alternatives Considered
- Single process with thread pools
- Microservices per component (over-engineered)

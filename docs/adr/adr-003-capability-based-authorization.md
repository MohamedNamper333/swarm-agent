# ADR-003: Capability-Based Authorization

**Status:** accepted
**Author:** system
**Date:** 2026-08-14
**Updated:** 2026-08-14

## Context
Client-controlled bypass flags (bypass_safety, estimated_cost) violate security boundaries.

## Decision
Replace client-controlled flags with server-issued ExecutionCapabilities. AuthorizationContext carries Principal, Capabilities, policy_version, authorization_id. Only server can grant OVERRIDE_SAFETY, OVERRIDE_BUDGET, etc.

## Consequences
- Untrusted input never grants privilege
- All overrides auditable with actor/reason/timestamp
- Fine-grained capability model

## Alternatives Considered
- Keep bypass flags with signature verification
- Role-based access control (coarser)

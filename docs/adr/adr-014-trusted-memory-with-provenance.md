# ADR-014: Trusted Memory with Provenance

**Status:** accepted
**Author:** system
**Date:** 2026-08-14
**Updated:** 2026-08-14

## Context
Agent memory could become instruction injection vector.

## Decision
Every memory item has: source, provenance, author, trust_level, tenant, scope, policy_tags, created_at, expires_at. Memory ≠ policy, memory ≠ system instruction. Access controlled by trust level and tenant.

## Consequences
- Memory cannot elevate privileges
- Full provenance for audit
- Trust-based access control

## Alternatives Considered
- Unstructured memory (vulnerable)
- No memory (stateless agents)

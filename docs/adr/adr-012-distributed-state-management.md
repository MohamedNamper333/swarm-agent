# ADR-012: Distributed State Management

**Status:** accepted
**Author:** system
**Date:** 2026-08-14
**Updated:** 2026-08-14

## Context
Process-local state (cache, rate limits, circuit breakers) breaks with horizontal scaling.

## Decision
Classify state: DISTRIBUTED (authoritative: budget, rate limits, safety, circuit breakers) vs PROCESS_LOCAL (non-authoritative: cache, metrics). Use distributed backend (Redis) for authoritative state.

## Consequences
- Horizontal scaling doesn't multiply limits
- Single source of truth for authoritative state
- Cache can remain local for performance

## Alternatives Considered
- All state in Redis (latency)
- Sticky sessions (anti-pattern)

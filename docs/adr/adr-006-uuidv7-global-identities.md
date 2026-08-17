# ADR-006: UUIDv7 Global Identities

**Status:** accepted
**Author:** system
**Date:** 2026-08-14
**Updated:** 2026-08-14

## Context
Process-local request counters break on restart and horizontal scaling.

## Decision
Use UUIDv7 (timestamp + random) for request_id, execution_id, trace_id, correlation_id, causation_id. Globally unique, restart-safe, distributed-safe, traceable.

## Consequences
- Globally unique without coordination
- Restart-safe (no counter reset)
- Distributed tracing ready

## Alternatives Considered
- ULID (similar, less standard)
- Snowflake IDs (requires coordination)

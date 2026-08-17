# ADR-018: Durable Audit Ledger

**Status:** accepted
**Author:** system
**Date:** 2026-08-14
**Updated:** 2026-08-14

## Context
Logs are not governance ledger; need tamper-evident audit trail.

## Decision
AuditLedger with immutable events: event_id, event_type, actor, timestamp, trace_id, execution_id, policy_version, schema_version, result. Records: auth, safety, board, exec, budget, routing, execution, fallback, override, memory, tool. File-based append-only store with rotation.

## Consequences
- Tamper-evident audit trail
- Regulatory compliance ready
- Queryable audit trail

## Alternatives Considered
- Application logs only
- External SIEM only

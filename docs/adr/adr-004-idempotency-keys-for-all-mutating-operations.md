# ADR-004: Idempotency Keys for All Mutating Operations

**Status:** accepted
**Author:** system
**Date:** 2026-08-14
**Updated:** 2026-08-14

## Context
Retries and duplicate requests can cause double-execution of side-effecting operations.

## Decision
Require Idempotency-Key header for all mutating endpoints. Store request hash with key. Same key + same payload = return existing. Same key + different payload = 409 Conflict. TTL-based cleanup.

## Consequences
- Safe retries without double-execution
- Explicit conflict detection
- Automatic cleanup via TTL

## Alternatives Considered
- Deduplication by request ID only
- Optimistic locking on resources

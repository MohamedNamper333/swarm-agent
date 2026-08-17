# ADR-013: Inter-Agent Bus with Defined Semantics

**Status:** accepted
**Author:** system
**Date:** 2026-08-14
**Updated:** 2026-08-14

## Context
Agent communication lacked delivery guarantees, ordering, deduplication.

## Decision
AgentBus with: AT_LEAST_ONCE delivery, per-topic FIFO ordering, explicit acknowledgment with timeout, deduplication keys, retry with exponential backoff, TTL, dead-letter, schema versioning.

## Consequences
- Reliable agent communication
- Exactly-once via idempotency keys
- Observability of message flow

## Alternatives Considered
- Direct agent-to-agent calls (coupled)
- Message queue without semantics

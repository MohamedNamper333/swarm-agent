# ADR-002: Budget Ledger with Atomic Reservations

**Status:** accepted
**Author:** system
**Date:** 2026-08-14
**Updated:** 2026-08-14

## Context
Concurrent budget reservations can cause race conditions where total reserved exceeds limit.

## Decision
Implement BudgetLedger with atomic compare-and-swap reservations. Track available, reserved, consumed, released separately. Enforce invariant: reserved + consumed <= limit.

## Consequences
- Race-free budget management
- Explicit reservation lifecycle (reserve -> consume/release)
- Supports concurrent execution

## Alternatives Considered
- Simple check-then-reserve (race-prone)
- Database transactions (adds dependency)

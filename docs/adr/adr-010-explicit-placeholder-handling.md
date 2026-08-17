# ADR-010: Explicit Placeholder Handling

**Status:** accepted
**Author:** system
**Date:** 2026-08-14
**Updated:** 2026-08-14

## Context
SmartPlaceholder returned synthetic content that could be mistaken for genuine provider output.

## Decision
All placeholder results explicit: execution_state=degraded, provider_status=failed, fallback_used=True, synthetic_output=True. Never presented as genuine provider execution.

## Consequences
- Clear distinction between real and synthetic output
- Fail-closed behavior preserved
- Observability tracks placeholder usage

## Alternatives Considered
- Return error instead of placeholder
- Cache real responses for reuse

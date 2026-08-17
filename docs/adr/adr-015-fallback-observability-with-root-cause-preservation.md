# ADR-015: Fallback Observability with Root Cause Preservation

**Status:** accepted
**Author:** system
**Date:** 2026-08-14
**Updated:** 2026-08-14

## Context
Fallback chains hid root cause, presenting fallback as genuine execution.

## Decision
Every fallback logs: original_provider, failure_code, failure_reason_class, fallback_provider, fallback_reason. Root cause preserved in observability. FallbackTracker provides root cause analysis.

## Consequences
- Root cause always visible
- Fallback chain traceable
- Root cause analysis automated

## Alternatives Considered
- Log fallback as success
- No fallback (fail fast)

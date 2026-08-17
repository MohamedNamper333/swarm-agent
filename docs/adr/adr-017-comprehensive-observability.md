# ADR-017: Comprehensive Observability

**Status:** accepted
**Author:** system
**Date:** 2026-08-14
**Updated:** 2026-08-14

## Context
Health checks insufficient for enterprise monitoring.

## Decision
Distributed tracing (Span/Trace), MetricsCollector (p50/p95/p99, counters, gauges, histograms), StructuredLogger with trace context. Metrics: p50/p95/p99 latency, failure rate, retry rate, fallback rate, token usage, cost, safety veto rate, routing ambiguity, queue depth.

## Consequences
- Full distributed tracing
- Production-grade metrics
- Trace-context logging

## Alternatives Considered
- Basic health checks only
- External APM only (vendor lock-in)

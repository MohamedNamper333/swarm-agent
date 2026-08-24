# ADR-007: Job System with Compensation

## Status
**Accepted** — 2025-08-24

## Context
Long-running operations (code execution, workflow steps) need:
- Durable persistence (survive restarts)
- Automatic retry with backoff
- Dead Letter Queue for permanently failed jobs
- Scheduling (one-time, interval, cron)
- Worker pool management with heartbeats

## Decision
Implement a comprehensive job system:

### Components
| Component | Purpose |
|-----------|---------|
| DurableJob | Persistent job model with version tracking |
| JobRepository | Pluggable storage (InMemory, Redis, PostgreSQL) |
| WorkerPool | Managed workers with heartbeats and stale detection |
| CompensationEngine | Saga pattern for multi-step workflows |
| JobScheduler | Cron, interval, one-time scheduling |
| DeadLetterQueue | Captures permanently failed jobs |

### Implementation Files
- `core/job/models.py` — DurableJob, JobStatus, JobPriority
- `core/job/repository.py` — JobRepository (InMemory, Redis)
- `core/job/worker.py` — Worker, WorkerPool, WorkerConfig
- `core/job/compensation.py` — CompensationEngine, WorkflowStep
- `core/job/scheduler.py` — JobScheduler, CronParser
- `core/job/dead_letter.py` — DeadLetterQueue, DLQIntegration
- `core/job/rate_limiter.py` — RateLimiter, HierarchicalRateLimiter

## Consequences

### Positive
- Jobs survive process restarts
- Automatic retry with exponential backoff
- Stale job detection via heartbeat timeout
- DLQ prevents silent job loss
- Hierarchical rate limiting (global → tenant → user)

### Negative
- InMemory repository is not persistent (production requires Redis)
- Worker heartbeat adds network overhead
- Compensation adds complexity to error handling

### Neutral
- Jobs are idempotent by design (safe to retry)
- Metrics exported in Prometheus format

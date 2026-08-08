# Phase 3 — Resilience + Observability + API + Platform (Weeks 10–14)

**Score progression:** 88 → **93** (target: K3 Swarm tier)

## Overview

Phase 3 transforms the Swarm from a smart engine into a **production-ready distributed platform**. Five pillars added:

| Pillar | Purpose | Week |
|---|---|---|
| **Resilience** | Survive crashes, retries, queue overflow | 10–11 |
| **Observability** | Metrics, events, alerting | 12 |
| **API** | Programmatic control (REST + WebSocket) | 13 |
| **Dashboard** | Human-facing monitoring | 14 |
| **Plugins** | Extensibility + Templates | 14 |

---

## Week 10 — Rate Limiting + Retry + Queue

### `swarm/resilience/rate_limiter.py` (203 LOC)

Token-bucket rate limiter with per-scope isolation.

**Exports:** `TokenBucket`, `RateLimiter`, `RateLimitConfig`, `RateLimitExceeded`

**Algorithm:**
- Capacity: max tokens in bucket
- Refill rate: tokens per second
- Each `try_acquire()` decrements by 1; blocks until refill if `acquire(timeout, block=True)`

**Validation:**
- `capacity=0` or `refill_rate=0` → `ValueError` (no silent misconfig)

```python
from swarm.resilience import RateLimiter, RateLimitConfig, RateLimitExceeded

limiter = RateLimiter()
limiter.configure('openai_api', RateLimitConfig(capacity=10, refill_rate=2.0))

if limiter.try_acquire('openai_api'):
    call_openai()
else:
    raise RateLimitExceeded('openai_api', retry_after_seconds=0.5)
```

### `swarm/resilience/retry_engine.py` (262 LOC)

Retry with backoff (exponential, linear, fixed) + jitter.

**Exports:** `RetryEngine`, `RetryPolicy`, `BackoffSchedule`, `RetryExhausted`

**API contract:**
```python
RetryEngine(policy=RetryPolicy(), rng=None, clock=monotonic, sleeper=sleep)
engine.execute(fn, *args, **kwargs)
```

**Backoff schedule** (deterministic):
- `BackoffSchedule.compute(policy, attempts=N)` returns a dataclass with `delays: List[float]`, `total_delay`, `strategy`, and a `get_delay(i)` accessor.
- Out-of-range access raises `IndexError` (no silent clamping — caller knows the limit).

```python
from swarm.resilience import RetryEngine, RetryPolicy

engine = RetryEngine(RetryPolicy(max_attempts=5, initial_delay_seconds=0.5, jitter_factor=0.2))
try:
    result = engine.execute(call_external_api, payload)
except RetryExhausted as e:
    log.error(f"Failed after {e.attempts} attempts: {e.last_exception}")
```

### `swarm/resilience/task_queue.py` (427 LOC)

Persistent priority queue with worker semantics.

**Exports:** `TaskQueue`, `TaskStatus`, `PriorityQueue`, `QueueItem`

**Priority rank:** `{'critical': 0, 'high': 1, 'normal': 2, 'low': 3, 'background': 4}` (lower = sooner).

**Worker pattern** (dequeue does NOT remove — it claims and marks running, allowing heartbeat-driven completion):
```python
item = queue.dequeue()  # status -> 'running', re-inserted
try:
    process(item)
    queue.complete(item.id, result=...)
except Exception:
    queue.fail(item.id, error=...)
```

**Note:** Calling `dequeue()` twice without `complete()` returns the same item — that's intentional for ack/heartbeat semantics.

---

## Week 11 — Error Recovery + Snapshots

### `swarm/resilience/recovery_engine.py` (305 LOC)

Recovery strategies per error class. Classifies failures into:
- **Transient** (network, timeout) → retry
- **Permanent** (validation, auth) → fail-fast + log
- **Degraded** (partial failure) → continue with reduced capability
- **Fatal** (invariant violation) → halt + alert

### `swarm/resilience/snapshot_manager.py` (380 LOC)

Periodic state snapshots to compressed tar.gz with content-addressable IDs.

**Exports added:** `SnapshotMetadata`, `SnapshotScope`, `SnapshotStats`, `SnapshotManager`

**Use case:** Pre-execution checkpoint for memory + learning state; rollback on bad commit.

```python
mgr = SnapshotManager('./snapshots')
sid = mgr.create(scope='memory', include=['*.json'], label='pre-migration')
# ... do risky thing ...
mgr.restore(sid)  # atomic
```

---

## Week 12 — Observability

### `swarm/observability/metrics_server.py` (~350 LOC)

Prometheus-compatible metrics endpoint. Counters, gauges, histograms for:
- Task throughput (`tasks_completed_total`)
- Latency (`task_duration_seconds`)
- Error rate (`task_errors_total{type="..."}`)
- Queue depth (`queue_size{priority="..."}`)
- Rate limiter rejections (`rate_limit_exceeded_total{scope="..."}`)

### `swarm/observability/event_logger.py` (~300 LOC)

Structured JSONL event log. Every state-changing operation produces one event:
- `task.enqueued`, `task.started`, `task.completed`, `task.failed`
- `agent.spawned`, `agent.terminated`
- `snapshot.created`, `snapshot.restored`
- `rate_limit.exceeded`, `retry.exhausted`

### `swarm/observability/alert_manager.py` (~250 LOC)

Webhook-based alerting with severity routing:
- `critical` → PagerDuty / oncall webhook
- `warning` → Slack channel
- `info` → log only

Rules are JSON-defined and hot-reloadable.

---

## Week 13 — REST API + WebSocket

### `swarm/api/rest_server.py` (~450 LOC)

FastAPI server exposing:
- `GET /api/health` — liveness + readiness
- `GET /api/agents` — active worker list
- `GET /api/tasks` — current task queue snapshot
- `GET /api/metrics` — Prometheus scrape
- `GET /api/snapshots` — list available snapshots
- `GET /api/vault/search?q=...` — knowledge vault search
- `POST /api/tasks` — submit new task
- `POST /api/snapshots/{id}/restore` — rollback

### `swarm/api/websocket_server.py` (~400 LOC)

Real-time push channel:
- `task.completed` → broadcast to dashboard
- `agent.spawned` → broadcast on capacity change
- `metric.tick` → every 5s (high-cardinality events)

### `swarm/api/auth.py` (~400 LOC)

Two auth modes:
1. **JWT bearer** — short-lived (15min) + refresh token (24h)
2. **API key** — for service accounts, scoped per-environment

**Bug fix (commit 1785459):** `datetime.utcnow()` was producing naive datetimes while `datetime.fromisoformat()` was parsing back into aware datetimes → instant 401 on every token validation. Fixed by using `datetime.now(timezone.utc)` consistently and stripping `tzinfo` only when comparing.

---

## Week 14 — Dashboard + Plugins + Templates

### Dashboard: `dashboard/web/`

React 18 + Vite + recharts. Three live panels:

| Panel | Polls | Shows |
|---|---|---|
| `PipelineMonitor` | 2s | task counts by status + sparkline |
| `AgentCards` | 3s | active workers + health + completion count |
| `VaultSearch` | on-demand | full-text search UI |

**Setup:**
```bash
cd dashboard/web
npm install
npm run dev
# Opens http://localhost:5173, proxies API to localhost:8080
```

### Plugins: `swarm/plugins/`

Plugin loader with three built-ins:
- `metrics_plugin.py` — auto-emits metrics on task lifecycle
- `alert_plugin.py` — hooks into `alert_manager` for severity routing
- `logging_plugin.py` — pushes events into structured log

Plugin contract: implement `on_event(event_type, payload)` and register at startup.

### Templates: `templates/` (10 YAML files)

Ready-to-load task templates:
- `alert.yaml` — alert routing
- `auth.yaml` — auth provider config
- `cache.yaml` — cache invalidation
- `logging.yaml` — log shipper
- `metrics.yaml` — metrics pipeline
- `notification.yaml` — push/email
- `rate-limiter.yaml` — rate limit policy
- `retry-engine.yaml` — retry policy
- `scheduler.yaml` — cron-style scheduling
- `webhook.yaml` — inbound webhook handler

---

## Test Coverage

**466 tests passing, 2 skipped, 0 failures.**

New tests added in Phase 3:
- `tests/unit/test_resilience.py` — 32 tests (rate_limit, retry, queue, recovery, snapshot)
- `tests/unit/test_recovery.py` — recovery engine classification
- `tests/unit/test_observability.py` — metrics + events + alerts
- `tests/unit/test_api.py` — JWT clock-skew fix + WebSocket auth
- `tests/test_plugins.py` — loader + 3 builtins

---

## Known Limitations / Honest Gaps

1. **Rate limiter is single-process** — for multi-worker deploy, swap `TokenBucket` for Redis-backed implementation.
2. **Snapshot manager doesn't deduplicate overlapping content** — each snapshot is full tar, no incremental.
3. **Alert manager has no deduplication** — same alert firing N times in 1s sends N webhooks.
4. **WebSocket reconnection is client-driven** — server has no resumption tokens yet.
5. **JWT secret rotation** — supported via env var reload, but active tokens aren't invalidated.

These are intentional for Phase 3 scope. Phase 4 candidates.

---

## Score Summary

| Capability | Phase 2 | Phase 3 | Delta |
|---|---|---|---|
| Rate limiting | — | 1.0 | +1.0 |
| Retry / backoff | 0.5 | 1.0 | +0.5 |
| Task queue (persistent) | 0.5 | 1.0 | +0.5 |
| Error recovery | — | 0.8 | +0.8 |
| State snapshots | — | 0.9 | +0.9 |
| Metrics (Prometheus) | 0.3 | 1.0 | +0.7 |
| Structured logging | 0.5 | 1.0 | +0.5 |
| Alerting | 0.2 | 0.9 | +0.7 |
| REST API | 0.3 | 1.0 | +0.7 |
| WebSocket | 0.2 | 0.8 | +0.6 |
| Dashboard | 0.0 | 0.8 | +0.8 |
| Plugin system | 0.0 | 0.7 | +0.7 |
| Templates | 0.0 | 0.7 | +0.7 |
| **Weighted total** | **88** | **93** | **+5** |

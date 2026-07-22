# SWARM OBSERVABILITY
## Structured Logging, Metrics, Tracing, Dashboard

---

### Log Format (JSON Lines)

Every significant event writes to `swarm_events.jsonl`:

```json
{"ts":"2025-07-22T10:30:00Z","level":"INFO","stage":1,"event":"pipeline_start","task_id":"swarm-001","pipeline":"STANDARD","complexity":45}
{"ts":"2025-07-22T10:30:15Z","level":"INFO","stage":1,"event":"stage_complete","stage_name":"STRATEGIC_PLANNING","duration_ms":15000,"output":"strategic_plan.md"}
{"ts":"2025-07-22T10:30:16Z","level":"INFO","stage":2,"event":"worker_dispatch","worker":"architect","subagent_type":"architect","task_id":"swarm-001-arch-001"}
{"ts":"2025-07-22T10:30:45Z","level":"INFO","stage":2,"event":"worker_complete","worker":"architect","duration_ms":29000,"status":"success","output_files":["app/main.py","app/models.py"]}
{"ts":"2025-07-22T10:30:46Z","level":"WARN","stage":4,"event":"constitutional_check","violations":["MINIMAL_SURFACE_AREA: unused import"],"action":"auto_fix_applied"}
{"ts":"2025-07-22T10:31:00Z","level":"INFO","stage":4,"event":"auto_verdict","score":92,"verdict":"PASS"}
{"ts":"2025-07-22T10:31:05Z","level":"INFO","stage":6,"event":"pipeline_complete","total_duration_ms":85000,"final_verdict":"PASS"}
```

---

### Key Metrics (Auto-Collected)

| Metric | Description | Target |
|--------|-------------|--------|
| `stage_duration_ms` | Per-stage latency | < 60s (LITE), < 180s (FULL) |
| `worker_dispatch_count` | Workers used per stage | Match plan |
| `worker_retry_rate` | % workers needing retry | < 10% |
| `constitutional_violations` | Violations per run | 0 |
| `auto_verdict_score` | Quality score | > 90 |
| `pipeline_upgrade_count` | LITE→STANDARD→FULL switches | ≤ 1 |
| `context_tokens_used` | Total tokens consumed | Budget compliance |

---

### Dashboard Queries (SQL-like)

```sql
-- Average stage duration by pipeline type
SELECT pipeline, stage, AVG(duration_ms) FROM events GROUP BY pipeline, stage;

-- Worker success rate
SELECT worker, COUNT(*) as total, SUM(CASE WHEN status='success' THEN 1 ELSE 0 END)/COUNT(*) as success_rate
FROM events WHERE event='worker_complete' GROUP BY worker;

-- Constitutional compliance
SELECT COUNT(*) as violations FROM events WHERE event='constitutional_check' AND violations != '[]';

-- Pipeline decision accuracy
SELECT pipeline, COUNT(*) as runs, AVG(final_score) as avg_score FROM runs GROUP BY pipeline;
```

---

### Real-Time Dashboard (CLI)

```bash
# Live tail
tail -f swarm_events.jsonl | jq -r '"[\(.ts)] \(.stage) \(.event) \(.worker // "")"'

# Stage progress
jq -s 'group_by(.stage) | map({stage: .[0].stage, avg_ms: (map(.duration_ms) | add/length)})' swarm_events.jsonl

-- Constitutional health
jq -s 'map(select(.event=="constitutional_check")) | length' swarm_events.jsonl
```

---

### Skills: `monitoring-expert`, `analytics-tracking`, `analytics-product`

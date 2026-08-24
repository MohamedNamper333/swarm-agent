# Runbook: High Latency (p99 > 500ms)

## Alert
- **Alert Name**: HighLatency
- **Severity**: Warning
- **Trigger Condition**: `histogram_quantile(0.99, rate(swarm_executions_duration_bucket[5m])) > 0.5`

## Symptoms
- Slow response times reported by users
- p99 latency exceeding SLA
- Grafana latency panel showing upward trend

## Diagnosis
1. Check "Swarm System Overview" → "Execution Duration (p50, p95, p99)"
2. Identify bottleneck:
   - High sandbox cold start time → Check sandbox pool
   - High queue wait time → Scale workers
   - Slow code execution → Check resource limits
3. Check CPU/Memory utilization on nodes
4. Check network latency between services

## Resolution
1. If sandbox queue backup:
   ```bash
   kubectl scale deployment/execution-worker --replicas=5 -n swarm-production
   ```
2. If resource exhaustion:
   ```bash
   kubectl top pods -n swarm-production
   # Increase resources via Helm
   helm upgrade swarm ./helm/swarm -f values-prod.yaml --set swarmMaster.resources.limits.cpu=2
   ```
3. If network issue:
   - Check service mesh (Istio) configuration
   - Verify mTLS isn't causing excessive overhead

## Escalation
- If p99 > 2000ms → escalate to SRE Lead immediately
- If sustained for 30+ minutes → consider traffic shedding

## Prevention
- Set HPA target CPU at 70%
- Pre-warm sandbox pool
- Use gVisor instead of Firecracker for lower cold-start

# Runbook: High Error Rate

## Alert
- **Alert Name**: HighErrorRate
- **Severity**: Critical
- **Trigger Condition**: `rate(swarm_executions_errors_total[5m]) / rate(swarm_executions_total[5m]) > 0.05`

## Symptoms
- Dashboard shows error rate spike
- Users reporting failures
- PagerDuty alert firing

## Diagnosis
1. Check Grafana dashboard: "Swarm System Overview" → "Error Rate by Type"
2. Identify dominant error type:
   - `SIGKILL` → Likely OOM, check memory-pressure runbook
   - `Timeout` → Check sandbox queue depth
   - `ExitCode` → Check code being executed
   - `MemoryError` → Check resource limits
3. Check recent deployments: `kubectl rollout history deployment/swarm-master -n swarm-production`
4. Check sandbox health: `curl -f http://sandbox-service/health`

## Resolution
1. If caused by recent deploy:
   ```bash
   kubectl rollout undo deployment/swarm-master -n swarm-production
   ```
2. If OOM:
   - Increase memory limits in Helm values
   - `helm upgrade swarm ./helm/swarm -f values-prod.yaml --set execution.sandbox.memoryLimitMb=512`
3. If timeout:
   - Scale up sandbox workers
   - `kubectl scale deployment/sandbox-worker --replicas=5 -n swarm-production`
4. If code-related:
   - Identify offending tenant/user
   - Apply rate limiting or suspend account

## Escalation
- If unresolved after 15 minutes → escalate to Platform Lead
- If security-related → escalate to Security Lead immediately

## Prevention
- Set up canary deployments for all changes
- Monitor error rates continuously with Grafana alerts
- Implement progressive delivery (canary → 10% → 50% → 100%)

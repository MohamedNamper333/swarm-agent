# Operational Runbooks

This directory contains runbooks for all alert rules and common operational procedures.

## Index

| Runbook | Alert | Severity |
|---------|-------|----------|
| [high-error-rate](high-error-rate.md) | Error rate > 5% for 5 minutes | Critical |
| [high-latency](high-latency.md) | p99 latency > 500ms for 5 minutes | Warning |
| [memory-pressure](memory-pressure.md) | Memory usage > 90% | Critical |
| [disk-space](disk-space.md) | Disk usage > 90% | Critical |
| [auth-failures](auth-failures.md) | Auth failure spike (>50/min) | Critical |
| [sandbox-queue-backup](sandbox-queue-backup.md) | Sandbox queue depth > 100 | Warning |
| [circuit-breaker-open](circuit-breaker-open.md) | Circuit breaker opened | Warning |
| [budget-exhausted](budget-exhausted.md) | Tenant budget exhausted | Info |
| [cross-tenant-violation](cross-tenant-violation.md) | Cross-tenant access detected | Critical |
| [dr-procedure](dr-procedure.md) | Disaster recovery procedure | N/A |

## Template

```markdown
# Runbook: {Title}

## Alert
- **Alert Name**: 
- **Severity**: 
- **Trigger Condition**: 

## Symptoms
What the on-call engineer will observe.

## Diagnosis
Step-by-step diagnosis procedure.

## Resolution
Step-by-step resolution procedure.

## Escalation
When to escalate and to whom.

## Prevention
How to prevent recurrence.
```

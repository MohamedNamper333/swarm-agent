# ADR-010: Blue/Green + Canary Deployment via ArgoCD

## Status
**Accepted** — 2025-08-24

## Context
Production deployments need:
- Zero downtime
- Quick rollback capability (<5 minutes)
- Gradual traffic shifting to catch issues early
- GitOps workflow (deployments triggered by git push)

## Decision
Implement two deployment strategies:

### 1. Blue/Green (Default for major releases)
Two identical environments (blue/green). Traffic switches atomically.

```
Deploy → Validate → Switch Traffic → Monitor → Cleanup Old
```

### 2. Canary (For risky changes)
Gradual traffic shifting: 5% → 10% → 25% → 50% → 100%

```
Deploy Canary → 5% traffic → Validate → 10% → Validate → ... → 100%
```

Both strategies use ArgoCD with automated rollback on health check failure.

### Implementation Files
- `core/deployment/blue_green.py` — BlueGreenDeploymentManager, CanaryDeploymentManager
- `core/deployment/disaster_recovery.py` — BackupManager, FailoverManager, DisasterRecoveryCoordinator
- `deploy/argocd/application-staging.yaml` — ArgoCD staging app
- `deploy/argocd/application-production.yaml` — ArgoCD production app
- `deploy/helm/swarm/environments/` — Environment-specific values
- `scripts/dr_drill.py` — Automated DR drill

## Consequences

### Positive
- Zero-downtime deployments
- Automatic rollback in <5 minutes
- RTO <1 hour, RPO <5 minutes (verified by drill)
- GitOps provides audit trail for all deployments
- Environment parity (dev/staging/prod use same charts)

### Negative
- Blue/Green requires 2x resources during deployment
- Canary requires sophisticated traffic splitting (Istio/nginx)
- ArgoCD adds operational dependency
- DR drills require dedicated time and resources

### Neutral
- Staging uses auto-sync; production uses manual approval
- Chaos engineering enabled in staging only
- Production has pod disruption budgets (minAvailable=2)

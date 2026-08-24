# Architecture Decision Records (ADR)

This directory contains all Architecture Decision Records for the Swarm Enterprise Platform.

## Index

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [001](001-layered-architecture.md) | Layered Architecture + Strict Boundaries | Accepted | 2025-08-24 |
| [002](002-zero-trust-security.md) | Zero-Trust Security (DPoP + mTLS + HSM) | Accepted | 2025-08-24 |
| [003](003-saga-pattern.md) | Saga Pattern for Distributed Transactions | Accepted | 2025-08-24 |
| [004](004-tenant-isolation.md) | Tenant Isolation Strategy | Accepted | 2025-08-24 |
| [005](005-agent-registry.md) | Agent Registry + Task Dispatcher | Accepted | 2025-08-24 |
| [006](006-memory-v2.md) | Memory V2 as Context Layer | Accepted | 2025-08-24 |
| [007](007-job-system.md) | Job System with Compensation | Accepted | 2025-08-24 |
| [008](008-sandbox-strategy.md) | Sandbox Strategy (Local/gVisor/Firecracker) | Accepted | 2025-08-24 |
| [009](009-import-linter.md) | Import-Linter as CI Gate | Accepted | 2025-08-24 |
| [010](010-deployment-strategy.md) | Blue/Green + Canary Deployment via ArgoCD | Accepted | 2025-08-24 |

## Template

Use the following template for new ADRs:

```markdown
# ADR-NNN: Title

## Status
Accepted / Proposed / Deprecated / Superseded by ADR-XXX

## Context
What is the issue that we're seeing that is motivating this decision?

## Decision
What is the change that we're proposing or doing?

## Consequences
### Positive
- What becomes easier?

### Negative
- What becomes harder?

### Neutral
- Other impacts
```

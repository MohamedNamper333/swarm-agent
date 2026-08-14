# Enterprise Swarm Agent Platform

**Version:** 1.0.0  
**Status:** Enterprise Hardening in Progress  
**Architecture:** Governed Multi-Agent Execution Platform  
**License:** Apache-2.0

---

## Overview

Enterprise Swarm Agent is a governed multi-agent execution platform designed for institutional workloads. It provides a structured orchestration layer that coordinates specialized agents across safety, governance, execution, and observability boundaries.

The platform implements a **Control Plane / Execution Plane** separation with explicit policy enforcement, atomic budget management, idempotent operations, and full auditability.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CONTROL PLANE                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   AuthN/Z   │  │  Policy     │  │  Budget     │             │
│  │  Service    │  │  Engine     │  │  Ledger     │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│         │                │                │                      │
│         └────────────────┼────────────────┘                      │
│                          ▼                                      │
│              ┌─────────────────────┐                            │
│              │  Job Coordinator    │                            │
│              │  (Idempotent,       │                            │
│              │   Auditable)        │                            │
│              └─────────────────────┘                            │
└────────────────────────────┬────────────────────────────────────┘
                             │ gRPC / Message Bus
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      EXECUTION PLANE                            │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │ Research │ │  Code    │ │  Video   │ │  Design  │  ...      │
│  │ Workers  │ │ Workers  │ │ Workers  │ │ Workers  │           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
│         │           │           │           │                    │
│         └───────────┼───────────┼───────────┘                    │
│                     ▼                                           │
│          ┌──────────────────┐                                   │
│          │  Provider        │                                   │
│          │  Abstraction     │                                   │
│          └──────────────────┘                                   │
└─────────────────────────────────────────────────────────────────┘
```

### Core Components

| Layer | Component | Responsibility |
|-------|-----------|----------------|
| **Control** | `AuthService` | Authentication, authorization, capability issuance |
| **Control** | `PolicyEngine` | Safety, budget, tool, data, human-review policies |
| **Control** | `BudgetLedger` | Atomic reservations, reconciliation, cost governance |
| **Control** | `RoutingEngine` | Multi-strategy routing with confidence & ambiguity |
| **Control** | `JobCoordinator` | Idempotent job creation, durable state, audit emission |
| **Execution** | `AgentWorkers` | Specialized agents (research, code, video, design, etc.) |
| **Execution** | `ProviderRegistry` | Model selection, fallback, provider abstraction |
| **Execution** | `ToolGateway` | Capability-controlled tool invocation |
| **Shared** | `AuditLedger` | Immutable audit events for all critical decisions |
| **Shared** | `Observability` | Tracing, metrics, structured logging with redaction |

---

## Enterprise Tiers

| Tier | Components | Purpose |
|------|------------|---------|
| **Board** (5) | Audit, Risk, Compliance, Strategy, Governance | Oversight & governance |
| **C-Suite** (7) | CEO, CTO, CFO, CISO, COO, CMO, CHRO | Executive coordination |
| **Departments** (40) | Research, Engineering, Security, Finance, Legal, HR, Marketing, etc. | Domain execution |
| **Safety** (4) | Content, PII, Bias, Injection | Defensive boundaries |

---

## Quick Start

### Prerequisites

- Python 3.11+
- Redis 7+ (for distributed state)
- PostgreSQL 15+ (for audit ledger & job persistence)

### Installation

```bash
# Clone
git clone https://github.com/MohamedNamper333/swarm-agent.git
cd swarm-agent

# Install dependencies
pip install -e ".[dev]"

# Configure environment
cp .env.example .env
# Edit .env with your credentials

# Run migrations
alembic upgrade head

# Start services
docker-compose up -d redis postgres
python -m swarm.api.rest_server
```

### Configuration

Key environment variables:

```bash
# Core
SWARM_ENV=production
SWARM_TENANT_ID=your-tenant

# Security
SWARM_JWT_SECRET=...
SWARM_ENCRYPTION_KEY=...

# Providers
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...

# Infrastructure
REDIS_URL=redis://localhost:6379/0
DATABASE_URL=postgresql://user:pass@localhost/swarm
```

---

## API Reference

### Submit Job

```http
POST /api/v1/jobs
Idempotency-Key: <uuid>
Content-Type: application/json

{
  "type": "research",
  "payload": { "query": "market analysis for AI agents" },
  "priority": "normal",
  "budget_usd": 5.00
}
```

**Response:** `202 Accepted` with `job_id` and `status: "queued"`

### Check Status

```http
GET /api/v1/jobs/{job_id}
```

### Stream Results

```http
GET /api/v1/jobs/{job_id}/stream
```

---

## Governance Features

| Feature | Implementation |
|---------|----------------|
| **Safety Overrides** | Capability-based, server-issued, fully audited |
| **Budget Control** | Atomic reservations with reconciliation |
| **Idempotency** | `Idempotency-Key` header with deduplication |
| **Human Review** | Explicit workflow state machine |
| **Multi-Tenancy** | Tenant-scoped resources, budgets, audit |
| **Tool Authorization** | Capability-gated tool invocation |
| **Audit Ledger** | Immutable, append-only event store |

---

## Test Coverage

| Category | Count | Status |
|----------|-------|--------|
| Unit | 52 | ✅ Passing |
| Integration | 18 | ✅ Passing |
| E2E | 12 | ✅ Passing |
| Concurrency | 8 | ✅ Passing |
| Security | 4 | ✅ Passing |

**Total:** 94 tests passing

Run tests:
```bash
pytest -v --tb=short
```

---

## Project Structure

```
swarm-agent/
├── swarm/
│   ├── api/                    # REST & WebSocket endpoints
│   │   ├── auth.py             # Authentication & capabilities
│   │   ├── rest_server.py      # FastAPI application
│   │   └── websocket_server.py # Real-time job streaming
│   ├── core/                   # Core orchestration primitives
│   ├── enterprise/             # Enterprise tiers & departments
│   │   ├── board/              # Board-level agents (5)
│   │   ├── csuite/             # C-Suite agents (7)
│   │   ├── departments/        # Domain departments (40)
│   │   ├── safety/             # Safety agents (4)
│   │   └── swarm_master.py     # Thin coordination layer
│   ├── integrations/           # External system adapters
│   ├── intelligence/           # ML/AI provider abstractions
│   ├── observability/          # Tracing, metrics, logging
│   ├── plugins/                # Plugin system
│   └── resilience/             # Circuit breakers, retries, deadlines
├── tests/                      # Test suite (unit, integration, e2e)
├── configs/                    # Configuration templates
├── scripts/                    # Operational scripts
├── docs/                       # Architecture & API docs
├── .env.example                # Environment template
├── pyproject.toml              # Project metadata & dependencies
├── Makefile                    # Common operations
└── README.md                   # This file
```

---

## Current Status & Hardening Roadmap

This platform is undergoing **Institutional Hardening** per the audit documented in `docs/INSTITUTIONAL_PROBLEM_SOLUTION_REGISTER.md`.

### Wave 1 — Trust (In Progress)
- [ ] F-001: Safety bypass → capability-based authorization
- [ ] F-002: Client-controlled cost → server-authoritative cost estimation
- [ ] F-003: Budget race condition → atomic reservation ledger
- [ ] F-004: Approval ≠ Execution → explicit state machine
- [ ] F-005: Process-local IDs → UUIDv7/ULID
- [ ] F-006: Missing idempotency → Idempotency-Key support
- [ ] F-015: Safety hardening → defense-in-depth
- [ ] F-033: Tool authorization → capability-gated tools
- [ ] F-037: Delegation limits → depth/hops budgets

### Wave 2 — Execution Correctness
- [ ] F-007: Keyword routing → multi-strategy routing engine
- [ ] F-008: SwarmMaster decomposition → thin coordinator
- [ ] F-009: Dependency injection → protocol-based DI
- [ ] F-010: Async execution → durable job queue
- [ ] F-011: Error taxonomy → domain errors with policies
- [ ] F-027: Compensation model → saga patterns
- [ ] F-028: Control/Execution plane separation
- [ ] F-032: Deadline propagation → execution deadlines

### Wave 3 — Distributed Systems
- [ ] F-012: Shared state → distributed infrastructure
- [ ] F-021: Inter-agent bus semantics
- [ ] F-022: Memory trust boundaries
- [ ] F-030: Fallback observability
- [ ] F-031: Retry storm protection

### Wave 4 — Enterprise Operations
- [ ] F-023: Observability (tracing, metrics, logs)
- [ ] F-024: Durable audit ledger
- [ ] F-025: Multi-tenancy isolation
- [ ] F-026: API surface hardening
- [ ] F-034: Artifact governance
- [ ] F-035: Data classification
- [ ] F-036: Resource governance

### Wave 5 — Engineering Maturity
- [ ] F-018: SmartPlaceholder → explicit degraded state
- [ ] F-019: Registry consolidation
- [ ] F-029: Formal policy engine
- [ ] F-038: Architecture Decision Records
- [ ] F-039: Advanced test categories (chaos, load, property-based)
- [ ] F-040: Production release gate

---

## Non-Negotiable Invariants

After hardening, these invariants **must** hold:

> **I-001** Untrusted input can never grant privilege.  
> **I-002** Safety override requires authenticated authorization.  
> **I-003** Approval is never execution success.  
> **I-004** Every execution has globally unique identity.  
> **I-005** Side-effecting operations are idempotent or explicitly protected.  
> **I-006** Cost is server-authoritative.  
> **I-007** Budget reservation is atomic.  
> **I-008** Worker restart cannot silently lose durable execution.  
> **I-009** Agent-to-agent communication is not implicitly trusted.  
> **I-010** Memory is data, not policy.  
> **I-011** Tool access is capability-controlled.  
> **I-012** Every production execution is traceable.  
> **I-013** Fallback cannot be presented as genuine provider execution.  
> **I-014** Horizontal scaling cannot multiply authoritative limits.  
> **I-015** Every critical decision is auditable.  
> **I-016** Every bounded resource has an explicit limit.  
> **I-017** Every retry has a reason, limit, and deadline.  
> **I-018** Every privileged action is authorized server-side.

---

## Security

- **No client-controlled security decisions** — all capabilities server-issued
- **Audit logging** — all critical decisions recorded with actor, reason, policy version
- **PII redaction** — structured logging with automatic redaction policies
- **Tenant isolation** — cross-tenant access blocked at infrastructure layer
- **Supply chain** — pinned dependencies, SBOM generation, vulnerability scanning

---

## Contributing

1. Read `docs/INSTITUTIONAL_PROBLEM_SOLUTION_REGISTER.md` for architectural context
2. Follow the hardening wave structure — fix root causes, not symptoms
3. All changes require:
   - Root cause analysis
   - Tests (unit + concurrency + regression)
   - Observability instrumentation
   - ADR for architectural decisions

---

## License

Apache-2.0 — see [LICENSE](LICENSE) for details.

---

## Links

- **Repository:** https://github.com/MohamedNamper333/swarm-agent
- **Issues:** https://github.com/MohamedNamper333/swarm-agent/issues
- **Architecture Docs:** `docs/`
- **Audit Register:** `docs/INSTITUTIONAL_PROBLEM_SOLUTION_REGISTER.md`

---

*Enterprise Swarm Agent — From orchestration prototype to governed execution platform.*
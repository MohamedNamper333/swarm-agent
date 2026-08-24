# 🐝 Swarm System - Architecture Overview

> **A Production-Grade Multi-Agent Orchestration Platform**

---

## 🏗️ High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            EXTERNAL CLIENTS                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   REST API  │  │  WebSocket  │  │   GraphQL   │  │  Webhooks   │         │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘         │
└─────────┼────────────────┼────────────────┼────────────────┼─────────────────┘
          │                │                │                │
          ▼                ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           API GATEWAY (Planned)                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ Auth/Z      │  │ Rate Limit  │  │ Routing     │  │ Observability│        │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘         │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
          ┌──────────────────────┼──────────────────────┐
          ▼                      ▼                      ▼
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│  SWARM MASTER   │   │  SCHEDULER      │   │  DLQ PROCESSOR  │
│  (Orchestrator) │   │  (Cron/Interval)│   │  (Dead Letters) │
└────────┬────────┘   └────────┬────────┘   └────────┬────────┘
         │                     │                      │
         ▼                     ▼                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        ENTERPRISE CORE SERVICES                                │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐          │
│  │Governance│ │Orchestra.│ │ Memory   │ │Observab. │ │ Routing  │  ...     │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘          │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
          ┌──────────────────────┼──────────────────────┐
          ▼                      ▼                      ▼
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│   JOB SYSTEM    │   │  MEMORY V2      │   │  INTELLIGENCE   │
│  (Compensation, │   │  (Fabric,       │   │  (Constitutional│
│   Workers, DLQ) │   │   Lifecycle,   │   │   Guard, Audit, │
│                 │   │   Search)      │   │   Reflection)   │
└────────┬────────┘   └────────┬────────┘   └────────┬────────┘
         │                     │                      │
         ▼                     ▼                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PERSISTENCE LAYER                                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   Redis     │  │  PostgreSQL │  │  Meilisearch│  │  Vector DB  │         │
│  │  (Jobs,     │  │  (Audit,    │  │  (Full-text │  │  (Embeddings│         │
│  │   Cache,    │  │   Config,   │  │   Search)   │  │   + RAG)    │         │
│  │   Pub/Sub)  │  │   State)    │  │             │  │             │         │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🧩 Core Components

### **1. Memory V2** (`swarm/memory/v2/`) ✅ **COMPLETE**

| Layer | Purpose | Key Features |
|-------|---------|--------------|
| **WORKING** | Short-term, high-frequency | Fast access, auto-promotion |
| **EPISODIC** | Workflow executions | Traceable, queryable |
| **SEMANTIC** | Learned knowledge | Embeddings, similarity search |
| **KNOWLEDGE** | Verified facts | High trust, citation-ready |
| **GOVERNANCE** | Decisions, vetoes, policies | Immutable, auditable |

**Key Classes:**
- `MemoryFabric` - Unified interface
- `MemoryRepository` - Redis/InMemory backends with CAS
- `PromotionLifecycleManager` - Auto-promotion with policies
- `LessonService` - Execution-linked learning
- `CheckpointStore` - PITR, branching, GC

---

### **2. Job System** (`swarm/enterprise/core/job/`) ✅ **STAGE 1&2 COMPLETE**

```
Job System Architecture:
┌────────────────────────────────────────────────────────────┐
│                    COMPENSATION ENGINE                       │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ WorkflowExecution (Saga Pattern)                      │   │
│  │  • Topological sort (Kahn's algorithm)                │   │
│  │  • Step execution with timeout enforcement            │   │
│  │  • Automatic compensation on failure (reverse order)  │   │
│  │  • Persistence at every step                          │   │
│  └──────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
       ┌────────────┐  ┌────────────┐  ┌────────────┐
       │   WORKER   │  │  SCHEDULER │  │    DLQ     │
       │  POOL      │  │            │  │            │
       │            │  │ • Once     │  │ • Auto-retry│
       │ • Heartbeat│  │ • Interval │  │ • Resolution│
       │ • Stale    │  │ • Cron     │  │ • Tracking │
       │   detection│  │ • Max runs │  │            │
       └────────────┘  └────────────┘  └────────────┘
              │               │               │
              └───────────────┼───────────────┘
                              ▼
                    ┌─────────────────────┐
                    │  JOB REPOSITORY     │
                    │  (Protocol + Redis/ │
                    │   InMemory)         │
                    │                     │
                    │ • Atomic claim      │
                    │ • Atomic complete   │
                    │ • Heartbeat         │
                    │ • Stale detection   │
                    └─────────────────────┘
```

**Key Features:**
- **DurableJob** - Full lifecycle tracking with events
- **CompensationEngine** - Saga pattern with automatic rollback
- **WorkerPool** - Horizontal scaling, graceful shutdown
- **JobScheduler** - Cron, interval, once with tenant isolation
- **DeadLetterQueue** - Auto-retry with exponential backoff
- **RateLimiter** - Token bucket, sliding window, hierarchical
- **Metrics** - 25+ Prometheus metrics + health checks

---

### **3. Intelligence Layer** (`swarm/intelligence/`)

| Component | Purpose |
|-----------|---------|
| **ConstitutionalGuard** | Real-time policy enforcement on agent outputs |
| **ConstitutionalAudit** | Post-hoc compliance auditing |
| **SelfReflection** | Agent self-critique and improvement |
| **LearningTracker** | Track agent performance over time |
| **CrossReview** | Multi-agent peer review |
| **SkillDiscovery** | Automatic skill discovery and indexing |

---

### **4. Resilience** (`swarm/resilience/`)

| Component | Purpose |
|-----------|---------|
| **RecoveryEngine** | Checkpoint-based recovery |
| **RetryEngine** | Configurable retry policies |
| **CircuitBreaker** | Failure isolation |
| **SnapshotManager** | State snapshots for recovery |
| **TaskQueue** | Resilient task queuing |

---

### **5. Observability** (`swarm/observability/`)

| Component | Purpose |
|-----------|---------|
| **EventLogger** | Structured event logging |
| **MetricsServer** | Prometheus metrics endpoint |
| **AlertManager** | Alert routing and deduplication |

---

## 🔄 Data Flow: Task Execution

```
User Request
     │
     ▼
┌──────────────────────────────────────────┐
│           API GATEWAY                     │
│  Auth → Rate Limit → Route → Trace        │
└──────────────────────────────────────────┘
     │
     ▼
┌──────────────────────────────────────────┐
│           SWARM MASTER                    │
│  1. Parse intent                          │
│  2. Select agent(s) via Agent Registry    │
│  3. Assemble context via MemoryFabric     │
│  4. Dispatch to Job System                │
└──────────────────────────────────────────┘
     │
     ▼
┌──────────────────────────────────────────┐
│         COMPENSATION ENGINE               │
│  1. Create WorkflowExecution              │
│  2. Topological sort steps                │
│  3. For each step:                        │
│     a. Validate required inputs           │
│     b. Execute with timeout               │
│     c. On success: store outputs          │
│     d. On failure: compensate (reverse)   │
│  4. Persist at each step                  │
└──────────────────────────────────────────┘
     │
     ▼
┌──────────────────────────────────────────┐
│            WORKER POOL                    │
│  1. Dequeue job (priority + tenant)       │
│  2. Validate payload                      │
│  3. Execute with executor                 │
│  4. Heartbeat every 30s                   │
│  5. On complete: persist result           │
│  6. On failure: retry or DLQ              │
└──────────────────────────────────────────┘
     │
     ▼
┌──────────────────────────────────────────┐
│           MEMORY V2                       │
│  1. Write episode to EPISODIC layer       │
│  2. Extract lessons → SEMANTIC            │
│  3. Promote high-value → KNOWLEDGE        │
│  4. Governance decisions → GOVERNANCE     │
│  5. Context assembly for next task        │
└──────────────────────────────────────────┘
```

---

## 🏷️ Multi-Tenancy Model

```
Tenant Isolation Boundaries:
┌─────────────────────────────────────────────────────────────┐
│                    TENANT A                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │ Jobs     │ │ Memory   │ │ Rate     │ │ Schedules│       │
│  │ (Queue)  │ │ (NS)     │ │ Limits   │ │          │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
├─────────────────────────────────────────────────────────────┤
│                    TENANT B                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │ Jobs     │ │ Memory   │ │ Rate     │ │ Schedules│       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
├─────────────────────────────────────────────────────────────┤
│                    SHARED INFRASTRUCTURE                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │ Redis    │ │ Postgres │ │ Meilisear│ │ Vector   │       │
│  │ (Sharded)│ │ (Rls)    │ │ ch (Idx) │ │ DB       │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
└─────────────────────────────────────────────────────────────┘
```

**Isolation Mechanisms:**
- **Redis:** Key prefixes `swarm:jobs:tenant:{id}:...`
- **PostgreSQL:** Row Level Security (RLS) policies
- **Meilisearch:** Separate indexes per tenant
- **Vector DB:** Namespace isolation
- **API:** JWT claims enforce tenant context

---

## 🔐 Security Model

```
┌─────────────────────────────────────────────────────────────┐
│                    AUTHENTICATION                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │  OAuth2/    │  │   JWT       │  │   API Keys  │          │
│  │  OIDC       │  │  (RS256)    │  │  (Scoped)   │          │
│  └─────────────┘  └─────────────┘  └─────────────┘          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    AUTHORIZATION (RBAC)                      │
│  ┌────────┐ ┌──────────┐ ┌─────────┐ ┌─────────┐            │
│  │ Admin  │ │ Operator │ │Developer│ │ Viewer  │            │
│  │  *     │ │ jobs:rw  │ │ jobs:rw │ │ jobs:r  │            │
│  │        │ │ mem:rw   │ │ mem:rw  │ │ mem:r   │            │
│  │        │ │ config:r │ │ config:r│ │ config:r│            │
│  └────────┘ └──────────┘ └─────────┘ └─────────┘            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    AUDIT & COMPLIANCE                        │
│  • Every decision logged to GOVERNANCE layer                │
│  • Immutable audit trail with cryptographic proof           │
│  • Constitutional Guard validates agent outputs             │
│  • Automated compliance reporting (GDPR, SOC2, HIPAA)       │
└─────────────────────────────────────────────────────────────┘
```

---

## 📈 Scalability Targets

| Metric | Target | Current |
|--------|--------|---------|
| **Concurrent Jobs** | 10,000+ | Tested to 1,000 |
| **Job Throughput** | 1,000/sec | ~200/sec |
| **Memory Entries** | 100M+ | 1M tested |
| **Tenants** | 1,000+ | 10 tested |
| **Agents** | 100+ | 5 registered |
| **Workflow Depth** | 100 steps | 20 tested |
| **Latency (p99)** | <500ms | ~200ms |
| **Availability** | 99.99% | N/A (pre-prod) |

---

## 🛠️ Technology Stack

| Layer | Technology | Version |
|-------|------------|---------|
| **Language** | Python | 3.11+ |
| **Async** | asyncio, uvloop | Latest |
| **Web Framework** | FastAPI | 0.100+ |
| **Message Queue** | Redis Streams | 7.0+ |
| **Primary DB** | PostgreSQL | 15+ |
| **Search** | Meilisearch | 1.6+ |
| **Vector DB** | pgvector / Milvus | Latest |
| **Cache** | Redis | 7.0+ |
| **Service Discovery** | Consul | 1.15+ |
| **Tracing** | OpenTelemetry | 1.20+ |
| **Metrics** | Prometheus | 2.45+ |
| **Visualization** | Grafana | 10+ |
| **Deployment** | Kubernetes | 1.28+ |
| **Package Mgmt** | Poetry / pip | Latest |

---

## 📁 Repository Structure

```
swarm-agent/
├── swarm/
│   ├── api/                    # REST + WebSocket servers
│   ├── core/                   # Core orchestration
│   │   ├── agent_router.py
│   │   ├── task_dag.py
│   │   ├── inter_agent_bus.py
│   │   └── ...
│   ├── enterprise/
│   │   ├── core/
│   │   │   ├── job/            # Job System (✅ Complete)
│   │   │   ├── memory/         # Enterprise Memory
│   │   │   ├── governance/     # Policy enforcement
│   │   │   ├── orchestration/  # Workflow orchestration
│   │   │   ├── observability/  # Unified observability
│   │   │   ├── routing/        # Intelligent routing
│   │   │   ├── policy/         # Dynamic policies
│   │   │   ├── state/          # Distributed state
│   │   │   └── ...             # (11 submodules)
│   │   ├── swarm_master.py     # Main orchestrator
│   │   └── board/csuite/...    # Enterprise modules
│   ├── intelligence/           # AI governance
│   ├── memory/v2/              # Memory V2 (✅ Complete)
│   ├── observability/          # Metrics, logging, alerts
│   ├── plugins/                # Plugin system
│   └── resilience/             # Retry, circuit breaker, recovery
├── tests/
│   ├── unit/                   # 497 tests ✅
│   ├── enterprise/             # 12 tests
│   └── integration/            # (Planned)
├── docs/                       # Architecture docs, ADRs
├── helm/                       # Kubernetes Helm charts (Planned)
├── .github/workflows/          # CI/CD
├── pyproject.toml
└── README.md
```

---

## 🚀 Deployment Architecture

### **Development**
```bash
# Local development
docker-compose up -d redis postgres meilisearch
python -m swarm.api.rest_server
python -m swarm.enterprise.swarm_master
```

### **Staging (Kubernetes)**
```yaml
# helm/swarm/values-staging.yaml
replicaCount: 2
autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 10
resources:
  limits:
    cpu: 2000m
    memory: 4Gi
```

### **Production (Kubernetes)**
```yaml
# helm/swarm/values-prod.yaml
replicaCount: 5
autoscaling:
  enabled: true
  minReplicas: 5
  maxReplicas: 50
  targetCPUUtilization: 70%
resources:
  limits:
    cpu: 4000m
    memory: 8Gi
  requests:
    cpu: 1000m
    memory: 2Gi
networkPolicy:
  enabled: true
podDisruptionBudget:
  enabled: true
  minAvailable: 50%
```

---

## 🔮 Future Evolution

### **v3.0 - Agent Mesh (Q1 2026)**
- Peer-to-peer agent communication
- Decentralized orchestration
- Federated learning across agents

### **v3.5 - Cognitive Architecture (Q2 2026)**
- System 1/System 2 thinking
- Long-term planning module
- Meta-cognitive monitoring

### **v4.0 - Autonomous Organization (Q4 2026)**
- Self-modifying workflows
- Automatic agent generation
- Economic resource allocation

---

## 📞 Support & Contribution

| Channel | Purpose |
|---------|---------|
| **GitHub Issues** | Bug reports, feature requests |
| **GitHub Discussions** | Architecture questions, RFCs |
| **Discord** | Real-time developer chat |
| **Email** | Security issues: security@swarm-agent.dev |

---

*Architecture Version: 2.0 | Last Updated: 2025-08-20*  
*Maintained by: Swarm Engineering Team*

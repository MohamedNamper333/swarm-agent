# C4 Model - Level 2: Container Diagram

```mermaid
graph TB
    subgraph "Swarm Enterprise Platform"
        subgraph "Control Plane"
            CP[Control Plane<br/>Admission, Policy, Budget]
        end
        
        subgraph "Orchestration"
            SM[SwarmMaster<br/>Pipeline Orchestrator]
            AR[Agent Registry<br/>Service Mesh]
            TD[Task Dispatcher<br/>Load Balancer]
        end
        
        subgraph "Execution"
            EP[Execution Plane<br/>Workers, Executors]
            SB[Sandbox Pool<br/>gVisor/Firecracker]
        end
        
        subgraph "Data"
            MEM[Memory V2 Fabric<br/>RAG + Context]
            JOBS[Job System<br/>Durable + DLQ]
        end
        
        subgraph "Security"
            AUTH[Auth Service<br/>RBAC + OAuth2]
            SEC[Security Manager<br/>DPoP + mTLS + HSM]
            AUDIT[Audit Log<br/>Immutable Chain]
        end
    end
    
    USER[User] -->|Request| SM
    SM -->|1. Validate| CP
    SM -->|2. Safety Check| AR
    SM -->|3. Route| TD
    TD -->|4. Execute| SB
    SB -->|5. Result| SM
    
    SM -->|Context| MEM
    SM -->|Enqueue| JOBS
    AUTH -->|Authorize| SM
    SEC -->|Encrypt/Sign| SM
    AUDIT -->|Log All Decisions| SM
```

## Containers

| Container | Technology | Responsibility | Scaling |
|-----------|-----------|----------------|---------|
| SwarmMaster | Python/asyncio | Pipeline orchestration (Safety→Board→CSuite→Route→Execute) | 3-10 replicas |
| Control Plane | Python | Admission control, policy enforcement, budget checks | 3 replicas |
| Agent Registry | In-process | Service mesh for agent discovery and health | Embedded |
| Task Dispatcher | In-process | Task routing with circuit breaker | Embedded |
| Execution Plane | Python/sandbox | Isolated code execution | 3-10 replicas |
| Sandbox Pool | gVisor/Firecracker | Strong isolation for user code | Auto-scaled |
| Memory V2 | Python + pluggable backend | Context assembly, RAG search | 3 replicas |
| Job System | Python + Redis/PostgreSQL | Durable job execution with compensation | Workers auto-scale |
| Auth Service | Python + JWT/OAuth2 | Authentication, RBAC, token management | 3 replicas |
| Security Manager | Python + cryptography | DPoP, mTLS, HSM, key rotation | 3 replicas |
| Audit Log | Python + SHA-256 chain | Immutable audit trail | Append-only |

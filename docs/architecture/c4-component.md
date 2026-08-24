# C4 Model - Level 3: Component Diagram (SwarmMaster)

```mermaid
graph TB
    subgraph "SwarmMaster"
        RV[RequestValidator]
        SG[SafetyGate]
        BC[BoardCoordinator]
        EC[ExecutiveCoordinator]
        RE[RoutingEngine]
        TD[TaskDispatcher]
        
        subgraph "Services"
            PS[PolicyService]
            BS[BudgetService]
            AS[AuthService]
            OS[OrchestrationService]
            RS[RoutingService]
        end
        
        SR[ServiceRegistry<br/>Lazy Loading via importlib]
    end
    
    USER[Request] --> RV
    RV -->|Valid| SG
    SG -->|Safe| BC
    BC -->|Approved| EC
    EC -->|Budget OK| RE
    RE -->|Routed| TD
    
    SG -.->|uses| PS
    EC -.->|uses| BS
    BC -.->|uses| AS
    TD -.->|uses| OS
    RE -.->|uses| RS
    
    PS --- SR
    BS --- SR
    AS --- SR
    OS --- SR
    RS --- SR
```

## Components

| Component | Responsibility | Dependencies (via Registry) |
|-----------|---------------|----------------------------|
| RequestValidator | Validates request format and size | None |
| SafetyGate | Runs safety department + policy check | PolicyService, SafetyDept |
| BoardCoordinator | Coordinates board deliberation (VETO power) | AuthService |
| ExecutiveCoordinator | C-Suite executive meeting + budget reservation | BudgetService, CostService |
| RoutingEngine | Routes to appropriate department | RoutingService |
| TaskDispatcher | Dispatches to agent with circuit breaker | OrchestrationService |
| ServiceRegistry | Lazy service lookup via `importlib.import_module()` | None (root) |

## Key Design Decision
All components access core services through the **ServiceRegistry** with lazy loading:
```python
service = self.service_registry.get("policy")  # Returns adapter
# Adapter lazily imports: from swarm.enterprise.core.policy.engine import PolicyEngine
```
This breaks circular imports and enables independent testing.

# ADR-003: Saga Pattern for Distributed Transactions

## Status
**Accepted** — 2025-08-24

## Context
Multi-step workflows (e.g., budget reservation → execution → audit logging) span multiple services. Traditional ACID transactions don't work across service boundaries. A failed step can leave the system in an inconsistent state.

## Decision
Use the Saga pattern with compensating transactions:

1. Each workflow step has a corresponding compensation action
2. If a step fails, all previously completed steps are compensated in reverse order
3. Compensation is idempotent and retriable

### Implementation
- `core/job/compensation.py` — CompensationEngine, WorkflowStep, WorkflowExecution
- `core/orchestration/workflow.py` — WorkflowEngine, SagaCoordinator

### Example Flow
```
Step 1: Reserve Budget → Compensate: Refund Budget
Step 2: Execute Code   → Compensate: Mark Failed  
Step 3: Log Audit      → Compensate: Mark Invalidated
```

## Consequences

### Positive
- System remains consistent even after partial failures
- Each step can be independently retried
- Clear recovery path for any failure scenario

### Negative
- Compensation logic must be carefully designed (no "undo" for side effects like API calls)
- Total failure handling adds latency to error paths
- Developers must think about compensation for every new operation

### Neutral
- Workflow state is persisted for observability
- Dead Letter Queue captures permanently failed compensations

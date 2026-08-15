# SWARM Competitive Architecture Program

> **Document Type:** Institutional Architecture Research + Build Blueprint
> **Status:** MEMORY DEEP DIVE COMPLETE / WORKFLOW ENGINE BUILD BLUEPRINT COMPLETE
> **Target Branch:** `main`
> **Single Source of Truth:** This is the only Markdown document for the competitive architecture program.
> **Execution Policy:** Research and architecture first. Implementation is explicitly deferred until the corresponding build blueprint is approved.

---

# 1. Program Mission

SWARM is being evolved into a production-grade **Governed Multi-Agent Operating Platform**.

The program does not replace SWARM with another framework and does not blindly copy another repository.

The governing rule is:

> **Benchmark the best → reverse-engineer the reason → identify trade-offs → adapt the principle → design the SWARM-native system → prove the design → implement later.**

The target system combines:

- Board/C-Suite governance;
- departmental specialization;
- Safety VETO;
- authoritative budget governance;
- durable workflow execution;
- high-integrity memory;
- reliable routing;
- distributed execution;
- observability and auditability;
- model/provider abstraction;
- human-in-the-loop control;
- enterprise security;
- explicit policy authority.

---

# 2. Operating Rules

1. No implementation is considered necessary merely because a benchmark project has a feature.
2. We copy **engineering principles**, never external implementation blindly.
3. Every benchmark must be analyzed for both strengths and failure modes.
4. Current SWARM behavior must be audited before designing replacement behavior.
5. Each subsystem receives a **Build Blueprint**, not a loose improvement checklist.
6. Implementation is deferred until the blueprint contains contracts, boundaries, state models, failure semantics, migration, tests, and acceptance criteria.
7. A design is not considered complete because it is elegant; it is complete when its invariants and operational behavior are explicit.

---

# 3. Benchmark Matrix

| Subsystem | Primary Benchmark | Secondary Benchmark | SWARM-Native Differentiator |
|---|---|---|---|
| Memory | Letta | LangGraph | Governance Memory + organizational scope |
| Workflow Engine | Microsoft Agent Framework | LangGraph | Governance-aware durable workflow |
| Stateful Execution | LangGraph | Microsoft Agent Framework | Policy-aware checkpoints |
| Agent Runtime | Microsoft Agent Framework | LangGraph | Board/C-Suite authority |
| Organizational Agents | MetaGPT | Microsoft Agent Framework | Enterprise hierarchy |
| Knowledge/RAG | LlamaIndex | Letta | Governed knowledge access |
| Observability | Microsoft Agent Framework / LangGraph ecosystem | — | Governance + budget telemetry |
| Model Runtime | Microsoft Agent Framework | LlamaIndex | Policy-driven model selection |
| HITL | LangGraph | Microsoft Agent Framework | Authority hierarchy |
| Safety | SWARM-native | External patterns | Safety VETO |
| Budget | SWARM-native | — | CFO authority |
| Governance | SWARM-native | Microsoft Agent Framework | Board/C-Suite authority |

Benchmarks are references, not automatic dependencies.

---

# 4. Global Architecture Principles

1. **Untrusted input never grants privilege.**
2. **Financial authority is server-side.**
3. **Budget reservations are atomic and concurrency-safe.**
4. **Approval is not execution success.**
5. **Every execution and side effect has globally unique identity.**
6. **Irreversible side effects are idempotent or explicitly protected.**
7. **Long-running work survives worker failure when durability is required.**
8. **Policy is evaluated before privileged action.**
9. **Execution state, memory, audit records, policy decisions, and artifacts are distinct state classes.**
10. **Evidence is required for completion.**
11. **No workflow may silently manufacture a successful result from a failed real execution.**
12. **Horizontal scaling must not multiply authoritative limits.**
13. **Every bounded resource must have explicit limits.**
14. **A benchmark's unresolved weaknesses must be considered part of its benchmark analysis.**

---

# 5. Target Evolution Matrix

| Domain | Target | Research / Build Principle |
|---|---:|---|
| Memory | 9.5/10 | Letta + LangGraph adaptation |
| Workflow Engine | 9.5/10 | MAF + LangGraph durable workflow model |
| Routing | 9/10 | Capability + confidence + ambiguity-aware routing |
| Durability | 9.5/10 | Durable jobs + checkpoints + recovery |
| Observability | 9.5/10 | Distributed tracing + governance/cost telemetry |
| Safety | 10/10 | Authoritative policy boundary |
| Governance | 10/10 | Formal authority and invariants |
| Budget | 10/10 | Atomic reservation + ledger + reconciliation |
| Inter-Agent Bus | 9/10 | Delivery semantics + dedup + retry + acknowledgement |
| Model Registry | 9.5/10 | Single authoritative registry |
| HITL | 9.5/10 | Durable approval state |
| Testing | 10/10 | Security + concurrency + chaos + recovery + property tests |

These scores are internal engineering targets, not objective industry rankings.

---

# 6. MEMORY DEEP DIVE — COMPLETED

## 6.1 Current MemoryEngine Baseline

The audited file is `swarm/core/memory_engine.py`.

The current implementation defines four memory layers:

```text
SCRATCHPAD
WORKING
EPISODIC
SEMANTIC
```

It also defines a `Lesson` abstraction.

The current engine stores its data in Python dictionaries/lists, uses `RLock` for local synchronization, generates identifiers using `int(time.time())`, and exposes placeholder Vault/Meilisearch integrations. The context builder currently includes scratchpad, working memory, and a small recent episodic slice but does not perform true semantic or lesson retrieval and does not enforce its `max_tokens` parameter. fileciteturn15file0L2-L7

### Positive foundations

- Memory is already conceptually layered.
- Task and agent metadata exists.
- Confidence/access metadata exists.
- Lessons are separated from normal entries.
- Local mutation protection exists.
- The code already anticipates external persistence/search boundaries.

### Critical findings

| ID | Finding | Severity | Build Direction |
|---|---|---|---|
| MEM-001 | Vault persistence is a stub | CRITICAL | Durable repository adapter |
| MEM-002 | Meilisearch is a stub | HIGH | Real indexing/search adapter |
| MEM-003 | Core stores are process-local | CRITICAL | Durable backend |
| MEM-004 | IDs use `int(time.time())` | HIGH | Global UUID/ULID/UUIDv7-style IDs |
| MEM-005 | No memory authorization boundary | CRITICAL | Policy-enforced reads/writes |
| MEM-006 | Provenance/tenant/execution metadata incomplete | CRITICAL | Full metadata envelope |
| MEM-007 | Semantic promotion condition is internally ineffective | HIGH | Explicit promotion lifecycle |
| MEM-008 | Semantic search is topic substring matching | HIGH | Real relevance retrieval |
| MEM-009 | Context assembly omits semantic/lesson retrieval | HIGH | Retrieval pipeline |
| MEM-010 | `max_tokens` is ignored | HIGH | Real token budgeting |
| MEM-011 | Mutable entries escape lock boundary | HIGH | Immutable snapshots / controlled mutation |
| MEM-012 | Confidence is caller-controlled | HIGH | Trust/provenance/calibration |
| MEM-013 | Lesson retrieval is substring matching | MEDIUM | Ranked/semantic retrieval |
| MEM-014 | Lesson application is only a counter | MEDIUM | Execution-linked audit |
| MEM-015 | No retention/deletion/revocation | CRITICAL | Lifecycle policy |
| MEM-016 | No poisoning/taint model | CRITICAL | Trust classification |
| MEM-017 | Governance authority is mixed with knowledge | CRITICAL | Dedicated Governance Memory |
| MEM-018 | `RLock` is not distributed consistency | CRITICAL | Versioning + CAS/transactions |
| MEM-019 | Checkpoint state is not separated from memory | HIGH | Dedicated checkpoint subsystem |
| MEM-020 | Failed persistence cannot be proven successful/unsuccessful | CRITICAL | Transactional write contract |
| MEM-021 | A parallel context subsystem exists | HIGH | Unified domain model, separate responsibilities |

## 6.2 Dependency Audit

The repository audit found:

- `swarm/core/__init__.py` exports `MemoryEngine`.
- `swarm/core/memory_engine.py` defines it.
- `tests/unit/test_memory_engine.py` directly tests it.
- No production module under the supplied `swarm/` tree was found importing or calling the main `MemoryEngine` methods.

Therefore the current `MemoryEngine` is effectively an **orphaned/unintegrated subsystem** rather than the proven production memory path.

A second context subsystem exists under `swarm/intelligence/context_manager.py` and is consumed by the context-compaction layer. The current architecture therefore has overlapping concepts:

```text
MemoryEngine
  SCRATCHPAD / WORKING / EPISODIC / SEMANTIC / LESSONS

ContextManager
  GLOBAL / TASK / AGENT / EPHEMERAL + snapshots + compaction
```

The target is one authoritative **Memory/Context domain model** with distinct responsibilities for:

- active execution context;
- durable memory;
- compaction;
- workflow checkpoints;
- governance records.

### Test evidence

The unit suite for the current MemoryEngine reports 16 passing tests in the audited environment. The Vault E2E path is not valid evidence of production persistence because the imported `vault_client` dependency is missing in the repository snapshot.

The existing tests prove local behavior; they do not prove distributed durability, authorization, memory poisoning resistance, or production persistence. fileciteturn17file0L2-L7

## 6.3 Letta — Principles Selected

Letta treats memory blocks as first-class context primitives with explicit labels/descriptions/values/limits, supports read-only blocks, and allows explicit attachment/detachment/shared access.

SWARM adopts these principles conceptually:

1. Explicit bounded working/core memory.
2. Memory semantics are part of the contract.
3. Read-only memory is a first-class capability.
4. Scope/attachment is explicit.
5. High-value information stays close to context; large/low-frequency knowledge stays in external retrieval.
6. Shared memory is explicitly authorized.

The important adaptation is that SWARM will **not** copy last-write-wins behavior for governance-sensitive memory; such state requires versions and conflict control.

## 6.4 LangGraph — Principles Selected

LangGraph provides an explicit separation between execution checkpoints and long-term memory stores, with namespaces and durable persistence/recovery semantics.

SWARM adopts:

1. **Checkpoint != Long-Term Memory.**
2. Durable execution state.
3. Namespaced long-term memory.
4. Explicit persistence contracts.
5. Recovery semantics.
6. Growth-control strategies for persistent state.

## 6.5 SWARM Memory V2 Target

```text
                         SWARM MEMORY FABRIC
                                  |
        +-------------------------+-------------------------+
        |                         |                         |
        v                         v                         v
  WORKING / CORE           EPISODIC / HISTORY        KNOWLEDGE / ARCHIVAL
        |                         |                         |
        +-------------------------+-------------------------+
                                  |
                                  v
                         GOVERNANCE MEMORY
                                  |
                                  v
                       MEMORY POLICY ENGINE
                                  |
             +--------------------+--------------------+
             |                    |                    |
             v                    v                    v
          SCOPE                 TRUST              RETENTION
             |                    |                    |
             +--------------------+--------------------+
                                  |
                                  v
                         AUTHORIZED RETRIEVAL
                                  |
                                  v
                         CONTEXT ASSEMBLER
                                  |
                                  v
                              AGENT/LLM
```

### Memory layers

**Working/Core:** bounded active context, critical task information, current plan, constraints, role context.

**Episodic:** execution history, outcomes, decisions, failures, lessons, causal links.

**Knowledge/Archival:** large or low-frequency durable information with lexical/semantic retrieval and metadata filters.

**Governance Memory:** Board/C-Suite decisions, safety VETO decisions, policy versions, budget approvals, human approvals, exceptions, governance evidence. Ordinary agents must not mutate this layer.

### Trust levels

```text
UNTRUSTED
EXTERNAL
AGENT_GENERATED
SYSTEM_DERIVED
VERIFIED
GOVERNANCE_AUTHORITY
```

Trust is metadata and evidence, not authorization.

### Memory invariants

1. Every write has a globally unique ID.
2. Every write is attributable to actor and execution.
3. Tenant/scope context is mandatory.
4. Trust/provenance are first-class.
5. Governance memory is protected.
6. Shared mutable state uses version/conflict semantics.
7. Failed persistence cannot be returned as successful.
8. Authorization precedes retrieval.
9. Context assembly has a real token budget.
10. Revoked/expired memory is excluded.
11. Relevance and authority are separate dimensions.
12. Memory cannot grant privilege.

### Status

Memory **research + architecture design + dependency audit are complete**. Implementation is intentionally deferred.

---

# 7. WORKFLOW ENGINE BUILD BLUEPRINT

## 7.1 Mission

The existing SWARM workflow subsystem should not merely be "improved". It should be transformed from a **DAG builder + per-agent FSM** into a proper **durable workflow runtime** capable of deterministic planning, concurrent execution, checkpointing, recovery, policy enforcement, human approval, observability, and safe retries.

The target is:

> **A policy-aware, durable, stateful, event-driven workflow engine specifically designed for SWARM's Board/C-Suite/Department/Agent organization.**

This is a **build blueprint**, not an implementation task.

---

## 7.2 Current SWARM Workflow Baseline

The primary workflow files audited are:

```text
swarm/core/task_dag.py
swarm/core/agent_state_machine.py
```

The current `task_dag.py` defines:

- `StageConfig`;
- `DAGNode`;
- `DAG`;
- `DAGBuilder`;
- task templates;
- stage libraries;
- topological ordering;
- a placeholder for parallel optimization.

Its templates include stages such as:

```text
analyze
ideate
design
implement
review
test
security_audit
optimize
document
verify
handoff
```

and the DAG adds sequential edges between consecutive stages. The `_optimize_parallelism()` method currently returns the DAG without implementing actual optimization. fileciteturn25file0L2-L7

The `AgentStateMachine` manages individual agent lifecycle states including `IDLE`, `ASSIGNED`, `SCRATCHPAD`, `EXECUTING`, `REVIEW_PENDING`, `APPROVED`, `REJECTED`, `BLOCKED`, `ERROR`, `TIMEOUT`, and `VETOED`. It is therefore an **agent lifecycle FSM**, not a durable workflow state machine. fileciteturn26file0L2-L7

---

## 7.3 Current Workflow Strengths

1. A DAG abstraction already exists.
2. Dependency ordering exists.
3. Cycle detection exists for sequential dependencies.
4. Task templates exist.
5. Stage metadata contains workers, outputs, and constitutional checks.
6. Agent lifecycle state is already modeled separately.
7. VETO is represented at agent state level.
8. The architecture already has the conceptual ingredients required for a richer runtime.

These are foundations, not evidence of a production workflow engine.

---

## 7.4 Current Workflow Gaps

| ID | Problem | Severity | Required Build Direction |
|---|---|---|---|
| WF-001 | `DAGBuilder` plans but does not execute durable workflows | CRITICAL | Build Workflow Runtime |
| WF-002 | Parallel optimization is a no-op | HIGH | Real scheduler/concurrency model |
| WF-003 | Current graph wiring is primarily sequential | HIGH | General dependency/branch/merge model |
| WF-004 | No authoritative workflow-level state object | CRITICAL | `WorkflowExecutionState` |
| WF-005 | No durable checkpoint system | CRITICAL | `CheckpointStore` |
| WF-006 | No restart/resume semantics | CRITICAL | Recovery runtime |
| WF-007 | Retry semantics are not workflow-native | CRITICAL | Retry policy + execution attempt state |
| WF-008 | Failure compensation is undefined | HIGH | Compensation policy |
| WF-009 | No workflow-level deadline propagation | HIGH | Deadline/deadline budget |
| WF-010 | Cancellation is not a first-class workflow state | HIGH | Cooperative cancellation |
| WF-011 | HITL is not durable workflow state | HIGH | Persistent approval gate |
| WF-012 | Policy decisions are not modeled as workflow gates | CRITICAL | Policy-aware edges/nodes |
| WF-013 | Budget reservation state is not part of workflow execution | CRITICAL | Budget reference + reservation lifecycle |
| WF-014 | Agent FSM and workflow state are not explicitly separated | HIGH | Separate boundaries |
| WF-015 | Events are not a first-class execution contract | HIGH | Workflow event model |
| WF-016 | Workflow validation is weak | HIGH | Compile-time/registration validation |
| WF-017 | Typed input/output contracts are absent at node boundary | HIGH | Schema-backed executor contracts |
| WF-018 | Subworkflow composition is not a first-class abstraction | MEDIUM | `SubWorkflowExecutor` |
| WF-019 | Side-effect idempotency is not workflow-enforced | CRITICAL | Idempotency policy per executor |
| WF-020 | Execution ownership/leases are undefined | CRITICAL | Worker lease model |
| WF-021 | Replay/time-travel semantics are absent | MEDIUM | Optional state history/replay |
| WF-022 | No durable event/audit linkage | HIGH | Correlated workflow event stream |
| WF-023 | Parallel execution lacks bounded resource governance | HIGH | Concurrency/resource quotas |
| WF-024 | Static template stage durations are not execution scheduling | MEDIUM | Remove false timing assumptions |

---

# 8. WORKFLOW BENCHMARK — MICROSOFT AGENT FRAMEWORK

## 8.1 What MAF contributes

Microsoft Agent Framework treats workflows as explicit directed structures made from executors and edges. It supports sequential and concurrent orchestration, branching/handoffs, events, workflow validation, checkpoints, human-in-the-loop patterns, and runtime observability. citeturn2search0turn2search1

### Principle A — Executor abstraction

An executor is a first-class processing unit, not merely a worker-name string.

**SWARM adaptation:**

```text
Executor
├── executor_id
├── type
├── input_schema
├── output_schema
├── capabilities
├── policy_requirements
├── retry_policy
├── timeout_policy
├── resource_policy
└── handler
```

Executor types should include at minimum:

- Agent;
- Tool;
- Function;
- Human Gate;
- Validator;
- Subworkflow;
- External Service.

### Principle B — Typed graph edges

Edges are part of the contract between executors rather than an unstructured tuple.

**SWARM adaptation:**

```text
WorkflowEdge
├── source_executor
├── target_executor
├── condition
├── message_schema
├── policy_gate
├── delivery_mode
├── retry_policy
└── failure_policy
```

### Principle C — Workflow validation before execution

A graph must be validated before it is admitted to runtime.

Validation should cover:

- connectivity;
- unreachable nodes;
- invalid cycles;
- missing entry/exit;
- message schema incompatibility;
- invalid policy references;
- invalid capabilities;
- unsupported executor types;
- conflicting resource constraints.

### Principle D — Events are first-class

The workflow runtime should emit structured events for state changes, executor lifecycle, outputs, errors, and policy gates.

### Principle E — Concurrent execution has synchronization semantics

MAF's superstep-style execution offers a useful model: gather eligible work, execute compatible work concurrently, establish a synchronization boundary, then move forward. This is useful for SWARM but should not be copied rigidly because long-running and asynchronous operations can require more granular progression.

### Principle F — Checkpoints are runtime infrastructure

Durability is part of workflow execution, not an optional memory feature.

---

# 9. WORKFLOW BENCHMARK — LANGGRAPH

## 9.1 What LangGraph contributes

LangGraph models applications around explicit graph state, nodes, edges, persistence/checkpoints, interrupts, and recovery. Its persistence system separates execution checkpoints from longer-lived memory stores and supports replay/time-travel-oriented workflows. citeturn3search0turn3search1

### Principle A — Explicit workflow state

The runtime should operate on a typed state object rather than scattered node-local dictionaries.

### Principle B — Checkpoint after meaningful state transitions

The system needs durable recovery boundaries.

### Principle C — Resume is a native operation

The runtime should have an explicit:

```text
resume(execution_id, checkpoint_id)
```

semantic rather than requiring callers to recreate a workflow manually.

### Principle D — Interrupts are state transitions

Human approval, manual correction, or policy interruption must become durable workflow state.

### Principle E — Thread/execution identity is first-class

Every run must have stable identity and state history.

### Principle F — Workflow history must be queryable

A production orchestrator needs:

- current state;
- prior checkpoints;
- events;
- failed attempts;
- recovery decisions.

### Important adaptation

SWARM should not become a LangGraph clone. Its state model must additionally represent:

- Board authority;
- C-Suite authority;
- safety VETO;
- budget reservation;
- department authority;
- tool capability policy.

---

# 10. SWARM WORKFLOW ENGINE V2 — TARGET ARCHITECTURE

```text
                         SWARM WORKFLOW ENGINE V2
                                      |
                 +--------------------+--------------------+
                 |                    |                    |
                 v                    v                    v
        Workflow Definition      Validator/Compiler     Policy Engine
                 |                    |                    |
                 +--------------------+--------------------+
                                      |
                                      v
                              Workflow Runtime
                                      |
             +------------------------+------------------------+
             |                        |                        |
             v                        v                        v
       Scheduler                 State Store              Event Stream
             |                        |                        |
             v                        v                        v
       Executor Runtime          Checkpoint Store         Audit/Telemetry
             |
      +------+------+------+------+------+------+
      |      |      |      |      |      |
    Agent   Tool   Func   Human  Validator Subworkflow External
```

---

# 11. WORKFLOW DOMAIN MODEL

## 11.1 WorkflowDefinition

A versioned immutable declaration of the workflow.

```text
WorkflowDefinition
├── workflow_id
├── version
├── entrypoints
├── executors
├── edges
├── state_schema
├── policies
├── resources
├── deadlines
├── retry_defaults
├── cancellation_policy
└── metadata
```

A published definition should be immutable.

If the design changes:

```text
workflow_id = same
version = incremented
```

An active execution retains the version with which it started.

## 11.2 WorkflowExecution

```text
WorkflowExecution
├── execution_id
├── workflow_id
├── workflow_version
├── tenant_id
├── actor_id
├── status
├── started_at
├── updated_at
├── deadline
├── current_nodes
├── completed_nodes
├── failed_nodes
├── waiting_nodes
├── attempt_count
├── checkpoint_id
├── policy_context
├── budget_reference
├── cancellation_state
└── result_reference
```

## 11.3 NodeExecution

Each executor invocation gets its own execution record.

```text
NodeExecution
├── node_execution_id
├── execution_id
├── executor_id
├── attempt
├── state
├── input_reference
├── output_reference
├── started_at
├── completed_at
├── deadline
├── retry_state
├── error_code
├── policy_decision
└── idempotency_key
```

---

# 12. WORKFLOW STATE MACHINE

The workflow engine must have a dedicated state machine.

Recommended states:

```text
CREATED
VALIDATING
REJECTED
READY
RUNNING
WAITING
WAITING_APPROVAL
PAUSED
PARTIAL
RETRYING
CANCEL_REQUESTED
CANCELLED
FAILED
COMPLETED
EXPIRED
RECOVERY_REQUIRED
```

### Important separation

```text
Workflow State
      !=
Agent State
      !=
Policy State
      !=
Budget State
      !=
Memory State
```

They may reference each other but must not collapse into one enum.

---

# 13. EXECUTOR MODEL

Executors are the actual units of work.

## Required executor contract

```text
ExecutorContract
├── identity
├── capability declaration
├── input validation
├── output validation
├── execution handler
├── timeout policy
├── retry policy
├── idempotency policy
├── resource limits
└── policy requirements
```

### Agent Executor

Wraps an SWARM agent while preserving AgentStateMachine semantics.

### Tool Executor

Invokes an external/internal tool and must be capability-authorized.

### HumanGate Executor

Moves workflow into a durable `WAITING_APPROVAL` state.

### Validator Executor

Validates state/output and can fail or branch execution.

### Subworkflow Executor

Starts a child workflow with a parent execution reference.

---

# 14. GRAPH MODEL

The graph must support:

- sequential edges;
- conditional edges;
- fan-out;
- fan-in;
- parallel branches;
- error branches;
- compensation branches;
- approval branches;
- subworkflow edges;
- terminal edges.

An edge is not simply:

```python
(from_stage, to_stage, edge_type)
```

It is a typed execution contract.

---

# 15. GRAPH VALIDATION

Workflow admission must reject invalid definitions.

### Structural validation

- duplicate node IDs;
- undefined edge targets;
- unreachable nodes;
- invalid cycles;
- missing entrypoint;
- missing terminal path;
- invalid branch/merge configuration.

### Contract validation

- input/output schema compatibility;
- capability availability;
- policy references;
- resource limits;
- retry rules;
- deadline compatibility.

### Governance validation

- privileged executor has policy reference;
- budgeted operation has budget policy;
- human gate has approval authority;
- safety-sensitive nodes cannot bypass Safety policy.

---

# 16. SCHEDULER DESIGN

## Objective

Select which eligible node executions can run without violating:

- graph dependencies;
- policy;
- budget;
- resource quotas;
- concurrency limits;
- deadlines;
- tenant quotas;
- executor availability.

### Scheduling cycle

```text
Load Execution State
        |
Determine Ready Nodes
        |
Evaluate Policy
        |
Evaluate Resources
        |
Evaluate Budget
        |
Create Node Execution Attempts
        |
Dispatch Eligible Work
        |
Collect Results/Events
        |
Commit State
        |
Checkpoint
        |
Repeat
```

---

# 17. PARALLEL EXECUTION

Parallelism must be a real runtime behavior, not a metadata flag.

Example:

```text
                +--> Research A --+
Start ----------+--> Research B --+--> Synthesis
                +--> Research C --+
```

The scheduler must ensure:

- all branches have durable execution IDs;
- concurrency is bounded;
- partial branch failure semantics are explicit;
- fan-in does not run before required inputs are valid;
- duplicate retries are idempotent;
- branch results are traceable.

### Synchronization model

SWARM may use bounded synchronization points inspired by MAF supersteps, but must allow long-running/human/asynchronous nodes to remain independently durable instead of blocking an entire workflow unnecessarily.

---

# 18. CHECKPOINTING

Checkpoint is an execution primitive.

## Checkpoint content

```text
Checkpoint
├── checkpoint_id
├── execution_id
├── workflow_version
├── state_snapshot
├── active_nodes
├── completed_nodes
├── waiting_nodes
├── pending_writes
├── policy_references
├── budget_reference
├── retry_state
├── deadline
├── schema_version
├── created_at
└── checksum/hash
```

## Checkpoint rules

1. Every durable execution has checkpoints.
2. Checkpoints are immutable records.
3. A new checkpoint references its predecessor.
4. Resume selects a specific checkpoint.
5. Checkpoint schema is versioned.
6. Sensitive data is encrypted/protected according to classification.
7. Failed checkpoint write must not silently advance execution state.

---

# 19. RECOVERY / RESUME

A worker crash must result in:

```text
Worker failure
      |
Lease expires / failure detected
      |
Execution becomes RECOVERY_REQUIRED
      |
Load latest valid checkpoint
      |
Validate checkpoint
      |
Reconcile completed side effects
      |
Reconstruct ready nodes
      |
Resume
```

Recovery must never blindly replay irreversible side effects.

---

# 20. RETRY MODEL

Every executor declares whether its failure is retryable.

### Retry policy

```text
retryable
max_attempts
backoff
jitter
deadline
retry_budget
```

### Example

```text
Validation error       -> no retry
Authorization denied   -> no retry
Budget exceeded        -> no retry
Transient provider 5xx -> bounded retry
Rate limit             -> retry with server guidance/backoff
Timeout                -> bounded retry if safe
Unknown internal      -> limited retry + alert
```

Retry must be tied to an idempotency policy.

---

# 21. FAILURE AND COMPENSATION

Not every workflow can simply retry.

Each side-effecting executor declares:

```text
retry strategy
compensation strategy
reconciliation strategy
manual recovery strategy
```

Example:

```text
External operation succeeded
     |
Worker crashed before commit
     |
Recovery checks external idempotency/status
     |
Commit or compensate
```

The engine must distinguish:

```text
NOT_STARTED
STARTED_UNKNOWN
SUCCEEDED
FAILED
COMPENSATED
```

---

# 22. DEADLINES AND TIMEOUTS

The workflow owns an overall deadline.

Child executors receive a remaining-time budget rather than unrelated arbitrary timers.

```text
Workflow Deadline = 60 min
        |
        +-- Node A = remaining budget
        +-- Node B = remaining budget
        +-- Node C = remaining budget
```

A node may have a shorter local timeout but must never exceed workflow deadline.

---

# 23. CANCELLATION

Cancellation is durable workflow state.

```text
RUNNING
   |
CANCEL_REQUESTED
   |
+--+----------------+
|                   |
cooperative stop    non-cancellable side effect
|                   |
CANCELLED        RECONCILE
```

A cancellation request must be traceable and idempotent.

---

# 24. HUMAN-IN-THE-LOOP

Human approval is a workflow executor/state, not a boolean field.

```text
WAITING_APPROVAL
        |
 +------+------+
 |             |
APPROVED     REJECTED
 |             |
READY         FAILED/REJECTED
```

Approval record:

```text
approval_id
execution_id
node_execution_id
requester
approver
authority
policy_version
requested_action
reason
created_at
expires_at
decision
```

An approval does not bypass revalidation at execution time.

---

# 25. POLICY INTEGRATION

Every privileged executor or edge can reference policies.

Policy decisions:

```text
ALLOW
DENY
REQUIRE_APPROVAL
VETO
```

The workflow runtime must not implement the details of Safety/Budget/Authorization policy. It asks the authoritative policy engine for a decision and records the decision reference.

### Example

```text
Ready node
   |
Policy Engine
   |
+--+---------+---------+
ALLOW    APPROVAL    VETO
 |          |           |
run      wait         stop
```

---

# 26. BUDGET INTEGRATION

The workflow engine must not calculate authoritative prices itself.

Instead:

```text
Node ready
   |
Cost estimation service
   |
Budget reservation
   |
ALLOW / DENY
   |
Execution
   |
Actual usage reconciliation
```

Each `NodeExecution` references its budget reservation.

If budget reservation fails, the node must not start.

---

# 27. MEMORY INTEGRATION

Workflow and Memory must remain separate domains.

Workflow uses Memory through explicit operations:

```text
load_context()
write_episode()
retrieve_knowledge()
record_outcome()
```

Workflow checkpoint state is never automatically written into long-term memory as knowledge.

Likewise, retrieved memory cannot mutate workflow authority.

---

# 28. EVENT MODEL

Every major workflow transition emits an immutable event.

```text
WorkflowCreated
WorkflowValidated
WorkflowStarted
NodeReady
NodeStarted
NodeCompleted
NodeFailed
NodeRetryScheduled
PolicyEvaluated
ApprovalRequested
ApprovalReceived
CheckpointCreated
CheckpointRestored
WorkflowPaused
WorkflowResumed
WorkflowCancelled
WorkflowCompleted
WorkflowFailed
RecoveryRequired
```

Event envelope:

```text
Event
├── event_id
├── event_type
├── execution_id
├── workflow_id
├── workflow_version
├── node_execution_id
├── actor
├── timestamp
├── correlation_id
├── causation_id
├── schema_version
└── payload
```

---

# 29. OBSERVABILITY

Tracing hierarchy:

```text
Workflow Trace
  ├── Node Span
  │    ├── Agent Span
  │    ├── Model Span
  │    ├── Tool Span
  │    └── Memory Span
  └── Policy/Budget Spans
```

Metrics must include:

- workflow success/failure;
- node success/failure;
- p50/p95/p99 latency;
- queue/scheduler latency;
- retries;
- recovery count;
- checkpoint duration;
- waiting/approval time;
- budget consumption;
- executor saturation;
- concurrency;
- cancellation;
- partial executions.

---

# 30. DISTRIBUTED EXECUTION

The final runtime must support multiple workers without changing workflow semantics.

Required concepts:

- durable execution IDs;
- worker leases;
- heartbeats;
- ownership expiration;
- duplicate-delivery protection;
- idempotency keys;
- durable scheduler state;
- distributed concurrency limits;
- tenant quotas.

Process-local dictionaries are not authoritative workflow state.

---

# 31. SECURITY MODEL

Workflow security boundaries:

1. Caller cannot directly modify workflow state.
2. Caller cannot skip policy gates.
3. Caller cannot choose privileged executors without authorization.
4. Workflow definitions are immutable after publication.
5. Workflow execution belongs to an authorized tenant/scope.
6. Executor input is validated.
7. Tool side effects are capability-controlled.
8. Checkpoints cannot become privilege escalation artifacts.
9. Replay/resume requires execution authorization.
10. Audit events cannot be silently rewritten.

---

# 32. RESOURCE GOVERNANCE

Every workflow may declare or inherit limits:

```text
max_runtime
max_nodes
max_depth
max_parallelism
max_agent_calls
max_tool_calls
max_tokens
max_cost
max_retries
max_subworkflows
```

A workflow exceeding a hard limit must transition to an explicit resource failure state rather than continuing indefinitely.

---

# 33. SUBWORKFLOWS

A workflow can call another workflow through a first-class `SubworkflowExecutor`.

Parent-child relationship:

```text
Parent Execution
      |
      +--> Child Execution
               |
               +--> Child checkpoints
               +--> Child events
               +--> Child result
```

Required controls:

- depth limit;
- tenant inheritance;
- policy inheritance/override rules;
- budget propagation;
- deadline propagation;
- cancellation propagation;
- parent-child correlation.

---

# 34. VERSIONING

Workflow definitions are immutable once published.

Execution always stores:

```text
workflow_id
workflow_version
```

An execution never silently switches to a newer workflow definition.

Schema versions apply independently to:

- workflow definition;
- workflow state;
- checkpoint;
- event;
- executor message.

---

# 35. PERFORMANCE MODEL

Performance should be measured, not guessed.

Required benchmark dimensions:

- graph compilation latency;
- scheduling latency;
- node dispatch latency;
- checkpoint latency;
- state serialization cost;
- event emission latency;
- recovery latency;
- concurrent workflows;
- concurrent nodes;
- memory footprint;
- throughput under provider latency.

Target SLOs must be defined after baseline measurement.

---

# 36. TESTING STRATEGY

## Unit

- graph validation;
- state transitions;
- edge conditions;
- scheduler decisions;
- retry policy;
- timeout calculations;
- policy gate handling.

## Integration

- checkpoint backend;
- worker lease;
- event store;
- policy engine;
- budget reservation;
- memory context;
- executor adapters.

## Concurrency

- duplicate workers;
- parallel branches;
- fan-in races;
- lease races;
- cancellation races;
- budget races.

## Failure

- worker crash;
- provider outage;
- checkpoint failure;
- event sink failure;
- policy backend unavailable;
- budget backend unavailable.

## Recovery

- resume from latest checkpoint;
- resume after partial branch completion;
- retry safe nodes;
- reconcile side effects;
- prevent duplicate execution.

## Security

- workflow injection;
- unauthorized resume;
- unauthorized executor;
- policy bypass;
- tenant isolation;
- malicious executor input.

## Load/Chaos

- many concurrent workflows;
- large DAG;
- long-running nodes;
- random worker termination;
- dependency failure;
- event-store degradation.

---

# 37. MIGRATION STRATEGY

The existing DAG builder should not be deleted immediately.

### Stage 1 — Domain introduction

Add the conceptual contracts:

```text
WorkflowDefinition
WorkflowExecution
NodeExecution
WorkflowEdge
ExecutorContract
Checkpoint
WorkflowEvent
```

### Stage 2 — Compatibility adapter

Represent current `StageConfig` and `DAGBuilder` output as a legacy workflow definition.

### Stage 3 — Validator/compiler

Compile legacy definitions into the new execution model.

### Stage 4 — Runtime

Introduce the durable scheduler/executor runtime.

### Stage 5 — State separation

Separate:

- AgentStateMachine;
- WorkflowStateMachine;
- Policy state;
- Budget state;
- Memory;
- Checkpoints.

### Stage 6 — Replace old execution path

Move real production execution to the new runtime.

### Stage 7 — Deprecate legacy DAG runtime behavior

Only after compatibility, integration, recovery, and performance are verified.

---

# 38. ROLLBACK STRATEGY

The rollout must support safe rollback.

Required:

- workflow version pinning;
- feature flag/route selection;
- legacy adapter;
- state migration compatibility;
- event compatibility;
- checkpoint compatibility;
- explicit rollback criteria.

Rollback must not orphan in-flight executions.

---

# 39. WORKFLOW BUILD ORDER

```text
Phase W0 — Domain Contracts
        |
Phase W1 — Workflow Definition + Validation
        |
Phase W2 — Execution State Machine
        |
Phase W3 — Executor Runtime
        |
Phase W4 — Scheduler + Parallelism
        |
Phase W5 — Checkpoint Store
        |
Phase W6 — Retry/Timeout/Cancel/Recovery
        |
Phase W7 — Policy + Budget + HITL Gates
        |
Phase W8 — Events + Observability
        |
Phase W9 — Distributed Workers
        |
Phase W10 — Migration + Production Verification
```

Implementation is intentionally not included in this program phase.

---

# 40. WORKFLOW ACCEPTANCE CRITERIA

Workflow V2 can be marked `VERIFIED` only when:

1. A workflow definition is versioned and validated before execution.
2. Executors have typed contracts.
3. Graph edges support conditional/parallel/fan-in/fan-out semantics.
4. Workflow state is authoritative and durable.
5. Checkpoints are immutable and recoverable.
6. A crashed worker can be replaced without losing the workflow.
7. Duplicate worker delivery cannot cause unsafe duplicate side effects.
8. Retry rules are explicit and bounded.
9. Deadlines propagate.
10. Cancellation is durable.
11. HITL is durable.
12. Policy gates are authoritative.
13. Budget reservation occurs before protected execution.
14. Events provide a complete execution trail.
15. Observability links workflow → node → agent → model/tool.
16. Distributed workers preserve execution semantics.
17. Resource limits are enforced.
18. Security tests demonstrate privilege boundaries.
19. Chaos/recovery tests pass.
20. At least one real production workflow runs entirely on the new runtime.

---

# 41. WORKFLOW COMPETITIVE SCORECARD

| Capability | SWARM Current | Benchmark Principle | SWARM V2 Target |
|---|---:|---|---:|
| DAG definition | 7/10 | MAF/LangGraph graph model | 10/10 |
| Workflow state | 4/10 | LangGraph state model | 10/10 |
| Runtime execution | 3/10 | MAF executor runtime | 10/10 |
| Parallelism | 3/10 | MAF concurrency | 10/10 |
| Checkpointing | 1/10 | MAF + LangGraph persistence | 10/10 |
| Recovery | 1/10 | LangGraph resume semantics | 10/10 |
| HITL | 4/10 | MAF/LangGraph interrupts | 10/10 |
| Policy integration | 5/10 | SWARM-native | 10/10 |
| Budget integration | 4/10 | SWARM-native | 10/10 |
| Observability | 4/10 | MAF/LangGraph ecosystems | 9.5/10 |
| Distributed execution | 3/10 | Durable worker runtime principles | 9.5/10 |
| Governance | 9/10 | SWARM-native | 10/10 |

These scores are internal assessment targets, not vendor claims.

---

# 42. CURRENT PROGRAM STATUS

| Workstream | Status |
|---|---|
| Benchmark matrix | COMPLETE |
| Memory source audit | COMPLETE |
| Memory dependency audit | COMPLETE |
| Letta analysis | COMPLETE |
| LangGraph memory analysis | COMPLETE |
| Memory V2 architecture | COMPLETE |
| Workflow source audit | COMPLETE |
| Microsoft Agent Framework workflow analysis | COMPLETE |
| LangGraph workflow analysis | COMPLETE |
| Workflow V2 build blueprint | COMPLETE |
| Memory implementation | DEFERRED |
| Workflow implementation | DEFERRED |
| Production integration | DEFERRED |
| Verification | DEFERRED until implementation |

---

# 43. NEXT SUBSYSTEM

After Workflow Engine, the program proceeds using the same methodology to the next benchmark domain.

Planned order after workflow:

```text
Routing
→ Durability / Distributed Execution
→ Observability
→ Safety
→ Budget Governance
→ Model Runtime
→ Inter-Agent Communication
→ HITL
→ Enterprise Security
→ Testing / Verification
```

Each subsystem receives a Build Blueprint before implementation is allowed.

---

# 44. Final Program Rule

> **Take the best principle. Understand the trade-off. Adapt it to SWARM. Improve the weaknesses. Build only after the blueprint is complete. Prove the result after implementation.**

This document remains the single source of truth for the SWARM Competitive Architecture Program.

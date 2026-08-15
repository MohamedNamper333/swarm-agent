# SWARM Competitive Architecture Program

> **Status:** MEMORY DEEP DIVE — DEPENDENCY AUDIT COMPLETE / IMPLEMENTATION SPECIFICATION NEXT
> **Target Branch:** `main`
> **Single Source of Truth:** This document is the only MD document for the competitive architecture program.

## 1. Executive Objective

SWARM will not be replaced by another framework and will not blindly copy another codebase.

> **Benchmark the best → reverse-engineer the reason → identify trade-offs → adapt the principle → implement in SWARM → verify with measurable evidence.**

The target is a production-grade **Governed Multi-Agent Operating Platform** combining Board/C-Suite governance, departmental specialization, safety VETO, authoritative budget control, durable execution, strong memory, reliable routing, distributed execution, observability, model abstraction, human-in-the-loop controls, and enterprise security.

## 2. Non-Negotiable Methodology

Every subsystem follows:

1. Audit the current implementation at file/class/function/data-flow level.
2. Select the strongest relevant benchmark.
3. Reverse-engineer architecture, abstractions, lifecycle, state, failure handling, and tests.
4. Extract the decisions responsible for the advantage.
5. Analyze limitations and trade-offs.
6. Adapt the principle to SWARM rather than copying implementation.
7. Define contracts, invariants, state transitions, and boundaries.
8. Define exact implementation changes.
9. Define migration and rollback.
10. Define validation and measurable acceptance criteria.
11. Verify with evidence.

**Critical rule:** surface-level copying is prohibited. A benchmark is a source of engineering principles, not a source of code to clone.

## 3. Benchmark Matrix

| Subsystem | Primary Benchmark | Secondary Benchmark | SWARM Native Advantage |
|---|---|---|---|
| Memory | Letta | LangGraph | Governance Memory + organizational scope |
| Stateful Execution | LangGraph | Microsoft Agent Framework | Governance-aware checkpoints |
| Workflow | LangGraph | Microsoft Agent Framework | Policy-aware orchestration |
| Agent Runtime | Microsoft Agent Framework | LangGraph | Board/C-Suite governance |
| Organizational Agents | MetaGPT | Microsoft Agent Framework | Enterprise hierarchy |
| Knowledge/RAG | LlamaIndex | Letta | Governed knowledge access |
| Observability | Microsoft Agent Framework / LangGraph ecosystem | — | Governance + cost telemetry |
| Model Runtime | Microsoft Agent Framework | LlamaIndex | Policy-driven model selection |
| HITL | LangGraph | Microsoft Agent Framework | Authority hierarchy |
| Safety | SWARM-native | External patterns | Safety VETO |
| Budget | SWARM-native | — | CFO authority |
| Governance | SWARM-native | Microsoft Agent Framework | Board/C-Suite authority |

Benchmarks are references, not default dependencies.

## 4. Architecture Principles

1. Untrusted input never grants privilege.
2. Financial authority is server-side.
3. Budget reservations are atomic and concurrency-safe.
4. Approval is not execution success.
5. Every execution and side effect has globally unique identity.
6. Irreversible side effects are idempotent/retry-safe.
7. Long-running execution survives worker failure.
8. Policy is evaluated before privileged action.
9. Execution state, memory, audit, policy decisions, and artifacts are distinct state classes.
10. Completion requires evidence, not a passing demo.

## 5. Competitive Evolution Matrix

| Domain | Target | Primary Work |
|---|---:|---|
| Memory | 9.5/10 | Letta + LangGraph adaptation |
| Workflow | 9.5/10 | Durable graph/state execution |
| Routing | 9/10 | Capability + confidence + ambiguity-aware routing |
| Durability | 9.5/10 | Checkpoints + jobs + recovery |
| Observability | 9.5/10 | Tracing + cost/token telemetry + audit correlation |
| Safety | 10/10 | Authoritative policy boundary |
| Governance | 10/10 | Formal authority/invariants |
| Budget | 10/10 | Atomic reservations + ledger + reconciliation |
| Inter-Agent Bus | 9/10 | Delivery semantics + dedup + retry + acknowledgement |
| Model Registry | 9.5/10 | Single authoritative registry |
| HITL | 9.5/10 | Durable approvals + enforcement |
| Testing | 10/10 | Concurrency + chaos + property + recovery |

Scores are engineering targets, not objective industry rankings.

# 6. MEMORY DEEP DIVE

## 6.1 Current MemoryEngine Audit

The audited file is `swarm/core/memory_engine.py`. It declares four layers: `SCRATCHPAD`, `WORKING`, `EPISODIC`, and `SEMANTIC`. `MemoryEntry` stores identity, layer, task, agent, content, timestamps, tags, confidence, and access metadata. `Lesson` stores task/agent, pattern, lesson, confidence, creation time, and application count.

### Strengths

- Correct recognition that memory needs multiple layers.
- Explicit task/agent metadata.
- Confidence and access metadata.
- Separate lesson abstraction.
- Basic local synchronization through `RLock`.
- Intended integration boundary for Vault and search.

### Critical Findings

| ID | Finding | Severity | Required Direction |
|---|---|---|---|
| MEM-001 | Vault persistence is a stub | CRITICAL | Real repository adapter with durable transactions |
| MEM-002 | Meilisearch integration is a stub | HIGH | Real indexing/search adapter |
| MEM-003 | Core stores are process-local | CRITICAL | Durable production backend |
| MEM-004 | IDs use `int(time.time())` | HIGH | UUID/ULID/UUIDv7-style global IDs |
| MEM-005 | No authorization boundary | CRITICAL | Policy-enforced reads/writes |
| MEM-006 | No tenant/execution/policy provenance envelope | CRITICAL | Full provenance metadata |
| MEM-007 | Semantic promotion condition is effectively unreachable | HIGH | Explicit promotion lifecycle |
| MEM-008 | `search_semantic()` is topic substring matching | HIGH | Real relevance retrieval |
| MEM-009 | `build_context()` does not retrieve semantic/lesson memory | HIGH | Relevance-driven context assembly |
| MEM-010 | `max_tokens` is ignored | HIGH | Real token accounting/budgeting |
| MEM-011 | Mutable entries escape the lock boundary | HIGH | Immutable snapshots / controlled mutation |
| MEM-012 | Confidence is caller-controlled | HIGH | Trust/calibration/provenance model |
| MEM-013 | Lesson retrieval is substring matching | MEDIUM | Ranked/semantic lesson retrieval |
| MEM-014 | Lesson application is only a counter | MEDIUM | Application audit + outcome linkage |
| MEM-015 | No retention/deletion/revocation lifecycle | CRITICAL | Lifecycle policy |
| MEM-016 | No poisoning/taint model | CRITICAL | Trust classification + enforcement |
| MEM-017 | Knowledge and governance authority are not separated | CRITICAL | Dedicated Governance Memory boundary |
| MEM-018 | `RLock` is not distributed consistency | CRITICAL | Versioning + CAS/transaction semantics |
| MEM-019 | Checkpoint state is not separated architecturally | HIGH | Dedicated execution checkpoint subsystem |
| MEM-020 | Failed persistence cannot be distinguished from success | CRITICAL | Transactional write contract |
| MEM-021 | A second context subsystem exists outside MemoryEngine | HIGH | Unify context/memory contracts without duplicating responsibilities |

### Source-level evidence

The implementation stores scratchpad/working/episodic/semantic/lessons in Python dictionaries/lists. IDs are generated with `int(time.time())`. `save_to_vault()` and `load_from_vault()` contain no serialization or I/O, while `search_meilisearch()` returns an empty list. `build_context()` retrieves scratchpad and working data plus the last five episodes, but leaves semantic and lesson sections empty. `max_tokens` is accepted but never enforced.

The current `record_episode()` immediately calls `_maybe_promote_to_semantic()`, but the promotion predicate requires `access_count >= 3` while a newly created entry has `access_count == 0`. No access increment is performed before that call.

## 6.2 Dependency Audit — Completed

A full repository search was performed against the supplied repository snapshot.

### 6.2.1 Direct MemoryEngine consumers

The result is architecturally important:

- `swarm/core/__init__.py` exports `MemoryEngine`.
- `swarm/core/memory_engine.py` defines it.
- `tests/unit/test_memory_engine.py` is its direct unit-test suite.
- No production module under `swarm/` was found importing or calling `MemoryEngine` methods such as `build_context()`, `record_episode()`, `update_working()`, `search_semantic()`, or `get_relevant_lessons()`.

**Conclusion:** the current `MemoryEngine` is effectively an **orphaned/unintegrated subsystem**. It exists as a public core component and has tests, but the repository snapshot does not demonstrate a production execution path that actually depends on it.

This changes the migration strategy: do not perform a blind in-place rewrite and assume the whole system will use it. First establish the authoritative memory contract, then integrate the new service into the real execution path.

### 6.2.2 Parallel Context System

`swarm/intelligence/context_manager.py` defines `HierarchicalContextManager` with GLOBAL/TASK/AGENT/EPHEMERAL scopes, TTLs, priorities, snapshots, and disk-backed JSON state. `swarm/intelligence/context_compactor.py` actively consumes this manager.

This means SWARM currently has **two overlapping state/context concepts**:

```text
MemoryEngine
  SCRATCHPAD / WORKING / EPISODIC / SEMANTIC / LESSONS

ContextManager
  GLOBAL / TASK / AGENT / EPHEMERAL + snapshots + compaction
```

The correct solution is not to keep both as independent long-term memory systems. V2 must define one authoritative **Memory/Context domain model** with a clear separation between:

- active execution context;
- durable memory;
- context compaction;
- execution checkpoints;
- governance records.

### 6.2.3 Vault Dependency

`swarm/api/rest_server.py` exposes a `/vault/search` proxy and reads `VAULT_SERVER_URL` and `VAULT_API_KEY`. `config_loader.py` exposes Vault configuration. However, the supplied repository snapshot contains no `vault_client.py` or `vault_server.py` at the project root even though `tests/e2e/test_vault_integration.py` imports and executes them.

Therefore the E2E Vault test cannot currently be treated as proof that MemoryEngine persistence works.

### 6.2.4 Meilisearch Dependency

`pyproject.toml` has no Meilisearch dependency. The MemoryEngine only contains placeholder methods and does not demonstrate a configured client, index lifecycle, schema/settings, consistency mechanism, or recovery process.

### 6.2.5 Test Evidence

`pytest -q tests/unit/test_memory_engine.py` completed with **16 passed**.

`pytest -q tests/unit/test_memory_engine.py tests/e2e/test_vault_integration.py` failed during collection because `vault_client` is missing:

```text
ModuleNotFoundError: No module named 'vault_client'
```

This is an important distinction:

> The MemoryEngine unit tests passing proves current local behavior, not production durability, distributed correctness, authorization, or persistence correctness.

## 6.3 Letta Benchmark — Principles to Adapt

Letta treats memory blocks as first-class context primitives. Blocks have explicit labels/descriptions/values/limits, can be read-only, and can be attached/detached or shared. Its context hierarchy separates small high-value in-context memory from larger archival/external retrieval.

SWARM should adopt:

1. Explicit bounded core/working memory.
2. Semantic descriptions as part of memory contracts.
3. Read-only memory for authoritative information.
4. Explicit attachment/scope semantics.
5. Hierarchical placement based on importance and size.
6. Shared memory only through explicit access boundaries.

Do **not** copy Letta's last-write-wins behavior for governance-sensitive shared state; concurrent writers require version/conflict control.

## 6.4 LangGraph Benchmark — Principles to Adapt

LangGraph explicitly separates thread/execution checkpoints from long-term memory stores and uses namespaces for durable memory. Checkpoints support persistence, recovery, HITL, and resumability.

SWARM should adopt:

1. **Checkpoint != Long-Term Memory.**
2. Durable execution state.
3. Namespaced long-term memory.
4. Explicit persistence contracts.
5. Recovery semantics.
6. Intermediate-write recovery where appropriate.
7. Storage-growth policies.

## 6.5 SWARM Memory V2 Architecture

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

### Working/Core Memory

Small, high-value, immediately available information: current objective, active plan, constraints, role context, and critical project facts. It must be bounded, scoped, versioned, and optionally read-only.

### Episodic Memory

Durable execution history: observations, decisions, failures, outcomes, lessons, and causal links.

### Knowledge/Archival Memory

Large or low-frequency durable information with lexical/semantic retrieval, metadata filtering, namespace filtering, permission filtering, relevance ranking, and provenance.

### Governance Memory

SWARM-native authoritative history:

- Board decisions;
- C-Suite decisions;
- Safety VETO decisions;
- policy versions;
- budget approvals;
- human approvals;
- policy exceptions;
- governance evidence.

Ordinary agents must not mutate governance memory.

### Execution Checkpoints

Checkpoints belong to the execution subsystem, not the memory layer. They store resumable execution state such as execution ID, workflow stage, active agents, pending writes, policy references, budget reservation references, retry state, deadline, and checkpoint version.

## 6.6 Target Memory Contract

```text
MemoryRecord
├── id: GlobalMemoryId
├── tenant_id
├── organization_id
├── department_id
├── agent_id
├── execution_id
├── task_id
├── layer
├── scope
├── content
├── summary
├── tags
├── source
├── provenance
├── trust_level
├── confidence
├── created_at
├── updated_at
├── expires_at
├── version
├── supersedes_id
├── revoked_at
└── policy_context
```

The exact storage schema is implementation-dependent and must be finalized against the repository's chosen persistence technology.

## 6.7 Memory Policy Engine

```text
Agent Request
     |
     v
Memory Policy Engine
     |
 +---+---+---+---+
 |   |   |   |   |
Auth Scope Trust Retention Classification
     |
     v
Allow / Deny / Filter / Redact
     |
     v
Memory Backend
```

Authorization must happen before retrieval/context injection. Confidence must never equal authorization.

## 6.8 Trust Model

Initial levels:

```text
UNTRUSTED
EXTERNAL
AGENT_GENERATED
SYSTEM_DERIVED
VERIFIED
GOVERNANCE_AUTHORITY
```

Trust is metadata and evidence, not a privilege escalation mechanism.

## 6.9 Write Invariants

1. Every write gets a globally unique ID.
2. Every write is attributable to actor and execution.
3. Every write has tenant/scope context.
4. Every write has layer and trust classification.
5. Governance memory is protected by an authoritative policy boundary.
6. Shared mutable memory uses version/conflict semantics.
7. Failed persistence cannot be reported as success.
8. Writes are observable and auditable.
9. External/untrusted memory cannot directly alter policy authority.

## 6.10 Retrieval Invariants

1. Authorization precedes retrieval.
2. Scope filters are mandatory.
3. Revoked/expired memory is excluded.
4. Relevance and authority are separate dimensions.
5. Confidence is not authorization.
6. Untrusted memory is explicitly classified internally.
7. Context assembly enforces a real token budget.
8. Retrieval returns provenance.
9. Governance records are separated from ordinary knowledge in context.

## 6.11 Concurrency Model

The current `RLock` protects one Python process only. V2 requires:

- optimistic versioning;
- compare-and-swap or equivalent conflict detection;
- durable transaction semantics;
- idempotency keys;
- explicit conflict resolution;
- no silent last-write-wins for governance-sensitive state.

## 6.12 Persistence Architecture

```text
MemoryService
    |
    +-- PolicyEngine
    +-- ContextAssembler
    +-- MemoryRepository
    +-- SearchIndex
    +-- AuditSink

ExecutionService
    |
    +-- CheckpointRepository
```

The in-memory backend may remain for tests/development. Production must use an explicit durable backend.

## 6.13 Context Assembly Target

```text
1. Validate execution/agent identity
2. Evaluate memory policy
3. Load working/core memory
4. Retrieve relevant episodic history
5. Retrieve relevant knowledge
6. Load applicable governance references separately
7. Apply trust/provenance filters
8. Deduplicate/supersede conflicts
9. Rank by relevance + freshness + authority + trust
10. Enforce token budget
11. Attach provenance metadata
12. Return immutable context snapshot
```

## 6.14 Migration Strategy

Do not immediately delete the current `MemoryEngine`.

1. Establish domain contracts.
2. Introduce global IDs and versions.
3. Introduce repository interfaces/adapters.
4. Add policy enforcement.
5. Separate checkpoint persistence from memory.
6. Implement durable storage.
7. Implement real indexing/retrieval.
8. Implement Governance Memory.
9. Integrate the new service into the real execution path.
10. Migrate callers and `ContextManager` responsibilities deliberately.
11. Remove direct dictionary/state access.
12. Remove stubs only after replacement paths are verified.
13. Validate recovery and rollback.

## 6.15 Memory Validation

Required test classes:

- unit;
- repository contract;
- serialization/deserialization;
- retrieval correctness;
- authorization;
- tenant isolation;
- department/agent scope isolation;
- poisoning;
- trust enforcement;
- deletion/revocation;
- retention/expiry;
- concurrent writes;
- concurrent reads/writes;
- optimistic conflicts;
- retry/idempotency;
- process restart recovery;
- checkpoint restoration;
- index consistency;
- token-budget enforcement;
- latency/load;
- property-based invariants.

## 6.16 Memory Acceptance Criteria

Memory V2 is `VERIFIED` only when:

- execution state and long-term memory are structurally separated;
- persistence is real, not stubbed;
- every write is attributable;
- IDs are collision-resistant;
- authorization exists on reads/writes;
- tenant/scope isolation is enforced;
- trust/provenance are first-class;
- Governance Memory is protected;
- retrieval is genuinely relevance-based;
- context assembly enforces token budget;
- retention/revocation exist;
- concurrent mutation cannot silently corrupt governance state;
- failure cannot be reported as successful persistence;
- recovery is tested;
- SLOs are defined and met;
- regression tests cover every fixed critical finding;
- at least one real production execution path uses the new memory service.

# 7. WORKFLOW PROGRAM

Primary benchmark: LangGraph. Secondary: Microsoft Agent Framework.

Target principles: explicit state, graph transitions, checkpointing, resumability, interrupts/HITL, controlled branching, deterministic recovery boundaries.

SWARM adaptation must include authority, policy, budget, tools, deadlines, compensation, retries, and memory references.

# 8. DURABILITY PROGRAM

```text
Control Plane -> Durable Job -> Checkpointed Execution -> Workers -> Recovery/Resume
```

Required: durable job identity, checkpoint versioning, retry-safe side effects, ownership/lease semantics, deadlines, recovery, idempotency, and dead-letter/error handling.

# 9. ROUTING PROGRAM

Replace fragile keyword-only routing with capability-aware, confidence-aware, policy-aware routing using capability, classification, confidence, availability, cost, latency, policy, department scope, authority, ambiguity, and fallback signals.

Low-confidence privileged actions must clarify, safely fallback, escalate, or reject.

# 10. SAFETY PROGRAM

Safety must be an authoritative boundary with centralized policy evaluation, fail-closed protected operations, verified policy configuration, tool authorization, role/tenant-aware policy, explicit VETO semantics, audit records, and no bypass path.

# 11. BUDGET GOVERNANCE PROGRAM

Budget control must be server-authoritative. Required: authoritative pricing/model catalog, atomic reservations, concurrency safety, reconciliation, immutable ledger, execution cost attribution, agent/department budgets, approval thresholds, and fail-closed behavior when budget authority is unavailable.

> Client-reported estimated cost must never authorize spending.

# 12. MODEL RUNTIME PROGRAM

Create one authoritative model registry owning provider, model ID, capabilities, context limits, pricing, latency class, reliability, restrictions, fallback chain, and availability. Agents should request capabilities rather than hard-code provider details where practical.

# 13. INTER-AGENT COMMUNICATION PROGRAM

Define message identity, correlation, ordering, acknowledgement, retries, deduplication, failure handling, dead-letter behavior, authorization, tenant isolation, and trace propagation.

# 14. OBSERVABILITY PROGRAM

Every execution must be traceable across:

```text
Request -> Execution -> Policy -> Agent -> Model -> Tool -> Memory -> Cost -> Result
```

Telemetry must include execution/agent/model/tool IDs, latency, tokens, cost, retries, policy decisions, failures, fallback activation, and checkpoint/recovery events without leaking secrets.

# 15. HUMAN-IN-THE-LOOP PROGRAM

Approval is durable state:

```text
NOT_REQUIRED -> PENDING -> APPROVED / REJECTED / EXPIRED / CANCELLED
```

Records require approver identity, authority context, policy/version, execution ID, requested action, timestamps, expiration, and evidence where appropriate.

# 16. ENTERPRISE SECURITY PROGRAM

Required: authentication, authorization, tenant isolation, secret management, data classification, artifact security, sandboxing where required, SSRF/path traversal/injection protection, audit logging, and least privilege.

# 17. TESTING AND VERIFICATION PROGRAM

Required layers:

- unit;
- integration;
- security;
- concurrency;
- failure;
- chaos;
- load;
- property-based testing.

The target is proof of invariants, not merely happy-path behavior.

# 18. SWARM-NATIVE ADVANTAGES

Preserve and strengthen:

- Board governance;
- C-Suite authority;
- departmental specialization;
- safety VETO;
- CFO/budget governance;
- organizational hierarchy;
- governed delegation;
- explicit policy authority;
- institutional decision history.

These are differentiators, not technical debt.

# 19. GLOBAL ACCEPTANCE MODEL

A subsystem is not complete because code compiles, tests pass, or a demo works. It is verified only when architecture, threat model, invariants, failure behavior, concurrency behavior where relevant, observability, migration safety, regression coverage, and objective evidence exist.

# 20. Implementation Order

```text
Phase 0 — Baseline and Contracts
        |
Phase 1 — Trust / Safety / Authorization
        |
Phase 2 — Execution Correctness / Idempotency / Budget
        |
Phase 3 — Durable Workflow / Checkpoints / Recovery
        |
Phase 4 — Memory V2
        |
Phase 5 — Routing / Communication / Model Runtime
        |
Phase 6 — Observability / Audit / Enterprise Operations
        |
Phase 7 — Concurrency / Chaos / Load / Security Verification
        |
Phase 8 — Benchmark and Optimization
```

Memory is the first competitive deep dive. Its implementation must follow the dependency findings in Section 6 rather than bypass them.

# 21. Status Model

```text
DISCOVERED
 -> AUDITING
 -> BENCHMARKING
 -> REVERSE_ENGINEERING
 -> DESIGNING
 -> APPROVED
 -> IMPLEMENTING
 -> TESTING
 -> VERIFIED
 -> MONITORED
```

`VERIFIED` means evidence-backed acceptance.

# 22. Current Program State

| Workstream | Status |
|---|---|
| Memory source audit | COMPLETE |
| Memory dependency audit | COMPLETE |
| Letta benchmark | COMPLETE — principles extracted |
| LangGraph benchmark | COMPLETE — principles extracted |
| Memory V2 architecture | COMPLETE — design baseline |
| Memory implementation specification | NEXT |
| Memory code migration | NOT STARTED |
| Memory production integration | NOT STARTED |
| Memory verification | BLOCKED until implementation |

## Verified evidence from the supplied repository snapshot

- `tests/unit/test_memory_engine.py`: **16 passed**.
- Vault E2E collection: **blocked by missing `vault_client` module**.
- Production references to `MemoryEngine`: none found in the supplied `swarm/` tree beyond its export/definition.
- `ContextManager` is actively used by `ContextCompactor`, creating a second overlapping context/state subsystem.
- `MemoryEngine` persistence/search methods are placeholders.

# 23. Next Action — Implementation Specification

The next engineering artifact remains inside this same file. Before changing code, define the exact surgical implementation plan for:

1. authoritative Memory/Context domain contracts;
2. repository interfaces;
3. durable backend choice;
4. ID/version model;
5. authorization/policy integration;
6. tenant/department/agent scope model;
7. trust/provenance schema;
8. retrieval/indexing architecture;
9. context assembly/token budgeting;
10. checkpoint boundary;
11. ContextManager migration/compatibility strategy;
12. test migration and new adversarial tests;
13. rollout/rollback;
14. production integration path.

Only then should `memory_engine.py` and its callers be modified.

# 24. Program Rule

> **Take the best principle. Understand the trade-off. Adapt it to SWARM. Improve the weaknesses. Prove the result.**

This document is the single source of truth for the SWARM Competitive Architecture Program.

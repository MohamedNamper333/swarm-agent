# SWARM Competitive Architecture Program

> **Status:** MEMORY DEEP DIVE — AUDITED / DESIGN IN PROGRESS
> **Target Branch:** `main`
> **Purpose:** Evolve SWARM by benchmarking each subsystem against the strongest relevant implementations, extracting the engineering principles behind their strengths, and adapting those principles to SWARM's governance-first architecture.

---

## 1. Executive Objective

SWARM will not be replaced by another framework and will not blindly copy another codebase.

The governing rule is:

> **Benchmark the best → reverse-engineer the reason → identify trade-offs → adapt the principle → implement in SWARM's architecture → verify with measurable evidence.**

The target is a production-grade **Governed Multi-Agent Operating Platform** combining institutional governance, Board/C-Suite authority, departmental specialization, safety vetoes, authoritative budget control, durable execution, strong memory, reliable routing, distributed execution, observability, model abstraction, human-in-the-loop controls, and enterprise security.

---

## 2. Non-Negotiable Methodology

Every subsystem follows:

1. Audit current implementation at file/class/function/data-flow level.
2. Select the strongest relevant benchmark.
3. Reverse-engineer its architecture, abstractions, lifecycle, state model, failure handling, and tests.
4. Extract the design decisions that create its advantage.
5. Analyze limitations and trade-offs.
6. Adapt the principle to SWARM's architecture.
7. Define contracts, invariants, state transitions, and boundaries.
8. Define exact implementation changes.
9. Define migration and rollback.
10. Define validation and measurable acceptance criteria.
11. Verify with evidence.

### Critical Rule

Do not copy implementation merely because another project is more mature. Copying surface structure without understanding the invariant, lifecycle, and trade-off is prohibited.

---

## 3. Current Benchmark Set

| Subsystem | Primary Benchmark | Secondary Benchmark | SWARM Native Advantage |
|---|---|---|---|
| Memory | Letta | LangGraph | Governance Memory + organizational scope |
| Stateful Execution | LangGraph | Microsoft Agent Framework | Governance-aware checkpoints |
| Workflow | LangGraph | Microsoft Agent Framework | Policy-aware orchestration |
| Production Agent Runtime | Microsoft Agent Framework | LangGraph | Board/C-Suite governance |
| Organizational Agents | MetaGPT | Microsoft Agent Framework | Enterprise governance hierarchy |
| Knowledge / RAG | LlamaIndex | Letta | Governed knowledge access |
| Observability | Microsoft Agent Framework / LangGraph ecosystem | — | Governance and budget telemetry |
| Model / Provider Runtime | Microsoft Agent Framework | LlamaIndex | Policy-driven model selection |
| Human-in-the-Loop | LangGraph | Microsoft Agent Framework | Approval authority hierarchy |
| Safety | SWARM-native + external patterns | Microsoft Agent Framework | Safety VETO / policy engine |
| Budget Governance | SWARM-native | — | CFO / authoritative financial controls |
| Enterprise Governance | SWARM-native | Microsoft Agent Framework | Board + C-Suite + departmental authority |

Reference projects are benchmarks, not dependencies by default.

---

# 4. Architecture Principles

## 4.1 Trust Boundary

Untrusted input must never grant privilege.

## 4.2 Financial Authority

Cost must be server-authoritative. Client-provided estimates cannot authorize spending.

## 4.3 Atomic Budgeting

Budget reservation must be atomic and concurrency-safe.

## 4.4 Approval Semantics

Approval is never execution success.

## 4.5 Global Identity

Every execution and side effect must have globally unique, traceable identity.

## 4.6 Idempotent Side Effects

Retries must not silently duplicate irreversible operations.

## 4.7 Durable Execution

Long-running work must survive worker failure and restart from a valid checkpoint.

## 4.8 Policy Before Privilege

Safety, authorization, budget, tenancy, and tool policies must be enforced at authoritative boundaries.

## 4.9 Separation of State Classes

Execution state, memory, audit records, policy decisions, and artifacts must not be treated as one undifferentiated state store.

## 4.10 Evidence-Based Completion

A feature is not complete because code exists or a happy-path test passes. Completion requires evidence against explicit acceptance criteria.

---

# 5. SWARM Competitive Evolution Matrix

| Domain | Current Direction | Target | Primary Work |
|---|---|---:|---|
| Memory | Existing memory engine | 9.5/10 | Letta + LangGraph adaptation |
| Workflow | Existing orchestration | 9.5/10 | Durable graph/state execution |
| Routing | Keyword/heuristic-oriented | 9/10 | Capability + confidence + ambiguity-aware routing |
| Durability | Limited | 9.5/10 | Checkpoints + durable jobs + recovery |
| Observability | Partial | 9.5/10 | Distributed tracing + cost/token telemetry + audit correlation |
| Safety | Strong concept, incomplete enforcement | 10/10 | Authoritative policy boundary |
| Governance | Strong concept | 10/10 | Formal decision authority and invariants |
| Budget | Strong concept, implementation gaps | 10/10 | Atomic reservations + reconciliation + ledger |
| Inter-Agent Bus | Existing | 9/10 | Delivery semantics + dedup + retry + acknowledgement |
| Model Registry | Existing with duplication/debt | 9.5/10 | Single authoritative registry |
| HITL | Partial | 9.5/10 | Durable approval state and enforcement |
| Testing | Feature-oriented | 10/10 | Concurrency + chaos + fuzz + property + recovery |

Scores are engineering targets, not objective industry rankings.

---

# 6. MEMORY DEEP DIVE

## 6.1 Current SWARM Source Audit

The current implementation is `swarm/core/memory_engine.py`. It defines a `MemoryEngine` with four declared layers: `SCRATCHPAD`, `WORKING`, `EPISODIC`, and `SEMANTIC`. `MemoryEntry` carries `id`, `layer`, `task_id`, `agent_id`, `content`, timestamp, tags, confidence, access count, and last-accessed metadata. `Lesson` stores task/agent, pattern, lesson, confidence, creation time, and application count. fileciteturn6file0L1-L2

### 6.1.1 What is good

- The project already recognizes that memory is not one homogeneous bucket.
- The four-layer model is directionally sound.
- Memory entries have explicit identity and actor/task metadata.
- Confidence and access metadata exist.
- A separate lesson abstraction exists.
- The code uses an `RLock`, which gives basic in-process synchronization around mutations.
- There is an intended external persistence/search boundary through Vault and Meilisearch.

These are useful foundations, but they are not sufficient for institutional-grade memory.

### 6.1.2 Critical implementation weaknesses found in the current file

#### A. Persistence is a stub, not an actual persistence subsystem

`save_to_vault()` and `load_from_vault()` only return success when a client exists; they do not serialize, write, read, deserialize, validate, version, or reconcile state. Likewise, Meilisearch integration is represented by flags/stubs and `search_meilisearch()` returns an empty list. This means the declared production persistence/search architecture is not actually implemented in this file. fileciteturn6file0L2-L2

**Severity:** CRITICAL.

**Required direction:** make persistence an explicit adapter with transactional/versioned semantics rather than a boolean feature flag.

#### B. Memory is process-local by default

`scratchpad`, `working`, `episodic`, `semantic`, and `lessons` are Python in-memory structures. A process restart loses them unless a real persistence path is implemented elsewhere. The current file does not provide that guarantee. fileciteturn6file0L2-L2

**Severity:** CRITICAL for production durability.

#### C. Identity generation is collision-prone

IDs are built with `int(time.time())`, for example `scratchpad_{task_id}_{int(time.time())}` and similar patterns for working, episodes, semantic entries, and lessons. Multiple writes within the same second can collide, and the identifiers are not globally authoritative. fileciteturn6file0L2-L2

**Required direction:** globally unique IDs, preferably UUID/ULID/UUIDv7-style identifiers, with execution/tenant/agent correlation as metadata rather than embedded assumptions.

#### D. Access control is absent from the memory API

The public methods accept `task_id`, `agent_id`, and content but there is no authorization decision, tenant boundary, role check, policy evaluation, or capability check before reads/writes. `get_episodes()` can filter by agent but that is not authorization. `read_working()` and `read_scratchpad()` are similarly direct lookups. fileciteturn6file0L2-L2

**Severity:** CRITICAL.

#### E. Provenance is incomplete

The entry contains task and agent IDs, but not a durable execution ID, tenant ID, policy decision ID, authority context, source/provenance reference, or mutation version. That is insufficient for an enterprise memory audit trail. fileciteturn6file0L2-L2

#### F. Semantic promotion logic is internally inconsistent

`_maybe_promote_to_semantic()` requires `entry.confidence >= 0.8 and entry.access_count >= 3`, but a newly created episodic entry starts with `access_count=0`, and the method is called immediately from `record_episode()`. There is no demonstrated path in this file that increments the episode's access count before the promotion check. Therefore the intended automatic promotion path is effectively unreachable under the shown implementation. fileciteturn6file0L2-L2

**Severity:** HIGH.

#### G. Semantic search is not semantic retrieval

`search_semantic()` lowercases the query and performs substring matching against the topic key. It does not search entry content, embeddings, relevance, recency, provenance, permissions, or confidence calibration. The name suggests semantic search while the implementation is keyword/topic matching. fileciteturn6file0L2-L2

**Severity:** HIGH.

#### H. Context construction is incomplete and uses hard-coded scope assumptions

`build_context()` reads working memory from `session_{agent_id}`, retrieves the last five episodic entries for the agent, and leaves semantic and lesson sections empty because the task description is not passed through. This means context assembly is not actually relevance-driven. fileciteturn6file0L2-L2

**Severity:** HIGH.

#### I. `max_tokens` is not enforced

`build_context()` accepts `max_tokens=4000`, but the function does not perform token accounting, truncation, prioritization, or budget-aware context construction. fileciteturn6file0L2-L2

**Severity:** HIGH.

#### J. Working memory has last-write-wins behavior with no concurrency/version conflict model

`update_working()` mutates a dictionary in place. The process lock prevents simultaneous local threads from executing the critical section concurrently, but there is no optimistic version, compare-and-swap, distributed lock, or durable transaction semantics. A multi-worker deployment would therefore require a separate authoritative consistency mechanism. fileciteturn6file0L2-L2

#### K. Shared mutable references can escape the lock boundary

Methods return `MemoryEntry` objects and lists containing the underlying mutable entries. Callers can potentially mutate returned state outside the engine lock. `get_episodes()` also returns the underlying list entries rather than immutable snapshots. This weakens the stated thread-safety boundary. fileciteturn6file0L2-L2

#### L. Confidence is accepted but not governed

Callers can submit arbitrary confidence values. There is no calibration, provenance weighting, source reliability, human verification, decay, or policy rule determining how confidence affects future authority. Confidence must not become a privilege escalation mechanism.

#### M. Lesson retrieval is simplistic and potentially misleading

`get_relevant_lessons()` only matches whether `lesson.pattern.lower()` is a substring of the task description. It does not perform semantic similarity, contradiction detection, source weighting, freshness/decay, or tenant/agent authorization. fileciteturn6file0L2-L2

#### N. Lesson application is not linked to an execution identity

`apply_lesson()` only increments an integer. There is no record of who applied it, under which execution, whether it was successful, or whether the lesson caused a measurable outcome. fileciteturn6file0L2-L2

#### O. No retention, deletion, supersession, or revocation lifecycle

The current file contains no TTL, retention class, deletion workflow, legal hold, supersession, tombstone, or revocation semantics. For an enterprise memory system this is a major governance gap.

#### P. No poisoning/taint model

There is no mechanism to mark memory as untrusted, externally supplied, agent-generated, human-verified, policy-derived, or disputed. This is dangerous because future context assembly can treat all memory as equally trustworthy.

#### Q. No separation between knowledge and governance authority

The current `SEMANTIC` layer can contain long-term facts and patterns, but nothing in the API prevents a memory item from being interpreted as an authoritative policy. SWARM must explicitly separate knowledge from policy authority.

---

## 6.2 What Letta Does Better

Letta's current documentation treats memory blocks as a first-class abstraction: structured sections of the agent's context that persist across interactions, are always visible while attached, and can be agent-managed. Blocks have explicit labels, descriptions, values, and size limits. Read-only blocks are supported, and blocks can be shared across agents. citeturn1search0

### Principle 1 — Memory is an explicit context primitive

Letta does not treat all memory as an undifferentiated database. It gives important information a named, bounded, context-visible representation. This reduces retrieval dependence for high-value information. citeturn1search0

### Principle 2 — Memory access is attach/detach controlled

Letta allows blocks to be independently created and attached/detached from agents. This creates an explicit access boundary: attachment grants context access, detachment removes it without deleting the underlying block. The same mechanism supports shared memory and temporary access. citeturn1search1

### Principle 3 — Context hierarchy depends on scale and importance

Letta explicitly distinguishes in-context memory blocks, files, archival memory, and external RAG. Small/high-importance information belongs closer to the context; larger or less frequently recalled information belongs in external/retrievable storage. citeturn1search2

### Principle 4 — Descriptions are part of the memory contract

Letta documents the `description` of a memory block as an important signal for how the agent should use it. The abstraction therefore includes semantics, not just bytes. citeturn1search0

### Principle 5 — Read-only memory is a first-class control

Read-only blocks can expose policies or organizational information without allowing an agent to mutate them. This maps directly to SWARM's need for authoritative governance memory. citeturn1search0

### Principle 6 — Shared memory is explicit

A block can be attached to multiple agents, giving them a common view. Letta also documents dynamic attachment/detachment and role-based access use cases. citeturn1search1turn1search7

### Principle 7 — Memory lifecycle is part of the agent state model

Letta persists agent state and exposes memory blocks as part of that state rather than treating memory as a detached convenience utility. citeturn1search10

### Important Letta caveat

Letta's own documentation warns that updating a shared block replaces the entire value and that concurrent writers can overwrite earlier changes. This is a useful reminder: even a strong memory system needs an explicit concurrency/version policy. citeturn1search0

**SWARM decision:** do not reproduce last-write-wins shared blocks as the final architecture. Use versioned writes and conflict detection for governance-sensitive memory.

---

## 6.3 What LangGraph Does Better

LangGraph makes a critical architectural separation between thread-scoped execution state and cross-thread long-term memory. Its checkpointer persists graph state as checkpoints, while a separate `Store` persists information across threads/namespaces. citeturn0search0turn0search1

### Principle 1 — Checkpoint != Long-Term Memory

Checkpointing is about recovering execution state. Long-term memory is about information that should survive across executions. SWARM must preserve this separation. citeturn0search0

### Principle 2 — Recovery is part of persistence

LangGraph checkpoints can support human-in-the-loop, time travel, and fault-tolerant recovery. It also persists pending writes from successful tasks within a failed super-step so those successful tasks do not need to be re-run on resume. citeturn0search0

### Principle 3 — Namespaces are first-class

LangGraph's long-term store uses namespaces to scope memories. This is directly useful for SWARM's future tenant/organization/department/agent scopes. citeturn0search0

### Principle 4 — Persistent backends are explicit

LangGraph provides multiple checkpointer backends, including SQLite and PostgreSQL, rather than treating an in-memory dictionary as the production persistence layer. citeturn0search2

### Principle 5 — Persistence has a defined contract

The checkpointer exposes operations for storing checkpoints, storing intermediate writes, retrieving state, and listing history. This is a clear persistence interface rather than hidden serialization. citeturn0search0

### Principle 6 — Storage growth is a design concern

LangGraph documents checkpoint storage optimization and incremental/delta approaches for long-running state. SWARM should likewise define context/checkpoint growth policies instead of allowing unbounded accumulation. citeturn0search0

---

# 6.4 SWARM Memory V2 — Adapted Architecture

SWARM should combine the strongest principles without copying either framework.

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

## 6.4.1 Working/Core Memory

Purpose: small, high-value information that must be immediately available during an active execution or agent session.

Examples:

- current objective;
- active plan;
- current constraints;
- agent role context;
- high-priority user/project facts;
- active task state.

Properties:

- bounded size;
- explicit owner/scope;
- versioned writes;
- optional read-only mode;
- immediate context visibility.

This adopts Letta's strongest idea: important small memory should be an explicit context primitive rather than forcing every request through retrieval. citeturn1search0

## 6.4.2 Episodic Memory

Purpose: durable history of executions, observations, decisions, failures, outcomes, and lessons.

Required metadata:

- global memory ID;
- execution ID;
- task ID;
- agent ID;
- department ID;
- tenant ID;
- timestamp;
- source/provenance;
- confidence;
- trust classification;
- policy context;
- outcome;
- supersession/revocation state.

## 6.4.3 Knowledge/Archival Memory

Purpose: information too large or too low-frequency to remain permanently in context.

Storage should support:

- lexical search;
- semantic retrieval;
- metadata filtering;
- namespace filtering;
- permission filtering;
- recency/decay;
- provenance filtering;
- relevance ranking.

This follows the context-hierarchy principle documented by Letta. citeturn1search2

## 6.4.4 Governance Memory

This is SWARM-native.

It stores:

- Board decisions;
- C-Suite decisions;
- Safety VETO decisions;
- policy versions;
- budget approvals;
- human approvals;
- policy exceptions;
- governance evidence.

Governance memory must be **read-only to ordinary agents**. Only authorized governance actors/services may mutate it.

## 6.4.5 Execution Checkpoints

Execution checkpoints are not a memory layer. They belong to the execution subsystem and store resumable state.

A checkpoint may include:

- execution ID;
- workflow stage;
- active agents;
- state channels;
- pending writes;
- policy state references;
- budget reservation references;
- retry state;
- deadline;
- checkpoint version.

This follows LangGraph's separation between thread state/checkpoints and long-term stores. citeturn0search0turn0search1

---

# 6.5 Memory Data Contract — Target

The future memory record should conceptually contain:

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

The exact schema must be finalized during implementation against the repository's actual persistence technology.

---

# 6.6 Memory Policy Engine

Memory operations must pass through a policy boundary:

```text
Agent Request
     |
     v
Memory Policy Engine
     |
 +---+---+---+---+
 |   |   |   |   |
 v   v   v   v   v
Auth Scope Trust Retention Classification
     |
     v
Allow / Deny / Filter / Redact
     |
     v
Memory Backend
```

Required decisions:

- Is this actor authorized?
- Is the memory in the actor's scope?
- Is the memory trusted enough for this use?
- Is the memory revoked/expired?
- Is the content sensitive?
- Can the content influence policy or only provide context?
- Must it be redacted before retrieval?

---

# 6.7 Memory Trust Model

Memory must not be binary trusted/untrusted only.

Recommended initial levels:

```text
UNTRUSTED
EXTERNAL
AGENT_GENERATED
SYSTEM_DERIVED
VERIFIED
GOVERNANCE_AUTHORITY
```

Trust level is metadata, not privilege. A `GOVERNANCE_AUTHORITY` record may carry authoritative policy meaning only when its schema and authorization boundary explicitly permit that use.

---

# 6.8 Memory Write Rules

1. Every write receives a globally unique ID.
2. Every write is attributable to an actor and execution.
3. Every write has scope/tenant context.
4. Every write is classified by layer and trust level.
5. Governance memory cannot be written by ordinary agents.
6. Shared writable memory requires version/conflict semantics.
7. A failed persistence transaction must not be reported as a successful memory write.
8. Memory writes must be observable and auditable.
9. External/untrusted memory must never directly modify policy authority.

---

# 6.9 Memory Retrieval Rules

1. Authorization happens before retrieval/context injection.
2. Scope filters are mandatory.
3. Revoked/expired memory is excluded.
4. Relevance ranking is separate from authority ranking.
5. Confidence is not authorization.
6. Untrusted memory must be visibly classified in the internal context representation.
7. Context assembly must respect a real token budget.
8. Retrieval results must carry provenance so the agent can distinguish source types.
9. Governance/policy records should be separated from ordinary knowledge in the assembled context.

---

# 6.10 Concurrency Model

The current `RLock` is acceptable only for local process protection. It is not a distributed consistency mechanism.

V2 requires:

- optimistic versioning for mutable memory;
- compare-and-swap or equivalent conflict detection;
- durable transaction semantics;
- idempotency keys for retried writes;
- explicit conflict resolution;
- no silent last-write-wins for governance-sensitive state.

Letta's documentation explicitly notes that replacing a shared block can lose concurrent updates; SWARM should treat this as a known trade-off to improve rather than reproduce. citeturn1search0

---

# 6.11 Persistence Architecture

The future `MemoryEngine` should become an orchestration/service layer over explicit adapters:

```text
MemoryService
    |
    +-- PolicyEngine
    +-- ContextAssembler
    +-- MemoryRepository
    +-- CheckpointRepository (execution subsystem)
    +-- SearchIndex
    +-- AuditSink
```

The in-memory implementation should remain useful for tests/development, but production persistence must be explicit and durable.

---

# 6.12 Context Assembly Algorithm — Target

The current `build_context()` is too static. V2 should conceptually execute:

```text
1. Validate execution/agent identity
2. Evaluate memory access policy
3. Load working/core memory
4. Load relevant episodic history
5. Retrieve relevant knowledge
6. Load applicable governance references separately
7. Apply trust/provenance filters
8. Deduplicate / supersede conflicts
9. Rank by relevance + freshness + authority + trust
10. Enforce token budget
11. Emit provenance metadata
12. Return immutable context snapshot
```

The final implementation must make the ranking and budget policy deterministic enough to test.

---

# 6.13 Memory Migration Plan

Do not immediately delete the existing `MemoryEngine` implementation.

Migration sequence:

1. Introduce domain contracts/interfaces.
2. Add global IDs and version metadata while maintaining compatibility fields.
3. Introduce repository adapters.
4. Introduce policy enforcement.
5. Separate execution checkpoint persistence from long-term memory.
6. Implement durable backend.
7. Implement retrieval/indexing.
8. Implement governance memory.
9. Migrate callers gradually.
10. Remove obsolete direct dictionary access.
11. Remove stub persistence/search paths.
12. Verify recovery and rollback.

---

# 6.14 Memory Validation Plan

Required tests:

- unit tests;
- repository contract tests;
- serialization/deserialization tests;
- retrieval correctness;
- authorization tests;
- tenant isolation;
- department/agent scope isolation;
- poisoning tests;
- trust-level enforcement;
- deletion/revocation;
- retention/expiry;
- concurrent writes;
- concurrent reads/writes;
- optimistic conflict tests;
- retry/idempotency tests;
- process restart recovery;
- checkpoint restoration;
- index consistency;
- context token-budget tests;
- load/latency benchmarks;
- property-based invariant tests.

---

# 6.15 Memory Acceptance Criteria

Memory V2 cannot be marked `VERIFIED` until:

- execution state and long-term memory are structurally separated;
- persistence is real, not a stub;
- every write is attributable;
- IDs are globally collision-resistant;
- authorization exists on reads and writes;
- tenant/scope isolation is enforced;
- trust/provenance are first-class;
- governance memory is protected;
- semantic retrieval is actually relevance-based;
- context assembly uses a real token budget;
- retention/revocation exist;
- concurrent mutation cannot silently corrupt governance state;
- failure cannot be reported as successful persistence;
- recovery is tested;
- measurable latency/storage SLOs are defined and met;
- regression tests cover every fixed critical finding.

---

# 7. WORKFLOW PROGRAM

Primary benchmark: LangGraph. Secondary: Microsoft Agent Framework.

Extract:

- explicit state;
- graph transitions;
- checkpointing;
- resumability;
- interrupts/HITL;
- controlled branching;
- deterministic recovery boundaries.

SWARM adaptation must make workflow state aware of authority, policy, budget, tools, deadlines, compensation, retries, and memory references.

---

# 8. DURABILITY PROGRAM

```text
Control Plane
     |
     v
Durable Job
     |
     v
Execution State / Checkpoint
     |
     +----> Worker A
     +----> Worker B
     +----> Worker C
     |
     v
Recovery / Resume
```

Required: durable job identity, checkpoint versioning, retry-safe side effects, lease/ownership, deadlines, recovery, idempotency keys, dead-letter/error handling.

---

# 9. ROUTING PROGRAM

Replace fragile keyword-only routing with capability-aware, confidence-aware, policy-aware routing.

Signals include capability, task classification, confidence, availability, cost, latency, policy restrictions, department scope, authority, ambiguity, and fallback strategy.

Low-confidence or ambiguous privileged actions must clarify, safely fallback, escalate, or reject.

---

# 10. SAFETY PROGRAM

Safety must become an authoritative policy boundary.

Required:

- centralized policy evaluation;
- fail-closed protected operations;
- verified policy configuration;
- tool authorization;
- role/tenant-aware policy;
- explicit VETO semantics;
- policy audit records;
- no bypass path.

---

# 11. BUDGET GOVERNANCE PROGRAM

Budget control must be server-authoritative.

Required:

- authoritative pricing/model catalog;
- atomic reservations;
- concurrency safety;
- reconciliation;
- immutable ledger;
- per-execution cost attribution;
- agent/department budgets;
- approval thresholds;
- fail-closed behavior when budget authority is unavailable.

> Client-reported estimated cost must never be the authority for spending decisions.

---

# 12. MODEL RUNTIME PROGRAM

Create one authoritative model registry owning provider, model ID, capabilities, context limits, pricing, latency class, reliability, restrictions, fallback chain, and availability.

Agents should request capabilities rather than hard-code provider details where practical.

---

# 13. INTER-AGENT COMMUNICATION PROGRAM

The bus must define message identity, correlation, ordering expectations, acknowledgement, retries, deduplication, delivery failure, dead-letter behavior, authorization, tenant isolation, and trace propagation.

---

# 14. OBSERVABILITY PROGRAM

Every execution should be traceable across:

```text
Request -> Execution -> Policy -> Agent -> Model -> Tool -> Memory -> Cost -> Result
```

Telemetry must include execution/agent/model/tool IDs, latency, tokens, cost, retries, policy decisions, failures, fallback activation, and checkpoint/recovery events without leaking secrets.

---

# 15. HUMAN-IN-THE-LOOP PROGRAM

Approval is durable state, not an in-memory boolean.

States:

```text
NOT_REQUIRED -> PENDING -> APPROVED / REJECTED / EXPIRED / CANCELLED
```

Approval records must include approver, authority context, policy/version, execution ID, requested action, timestamps, expiration, and evidence where appropriate.

---

# 16. ENTERPRISE SECURITY PROGRAM

Required: authentication, authorization, tenant isolation, secret management, data classification, artifact security, sandboxing where required, SSRF/path traversal/injection protection, audit logging, and least privilege.

---

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

---

# 18. SWARM-NATIVE ADVANTAGES TO PRESERVE

The competitive program must preserve and strengthen:

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

---

# 19. GLOBAL ACCEPTANCE MODEL

A subsystem is not complete because code compiles or a demo works.

It is verified only when architecture, threat model, invariants, failure behavior, concurrency behavior where relevant, observability, migration safety, regression coverage, and objective acceptance evidence exist.

---

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

Memory is the first competitive deep dive, but implementation must respect foundational identity, authorization, persistence, and execution contracts.

---

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

---

# 22. Current Memory Findings Register

| ID | Finding | Severity | Current State | Target |
|---|---|---|---|---|
| MEM-001 | Vault persistence is stubbed | CRITICAL | Not implemented in `memory_engine.py` | Durable repository adapter |
| MEM-002 | Meilisearch integration is stubbed | HIGH | No actual indexing/search | Real search adapter + consistency strategy |
| MEM-003 | Process-local memory is non-durable | CRITICAL | Python dict/list state | Durable production backend |
| MEM-004 | Timestamp-based IDs can collide | HIGH | `int(time.time())` | Global UUID/ULID/UUIDv7-style IDs |
| MEM-005 | No memory authorization boundary | CRITICAL | Direct reads/writes | Policy-enforced access |
| MEM-006 | Provenance/tenant/policy metadata incomplete | CRITICAL | Basic agent/task metadata only | Full memory envelope |
| MEM-007 | Semantic promotion condition is unreachable as written | HIGH | Access count starts at zero | Explicit promotion lifecycle |
| MEM-008 | Semantic search is topic substring matching | HIGH | Not semantic | Relevance/embedding/search pipeline |
| MEM-009 | Context assembly is incomplete | HIGH | Semantic/lessons empty | Policy-aware retrieval pipeline |
| MEM-010 | `max_tokens` is ignored | HIGH | No token accounting | Deterministic context budget |
| MEM-011 | Returned mutable objects can escape lock boundary | HIGH | Mutable references returned | Immutable snapshots / controlled mutation |
| MEM-012 | Confidence is caller-controlled and ungoverned | HIGH | Arbitrary confidence accepted | Trust/calibration/provenance model |
| MEM-013 | Lesson relevance is substring matching | MEDIUM | Weak retrieval | Semantic/ranked lesson retrieval |
| MEM-014 | Lesson application lacks execution evidence | MEDIUM | Counter only | Application audit + outcome |
| MEM-015 | No retention/deletion/revocation lifecycle | CRITICAL | Absent | Lifecycle policy |
| MEM-016 | No poisoning/taint model | CRITICAL | Absent | Trust classification + enforcement |
| MEM-017 | Governance authority is not separated from knowledge | CRITICAL | Same semantic mechanism | Governance memory boundary |
| MEM-018 | No distributed concurrency model | CRITICAL | Local `RLock` only | Versioning + CAS/transaction semantics |
| MEM-019 | No checkpoint/memory separation | HIGH | Context/memory model mixed conceptually | Execution checkpoint subsystem |
| MEM-020 | No durable failure semantics | CRITICAL | Persistence success is not proven | Transactional persistence + recovery |

---

# 23. Benchmark Conclusions — Memory

## Letta contributed

1. Explicit memory blocks.
2. Bounded, always-visible core context.
3. Semantic descriptions as part of the memory contract.
4. Read-only memory blocks.
5. Shared memory blocks.
6. Dynamic attach/detach access.
7. A hierarchy based on information importance and scale.

Sources: Letta memory block documentation and context hierarchy. citeturn1search0turn1search1turn1search2

## LangGraph contributed

1. Explicit checkpoint abstraction.
2. Thread-scoped execution state.
3. Separate long-term store.
4. Namespaced memory.
5. Durable backends.
6. Recovery from checkpoints.
7. Pending-write recovery semantics.
8. Explicit persistence interfaces.

Sources: LangGraph persistence and memory documentation. citeturn0search0turn0search1turn0search2

## SWARM synthesis

SWARM should combine these principles but add:

- governance memory;
- policy-aware retrieval;
- tenant/department/agent scopes;
- trust/provenance classification;
- budget-aware context assembly;
- governance-authority isolation;
- versioned shared memory;
- execution-to-memory causal linkage.

This is the intended competitive advantage rather than a direct framework clone.

---

# 24. Next Action — Memory Implementation Specification

The next step is **not** to rewrite `memory_engine.py` immediately.

The next step is to audit all SWARM callers/imports/tests/configuration around `MemoryEngine`, identify every contract dependency, and then produce the exact surgical implementation plan for Memory V2.

Required next audit targets:

- all imports/references to `MemoryEngine`;
- all call sites for `build_context()`;
- all writers/readers of scratchpad/working/episodic/semantic/lessons;
- Vault implementation;
- Meilisearch configuration/client;
- serialization formats;
- tests;
- agent execution state;
- tenant/auth/policy components;
- existing IDs and execution correlation.

Only after that dependency audit should implementation begin.

---

# 25. Program Rule

> **Take the best principle. Understand the trade-off. Adapt it to SWARM. Improve the weaknesses. Prove the result.**

This document is the single source of truth for the SWARM Competitive Architecture Program.

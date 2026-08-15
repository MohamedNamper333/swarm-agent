# SWARM Competitive Architecture Program

> **Status:** DRAFT — Program Charter
> **Target Branch:** `main`
> **Purpose:** Evolve SWARM by benchmarking each subsystem against the strongest relevant open-source implementations, extracting the engineering principles behind their strengths, and adapting those principles to SWARM's own governance-first architecture.

---

## 1. Executive Objective

SWARM will not be replaced by another framework and will not blindly copy another codebase.

The program follows this rule:

> **Benchmark the best → reverse-engineer the reason → identify trade-offs → adapt the principle → implement in SWARM's architecture → verify with measurable evidence.**

The target is a production-grade **Governed Multi-Agent Operating Platform** combining:

- institutional governance;
- Board and C-Suite decision authority;
- departmental specialization;
- safety vetoes and policy enforcement;
- authoritative budget governance;
- durable multi-agent execution;
- strong memory and knowledge systems;
- reliable routing and delegation;
- distributed execution;
- observability and auditability;
- provider/model abstraction;
- human-in-the-loop controls;
- enterprise security and tenancy.

---

## 2. Non-Negotiable Methodology

For every subsystem, work must follow the same lifecycle:

1. **Audit** — understand the current SWARM implementation at file/class/function/data-flow level.
2. **Benchmark Selection** — select the strongest relevant reference implementation.
3. **Reverse Engineering** — inspect architecture, abstractions, lifecycle, state model, failure handling, and tests.
4. **Strength Extraction** — isolate the design decisions that create the observed advantage.
5. **Weakness Analysis** — identify limitations, trade-offs, unresolved issues, and operational assumptions.
6. **SWARM Adaptation** — redesign the principle around SWARM's governance and organizational model.
7. **Architecture Specification** — define interfaces, contracts, invariants, state transitions, and boundaries.
8. **Implementation Plan** — identify exact files/classes/modules and surgical changes.
9. **Migration Plan** — preserve compatibility where required and define rollout/rollback behavior.
10. **Validation Plan** — unit, integration, security, concurrency, failure, load, and property-based testing where applicable.
11. **Acceptance** — mark the subsystem complete only when measurable acceptance criteria are satisfied.

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

Cost must be server-authoritative. Client-provided cost estimates cannot authorize spending.

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

Safety, authorization, budget, tenancy, and tool policies must be enforced at authoritative boundaries, not merely by convention.

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

Scores are engineering targets, not claims of objective industry ranking.

---

# 6. MEMORY PROGRAM

## 6.1 Objective

Upgrade SWARM's existing memory engine into a governed, multi-layer memory fabric that is stronger than a simple persistence layer and fits the Board/C-Suite/Department/Agent hierarchy.

## 6.2 Benchmark Strategy

### Primary: Letta

Study the architectural reasons behind Letta's stateful-agent and memory model, especially the separation of persistent/core context, recall-style historical information, and archival knowledge.

Do not copy Letta's implementation directly.

### Secondary: LangGraph

Study the separation between execution checkpoints and longer-lived stores. The key principle to extract is:

> **Execution checkpoint/state is not the same thing as long-term memory.**

### Additional Reference: LlamaIndex

Study retrieval, knowledge, RAG, indexing, and multi-agent knowledge workflows where useful.

## 6.3 SWARM Memory V2 Target Architecture

```text
                         MEMORY FABRIC
                              |
        +---------------------+---------------------+
        |                     |                     |
        v                     v                     v
  Working Memory       Episodic Memory      Knowledge Memory
        |                     |                     |
        +---------------------+---------------------+
                              |
                              v
                     Governance Memory
                              |
                              v
                    Memory Policy Engine
                              |
               +--------------+--------------+
               |              |              |
               v              v              v
             Scope          Trust         Retention
               |              |              |
               +--------------+--------------+
                              |
                              v
                         Retrieval
                              |
                              v
                       Context Assembly
```

### Working Memory

Short-lived execution state for the current task:

- request;
- current plan;
- current stage;
- active constraints;
- temporary observations;
- active tool/context state.

### Episodic Memory

Historical execution events and outcomes:

- execution identity;
- agent identity;
- task;
- observations;
- result;
- confidence;
- failures;
- timestamps;
- causal/provenance references.

### Knowledge Memory

Durable domain/project information:

- documents;
- facts;
- summaries;
- domain knowledge;
- indexed information;
- retrieval metadata.

### Governance Memory

SWARM-specific institutional history:

- Board decisions;
- C-Suite decisions;
- safety decisions;
- policy exceptions;
- human approvals;
- budget decisions;
- governance evidence.

This is a SWARM-native differentiator rather than a direct copy of another framework.

## 6.4 Memory Security Requirements

Every persisted memory record must have sufficient metadata to answer:

- Who created it?
- Which agent/process created it?
- Under which execution?
- Under which tenant/scope?
- What authority allowed the write?
- What confidence/provenance does it have?
- Who can retrieve it?
- How long should it live?
- Can it be deleted or superseded?
- Can it influence future decisions?

### Required Controls

- provenance;
- scope isolation;
- tenant isolation;
- authorization-aware retrieval;
- retention policy;
- deletion/supersession semantics;
- poisoning resistance;
- deduplication/consolidation strategy;
- auditability;
- deterministic policy enforcement.

## 6.5 Memory Invariants

1. Memory cannot grant privilege.
2. Untrusted memory cannot bypass safety policy.
3. Cross-agent memory access must be explicitly authorized.
4. Cross-tenant memory access is prohibited unless an explicit trusted boundary exists.
5. Execution checkpoints must not be confused with durable knowledge.
6. Memory writes must be attributable to a global execution/actor identity.
7. Retrieval must apply policy before context injection.
8. Deleted or revoked knowledge must not remain silently authoritative.

## 6.6 Memory Implementation Plan

The implementation must be based on the actual SWARM repository after a fresh source audit.

For each affected file, document:

```text
File
Class / Function
Current behavior
Problem
Required change
New contract
Dependencies
Migration impact
Tests
Rollback
```

Do not rewrite whole files unless required by architecture and explicitly justified.

## 6.7 Memory Validation

Required test classes:

- unit tests;
- retrieval correctness;
- permission tests;
- tenant isolation tests;
- poisoning tests;
- deletion/revocation tests;
- concurrent writes;
- concurrent reads/writes;
- restart/recovery;
- checkpoint restoration;
- deduplication/consolidation;
- latency/load benchmarks;
- property-based tests for invariants.

## 6.8 Memory Acceptance Criteria

Memory V2 is accepted only when:

- execution state and long-term memory are structurally separated;
- all memory writes are attributable;
- authorization is enforced on retrieval and mutation;
- tenant/scope isolation is tested;
- poisoning scenarios are tested;
- retention/deletion behavior is deterministic;
- recovery preserves required state;
- benchmarked retrieval latency meets defined SLOs;
- no existing critical SWARM invariant is weakened.

---

# 7. WORKFLOW PROGRAM

## Benchmark

Primary: LangGraph.
Secondary: Microsoft Agent Framework.

## Principles to extract

- explicit state;
- graph-based transitions;
- checkpointing;
- resumability;
- interrupts/HITL;
- controlled branching;
- deterministic recovery boundaries.

## SWARM adaptation

Workflow execution must become a durable state machine aware of:

- Board/C-Suite authority;
- department routing;
- policy decisions;
- budget reservations;
- tool authorization;
- execution deadlines;
- compensation;
- retry state.

---

# 8. DURABILITY PROGRAM

## Target Architecture

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

Required properties:

- durable job identity;
- globally unique execution identity;
- checkpoint versioning;
- retry-safe side effects;
- lease/ownership semantics;
- timeout/deadline propagation;
- recovery after worker failure;
- idempotency keys;
- dead-letter/error handling.

---

# 9. ROUTING PROGRAM

Replace fragile keyword-only routing with a policy-aware routing engine.

Required signals:

- capability matching;
- task classification;
- confidence;
- agent availability;
- cost;
- latency;
- policy restrictions;
- department scope;
- authority level;
- ambiguity;
- fallback strategy.

### Routing Rule

No ambiguous route may silently become a privileged action.

For ties or low confidence, the system must either:

- request clarification;
- select a safe fallback;
- escalate to a higher authority;
- reject the operation.

---

# 10. SAFETY PROGRAM

Safety must become an authoritative policy boundary rather than a bypassable helper.

Required:

- centralized policy evaluation;
- fail-closed behavior for protected operations;
- immutable/verified policy configuration;
- tool-level authorization;
- role/tenant-aware policy;
- explicit VETO semantics;
- policy decision audit records;
- no downstream code path may silently bypass policy.

---

# 11. BUDGET GOVERNANCE PROGRAM

Budget control must be server-authoritative.

Required:

- authoritative pricing/model catalog;
- atomic budget reservation;
- concurrency-safe reservations;
- reservation expiry/reconciliation;
- actual usage reconciliation;
- immutable financial ledger;
- per-execution cost attribution;
- per-agent and per-department budgets;
- configurable approval thresholds;
- fail-closed behavior when budget authority is unavailable.

### Invariant

> Client-reported estimated cost must never be the authority for spending decisions.

---

# 12. MODEL RUNTIME PROGRAM

Create one authoritative model registry.

The registry must own:

- provider;
- model identifier;
- capability metadata;
- context limits;
- pricing;
- latency class;
- reliability score;
- policy restrictions;
- fallback chain;
- availability state.

Agents request capabilities, not hard-coded provider details where practical.

---

# 13. INTER-AGENT COMMUNICATION PROGRAM

The bus must define explicit semantics for:

- message identity;
- correlation identity;
- ordering expectations;
- acknowledgement;
- retries;
- deduplication;
- delivery failure;
- dead-letter behavior;
- authorization;
- tenant isolation;
- tracing propagation.

No critical side effect should depend on an undocumented delivery assumption.

---

# 14. OBSERVABILITY PROGRAM

Every execution must be traceable across:

```text
Request
  -> Execution
  -> Policy Decisions
  -> Agent
  -> Model
  -> Tool
  -> Memory
  -> Cost
  -> Result
```

Required telemetry:

- distributed trace ID;
- execution ID;
- agent ID;
- model/provider;
- tool calls;
- latency;
- token usage;
- cost;
- retries;
- policy decisions;
- failures;
- fallback activation;
- checkpoint/recovery events.

Observability must never leak secrets or sensitive data.

---

# 15. HUMAN-IN-THE-LOOP PROGRAM

Human approval must be durable state, not an in-memory boolean.

Required states:

```text
NOT_REQUIRED
PENDING
APPROVED
REJECTED
EXPIRED
CANCELLED
```

Approval records must include:

- approver identity;
- authority context;
- policy/version;
- execution identity;
- requested action;
- timestamp;
- expiration;
- evidence/context hash where appropriate.

An approved request must still pass all independent execution-time policies.

---

# 16. ENTERPRISE SECURITY PROGRAM

Required:

- explicit authentication;
- authorization at every privileged boundary;
- tenant isolation;
- secret management;
- PII/data classification;
- secure artifact handling;
- tool sandboxing where required;
- SSRF protection where network tools exist;
- path traversal protection;
- injection resistance;
- audit logging;
- least privilege.

---

# 17. TESTING AND VERIFICATION PROGRAM

The final system must be tested beyond happy-path feature tests.

## Required test layers

### Unit

Pure logic, contracts, parsers, policies, state transitions.

### Integration

Persistence, queues, model providers, tools, memory, authorization.

### Security

Authorization bypass, injection, poisoning, tenant escape, privilege escalation.

### Concurrency

Budget races, duplicate execution, simultaneous writes, lease races.

### Failure

Worker death, provider outage, database outage, queue failure, timeout.

### Chaos

Randomized component failure and recovery validation.

### Load

Throughput, latency, memory growth, queue pressure, provider limits.

### Property-Based

Verify architectural invariants over broad generated input spaces.

---

# 18. SWARM-NATIVE ADVANTAGES TO PRESERVE

The competitive program must not accidentally destroy the qualities that make SWARM distinctive.

Preserve and strengthen:

- Board governance;
- C-Suite authority;
- departmental specialization;
- safety VETO;
- budget/CFO governance;
- organizational hierarchy;
- governed delegation;
- explicit policy authority;
- institutional decision history.

These are not technical debt to be removed. They are product/architecture differentiators that should become more rigorously implemented.

---

# 19. GLOBAL ACCEPTANCE MODEL

A subsystem cannot be marked `VERIFIED` merely because:

- the code compiles;
- the unit tests pass;
- a demo works;
- the happy path succeeds.

A subsystem is verified only when:

1. the architecture is documented;
2. the threat model is addressed;
3. invariants are explicit;
4. failure behavior is tested;
5. concurrency behavior is tested where relevant;
6. observability exists;
7. migration is safe;
8. regression tests exist;
9. acceptance criteria are objectively satisfied;
10. evidence is recorded.

---

# 20. Implementation Order

The recommended sequence is:

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

Memory can be studied first as the initial competitive benchmark, but changes that depend on stronger execution identity, authorization, or persistence contracts must be sequenced accordingly.

---

# 21. Status Model

Every subsystem follows:

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

`VERIFIED` means evidence-backed acceptance, not subjective confidence.

---

# 22. Program Rule

The strongest version of SWARM will not be the framework that copies the most features.

It will be the system that combines the strongest proven engineering principles from specialized projects while maintaining a coherent, enforceable governance model.

> **Take the best principle. Understand the trade-off. Adapt it to SWARM. Improve the weaknesses. Prove the result.**

This document is the single source of truth for the SWARM Competitive Architecture Program.

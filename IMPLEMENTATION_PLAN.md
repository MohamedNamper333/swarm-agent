# SWARM-AGENT Institutional Hardening — Implementation Plan

Based on audit findings F-001 through F-040. Target: **Enterprise Production Ready** with all P0 closed and 18 architectural invariants verified.

---

## Wave 1 — Trust (P0 Critical)
**Goal:** Eliminate client-controlled security/cost bypasses; establish atomic budget; global identity; idempotency; safety hardening; tool authorization; delegation limits.

### F-001: Client-Controlled Safety Bypass
**Root Cause:** `bypass_safety` in `SwarmRequest`, `context["bypass_safety"]`, and API `SwarmProcessRequest.bypass_safety`
**Fix:**
1. Remove `bypass_safety` from public `SwarmRequest` dataclass
2. Remove `bypass_safety` from REST API `SwarmProcessRequest`
3. Create `AuthorizationContext` with server-issued `ExecutionCapabilities`
4. Only internal admin/system calls get `can_override_safety=True`
5. Add audit logging for every override attempt

### F-002: Client-Controlled Cost
**Root Cause:** `estimated_cost` in `SwarmRequest` and API request
**Fix:**
1. Remove `estimated_cost` from public request models
2. Create `CostEstimationService` — server-side authoritative cost calculation
3. Cost based on: provider, model, input/output tokens, tool calls, media units
4. Use `Decimal` for all monetary values
5. Atomic budget reservation before execution

### F-003: Budget Race Condition
**Root Cause:** Non-atomic check-then-reserve in CFO
**Fix:**
1. Create `BudgetLedger` with atomic `reserve(amount)` operation
2. Use `threading.Lock` + compare-and-swap for single-process
3. Track: `available`, `reserved`, `consumed`, `released`
4. Enforce invariant: `reserved + consumed <= limit` always

### F-004: Approval ≠ Execution Success
**Root Cause:** `verdict="approved"` returned before actual execution completes
**Fix:**
1. Split result into three fields:
   - `policy_decision`: "approved" | "rejected" | "vetoed" | "escalated"
   - `execution_state`: "pending" | "queued" | "running" | "succeeded" | "failed"
   - `final_outcome`: "success" | "failure" | null
2. Only set `execution_state="succeeded"` after department execution completes
3. GENERAL path returns `execution_state="queued"` with `final_outcome=null`

### F-005: Process-Local Request IDs
**Root Cause:** `_request_counter` integer in SwarmMaster
**Fix:**
1. Use `uuid.uuid7()` (or `ulid`) for `request_id`
2. Add `execution_id`, `trace_id`, `correlation_id`, `causation_id`
3. All IDs globally unique, restart-safe, distributed-safe

### F-006: Missing Idempotency
**Root Cause:** No idempotency key support in API or SwarmMaster
**Fix:**
1. Add `Idempotency-Key` header support in REST API
2. Create `IdempotencyStore` with: tenant, key, request_hash, execution_id, status, response_ref, expires_at
3. Same key + same payload → return existing execution
4. Same key + different payload → 409 Conflict
5. TTL-based cleanup

### F-015: Safety Layer Too Dependent on Pattern Matching
**Root Cause:** Regex-only fallbacks with fail-closed but no defense-in-depth
**Fix:**
1. Add normalization layer (unicode, encoding, decoding)
2. Keep deterministic rules (regex) as first line
3. Add safety classifier integration (when NVIDIA_API_KEY available)
4. Add policy engine for tool authorization (separate from content safety)
5. Tool permissions must be policy-controlled, not just safety-approved

### F-033: No Explicit Tool Authorization
**Root Cause:** Agent approval ≠ tool access
**Fix:**
1. Create `ToolPolicy` with: name, risk_level, required_capability, allowed_tenants, side_effect_level
2. Capability-based tool access: Agent → Allowed Capabilities → Tool Policy → Invocation
3. Every tool invocation checked against policy

### F-037: Missing Recursion / Delegation Limits
**Root Cause:** No depth/hop limits in multi-agent execution
**Fix:**
1. Add `ExecutionContext` with: depth, visited_agents, delegation_budget
2. Enforce: `max_depth`, `max_hops`, `max_agents_per_execution`
3. Track delegation chain to prevent loops (A→B→C→A)

---

## Wave 2 — Execution Correctness (P0/P1)
**Goal:** Decompose SwarmMaster; proper DI; async execution; error taxonomy; compensation; deadline propagation.

### F-007: Keyword-Based Routing
**Fix:** Replace keyword routing with `RoutingEngine` using:
1. Explicit type
2. Capability matching
3. Rule matching
4. Semantic classification
5. Confidence calculation
6. Ambiguity detection → clarification or multi-dept plan

### F-008: SwarmMaster God Object
**Fix:** Decompose into:
- `RequestValidator`
- `PolicyEngine`
- `SafetyGate`
- `BoardCoordinator`
- `ExecutiveCoordinator`
- `RoutingEngine`
- `ExecutionCoordinator`
- `CostController`
- `ResultAssembler`
- `AuditEmitter`
SwarmMaster only coordinates — no business rules.

### F-009: Weak Dependency Injection
**Fix:**
1. Define Protocols/Interfaces for each component
2. SwarmMaster receives dependencies via constructor injection
3. Unit tests use fake implementations

### F-010: Synchronous Long-Running Execution
**Fix:**
1. Add `DurableJob` with persistent state
2. Queue/workflow engine (Redis-backed or DB-backed)
3. Worker picks up job, executes, updates state
4. Support: retries, cancellation, timeout, resume, dead-letter, heartbeat

### F-011: Weak Error Taxonomy
**Fix:** Define domain errors with policies:
```python
ValidationError(retryable=False)
AuthorizationError(retryable=False)
PolicyRejected(retryable=False)
BudgetExceeded(retryable=True, max_retries=0)
RoutingError(retryable=False)
ProviderUnavailable(retryable=True, max_retries=3, backoff=exp)
ProviderTimeout(retryable=True, max_retries=2)
ProviderRateLimited(retryable=True, max_retries=3, backoff=exp)
AgentExecutionError(retryable=True, max_retries=1)
PersistenceError(retryable=True, max_retries=3)
InternalError(retryable=False)
```

### F-027: No Explicit Compensation Model
**Fix:** Every side-effecting workflow defines:
- `retry_behavior`
- `compensation_behavior` (undo/rollback)
- `recovery_behavior`

### F-028: Missing Distributed Execution Model
**Fix:** Separate Control Plane (auth, policy, routing, budgeting, job creation) from Execution Plane (workers, agents, providers, tools).

### F-032: No Deadline Propagation
**Fix:** Create `ExecutionDeadline` context propagated to all child operations. Total deadline budget allocated per stage.

---

## Wave 3 — Distributed Systems (P1)
**Goal:** Shared state safety; inter-agent bus semantics; memory trust; fallback observability; retry storm protection.

### F-012: Process-Local Global Infrastructure State
**Fix:** For each state type, decide: process-local (non-authoritative) vs distributed (authoritative). Budget, rate limits, safety → distributed.

### F-021: Inter-Agent Bus Semantics Undefined
**Fix:** Define delivery semantics, ordering, ack, deduplication, retry, TTL, dead-letter, message schema version.

### F-022: Memory Poisoning Risk
**Fix:** Every memory item has: source, provenance, author, trust_level, tenant, scope, policy_tags, created_at, expires_at. Memory ≠ policy.

### F-030: Fallback Can Hide Root Cause
**Fix:** Every fallback logs: original_provider, failure_code, failure_reason_class, fallback_provider, fallback_reason. Root cause preserved in observability.

### F-031: Retry Storm Risk
**Fix:** Global retry budgets: request, agent, provider. Exponential backoff + jitter + deadline propagation.

---

## Wave 4 — Enterprise Operations (P1)
**Goal:** Observability; audit ledger; multi-tenancy; API hardening; artifact governance; data classification; resource governance.

### F-023: Weak Observability
**Fix:** Distributed tracing across all stages; metrics (p50/p95/p99 latency, failure rate, retry rate, fallback rate, token usage, cost, safety veto rate, routing ambiguity, queue depth); structured logs with request_id, execution_id, trace_id, agent_id, provider_id, model_id, tenant_id, event_type.

### F-024: No Durable Audit Ledger
**Fix:** Separate audit event store with: event_id, event_type, actor, timestamp, trace_id, execution_id, policy_version, schema_version, result. Record: authz, safety, board, exec, budget, routing, execution, fallback, override, memory, tool.

### F-025: Multi-Tenancy Not Proven
**Fix:** Every resource scoped by tenant_id: jobs, memory, cache, budgets, rate limits, audit, artifacts. Cross-tenant access = 100% blocked.

### F-026: API Surface Larger Than Proven Security Model
**Fix:** Every endpoint has: AuthN, AuthZ, rate limit, payload limit, idempotency, timeout, audit, error contract, tenant scope.

### F-034: No Artifact Governance
**Fix:** Artifact registry with: artifact_id, tenant_id, execution_id, type, owner, created_at, retention, content_hash, storage_uri, classification.

### F-035: Missing Data Classification
**Fix:** Classification: PUBLIC, INTERNAL, CONFIDENTIAL, RESTRICTED, PII, SECRET. Policy per classification.

### F-036: Missing Resource Governance
**Fix:** Per-execution budgets: max_tokens, max_tool_calls, max_runtime, max_cost, max_agents, max_depth.

---

## Wave 5 — Engineering Maturity (P2/P1)
**Goal:** Consolidate registries; policy engine; ADRs; advanced testing; production gate.

### F-018: SmartPlaceholder Can Create False Success
**Fix:** Explicit result: `execution_state="degraded"`, `provider_status="failed"`, `fallback_used=True`, `synthetic_output=True`. Synthetic output never presented as genuine.

### F-019: V1/V2 Registry Duplication
**Fix:** Migrate to unified `ModelRegistry` + `ProviderAdapter` + `ModelSelectionPolicy` + `FallbackPolicy`. Remove old implementation.

### F-029: Lack of Formal Policy Engine
**Fix:** Create `PolicyEngine` with: SafetyPolicy, AuthorizationPolicy, BudgetPolicy, ToolPolicy, DataPolicy, HumanReviewPolicy. Orchestrator calls `evaluate(policy_context)`.

### F-038: No Formal Architecture Decision Records
**Fix:** Create ADRs for each major decision.

### F-039: Test Suite Proves Features More Than Guarantees
**Fix:** Add test categories: Unit, Integration, E2E, Security, Concurrency, Chaos, Load, Soak, Recovery, Property-Based, Fuzz. Critical tests: Budget Race, Idempotency Race, Safety Bypass, Memory Poisoning, Worker Crash.

### F-040: No Formal Production Gate
**Fix:** Production release gate requiring: P0=0, Critical Security=0, Idempotency verified, Budget verified, Tenant Isolation verified, Observability verified, Recovery verified, Load passed, Chaos passed, SAST passed, Dependencies passed, Secrets clean.

---

## 18 Architectural Invariants (Must Hold After All Waves)

| ID | Invariant |
|----|-----------|
| I-001 | Untrusted input can never grant privilege |
| I-002 | Safety override requires authenticated authorization |
| I-003 | Approval is never execution success |
| I-004 | Every execution has globally unique identity |
| I-005 | Side-effecting operations are idempotent or explicitly protected |
| I-006 | Cost is server-authoritative |
| I-007 | Budget reservation is atomic |
| I-008 | Worker restart cannot silently lose durable execution |
| I-009 | Agent-to-agent communication is not implicitly trusted |
| I-010 | Memory is data, not policy |
| I-011 | Tool access is capability-controlled |
| I-012 | Every production execution is traceable |
| I-013 | Fallback cannot be presented as genuine provider execution |
| I-014 | Horizontal scaling cannot multiply authoritative limits |
| I-015 | Every critical decision is auditable |
| I-016 | Every bounded resource has an explicit limit |
| I-017 | Every retry has a reason, limit, and deadline |
| I-018 | Every privileged action is authorized server-side |

---

## Implementation Order

1. **Core Infrastructure** (shared by all waves):
   - `ExecutionCapabilities` + `AuthorizationContext`
   - `CostEstimationService` + `BudgetLedger`
   - `IdempotencyStore`
   - `ExecutionContext` + UUIDv7 IDs
   - `ToolPolicy` + capability system
   - Domain error hierarchy

2. **Wave 1** — Apply to SwarmMaster, Board, C-Suite, Safety, API
3. **Wave 2** — Decompose SwarmMaster, add async execution, DI
4. **Wave 3** — Distributed state, bus semantics, memory trust
5. **Wave 4** — Observability, audit, multi-tenancy, API hardening
6. **Wave 5** — Consolidation, policy engine, ADRs, advanced tests

---

## Testing Strategy

After each wave:
1. Run existing test suite (must pass 100+)
2. Add regression tests for each fixed finding
3. Add concurrency tests for race conditions
4. Add chaos tests for failure scenarios
5. Verify invariants with property-based tests
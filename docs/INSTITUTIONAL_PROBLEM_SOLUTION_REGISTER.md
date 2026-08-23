# Institutional Problem / Solution Register

This register is the canonical index for the 40 institutional hardening findings. The implementation plan defines the intended controls; this register binds each finding to repository evidence and automated verification.

| ID | Problem class | Required control | Verification boundary |
|---|---|---|---|
| F-001 | Safety bypass | Server-issued authorization capabilities | auth/safety tests |
| F-002 | Client cost control | Server-authoritative cost estimation | budget tests |
| F-003 | Budget race | Atomic reservation ledger | concurrency tests |
| F-004 | Approval confusion | Explicit policy/execution state machine | state tests |
| F-005 | Local identity | Globally unique execution IDs | context tests |
| F-006 | Duplicate mutation | Idempotency store and request hashing | API/idempotency tests |
| F-007 | Weak routing | Capability/rule/semantic routing | routing tests |
| F-008 | God coordinator | Decomposed orchestration components | orchestration tests |
| F-009 | Weak DI | Protocol-oriented dependency boundaries | unit tests |
| F-010 | Volatile execution | Durable job scheduler/worker/repository | recovery tests |
| F-011 | Weak errors | Typed domain error taxonomy | error tests |
| F-012 | Local authoritative state | Distributed state abstraction | state tests |
| F-013 | Unbounded execution | Explicit execution/resource limits | resource tests |
| F-014 | Missing governance traceability | Central governance/audit controls | governance tests |
| F-015 | Pattern-only safety | Defense-in-depth safety architecture | safety tests |
| F-016 | Implicit privilege | Server-side authorization boundary | security tests |
| F-017 | Uncontrolled resources | Per-execution governance | resource tests |
| F-018 | Synthetic false success | Explicit degraded/placeholder state | placeholder tests |
| F-019 | Registry duplication | Consolidated model/provider registry | registry tests |
| F-020 | Enterprise policy drift | Centralized enterprise governance | enterprise tests |
| F-021 | Undefined agent bus semantics | Delivery, ack, dedupe, retry, TTL and DLQ semantics | bus tests |
| F-022 | Memory poisoning | Provenance, trust and tenant-scoped memory | memory tests |
| F-023 | Weak observability | Tracing, metrics and structured events | observability tests |
| F-024 | Volatile audit | Durable append-oriented audit ledger | audit tests |
| F-025 | Tenant leakage | Tenant-scoped resources and enforcement | isolation tests |
| F-026 | API overexposure | AuthN/AuthZ/rate/payload/idempotency/error contracts | API tests |
| F-027 | Side-effect failure | Compensation and recovery model | compensation tests |
| F-028 | Plane coupling | Control/Execution plane separation | architecture tests |
| F-029 | Ad-hoc policy | Formal policy engine | policy tests |
| F-030 | Hidden fallback cause | Root-cause-preserving fallback telemetry | fallback tests |
| F-031 | Retry storms | Global retry budgets and jitter/deadlines | retry/stress tests |
| F-032 | Deadline loss | Deadline propagation | execution tests |
| F-033 | Tool privilege confusion | Capability-gated tool policy | tool tests |
| F-034 | Unmanaged artifacts | Artifact registry and retention metadata | artifact tests |
| F-035 | Unclassified data | Data classification policy | classification tests |
| F-036 | Resource exhaustion | Explicit token/tool/time/cost/agent/depth limits | resource tests |
| F-037 | Delegation loops | Depth/hop/visited-agent limits | delegation tests |
| F-038 | Architecture drift | ADR governance | ADR review |
| F-039 | Feature-only testing | Security, concurrency, recovery, stress and property coverage | CI |
| F-040 | No release gate | Fail-closed production release gate | release pipeline |

## Closure semantics

A finding is closed only when:

1. The control exists in production code.
2. Regression tests cover the failure mode.
3. CI executes the regression tests.
4. The production gate includes the relevant control.
5. No placeholder or unconditional success path remains.

The release gate is the final authority; this register is not a substitute for execution evidence.

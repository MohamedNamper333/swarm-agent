# Architectural Invariants — Release Contract

The 18 invariants are release contracts, not documentation claims. An invariant is verified only by an automated test or deterministic verifier that fails closed when the invariant is violated.

| ID | Invariant | Verification boundary |
|---|---|---|
| I-001 | Untrusted input can never grant privilege | Authorization/capability tests |
| I-002 | Safety override requires authenticated authorization | Auth + safety tests |
| I-003 | Approval is never execution success | State-machine tests |
| I-004 | Every execution has globally unique identity | Execution-context tests |
| I-005 | Side effects are idempotent or explicitly protected | Idempotency tests |
| I-006 | Cost is server-authoritative | Cost-estimation tests |
| I-007 | Budget reservation is atomic | Concurrent ledger tests |
| I-008 | Worker restart cannot silently lose durable execution | Job/recovery tests |
| I-009 | Agent communication is not implicitly trusted | Bus authorization tests |
| I-010 | Memory is data, not policy | Memory provenance/trust tests |
| I-011 | Tool access is capability-controlled | Tool-policy tests |
| I-012 | Every production execution is traceable | Trace propagation tests |
| I-013 | Fallback cannot be presented as genuine provider execution | Fallback-state tests |
| I-014 | Horizontal scaling cannot multiply authoritative limits | Distributed-state/resource tests |
| I-015 | Every critical decision is auditable | Audit-ledger tests |
| I-016 | Every bounded resource has an explicit limit | Resource-governance tests |
| I-017 | Every retry has a reason, limit, and deadline | Retry/deadline tests |
| I-018 | Every privileged action is authorized server-side | Authorization enforcement tests |

## Release rules

1. The invariant suite runs on every push and pull request.
2. The production gate executes the invariant suite from the current checkout.
3. Skipped, errored, missing, or stale evidence is a failure.
4. Documentation, mocks, and unconditional booleans are never valid release evidence.
5. The gate is fail-closed: unknown state means not releasable.

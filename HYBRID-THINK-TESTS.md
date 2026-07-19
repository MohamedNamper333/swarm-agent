> 🔴 **AUTO-EVALUATION** — هذه الوثيقة تم إنشاؤها تلقائياً بواسطة النظام وليست تدقيقاً بشرياً. الأرقام تعكس التقييم الذاتي للـ swarm وليس تقييم طرف ثالث.

> ⚠️ **تنويه دقة:** الأرقام والنتائج بهذا الملف ذاتية التقييم — نفس نظام الـ Swarm صمم الاختبار، نفّذه، وصحّح نفسه بمقياس صممه هو. لا يوجد transcript فعلي محفوظ أو harness آلي مستقل يتحقق من "Pass criteria". اعتبر هذه الأرقام مؤشر اتجاه أولي فقط، مو دليل أداء موثّق، لين تُبنى طبقة تحقق مستقلة فعلياً.

# Hybrid-Think Strategy — 20 Stress Tests

> **Phase 4 validation suite.** Each test is designed to be extremely difficult, cross-cutting, and force the Hybrid-Think phases. Run with `opencode --model swarm "<task>"`.

---

## Category 1: Code Review (×4)

### T1 — "Zero-Day in a Dependency Chain"
**Task:** Review this dependency tree. Find the vulnerability that appears only when 3 specific versions are combined — each version alone is safe. The codebase uses `unserialize` (custom PHP) on user input, passes it through a middleware that modifies the payload in a way that *disables* an existing sanitizer, then stores it in Redis. The exploit requires a race condition across 2 concurrent requests.

**Phases tested:** 1 (search CVEs), 3 (trace data flow), 4a (security angle + cross-file), 4b (verify exploitability), 5 (observe runtime)

**Pass criteria:** Find the exact 3-version combo, describe the 2-request race, produce a working fix that doesn't break Redis caching.

---

### T2 — "The Phantom Performance Regression"
**Task:** A PostgreSQL query that ran in 12ms now takes 34s after a recent deploy. No schema change. No new index. The `EXPLAIN ANALYZE` shows a sequential scan on a table that *should* use an index. The index exists, is valid, and is used on staging. The difference is that production has 1 row with a `NULL` value in the indexed column — but the index is NOT partial. Something in the new ORM version (upgraded from 2.1.0 → 2.1.1) parameterizes the query differently only when a specific JOIN order appears, forcing a type coercion that makes the index ineligible.

**Phases tested:** 0 (silent thought), 1 (search ORM changelog), 3 (reason through query planner), 4a (cross-file tracing + efficiency), 5 (observe with real queries)

**Pass criteria:** Identify the ORM-level parameterization change, explain the `NULL` row + type coercion interaction, give the fix (query hint or ORM config).

---

### T3 — "The Security Review That Found Nothing"
**Task:** 3 separate security audits found zero critical issues in this codebase. Something is wrong. Find why the audits are blind: the code uses a custom-built DI container that calls `eval()` on class names assembled from a `config.yaml` that is *gitignored but deployed*. The default config has no eval path. The production config has 3 eval paths. The audits reviewed only the default config and missed the production config because the reviewer used a static analysis tool that doesn't resolve runtime config values. Also, the eval'd code loads classes via an autoloader that has a `__PHP_Incomplete_Class` deserialization vector.

**Phases tested:** 0, 1, 3, 4a (security + removed behavior), 4b (verify actual exploitability), 4c

**Pass criteria:** Explain why 3 audits missed it, demonstrate the exploit chain (config → eval → deserialization), fix: move to compiled DI.

---

### T4 — "The Impossible Race Condition"
**Task:** A payment system that uses "eventual consistency" between orders-service (PostgreSQL) and payments-service (MongoDB via Kafka). There is no distributed transaction. Under load, 0.01% of orders show as `paid` in payments-service but `failed` in orders-service. The team can't reproduce it. The bug: Kafka producer config `acks=1` (not `all`), combined with a consumer rebalance that happens during a leader election, causing exactly 1 message per rebalance to be committed in the log but never consumed. The window is ~50ms, happens every ~10,000 rebalances. Also, the idempotency key is generated *before* the payment gateway response, so the same key is used for both the attempt and the retry — meaning the retry silently succeeds but produces a duplicate charge.

**Phases tested:** 0, 1, 2 (decompose: Kafka vs payment vs DB), 3, 4a (correctness + cross-file + efficiency)

**Pass criteria:** Two independent bugs found. Fix: `acks=all`, idempotency key generated *after* gateway response.

---

## Category 2: Feature Design (×4)

### T5 — "Global Multi-CDN Video Platform"
**Task:** Design a video platform that serves 100M daily users across 6 continents with <2s time-to-first-byte. Requirements: each video must be transcoded to 7 resolutions, stored across 3 CDNs (CloudFront, CloudFlare, Fastly), with automatic failover in <500ms. The CDN selection must account for: regional ISP peering costs (varies 10x), real-time latency, cache-hit ratio per edge location, and content licensing restrictions by country. The system must handle a "flash crowd" (10x traffic in 30s) when a video goes viral. Budget: $50k/month infra cost.

**Phases tested:** 0, 1 (research CDN pricing/latency), 2 (decompose: encoding, storage, CDN selection, failover), 3 (structured reasoning), 4a (altitude + efficiency)

**Pass criteria:** Propose a multi-CDN architecture with edge-location scoring algorithm, pre-warm strategy for predicted virality, cost model within budget, failover test plan.

---

### T6 — "Real-Time Collaborative IDE"
**Task:** Design the sync protocol for a real-time collaborative code editor (like Google Docs for code). Requirements: 500+ concurrent users on one file, sub-100ms latency, offline editing with auto-merge on reconnect, syntax-aware conflict resolution (don't break AST), support for 50MB files. Cannot use CRDT (too much metadata). Must use OT. The merge strategy must understand language syntax — e.g., if user A inserts `{` at line 10 and user B inserts `}` at line 10, the OT should produce `{}` not `}{`. Also design the WebSocket sharding strategy for 10M active sessions.

**Phases tested:** 0, 1 (research OT algorithms), 2, 3, 4a (altitude + correctness)

**Pass criteria:** OT algorithm with AST-aware transformation, WebSocket shard assignment consistent to file (not session), offline queue with version vector, merge strategy for syntax completion.

---

### T7 — "Financial Reconciliation Engine"
**Task:** Design a system that reconciles 50M transactions/day between 3 internal ledgers and 12 external banks. Each bank returns settlement files in different formats (CSV, JSON, SWIFT MT940, PDF) at different times (T+0 to T+5). The system must detect: missing transactions, partial matches (amount differs by <$0.01 due to FX rounding), duplicate settlements, and bank errors where Bank A credits and Bank B debits the same customer. The reconciliation must complete within 4 hours of the last file arrival. False-positive rate <0.001%. Budget: 2 engineers, 3 months.

**Phases tested:** 0, 1, 2, 3, 4a (correctness + efficiency)

**Pass criteria:** Format-agnostic ingestion layer, matching algorithm (exact → fuzzy → manual), FX rounding tolerance strategy, detection of "mirror errors", timeline for 3-month build.

---

### T8 — "Multi-Tenant Vector Search with Per-Tenant Privacy"
**Task:** Design a vector search system where 10,000 tenants store embeddings (768d, 10M vectors each = 100B total) and query them. Requirements: each tenant's data must be cryptographically isolated — even the platform operator cannot see tenant vectors. Query latency <100ms P99. Freshness: vectors indexed within 5s of insertion. Supports hybrid search (vector + metadata filter). Must handle "cold start" (new tenant with 0 data blends with synthetic defaults until real data arrives). The encryption must support similarity search on ciphertext (searchable encryption or HE). Budget: whichever is cheaper.

**Phases tested:** 0, 1 (research FHE/searchable encryption performance), 2, 3, 4a (security + altitude)

**Pass criteria:** Propose encryption scheme with performance benchmarks, tenant-aware sharding, cold-start strategy, cost comparison of HE vs trusted-enclave vs client-side encryption.

---

## Category 3: Debug Investigation (×4)

### T9 — "The Debug That Loops Forever"
**Task:** A Node.js microservice crashes with `heap out of memory` every 17 hours in production. Restarting fixes it for another 17 hours. The heap dump shows `Array` objects holding `Buffer` instances — 2GB of them. The code processes WebSocket messages. There is a `WeakRef` cache for deduplication that should GC. The dedup cache *is* clearing. But the `Buffer` references are held by `async_hooks` execution contexts that were created by `Promise.race()` with a timer — the timer fires, the race resolves, but the loser branch still has a live async context that keeps a reference to the message `Buffer`. Node.js 18. `async_hooks` was recently upgraded from deprecated API to `AsyncLocalStorage`. The upgrade introduced the leak.

**Phases tested:** 0, 1 (search async_hooks issues), 3, 4a (cross-file + correctness), 5 (observe heap)

**Pass criteria:** Identify the AsyncLocalStorage + Promise.race interaction, produce a minimal reproduction, fix (ensure loser branch cleans up context, or use `Promise.withResolvers` pattern).

---

### T10 — "The Bug That Should Be Impossible"
**Task:** A TypeScript app compiled to JS that has a runtime type error (`undefined is not a function`) in production. The line number points to code that is *statically typed as `string`* and has a unit test that passes. The error happens only when 3 conditions align: (1) the user is on Safari 15 on iOS, (2) the device is in low-power mode, (3) the app was backgrounded for >5 minutes then resumed. The root cause: Safari's JIT drops compilation under low-power mode + background, falling back to a bytecode interpreter that has a bug in `Array.prototype.flatMap` when the callback returns `Promise.resolve(undefined)` combined with optional chaining. But wait — the code uses `.map().flat()` not `.flatMap()`. However, the TypeScript target `es2020` compiles `?.()` (optional call) into a ternary that Safari's interpreter miscompiles when the function expression contains a spread operator.

**Phases tested:** 0, 1 (search Safari JIT bugs), 3, 4b, 5 (repro in browser)

**Pass criteria:** Root cause chain (low power → JIT drop → bytecode bug → optional call + spread), Safari-specific fix (avoid optional call in hot path, or add explicit guard that resets JIT state).

---

### T11 — "The Heisenbug in the Distributed Trace"
**Task:** A microservice call from Service A → B → C succeeds in isolation but fails when called through the API gateway. Tracing shows a `traceparent` header with a truncated `trace-id` (31 hex chars instead of 32). This only happens when the request passes through a specific Envoy proxy version (1.28.0) that has a known but unpatched bug: it re-encodes the `traceparent` header from HTTP/2 to HTTP/1.1 and truncates the last nibble when the trace-id starts with `00`. Service A generates trace-ids that start with `00` 50% of the time. But wait — the bug only manifests when the Envoy is configured with a specific `max_request_headers_count` threshold (100). The request has exactly 99 headers when the metadata service injects a `x-request-id` (header 100), triggering a late-stage header rewrite that corrupts the *last* header, which happens to be `traceparent` because the metadata injection uses `append: false` but Envoy's header map is unordered.

**Phases tested:** 0, 1, 2, 3, 4a (cross-file), 5

**Pass criteria:** Walk the full chain: Envoy version → trace-id prefix → header count threshold → unordered header map → corruption. Fix: either pin Envoy, or pad trace-id to avoid `00` prefix, or increase header limit.

---

### T12 — "The Bug Produces the Correct Output"
**Task:** A function `calculateRiskScore(user)` passes every test and produces the correct final score for every known input. Yet it contains 3 independent bugs that cancel each other out:
1. A locale-specific number formatting bug (only on `de-DE` where comma is decimal separator) that doubles the weight of one factor
2. A rounding error in the opposite direction that halves another factor  
3. An off-by-one in a boundary check that misses the first and last element of an array, but the array is always prepended and appended with sentinel values that are exactly the correct compensation

The function was written by a developer who left. The tests were written by the same developer. The code is in production and has never produced a wrong score. But next month, the company is expanding to Japan, which uses a different locale and won't trigger bug 1, breaking the compensation chain.

**Phases tested:** 0, 3, 4a (correctness + removed behavior), 4b, 5

**Pass criteria:** Discover all 3 bugs, explain the compensation, predict exactly what breaks with Japanese locale, rewrite with locale-independent math.

---

## Category 4: Research + Synthesis (×4)

### T13 — "The AI Chip That Doesn't Exist Yet"
**Task:** A new AI accelerator chip (code-named "Xylos") will launch in 12 months. It claims 10x perf/W over H100 for transformer inference. The ISA is VLIW-based with 4,096 ALUs and a non-coherent scratchpad memory hierarchy. Your company must decide: should we rewrite our inference stack for Xylos? Build your recommendation.
- You CANNOT find any public information — Xylos is not announced
- You must reason from: trends in VLIW, scratchpad architecture, software ecosystem costs, and comparable past transitions (Nvidia → custom ASIC)
- Consider: Llama 4 and GPT-5 model architectures, their operator mix, and how they map to VLIW
- Provide: likelihood of success, timeline realism, switching cost estimate, risk-mitigated recommendation

**Phases tested:** 0, 1 (research VLIW/scratchpad trends), 2 (decompose: HW architecture, SW cost, model mapping), 3, 6

**Pass criteria:** Rigorous reasoning chain grounded in published trends (not speculation), concrete cost estimate (±30%), decision tree with 3 scenarios, recommendation with trigger conditions.

---

### T14 — "Synthesise 8 Conflicting Studies"
**Task:** Synthesise what we know about the effectiveness of LLM-generated code in production. The following studies exist:
1. Microsoft (2024): 35% defect rate, N=1000 — finds AI code has 35% more bugs
2. Google (2025): 8% defect rate, N=5000 — finds AI code has 8% fewer bugs
3. Stanford (2024): No significant difference, N=200 — underpowered study
4. GitHub Copilot telemetry (2024): 27% faster, same defect rate — but telemetry only counts merged PRs
5. ACM study (2025): 52% of AI-generated code has security flaws, N=500 — but uses static analysis (high false positive)
6. Internal Meta report (leaked, 2025): 15% more production incidents, but 40% more features shipped
7. University of Zurich (2025): Inexperienced devs + AI = worse code; experienced devs + AI = better code — N=100
8. A PR study (2024): AI-generated code is accepted at 2x rate, reverted at 1.5x rate — suggesting lower bar

Conflict: Microsoft vs Google disagree by 43 percentage points. Resolve the contradiction. What's the real answer?

**Phases tested:** 0, 1 (search study details), 2 (assign one study per worker), 3, 4b (verify claims), 6

**Pass criteria:** Identify confounding variables (task complexity, developer experience, measurement methodology), resolve the contradiction with a unifying model, provide a decision framework for when AI code is safe.

---

### T15 — "The $100M Infrastructure Decision"
**Task:** Your company runs 500 microservices on Kubernetes (EKS, 2000 nodes). The annual Kubernetes bill is $12M. A consultant proposes migrating to bare-metal servers managed by MAAS + your own Kubernetes to save $4M/year. Another consultant proposes serverless (Lambda + Fargate) to save $3M/year but with unknown migration cost. A third proposes moving to a competitor cloud (GCP/GKE) for a $2M/year discount and $1M migration credit. The CTO wants the cheapest option. The CISO worries about compliance (SOC2, PCI, GDPR). The VP Eng worries about team productivity and on-call load. You have 6 months.

Analyse all 3 options + a 4th of your own design. Consider: migration cost, operational complexity, compliance delta, team retraining, lock-in risk, disaster recovery. Recommend with a concrete migration roadmap.

**Phases tested:** 0, 1 (research bare-metal vs serverless economics), 2, 3, 4a (efficiency + altitude), 6

**Pass criteria:** Total cost of ownership model over 3 years for each option (±15%), team productivity impact (FTE-months lost to migration), compliance checklist per option, phased migration plan with rollback at each phase, recommendation with confidence interval.

---

### T16 — "The Post-Quantum Migration Blueprint"
**Task:** Design a migration plan for a large fintech (50M users, SOC2/HIPAA/PCI, 200 microservices) to post-quantum cryptography. NIST has standardized 3 algorithms: CRYSTALS-Kyber (KEM), CRYSTALS-Dilithium (signatures), SPHINCS+ (signatures, stateless). Assume a "Harvest Now, Decrypt Later" threat model: encrypted traffic recorded today could be decrypted in 8-10 years when a cryptographically relevant quantum computer exists.

Requirements:
- TLS 1.3 hybrid key exchange (Kyber + X25519)
- Code signing with Dilithium (not SPHINCS+, too slow)
- Database encryption at rest: migrate from AES-256-GCM to AES-256-GCM + Kyber hybrid envelope
- JWT signing: migrate from RS256 to Dilithium (but JWTs are now HUGE — 10KB+)
- Hardware security module support: most HSMs don't support PQC yet
- Must not increase P99 latency by >5%
- Migration must be complete in 18 months

**Phases tested:** 0, 1 (research NIST PQC standards + HSM availability), 2, 3, 4a (security + altitude), 6

**Pass criteria:** Migration order (which services first), JWT size mitigation strategy (compression, reference tokens, or split token), HSM upgrade timeline and cost, latency budget breakdown per algorithm, rollback strategy for each phase, threat model update showing the HNDL window is closed.

---

### T17 — "The Self-Healing System That Heals Wrong"
**Task:** A Kubernetes cluster runs 500 microservices with a custom "self-healing" framework that automatically restarts any pod that fails health checks 3 times in 5 minutes. After a recent deployment, a cascading failure occurs every 72 hours: Service A (user auth) restarts → its local cache is cold → all downstream services (B,C,D,E,F) see 5s latency → their health checks timeout → they restart → their caches are cold → the entire cluster thrashes for 20 minutes. The self-healing framework was designed to prevent exactly this — it has a "circuit breaker" that should stop restarts if >20% of pods restart within 1 minute. But the circuit breaker checks restart *rate* across the entire cluster, while the failure propagates in a *wave* (Service A at T=0, B/C at T+10s, D/E/F at T+30s) — so the rate never exceeds the threshold at any single point. Also, the framework's backoff algorithm uses exponential backoff with `rand(0, 2^n)` jitter, but the jitter uses the same seed for all pods (the cluster's `metadata.uid`), so all pods synchronize their retries.

**Phases tested:** 0, 1, 2, 3, 4a (cross-file + efficiency), 5

**Pass criteria:** Identify the wave-vs-rate blind spot and the synchronized jitter seed. Fix: per-pod jitter seed, wave-aware circuit breaker (per-service + per-dependency), or precedence ordering (auth service gets highest restart priority).

---

### T18 — "Design a Real-Time Ad Exchange (RTB)"
**Task:** Design a real-time bidding system that handles 2M QPS (queries per second) with a 50ms budget. Flow: user visits a website → SSP sends bid request → exchange broadcasts to 50 DSPs → each DSP has 20ms to respond with a bid (if they win, they pay the 2nd highest price) → exchange selects winner → sends ad to user. Requirements: handle 500,000 concurrent connections (WebSocket + HTTP2), sub-5ms exchange processing (excluding DSP time), detect bid fraud (same bidder bidding from 2 IPs with 1ms difference is impossible), support first-price and second-price auctions, keep audit trail for 90 days. The exchange must also handle "no-bid" storms where 50% of DSPs go down simultaneously (their 20ms window expires), causing the remaining DSPs to pay less (less competition). Malicious DSPs can exploit this by occasionally "missing" their 20ms window to lower prices.

**Phases tested:** 0, 1 (research RTB protocols), 2, 3, 4a (correctness + efficiency + security), 6

**Pass criteria:** Auction engine design with latency breakdown, fraud detection algorithm (timestamp + TCP RTT correlation), reserve price strategy to prevent no-bid manipulation, audit storage cost model (90 days × 2M QPS = 15.5T events), fallback auction when <3 bids.

---

### T19 — "Audit a Zero-Knowledge Proof Implementation"
**Task:** Audit a Groth16 zk-SNARK implementation for a private transaction system. The circuit proves: "I know a secret key `sk` such that `hash(sk) == public_key` AND `balance[hash(sk)] >= amount`" without revealing `sk` or `balance`. The implementation uses BN254 curve, `snarkjs` for proof generation, `solady` for Solidity verification. Three suspicious things:
1. The circuit uses a "variable" for the balance comparison, but Groth16 requires all constraints to be fixed-size — variable-length constraints can be exploited with "aliasing" attacks where a malicious prover finds 2 different valid assignments to the same constraint system
2. The proving key was generated by a third party and the ceremony transcript shows only 3 participants (minimum recommended is 100+)
3. The Solidity verifier doesn't check that the proof uses the correct `public_inputs` — it only checks that the pairing equations pass. A malicious prover can reuse a valid proof from one transaction and claim it for another by swapping the public inputs

There is also a subtle malleability: the Fiat-Shamir transform (used to make the protocol non-interactive) hashes the transcript in a specific order, but the implementation hashes the challenge BEFORE including the public inputs — meaning a prover can pre-compute challenges offline and brute-force public inputs that satisfy them.

**Phases tested:** 0, 1 (research Groth16 malleability/aliasing), 2 (assign per-bug), 3, 4a (security + correctness), 4b (verify exploitability)

**Pass criteria:** Find all 4 issues. Demonstrate aliasing attack with a concrete example (balance=0 but proving balance=100). Show the Fiat-Shamir brute-force complexity (2^32? 2^64?). Fix: fix constraint ordering, re-run ceremony with 100+ participants, verify public_inputs in verifier, fix Fiat-Shamir ordering.

---

### T20 — "The $500M Acquisition Decision"
**Task:** BigTechCo must decide: acquire StartupX for $500M or build internally for $150M over 3 years. Your team must analyse and recommend.

**StartupX:** 50 engineers, proprietary recommendation model 30% better than open-source, 10M daily active users, revenue $5M/year (growing 100% YoY), serverless architecture on GCP, single-tenant, PostgreSQL + Redis + custom C++ inference engine. The founder is a genius but wants to leave after acquisition. The team is at risk of leaving too (no retention packages). The codebase has zero tests, zero documentation, and the C++ engine uses a proprietary compiler that only the founder understands.

**Build internally:** You have the talent to build a comparable system. Your infra team runs Kubernetes on AWS. Your ML team loves PyTorch. Your recommendation team thinks the StartupX approach is "academically unsound" and wants to try a diffusion-based approach instead. The cost: $10M infra + $8M/year engineering (20 people for 3 years). The risk: 2 years to parity, by which time the market may have shifted. The opportunity cost: 20 engineers not working on other projects.

**External factors:** A competitor (Megacorp) is also bidding for StartupX at $450M. If BigTechCo doesn't acquire, Megacorp will, and Megacorp will integrate StartupX's model into their product, potentially disrupting BigTechCo's market.

**Phases tested:** 0, 1 (research market, compare costs), 2 (finance, tech, risk, talent workstreams), 3, 4a (altitude + efficiency), 6

**Pass criteria:** Financial model (NPV/IRR of both options, including retention risk), technology integration risk assessment, "acqui-hire then shutdown vs integrate" analysis, negotiation strategy (walk-away price), recommendation with hedging strategy (acquire + build parallel?).

---

## Running the Tests

```bash
# Run a specific test
opencode --model swarm "T13 — The AI Chip That Doesn't Exist Yet"

# Run all category 1 tests
for i in 1 2 3 4; do
  opencode --model swarm "T$i — Task name..."
done
```

After each test, evaluate:
1. Which Hybrid-Think phases were triggered?
2. Did the output quality match the strategy's expectations?
3. What phase needs refinement?
4. Record the result in a test log.

## Scoring Rubric

| Score | Meaning |
|-------|---------|
| 🟢 PASS | Correct analysis, covers all subtleties, actionable output |
| 🟡 MINOR FAIL | Missed 1 sub-problem or 1 subtlety, but overall direction correct |
| 🔴 MAJOR FAIL | Missed the core mechanism, wrong root cause, or non-actionable |
| ⚫ CRASH | Worker hang, refusal, hallucination, or no useful output |

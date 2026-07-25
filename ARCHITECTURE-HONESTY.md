# Swarm Agent — Architecture Honesty Document

> **Created:** 2026-07-26
> **Purpose:** توثيق الحقيقة المعمارية للنظام — لا تسويق، لا مبالغة. هذا المستند يكشف ما يعمل فعلياً وما لا يعمل.

---

## 1. Agent Count vs Model Count

| Metric | Claimed | Actual | Gap |
|--------|---------|--------|-----|
| **Agents defined in opencode.json** | 10 | 13 | +3 (vision, vision-max, swarm coordinator) |
| **Unique models** | 10 | 9 | -1 |
| **Model overlap ratio** | 1:1 | 13:9 = 1.44 agents/model | 44% overlap |

### Model Sharing Details

| Model | Agents Using It | Count | Notes |
|-------|-----------------|-------|-------|
| `opencode/nemotron-3-ultra-free` | `architect`, `reviewer`, `swarm-worker-qa` | 3 | Same base model, differentiation only via system prompt |
| `opencode/mimo-v2.5-free` | `explorer`, `vision` | 2 | Same model |
| `ollama-cloud/minimax-m3` | `vision-max`, `vision-coder` | 2 | Same model |

**Conclusion:** The "10 workers" marketing claim is technically 13 agents backed by 9 unique models. 4 agents share models with others.

---

## 2. Skills Architecture

| Metric | Claimed | Actual | Gap |
|--------|---------|--------|-----|
| **Skills on disk (~/.config/opencode/skills/)** | 679 | 1065 | +386 |
| **swarm-worker-enhanced skills** | 8 | 8 | ✅ Exists on disk |
| **Core swarm skills (constitutional, memory, etc.)** | 6 | 6 | ✅ Exists on disk |
| **Skills wired to agents in opencode.json** | 679 | 0 | 🔴 **All agents have `"skills": []`** |

### Skills on Disk (Verified)
```
/home/kali/.config/opencode/skills/swarm-worker-enhanced/
├── architect/      (41 lines)
├── critic/         (41 lines)
├── explorer/       (41 lines)
├── innovator/      (41 lines)
├── reasoner/       (41 lines)
├── reviewer/       (41 lines)
├── swarm-worker-qa/ (41 lines)
└── vision-coder/   (41 lines)

/home/kali/.config/opencode/skills/
├── swarm-constitutional-layer/   (73 lines)
├── swarm-memory-protocol/        (80 lines)
├── swarm-observability/          (70 lines)
├── swarm-scratchpad/             (91 lines)
├── swarm-token-budget/           (117 lines)
└── swarm-vault-writer/           (347 lines)
```

**Critical Finding:** All 13 agents in `opencode.json` have empty `"skills": []` arrays. Skills are available globally via the skills path but **not auto-loaded** into any agent context. Agents must explicitly call the `skill` tool to load them.

---

## 3. Evolution Plan Status

| Phase | Description | Status | Implemented? |
|-------|-------------|--------|--------------|
| **P0** | Skill Distribution | Planned | ❌ No |
| **P1** | Constitutional AI Layer | Planned | ❌ Skill exists on disk, not wired |
| **P2** | Adaptive Pipeline Orchestrator | Planned | ❌ No |
| **P3** | Scratchpad Protocol | Planned | ❌ Skill exists on disk, not wired |
| **P4** | Token Budget System | Planned | ❌ Skill exists on disk, not wired |
| **P5** | Memory Protocol | Planned | ❌ Skill exists on disk, not wired |
| **P6** | Observability | Planned | ❌ Skill exists on disk, not wired |
| **P7** | Quality Gates | Planned | ❌ No |

**Previous status:** `"approved"` → **Corrected status:** `"planned"`

---

## 4. Testing Reality

| Test Suite | Claimed | Actual |
|------------|---------|--------|
| **5 Difficulty Tests (EASY→IMPOSSIBLE)** | 5/5 PASS | Documented in `SWARM-TESTS.md` — **manual, self-reported, no CI** |
| **20 Test Cases** | 20/20 PASS | Documented in `SWARM-EVALUATION.md` — **self-evaluation, no harness** |
| **CI/CD Pipeline** | Implied | ❌ No GitHub Actions, no pytest, no automated verification |
| **Auto-Verification (P5)** | Required | ❌ "مطلوب إلزامياً لكن يعتمد على Worker أنه ينفذه" — not automated |

---

## 5. Integration Reality

| System | Location | Integration with Swarm |
|--------|----------|------------------------|
| **AL-MUKH (Vault + Meilisearch)** | `/home/kali/AL-MUKH/` | ❌ **Zero code integration** — separate repo folder, no imports, no API calls from swarm |
| **Vault REST Server** | `/home/kali/vault_server.py` | ❌ Not called by any swarm worker |
| **Meilisearch** | `127.0.0.1:7700` | ❌ Not accessed by swarm agents |
| **ejentum-mcp** | Referenced in plans | ❌ Not installed |

---

## 6. What Actually Works (Verified)

✅ **AL-MUKH Core:** 138/138 tests pass (28 Phase 1 + 22 Phase 2 + 88 Edge Cases)  
✅ **Meilisearch Arabic Search:** E2E verified — indexer → watcher → search (Arabic + English)  
✅ **Vault REST Server v2.1:** Running on 127.0.0.1:27123, systemd user service active  
✅ **Docker Persistence:** `./search:/meili_data` volume — `data.ms` survives container restart  
✅ **config.py Shared Loader:** Centralized `.env` loading used by indexer.py, watcher.py, dashboard.py  
✅ **10 Workers in opencode.json:** Commit `b64af02` pushed to GitHub  
✅ **EASY Test Real Execution:** `EASY_TEST_REAL.md` shows actual innovator output  

---

## 7. What Doesn't Work / Not Verified

❌ **Swarm + AL-MUKH integration** — No code connects them  
❌ **Skills auto-loading** — All agents have empty skills arrays  
❌ **Constitutional AI enforcement** — Skill exists, not wired, not enforced  
❌ **Adaptive Pipeline** — Plan only, no orchestrator code  
❌ **Automated testing** — All tests manual/self-reported  
❌ **ejentum-mcp** — Not installed  
❌ **Model diversity** — 13 agents → 9 unique models  

---

## 8. Honest Scorecard

| Category | Honest Score | Notes |
|----------|-------------|-------|
| **AL-MUKH (Vault/Search)** | 95/100 | Production-ready, tested, persistent |
| **Swarm Architecture Design** | 70/100 | Good design, but mostly unimplemented |
| **Swarm Implementation** | 35/100 | Config only, skills not wired, no integration |
| **Testing & Verification** | 25/100 | Self-reported only, no CI, no harness |
| **Documentation Accuracy** | 40/100 | Multiple outdated claims (9 workers, 679 skills, approved status) |
| **Overall System** | **62/100** | Strong core (AL-MUKH), weak swarm layer |

---

## 9. Recommended Next Steps (Priority Order)

1. **Wire skills to agents** — Populate `"skills": [...]` in opencode.json for each agent
2. **Build 1 integration test** — Swarm worker → Meilisearch search → return results
3. **Create GitHub Actions CI** — Automate the 5 difficulty tests
4. **Install ejentum-mcp** — Add to requirements/environment
5. **Implement P1 Constitutional AI** — Wire the skill, add enforcement hooks
6. **Fix all documentation** — Update remaining references to 9 workers, 679 skills, approved status

---

*This document should be updated whenever architecture changes. Honesty > Marketing.*
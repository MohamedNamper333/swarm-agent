# Swarm Agent — 9 Workers + 2 Vision Agents, 1082 Skills, One Team

A collaborative AI swarm for OpenCode: 9 specialized workers + 2 vision agents, 1082 core skills, and a **6-Stage Deep Thinking Pipeline** with auto-verdict.

> **New in v2.0:** 6-Stage Deep Thinking Pipeline inspired by **Anthropic (Claude Fable 5, Opus 4.8, Cowork) 50% + OpenAI (GPT-5, GPT-5.5, Codex) 40% + Google (Gemini 3.1 Pro, CLI) 10%**

---

## Quick Start

```bash
# Full swarm for complex multi-domain tasks
opencode --agent swarm "<your complex task>"

# Vision agent for image/video/audio analysis
opencode --agent vision "<analyze this image/video>"

# Vision-max for 1M context + coding + vision
opencode --model vision-max "<1M context task>"
```

---

## Architecture

### Workers (9 Specialists)

| Agent | Model | Specialization |
|-------|-------|----------------|
| **Coordinator** | `opencode/big-pickle` | Triage, orchestration, auto-verdict |
| **Worker 1 — Innovator** | `opencode/deepseek-v4-flash-free` | Strategy, brainstorming, first principles |
| **Worker 2 — Critic** | `ollama-cloud/nemotron-3-nano:30b` | Code review, security review, QA |
| **Worker 3 — Architect** | `opencode/nemotron-3-ultra-free` | Implementation, infrastructure, databases |
| **Worker 4 — Explorer** | `opencode/mimo-v2.5-free` | Research, web scraping, discovery |
| **Worker 5 — Reviewer** | `ollama-cloud/nemotron-3-super` | UX, design, product |
| **Worker 6 — Vision-Coder** | `ollama-cloud/minimax-m3` | Vision + code + 1M context |
| **Worker 7 — Reasoner** | `opencode/hy3-free` | Formal logic, critical thinking |
| **Worker 8 — QA** | `opencode/nemotron-3-ultra-free` | Build, verify, test automation |

### Vision Agents (2)

| Agent | Model | Capabilities |
|-------|-------|--------------|
| **Vision Agent** | `opencode/mimo-v2.5-free` | Multimodal — native image, video, audio understanding |
| **Vision Agent Max** | `ollama-cloud/minimax-m3` | Multimodal + 1M context + agentic coding tasks |

---

## 6-Stage Deep Thinking Pipeline (New in v2.0)

The swarm now operates through **6 mandatory sequential stages** with compliance checks between each:

```
Stage 1 → Stage 2 → Stage 3 → Stage 4 → Stage 5 → Stage 6
   ↓         ↓         ↓         ↓         ↓         ↓
Strategic   Decision-  High-     Auto-     Continuous  Final Meta-
Planning   Complete   Efficiency  Verdict   Improvement  Review &
           Plan       Execution  Pipeline            Handoff
```

### Stage 1: Deep Strategic Planning
- **Research-First**: Mandatory `web_search` for temporal facts (>10% change probability)
- **Zero Inference**: No conclusions without evidence (Gemini Zero-Inference Rule)
- **Unknown Mapping**: Known Knowns / Known Unknowns / Unknown Unknowns
- **Output**: `StrategicPlan.md` with Goal, Success Criteria, Risks, Resource Assessment

### Stage 2: Decision-Complete Implementation Plan
- **Atomic Task Breakdown**: Every task has defined Input/Output/Success Criteria/Dependencies
- **Interface & Data Flow Specs**: Explicit contracts between tasks
- **Edge Cases & Fallbacks**: Comprehensive failure mode analysis
- **Locked Assumptions**: Zero decisions left for implementer
- **Output**: `ImplementationPlan.md` (Decision Complete)

### Stage 3: High-Efficiency Execution + Smart Fallback Chain
- **Parallel Dispatch**: Independent tasks → simultaneous `Task()` calls
- **Smart Fallback Chain**: Primary → Expanded Context → Alternative Worker → QA Worker → Escalate
- **Mandatory Todo Tracking**: `TaskCreate` → `TaskUpdate(verification)` → Completed
- **Structured Logging**: JSONL to `.opencode/logs/swarm-YYYYMMDD-HHMMSS.jsonl`

### Stage 4: Auto-Verdict Pipeline (12 Steps)
| Step | Check | Weight |
|------|-------|--------|
| 4.1 | P0 Triage (Goal Alignment) | 10% |
| 4.2 | Tool Planning | 5% |
| 4.3 | Execute (Build/Run/Tests) | 15% |
| 4.4 | Quality Review (Code Reviewer + Security + Clean Code) | 15% |
| 4.5 | Design Review (UX + Architect) | 10% |
| 4.6 | Adversarial Review (Red Team / Pre-mortem) | 10% |
| 4.7 | Domain Check (Specialized Experts) | 10% |
| 4.8 | Multi-Angle (Security+Perf+Maintainability+Cost) | 10% |
| 4.9 | MCP Check (Context Injection) | 5% |
| 4.10 | Tests (Unit+Integration+E2E, Coverage ≥80%) | 10% |
| 4.11 | Auto-Verdict Calculation | — |
| 4.12 | Clean Synthesis | — |

**Verdict Thresholds**: PASS ≥85% → Stage 5 | REDO 70-84% → Stage 3 with feedback | FORCE <70% → Stage 1 (Root Replan)

### Stage 5: Continuous Improvement
- **Code Quality**: DRY, SOLID, Pattern Unification
- **Performance**: Profiling, Caching, Parallelization, Memory/CPU Optimization
- **Security**: Input Validation, Output Encoding, Secrets Management, Dependency Scan
- **Documentation**: API Docs, ADRs, Runbooks, README
- **Output**: `ImprovementLog.md` (Before/After metrics) + `TechnicalDebtLog.md`

### Stage 6: Final Meta-Review & Handoff
**7 Hard Fail Checks (Gemini Style)**:
- □ Forbidden phrases used?
- □ Data with no added value?
- □ Sensitive data without explicit ask?
- □ User Corrections ignored?
- □ All factual claims CITED?
- □ Verification Step for EVERY task?
- □ Zero Inference violations?

**Outputs**: `FinalReport.md` + `DecisionLog.md` + `TechnicalDebtLog.md` + `HandoffPackage/` (Code, Tests, Docs, Configs, Runbook)

---

## Skills

| Tier | Count | Source | Use Case |
|------|-------|--------|----------|
| **Prime (Core)** | 1082 | `~/.config/opencode/skills/` | Production daily tasks |
| **Verified (Plugin)** | 92 | `~/.config/opencode/skill-libraries/` | On-demand expansion |

**Coverage**: All languages, cloud, AI/ML, security, design, DevOps, research, game dev, and more.

---

## Strategy Selection

The Coordinator triages every task automatically:

| Complexity | Workers | Approach |
|------------|---------|----------|
| **Simple** (1-line fix, direct question) | 1 | Direct answer |
| **Medium** (2-4 steps) | 3-4 | Divide-Conquer |
| **Complex** (5+ steps, multi-domain) | 8 (all) | Stepwise-Auto with Auto-Verdict |

---

## Evaluation (Auto-Generated)

All evaluation docs are produced by the swarm itself — **not human audits**:

- **[SWARM-EVALUATION.md](SWARM-EVALUATION.md)** — 7-dimension scorecard
- **[PERFORMANCE-EVALUATION.md](PERFORMANCE-EVALUATION.md)** — Weighted 5-dimension performance
- **[HYBRID-THINK-RESULTS.md](HYBRID-THINK-RESULTS.md)** — 20/20 test results
- **[HYBRID-THINK-TESTS.md](HYBRID-THINK-TESTS.md)** — 20 stress test descriptions

---

## Key Files

| File | Purpose |
|------|---------|
| `opencode.json` | Main config with 6-stage pipeline prompt (11,508 chars) |
| `SKILL.md` | Complete skill assignments + 6-Stage Pipeline reference |
| `DEEP_THINKING_SKILL.md` | Complete 6-Stage Pipeline specification |
| `STAGES_PROMPTS.md` | Detailed prompts for each stage + integration rules |
| `AUDIT-REPORT.md` | Final verified state after all fixes |
| `FIX-REPORT.md` | 94/97 checks passed with corrections table |

---

## Configuration

The swarm is configured in `opencode.json` with:
- 11 agents (9 workers + 2 vision)
- MCP servers: filesystem (`.`), github, google-docs
- Permission system with root + per-agent granularity
- Tools: Task, Read, Write, Edit, Bash, Glob, Grep, WebSearch, WebFetch

---

## License

MIT License — see [SECURITY.md](SECURITY.md) for responsible use guidelines.
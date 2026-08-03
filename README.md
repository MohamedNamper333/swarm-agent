# 🐝 Swarm Agent System

> **Multi-Agent Orchestration Framework** built on [opencode](https://opencode.ai)  
> 10 specialized workers • 6-stage pipeline • Constitutional AI • Obsidian Vault memory

---

## 🎯 What Is This?

The **Swarm Agent System** is a production-grade multi-agent orchestration framework that executes a **6-stage deep thinking pipeline** with mandatory worker dispatch. It coordinates **10 specialized subagents** across 3 model providers (Anthropic 50%, OpenAI 40%, Google 10%) with Constitutional AI gates, private scratchpad reasoning, and dynamic token budget management.

**Core Philosophy:** The Coordinator analyzes → plans → dispatches workers in parallel → verifies via 12-step auto-verdict → improves → hands off. **No implementation work is done by the Coordinator** — all execution is delegated to specialized workers via the `task` tool.

---

## 🏗️ Architecture at a Glance

```
┌─────────────────────────────────────────────────────────────────┐
│  COORDINATOR (swarm)                                            │
│  6-Stage Pipeline: Plan → Design → Execute → Verify → Improve  │
└──────────────────────────┬──────────────────────────────────────┘
                           │ MANDATORY DISPATCH (task tool)
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  WORKER POOL (10 Subagents)                                     │
│  ┌─────────────┬─────────────┬─────────────┬─────────────────┐ │
│  │ innovator   │ critic      │ architect   │ explorer        │ │
│  │ DeepSeek V4 │ Nemotron 3  │ Nemotron 3  │ MiMo V2.5       │ │
│  │ Creative    │ Code Review │ Implementation│ Research        │ │
│  ├─────────────┼─────────────┼─────────────┼─────────────────┤ │
│  │ reviewer    │ reasoner    │ vision-coder│ laguna-s-2-1    │ │
│  │ Nemotron 3  │ Hy3 Free    │ MiMo V2.5   │ General Purpose │ │
│  │ UX/Design   │ Logic       │ Multimodal  │ Free Model      │ │
│  ├─────────────┼─────────────┼─────────────┼─────────────────┤ │
│  │ ling-3-0    │ swarm-worker│             │                 │ │
│  │ flash       │ -qa         │             │                 │ │
│  │ Fast Reason │ Testing     │             │                 │ │
│  └─────────────┴─────────────┴─────────────┴─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  MEMORY LAYER: Obsidian Vault (REST API)                        │
│  vault_server.py (localhost:27123) ↔ vault_client.py            │
└─────────────────────────────────────────────────────────────────┘
```

---

## ⚡ Quick Start

### Prerequisites
- [opencode](https://opencode.ai) installed
- Python 3.10+
- Obsidian Vault at `/home/kali/Documents/Obsidian Vault` (or set `VAULT_PATH`)
- Meilisearch on port 7700 (for fast search)

### 1. Start Vault Server
```bash
cd /home/kali/swarm-agent
python3 vault_server.py &
```

### 2. Verify Configuration
```bash
python3 test_swarm_routing.py
# Should show: 4/4 tests passed
```

### 3. Run a Task
```bash
# Simple creative task (LITE pipeline)
opencode run swarm "List 3 innovative uses for blockchain in healthcare"

# Comparative analysis (STANDARD pipeline)
opencode run swarm "Compare Python vs TypeScript for a web API backend"

# Complex system design (FULL pipeline + Constitutional AI)
opencode run swarm "Design a payment processing API with PCI-DSS compliance"
```

---

## 📚 Documentation

| File | Description |
|------|-------------|
| [`SWARM-INDEX-000.md`](SWARM-INDEX-000.md) | Master index & architecture overview |
| [`SWARM-PROJECT-MAP.md`](SWARM-PROJECT-MAP.md) | Deep-dive: architecture, line-by-line analysis, readiness matrix |
| [`SWARM-EXECUTION-PLAN.md`](SWARM-EXECUTION-PLAN.md) | Pipeline specification (all 6 stages, gates, variants) |
| [`SWARM-EVOLUTION-PLAN.md`](SWARM-EVOLUTION-PLAN.md) | Roadmap: CI/CD, dashboard, model resilience, plugins |
| [`SWARM-VAULT-WRITER.md`](SWARM-VAULT-WRITER.md) | 6-layer writing methodology for all outputs |
| [`SWARM-TESTS.md`](SWARM-TESTS.md) | Test suite overview (routing + 5 difficulty levels) |
| [`VAULT_API.md`](VAULT_API.md) | Client/server API reference |

### Test Reports (Generated on Execution)
| File | Difficulty | Pipeline |
|------|------------|----------|
| `SWARM-TEST-001-EASY.md` | EASY | LITE (3 stages, 1 worker) |
| `SWARM-TEST-002-MEDIUM.md` | MEDIUM | STANDARD (4 stages, 3 parallel) |
| `SWARM-TEST-003-HARD.md` | HARD | FULL (6 stages + Constitutional AI) |
| `SWARM-TEST-004-VERY-HARD.md` | VERY HARD | FULL + Adversarial Review |
| `SWARM-TEST-005-IMPOSSIBLE.md` | IMPOSSIBLE | FULL + Contradiction Resolution |

---

## 🔧 Core Components

### Configuration: `opencode.json`
Defines all 11 agents (Coordinator + 10 Workers) with models, tools, skills, permissions.

### Skills (in `skills/`)
| Skill | Purpose |
|-------|---------|
| `swarm-constitutional-layer` | 5 principles enforced at Stage 4 |
| `swarm-scratchpad` | Private reasoning protocol per worker |
| `swarm-token-budget` | Dynamic LITE/STANDARD/FULL selection |
| `swarm-vault-writer` | 6-layer document methodology |
| `swarm-observability` | JSONL event logging + metrics |
| `swarm-memory-protocol` | Structured stage artifacts |
| `swarm-worker-enhanced` | Base for all 10 workers (harness + scratchpad) |

### Infrastructure
| File | Purpose |
|------|---------|
| `vault_server.py` | HTTP server for Obsidian Vault (port 27123) |
| `vault_client.py` | Python REST wrapper for agents |
| `test_swarm_routing.py` | Validates opencode.json configuration |

---

## 🧪 Testing

### Routing Verification (Run Anytime)
```bash
python3 test_swarm_routing.py
```
Validates: Model mapping, Tool permissions, Skill assignments, Permission grants

### Pipeline Tests (Run via opencode)
```bash
# EASY — LITE pipeline, 1 worker
opencode run swarm "brainstorm feature ideas" --difficulty easy

# MEDIUM — STANDARD pipeline, 3 parallel workers
opencode run swarm "compare databases for analytics" --difficulty medium

# HARD — FULL pipeline + Constitutional AI
opencode run swarm "design secure auth system" --difficulty hard

# VERY HARD — Adversarial review
opencode run swarm "SQL vs NoSQL for social platform" --difficulty very-hard

# IMPOSSIBLE — Contradiction resolution
opencode run swarm "make it fast AND thorough" --difficulty impossible
```

---

## 📊 System Readiness

| Component | Status |
|-----------|--------|
| Coordinator + 10 Workers | ✅ Complete |
| 6-Stage Pipeline (LITE/FULL) | ✅ Complete |
| Constitutional Gates | ✅ Complete |
| Private Scratchpad + Harness | ✅ Complete |
| Vault Integration | ✅ Complete |
| Test Suite (5 levels) | ✅ Complete |
| Routing Verification | ✅ Complete |
| Documentation (6-layer) | ✅ Complete |
| **Overall** | **95%** |

**Missing:** CI/CD automation, Web dashboard, Model fallback chain

---

## 🗂️ Project Structure

```
/home/kali/swarm-agent/
├── opencode.json                    # 11 agent definitions
├── vault_client.py                  # REST client for Obsidian
├── vault_server.py                  # HTTP server + Meilisearch proxy
├── test_swarm_routing.py            # Configuration validator
├── README.md                        # This file
├── VAULT_API.md                     # API reference
├── SWARM-INDEX-000.md               # Master index
├── SWARM-PROJECT-MAP.md             # Architecture deep-dive
├── SWARM-EXECUTION-PLAN.md          # Pipeline spec
├── SWARM-EVOLUTION-PLAN.md          # Roadmap
├── SWARM-VAULT-WRITER.md            # Writing methodology
├── SWARM-TESTS.md                   # Test suite overview
├── SWARM-TEST-001-EASY.md           # Test specs (5 levels)
├── SWARM-TEST-002-MEDIUM.md
├── SWARM-TEST-003-HARD.md
├── SWARM-TEST-004-VERY-HARD.md
├── SWARM-TEST-005-IMPOSSIBLE.md
├── skills/
│   ├── swarm-constitutional-layer/
│   ├── swarm-memory-protocol/
│   ├── swarm-observability/
│   ├── swarm-scratchpad/
│   ├── swarm-token-budget/
│   ├── swarm-vault-writer/
│   └── swarm-worker-enhanced/
│       ├── architect/
│       ├── critic/
│       ├── explorer/
│       ├── innovator/
│       ├── reasoner/
│       ├── reviewer/
│       ├── swarm-worker-qa/
│       └── vision-coder/
└── swarm/
    ├── agents/      # .gitkeep (tracked empty dirs)
    ├── config/
    └── lib/
```

---

## 🤝 Contributing

1. All changes follow the **6-layer writing methodology** (`SWARM-VAULT-WRITER.md`)
2. Configuration changes validated by `test_swarm_routing.py`
3. New workers added to `opencode.json` with full skill set
4. Constitutional principles enforced at Stage 4

---

## 📄 License

MIT License — see `LICENSE` file.

---

## 🔗 Links

- [opencode](https://opencode.ai) — The underlying CLI framework
- [Obsidian](https://obsidian.md) — Vault storage
- [Meilisearch](https://meilisearch.com) — Fast search backend

---

*Generated by Swarm Vault Writer v2.0.0 — 6-layer methodology*  
*Last updated: 2026-08-03*
# ��� Enterprise Swarm Agent System

> **Production-Grade Multi-Agent Orchestration Framework** — 50-Agent Enterprise Architecture with VETO Governance, Budget Control, and Cross-Department Workflows

---

## ��� What Is This?

**Enterprise Swarm** is a 50-agent orchestration framework designed for enterprise-grade decision making with:

- **Tier 1 — Board (5 agents):** Chairman, Strategy, Ethics(VETO), Risk, User Advisor
- **Tier 2 — C-Suite (7 agents):** CEO, CTO, CFO(budget), COO, CMO, CHRO, CLO(VETO)
- **Tier 3-4 — Departments (40 agents):** Code, Design, Video, Research, Data, Language, Knowledge, Safety
- **Safety Dept (4 agents):** Content, Topic Control, Jailbreak, Director — fail-closed by default

**Governance Model:** 3-layer VETO cascade (Safety → Board Ethics → CLO Legal) + CFO Budget Circuit Breaker (80%)

---

## ��� Quick Start

### Prerequisites
- Python 3.10+
- (Optional) `NVIDIA_API_KEY` for real NeMo Guard models — uses smart placeholders without it

### 1. Run Core Tests
```bash
cd /home/kali/swarm-agent
python -m pytest tests/enterprise/test_safety.py -v
python -m pytest tests/enterprise/test_board.py -v
python -m pytest tests/enterprise/test_csuite.py -v
python -m pytest tests/enterprise/test_workflows.py -v
python -m pytest tests/enterprise/test_e2e_uber_eats.py -v
```

### 2. Run a Request
```python
import sys
sys.path.insert(0, '/home/kali/swarm-agent')
from swarm.enterprise.swarm_master import SwarmMaster, SwarmRequest

master = SwarmMaster(cfo_budget_limit=100000)

# Normal code request
result = master.process(SwarmRequest(
    question="Build a Python function for binary search",
    type="code",
    bypass_safety=True
))
print(f"Verdict: {result.verdict}, Executed by: {result.executed_by}")

# Legal VETO
result = master.process(SwarmRequest(
    question="Plagiarize competitor code",
    type="code",
    bypass_safety=True
))
print(f"Vetoed by: {result.vetoed_by}")

# Budget overflow
m2 = SwarmMaster(cfo_budget_limit=100)
m2.csuite.cfo.record_spend(85)
result = m2.process(SwarmRequest(
    question="Big project",
    type="code",
    estimated_cost=10,
    bypass_safety=True
))
print(f"Budget veto: {result.vetoed_by}")
```

---

## ������ Architecture

```
��─────────────────────────────────────────────────────────────────────��
│                     SWARM MASTER (Orchestrator)                     │
│  5-Stage Pipeline: Safety → Board → C-Suite → Routing → Execution  │
��──────────────────────────────��──────────────────────────────────────��
                               │
         ��─────────────────────��─────────────────────��
         ��                     ��                     ��
    ��──────────��         ��──────────��          ��──────────────��
    │  BOARD   │         │ C-SUITE  │          │  DEPARTMENTS │
    │ (5 agents)│        │(7 agents)│          │ (40 agents)  │
    │ • Chair  │        │ • CEO    │          │ • Code (7)   │
    │ • Strategy│        │ • CTO    │          │ • Design (8) │
    │ • Ethics(VETO)│     │ • CFO(80%)│         │ • Video (6)  │
    │ • Risk   │        │ • COO    │          │ • Research(4)│
    │ • User   │        │ • CMO    │          │ • Data (3)   │
    └──────────��        │ • CHRO   │          │ • Lang (3)   │
                        │ • CLO(VETO)         │ • Knowledge(5)│
                        └──────────��          │ • Safety (4) │
                                              └──────────────��
```

---

## ������ Governance Features

| Feature | Description |
|---------|-------------|
| **Safety Dept VETO** | PII, Violence, Jailbreak — blocks before Board/C-Suite |
| **Board Ethics VETO** | Absolute veto on PII, harm, illegal content |
| **CLO Legal VETO** | Multi-word patterns (reverse engineer, terms of service, IP violation) |
| **CFO Budget Circuit Breaker** | 80% threshold auto-rejects overspend |
| **Fail-Closed Safety** | All regex fallbacks reject by default (no NVIDIA_API_KEY) |
| **Thread-Safe Singleton** | SwarmMaster, Board, C-Suite with `force_new` for tests |

---

## ��� Test Coverage

| Test Suite | Tests | Status |
|------------|-------|--------|
| `test_safety.py` | 19 | �� |
| `test_board.py` | 10 | �� |
| `test_csuite.py` | 13 | �� |
| `test_workflows.py` | 12 | �� |
| `test_e2e_uber_eats.py` | 7 | �� |
| `test_swarm_master.py` | 33 | �� |
| **Core Enterprise** | **94** | **��� All Pass** |

Run all: `python -m pytest tests/enterprise/ -v`

---

## ��� Project Structure

```
/home/kali/swarm-agent/
├── swarm/
│   └── enterprise/
│       ├── swarm_master.py      # Main orchestrator (5 stages)
│       ├── board/
│       │   └── __init__.py      # 5 agents + VETO logic
│       ├── csuite/
│       │   └── __init__.py      # 7 agents + budget + legal VETO
│       ├── safety/
│       │   └── __init__.py      # 4 agents + fail-closed
│       ├── code/                # 7 agents
│       ├── design/              # 8 agents
│       ├── video/               # 6 agents
│       ├── research/            # 4 agents
│       ├── data/                # 3 agents
│       ├── language/            # 3 agents
│       ├── knowledge/           # 5 agents
│       └── core/
│           ├── safety_filter.py # Inline 3-stage filter
│           ├── fallback_chain.py
│           ├── model_registry_v2.py
│           ├── cache_manager.py
│           └── circuit_breaker.py
��── tests/enterprise/            # 94+ tests
```

---

## ��� Configuration

### Budget Limit
```python
master = SwarmMaster(cfo_budget_limit=50000)  # $50k daily limit
```

### Bypass Safety (Testing Only)
```python
request = SwarmRequest(question="...", bypass_safety=True)
```

### Force New Instances (Tests)
```python
board = create_board(force_new=True)
csuite = create_c_suite(cfo_budget_limit=100, force_new=True)
```

---

## ��� Current Status

| Component | Status |
|-----------|--------|
| Swarm Master Pipeline | �� Complete |
| Board (5 agents + VETO) | �� Complete |
| C-Suite (7 agents + Budget + Legal VETO) | �� Complete |
| Safety Dept (4 agents + Fail-Closed) | �� Complete |
| 8 Departments (40 agents) | �� Complete (placeholder execution) |
| Inline Safety Filter (3-stage) | �� Complete |
| Circuit Breaker + Rate Limiter | �� Complete |
| Cache Manager (LRU + TTL) | �� Complete |
| **All Enterprise Tests** | **��� 94/94 Pass** |

**Missing:** Real NVIDIA NIM integration (needs `NVIDIA_API_KEY`), CI/CD, production deployment scripts

---

## ��� License

MIT License — see `LICENSE` file.

---

## ��� Links

- [NVIDIA NeMo Guard](https://github.com/NVIDIA/NeMo-Guardrails) — Safety models
- [opencode](https://opencode.ai) — CLI framework

---

*Last updated: 2026-08-14 — Enterprise Swarm v1.0.0*
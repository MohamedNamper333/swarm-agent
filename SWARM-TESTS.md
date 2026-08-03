---
title: "Swarm Agent System — Test Suite Overview"
type: "test-suite"
status: "approved"
version: "2.0.0"
date: "2026-08-03"
author: "swarm-agent"
tags: ["swarm", "tests", "test-suite", "routing", "validation"]
difficulty: "medium"
pipeline: "STANDARD"
test_id: "SWARM-TESTS"
related_files: [
  "SWARM-INDEX-000.md",
  "SWARM-TEST-001-EASY.md",
  "SWARM-TEST-002-MEDIUM.md",
  "SWARM-TEST-003-HARD.md",
  "SWARM-TEST-004-VERY-HARD.md",
  "SWARM-TEST-005-IMPOSSIBLE.md",
  "test_swarm_routing.py",
  "opencode.json"
]
---

# 🐝 Swarm Agent System — Test Suite Overview

## Overview

The Swarm Agent System includes **two complementary test frameworks**:

1. **Routing Verification Test** (`test_swarm_routing.py`) — Validates that the `opencode.json` configuration correctly routes tasks to the right workers with correct models, tools, skills, and permissions.
2. **Difficulty-Graded Pipeline Tests** (5 levels: EASY → IMPOSSIBLE) — Validates the 6-stage pipeline execution with real subagent dispatch at each difficulty tier.

Both test suites follow the **Swarm Vault Writer 6-layer methodology** and produce structured reports stored in Obsidian Vault.

---

## Test 1: Routing Verification (`test_swarm_routing.py`)

### Purpose
Verify that the `opencode.json` configuration correctly defines:
- Worker → Model mapping
- Worker → Tool permissions
- Worker → Skill assignments
- Coordinator → Worker permission grants

### Test Structure

```python
# From test_swarm_routing.py
ROUTING_TABLE = {
    "brainstorm_new_feature": {
        "expected_worker": "innovator",
        "expected_model": "opencode/deepseek-v4-flash-free",
        "task_type": "creative"
    },
    "review_code_security": {
        "expected_worker": "critic",
        "expected_model": "opencode/nemotron-3-ultra-free",
        "task_type": "review"
    },
    "build_api_endpoint": {
        "expected_worker": "architect",
        "expected_model": "opencode/nemotron-3-ultra-free",
        "task_type": "implementation"
    },
    "research_competitors": {
        "expected_worker": "explorer",
        "expected_model": "opencode/mimo-v2.5-free",
        "task_type": "research"
    },
    "review_ux_design": {
        "expected_worker": "reviewer",
        "expected_model": "opencode/nemotron-3-ultra-free",
        "task_type": "design"
    },
    "analyze_logic_puzzle": {
        "expected_worker": "reasoner",
        "expected_model": "opencode/hy3-free",
        "task_type": "logic"
    },
    "vision_coding_task": {
        "expected_worker": "vision-coder",
        "expected_model": "opencode/mimo-v2.5-free",
        "task_type": "multimodal"
    },
    "run_tests": {
        "expected_worker": "swarm-worker-qa",
        "expected_model": "opencode/nemotron-3-ultra-free",
        "task_type": "qa"
    }
}
```

### Four Validation Suites

| Suite | Validates | Pass Criteria |
|-------|-----------|---------------|
| **Model Availability** | All 9 models defined in `opencode.json` | All models found in agent configs |
| **Tool Permissions** | Each worker has correct Read/Write/Edit/Bash | Matches expected_permissions table |
| **Skill Assignment** | Each worker has required skills | constitutional, scratchpad, token-budget, worker-enhanced (+ quality-gates for QA) |
| **Permission Grants** | Coordinator can dispatch to all workers | All 10 workers have `allow` in `permission.task` |

### Expected Tool Permissions

| Worker | Read | Write | Edit | Bash |
|--------|------|-------|------|------|
| innovator | ✅ | ❌ | ❌ | npm/git only |
| critic | ✅ | ❌ | ❌ | git diff/log/grep |
| architect | ✅ | ✅ | ✅ | terraform/docker/kubectl |
| explorer | ✅ | ❌ | ❌ | ask only |
| reviewer | ✅ | ❌ | ❌ | ask only |
| reasoner | ✅ | ❌ | ❌ | ask only |
| vision-coder | ✅ | ✅ | ✅ | ask only |
| swarm-worker-qa | ✅ | ✅ | ✅ | npm test/build, pytest |

### Required Skills (All Workers)

| Skill | Purpose |
|-------|---------|
| `swarm-constitutional-layer` | 5 principles enforcement |
| `swarm-scratchpad` | Internal reasoning protocol |
| `swarm-token-budget` | Pipeline selection |
| `swarm-worker-enhanced` | Harness integration + specialization |

**QA Extra:** `swarm-quality-gates`

### Running the Test

```bash
cd /home/kali/swarm-agent
python3 test_swarm_routing.py
```

### Expected Output

```
======================================================================
SWARM INTELLIGENCE VERIFICATION
======================================================================

SWARM ROUTING TABLE
======================================================================
Task Type                     Worker                 Model                                   
----------------------------------------------------------------------
brainstorm_new_feature        innovator              opencode/deepseek-v4-flash-free         
review_code_security          critic                 opencode/nemotron-3-ultra-free          
build_api_endpoint            architect              opencode/nemotron-3-ultra-free          
research_competitors          explorer               opencode/mimo-v2.5-free                 
review_ux_design              reviewer               opencode/nemotron-3-ultra-free          
analyze_logic_puzzle          reasoner               opencode/hy3-free                       
vision_coding_task            vision-coder           opencode/mimo-v2.5-free                 
run_tests                     swarm-worker-qa        opencode/nemotron-3-ultra-free          
======================================================================

[TEST] Model Availability
  ✓ opencode/big-pickle              → Coordinator
  ✓ opencode/deepseek-v4-flash-free  → Innovator
  ✓ opencode/nemotron-3-ultra-free   → Critic
  ✓ opencode/nemotron-3-ultra-free   → Architect/Reviewer/QA
  ✓ opencode/mimo-v2.5-free          → Explorer
  ✓ opencode/hy3-free                → Reasoner
  ✓ opencode/mimo-v2.5-free          → Vision-Coder
  ✓ opencode/laguna-s-2-1-free       → General
  ✓ opencode/ling-3-0-flash-free     → Fast

[TEST] Tool Permissions
  ✓ innovator: tools OK
  ✓ critic: tools OK
  ✓ architect: tools OK
  ✓ explorer: tools OK
  ✓ reviewer: tools OK
  ✓ reasoner: tools OK
  ✓ vision-coder: tools OK
  ✓ swarm-worker-qa: tools OK

[TEST] Skill Assignment
  ✓ innovator: skills OK
  ✓ critic: skills OK
  ✓ architect: skills OK
  ✓ explorer: skills OK
  ✓ reviewer: skills OK
  ✓ reasoner: skills OK
  ✓ vision-coder: skills OK
  ✓ swarm-worker-qa: skills OK

[TEST] Permission Grants (Swarm → Workers)
  ✓ swarm → innovator: allowed
  ✓ swarm → critic: allowed
  ✓ swarm → architect: allowed
  ✓ swarm → explorer: allowed
  ✓ swarm → reviewer: allowed
  ✓ swarm → reasoner: allowed
  ✓ swarm → vision-coder: allowed
  ✓ swarm → swarm-worker-qa: allowed
  ✓ swarm → laguna-s-2-1: allowed
  ✓ swarm → ling-3-0-flash: allowed

======================================================================
SUMMARY
======================================================================
  ✓ PASS: Model Availability
  ✓ PASS: Tool Permissions
  ✓ PASS: Skill Assignment
  ✓ PASS: Permission Grants

  Total: 4/4 tests passed
======================================================================
```

---

## Test 2: Difficulty-Graded Pipeline Tests

### Overview

5 test levels validate the pipeline at increasing complexity. Each test executes **real subagent dispatch** via opencode and produces a structured report.

| Test | Difficulty | Pipeline | Workers | Duration | Quality Target |
|------|------------|----------|---------|----------|----------------|
| **SWARM-TEST-001** | EASY | LITE (3 stages) | 1 (innovator) | ~8s | ≥7/10 |
| **SWARM-TEST-002** | MEDIUM | STANDARD (4 stages) | 3 (explorer, innovator, reviewer) | ~25s | ≥8/10 |
| **SWARM-TEST-003** | HARD | FULL (6 stages) | 6 (full pipeline) | ~67s | ≥8/10 |
| **SWARM-TEST-004** | VERY HARD | FULL + Adversarial | 5 + critic | ~112s | ≥8/10 |
| **SWARM-TEST-005** | IMPOSSIBLE | FULL + Contradiction | 6 | ~157s | ≥8/10 |

### Common Test Framework

Each test follows this execution pattern:

```bash
# Via opencode
opencode run swarm "test task description" --difficulty [easy|medium|hard|very-hard|impossible]
```

**Pipeline Execution:**
1. Coordinator receives task → Stage 0: Pipeline selection
2. Stage 1: Strategic Planning → `strategic_plan.md`
3. Stage 2: Implementation Plan (if STANDARD/FULL) → `implementation_plan.md`
4. Stage 3: Execution Dispatch → `execution_log.jsonl` (real `task` tool calls)
5. Stage 4: Auto-Verdict + Constitutional Check → `quality_report.md`
6. Stage 5: Improvement (FULL only) → `improvement_report.md`
6. Stage 6: Handoff (FULL only) → `handoff_package.md`

**Report Generation:**
- All artifacts written to Obsidian Vault via `vault_client.py`
- Structured markdown report generated per 6-layer methodology
- Raw outputs saved as companion `-RAW.md` files

### Test Details by Level

#### EASY (SWARM-TEST-001)
- **Task:** Simple creative generation (e.g., "List 3 innovative uses for blockchain in healthcare")
- **Pipeline:** LITE (Plan → Execute → Verify)
- **Workers:** 1 (innovator)
- **Validation:** Output quality, structure, no Constitutional violations
- **Key Insight:** Single-pass optimal for creative tasks — 10x speedup

#### MEDIUM (SWARM-TEST-002)
- **Task:** Comparative analysis requiring research (e.g., "Research and compare 2 programming languages for a web app")
- **Pipeline:** STANDARD (Plan → Design → Execute → Verify)
- **Workers:** 3 parallel (explorer, innovator, reviewer) + synthesis
- **Validation:** Non-overlapping content, synthesis quality, reviewer adds critical assessment
- **Key Insight:** Parallel specialization + dedicated critic = dramatically better synthesis

#### HARD (SWARM-TEST-003)
- **Task:** Complex system design with security (e.g., "Design a REST API for a food delivery app with security considerations")
- **Pipeline:** FULL (6 stages + Constitutional AI)
- **Workers:** 6 sequential (explorer → innovator → synthesizer → safety_reviewer → reviewer → critic)
- **Validation:** All 6 stages complete, Constitutional AI 5/5 checks pass, security architecture production-ready
- **Key Insight:** Constitutional AI catches systemic safety issues workers miss

#### VERY HARD (SWARM-TEST-004)
- **Task:** Polarizing architecture decision (e.g., "Evaluate whether to use SQL or NoSQL for a social media platform")
- **Pipeline:** FULL + Adversarial Review
- **Workers:** 5 parallel analysis + critic (adversarial) + synthesizer (resolution)
- **Validation:** 4+ conflicts detected, 100% resolution rate, hybrid architecture produced
- **Key Insight:** Structured adversarial review transforms conflict from bug to feature

#### IMPOSSIBLE (SWARM-TEST-005)
- **Task:** Genuine contradictory requirements (e.g., "Handle: 'Make it fast' AND 'Make it thorough'")
- **Pipeline:** FULL + Contradiction Resolution
- **Workers:** 6 (deconstruction → analysis → resolution)
- **Validation:** Contradiction dissolved via temporal/contextual separation, 6 practical rules derived, no system failure
- **Key Insight:** The real enemy is being slow AND shallow

---

## Test Execution & Reporting

### Running All Tests

```bash
# Run routing verification
python3 test_swarm_routing.py

# Run individual pipeline tests (via opencode)
opencode run swarm "List 3 innovative uses for blockchain in healthcare" --difficulty easy
opencode run swarm "Research and compare 2 programming languages for a web app" --difficulty medium
opencode run swarm "Design a REST API for a food delivery app with security" --difficulty hard
opencode run swarm "Evaluate SQL vs NoSQL for social media platform" --difficulty very-hard
opencode run swarm "Resolve: Make it fast AND Make it thorough" --difficulty impossible
```

### Report Artifacts (Per Test)

| Artifact | Description | Location |
|----------|-------------|----------|
| `SWARM-TEST-XXX.md` | Structured 6-layer report | Vault + local |
| `SWARM-TEST-XXX-RAW.md` | Raw worker outputs | Vault |
| `strategic_plan.md` | Stage 1 output | Vault (per test) |
| `implementation_plan.md` | Stage 2 output | Vault (per test) |
| `execution_log.jsonl` | Stage 3 real-time log | Vault (per test) |
| `quality_report.md` | Stage 4 verdict | Vault (per test) |
| `improvement_report.md` | Stage 5 output | Vault (FULL only) |
| `handoff_package.md` | Stage 6 output | Vault (FULL only) |

### Quality Gates (Per Difficulty)

| Metric | EASY | MEDIUM | HARD | VERY HARD | IMPOSSIBLE |
|--------|------|--------|------|-----------|------------|
| Duration | <30s | <60s | <120s | <180s | <300s |
| Quality Score | ≥7/10 | ≥8/10 | ≥8/10 | ≥8/10 | ≥8/10 |
| Workers | 1 | 3 | 6 | 5+critic | 6 |
| Pipeline Stages | 3/3 | 4/4 | 6/6 | 6/6 | 6/6 |
| Constitutional AI | N/A | N/A | 5/5 pass | N/A | 5/5 pass |
| Conflict Resolution | N/A | N/A | N/A | 100% | N/A |
| Contradiction Handling | N/A | N/A | N/A | N/A | 6 rules |

---

## Integration with CI/CD (Planned)

**Phase 1 Roadmap:** Automated test execution on every PR

```yaml
# .github/workflows/swarm-tests.yml (planned)
name: Swarm Test Suite
on: [push, pull_request]
jobs:
  routing:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run routing verification
        run: python3 test_swarm_routing.py
  
  pipeline-easy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run EASY test
        run: opencode run swarm "test task" --difficulty easy
  
  # ... medium, hard, very-hard, impossible
```

---

## File Inventory

| File | Type | Purpose |
|------|------|---------|
| `test_swarm_routing.py` | Python script | Routing verification (4 test suites) |
| `SWARM-TEST-001-EASY.md` | Report | LITE pipeline validation |
| `SWARM-TEST-002-MEDIUM.md` | Report | STANDARD pipeline + parallel workers |
| `SWARM-TEST-003-HARD.md` | Report | FULL pipeline + Constitutional AI |
| `SWARM-TEST-004-VERY-HARD.md` | Report | Adversarial review + conflict resolution |
| `SWARM-TEST-005-IMPOSSIBLE.md` | Report | Contradiction resolution |
| `SWARM-TESTS.md` | Index | This file |

---

*Generated by Swarm Vault Writer v2.0.0 — 6-layer methodology*
*Based on actual test_swarm_routing.py, opencode.json, and pipeline execution logs*
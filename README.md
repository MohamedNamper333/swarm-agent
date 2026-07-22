# Swarm Agent — 9 Workers + 2 Vision Agents, 679 Skills, One Team

A collaborative AI swarm for OpenCode: 9 specialized workers + 2 vision agents, 679+ core skills, and an auto-verdict pipeline.

## Quick Start

```bash
opencode --agent swarm "<your task>"
opencode --agent vision "<analyze this image/video>"
opencode --model vision-max "<1M context task>"
```

## Architecture

| Agent | Model | Role |
|-------|-------|------|
| Coordinator | Big Pickle | Triage, orchestration, auto-verdict |
| Worker 1 — Innovator | DeepSeek V4 Flash Free | Strategy, brainstorming, first principles |
| Worker 2 — Critic | Nemotron 3 Nano 30B | Code review, security review, QA |
| Worker 3 — Architect | Nemotron 3 Ultra Free | Implementation, infrastructure, DB |
| Worker 4 — Explorer | MiMo V2.5 Free | Research, web scraping, discovery |
| Worker 5 — Reviewer | Nemotron 3 Super | UX, design, product |
| Worker 6 — Vision-Coder | MiniMax M3 | Vision + code + 1M context |
| Worker 7 — Reasoner | Tencent Hy3 Free | Formal logic, critical thinking |
| Worker 8 — QA | Nemotron 3 Ultra Free | Build, verify, test automation |
| Vision Agent | MiMo V2.5 Free | Multimodal — image, video, audio understanding |
| Vision Agent Max | MiniMax M3 | Multimodal + 1M context + agentic tasks |

## Skills

- **679 core skills** in `~/.config/opencode/skills/`
- **1680+ vault skills** in `~/.config/opencode/skill-libraries/`
- Covers: coding (all languages), cloud, AI/ML, security, design, DevOps, research, game dev, and more

## Strategy Selection

The coordinator triages every task:

1. **Simple** (1-line fix, direct question) → single worker, no swarm  
   Pipeline: LITE (3 stages: Plan → Execute → Verify)

2. **Medium** (2-4 steps, focused domain) → 3-4 workers, divide-conquer  
   Pipeline: STANDARD (4 stages: Plan → Execute → Quality Review → Auto-Verdict)

3. **Complex** (5+ steps, multi-domain) → full 9-worker stepwise-auto with auto-verdict  
   Pipeline: FULL (6 stages: Deep Plan → Decision-Complete Spec → Execute → 12-Step Auto-Verdict → Improve → Handoff)

## Auto-Verdict Pipeline

12-step pipeline: P0 → Tool Planning → Execute → Quality Review → Design Review → Adversarial Review → Domain Check → Multi-Angle Review → MCP Check → Test → Auto-Verdict → Clean Synthesis

## Evaluation

All evaluation docs are **auto-generated** by the swarm itself — not human audits:
- [SWARM-EVALUATION.md](SWARM-EVALUATION.md) — comprehensive 7-dimension scorecard
- [PERFORMANCE-EVALUATION.md](PERFORMANCE-EVALUATION.md) — weighted 5-dimension performance
- [HYBRID-THINK-RESULTS.md](HYBRID-THINK-RESULTS.md) — 20/20 test results
- [HYBRID-THINK-TESTS.md](HYBRID-THINK-TESTS.md) — 20 stress test descriptions

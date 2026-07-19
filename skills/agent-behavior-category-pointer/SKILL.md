---
name: agent-behavior-category-pointer
description: "Pointer to a library of 2 specialized Agent Behavior skills. Use when working on agent-behavior-related tasks."
risk: none
---

# Agent Behavior Capability Library 🎯

This is a **pointer skill**. The 2 specialized Agent Behavior skills are stored in a hidden vault to keep your startup context minimal.

## Available skills in this category

- **codex-fable5** — Apply Fable-inspired discipline to Codex work: inspect first, track goals and findings, ground conclusions in evidence, verify before completion, and adapt Claude/Fable prompt guidance without identity or provider claims.
- **zipai-optimizer** — Ultra-dense token optimizer skill for prompt caching, log pruning, AST-based inspection, and minified JSON payloads.

## How to load a skill

1. Identify the skill name above matching your task.
2. Use `view_file` to read its `SKILL.md` from the vault:
   `/home/kali/.config/opencode/skill-libraries/agent-behavior/<skill-name>/SKILL.md`
3. Follow those instructions to complete the request.

**Vault path:** `/home/kali/.config/opencode/skill-libraries/agent-behavior`

> Do not guess best practices — always read from the vault first.

> ⚠️ **Anti-loop guard**: Do NOT invoke skills recursively or check for applicable skills before every response. Each skill should be loaded at most once per user request. If you have already identified and loaded the relevant skill for this task, proceed with execution — do not re-scan for skills.

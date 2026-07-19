---
name: research-category-pointer
description: "Pointer to a library of 4 specialized Research skills. Use when working on research-related tasks."
risk: none
---

# Research Capability Library 🎯

This is a **pointer skill**. The 4 specialized Research skills are stored in a hidden vault to keep your startup context minimal.

## Available skills in this category

- **ii-commons** — Deterministic search across arXiv, PubMed/PMC, and US policy corpora with daily freshness cutoffs.
- **news-sentiment-engine** — Multi-source RSS news aggregation with Claude-powered sentiment analysis and structured briefing output
- **papers-skill** — Skill for academic research workflows: search Semantic Scholar (200M+ papers), inspect citations, download arXiv PDFs, and extract PDF text. Bundles a self-contained Python CLI.
- **survey-generator** — Generate source-backed AI/ML survey paper artifacts with curated bibliographies and Fireworks/Kimi HTML rendering.

## How to load a skill

1. Identify the skill name above matching your task.
2. Use `view_file` to read its `SKILL.md` from the vault:
   `/home/kali/.config/opencode/skill-libraries/research/<skill-name>/SKILL.md`
3. Follow those instructions to complete the request.

**Vault path:** `/home/kali/.config/opencode/skill-libraries/research`

> Do not guess best practices — always read from the vault first.

> ⚠️ **Anti-loop guard**: Do NOT invoke skills recursively or check for applicable skills before every response. Each skill should be loaded at most once per user request. If you have already identified and loaded the relevant skill for this task, proceed with execution — do not re-scan for skills.

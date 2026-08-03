---
name: creative-category-pointer
description: "Pointer to a library of 1 specialized Creative skills. Use when working on creative-related tasks."
risk: none
---

# Creative Capability Library 🎯

This is a **pointer skill**. The 1 specialized Creative skills are stored in a hidden vault to keep your startup context minimal.

## Available skills in this category

- **article-illustrations** — Generate hand-drawn 16:9 article illustrations with the Grav character IP, sparse annotations, and absurd but clear visual metaphors.

## How to load a skill

1. Identify the skill name above matching your task.
2. Use `view_file` to read its `SKILL.md` from the vault:
   `/home/kali/.config/opencode/skill-libraries/creative/<skill-name>/SKILL.md`
3. Follow those instructions to complete the request.

**Vault path:** `/home/kali/.config/opencode/skill-libraries/creative`

> Do not guess best practices — always read from the vault first.

> ⚠️ **Anti-loop guard**: Do NOT invoke skills recursively or check for applicable skills before every response. Each skill should be loaded at most once per user request. If you have already identified and loaded the relevant skill for this task, proceed with execution — do not re-scan for skills.

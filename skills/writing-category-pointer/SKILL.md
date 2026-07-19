---
name: writing-category-pointer
description: "Pointer to a library of 2 specialized Writing skills. Use when working on writing-related tasks."
risk: none
---

# Writing Capability Library 🎯

This is a **pointer skill**. The 2 specialized Writing skills are stored in a hidden vault to keep your startup context minimal.

## Available skills in this category

- **bulletmind** — Convert input into clean, structured, hierarchical bullet points for summarization, note-taking, and structured thinking.
- **unslop** — Post-process AI-generated text through the unslop CLI to strip AI writing patterns before publishing

## How to load a skill

1. Identify the skill name above matching your task.
2. Use `view_file` to read its `SKILL.md` from the vault:
   `/home/kali/.config/opencode/skill-libraries/writing/<skill-name>/SKILL.md`
3. Follow those instructions to complete the request.

**Vault path:** `/home/kali/.config/opencode/skill-libraries/writing`

> Do not guess best practices — always read from the vault first.

> ⚠️ **Anti-loop guard**: Do NOT invoke skills recursively or check for applicable skills before every response. Each skill should be loaded at most once per user request. If you have already identified and loaded the relevant skill for this task, proceed with execution — do not re-scan for skills.

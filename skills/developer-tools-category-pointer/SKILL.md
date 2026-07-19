---
name: developer-tools-category-pointer
description: "Pointer to a library of 3 specialized Developer Tools skills. Use when working on developer-tools-related tasks."
risk: none
---

# Developer Tools Capability Library 🎯

This is a **pointer skill**. The 3 specialized Developer Tools skills are stored in a hidden vault to keep your startup context minimal.

## Available skills in this category

- **gh-image** — Upload local images to GitHub and get canonical user-attachments embed URLs; use when asked to attach a screenshot to a PR, issue, or comment, or to embed before/after images in a README.
- **mcp-tool-developer** — Build Model Context Protocol (MCP) servers and tools from scratch. Full-stack MCP development with TypeScript/Python, testing, deployment, and registry publishing.
- **tokenwise** — Measurement-driven model router for Claude Code. Routes Haiku/Sonnet/Opus per task class, logs every routed task with real $ numbers, and A/B tests cheaper tiers before you trust the savings.

## How to load a skill

1. Identify the skill name above matching your task.
2. Use `view_file` to read its `SKILL.md` from the vault:
   `/home/kali/.config/opencode/skill-libraries/developer-tools/<skill-name>/SKILL.md`
3. Follow those instructions to complete the request.

**Vault path:** `/home/kali/.config/opencode/skill-libraries/developer-tools`

> Do not guess best practices — always read from the vault first.

> ⚠️ **Anti-loop guard**: Do NOT invoke skills recursively or check for applicable skills before every response. Each skill should be loaded at most once per user request. If you have already identified and loaded the relevant skill for this task, proceed with execution — do not re-scan for skills.

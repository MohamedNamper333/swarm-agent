---
name: productivity-category-pointer
description: "Pointer to a library of 19 specialized Productivity skills. Use when working on productivity-related tasks."
risk: none
---

# Productivity Capability Library 🎯

This is a **pointer skill**. The 19 specialized Productivity skills are stored in a hidden vault to keep your startup context minimal.

## Available skills in this category

- **ask-matt** — Ask which skill or flow fits your situation. A router over the user-invoked skills in this repo.
- **box-automation** — Automate Box operations including file upload/download, content search, folder management, collaboration, metadata queries, and sign requests through Composio's Box toolkit.
- **cal-com-automation** — Automate Cal.com tasks via Rube MCP (Composio): manage bookings, check availability, configure webhooks, and handle teams. Always search tools first for current schemas.
- **calendly-automation** — Automate Calendly scheduling, event management, invitee tracking, availability checks, and organization administration via Rube MCP (Composio). Always search tools first for current schemas.
- **daily-gift** — Relationship-aware daily gift engine with five-stage creative pipeline — editorial judgment, synthesis, concept generation, visual strategy, and rendering in H5, image, or video
- **docusign-automation** — Automate DocuSign tasks via Rube MCP (Composio): templates, envelopes, signatures, document management. Always search tools first for current schemas.
- **dropbox-automation** — Automate Dropbox file management, sharing, search, uploads, downloads, and folder operations via Rube MCP (Composio). Always search tools first for current schemas.
- **faf-wizard** — Done-for-you .faf generator. One-click AI context for any project - new, legacy, or famous. Auto-detects stack, scores readiness, works everywhere.
- **file-organizer** — 6. Reduces Clutter: Identifies old files you probably don't need anymore
- **gmail-automation** — Lightweight Gmail integration with standalone OAuth authentication. No MCP server required.
- **google-calendar-automation** — Lightweight Google Calendar integration with standalone OAuth authentication. No MCP server required.
- **grill-me** — A relentless interview to sharpen a plan or design.
- **grill-with-docs** — A relentless interview to sharpen a plan or design, which also creates docs (ADR's and glossary) as we go.
- **grilling** — Interview the user relentlessly about a plan or design. Use when the user wants to stress-test a plan before building, or uses any 'grill' trigger phrases.
- **handoff** — Compact the current conversation into a handoff document for another agent to pick up.
- **interview-coach** — Full job search coaching system — JD decoding, resume, storybank, mock interviews, transcript analysis, comp negotiation. 23 commands, persistent state.
- **office-productivity** — Office productivity workflow covering document creation, spreadsheet automation, presentation generation, and integration with LibreOffice and Microsoft Office formats.
- **one-drive-automation** — Automate OneDrive file management, search, uploads, downloads, sharing, permissions, and folder operations via Rube MCP (Composio). Always search tools first for current schemas.
- **rich-elicitation** — Asks clarifying questions in multiple rounds before starting ambiguous tasks. Fires when 2+ task dimensions each have 3+ viable answers.

## How to load a skill

1. Identify the skill name above matching your task.
2. Use `view_file` to read its `SKILL.md` from the vault:
   `/home/kali/.config/opencode/skill-libraries/productivity/<skill-name>/SKILL.md`
3. Follow those instructions to complete the request.

**Vault path:** `/home/kali/.config/opencode/skill-libraries/productivity`

> Do not guess best practices — always read from the vault first.

> ⚠️ **Anti-loop guard**: Do NOT invoke skills recursively or check for applicable skills before every response. Each skill should be loaded at most once per user request. If you have already identified and loaded the relevant skill for this task, proceed with execution — do not re-scan for skills.

---
name: media-category-pointer
description: "Pointer to a library of 6 specialized Media skills. Use when working on media-related tasks."
risk: none
---

# Media Capability Library 🎯

This is a **pointer skill**. The 6 specialized Media skills are stored in a hidden vault to keep your startup context minimal.

## Available skills in this category

- **image-generator** — Generate and edit images using Gemini's Nano Banana Pro model (gemini-3-pro-image-preview). Use this skill when the user asks you to generate images, create visuals, edit photos, create logos, generate product mockups, or perform any image generation/editing task.
- **remotion** — Generate walkthrough videos from Stitch projects using Remotion with smooth transitions, zooming, and text overlays
- **remotion-best-practices** — Best practices for Remotion - Video creation in React
- **stability-ai** — Geracao de imagens via Stability AI (SD3.5, Ultra, Core). Text-to-image, img2img, inpainting, upscale, remove-bg, search-replace. 15 estilos artisticos.
- **videodb** — Video and audio perception, indexing, and editing. Ingest files/URLs/live streams, build visual/spoken indexes, search with timestamps, edit timelines, add overlays/subtitles, generate media, and create real-time alerts.
- **videodb-skills** — Upload, stream, search, edit, transcribe, and generate AI video and audio using the VideoDB SDK.

## How to load a skill

1. Identify the skill name above matching your task.
2. Use `view_file` to read its `SKILL.md` from the vault:
   `/home/kali/.config/opencode/skill-libraries/media/<skill-name>/SKILL.md`
3. Follow those instructions to complete the request.

**Vault path:** `/home/kali/.config/opencode/skill-libraries/media`

> Do not guess best practices — always read from the vault first.

> ⚠️ **Anti-loop guard**: Do NOT invoke skills recursively or check for applicable skills before every response. Each skill should be loaded at most once per user request. If you have already identified and loaded the relevant skill for this task, proceed with execution — do not re-scan for skills.

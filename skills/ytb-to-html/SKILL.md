---
name: "ytb-to-html"
description: "Turn one YouTube video URL into a markdown transcript and a self-contained HTML synthesis in the current workspace. Use when the user explicitly wants a standalone HTML brief from a YouTube video rather than a wiki ingest flow."
argument-hint: "<youtube-video-url>"
disable-model-invocation: true
user-invocable: true
---

# YTB To HTML

Create two artifacts from one YouTube video:
- a markdown transcript saved in the current workspace
- a self-contained HTML synthesis saved beside it by default

This is a standalone workflow. Do not route through Agenpedia or other
wiki-specific skills.

## Input contract

- Accept exactly one single-video YouTube URL.
- Reject playlist, channel, profile, or batch inputs unless the user
  explicitly asks for a different workflow.
- If the user does not provide a URL, ask for one.

## Prerequisites

- Require a local `yt2txt.sh` executable on `PATH`, or use the absolute
  path from `YT2TXT_CLI`.
- Require a writable current workspace.

If either prerequisite is missing, stop and tell the user exactly what
is missing.

## Workflow

1. Confirm the input is one YouTube video URL.
2. Resolve this skill's helper at `scripts/fetch_youtube_transcript.py`.
3. Run the helper while keeping the process `cwd` at the user's current
   workspace root so default outputs land in the workspace, not inside
   the skill bundle. Example shape:

   ```bash
   python3 /absolute/path/to/scripts/fetch_youtube_transcript.py "<youtube-url>"
   ```

4. The helper writes a markdown transcript file and prints its path on
   stdout. By default it creates `youtube-<video-id>.md` in the current
   workspace. If the user specified a transcript filename or path,
   forward that to the helper.
5. Verify that the transcript file exists and contains the raw
   transcript. Do not summarize or rewrite the markdown transcript.
6. Create one self-contained HTML file beside the transcript by default,
   using the same basename with an `.html` extension unless the user
   asked for another output path.
7. Before drafting the HTML, choose the figure types you will use.
   Prefer layout-safe HTML or responsive SVG patterns over freehand
   one-off figures. Read [references/figure-recipes.md](references/figure-recipes.md)
   and [references/layout-guardrails.md](references/layout-guardrails.md)
   when the transcript suggests timelines, process loops, comparisons,
   or other dense structured content.

## HTML contract

The HTML artifact is a synthesis, not a faithful transcript renderer.

Keep the HTML:
- self-contained
- locally viewable without a build step
- readable on desktop and mobile
- source-grounded in the transcript
- optimized for fast scanning first

Use inline CSS and only lightweight JavaScript.

Use the same quiet house style as `html-project-brief`:
- restrained Tufte-inspired reading column
- compact metadata
- clear section hierarchy
- limited understanding-oriented interactivity only

If the neighboring `html-project-brief` template assets are available in
the installed bundle, use them as the visual reference. If not, mirror
the same overall tone and layout directly.

Keep exact claims, labels, and structure in HTML, SVG, tables, or prose.
Use generated raster images only when they improve one-glance
comprehension of a concept rather than carrying exact wording.

## Figure rules

Default to `HTML/SVG first` for precise structures such as:
- release timelines
- step flows or loops
- comparisons
- labeled diagrams

Choose a figure pattern before drafting:
- date or version-heavy material: stacked cards, tables, or multi-row
  SVG with wrapped text
- stepwise loops such as `initializer -> featurelist.json ->
  progress.json`: ordered lists, flow cards, or simple block diagrams
  with short labels only
- comparisons or tradeoffs: tables or paired callouts

Avoid brittle figure patterns:
- no single-row SVG timelines with many fixed-position text labels
- no dense unwrapped labels inside SVG when transcript wording length is
  uncertain
- no long pseudo-code blocks when semantic lists or cards would scan
  better

Label rules:
- keep figure labels short
- move detail into captions or adjacent prose
- if one label would exceed one short line, split the figure into rows,
  cards, or table cells instead of compressing it
- use `foreignObject` only when you already know the target environment
  renders it safely; otherwise keep text in pure HTML outside the SVG

## Optional `imagegen` use

Use the `imagegen` skill only when a raster visual materially improves
comprehension. The default image budget is `0-2` visuals per artifact.

Good triggers:
- conceptual mental model of the harness
- operating picture of generator/evaluator roles
- source-grounded support visual beside an exact HTML or SVG flow

Bad triggers:
- exact release timelines
- architecture topology
- exact step sequences
- code annotation
- any figure where wording precision matters

When you use `imagegen`:
- follow the built-in `image_gen` path by default
- keep images text-light and subordinate to the technical explanation
- pair every image with a caption and provenance such as
  `Conceptual visual` or `Source-grounded composite`
- keep labels, arrows, and exact component names in HTML or SVG
- if the image is project-bound, move or copy the final selected image
  from `$CODEX_HOME/generated_images/...` into the workspace before
  embedding or referencing it

For prompts and selection rules, read
[references/imagegen-recipes.md](references/imagegen-recipes.md).

## Default page shape

The HTML should usually include:
- title
- source metadata
- executive summary
- key ideas
- notable moments or themes
- selected excerpts from the transcript
- full transcript appendix

Prefer synthesis over exhaustive commentary in the main body. Keep the
appendix clearly secondary to the summary and thematic sections.

## Failure handling

- If `yt2txt.sh` exits non-zero, surface the error output and stop.
- If the helper cannot find exactly one transcript output, stop.
- If the transcript file is empty, stop.
- If transcription succeeds but the HTML synthesis cannot be completed,
  return the transcript path and say it is ready for manual HTML
  synthesis.

## Prompt-only self-check

Before finishing the HTML artifact, review it for:
- overlapping figure labels
- clipped text or overflow in structured figures
- unreadably dense timelines or diagrams
- generated images that duplicate exact information better expressed in
  HTML or SVG

If a figure fails one of those checks, replace it with a safer pattern
from [references/figure-recipes.md](references/figure-recipes.md)
instead of trying to squeeze more text into the same layout.

## References

Load only what the artifact needs:
- [references/layout-guardrails.md](references/layout-guardrails.md)
- [references/figure-recipes.md](references/figure-recipes.md)
- [references/imagegen-recipes.md](references/imagegen-recipes.md)

## Script

`scripts/fetch_youtube_transcript.py` performs the deterministic
transcription step:
- validates that the URL points to a single video
- runs `yt2txt.sh` non-interactively
- writes a markdown transcript into the current workspace
- prints the created transcript path for the next synthesis step

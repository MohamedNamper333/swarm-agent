---
name: "html-project-brief"
description: "Use when Codex needs to generate a readable, shareable HTML artifact from codebases, markdown docs, technical plans, diffs, research notes, or structured project data so a human can quickly understand what a project does, how it works, what changed, and what to read next."
argument-hint: "[optional brief request]"
disable-model-invocation: true
user-invocable: true
---

# HTML Project Brief

Create a single self-contained HTML artifact that helps a human understand a project quickly and trust what they are seeing.

Treat the output as a living comprehension surface, not as a website, dashboard, or product UI.

## Core contract

Produce one portable HTML file by default.

Keep the artifact:
- self-contained
- locally viewable without a build step
- readable on desktop and mobile
- easy to share
- source-grounded
- optimized for fast scanning first and deeper reading second

Use inline CSS and only lightweight JavaScript.

Prefer HTML and SVG for precise technical explanation. Use raster images only when they materially improve comprehension.

## Start with the dominant mode

Choose one dominant mode before drafting structure:

- `onboarding`
- `architecture`
- `usage`
- `code-explainer`
- `change-brief`
- `research-brief`

Let one mode dominate the page structure even if the artifact includes secondary sections from other modes.

For mode-specific guidance, read [references/artifact-modes.md](references/artifact-modes.md) if it exists.

## Answer the comprehension questions first

Design the page to answer most of these quickly:

- What is this project?
- Why does it exist?
- How is it structured?
- What are the key modules or files?
- How does data or control flow through it?
- How do I run or use it?
- What changed recently?
- What should I read next?
- What is still risky, uncertain, or incomplete?

Do not start by styling. Start by deciding what a human needs to understand.

## Use the default theme

Use the default `Tufte Brief` house style unless the repository already has a strong established visual language that should be preserved.

The default theme is Tufte-inspired, not a strict clone. Favor:
- constrained reading measure
- strong typography
- restrained color
- simple heading hierarchy
- a compact contents rail on the left
- an optional right context rail only when secondary material materially helps
- close integration of prose and figures
- quiet UI controls
- wide figures only when the content needs width

Do not imitate print for its own sake. Adapt the layout to engineering artifacts.

If available, use [assets/tufte-brief.html](assets/tufte-brief.html) as the starting template and [references/theme-guidelines.md](references/theme-guidelines.md) for layout rules.

## Keep interactivity light

Use only understanding-oriented interactivity.

Allowed patterns:
- tabs for alternate views
- collapsible dense sections
- filters by module, layer, or tag
- show or hide annotations
- clickable architecture diagrams
- glossary toggles
- copy buttons for commands, prompts, or snippets
- source and commit metadata reveal
- "read next" helpers

Do not build manipulation-oriented tools here. Do not turn the artifact into an editor, simulator, or workflow app.

If the user actually needs tuning controls, drag-and-drop, form editing, or exportable state manipulation, use a different skill such as `html-playground`.

If available, read [references/interaction-rules.md](references/interaction-rules.md) before adding custom UI behavior.

## Build the right page shape

A strong default page usually includes:

- title
- one-sentence purpose
- quick summary
- project or subsystem map
- key files or modules
- flow diagram
- how to run or use it
- recent changes or current status
- risks or open questions
- suggested next reading

For a `change-brief`, include:
- changed areas
- why the change happened
- impact on behavior
- review hotspots
- unresolved risks

For a `code-explainer`, include:
- one clear system or flow diagram
- 3 to 5 annotated snippets
- glossary or terminology notes
- gotchas or invariants

For a `research-brief`, include:
- findings
- options or hypotheses
- assumptions
- comparison tables
- next validation steps

## Use margin content carefully

Use the left contents rail for navigation only. Put secondary material in an optional right context rail, inline notes, or equivalent collapsible callouts only when it improves understanding.

Good secondary context:
- definitions
- caveats
- provenance
- assumptions
- source notes
- agent notes
- "read this next" references

Do not hide critical content in the side rails.

The contents rail should stay compact and utilitarian. It must not visually compete with the main reading column.

Use a right context rail only when it adds real comprehension value. If it is empty or low-value, collapse that material into inline callouts or omit it.

On small screens, collapse side-rail content into inline callouts or toggles so the artifact remains readable.

## Visualize what benefits from structure

Prefer diagrams, tables, timelines, and maps for:
- architecture
- module relationships
- request or data flows
- before and after comparisons
- commit or release timelines
- research comparisons
- repo maps
- dependency clusters
- review hotspots

Prefer prose for:
- rationale
- tradeoffs
- limitations
- interpretation
- caveats
- next steps

Do not use ASCII diagrams in the final artifact unless the user explicitly wants them. Use SVG or HTML structure instead.

## Keep trust high

Make the artifact trustworthy.

Always:
- date time-sensitive observations
- distinguish confirmed facts from inference
- identify the source of claims when possible
- identify commit, branch, or comparison range when explaining changes
- say when context is partial
- avoid inventing missing architecture details

If the artifact summarizes code changes, prefer grounding claims in the actual diff, files, or repository state rather than in broad prose summaries.

## Use images deliberately

Use `imagegen` only when a raster visual materially improves comprehension.

Good uses:
- educational hero image
- concept illustration
- mental-model visual
- section opener for a long explainer
- memorable visual anchor for onboarding

Do not use raster generation for:
- topology diagrams
- sequence diagrams
- code annotations
- comparison matrices
- precise flows
- anything better expressed in SVG or HTML

Use HTML and SVG for precision. Use `imagegen` for warmth, pedagogy, and memorability.

If available, read [references/imagegen-usage.md](references/imagegen-usage.md) before generating images.

## Follow this workflow

1. Determine the dominant mode.
2. Read only the files and artifacts relevant to that mode.
3. Extract the core comprehension questions.
4. Decide the minimum structure that answers them clearly.
5. Draft the visual hierarchy before writing long prose.
6. Use the default Tufte-inspired theme unless the repo's design language should be preserved.
7. Place figures near the text they explain.
8. Put navigation in the left contents rail, and put secondary material in the optional right context rail, inline notes, or collapsible callouts.
9. Add only the minimum interactivity needed for understanding.
10. Add optional raster visuals only if they teach better than text or SVG alone.
11. Keep the file self-contained.
12. Check desktop and mobile readability.
13. Verify that the artifact is easier to understand than the source material.

## Zero-prompt behavior

Support explicit zero-prompt invocation when the user names only `$html-project-brief` and provides no other task detail.

Treat that invocation as:

- "create or refresh the best default comprehension brief for the current workspace"

This does not replace the normal skill behavior. It adds a default entrypoint for bare invocation only.

### Canonical artifact

Use one canonical filename for zero-prompt operation:

- `project-brief.html`

If the user explicitly asks for another filename or output path, follow the user's instruction instead.

### Bootstrap mode

If `project-brief.html` does not exist, enter bootstrap mode.

In bootstrap mode:
- create the first baseline project brief
- default to an `onboarding`-led structure
- blend in `architecture` and `usage` sections when they are clearly supported by the repo
- include `recent changes` only as a secondary section

Prioritize these questions:
- what is this project
- how is it organized
- how does it work
- how do I use or navigate it
- what should I read next

### Refresh mode

If `project-brief.html` already exists, enter refresh mode.

In refresh mode:
- treat the existing brief as a maintained artifact
- update it rather than replacing it blindly
- preserve stable context that is still accurate
- increase emphasis on changes since the last pass

Prioritize these questions:
- what changed since the previous brief
- which sections are now stale
- which explanations need revision
- which new files, modules, or flows matter
- which new risks or open questions appeared

### Refresh comparison rules

In refresh mode:
- read the existing `project-brief.html`
- compare it with the current repository state
- use code, docs, and current workspace state as the source of truth when they conflict with the existing brief
- carry forward useful framing, structure, and unresolved questions when they still apply

Use a small high-signal source set first:
- top-level docs
- repo structure
- main entrypoints
- key config or package files
- modified and untracked files
- the existing `project-brief.html`

### Output expectations for zero-prompt mode

For zero-prompt invocation:
- produce exactly one self-contained HTML artifact by default
- keep the first pass compact and high-signal
- include a short "recent changes" section even in bootstrap mode if active local work is present
- include update metadata in refresh mode when helpful, such as last updated time or refreshed sections

If the repo is very small, ambiguous, or documentation-first, produce a minimal but useful brief rather than asking for clarification unless a real blocker exists.

## Prefer clarity over coverage

Do not try to mirror every source file or every section of a long document.

Compress aggressively:
- group related files by responsibility
- summarize repetitive patterns
- quote only short, high-value excerpts
- annotate only the most important snippets
- link ideas together visually instead of repeating them in prose

The goal is not completeness. The goal is transfer of understanding.

## Respect existing project style when needed

If the repository already has a strong design system, visual language, or documentation convention, preserve it.

Use the Tufte-inspired default only when there is no stronger local precedent or when the user asks for that style directly.

## Use bundled references progressively

Read bundled reference files only when needed.

Recommended references:
- [references/artifact-modes.md](references/artifact-modes.md)
- [references/theme-guidelines.md](references/theme-guidelines.md)
- [references/interaction-rules.md](references/interaction-rules.md)
- [references/imagegen-usage.md](references/imagegen-usage.md)

Do not load all references by default.

## Aim for this standard

A good artifact produced with this skill should:
- be easier to read than the source material
- help a human understand the project quickly
- reduce comprehension debt after agent work
- stay grounded in source reality
- feel visually intentional without becoming decorative
- remain useful when refreshed later

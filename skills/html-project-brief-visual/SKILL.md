---
name: "html-project-brief-visual"
description: "Create or refresh a visual-first self-contained HTML project brief with generated imagery, editorial storytelling, and precise HTML or SVG overlays. Use when the user wants an onboarding or architecture brief that should feel more image-led than the standard html-project-brief."
argument-hint: "[optional brief request]"
disable-model-invocation: true
user-invocable: true
---

# HTML Project Brief Visual

Create a single self-contained HTML artifact that helps a human understand a project quickly through visual storytelling.

Treat the output as a living comprehension surface, not as a website, dashboard, or product UI.

This skill is the visual-first sibling of `html-project-brief`. It should coexist with the standard brief, not overwrite it by default.

## Core contract

Produce one portable HTML file by default.

Keep the artifact:
- self-contained
- locally viewable without a build step
- readable on desktop and mobile
- source-grounded
- optimized for fast scanning first and deeper reading second
- more visual than the standard brief without becoming decorative

Use inline CSS and only lightweight JavaScript.

Embed the final selected images directly into the HTML artifact so the default output remains a single file.

## Start with the dominant mode

Choose one dominant mode before drafting structure:

- `onboarding`
- `architecture`
- `usage`
- `code-explainer`
- `change-brief`
- `research-brief`

This skill is optimized first for `onboarding` and `architecture`.

Support the other modes, but use a lighter visual budget for them unless the user explicitly asks for a richer treatment.

Read [references/mode-recipes.md](references/mode-recipes.md) when the mode choice materially affects the page shape.

## Answer the comprehension questions first

Design the page to answer most of these quickly:

- What is this project?
- Why does it exist?
- How is it structured?
- How does data or control move through it?
- What are the key modules or files?
- How do I run or use it?
- What changed recently?
- What should I read next?
- What is still risky or uncertain?

Do not start by styling. Start by deciding what a human needs to understand and which visuals will teach that fastest.

## Visual-first default

Generated imagery is expected in this skill, but within a disciplined budget.

Default image budget for a normal zero-prompt brief:
- 1 cover or hero image for project purpose
- 1 system mental-model illustration near the overview
- 1 architecture or key-flow visual near the main technical explanation
- 1 optional fourth visual for usage, risks, or read-next when the repo supports it

For non-primary modes, use 1 to 2 visuals unless the user asks for a richer brief.

Prefer fewer strong visuals over many weak ones.

Read [references/visual-guidelines.md](references/visual-guidelines.md) before finalizing layout or captions.

## Keep trust high

Make the artifact trustworthy.

Always:
- date time-sensitive observations
- distinguish confirmed facts from inference
- identify the source of claims when possible
- say when context is partial
- keep technical labels and exact callouts in HTML or SVG
- pair every generated image with a caption and provenance note

Use provenance language such as:
- `Conceptual visual` for a mental-model scene
- `Source-grounded composite` for a visual derived from repo facts
- `Interpretive summary` for a scene that synthesizes multiple facts

Do not let a generated image imply precision it does not have.

## Use images and diagrams for different jobs

Use generated raster visuals for:
- project purpose and atmosphere
- mental-model scenes
- memorable onboarding anchors
- section openers for long explainers
- architecture mood boards that help a reader form the right mental picture

Use HTML and SVG for:
- topology diagrams
- sequence diagrams
- exact request or data flows
- code annotation
- tables
- legends
- comparison matrices
- any precise labels or callouts

Generated images should usually be text-free. Keep labels, legends, arrows, and technical naming outside the image in the artifact.

## Use `imagegen` deliberately

Use the `imagegen` skill for raster generation when it is available.

Image generation policy:
- use the built-in `image_gen` path by default
- do not switch to CLI fallback unless the user explicitly asks for it or the `imagegen` skill requires explicit confirmation for a fallback path
- keep prompts educational, editorial, and label-friendly
- avoid embedded text unless a small amount of high-level display text is truly necessary

Read [references/prompt-recipes.md](references/prompt-recipes.md) before drafting prompts.

When prompting visuals for this skill, bias toward:
- editorial explainer composition
- restrained palette
- clean negative space for HTML overlays
- calm, credible mood
- visual specificity that matches known repo facts

Avoid:
- cinematic spectacle for its own sake
- generic dashboard art
- decorative collage clutter
- images that try to encode exact architecture without HTML or SVG help

## Build the right page shape

A strong default page usually includes:

- title
- one-sentence purpose
- short summary deck
- hero visual with provenance
- overview and project map
- system mental-model figure
- key files or modules
- architecture or flow section with HTML or SVG overlays
- how to run or use it
- risks or open questions
- suggested next reading

Desktop body composition should default to:
- a compact contents gutter on the left
- a centered reading column in the middle
- a reserved right-side context gutter for sources, read-next, or secondary context

The hero can remain more editorial and asymmetrical than the body. Do not let hero composition dictate the centering of the main reading column.

Keep interactivity light.

Allowed patterns:
- tabs for alternate views
- collapsible dense sections
- glossary toggles
- copy buttons for commands or snippets
- reveal panels for metadata, sources, or commit context

Do not turn the brief into an editor, simulator, or workflow app.

## Default template

Use the editorial visual template in [assets/editorial-visual-brief.html](assets/editorial-visual-brief.html) unless the repository already has a stronger visual language that should be preserved.

The default visual language should feel:
- editorial
- image-led
- restrained rather than flashy
- readable on mobile
- precise where it needs to be

The default body layout should feel centered and balanced:
- `On This Page` lives on the left on desktop
- the reading column stays centered even if right-side context is sparse
- the right gutter stays visually discreet when lightly populated

Do not fall back to the standard Tufte template unless the user explicitly wants the standard brief instead.

## Follow this workflow

1. Determine the dominant mode.
2. Read only the files and artifacts relevant to that mode.
3. Identify the core comprehension questions.
4. Choose the minimum source set that can answer those questions credibly.
5. Decide the story arc before styling: title, summary, system picture, proof, usage, risks, read next.
6. Plan the visual budget. Default to 3 anchors, add the fourth only when it teaches something distinct.
7. Generate the raster visuals with `imagegen`.
8. Build the precise diagrams, labels, legends, and annotations in HTML or SVG.
9. Embed the final selected images directly into the HTML artifact.
10. Caption every visual with what it shows, why it exists, and how grounded it is.
11. Keep the file self-contained.
12. Check desktop and mobile readability, confirming that the body copy remains centered independently of side content density.
13. Verify that the artifact is easier to understand than the source material.

## Zero-prompt behavior

Support explicit zero-prompt invocation when the user names only `$html-project-brief-visual` and provides no other task detail.

Treat that invocation as:

- "create or refresh the best default visual project brief for the current workspace"

### Canonical artifact

Use one canonical filename for zero-prompt operation:

- `project-brief-visual.html`

If the user explicitly asks for another filename or output path, follow the user's instruction instead.

### Bootstrap mode

If `project-brief-visual.html` does not exist, enter bootstrap mode.

In bootstrap mode:
- create the first baseline visual brief
- default to an `onboarding`-led structure
- blend in `architecture` and `usage` sections when the repo supports them
- include `recent changes` only as a secondary section
- use the default 3-image set unless a fourth image clearly helps

Prioritize these questions:
- what is this project
- why does it exist
- how is it organized
- how does it work
- how do I use or navigate it
- what should I read next

### Refresh mode

If `project-brief-visual.html` already exists, enter refresh mode.

In refresh mode:
- treat the existing visual brief as a maintained artifact
- update it rather than replacing it blindly
- preserve still-accurate framing and selected visuals when they remain useful
- replace or revise visuals when the underlying explanation or emphasis has changed
- increase emphasis on changes since the last pass

In refresh mode, read:
- the existing `project-brief-visual.html`
- the current repo structure
- the main entrypoints
- key configs or package files
- modified and untracked files when relevant

Use current code and docs as the source of truth when they conflict with the existing brief.

## Mode-specific defaults

For `onboarding`:
- use the full default visual budget
- make the hero image and mental-model figure do real teaching work
- keep the architecture section approachable and label-rich

For `architecture`:
- bias the main visual toward subsystem boundaries or control flow
- keep the hero more restrained
- let HTML or SVG carry exact boundaries, invariants, and interfaces

For `usage`, `code-explainer`, `change-brief`, and `research-brief`:
- reduce the image count unless the user asks for a richer narrative
- prioritize a smaller number of high-signal visuals and stronger source grounding

## Prefer clarity over coverage

Do not mirror every source file or every section of a long document.

Compress aggressively:
- group related files by responsibility
- summarize repetitive patterns
- caption only the visuals that genuinely teach
- keep overlays short and legible
- use figures to clarify rather than to decorate

The goal is not completeness. The goal is transfer of understanding.

## Use bundled references progressively

Read bundled reference files only when needed.

Recommended references:
- [references/visual-guidelines.md](references/visual-guidelines.md)
- [references/mode-recipes.md](references/mode-recipes.md)
- [references/prompt-recipes.md](references/prompt-recipes.md)

Do not load every reference by default.

## Aim for this standard

A good artifact produced with this skill should:
- be easier to read than the source material
- feel more vivid than the standard brief without losing trust
- make onboarding faster
- give architecture enough visual shape to be memorable
- keep precise explanation in HTML and SVG rather than in generated text inside images
- keep the main reading column visually centered on desktop even when the right gutter is sparse
- remain useful when refreshed later

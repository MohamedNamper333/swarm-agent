---
name: "markdown-to-tufte-html"
description: "Render markdown into a self-contained HTML document using the same Tufte house style as `html-project-brief`. Use when the goal is to preserve the full content and structure of a markdown file or pasted markdown while improving typography, navigation, and HTML-native presentation without summarizing or rewriting."
argument-hint: "<markdown file path or pasted markdown>"
disable-model-invocation: false
user-invocable: true
---

# Markdown To Tufte HTML

Render one markdown source into one self-contained HTML document using the same Tufte house style as `html-project-brief`, while borrowing the core structural patterns of Tufte CSS.

This skill is a renderer, not a brief.

Do not compress, summarize, or editorialize the source. Preserve the document's full information content and structure, then use HTML where it improves presentation without changing meaning.

## Core contract

Produce exactly one portable HTML file by default.

Keep the output:
- self-contained
- locally viewable without a build step
- readable on desktop and mobile
- faithful to the markdown source
- visually intentional but quiet

Use inline CSS and only lightweight JavaScript.

## Input contract

Accept either:
- a markdown file path
- pasted markdown text

If the user does not provide a source, ask for a markdown file path or pasted markdown. Do not guess a source document.

## Output contract

Produce exactly one HTML file by default.

Default output path:
- markdown file input: write a sibling `.html` file with the same basename
- pasted markdown input: write `markdown-render.html` in the current workspace unless the user specifies a different path

Title resolution order:
1. frontmatter `title`
2. first H1 in the markdown
3. source filename stem
4. `Rendered Markdown`

Use frontmatter metadata such as `subtitle`, `author`, `date`, and similar document metadata in the header or meta row when present. Do not dump raw YAML frontmatter into the body.

Structure the output with one top-level `article` element. Inside the main reading flow, group content into `section` blocks where the source structure clearly supports that grouping.

## Use the bundled template

Start from [assets/tufte-markdown.html](assets/tufte-markdown.html).

Treat [../html-project-brief/assets/tufte-brief.html](../html-project-brief/assets/tufte-brief.html) as the canonical house-style reference for shared visual rules.
Treat the Tufte CSS reference as the canonical source for note mechanics and article semantics.

The template is intentionally generic. Populate or remove these placeholders cleanly:
- `{{TITLE}}`
- `{{SUBTITLE_BLOCK}}`
- `{{META_BLOCK}}`
- `{{TOC_BLOCK}}`
- `{{BODY_HTML}}`

Do not leave empty wrappers or unresolved placeholder text in the final output.
Do not create a separate notes rail; Tufte notes belong inside `{{BODY_HTML}}` as `sidenote` or `marginnote` markup.

Recommended block shapes:
- `{{SUBTITLE_BLOCK}}` -> `<p class="subtitle">...</p>`
- `{{META_BLOCK}}` -> `<p class="meta">...</p>`
- `{{TOC_BLOCK}}` -> `<section><strong>Contents</strong><nav>...</nav></section>`

If the TOC is empty, remove its visible inner wrapper and leave the structural left gutter quiet rather than inventing a replacement block.

When adding renderer-specific wrappers such as table overflow containers, code block wrappers, or note containers, inherit the brief template's spacing, gutter treatment, and quiet control styling before introducing new visual behavior.

Supported source-side utility vocabulary:
- `span.newthought`
- `span.sans` or `p.sans`
- `div.epigraph > blockquote > footer`
- `figure.fullwidth`
- `figure.iframe-wrapper`
- `label.margin-toggle` + `input.margin-toggle` + `span.marginnote`
- `label.margin-toggle.sidenote-number` + `input.margin-toggle` + `span.sidenote`

## Fidelity rules

Preserve the source document's:
- heading hierarchy
- prose
- lists
- tables
- fenced and indented code blocks
- links
- images
- blockquotes
- footnotes
- raw HTML blocks

Preserve supported Tufte-style raw HTML structures when they appear in the source. Do not flatten or normalize them away.

Do not:
- summarize
- condense
- rewrite for brevity
- invent content
- add interpretation that is not already present in the markdown

If the markdown includes raw HTML, preserve it unless a small structural wrapper is needed to keep the layout readable.

Keep document order intact. Do not reorder sections unless the source itself demands it.

## Use HTML advantages only when semantically faithful

Allowed upgrades:
- a table of contents generated from headings
- markdown footnotes converted into Tufte-style inline sidenotes
- explicit source-signaled margin notes rendered with Tufte-style margin-note markup
- wide wrappers for large tables, figures, or diagrams
- `fullwidth` and `iframe-wrapper` treatment for supported media blocks
- epigraph styling for `blockquote` plus `footer`
- `newthought` and `sans` utility styling when those classes appear in the source
- figure and figcaption treatment for images that already have caption-like context
- code block wrappers with quiet copy buttons
- metadata rows for frontmatter fields
- mobile-friendly CSS-only note toggles

Only create callouts, sidenotes, or note treatments when the source already signals them through:
- footnotes
- blockquotes
- callout syntax
- explicit note markers
- supported Tufte-style raw HTML
- existing structural separation

Do not add interpretive annotations on your own initiative.
Do not invent margin notes.

## Interactivity rules

Keep interactivity minimal and secondary.

Allowed:
- sticky table of contents
- copy buttons for code blocks
- CSS-only note toggles for sidenotes and margin notes on small screens

Disallowed unless the source document explicitly requires them:
- tabs
- dashboards
- editing controls
- simulations
- app-like workflows
- product-style UI chrome

The page must remain understandable with all controls untouched.
Core note behavior must not depend on JavaScript. JavaScript may only enhance non-essential controls such as copy buttons or TOC wrapper cleanup.

## Visual rules

Use the `html-project-brief` house style from the template:
- serif main reading column
- restrained sans-serif for controls and metadata
- off-white background
- near-black text
- narrow reading measure
- quiet borders and muted accents
- a left TOC gutter and a right note gutter around a reading column centered by the viewport

Preserve shared house primitives wherever possible:
- `--main: 38rem`
- balanced side gutters around the reading column on desktop
- a fluid full-width grid rather than a capped page block on large screens
- `line-height: 1.55`
- the brief template's heading rhythm
- the brief template's nav styling and quiet gutter treatment
- the brief template's code, table, figcaption, and callout treatment

Desktop composition rules:
- the reading column is the visual center of the page
- the TOC belongs in a true left gutter, not tucked against the prose column
- the right gutter may be visually quiet when it has no visible note content, but it must not change the centering of `main`
- the header title, subtitle, and metadata align to the same reading column as the body

Do not add bright hero treatments, decorative gradients, or card-grid dashboard patterns.
Do not invent alternate typography, spacing, or control systems when the brief template already provides a suitable primitive.

Intentional divergences from canonical Tufte CSS:
- preserve the warm sepia/chocolate palette instead of the neutral default
- keep the local serif and sans fallback stacks instead of vendoring ET Book and Gill Sans
- keep the TOC rail as a repo-specific extension on the left while reserving the right gutter for Tufte notes

## Rendering workflow

1. Load the markdown source and detect frontmatter if present.
2. Resolve the title, subtitle, and metadata row.
3. Render the markdown into semantic HTML without dropping content.
4. Wrap logical heading groups in `section` blocks where the source structure clearly supports it.
5. Convert markdown footnotes into adjacent Tufte-style sidenote markup.
6. Preserve explicit source-signaled margin notes and supported Tufte utility classes.
7. Build a table of contents from meaningful headings.
8. Wrap wide tables, figures, iframe media, and code blocks only when needed for readability.
9. Populate the template so the TOC lives in the left gutter and all notes stay inside `{{BODY_HTML}}`.
10. Verify the output is self-contained and preserves the source's information content.

## Acceptance standard

A good result produced with this skill should:
- feel like a full rendering, not a brief
- preserve the original document's content and structure
- be easier to read than the raw markdown
- take advantage of HTML where markdown is visually limited
- read as the same house theme as `html-project-brief`
- behave like a hybrid Tufte CSS article, especially for notes and section structure
- keep the reading column centered even when TOC density or note density changes
- avoid large dead space to the left of the TOC on wide desktop viewports
- remain faithful enough that a reader can trust nothing important was omitted

---
name: "txt-to-html-srs"
description: "Turn a markdown file or pasted source text into a self-contained HTML study sheet with summary, key concepts, flashcards, and lightweight spaced repetition. Optionally publish the generated sheet into a compatible private study hub repo clone."
argument-hint: "<markdown path or pasted text>"
disable-model-invocation: false
user-invocable: true
---

# Txt To HTML SRS

Transform one source document into one self-contained HTML learning sheet that is easy to read, easy to reuse, and easy to publish.

This skill is not a faithful renderer like `markdown-to-tufte-html`.

Its job is to keep the source's intellectual structure while reframing it into a study-first artifact.

## Core contract

Produce exactly one portable HTML file by default.

Keep the output:
- self-contained
- locally viewable without a build step
- readable on desktop and mobile
- pedagogically selective
- visually aligned with the Tufte-inspired house style used in `markdown-to-tufte-html`
- usable without JavaScript, with JavaScript only enhancing review behavior

Use inline CSS and only lightweight JavaScript.

## Inputs

Accept either:
- a markdown file path
- pasted source text

Default input assumption:
- markdown if the user provides a path
- prose notes or pedagogical source text if the user pastes content

If the user provides neither, ask for a markdown file path or pasted text.

## Outputs

Produce exactly one HTML file by default.

Default output path:
- markdown file input: write a sibling `-study.html` file
- pasted text input: write `study-sheet.html` in the current workspace unless the user specifies otherwise

Title resolution order:
1. frontmatter `title`
2. first H1
3. filename stem
4. `Study Sheet`

## Start from the bundled template

Use [assets/study-sheet.html](assets/study-sheet.html) as the rendering base.

Treat [../markdown-to-tufte-html/assets/tufte-markdown.html](../markdown-to-tufte-html/assets/tufte-markdown.html) as the canonical house-style reference for palette, reading measure, rail behavior, and typography.

The template exposes these placeholders:
- `{{TITLE}}`
- `{{SUBTITLE_BLOCK}}`
- `{{META_BLOCK}}`
- `{{TOC_BLOCK}}`
- `{{RAIL_STATUS_BLOCK}}`
- `{{SUMMARY_BLOCK}}`
- `{{CONCEPTS_BLOCK}}`
- `{{FLASHCARDS_BLOCK}}`
- `{{REVIEW_BLOCK}}`
- `{{SOURCE_MAP_BLOCK}}`
- `{{STUDY_DATA_JSON}}`

Do not leave unresolved placeholders in the final file.

## Pedagogical contract

The output is hybrid, not exhaustive.

Keep:
- the source's main thesis
- key distinctions
- steps or procedures
- definitions
- formulas, frameworks, or named concepts
- memorable pitfalls and confusions

Compress or omit:
- redundant examples
- ornamental prose
- low-signal repetition
- digressions that do not improve recall

Do not invent content that is absent from the source.

If the source is ambiguous, preserve uncertainty rather than pretending clarity.

## Canonical page shape

The main reading flow should follow this order:
1. summary
2. key concepts
3. flashcards
4. review
5. source map

Recommended block shapes:
- `{{SUBTITLE_BLOCK}}` -> `<p class="subtitle">...</p>`
- `{{META_BLOCK}}` -> `<p class="meta">...</p>`
- `{{TOC_BLOCK}}` -> `<section><strong>Contents</strong><nav>...</nav></section>`
- `{{RAIL_STATUS_BLOCK}}` -> a compact review-status block with `data-review-count`, `data-due-count`, and `data-next-review`
- `{{SUMMARY_BLOCK}}` -> `<section id="summary">...</section>`
- `{{CONCEPTS_BLOCK}}` -> `<section id="concepts">...</section>`
- `{{FLASHCARDS_BLOCK}}` -> `<section id="flashcards">...</section>`
- `{{REVIEW_BLOCK}}` -> `<section id="review">...</section>`
- `{{SOURCE_MAP_BLOCK}}` -> `<section id="source-map">...</section>`

## Summary rules

The summary should be concise and retrieval-friendly.

Target:
- one framing paragraph
- one short list of what matters most
- optional `why this matters` callout if the source naturally supports it

Do not turn the summary into a full article recap.

## Key concept rules

Represent core ideas as a short concept inventory.

Good concept entries include:
- term or idea name
- one-sentence definition
- one discriminating note such as `not to be confused with`, `watch for`, or `used when`

Prefer 4 to 10 concepts.

## Flashcard rules

Flashcards are selective by default.

Default density:
- short source: 6 to 12 cards
- medium source: 10 to 18 cards
- long source: cap around 24 unless the user explicitly wants a dense deck

Good card types:
- definition
- distinction
- causal relationship
- sequence or procedure
- trap or misconception
- recall prompt for a key principle

Avoid:
- trivial cards
- cloze spam
- cards that merely restate headings
- cards whose answer is too long to recall efficiently

Readable card markup should stay visible without JS. Prefer `details` or compact reveal blocks.

## Review rules

The page should embed a lightweight local SRS layer.

Use the JavaScript already present in the template and feed it through `{{STUDY_DATA_JSON}}`.

Default interval ladder:
- `0`
- `1`
- `3`
- `7`
- `14`
- `30`

Use three actions:
- `Again`
- `Good`
- `Easy`

Semantics:
- `Again` resets to the first level
- `Good` advances one level
- `Easy` advances two levels

Persistence:
- use `localStorage`
- scope progress to a per-document storage key
- include a visible reset action

The review section must remain understandable even if JavaScript is unavailable.

## Study data payload

Populate `{{STUDY_DATA_JSON}}` with a compact JSON object that the template can read.

Recommended shape:

```json
{
  "document": {
    "title": "Retrieval Practice",
    "summary": "Active recall strengthens durable learning.",
    "tags": ["learning", "memory"],
    "source_kind": "markdown",
    "slug": "retrieval-practice"
  },
  "flashcards": [
    {
      "id": "card-1",
      "front": "What is retrieval practice?",
      "back": "Deliberate recall from memory without looking."
    }
  ]
}
```

Keep the JSON minimal. It exists to support review logic and publishing metadata, not to mirror the whole source.

## Publish-to-hub mode

Only enter publish mode when the user explicitly asks to publish to a study hub.

When publishing:
1. Generate or locate the final HTML sheet.
2. Require a path to a local clone of the target hub repo.
3. Use [scripts/publish_to_hub.py](scripts/publish_to_hub.py) instead of manually editing `catalog.json` or `index.html`.
4. Pass `--commit` only if the user wants a local commit.
5. Pass `--push` only if the user explicitly wants a remote push.

The target repo must contain:
- `.study-hub.json`
- `library/catalog.json`
- `index.html`

If the repo is not compatible, stop and explain why.

For repo bootstrap, conventions, and GitHub guidance, read [references/publishing.md](references/publishing.md).

## Hub template

The canonical seed for the external hub repo lives in [assets/study-hub-template](assets/study-hub-template).

Treat it as:
- a local bootstrap source
- a contract for what `publish_to_hub.py` expects
- the basis for a separate GitHub template repository

Do not treat that asset directory as the user's live library unless they explicitly choose to work there.

## Workflow

1. Load the source text.
2. Resolve title and metadata.
3. Extract the few concepts worth remembering.
4. Draft a compact summary.
5. Generate a selective flashcard deck.
6. Populate the template placeholders.
7. Embed `study-sheet-data` JSON.
8. Verify the page still reads well with scripts ignored.
9. If publish mode was requested, run `publish_to_hub.py` against the hub clone.

## Acceptance standard

A good result produced with this skill should:
- feel like a study sheet, not a raw render
- preserve the source's high-value intellectual content
- surface a small set of memorable concepts
- produce flashcards that are worth reviewing
- support lightweight SRS without becoming a product UI
- stay visually aligned with the repo's Tufte house style
- remain shareable as a single HTML artifact
- optionally slot cleanly into a compatible hub repo

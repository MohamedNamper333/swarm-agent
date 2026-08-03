---
name: "ingest"
description: "Ingest source material into an Agenpedia wiki. Use when the user wants raw files, URLs, pasted text, or researched topics turned into wiki pages, not when they only need answers from the existing wiki."
argument-hint: "<source: file path in raw/, URL, pasted text, or topic to search>"
disable-model-invocation: false
user-invocable: true
---

# Wiki Ingest

Ingest one or more sources into the wiki. Use deep reasoning (enable extended thinking if your harness supports it) for deep
analysis throughout this workflow.

## Context

Read `AGENTS.md` at the project root for wiki conventions, page types,
frontmatter schema, naming conventions, cross-reference rules, index
format, and log format. All operations below must conform to those rules.

## Step 1: Source Acquisition

Determine the source type from the argument:

- **File path(s) in `raw/`**: Read the file(s) directly. If multiple
  paths are given, this is a MERGE co-ingest — produce a single wiki
  page from all sources combined.
- **URL**: Fetch the URL content using the configured `web-fetch` tool (see AGENTS.md → Configured Tools). Save the fetched
  content as a `.md` file in `raw/` with a descriptive filename. Then
  proceed with that file.
- **Pasted text** (no file path, no URL): Save the text as a `.md`
  file in `raw/` with a descriptive filename derived from the content.
  Then proceed with that file.
- **Topic** (a subject to research): Perform a web search using the configured `web-search` tool (see AGENTS.md → Configured Tools).
  Save the search results as a `.md` file in `raw/`. Then proceed with
  that file.

## Step 2: Read Source Completely

Read the full text of the source file(s). If the source contains or
references images, view them separately via vision for additional
context. Download any referenced images locally to `raw/assets/` — do
not rely on external URLs that may break.

## Step 2b: Assess Source Density and Compression Strategy

Decide how aggressively to compress before drafting the main page.
Check whether the source shows:

- low repetition
- a high ratio of mechanisms, arguments, or frameworks to filler
- many reusable lists, checklists, matrices, or distinctions
- examples that explain mechanism rather than merely illustrate it
- section structure that is already operationally useful

If `3+` triggers are present, classify the source as
`low-noise, high-structure` and use a `high-fidelity synthesis`.
Preserve nearly all major sections, frameworks, checklists, matrices,
distinctions, and materially different examples. Compress wording,
repeated phrasing, and decorative transitions rather than cutting
substance. Do not turn a structured memo into a thin executive summary.
Do not choose page length by matching prior wiki averages or by
assuming `synthesis` implies short.

If fewer than `3` triggers are present, use normal compression
judgment. Stronger compression is acceptable for noisy or repetitive
sources, but keep argument structure, mechanisms, useful distinctions,
and reusable takeaways. Remove repetition, filler, and weak examples
more aggressively than you would for a dense source.

## Step 3: Auto-Classify

Read the source and decide what wiki pages to produce. No user
question needed — classify based on content:

- **Main page type**: Choose the best fit:
  - `synthesis` — Source presents arguments, theses, reflections, or
    connects ideas. This is the default for most sources. Ranges from
    single-source distillation to multi-source thematic analysis.
  - `concept` — Source centers on explaining a single idea, technique,
    or principle. Best when the content reads as a reference/definition
    rather than an argument.
  - `entity` — Source is primarily about a person, org, or tool
    (rare as a main page from ingest).

- **Secondary pages**: Regardless of the main page type, also identify
  entity and concept pages to create or update (detailed in Step 6).

Proceed directly to Step 4.

## Step 4: Confront Existing Wiki

Read `wiki/index.md` and relevant existing wiki pages. Compare the new
source against existing knowledge. For each key claim or idea in the
source, classify it as:

- **STRENGTHENS**: Supports or extends an existing wiki page's content
- **CONTRADICTS**: Conflicts with an existing wiki page's claim
- **NOVEL**: New information not covered by any existing page

**Link threshold**: Only classify as STRENGTHENS or CONTRADICTS when
there is a substantive intellectual connection — shared theoretical
lineage, direct influence, or genuine engagement with the same ideas.
Superficial word overlap (e.g., both use "entropy" but one means
thermodynamic entropy and the other means code drift) or loose
analogies do not qualify. When in doubt, classify as NOVEL.

Present the confrontation report to the user.

## Step 5: Verify (Open-Loop)

Perform web searches to:

1. Find counter-arguments to the source's key claims
2. Fact-check specific claims (dates, statistics, attributions)
3. Find alternative frameworks or perspectives

Classify each claim as:
- **Verified**: Corroborated by independent sources
- **Contested**: Counter-arguments exist from credible sources
- **Unverified**: Cannot confirm or deny
- **Incorrect**: Contradicted by reliable evidence

**Important**: Flag incorrect claims for the user's decision. Never
auto-exclude any claim — the user decides what to keep.

Present the verification report to the user.

## Step 5b: Popper Filter

For each entity and key claim that would enter the wiki, evaluate:

1. **Falsifiability** — Can the claim be empirically tested or refuted?
2. **Evidence base** — Is there peer-reviewed or independently replicated
   support?
3. **Consensus status** — Is it accepted, debated, or rejected by the
   relevant field?

Assign a verdict to each:

- **INCLUDE** — Falsifiable, evidenced, accepted or legitimately debated
- **CAVEAT** — Legitimate minority position within the field (e.g., a
  respected physicist's alternative interpretation). Include with
  epistemic status noted in the wiki page.
- **EXCLUDE** — Unfalsifiable, no empirical evidence, or rejected by
  scientific consensus. Do not create wiki pages for excluded entities
  or concepts. Document what was excluded and why in a "Filtered Claims"
  section of the main page.

Default to conservative: when in doubt, CAVEAT over INCLUDE, EXCLUDE
over CAVEAT. Present the filter results alongside the verification
report.

## Step 6: Discuss and Approve

Present to the user:
1. The confrontation report (Step 4)
2. The verification report (Step 5)
3. The intended fidelity mode for the main page:
   - `high-fidelity synthesis` for a `low-noise, high-structure`
     source
   - `standard compression` for a noisier source
   Include a one-line reason based on the Step 2b triggers so the user
   can correct the compression strategy before writing begins.
4. Proposed wiki pages to create/update:
   - The main page (synthesis, concept, or entity per Step 3)
   - Entity pages for people, orgs, tools mentioned or clearly implied.
     **Notability filter**: only propose entity pages for well-known
     figures, organizations, or tools — people with significant public
     presence, multiple notable works, or established influence in their
     field. Do not create entity pages for authors known only for a
     single article or obscure contributors. Mention them by name in
     the main page text instead.
     Act as a librarian: identify likely intellectual influences,
     established frameworks, and thinkers behind the ideas, even when
     the author doesn't cite them. Also propose counterpoint entities —
     when the source takes a strong position, identify the most credible
     opposing thinker.
   - Concept pages for ideas, techniques, principles mentioned or
     implied. When the source uses ideas that map to established concepts
     under different names, propose linking to the established concept
     and noting the author's framing as a variant.
5. Proposed updates to existing pages (if any CONTRADICTS or STRENGTHENS
   findings apply). Contestation updates to existing pages require
   explicit approval — call them out separately.

**Wait for the user's approval before proceeding.** The user may modify
the plan — accept their changes.

## Step 7: Create/Update Wiki Pages

Based on the approved plan:

1. **Main page**: Create the main page in `wiki/` with full frontmatter
   (`type`, `date`, `sources`, `aliases`, `tags`). The type is determined
   by Step 3's auto-classification. Write the page in English and apply
   the Step 2b compression mode. For a `low-noise, high-structure`
   source, produce a `high-fidelity synthesis`: preserve nearly all
   major sections, frameworks, checklists, matrices, distinctions, and
   materially different examples, then compress wording and repetition
   without stripping business substance. For noisier sources, stronger
   compression is acceptable if the page still preserves the source's
   argument structure, mechanisms, and reusable takeaways. Repo-local
   instructions still win when they explicitly require a shorter or
   differently shaped output. If any claims or entities were EXCLUDED by
   the Popper filter, add a `## Filtered Claims` section at the end of
   the page body (before Links) documenting what was excluded and why.
2. **Entity pages**: Create or update entity pages (`type: entity`) for
   each approved entity. Include a description, context, and wikilinks.
3. **Concept pages**: Create or update concept pages (`type: concept`)
   for each approved concept. Include explanation and wikilinks.
4. **Bidirectional wikilinks**: Add `[[wikilinks]]` between all related
   pages. When new pages reference existing pages, update the existing
   pages' Links section with backlinks to the new pages.
   **Only link pages with substantive intellectual connections** — shared
   theoretical lineage, direct influence, or genuine engagement with
   the same ideas. Do not add backlinks based on metaphorical parallels
   or superficial word overlap across unrelated domains.

## Step 8: Update Index and Log

1. Add entries to `wiki/index.md` under the correct type section
   (alphabetically sorted within each section).
2. Prepend an entry to `wiki/log.md`:
   ```
   ## [YYYY-MM-DD] ingest | <source title>
   Brief description of what was ingested and pages created.
   ```

## Step 9: Archive Source

Move the ingested source file(s) from `raw/` to `raw/_ingested/`
(create the directory if it doesn't exist). This prevents
`ingest-batch` from re-proposing already-processed sources.

The `sources` frontmatter in wiki pages should reference the new
path (e.g. `raw/_ingested/filename.md`).

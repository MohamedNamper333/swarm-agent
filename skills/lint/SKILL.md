---
name: "lint"
description: "Run a wiki health pass for an Agenpedia wiki. Use when the user wants structural cleanup, maintenance, or a pre-commit review, not for ordinary wiki questions or ingest requests."
disable-model-invocation: false
user-invocable: true
---

# Wiki Lint

Check the health of the wiki and fix actionable issues.

## Context

Read `AGENTS.md` at the project root for wiki conventions, page types,
frontmatter schema, naming conventions, cross-reference rules, index
format, and log format. All operations below must conform to those rules.

## Determine Mode

This skill can run in two contexts:

- **Manual / pre-commit mode**: invoked directly by the user or during
  a pre-commit check. Run ALL checks including growth suggestions.
- **Auto-maintenance mode**: invoked after `ingest` or `ingest-batch`,
  whether that follow-on step was requested directly or loaded
  implicitly from context. Skip growth suggestions — only run
  structural checks and report contradictions.

To determine mode: if the conversation shows that `ingest` or
`ingest-batch` just ran and this lint is acting as a follow-on
maintenance step, use auto-maintenance mode. Otherwise, use manual
mode.

## Checks

### 1. Broken Wikilinks

Scan all `wiki/*.md` files for `[[wikilink]]` references. For each
wikilink, verify the target file exists in `wiki/` (target is
`wiki/<link-text>.md`). Report all broken wikilinks with the source
file and line number.

**Auto-fix**: Use `git log -- wiki/<target>.md` to check whether git
has any record of the file:

- **Has git history (deleted page)**: The page existed before and was
  removed. Clean up references — remove the wikilink from referring
  pages, remove the index entry if present, and remove any backlinks
  to the deleted page from other pages' Links sections.
- **No git history (missing page)**: The page never existed. If the
  target clearly should exist (e.g., a concept or entity referenced
  by multiple pages), create it with appropriate frontmatter and add
  it to the index.

### 2. Orphan Pages

Find wiki pages that have zero inbound wikilinks from other wiki pages.
Exclude `wiki/index.md` and `wiki/log.md` from this check (they are
structural pages, not content pages).

**Auto-fix**: Add wikilinks from the most relevant existing pages to
the orphan page. Update both the orphan and the linking page to maintain
bidirectional links. **Only create links with substantive intellectual
connections** — shared theoretical lineage, direct influence, or genuine
engagement with the same ideas. Do not link based on metaphorical
parallels or superficial word overlap across unrelated domains.

### 3. Missing Entity/Concept Pages

Scan wiki page bodies for mentions of proper names (people, orgs,
tools, products) or established concepts that don't have dedicated
wiki pages. Cross-reference against the index.

**Auto-fix**: Create missing entity or concept pages with appropriate
frontmatter, a brief description, and wikilinks back to the pages that
mention them. Add to the index.

### 4. Coverage Gaps

Compare files in `raw/` against wiki pages. A raw source has coverage
if at least one wiki page lists it in its `sources` frontmatter field.

**Exclude** from this check:
- `raw/_skipped/` (files triaged as SKIP)
- `raw/assets/` (binary attachments, not sources)

Report uncovered raw sources and suggest ingesting them.

### 5. Contradiction Detection

Read wiki pages that cover overlapping topics and check for
contradictory claims. This requires reasoning about content, not just
structural checks.

**Report only** — flag contradictions for the human to review. Do not
auto-fix contradictions.

### 6. Stale Information

Check for wiki pages with dates significantly in the past or content
that references time-sensitive information (e.g., "currently",
"as of 2024") that may need updating.

**Report only** — flag for human review.

## Growth Suggestions (Manual Mode Only)

Skip this section entirely in auto-maintenance mode.

In manual mode, after completing all checks:

1. **New questions**: Based on themes and gaps in the wiki, suggest
   questions the wiki could investigate.
2. **New sources**: Based on concepts mentioned but not deeply covered,
   suggest sources to look for.

## Output

Produce a structured report:

```
## Wiki Lint Report — YYYY-MM-DD

### Broken Wikilinks
(list or "None found")

### Orphan Pages
(list or "None found")

### Missing Entity/Concept Pages
(list or "None found")

### Coverage Gaps
(list or "All raw sources covered")

### Contradictions
(list or "None detected")

### Stale Information
(list or "None detected")

### Auto-Fixes Applied
(list of changes made)

### Growth Suggestions (manual mode only)
(suggestions or omitted in auto-maintenance mode)
```

## Log Entry

After completing the lint, prepend an entry to `wiki/log.md`:

```
## [YYYY-MM-DD] lint | Wiki health check
Brief summary of findings and fixes applied.
```

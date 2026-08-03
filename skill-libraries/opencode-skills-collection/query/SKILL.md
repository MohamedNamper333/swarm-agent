---
name: "query"
description: "Answer natural-language questions from an Agenpedia wiki. Use when the user wants information from existing wiki pages, not when they need new sources ingested or a maintenance workflow run."
argument-hint: "<question>"
disable-model-invocation: false
user-invocable: true
---

# Wiki Query

Answer a natural language question using the wiki knowledge base.

## Context

Read `AGENTS.md` at the project root for wiki conventions, page types,
frontmatter schema, cross-reference rules, index format, and log format.
All operations below must conform to those rules.

## Step 1: Identify Relevant Pages

Read `wiki/index.md` to identify pages relevant to the question. Use
the index entries and page types to narrow down which pages to consult.

## Step 2: Read Relevant Pages

Read the full content of the most relevant wiki pages. Follow wikilinks
to gather additional context if needed.

## Step 3: Answer with Citations

Answer the question using information from the wiki pages. Include
`[[wikilink]]` citations to every wiki page used in the answer.

If no relevant pages are found, say so and suggest ingesting sources
on the topic (e.g., "No wiki pages cover this topic yet. You could
ingest a source about it with the `ingest` skill").

Answers are not limited to plain text — use the best format for the
question:
- Comparison tables for "compare X vs Y" questions
- Charts or structured data for quantitative questions
- Prose with citations for explanatory questions

## Step 4: Auto-File Synthesis (When Appropriate)

Create a new synthesis page **only** when the answer:
- Synthesizes information across multiple wiki pages
- Produces a comparison or thematic analysis
- Surfaces a non-obvious connection between concepts or entities

**Do not** auto-file for simple factual lookups that just repeat what
one page already says.

When filing a synthesis page:

1. Create the page in `wiki/` with frontmatter:
   ```yaml
   ---
   type: synthesis
   origin: query
   date: YYYY-MM-DD
   sources:
     - "wiki/cited-page-1.md"
     - "wiki/cited-page-2.md"
   aliases: []
   tags: []
   ---
   ```
   Note: for query-origin synthesis pages, `sources` lists the wiki
   pages cited (as wiki paths), not raw sources.

2. Add bidirectional wikilinks between the synthesis page and the
   pages it cites.

3. Add the entry to `wiki/index.md` under `## Syntheses` (alphabetically).

4. Prepend a log entry to `wiki/log.md`:
   ```
   ## [YYYY-MM-DD] query | <question>
   Brief description of the answer and synthesis filed.
   ```

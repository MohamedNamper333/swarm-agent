---
name: "ingest-batch"
description: "Batch-triage raw sources for an Agenpedia wiki. Use when the user explicitly wants multiple files reviewed and processed through Wiki Ingest, not when they only need wiki answers or a single-source ingest."
argument-hint: "<optional: pasted text with multiple notes, or directory path to scan>"
disable-model-invocation: true
user-invocable: true
---

# Wiki Batch Ingest

Triage and batch-ingest multiple sources into the wiki. Use deep reasoning (enable extended thinking if your harness supports it) for deep analysis of sources during triage.

## Context

Read `AGENTS.md` at the project root for wiki conventions, page types,
frontmatter schema, naming conventions, and cross-reference rules.
All operations below must conform to those rules.

## Step 1: Collect Sources

Determine the input type from the argument:

- **No argument**: Scan `raw/` for files that don't have a corresponding
  wiki page. A file is "covered" if it lives in `raw/_ingested/` or
  if at least one wiki page in `wiki/` lists it in its `sources`
  frontmatter. Exclude `raw/_skipped/`, `raw/_ingested/`, and
  `raw/assets/` from the scan.
- **Directory path**: Scan the specified directory instead of `raw/`.
- **Pasted text** (multiple notes separated by clear boundaries): Save
  each note as a separate `.md` file in `raw/` with a descriptive
  filename derived from the content. Then proceed with those files.

If no uncovered files are found, report "All raw sources are already
covered by wiki pages" and stop.

## Step 2: Triage

Read each uncovered file and assign a verdict:

- **INGEST**: Source has substantive content worth adding to the wiki.
  Will be processed by `ingest`.
- **SKIP**: Source is low-value, duplicate, or irrelevant (e.g., empty
  files, test content, exact duplicates of existing sources). Will be
  moved to `raw/_skipped/`.
- **MERGE**: Source covers the same topic as another uncovered source
  and should be co-ingested into a single wiki page. Group MERGE files
  together.

## Step 3: Present Verdicts

Present the triage results as a table:

```
| File | Verdict | Reason |
|------|---------|--------|
| raw/article-1.md | INGEST | Substantive article on X |
| raw/notes-old.md | SKIP | Duplicate of raw/notes.md |
| raw/paper-part1.md | MERGE (group 1) | Part 1 of paper on Y |
| raw/paper-part2.md | MERGE (group 1) | Part 2 of paper on Y |
```

**Wait for the user's approval.** The user may change verdicts before
confirming.

## Step 4: Execute Verdicts

After approval, process in this order:

### SKIP files
For each SKIP file, move it to `raw/_skipped/` (create the directory
if it doesn't exist):
```
mv raw/<filename> raw/_skipped/<filename>
```

### INGEST files
List all approved INGEST files and ask the user to confirm before
processing begins.

For each approved INGEST file, **sequentially**:
1. Trigger the `ingest` skill with <filepath>
2. Wait for the ingest to complete (user approves each one)
3. Only then proceed to the next file

**Do not process INGEST files in parallel.** Sequential execution
prevents conflicting cross-references and duplicate entity pages.

### MERGE groups
For each MERGE group, Trigger the `ingest` skill with <filepath1> <filepath2> ... with all files in the group as arguments.

Process MERGE groups sequentially, one at a time.

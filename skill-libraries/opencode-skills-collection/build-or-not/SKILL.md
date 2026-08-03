---
name: "build-or-not"
description: "Assess whether a capability should be reused, adapted, or built from scratch. Use when the user asks whether something already exists or whether building it would reinvent the wheel."
argument-hint: "[capability or product idea to assess]"
disable-model-invocation: false
user-invocable: true
---

# Build Or Not

Run a conservative prior-art and reuse check before recommending a greenfield build.

This skill is self-contained. The local Python runtime shipped in `scripts/` performs the real retrieval, ranking, rendering, and audit persistence.

## Trigger

Use this skill when the user is effectively asking one of these:

- should I build this?
- does this already exist?
- am I reinventing the wheel?
- what tools, products, repos, or packages already cover this?
- is there enough prior art that `build_new` would be a mistake?

Do not use this skill for general brainstorming without an existence or reuse question.

## Default posture

Stay conservative.

- A credible existing product counts against `build_new`.
- A credible existing repo, framework, package, MCP server, or reusable component also counts against `build_new`.
- Prefer `reuse_existing` or `adapt_existing` unless the evidence is genuinely thin after Exa-first discovery plus structured corroboration.
- Treat `build_new` as the rare outcome.

## Mandatory execution step

Do not answer from memory alone.

Always run the local script:

```bash
python scripts/run.py "<capability or idea>"
```

If you need structured output:

```bash
python scripts/run.py "<capability or idea>" --json
```

## What the script produces

The local runtime writes:

- final JSON result
- canonical markdown report
- reference HTML report
- audit bundle with raw evidence artifacts

Artifacts are written under the current workspace:

```text
.cache/skills-tools/build-or-not/<run_id>/
```

## How to use the result

After the script finishes:

- read the verdict and confidence first
- open the HTML report for the human-facing explanation
- inspect the JSON only if downstream structure is needed
- keep the audit bundle path in the answer so the run stays traceable

If warnings mention missing Exa configuration or incomplete evidence, surface that plainly and avoid claiming `build_new` too confidently.

## Evidence rules

Follow the rubric in [references/evidence-rubric.md](references/evidence-rubric.md).

## Expected answer shape

Your answer should usually include:

- the normalized verdict
- the confidence level
- a short rationale
- the most important reuse candidate or gap
- the HTML report path
- the audit bundle path

Do not dump the full JSON unless the user asked for it.

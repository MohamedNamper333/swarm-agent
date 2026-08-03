---
name: "find-tools"
description: "Recommend the best existing tool for a capability. Use when the user wants one concrete tool, package, framework, repo, product, MCP server, or skill choice plus alternatives, not a build-vs-buy verdict."
argument-hint: "[tool query or capability to satisfy]"
disable-model-invocation: false
user-invocable: true
---

# Find Tools

Find the strongest existing tool candidates for a capability and recommend the current best fit when the evidence is strong enough.

This skill is self-contained. The local Python runtime shipped in `scripts/` performs retrieval, grouping, rendering, and audit persistence.

## Trigger

Use this skill when the user is effectively asking one of these:

- what tool should I use for this?
- what is the best package/framework/repo/product for this job?
- are there existing tools that solve this capability?
- give me one best fit plus alternatives

Do not use this skill when the main question is whether to build something new. In that case use `build-or-not`.

## Mandatory execution step

Always run the local script:

```bash
python scripts/run.py "<tool query>"
```

If you need structured output:

```bash
python scripts/run.py "<tool query>" --json
```

## Decision posture

- Recommend one `best fit` only when corroboration is strong enough.
- Otherwise return `no_clear_fit` or `needs_manual_review`.
- A recommendation may be a product, repo, package, framework, MCP server, or skill.
- Keep the recommendation conservative when Exa-first discovery did not run.

## What the script produces

The local runtime writes:

- final JSON result
- canonical markdown report
- reference HTML report
- audit bundle with raw evidence artifacts

Artifacts are written under the current workspace:

```text
.cache/skills-tools/find-tools/<run_id>/
```

## Expected answer shape

Your answer should usually include:

- the decision
- the confidence level
- the best fit if one exists
- 2 to 4 alternatives when useful
- the HTML report path
- the audit bundle path

Do not claim a strong single recommendation when the runtime returned `no_clear_fit` or `needs_manual_review`.

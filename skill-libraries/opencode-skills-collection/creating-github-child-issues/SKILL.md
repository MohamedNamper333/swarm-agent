---
name: "creating-github-child-issues"
description: "Creates or reconciles GitHub child task issues for an approved Phase 4 task plan. Use after docs/<ISSUE_SLUG>-tasks.md is clarified and the user has approved GitHub writes; dispatches task-issue-creator and returns a compact status summary."
---

# Creating GitHub Child Issues

You are a Phase 4 GitHub child-issue orchestrator. The orchestrator does three
things: **derive identifiers** from `ISSUE_URL`, **dispatch** `task-issue-creator`
with the original URL, and **relay** the structured Phase 4 summary to the
caller.

The subagent owns plan parsing, `gh` CLI and REST API calls, capability
detection, plan-file edits, and validation. The orchestrator keeps only
verdicts, paths, counts, write-path metadata, warnings, and failures.

Run this skill only after the caller or user has approved GitHub issue writes
and the scoped update to `docs/<ISSUE_SLUG>-tasks.md`. Normal orchestration
passes that approval as `APPROVED_MUTATION_SCOPE`. If invoked directly and
approval is unclear, ask once for that approval; if approval is absent or
declined, return the contract-defined blocked summary with
`Validation: NOT_RUN`.

## Inputs

| Input | Required | Example |
| ----- | -------- | ------- |
| `ISSUE_URL` | Yes | `https://github.com/acme/app/issues/42` |
| `APPROVED_MUTATION_SCOPE` | No | `GitHub child issues plus docs/acme-app-42-tasks.md update approved` |

Normal orchestrated runs include `APPROVED_MUTATION_SCOPE`. Direct standalone
runs may collect the same approval from the user before dispatch. Derive
locally for routing and reporting only. The full URL is the canonical context
that flows to the subagent and to `gh --repo`:

- **OWNER:** path segment after `github.com/`, lowercased for slug stability
- **REPO:** next path segment, lowercased for slug stability
- **PARENT_NUMBER:** numeric segment after `/issues/`
- **ISSUE_SLUG:** `<owner>-<repo>-<parent_number>`

## Progressive Loading Map

Read each row's target file **only** when the listed need arises. Load paths
are relative to this `SKILL.md`; never preload them.

| Need | Load |
| ---- | ---- |
| Phase 4 artifact shape, summary fields, or status semantics | `./references/phase-4-io-contracts.md` |
| Current GitHub CLI flags, REST sub-issue endpoint behavior, task-list semantics, or skill-maintenance rationale | `./references/external-sources.md`, then fetch only the smallest relevant URL |
| Child issue creation or reconciliation | `./subagents/task-issue-creator.md` |

External URLs are **optional, just-in-time** sources. This skill remains
executable from its bundled files when network access is unavailable; the
subagent and references include enough local guidance for routine runs.

## Subagent Registry

Read a subagent definition only when dispatching that subagent.

| Subagent | Path | Purpose |
| -------- | ---- | ------- |
| `task-issue-creator` | `./subagents/task-issue-creator.md` | Reconciles the clarified plan with GitHub task issues and returns the Phase 4 summary |

## Workflow

1. Confirm `ISSUE_URL` is present. If it is missing or malformed, return the
   blocked summary from `./references/phase-4-io-contracts.md` with
   `Parent: UNKNOWN`, `ISSUE_SLUG: UNKNOWN`, `Plan file: not updated`, zero
   counts, `Write model: unknown`, `Capability: not checked`, and
   `Validation: NOT_RUN`.
2. Derive `ISSUE_SLUG` for local reporting, then confirm the run is approved
   for GitHub writes plus the scoped plan-file update. If approval is absent
   or declined, return the same blocked-summary shape with the derived
   `ISSUE_SLUG` and `Plan file: not updated`.
3. Read `./references/phase-4-io-contracts.md` only when interpreting an output,
   validating Phase 4, or explaining the required artifact shape.
4. Read `./subagents/task-issue-creator.md` and dispatch it with `ISSUE_URL`
   and the approved mutation scope. The approved scope is limited to GitHub
   child-issue create/reuse actions, accepted task-list fallback records, and
   `docs/<ISSUE_SLUG>-tasks.md`.
5. Route on the returned `TASK_ISSUES` and `Validation` lines.
6. Report a concise Phase 4 rollup: parent, `ISSUE_SLUG`, plan path, counts,
   write model, capability note, warnings, failures, and the reminder that
   implementation work has not begun.

## Routing Rules

| Result | Orchestrator action |
| ------ | ------------------- |
| `TASK_ISSUES: PASS` with `Validation: PASS` | Report success and proceed |
| `TASK_ISSUES: WARN` with `Validation: PASS` | Report usable linked output, degraded `task-list` traceability, and any `Not Created` rows that require manual resolution before that task can execute |
| `TASK_ISSUES: BLOCKED` | Stop and surface missing approval, plan-shape, or unsafe-linkage issues |
| `TASK_ISSUES: FAIL` | Stop and surface the fatal GitHub, auth, `gh`, create/link, or validation failure |
| `TASK_ISSUES: ERROR` or `Validation: FAIL` | Stop and surface the unexpected failure or local contract failure |

Treat `Validation: NOT_RUN` as incomplete Phase 4 output even when the top-level
status is already `BLOCKED`, `FAIL`, or `ERROR`.

## Output Contract

Return only the subagent's structured summary plus a short caller-facing rollup.
The full summary schema lives in `./references/phase-4-io-contracts.md`.

Always include `Write model:` and `Capability:` when reporting GitHub results.
GitHub child-issue support varies by CLI version, repository, API availability,
and installed extensions, so the run-time path matters to the caller.

## Example

<example>
Input: `ISSUE_URL=https://github.com/acme/app/issues/42`

1. The orchestrator derives `ISSUE_SLUG=acme-app-42` for reporting.
2. The orchestrator dispatches `task-issue-creator` with `ISSUE_URL` and
   approved mutation scope.
3. The subagent returns the contract summary with `TASK_ISSUES: PASS`,
   `Validation: PASS`, parent, plan path, detected write model, capability,
   counts, warnings, and failures.
4. The orchestrator reports success, write path, creation/link counts,
   warnings/failures if any, and that no implementation has started.
</example>

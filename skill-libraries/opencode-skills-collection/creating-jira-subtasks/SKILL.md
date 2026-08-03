---
name: "creating-jira-subtasks"
description: "Creates or reconciles Jira subtasks for an approved Phase 4 task plan. Use after docs/<TICKET_KEY>-tasks.md is clarified and the user has approved Jira writes; dispatches subtask-creator and returns a compact status summary."
---

# Creating Jira Subtasks

You are a Phase 4 Jira subtask orchestrator. The orchestrator does three
things: **derive identifiers** from `JIRA_URL`, **dispatch** `subtask-creator`
with the original URL, and **relay** the structured Phase 4 summary to the
caller.

The subagent owns plan parsing, Jira operations, plan-file edits, and
validation. The orchestrator keeps only verdicts, paths, counts, warnings, and
failures.

Run this skill only after the caller or user has approved Jira subtask writes
and the scoped update to `docs/<TICKET_KEY>-tasks.md`. Normal orchestration
passes that approval as `APPROVED_MUTATION_SCOPE`. If invoked directly and
approval is unclear, ask once for that approval; if approval is absent or
declined, return the contract-defined blocked summary with
`Validation: NOT_RUN`.

## Inputs

| Input | Required | Example |
| ----- | -------- | ------- |
| `JIRA_URL` | Yes | `https://workspace.atlassian.net/browse/PROJ-123` |
| `APPROVED_MUTATION_SCOPE` | No | `Jira subtasks plus docs/PROJ-123-tasks.md update approved` |

Normal orchestrated runs include `APPROVED_MUTATION_SCOPE`. Direct standalone
runs may collect the same approval from the user before dispatch. Derive
locally for routing and reporting only. The full URL is the canonical context
that flows to the subagent and to Jira-capable tools:

- **Workspace:** subdomain before `.atlassian.net`
- **Project:** prefix before the dash in the ticket key
- **TICKET_KEY:** full path segment, such as `PROJ-123`

## Progressive Loading Map

Read each row's target file **only** when the listed need arises. Load paths
are relative to this `SKILL.md`; never preload them.

| Need | Load |
| ---- | ---- |
| Phase 4 artifact shape, summary fields, or status semantics | `./references/phase-4-io-contracts.md` |
| Current Jira REST v3 syntax, subtask configuration, Atlassian Document Format, or skill-maintenance rationale | `./references/external-sources.md`, then fetch only the smallest relevant URL |
| Subtask creation or reconciliation | `./subagents/subtask-creator.md` |

External URLs are **optional, just-in-time** sources. This skill remains
executable from its bundled files when network access is unavailable; the
subagent and references include enough local guidance for routine runs.

## Subagent Registry

Read a subagent definition only when dispatching that subagent.

| Subagent | Path | Purpose |
| -------- | ---- | ------- |
| `subtask-creator` | `./subagents/subtask-creator.md` | Reconciles the clarified plan with Jira subtasks and returns the Phase 4 summary |

## Workflow

1. Confirm `JIRA_URL` is present. If it is missing or malformed, return the
   blocked summary from `./references/phase-4-io-contracts.md` with
   `Parent: UNKNOWN`, `TICKET_KEY: UNKNOWN`, `Plan file: not updated`, zero
   counts, and `Validation: NOT_RUN`.
2. Derive `TICKET_KEY` for local reporting, then confirm the run is approved
   for Jira writes plus the scoped plan-file update. If approval is absent or
   declined, return the same blocked-summary shape with the derived
   `TICKET_KEY` and `Plan file: not updated`.
3. Read `./references/phase-4-io-contracts.md` only when interpreting an
   output, validating Phase 4, or explaining the required artifact shape.
4. Read `./subagents/subtask-creator.md` and dispatch it with `JIRA_URL` and
   the approved mutation scope. The approved scope is limited to Jira subtask
   create/reuse actions and `docs/<TICKET_KEY>-tasks.md`.
5. Route on the returned `SUBTASKS` and `Validation` lines.
6. Report a concise Phase 4 rollup: parent, `TICKET_KEY`, plan path, counts,
   warnings, failures, and the reminder that implementation work has not
   begun.

## Routing Rules

| Result | Orchestrator action |
| ------ | ------------------- |
| `SUBTASKS: PASS` with `Validation: PASS` | Report success and proceed |
| `SUBTASKS: WARN` with `Validation: PASS` | Report usable linked output, visible warnings, and any `Not Created` rows that require manual resolution before that task can execute |
| `SUBTASKS: BLOCKED` | Stop and surface missing approval, unsafe plan shape, unsafe linkage, or manual subtask-type selection |
| `SUBTASKS: FAIL` | Stop and surface the fatal Jira, configuration, required-field, or validation failure |
| `SUBTASKS: ERROR` or `Validation: FAIL` | Stop and surface the unexpected failure or local contract failure |

Treat `Validation: NOT_RUN` as incomplete Phase 4 output even when the
top-level status is already `BLOCKED`, `FAIL`, or `ERROR`.

## Output Contract

Return only the subagent's structured summary plus a short caller-facing
rollup. The full summary schema lives in `./references/phase-4-io-contracts.md`.

Do not add GitHub-style write-model or capability lines to the Jira report.
Jira uses one native subtask relationship path for this workflow.

## Example

<example>
Input: `JIRA_URL=https://workspace.atlassian.net/browse/PROJ-123`

1. The orchestrator derives `TICKET_KEY=PROJ-123` for reporting.
2. The orchestrator dispatches `subtask-creator` with `JIRA_URL` and approved
   mutation scope.
3. The subagent returns the contract summary with `SUBTASKS: PASS`,
   `Validation: PASS`, parent, plan path, counts, warnings, and failures.
4. The orchestrator reports success, creation/link counts, warnings/failures
   if any, and that no implementation has started.
</example>

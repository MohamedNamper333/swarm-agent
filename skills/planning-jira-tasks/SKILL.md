---
name: "planning-jira-tasks"
description: "Phase 2 of the Jira planning workflow. Reads a Jira ticket snapshot, dispatches a plan/prioritize/validate pipeline, and writes docs/<TICKET_KEY>-tasks.md with branch names for every planned Jira subtask."
---

# Planning Jira Ticket Tasks

Plan a Jira ticket snapshot into `docs/<TICKET_KEY>-tasks.md`. This is the
Phase 2 orchestrator for the Jira planning workflow: it routes stages,
dispatches specialists, preserves stage artifacts for resume and critique, and
returns a concise handoff.

The orchestrator keeps only workflow state, subagent verdicts, paths, counts,
and user decisions in context. Detailed contracts, templates, validation checks,
and source-backed background are loaded just in time from bundled references or
optional external URLs.

## Inputs

| Input | Required | Example |
| ----- | -------- | ------- |
| `TICKET_KEY` | Yes | `JNS-6065` |
| `RE_PLAN` | No | `true` |
| `DECISIONS` | No | `SSO decision changes task dependencies` |

Phase 2 is file-driven. `docs/<TICKET_KEY>.md` must already exist as the Jira
ticket snapshot.

## Progressive Loading Map

| Need | Load |
| ---- | ---- |
| Normal run, dispatch payloads, retry loop | `./references/execution-guide.md` |
| Final artifact contract, branch policy, subtask handling | `./references/output-contract.md` |
| Critique-driven re-plan or recovery from stage artifacts | `./references/re-plan-cycle.md` |
| Source-backed background or current platform syntax | `./references/external-sources.md` |
| Subagent-specific guides, templates, or validation checks | Load only from the dispatched subagent |

Bundled paths in this file are relative to this `SKILL.md`; files loaded later
use paths relative to their own locations. All bundled files travel with the
package.
External URLs are optional progressive enhancement: fetch them only when local
contracts need background or current syntax, and proceed from bundled references
when network access is unavailable.

## Subagent Registry

| Subagent | Path | Purpose |
| -------- | ---- | ------- |
| `task-planner` | `./subagents/task-planner.md` | Decompose the ticket and draft the stage 1 plan |
| `dependency-prioritizer` | `./subagents/dependency-prioritizer.md` | Add dependency order, priority, and branch names |
| `task-validator` | `./subagents/task-validator.md` | Validate the prioritized plan and append QA findings |
| `stage-validator` | `./subagents/stage-validator.md` | Check preflight, inter-stage, and final structural gates |

## Workflow

| Path | When | Next reference |
| ---- | ---- | -------------- |
| Normal | `RE_PLAN` is absent or `false` | `./references/execution-guide.md` |
| Re-plan | `RE_PLAN=true` with critique decisions | `./references/re-plan-cycle.md`, then `./references/execution-guide.md` |

The normal path is: preflight snapshot validation, Stage 1 detailed planning,
Stage 1 validation, Stage 2 dependency/branch planning, Stage 2 validation,
Stage 3 final validation report, Stage 3 validation, postpipeline validation,
handoff.

Preserve `docs/<TICKET_KEY>-stage-1-detailed.md`,
`docs/<TICKET_KEY>-stage-2-prioritized.md`, and
`docs/<TICKET_KEY>-tasks.md` on disk. They are orchestration state for resume,
critique, and targeted retries; they are not implementation outputs.

Use targeted fix loops only. Re-dispatch the stage that produced the failing
artifact, pass only the validator's issue list, rerun only the failing gate, and
stop after 3 failed cycles for the same gate.

## Return Format

Return only this phase handoff. Use `PLANNING: PASS` only when every stage and
stage-validation gate has passed.

```text
PLANNING: PASS | FAIL
TICKET_KEY: <TICKET_KEY>
File: <final file path or "not written">
Tasks: <N>
Branches: <N unique branch names>
Cross-cutting questions: <N>
Validation warnings: <N>
Failure category: PREFLIGHT | STAGE_1 | STAGE_2 | STAGE_3 | POSTPIPELINE | NONE
Reason: <one line>
Artifacts preserved: <comma-separated paths>
```

## Example

<example>
Input: `TICKET_KEY=JNS-6065`

1. Load `./references/execution-guide.md` for the dispatch payloads.
2. Dispatch `stage-validator` for `preflight`; it returns `STAGE_VALIDATION: PASS`.
3. Dispatch `task-planner`, `dependency-prioritizer`, and `task-validator` in sequence, validating after each produced artifact.
4. Dispatch `stage-validator` for `postpipeline`; it returns `STAGE_VALIDATION: PASS`.
5. Return the concise `PLANNING: PASS` handoff with preserved artifact paths.
</example>

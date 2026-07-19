---
name: "planning-github-task"
description: "Plans execution for one task from docs/<ISSUE_SLUG>-tasks.md by coordinating brief, implementation plan, test specification, and refactoring recommendation artifacts before critique or implementation."
---

# Planning GitHub Task

You are a GitHub issue task planning coordinator. Plan exactly how to
execute one task from a GitHub issue task plan by dispatching focused
subagents, retaining only their structured summaries, and leaving reusable
workflow artifacts on disk.

This skill is standalone. It depends only on files bundled in this folder
and on optional public URLs listed in `./references/external-sources.md`
for just-in-time methodology checks.

Success means the four planning artifacts exist and are ready for downstream
critique and task execution. When a prerequisite is missing, a planning
ambiguity remains material, or a subagent cannot complete its artifact, stop
and surface the blocker with a concise summary.

## Inputs

| Input | Required | Example |
| ----- | -------- | ------- |
| `ISSUE_SLUG` | Yes | `acme-app-42` |
| `TASK_NUMBER` | Yes | `3` |
| `RE_PLAN` | No | `true` |
| `DECISIONS_FILE` | No | `docs/acme-app-42-task-3-decisions.md` |

Use `RE_PLAN` and `DECISIONS_FILE` only for critique-driven reruns.

## Workflow Overview

| Step | Owner | Output |
| ---- | ----- | ------ |
| Normalize inputs | Inline | Required task identity and re-plan options, or blocker |
| Validate readiness and prepare brief | `execution-prepper` | `PREP` summary and brief path |
| Plan implementation | `execution-planner` | `PLAN` summary and execution-plan path |
| Specify tests | `test-strategist` | `TEST_SPEC` summary and test-spec path |
| Advise refactoring | `refactoring-advisor` | `REFACTORING` summary and recommendation path |
| Report result | Inline | Short planning summary and artifact paths |

## Subagent Registry

| Subagent | Path | Purpose |
| -------- | ---- | ------- |
| `execution-prepper` | `./subagents/execution-prepper.md` | Validate task readiness and assemble the execution brief |
| `execution-planner` | `./subagents/execution-planner.md` | Inspect the codebase and write the implementation plan |
| `test-strategist` | `./subagents/test-strategist.md` | Define behavior-driven tests for the task |
| `refactoring-advisor` | `./subagents/refactoring-advisor.md` | Recommend only the refactoring needed for this task |

Read a subagent definition only when dispatching that exact specialist.

## Progressive Disclosure Policy

| Layer | File or source | Load when |
| ----- | -------------- | --------- |
| Core orchestration | This `SKILL.md` | Always, when the skill triggers |
| Pipeline routing | `./references/pipeline.md` | Running the standard pipeline or a critique-driven re-plan |
| Data contracts | `./references/data-contracts.md` | Checking invocation boundaries, artifact paths, readiness rules, or lifecycle rules |
| Artifact templates | `./references/artifact-templates.md` | A subagent is assembling or repairing its owned artifact |
| Handoff formats | `./references/handoff-formats.md` | A subagent is preparing or repairing its return summary |
| External source routing | `./references/external-sources.md` | A public source could change the current planning, testing, or refactoring decision |
| Subagent definition | `./subagents/<name>.md` | Dispatching that subagent |

External pages are optional just-in-time sources. Local contracts and
templates remain authoritative when network access is absent. The coordinator
does not fetch methodology pages in advance.

## Coordinator Behavior

The coordinator validates required invocation inputs, loads the smallest
reference for the current phase, dispatches one subagent at a time, and
branches on the returned status. Task-plan parsing, readiness checks,
codebase inspection, artifact writing, methodology fetches, and validation
repairs stay inside the phase owner.

Dispatch each subagent with the relevant task handoff. Reference path inputs
are optional because each subagent defaults to the co-located files it needs.
If a runtime requires explicit path values, use the subagent-relative defaults
from that subagent's input table.

Branch on the structured status fields, not on prose:

| Summary state | Coordinator action |
| ------------- | ------------------ |
| `*: PASS` | Continue to the next stage or final report |
| `*: BLOCKED` | Stop and report the missing prerequisite artifact or task section |
| `*: FAIL` | Stop and report the unresolved dependency, ambiguity, behavior gap, or planning risk |
| `*: ERROR` | Stop and ask the user how to proceed |

Keep only verdicts, file paths, source URLs fetched, and next-step-relevant
notes from each subagent.

## Output Contract

This skill writes only workflow-planning artifacts for one task:

```text
docs/<ISSUE_SLUG>-task-<TASK_NUMBER>-brief.md
docs/<ISSUE_SLUG>-task-<TASK_NUMBER>-execution-plan.md
docs/<ISSUE_SLUG>-task-<TASK_NUMBER>-test-spec.md
docs/<ISSUE_SLUG>-task-<TASK_NUMBER>-refactoring-plan.md
```

These workflow-state files stay on disk for resumability and are not
implementation history. Use `./references/data-contracts.md` for
prerequisite and lifecycle rules. Use `./references/artifact-templates.md`
for exact artifact sections.

## Validation And Re-Plan

Read `./references/pipeline.md` before a standard run or re-plan. Validate
each stage before dispatching and after the subagent returns. On
critique-driven reruns, start at the earliest invalidated stage and rerun
only downstream dependents. Stop after 3 re-plan loops and surface the
remaining high-severity concerns.

When an artifact validation repair is needed, re-dispatch only the artifact
owner with `REPAIR_FINDINGS` and the minimum existing artifact inputs required
for that owner.

## Example

<example>
Input: `ISSUE_SLUG=acme-app-42`, `TASK_NUMBER=2`

Flow: dispatch `execution-prepper` to validate `docs/acme-app-42-tasks.md`
and write the brief, then dispatch `execution-planner`, `test-strategist`,
and `refactoring-advisor` with the artifact paths returned by the prior
stages. Report that Task 2 planning is complete, list the four artifact
paths, summarize the approach, test coverage shape, refactoring verdict,
and any `References fetched` URLs returned by the subagents.
</example>

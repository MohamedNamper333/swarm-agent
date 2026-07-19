---
name: "executing-github-task"
description: "Executes exactly one planned GitHub workflow task after critique approval. Use when a numbered task should move through kickoff, implementation, documentation, requirements verification, review gates, targeted fix cycles, and final reporting without continuing to the next task."
---

# Executing GitHub Task

You are the per-task execution orchestrator for the GitHub workflow. Do three
things: **validate** readiness, **dispatch** the next specialist, and **decide**
whether to advance, run a targeted fix cycle, or escalate. Specialists do the
heavy lifting in isolation; the orchestrator carries only concise summaries,
paths, and verdicts between phases.

The execution kickoff is the **first mutation boundary after critique
approval**. Everything before kickoff remains critique and planning on disk.

## Inputs

| Input | Required | Example | Notes |
| ----- | -------- | ------- | ----- |
| `ISSUE_SLUG` | Yes | `acme-app-42` | Workflow key; derives standard artifact paths. |
| `TASK_NUMBER` | Yes | `3` | Exactly one task per invocation. |

Required artifacts, readiness checks, handoff shapes, kickoff semantics, and
artifact lifecycle rules live in `./references/contracts.md`. Read that file
before crossing the execution boundary.

## Workflow Overview

| Stage | Goal | Primary result |
| ----- | ---- | -------------- |
| 0. Readiness | Confirm the selected task can start | Ready task or explicit blocker |
| 1. Kickoff | Enter the planned branch and start tracker state | `KICKOFF_REPORT` |
| 2. Execution | Implement the approved change | `EXECUTION_REPORT` |
| 3. Documentation | Add in-code docs and update local tracking before gates | `DOCUMENTATION_REPORT` |
| 4. Requirements Verification | Confirm Definition of Done coverage | `VERIFICATION_RESULT` |
| 5. Quality Gates | Run clean-code, architecture, security review | Review verdicts |
| 6. Targeted Fix Cycle | Re-run only failed verification or review paths with explicit retry budgets | Re-validated task or escalation |
| 7. Finalize and Report | Finalize eligible tracker completion after gates and report this task's outcome | `FINAL_TRACKING_REPORT` and `FINAL_TASK_REPORT` |

## Subagent Registry

| Subagent | Path | Purpose |
| -------- | ---- | ------- |
| `execution-starter` | `./subagents/execution-starter.md` | Performs kickoff, workspace checks, branch entry, and eligible `gh` startup updates. |
| `task-executor` | `./subagents/task-executor.md` | Implements the scoped change and tests from approved planning artifacts. |
| `documentation-writer` | `./subagents/documentation-writer.md` | Adds minimal in-code docs, updates task tracking, and finalizes optional `gh` completion updates only after gates pass. |
| `requirements-verifier` | `./subagents/requirements-verifier.md` | Checks that the task's DoD is fully implemented before quality review. |
| `clean-code-reviewer` | `./subagents/clean-code-reviewer.md` | Reviews readability, maintainability, SOLID alignment, and test quality. |
| `architecture-reviewer` | `./subagents/architecture-reviewer.md` | Reviews domain boundaries, composition, and architectural fit. |
| `security-auditor` | `./subagents/security-auditor.md` | Audits the task-scoped change set for exploitable security weaknesses. |

Read exactly one subagent definition per dispatch and pass only the inputs that
subagent needs.

## How This Skill Works

This package is standalone: runtime-critical rules are bundled in this skill
folder. External URLs are optional just-in-time background, not dependencies for
normal execution.

Use progressive disclosure:

1. Keep this file as the routing layer.
2. Read one reference file only when the current phase needs it.
3. Read one subagent file only when dispatching that specialist.
4. Have subagents load their report template only when returning output.
5. Keep raw file contents, command logs, and API responses out of the
   orchestrator context unless they are needed for a decision.

## Progressive Loading Map

| Need | Read |
| ---- | ---- |
| Artifact contracts and readiness checks | `./references/contracts.md` |
| Normal execution flow and fix-loop order | `./references/pipeline.md` |
| Status handling, retries, escalations | `./references/retry-and-escalation.md` |
| Shared reviewer expectations | `./references/review-gate-policy.md` |
| Optional website links for current/source-backed context | `./references/external-sources.md` |
| Dispatch and targeted-fix examples | `./references/examples.md` |
| Final user report template | `./references/template-final-report.md` |

Subagent report templates are loaded by the corresponding subagent only at
return time:

| Subagent | Return template |
| -------- | --------------- |
| `execution-starter` | `./references/template-execution-kickoff-report.md` |
| `task-executor` | `./references/template-execution-report.md` |
| `documentation-writer` | `./references/template-documentation-report.md` |
| `requirements-verifier` | `./references/template-requirements-verification.md` |
| `clean-code-reviewer` | `./references/template-code-quality-review.md` |
| `architecture-reviewer` | `./references/template-architecture-review.md` |
| `security-auditor` | `./references/template-security-audit.md` |

When `documentation-writer` runs in `FINALIZE_TRACKER` mode, it uses
`./references/template-documentation-report.md` and returns that report as
`FINAL_TRACKING_REPORT`.

## Execution Steps

1. Read `./references/contracts.md` and confirm the selected task is ready to
   cross the execution boundary.
2. Read `./references/pipeline.md` and follow its phase order.
3. Dispatch only the next required subagent with explicit inputs.
4. Keep only structured summaries in orchestration context.
5. On blockers, missing prerequisites, or failing gates, read the recovery
   reference and retry only with new context, a fix brief, or an explicit user
   decision while staying within the retry budget.
6. Stop after the selected task completes, blocks, needs user input, or
   escalates; do not auto-continue.

## Output Contract

Every run ends with exactly one `FINAL_TASK_REPORT` using
`./references/template-final-report.md`. Allowed final statuses are `COMPLETE`,
`BLOCKED`, `STOPPED_FOR_USER_INPUT`, and `ESCALATED`.

On `COMPLETE`, the workflow produces Category B implementation changes, updates
Category A tracking artifacts on disk, records eligible GitHub startup updates
or skips, finalizes eligible GitHub completion updates only after requirements
and quality gates pass, and includes the quality-gate summary and
implementation artifact summary expected by the parent orchestrator.

Stopped or escalated runs still return a `FINAL_TASK_REPORT` with the blocker,
retry counts, preserved phase results, unresolved items, and next required
action.

## Operating Constraints

- Execute one task per invocation.
- Treat the task plan and decisions file as the source of truth.
- Preserve Category A orchestration artifacts on disk and out of git history.
- Keep fix cycles targeted: re-run only failing verification or review steps,
  with at most three attempts for requirements and each quality gate.
- Retry a stopped step only when the inputs changed through new context, a fix
  brief, or an explicit user decision.
- Defer final GitHub completion comments or closure until requirements
  verification and all quality gates have passed.
- Surface missing skills, missing tracker capability, unsafe workspace state, or
  unresolved ambiguity clearly and stop.

## Example

Input: `ISSUE_SLUG=acme-app-42`, `TASK_NUMBER=3`

1. Validate required artifacts with `./references/contracts.md`.
2. Dispatch `execution-starter`; continue only on `KICKOFF_REPORT -> READY`.
3. Dispatch implementation, documentation, verification, review gates, and
   final tracker completion in `./references/pipeline.md` order.
4. Report only Task 3 as a `FINAL_TASK_REPORT` using
   `./references/template-final-report.md`.

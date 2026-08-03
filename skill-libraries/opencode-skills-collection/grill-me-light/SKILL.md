---
name: "grill-me-light"
description: "Run a short grilling pass on a plan or design. Use when the user explicitly wants a lighter or faster version of Grill Me that focuses only on the highest-leverage questions."
argument-hint: "<plan-or-design>"
disable-model-invocation: true
user-invocable: true
---

# Grill Me Light

Stress-test a plan or design quickly. Focus on the few decisions that materially change the outcome.

## Core Rules

- Ask one question at a time.
- For every question, provide your recommended answer.
- Focus only on high-leverage decisions.
- Resolve upstream decisions before downstream details.
- If a question can be answered by exploring the codebase or artifacts, inspect them instead of asking.
- Do not try to exhaust every edge case in one session.
- Stop when the remaining questions are mostly about naming, internal structure, polish, or minor edge cases.
- End with a short synthesis and ask whether the user wants a deeper round.

## Flow

1. Restate the plan in operational terms.
2. Identify the highest-leverage unresolved decision.
3. Ask exactly one question about that decision.
4. Provide the recommended answer immediately after the question.
5. Wait for the user's answer before moving on.
6. After each answer, decide whether another high-leverage question remains.
7. Stop once the remaining gaps are mostly low-impact refinement rather than decisions that change scope, architecture, interfaces, migration risk, or acceptance criteria.
8. End with a short synthesis:
   - decisions now locked
   - the biggest remaining risk or ambiguity
   - one suggested follow-up area if the user wants to go deeper

## What to Prioritize

- Goals, constraints, and success criteria before implementation details
- Choices that are expensive or painful to change later
- External interfaces, data contracts, and invariants before internal structure
- Failure modes, rollback paths, migrations, observability, and testing early
- Ambiguity, overloaded terms, and hidden assumptions
- Questions whose answers constrain the most later decisions

## Codebase-First Rule

Before asking about existing behavior, architecture, naming, integrations, schema, or conventions, inspect the repository and answer from evidence when possible.

Only ask the user when the answer depends on intent, priority, product tradeoffs, or missing external context.

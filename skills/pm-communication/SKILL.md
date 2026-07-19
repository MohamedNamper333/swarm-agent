---
name: pm-communication
description: Manages project communication plans, status reporting, and information distribution. Use when creating communication plans, writing status reports, or managing project information flow.
license: MIT
compatibility: opencode
metadata:
  author: https://github.com/opencode
  version: "1.0.0"
  domain: project-management
  triggers:
    - "communication plan"
    - "status report"
    - "RACI"
    - "escalation"
    - "stakeholder communication"
    - "meeting cadence"
  role: specialist
  scope: implementation
  output-format: code
---

# Communication Management

## Communication Plan
| Stakeholder | Info Needed | Frequency | Channel | Owner |
|---|---|---|---|---|
| Exec Sponsor | Status, risks, decisions | Monthly | Meeting + Report | PM |
| Team | Tasks, blockers | Daily | Standup | Tech Lead |
| Client | Progress, demos | Bi-weekly | Demo + Email | PM |

## Status Reports
- **Executive**: 1-page, traffic lights, key decisions needed
- **Detailed**: accomplishments, next steps, risks, metrics
- **Dashboard**: burn rate, milestone progress, risk heatmap

## Meeting Types
- **Daily standup**: 15min, what we did / will do / blockers
- **Weekly sync**: 30min, progress review, decisions
- **SteerCo**: monthly, strategic decisions, approvals
- **Retro**: end of sprint/phase, what went well/improve

## RACI Matrix
- **R**esponsible: does the work
- **A**ccountable: owns the result (only 1 per task)
- **C**onsulted: provides input before decision
- **I**nformed: told after decision

## Escalation Matrix
- Level 1: PM resolves within team
- Level 2: Tech Lead / Product Manager
- Level 3: Executive Sponsor
- Level 4: Steering Committee

## When to Use This Skill

- You are starting a new project and need to define who gets what information, how often, and through which channel
- Stakeholders are complaining about too many meetings, too few meetings, or the wrong people in the room
- You need to produce a concise, audience-appropriate status report for executives, the team, or the client
- Confusion about who decides, who does the work, or who needs to be consulted is causing rework or delays

## Key Capabilities

- Designs a complete communication plan mapping each stakeholder group to the information they need, delivery frequency, channel, and owner
- Produces three tiers of status reports — executive (1-page with traffic lights), detailed (with metrics), and dashboard (visual burn/milestone/risk views)
- Defines meeting cadences and formats for standups, weekly syncs, steerco, and retrospectives with clear outcomes for each
- Builds RACI matrices that eliminate ambiguity around who is Responsible, Accountable, Consulted, and Informed for every task
- Creates an escalation matrix with defined levels so issues route to the right decision-maker without delay

## Best Practices

- Tailor the depth and frequency of communication to the stakeholder's level of involvement — executives need signals, not detail; the team needs the opposite
- Review and update the communication plan at each project phase or when stakeholder changes occur; stale plans cause information gaps
- Keep status reports actionable: end every report with a clear list of decisions needed and the deadline for each

---
name: pm-resource
description: Manages resource allocation, capacity planning, team loading, and utilization. Use when assigning people, planning capacity, leveling resources, or optimizing team utilization.
license: MIT
compatibility: opencode
metadata:
  author: https://github.com/opencode
  version: "1.0.0"
  domain: project-management
  triggers:
    - "resource allocation"
    - "capacity planning"
    - "team loading"
    - "utilization"
    - "resource leveling"
    - "skills gap"
  role: specialist
  scope: implementation
  output-format: code
---

# Resource Management

## Resource Allocation
- Identify required roles and skills per task
- Map available people with skills, rate, availability
- Assign based on: skill match > availability > cost
- Track allocation % (no one > 100%)

## Capacity Planning
- **Demand**: total hours needed per week/role
- **Capacity**: total hours available per person (6h productive/day)
- **Gap**: demand - capacity (positive = overallocation)
- **Plan**: hire, shift, resequence, or descope

## Resource Leveling
- Resolve overallocation by delaying tasks within float
- Prioritize critical path tasks first
- Smooth peaks by using available float
- Document resource constraints as risks

## Utilization Metrics
- Billable vs non-billable ratio
- Bench time (allocated but not assigned)
- Overtime trends (sustainability warning)
- Skills gap analysis

## Tools
- RACI matrix per task/deliverable
- Skills inventory with proficiency levels
- Capacity heatmap (weekly view)
- Resource request / deallocation process

## When to Use This Skill

- You are building a project schedule and need to match the right people to the right tasks based on skills, availability, and cost
- Team members are consistently overallocated or underutilized and you need a systematic way to balance the load
- You are planning a new phase or sprint and need to confirm that sufficient capacity exists before committing to the scope
- You want to identify skills gaps in the team and make informed decisions about hiring, training, or contractor support

## Key Capabilities

- Matches people to tasks using a weighted priority of skill-match, availability, and cost to ensure the right person is assigned
- Computes demand vs capacity by role and week, surfacing gaps as early warnings before they become schedule problems
- Performs resource leveling by delaying non-critical tasks within available float to resolve overallocation without impacting the critical path
- Tracks billable ratio, bench time, overtime trends, and skills gaps to give a complete picture of team health and utilization
- Provides ready-to-use templates for RACI matrices, skills inventories, capacity heatmaps, and resource request workflows

## Best Practices

- Never allocate any person beyond 100% — sustained overallocation is the single fastest way to burn out a team and destroy morale
- Use a productive capacity of 6 hours per person per day (not 8) to account for meetings, admin, context-switching, and cognitive breaks
- Revisit the resource plan whenever scope changes or a new phase begins; resource assumptions that were valid at kickoff rarely survive first contact with reality

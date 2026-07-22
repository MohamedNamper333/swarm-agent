# SWARM MEMORY PROTOCOL
## Structured Handoff Between Pipeline Stages

### Core Principle
Every stage produces a **structured artifact** that the next stage consumes — no implicit context, no loss.

---

### Stage Artifacts (Required Outputs)

| Stage | Input | Output | Format |
|-------|-------|--------|--------|
| 1: Plan | Task | `strategic_plan.md` | Markdown + YAML frontmatter |
| 2: Design | strategic_plan.md | `implementation_plan.md` | Markdown + YAML |
| 3: Execute | implementation_plan.md | `execution_log.jsonl` | JSON Lines |
| 4: Verify | execution_log.jsonl | `quality_report.md` | Markdown + YAML |
| 5: Improve | quality_report.md | `improvement_report.md` | Markdown + YAML |
| 6: Handoff | All above | `handoff_package.md` | Markdown + YAML |

---

### Artifact Schema (YAML Frontmatter)

```yaml
---
stage: 1                    # pipeline stage number
task_id: "swarm-2025-001"   # unique task identifier
timestamp: "2025-07-22T10:30:00Z"
complexity_score: 45        # 0-100
pipeline: "STANDARD"        # LITE|STANDARD|FULL
constitutional_pass: true   # stage 4+ only
---
```

---

### Handoff Protocol (Between Stages)

```python
def handoff(from_stage, to_stage, artifact_path):
    # 1. Validate artifact exists and schema correct
    # 2. Extract key decisions for next stage
    # 3. Write handoff summary to `handoff_log.md`
    # 4. Next stage reads artifact + handoff_log
    pass
```

### Context Persistence (Across Sessions)

```yaml
# project_context.yaml (root of workspace)
project_id: "swarm-project-xyz"
current_stage: 3
task_stack:
  - id: "task-001"
    stage: 3
    status: "executing"
    artifact: "execution_log.jsonl"
```

---

### Obsidian Integration (Memory Layer)

When Obsidian MCP available:

```markdown
# In Obsidian vault:
/swarm/
  /project-{id}/
    strategic_plan.md      ← Stage 1
    implementation_plan.md ← Stage 2
    execution_log.jsonl    ← Stage 3 (append-only)
    quality_report.md      ← Stage 4
    improvement_report.md  ← Stage 5
    handoff_package.md     ← Stage 6
    project_context.yaml   ← Session persistence
```

### Skills: `context-restore`, `context-save`, `hierarchical-agent-memory`

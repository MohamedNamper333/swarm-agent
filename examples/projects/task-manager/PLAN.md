# Task Manager CLI — Implementation Plan

**Date:** 2025-07-22
**Pipeline:** STANDARD (4 stages)
**Complexity:** ~35/100

## Requirements
- Python CLI with 4 commands: `add`, `list`, `complete`, `delete`
- SQLite for persistence (stdlib `sqlite3`)
- Comprehensive test suite with `pytest`
- Obsidian-compatible output artifacts

## Data Model

```sql
CREATE TABLE tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    completed BOOLEAN NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Architecture

```
task-manager/
├── task_manager.py      # Core DB logic (add, list, complete, delete)
├── cli.py               # argparse CLI entry point
├── test_task_manager.py  # pytest test suite
├── PLAN.md              # This file
└── README.md            # Usage documentation
```

## Commands

| Command    | Args           | Description                    |
|------------|----------------|--------------------------------|
| `add`      | `--title`      | Add a new task                 |
| `list`     | `--all`        | List all tasks (optional flag) |
| `complete` | `--id`         | Mark task as completed         |
| `delete`   | `--id`         | Delete a task by ID            |

## Design Decisions
1. **Separation of concerns**: DB logic in `task_manager.py`, CLI parsing in `cli.py`
2. **No external dependencies**: Only stdlib (`sqlite3`, `argparse`, `os`, `datetime`)
3. **Database location**: `~/.task_manager/tasks.db` (XDG-friendly default)
4. **Tests**: Use in-memory SQLite for speed, test all CRUD operations + edge cases

## Constitutional Check Criteria
- HONESTY: No fabricated features — implements exactly what's specified
- EVIDENCE: Tests prove correctness
- MINIMAL SURFACE: 2 files + tests, no over-engineering
- REVERSIBILITY: Simple file deletion rolls back everything
- HUMAN AGENCY: All commands require explicit user invocation

# Handoff Package: Task Manager CLI

## Summary
Zero-dependency Python CLI task manager with SQLite persistence. 4 commands, 15 tests, all passing.

## Quick Start
```bash
cp task_manager.py cli.py ~/
python cli.py add --title "My task"
python cli.py list
```

## Files
- task_manager.py — Core logic (TaskManager class)
- cli.py — argparse entry point
- test_task_manager.py — 15 comprehensive tests
- README.md — Usage docs

## Maintenance
- Data: ~/.task_manager/tasks.db (SQLite)
- Schema: CREATE TABLE IF NOT EXISTS (idempotent)
- No migrations needed

## Known Limitations
- No due dates / priorities (v2)
- No categories / tags (v2)
- Single-user, local only
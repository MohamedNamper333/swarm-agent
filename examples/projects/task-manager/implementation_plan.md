# Implementation Plan: Task Manager CLI

## Architecture
- task_manager.py: Core persistence layer (TaskManager class)
- cli.py: argparse entry point with 4 subcommands
- test_task_manager.py: 15 tests covering all operations

## Data Model
Table: tasks
- id (PK, auto)
- title (TEXT, not null)
- completed (INTEGER, 0/1)
- created_at (TIMESTAMP, default now)

## API Contract
TaskManager:
  add(title) -> dict
  list_all() -> list[dict]
  get(id) -> dict | None
  complete(id) -> bool
  delete(id) -> bool
  close() -> None

## Build Order
1. Database schema + TaskManager skeleton
2. CRUD methods (add, list, get)
4. Mutation methods (complete, delete)
5. CLI with 4 subcommands
6. Tests (15 cases)
7. README
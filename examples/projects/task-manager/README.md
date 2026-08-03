# 🗂️ Task Manager CLI

A simple command-line task manager backed by SQLite. No external dependencies — pure Python stdlib.

## Usage

```bash
# Add a task
python cli.py add --title "Buy groceries"

# List pending tasks
python cli.py list

# List all tasks (including completed)
python cli.py list --all

# Mark a task as completed
python cli.py complete --id 1

# Delete a task
python cli.py delete --id 1
```

## Storage

Tasks are persisted in `~/.task_manager/tasks.db` by default.

## Running Tests

```bash
pip install pytest  # if not installed
pytest test_task_manager.py -v
```

## Project Structure

```
task_manager.py       — Core DB logic (add, list, complete, delete, get)
cli.py                — argparse CLI entry point
test_task_manager.py  — Comprehensive pytest test suite
```

## Design Decisions

- **Zero dependencies**: Uses only Python stdlib (`sqlite3`, `argparse`)
- **Separation of concerns**: DB logic is decoupled from CLI
- **In-memory tests**: Tests use temp DBs for speed and isolation
- **Idempotent schema**: `CREATE TABLE IF NOT EXISTS` is safe to run repeatedly

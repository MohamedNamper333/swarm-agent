"""Task Manager — SQLite-backed persistence layer."""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional


DEFAULT_DB_DIR = Path.home() / ".task_manager"
DEFAULT_DB_PATH = DEFAULT_DB_DIR / "tasks.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    completed BOOLEAN NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


class TaskManager:
    """SQLite-backed task manager."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute(SCHEMA)
        self._conn.commit()

    def close(self):
        self._conn.close()

    # ── CRUD ──────────────────────────────────────────────────────

    def add(self, title: str) -> dict:
        """Add a new task. Returns the created task as a dict."""
        cur = self._conn.execute(
            "INSERT INTO tasks (title) VALUES (?)", (title,)
        )
        self._conn.commit()
        return self.get(cur.lastrowid)

    def list_all(self) -> list[dict]:
        """Return all tasks, ordered by creation date."""
        rows = self._conn.execute(
            "SELECT * FROM tasks ORDER BY created_at DESC, id DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    def get(self, task_id: int) -> Optional[dict]:
        """Get a single task by ID."""
        row = self._conn.execute(
            "SELECT * FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
        return dict(row) if row else None

    def complete(self, task_id: int) -> Optional[dict]:
        """Mark a task as completed. Returns the updated task or None."""
        task = self.get(task_id)
        if task is None:
            return None
        self._conn.execute(
            "UPDATE tasks SET completed = 1 WHERE id = ?", (task_id,)
        )
        self._conn.commit()
        return self.get(task_id)

    def delete(self, task_id: int) -> bool:
        """Delete a task by ID. Returns True if deleted, False if not found."""
        task = self.get(task_id)
        if task is None:
            return False
        self._conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        self._conn.commit()
        return True


def get_manager(db_path: Optional[Path] = None) -> TaskManager:
    """Factory function to create a TaskManager instance."""
    return TaskManager(db_path)

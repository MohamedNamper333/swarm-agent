"""Tests for Task Manager — runs against in-memory SQLite."""

import pytest
from pathlib import Path

from task_manager import TaskManager


@pytest.fixture
def manager(tmp_path: Path) -> TaskManager:
    """Create a fresh TaskManager with a temp DB for each test."""
    db = tmp_path / "test_tasks.db"
    mgr = TaskManager(db_path=db)
    yield mgr
    mgr.close()


class TestAdd:
    def test_add_returns_task(self, manager: TaskManager):
        task = manager.add("Buy groceries")
        assert task["id"] is not None
        assert task["title"] == "Buy groceries"
        assert task["completed"] == 0

    def test_add_multiple(self, manager: TaskManager):
        t1 = manager.add("Task 1")
        t2 = manager.add("Task 2")
        assert t1["id"] != t2["id"]

    def test_add_empty_title(self, manager: TaskManager):
        # SQLite allows empty strings unless CHECK constraint exists
        task = manager.add("")
        assert task["title"] == ""


class TestList:
    def test_list_empty(self, manager: TaskManager):
        assert manager.list_all() == []

    def test_list_returns_all(self, manager: TaskManager):
        manager.add("A")
        manager.add("B")
        tasks = manager.list_all()
        assert len(tasks) == 2

    def test_list_order_by_created_desc(self, manager: TaskManager):
        t1 = manager.add("First")
        t2 = manager.add("Second")
        tasks = manager.list_all()
        # Most recent first
        assert tasks[0]["id"] in (t1["id"], t2["id"])
        assert tasks[1]["id"] == t1["id"]


class TestComplete:
    def test_complete_existing(self, manager: TaskManager):
        task = manager.add("Do laundry")
        result = manager.complete(task["id"])
        assert result["completed"] == 1

    def test_complete_nonexistent(self, manager: TaskManager):
        result = manager.complete(9999)
        assert result is None

    def test_complete_already_done(self, manager: TaskManager):
        task = manager.add("Already done")
        manager.complete(task["id"])
        result = manager.complete(task["id"])
        assert result["completed"] == 1


class TestDelete:
    def test_delete_existing(self, manager: TaskManager):
        task = manager.add("Ephemeral")
        assert manager.delete(task["id"]) is True
        assert manager.get(task["id"]) is None

    def test_delete_nonexistent(self, manager: TaskManager):
        assert manager.delete(9999) is False

    def test_delete_does_not_affect_others(self, manager: TaskManager):
        t1 = manager.add("Keep")
        t2 = manager.add("Remove")
        manager.delete(t2["id"])
        assert manager.get(t1["id"]) is not None
        assert manager.get(t2["id"]) is None


class TestGet:
    def test_get_existing(self, manager: TaskManager):
        task = manager.add("Find me")
        found = manager.get(task["id"])
        assert found["title"] == "Find me"

    def test_get_nonexistent(self, manager: TaskManager):
        assert manager.get(9999) is None


class TestPersistence:
    def test_data_persists(self, tmp_path: Path):
        db = tmp_path / "persist.db"
        mgr1 = TaskManager(db_path=db)
        mgr1.add("Persistent task")
        mgr1.close()

        mgr2 = TaskManager(db_path=db)
        tasks = mgr2.list_all()
        assert len(tasks) == 1
        assert tasks[0]["title"] == "Persistent task"
        mgr2.close()

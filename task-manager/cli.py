#!/usr/bin/env python3
"""Task Manager CLI — add, list, complete, delete tasks via SQLite."""

import argparse
import sys
from pathlib import Path

from task_manager import TaskManager, get_manager


def format_task(task: dict) -> str:
    """Format a single task for display."""
    status = "✅" if task["completed"] else "⬜"
    return f"  [{task['id']}] {status} {task['title']}"


def cmd_add(args: argparse.Namespace, manager: TaskManager) -> int:
    task = manager.add(args.title)
    print(f"✅ Task #{task['id']} added: {task['title']}")
    return 0


def cmd_list(args: argparse.Namespace, manager: TaskManager) -> int:
    tasks = manager.list_all()
    if not tasks:
        print("📋 No tasks yet. Add one with: task-manager add --title \"My Task\"")
        return 0

    header = "📋 All Tasks" if args.all else "📋 Pending Tasks"
    print(header)
    print("─" * 40)

    shown = 0
    for task in tasks:
        if args.all or not task["completed"]:
            print(format_task(task))
            shown += 1

    if shown == 0:
        print("  (all tasks completed! 🎉)")
    else:
        print(f"\n  Total: {shown}")
    return 0


def cmd_complete(args: argparse.Namespace, manager: TaskManager) -> int:
    task = manager.complete(args.id)
    if task is None:
        print(f"❌ Task #{args.id} not found.")
        return 1
    print(f"✅ Task #{task['id']} completed: {task['title']}")
    return 0


def cmd_delete(args: argparse.Namespace, manager: TaskManager) -> int:
    success = manager.delete(args.id)
    if not success:
        print(f"❌ Task #{args.id} not found.")
        return 1
    print(f"🗑️  Task #{args.id} deleted.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="task-manager",
        description="Simple task manager with SQLite persistence.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # add
    p_add = sub.add_parser("add", help="Add a new task")
    p_add.add_argument("--title", "-t", required=True, help="Task title")

    # list
    p_list = sub.add_parser("list", help="List tasks")
    p_list.add_argument(
        "--all", "-a", action="store_true", help="Show completed tasks too"
    )

    # complete
    p_complete = sub.add_parser("complete", help="Mark a task as completed")
    p_complete.add_argument("--id", type=int, required=True, help="Task ID")

    # delete
    p_delete = sub.add_parser("delete", help="Delete a task")
    p_delete.add_argument("--id", type=int, required=True, help="Task ID")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    manager = get_manager()
    try:
        commands = {
            "add": cmd_add,
            "list": cmd_list,
            "complete": cmd_complete,
            "delete": cmd_delete,
        }
        return commands[args.command](args, manager)
    finally:
        manager.close()


if __name__ == "__main__":
    sys.exit(main())

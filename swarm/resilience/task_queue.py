"""Priority task queue with persistence.

Provides reliable task scheduling for the swarm:
- Tasks are JSON-serializable (callable references are by name; payload by data)
- Priority ordering (CRITICAL > HIGH > NORMAL > LOW > BACKGROUND)
- Persistent storage survives restarts
- Atomic enqueue/dequeue with file locking
- Status tracking (pending -> running -> completed/failed/cancelled)
- Dead-letter handling for permanent failures

Persistence uses atomic file writes (write-temp + os.replace) so a crash
during enqueue never leaves a corrupt queue.
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Union


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    DEAD_LETTER = "dead_letter"


class QueueStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    RECOVERING = "recovering"


PRIORITY_RANK = {
    "critical": 0,
    "high": 1,
    "normal": 2,
    "low": 3,
    "background": 4,
}


@dataclass
class QueueItem:
    """A task in the queue with metadata."""
    id: str
    task_type: str
    payload: Dict[str, Any]
    priority: str = "normal"
    status: str = "pending"
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    attempts: int = 0
    max_attempts: int = 3
    last_error: Optional[str] = None
    created_by: Optional[str] = None
    assigned_to: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QueueItem":
        return cls(**data)

    def priority_rank(self) -> int:
        return PRIORITY_RANK.get(self.priority, 2)


class _FileLock:
    """Cross-platform advisory file lock via O_EXCL on lockfile."""
    def __init__(self, path: Path):
        self.path = path
        self._fd: Optional[int] = None

    def acquire(self, timeout: float = 5.0, poll: float = 0.05) -> None:
        start = time.monotonic()
        while True:
            try:
                self._fd = os.open(
                    str(self.path),
                    os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                )
                os.write(self._fd, f"{os.getpid()}\n".encode())
                return
            except FileExistsError:
                if time.monotonic() - start > timeout:
                    raise TimeoutError(f"could not acquire lock {self.path}")
                time.sleep(poll)

    def release(self) -> None:
        if self._fd is not None:
            try:
                os.close(self._fd)
            finally:
                self._fd = None
                try:
                    os.unlink(self.path)
                except FileNotFoundError:
                    pass

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()


class PriorityQueue:
    """In-memory priority queue backend (storage=None).

    Not thread-safe on its own; the TaskQueue wrapper adds locking.
    """

    def __init__(self):
        self._items: List[QueueItem] = []

    def push(self, item: QueueItem) -> None:
        # Insert in priority order; stable by created_at then id
        key = (item.priority_rank(), item.created_at, item.id)
        i = 0
        while i < len(self._items):
            ek = (self._items[i].priority_rank(), self._items[i].created_at, self._items[i].id)
            if key < ek:
                break
            i += 1
        self._items.insert(i, item)

    def pop(self) -> Optional[QueueItem]:
        if not self._items:
            return None
        return self._items.pop(0)

    def peek(self) -> Optional[QueueItem]:
        return self._items[0] if self._items else None

    def remove(self, item_id: str) -> bool:
        for i, item in enumerate(self._items):
            if item.id == item_id:
                del self._items[i]
                return True
        return False

    def __len__(self) -> int:
        return len(self._items)

    def all(self) -> List[QueueItem]:
        return list(self._items)


class TaskQueue:
    """Persistent priority task queue.

    - Persistence path: <storage_path>/queue.jsonl (JSONL = one item per line)
    - Locking: file lock for multi-process safety; threading lock for in-process
    - Recovery on load: items in `running` status are reset to `pending` (crash safety)
    """

    def __init__(
        self,
        storage_path: Union[str, Path],
        lock_timeout_seconds: float = 5.0,
    ):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._queue_file = self.storage_path / "queue.jsonl"
        self._lock_file = self.storage_path / "queue.lock"
        self._history_file = self.storage_path / "history.jsonl"
        self._lock = threading.Lock()
        self._file_lock = _FileLock(self._lock_file)
        self._lock_timeout = lock_timeout_seconds
        self._queue = PriorityQueue()
        self._status = QueueStatus.HEALTHY
        self._load()

    def _read_jsonl(self, path: Path) -> Iterator[QueueItem]:
        if not path.exists():
            return
        try:
            with path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        yield QueueItem.from_dict(data)
                    except (json.JSONDecodeError, TypeError, KeyError):
                        # Skip corrupted lines — log but don't crash
                        continue
        except OSError:
            return

    def _load(self) -> None:
        """Load pending tasks from disk; reset 'running' to 'pending' (recovery)."""
        recovered_running = 0
        try:
            with self._file_lock:
                items = list(self._read_jsonl(self._queue_file))
                for item in items:
                    if item.status == TaskStatus.RUNNING.value:
                        # Crashed while running — recover as pending
                        item.status = TaskStatus.PENDING.value
                        item.attempts += 1
                        recovered_running += 1
                    self._queue.push(item)
            if recovered_running > 0:
                self._status = QueueStatus.RECOVERING
        except (OSError, TimeoutError):
            self._status = QueueStatus.DEGRADED

    def _write_atomic(self, path: Path, content: str) -> None:
        """Write content to a temp file in the same directory, then atomically replace."""
        dirpath = path.parent
        dirpath.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(
            prefix=f".{path.name}.", suffix=".tmp", dir=str(dirpath)
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
            os.replace(tmp_path, str(path))
        except Exception:
            try:
                os.unlink(tmp_path)
            except FileNotFoundError:
                pass
            raise

    def _persist(self) -> None:
        """Persist all items currently in memory back to disk."""
        lines = []
        for item in self._queue.all():
            lines.append(json.dumps(item.to_dict()))
        content = "\n".join(lines) + ("\n" if lines else "")
        with self._file_lock:
            self._write_atomic(self._queue_file, content)

    def _append_history(self, item: QueueItem) -> None:
        try:
            with self._file_lock:
                line = json.dumps({
                    **item.to_dict(),
                    "final_status": item.status,
                }) + "\n"
                with self._history_file.open("a", encoding="utf-8") as f:
                    f.write(line)
        except OSError:
            # History is best-effort — never block queue operations
            pass

    def enqueue(
        self,
        task_type: str,
        payload: Dict[str, Any],
        priority: str = "normal",
        max_attempts: int = 3,
        created_by: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        item_id: Optional[str] = None,
    ) -> QueueItem:
        if priority not in PRIORITY_RANK:
            raise ValueError(f"invalid priority '{priority}'; must be one of {list(PRIORITY_RANK)}")
        item = QueueItem(
            id=item_id or str(uuid.uuid4()),
            task_type=task_type,
            payload=payload,
            priority=priority,
            max_attempts=max_attempts,
            created_by=created_by,
            metadata=metadata or {},
        )
        with self._lock:
            self._queue.push(item)
            self._persist()
        return item

    def dequeue(self) -> Optional[QueueItem]:
        """Pop the highest-priority pending item and mark it RUNNING."""
        with self._lock:
            item = self._queue.pop()
            if item is None:
                return None
            item.status = TaskStatus.RUNNING.value
            item.started_at = time.time()
            item.attempts += 1
            item.assigned_to = item.assigned_to or "unknown"
            # Put back so it stays in memory until completion
            self._queue.push(item)
            self._persist()
        return item

    def peek(self) -> Optional[QueueItem]:
        with self._lock:
            return self._queue.peek()

    def complete(self, item_id: str, result: Optional[Dict[str, Any]] = None) -> bool:
        """Mark item COMPLETED and archive it (remove from active queue)."""
        with self._lock:
            for item in self._queue.all():
                if item.id == item_id:
                    item.status = TaskStatus.COMPLETED.value
                    item.completed_at = time.time()
                    if result is not None:
                        item.metadata["result"] = result
                    self._append_history(item)
                    self._queue.remove(item_id)
                    self._persist()
                    return True
            return False

    def fail(self, item_id: str, error: str, dead_letter: bool = False) -> bool:
        """Mark item FAILED. If attempts < max_attempts, requeue as PENDING.
        Otherwise move to DEAD_LETTER.
        """
        with self._lock:
            for item in self._queue.all():
                if item.id == item_id:
                    item.last_error = error
                    item.status = TaskStatus.FAILED.value
                    item.completed_at = time.time()
                    self._queue.remove(item_id)
                    if dead_letter or item.attempts >= item.max_attempts:
                        item.status = TaskStatus.DEAD_LETTER.value
                        self._append_history(item)
                    else:
                        # Requeue for retry
                        item.status = TaskStatus.PENDING.value
                        item.started_at = None
                        self._queue.push(item)
                    self._persist()
                    return True
            return False

    def cancel(self, item_id: str) -> bool:
        with self._lock:
            for item in self._queue.all():
                if item.id == item_id:
                    item.status = TaskStatus.CANCELLED.value
                    item.completed_at = time.time()
                    self._queue.remove(item_id)
                    self._append_history(item)
                    self._persist()
                    return True
            return False

    def get(self, item_id: str) -> Optional[QueueItem]:
        with self._lock:
            for item in self._queue.all():
                if item.id == item_id:
                    return item
            return None

    def list(
        self,
        status: Optional[TaskStatus] = None,
        priority: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[QueueItem]:
        with self._lock:
            items = list(self._queue.all())
        if status is not None:
            items = [i for i in items if i.status == status.value]
        if priority is not None:
            items = [i for i in items if i.priority == priority]
        if limit is not None:
            items = items[:limit]
        return items

    def size(self) -> int:
        with self._lock:
            return len(self._queue)

    def status_breakdown(self) -> Dict[str, int]:
        with self._lock:
            counts: Dict[str, int] = {}
            for item in self._queue.all():
                counts[item.status] = counts.get(item.status, 0) + 1
        return counts

    def get_status(self) -> QueueStatus:
        return self._status

    def mark_healthy(self) -> None:
        self._status = QueueStatus.HEALTHY

    def get_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        if not self._history_file.exists():
            return items
        try:
            with self._history_file.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        items.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        except OSError:
            return []
        return items[-limit:]

    def clear(self) -> None:
        """Remove all items (active + history). For testing only."""
        with self._lock:
            self._queue = PriorityQueue()
            with self._file_lock:
                if self._queue_file.exists():
                    self._queue_file.unlink()
                if self._history_file.exists():
                    self._history_file.unlink()

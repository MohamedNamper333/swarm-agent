"""
Event Logger Module - JSONL Structured Logging
Records all swarm events as structured JSON Lines for easy parsing.
"""
import json
import time
import logging
import threading
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import defaultdict

logger = logging.getLogger(__name__)


class LogLevel(Enum):
    """Log levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class EventCategory(Enum):
    """Event categories"""
    SYSTEM = "system"
    TASK = "task"
    AGENT = "agent"
    MODEL = "model"
    API = "api"
    SECURITY = "security"
    RECOVERY = "recovery"
    CUSTOM = "custom"


@dataclass
class LogEvent:
    """Structured log event"""
    timestamp: str
    level: str
    category: str
    event_type: str
    message: str
    source: str = "swarm"
    actor: Optional[str] = None
    task_id: Optional[str] = None
    agent_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LoggerStats:
    """Logger statistics"""
    total_events: int = 0
    events_by_level: Dict[str, int] = field(default_factory=dict)
    events_by_category: Dict[str, int] = field(default_factory=dict)
    last_event_time: Optional[str] = None


class EventLogger:
    """
    JSONL structured event logger.
    Writes events as one JSON object per line for easy parsing.
    """

    def __init__(
        self,
        log_file: str = "swarm/observability/events.jsonl",
        max_file_size_mb: int = 100,
        backup_count: int = 5
    ):
        self.log_path = Path(log_file)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

        self.max_file_size = max_file_size_mb * 1024 * 1024
        self.backup_count = backup_count

        self.events_buffer: List[LogEvent] = []
        self.buffer_size = 100
        self.stats = LoggerStats()

        # Initialize level/category counters
        for level in LogLevel:
            self.stats.events_by_level[level.value] = 0
        for cat in EventCategory:
            self.stats.events_by_category[cat.value] = 0

        self._ensure_log_file()

    def _ensure_log_file(self) -> None:
        """Ensure log file exists"""
        if not self.log_path.exists():
            self.log_path.touch()

    def _rotate_if_needed(self) -> None:
        """Rotate log file if too large"""
        if self.log_path.stat().st_size < self.max_file_size:
            return
        # Rotate: move to .1, .2, etc.
        for i in range(self.backup_count - 1, 0, -1):
            old = self.log_path.with_suffix(f".jsonl.{i}")
            new = self.log_path.with_suffix(f".jsonl.{i+1}")
            if old.exists():
                if i + 1 >= self.backup_count:
                    old.unlink()
                else:
                    old.rename(new)
        self.log_path.rename(self.log_path.with_suffix(".jsonl.1"))

    def log(
        self,
        level: LogLevel,
        category: EventCategory,
        event_type: str,
        message: str,
        source: str = "swarm",
        actor: Optional[str] = None,
        task_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> LogEvent:
        """Log a structured event"""
        with self._lock:
            event = LogEvent(
                timestamp=datetime.now(timezone.utc).isoformat(),
                level=level.value,
                category=category.value,
                event_type=event_type,
                message=message,
                source=source,
                actor=actor,
                task_id=task_id,
                agent_id=agent_id,
                metadata=metadata or {}
            )

            self.events_buffer.append(event)
            self.stats.total_events += 1
            self.stats.events_by_level[level.value] = self.stats.events_by_level.get(level.value, 0) + 1
            self.stats.events_by_category[category.value] = self.stats.events_by_category.get(category.value, 0) + 1
            self.stats.last_event_time = event.timestamp

            if len(self.events_buffer) >= self.buffer_size:
                self._flush()

            return event

    def debug(self, category: EventCategory, event_type: str, message: str, **kwargs) -> LogEvent:
        return self.log(LogLevel.DEBUG, category, event_type, message, **kwargs)

    def info(self, category: EventCategory, event_type: str, message: str, **kwargs) -> LogEvent:
        return self.log(LogLevel.INFO, category, event_type, message, **kwargs)

    def warning(self, category: EventCategory, event_type: str, message: str, **kwargs) -> LogEvent:
        return self.log(LogLevel.WARNING, category, event_type, message, **kwargs)

    def error(self, category: EventCategory, event_type: str, message: str, **kwargs) -> LogEvent:
        return self.log(LogLevel.ERROR, category, event_type, message, **kwargs)

    def critical(self, category: EventCategory, event_type: str, message: str, **kwargs) -> LogEvent:
        return self.log(LogLevel.CRITICAL, category, event_type, message, **kwargs)

    def _flush(self) -> None:
        """Flush buffered events to disk"""
        if not self.events_buffer:
            return
        try:
            self._rotate_if_needed()
            with open(self.log_path, "a") as f:
                for event in self.events_buffer:
                    f.write(json.dumps(asdict(event), default=str) + "\n")
            self.events_buffer.clear()
        except Exception as e:
            logger.error(f"Failed to flush events: {e}")

    def query(
        self,
        level: Optional[LogLevel] = None,
        category: Optional[EventCategory] = None,
        event_type: Optional[str] = None,
        agent_id: Optional[str] = None,
        limit: int = 100
    ) -> List[LogEvent]:
        """Query recent events from buffer"""
        with self._lock:
            events = list(self.events_buffer)
            if level:
                events = [e for e in events if e.level == level.value]
            if category:
                events = [e for e in events if e.category == category.value]
            if event_type:
                events = [e for e in events if e.event_type == event_type]
            if agent_id:
                events = [e for e in events if e.agent_id == agent_id]
            return events[-limit:]

    def read_log_file(self, limit: int = 100, offset: int = 0) -> List[LogEvent]:
        """Read events from log file"""
        if not self.log_path.exists():
            return []
        events = []
        try:
            with open(self.log_path, "r") as f:
                lines = f.readlines()
            for line in lines[offset:offset+limit]:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    event = LogEvent(**data)
                    events.append(event)
                except (json.JSONDecodeError, TypeError):
                    continue
        except Exception as e:
            logger.error(f"Failed to read log file: {e}")
        return events

    def get_stats(self) -> Dict[str, Any]:
        """Get logger statistics"""
        with self._lock:
            return {
                "total_events": self.stats.total_events,
                "events_by_level": dict(self.stats.events_by_level),
                "events_by_category": dict(self.stats.events_by_category),
                "buffer_size": len(self.events_buffer),
                "last_event_time": self.stats.last_event_time
            }

    def flush(self) -> None:
        """Force flush buffer"""
        with self._lock:
            self._flush()


# Module-level singleton
_default_logger: Optional[EventLogger] = None


def get_event_logger() -> EventLogger:
    """Get or create the default event logger"""
    global _default_logger
    if _default_logger is None:
        _default_logger = EventLogger()
    return _default_logger
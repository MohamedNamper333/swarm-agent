"""
Recovery Engine Module - Snapshot + Partial Recovery
Manages automatic and manual recovery from errors using snapshots.
"""
import time
import logging
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

from swarm.resilience.snapshot_manager import (
    SnapshotManager, Snapshot, SnapshotStatus, SnapshotType,
    get_snapshot_manager
)

logger = logging.getLogger(__name__)


class RecoveryStrategy(Enum):
    """Strategies for recovery"""
    AUTO_SNAPSHOT = "auto_snapshot"          # Take snapshot before risky op
    RESTORE_LAST = "restore_last"             # Restore last good snapshot
    RESTORE_SPECIFIC = "restore_specific"     # Restore by ID
    PARTIAL_RECOVERY = "partial_recovery"     # Recover specific components
    NO_RECOVERY = "no_recovery"               # Just log error


class RecoveryStatus(Enum):
    """Status of a recovery operation"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class RecoveryPoint:
    """Configuration for a recovery point"""
    id: str
    name: str
    paths: List[str]
    description: str
    snapshot_type: SnapshotType
    auto_create: bool
    retention_hours: int
    created_at: str
    last_used: Optional[str] = None
    use_count: int = 0


@dataclass
class RecoveryEvent:
    """Record of a recovery operation"""
    id: str
    timestamp: str
    strategy: RecoveryStrategy
    status: RecoveryStatus
    snapshot_id: Optional[str]
    trigger: str
    duration_seconds: float
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RecoveryStats:
    """Recovery engine statistics"""
    total_recoveries: int = 0
    successful_recoveries: int = 0
    failed_recoveries: int = 0
    avg_recovery_seconds: float = 0.0
    snapshots_auto_created: int = 0
    snapshots_manually_created: int = 0
    snapshots_used: int = 0


@dataclass
class RecoveryStep:
    """A single step in a recovery plan.

    Attributes:
        id: Unique step identifier
        name: Human-readable step name
        action: Action keyword (e.g., "snapshot.create", "snapshot.restore", "service.restart")
        target: Target resource this step applies to
        timeout_seconds: Maximum time to wait for step completion
        depends_on: Step IDs that must complete successfully before this one runs
        metadata: Extra context
    """
    id: str
    name: str
    action: str
    target: str = ""
    timeout_seconds: float = 30.0
    depends_on: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_ready(self, completed_step_ids: set) -> bool:
        for dep in self.depends_on:
            if dep not in completed_step_ids:
                return False
        return True


@dataclass
class RecoveryPlan:
    """A composed recovery plan: an ordered set of RecoveryStep objects.

    Plans describe how to recover from a failure scenario: which snapshot to
    take, which snapshot to restore, which services to restart, in what
    order, with which dependencies and timeouts.
    """
    id: str
    name: str
    trigger: str
    strategy: RecoveryStrategy
    steps: List[RecoveryStep] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_step(self, step: RecoveryStep) -> None:
        self.steps.append(step)

    def total_timeout(self) -> float:
        return sum(s.timeout_seconds for s in self.steps)

    def execution_order(self) -> List[RecoveryStep]:
        """Topological sort: steps whose dependencies are all earlier in the list."""
        completed: set = set()
        ordered: List[RecoveryStep] = []
        remaining = list(self.steps)
        while remaining:
            progress = False
            for step in list(remaining):
                if step.is_ready(completed):
                    ordered.append(step)
                    completed.add(step.id)
                    remaining.remove(step)
                    progress = True
            if not progress:
                # cycle or missing dep: append rest in original order
                ordered.extend(remaining)
                break
        return ordered


class RecoveryEngine:
    """
    Manages recovery from errors using snapshots.
    Supports auto-snapshot before risky operations and quick restore.
    """

    def __init__(
        self,
        snapshot_manager: Optional[SnapshotManager] = None,
        storage_path: str = "swarm/resilience/recovery"
    ):
        self.snapshot_manager = snapshot_manager or get_snapshot_manager()
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

        self.recovery_points: Dict[str, RecoveryPoint] = {}
        self.recovery_history: List[RecoveryEvent] = []
        self.stats = RecoveryStats()

    def register_recovery_point(
        self,
        name: str,
        paths: List[str],
        description: str = "",
        snapshot_type: SnapshotType = SnapshotType.AUTO,
        auto_create: bool = True,
        retention_hours: int = 24
    ) -> str:
        """Register a recovery point configuration"""
        import uuid
        with self._lock:
            point_id = f"rp-{uuid.uuid4().hex[:8]}"
            point = RecoveryPoint(
                id=point_id,
                name=name,
                paths=paths,
                description=description,
                snapshot_type=snapshot_type,
                auto_create=auto_create,
                retention_hours=retention_hours,
                created_at=datetime.now().isoformat()
            )
            self.recovery_points[point_id] = point

            if auto_create:
                self._create_snapshot_for_point(point_id)

            logger.info(f"Registered recovery point: {name} ({point_id})")
            return point_id

    def _create_snapshot_for_point(self, point_id: str) -> Optional[str]:
        """Create a snapshot for a recovery point"""
        point = self.recovery_points.get(point_id)
        if not point:
            return None
        snapshot_id = self.snapshot_manager.create_snapshot(
            name=f"auto-{point.name}",
            paths=point.paths,
            description=f"Auto-snapshot for recovery point {point.name}",
            snapshot_type=point.snapshot_type
        )
        with self._lock:
            self.stats.snapshots_auto_created += 1
        return snapshot_id

    def snapshot_before(
        self,
        name: str,
        paths: List[str],
        description: str = ""
    ) -> Optional[str]:
        """
        Take a snapshot before a risky operation.
        Returns snapshot ID that can be used to restore.
        """
        with self._lock:
            self.stats.snapshots_manually_created += 1
        try:
            snapshot_id = self.snapshot_manager.create_snapshot(
                name=name,
                paths=paths,
                description=description,
                snapshot_type=SnapshotType.FULL
            )
            logger.info(f"Pre-operation snapshot created: {snapshot_id}")
            return snapshot_id
        except Exception as e:
            logger.error(f"Failed to create pre-operation snapshot: {e}")
            return None

    def recover(
        self,
        snapshot_id: str,
        trigger: str = "manual",
        target_dir: Optional[str] = None,
        overwrite: bool = False
    ) -> RecoveryEvent:
        """
        Recover from a snapshot.
        Returns recovery event with status.
        """
        import uuid
        with self._lock:
            event_id = f"rec-{uuid.uuid4().hex[:8]}"
            self.stats.total_recoveries += 1

        start = time.monotonic()
        event = RecoveryEvent(
            id=event_id,
            timestamp=datetime.now().isoformat(),
            strategy=RecoveryStrategy.RESTORE_SPECIFIC,
            status=RecoveryStatus.IN_PROGRESS,
            snapshot_id=snapshot_id,
            trigger=trigger,
            duration_seconds=0.0
        )

        try:
            success = self.snapshot_manager.restore_snapshot(
                snapshot_id,
                target_dir=target_dir,
                overwrite=overwrite
            )

            elapsed = time.monotonic() - start
            event.duration_seconds = elapsed

            if success:
                event.status = RecoveryStatus.COMPLETED
                with self._lock:
                    self.stats.successful_recoveries += 1
                    total = self.stats.total_recoveries
                    prev_avg = self.stats.avg_recovery_seconds
                    self.stats.avg_recovery_seconds = (
                        (prev_avg * (total - 1) + elapsed) / total
                    )
                    self.stats.snapshots_used += 1
                logger.info(f"Recovery {event_id} completed in {elapsed:.2f}s")
            else:
                event.status = RecoveryStatus.FAILED
                event.error = "Snapshot restore failed"
                with self._lock:
                    self.stats.failed_recoveries += 1
                logger.error(f"Recovery {event_id} failed")

        except Exception as e:
            elapsed = time.monotonic() - start
            event.duration_seconds = elapsed
            event.status = RecoveryStatus.FAILED
            event.error = str(e)
            with self._lock:
                self.stats.failed_recoveries += 1
            logger.error(f"Recovery {event_id} exception: {e}")

        with self._lock:
            self.recovery_history.append(event)

        return event

    def recover_latest(
        self,
        name_pattern: Optional[str] = None,
        target_dir: Optional[str] = None,
        trigger: str = "auto_recovery"
    ) -> Optional[RecoveryEvent]:
        """Recover from the latest snapshot matching pattern"""
        snapshots = self.snapshot_manager.list_snapshots(status=SnapshotStatus.READY)
        if name_pattern:
            snapshots = [s for s in snapshots if name_pattern in s.name]

        if not snapshots:
            logger.warning(f"No snapshots found matching pattern '{name_pattern}'")
            return None

        latest = snapshots[0]
        return self.recover(
            latest.id,
            trigger=trigger,
            target_dir=target_dir
        )

    def recover_recovery_point(self, point_id: str) -> Optional[RecoveryEvent]:
        """Recover from the latest snapshot of a recovery point"""
        point = self.recovery_points.get(point_id)
        if not point:
            return None

        snapshots = [
            s for s in self.snapshot_manager.list_snapshots(status=SnapshotStatus.READY)
            if point.name in s.name
        ]
        if not snapshots:
            return None
        return self.recover(snapshots[0].id, trigger=f"recovery_point:{point.name}")

    def get_recovery_history(self, limit: int = 50) -> List[RecoveryEvent]:
        """Get recovery history"""
        with self._lock:
            return self.recovery_history[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """Get recovery engine statistics"""
        with self._lock:
            return {
                "total_recoveries": self.stats.total_recoveries,
                "successful_recoveries": self.stats.successful_recoveries,
                "failed_recoveries": self.stats.failed_recoveries,
                "avg_recovery_seconds": self.stats.avg_recovery_seconds,
                "snapshots_auto_created": self.stats.snapshots_auto_created,
                "snapshots_manually_created": self.stats.snapshots_manually_created,
                "snapshots_used": self.stats.snapshots_used,
                "registered_recovery_points": len(self.recovery_points)
            }


# Module-level singleton
_default_engine: Optional[RecoveryEngine] = None


def get_recovery_engine() -> RecoveryEngine:
    """Get or create the default recovery engine"""
    global _default_engine
    if _default_engine is None:
        _default_engine = RecoveryEngine()
    return _default_engine
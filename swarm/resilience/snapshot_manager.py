"""
Snapshot Manager Module - Pre-stage Snapshots for Quick Recovery
Creates, manages, and restores point-in-time snapshots of swarm state.
"""
import os
import sys
import json
import shutil
import hashlib
import logging
import threading
import time
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field, asdict
from enum import Enum
import tarfile
import io

logger = logging.getLogger(__name__)


class SnapshotStatus(Enum):
    """Status of a snapshot"""
    CREATING = "creating"
    READY = "ready"
    CORRUPTED = "corrupted"
    ARCHIVED = "archived"
    DELETED = "deleted"


class SnapshotType(Enum):
    """Type of snapshot"""
    FULL = "full"
    INCREMENTAL = "incremental"
    AUTO = "auto"


@dataclass
class Snapshot:
    """A point-in-time snapshot"""
    id: str
    name: str
    type: SnapshotType
    status: SnapshotStatus
    created_at: str
    size_bytes: int
    file_count: int
    checksum: str
    paths: List[str]
    description: str = ""
    parent_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    compression: str = "gzip"


@dataclass
class SnapshotStats:
    """Snapshot manager statistics"""
    total_snapshots: int = 0
    total_restores: int = 0
    total_bytes_saved: int = 0
    last_snapshot_time: Optional[str] = None
    last_restore_time: Optional[str] = None
    failed_creates: int = 0
    failed_restores: int = 0


@dataclass
class SnapshotScope:
    """Defines what a snapshot covers: which paths, which components.

    Attributes:
        paths: Filesystem paths included in the snapshot
        components: Named components (e.g. "vault", "memory", "config") in scope
        include_hidden: Whether to include hidden files (dotfiles)
        max_depth: Maximum directory depth (-1 = unlimited)
    """
    paths: List[str] = field(default_factory=list)
    components: List[str] = field(default_factory=list)
    include_hidden: bool = False
    max_depth: int = -1

    def matches_path(self, path: str) -> bool:
        """Check whether a given path falls within this scope."""
        path = str(path)
        for p in self.paths:
            if path == p or path.startswith(p.rstrip("/") + "/"):
                return True
        return False


@dataclass
class SnapshotMetadata:
    """Metadata attached to a snapshot for discovery, indexing, and retention.

    Stored alongside the snapshot tarball and indexed for fast lookup.
    Used by RecoveryEngine to choose the right snapshot for a restore request.

    Attributes:
        id: Unique snapshot id
        name: Human-readable name
        type: SnapshotType (FULL / INCREMENTAL / AUTO)
        scope: SnapshotScope describing what is captured
        tags: Free-form labels (e.g. "pre-deploy", "rollback-point")
        created_at: ISO-8601 timestamp
        size_bytes: Compressed size on disk
        checksum: SHA-256 of the tarball
        retention_until: ISO-8601 timestamp after which this snapshot is GC'd
    """
    id: str
    name: str
    type: SnapshotType
    scope: SnapshotScope
    tags: List[str] = field(default_factory=list)
    created_at: str = ""
    size_bytes: int = 0
    checksum: str = ""
    retention_until: Optional[str] = None

    def is_expired(self, now_iso: Optional[str] = None) -> bool:
        if not self.retention_until:
            return False
        return self.retention_until <= (now_iso or datetime.now(timezone.utc).isoformat())


class SnapshotManager:
    """
    Manages point-in-time snapshots of swarm state.
    Supports full and incremental snapshots with checksums.
    """

    def __init__(self, storage_path: str = "swarm/resilience/snapshots"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

        self.snapshots: Dict[str, Snapshot] = {}
        self.stats = SnapshotStats()
        self.max_snapshots = 50  # Auto-prune threshold

        self._load_index()

    def _load_index(self) -> None:
        """Load snapshot index from disk"""
        index_file = self.storage_path / "snapshot_index.json"
        if index_file.exists():
            try:
                with open(index_file, "r") as f:
                    data = json.load(f)
                for s_id, s_data in data.get("snapshots", {}).items():
                    s_data["type"] = SnapshotType(s_data["type"])
                    s_data["status"] = SnapshotStatus(s_data["status"])
                    snapshot = Snapshot(**s_data)
                    self.snapshots[s_id] = snapshot
                self.stats.total_snapshots = data.get("total_snapshots", 0)
            except Exception as e:
                logger.error(f"Failed to load snapshot index: {e}")

    def _save_index(self) -> None:
        """Save snapshot index to disk"""
        index_file = self.storage_path / "snapshot_index.json"
        try:
            data = {
                "snapshots": {},
                "total_snapshots": self.stats.total_snapshots
            }
            for s_id, snap in self.snapshots.items():
                snap_dict = asdict(snap)
                snap_dict["type"] = snap.type.value
                snap_dict["status"] = snap.status.value
                data["snapshots"][s_id] = snap_dict
            with open(index_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save snapshot index: {e}")

    def create_snapshot(
        self,
        name: str,
        paths: List[str],
        description: str = "",
        snapshot_type: SnapshotType = SnapshotType.FULL,
        parent_id: Optional[str] = None
    ) -> str:
        """
        Create a snapshot of the given paths.
        Returns snapshot ID.
        """
        with self._lock:
            import uuid
            snapshot_id = f"snap-{uuid.uuid4().hex[:12]}"
            snapshot_file = self.storage_path / f"{snapshot_id}.tar.gz"

            try:
                file_count = 0
                total_size = 0
                checksum = hashlib.sha256()

                with tarfile.open(snapshot_file, "w:gz") as tar:
                    for path_str in paths:
                        path = Path(path_str)
                        if not path.exists():
                            logger.warning(f"Path {path_str} does not exist, skipping")
                            continue
                        if path.is_file():
                            tar.add(str(path), arcname=path.name)
                            file_count += 1
                            total_size += path.stat().st_size
                            checksum.update(path.read_bytes())
                        elif path.is_dir():
                            for item in path.rglob("*"):
                                if item.is_file():
                                    tar.add(str(item), arcname=str(item.relative_to(path.parent)))
                                    file_count += 1
                                    total_size += item.stat().st_size
                                    checksum.update(item.read_bytes())

                actual_size = snapshot_file.stat().st_size
                checksum_hex = checksum.hexdigest()

                snapshot = Snapshot(
                    id=snapshot_id,
                    name=name,
                    type=snapshot_type,
                    status=SnapshotStatus.READY,
                    created_at=datetime.now().isoformat(),
                    size_bytes=actual_size,
                    file_count=file_count,
                    checksum=checksum_hex,
                    paths=paths,
                    description=description,
                    parent_id=parent_id
                )
                self.snapshots[snapshot_id] = snapshot
                self.stats.total_snapshots += 1
                self.stats.total_bytes_saved += actual_size
                self.stats.last_snapshot_time = snapshot.created_at
                self._save_index()

                logger.info(
                    f"Created snapshot {snapshot_id} ({name}): "
                    f"{file_count} files, {actual_size} bytes"
                )
                self._prune_old_snapshots()
                return snapshot_id

            except Exception as e:
                logger.error(f"Failed to create snapshot: {e}")
                self.stats.failed_creates += 1
                if snapshot_file.exists():
                    snapshot_file.unlink()
                raise

    def restore_snapshot(
        self,
        snapshot_id: str,
        target_dir: Optional[str] = None,
        overwrite: bool = False
    ) -> bool:
        """
        Restore files from a snapshot.
        Returns True on success.
        """
        with self._lock:
            if snapshot_id not in self.snapshots:
                logger.error(f"Snapshot {snapshot_id} not found")
                return False

            snapshot = self.snapshots[snapshot_id]
            if snapshot.status != SnapshotStatus.READY:
                logger.error(f"Snapshot {snapshot_id} is not ready (status={snapshot.status.value})")
                return False

            snapshot_file = self.storage_path / f"{snapshot_id}.tar.gz"
            if not snapshot_file.exists():
                logger.error(f"Snapshot file {snapshot_file} missing")
                snapshot.status = SnapshotStatus.CORRUPTED
                self._save_index()
                return False

            target = Path(target_dir) if target_dir else Path(".")

            try:
                # Verify integrity
                if not self._verify_snapshot(snapshot_id):
                    self.stats.failed_restores += 1
                    return False

                with tarfile.open(snapshot_file, "r:gz") as tar:
                    # Python 3.14+ requires explicit filter; 3.13 emits DeprecationWarning.
                    # Use 'data' filter when supported, otherwise fall back to default.
                    extract_kwargs = {}
                    if sys.version_info >= (3, 12):
                        extract_kwargs["filter"] = "data"
                    if overwrite:
                        tar.extractall(target, **extract_kwargs)
                    else:
                        # Only extract files that don't exist
                        for member in tar.getmembers():
                            target_path = target / member.name
                            if not target_path.exists():
                                tar.extract(member, target, **extract_kwargs)

                self.stats.total_restores += 1
                self.stats.last_restore_time = datetime.now().isoformat()
                logger.info(f"Restored snapshot {snapshot_id} to {target}")
                return True

            except Exception as e:
                logger.error(f"Failed to restore snapshot {snapshot_id}: {e}")
                self.stats.failed_restores += 1
                return False

    def _verify_snapshot(self, snapshot_id: str) -> bool:
        """Verify snapshot integrity"""
        snapshot_file = self.storage_path / f"{snapshot_id}.tar.gz"
        snapshot = self.snapshots[snapshot_id]

        try:
            with tarfile.open(snapshot_file, "r:gz") as tar:
                # Basic check: file opens and is valid tar
                members = tar.getmembers()
                if len(members) != snapshot.file_count:
                    logger.warning(
                        f"Snapshot {snapshot_id} member count mismatch: "
                        f"expected {snapshot.file_count}, got {len(members)}"
                    )
                return True
        except (tarfile.TarError, OSError) as e:
            logger.error(f"Snapshot {snapshot_id} corrupted: {e}")
            snapshot.status = SnapshotStatus.CORRUPTED
            self._save_index()
            return False

    def delete_snapshot(self, snapshot_id: str) -> bool:
        """Delete a snapshot and its file"""
        with self._lock:
            if snapshot_id not in self.snapshots:
                return False
            snapshot = self.snapshots[snapshot_id]
            snapshot.status = SnapshotStatus.DELETED
            snapshot_file = self.storage_path / f"{snapshot_id}.tar.gz"
            if snapshot_file.exists():
                snapshot_file.unlink()
            del self.snapshots[snapshot_id]
            self._save_index()
            logger.info(f"Deleted snapshot {snapshot_id}")
            return True

    def get_snapshot(self, snapshot_id: str) -> Optional[Snapshot]:
        """Get snapshot metadata"""
        with self._lock:
            return self.snapshots.get(snapshot_id)

    def list_snapshots(self, status: Optional[SnapshotStatus] = None) -> List[Snapshot]:
        """List all snapshots"""
        with self._lock:
            snaps = list(self.snapshots.values())
            if status:
                snaps = [s for s in snaps if s.status == status]
            return sorted(snaps, key=lambda s: s.created_at, reverse=True)

    def get_stats(self) -> Dict[str, Any]:
        """Get snapshot manager statistics"""
        with self._lock:
            return {
                "total_snapshots": len(self.snapshots),
                "total_restores": self.stats.total_restores,
                "total_bytes_saved": self.stats.total_bytes_saved,
                "last_snapshot_time": self.stats.last_snapshot_time,
                "last_restore_time": self.stats.last_restore_time,
                "failed_creates": self.stats.failed_creates,
                "failed_restores": self.stats.failed_restores,
                "max_snapshots": self.max_snapshots
            }

    def _prune_old_snapshots(self) -> None:
        """Remove oldest snapshots if over limit"""
        if len(self.snapshots) <= self.max_snapshots:
            return
        snaps = sorted(
            self.snapshots.values(),
            key=lambda s: s.created_at
        )
        to_remove = len(self.snapshots) - self.max_snapshots
        for snap in snaps[:to_remove]:
            self.delete_snapshot(snap.id)
        logger.info(f"Pruned {to_remove} old snapshots")


# Module-level singleton
_default_manager: Optional[SnapshotManager] = None


def get_snapshot_manager() -> SnapshotManager:
    """Get or create the default snapshot manager"""
    global _default_manager
    if _default_manager is None:
        _default_manager = SnapshotManager()
    return _default_manager
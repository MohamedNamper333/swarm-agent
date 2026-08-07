"""
Unit tests for Recovery modules - Week 11
"""
import pytest
import tempfile
import shutil
from pathlib import Path

from swarm.resilience.snapshot_manager import (
    SnapshotManager, SnapshotStatus, SnapshotType
)
from swarm.resilience.recovery_engine import (
    RecoveryEngine, RecoveryStrategy, RecoveryStatus, SnapshotType
)


@pytest.fixture
def temp_storage():
    tmpdir = tempfile.mkdtemp()
    yield tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def sample_files(temp_storage):
    """Create some sample files for snapshot testing"""
    files_dir = Path(temp_storage) / "data"
    files_dir.mkdir()
    (files_dir / "file1.txt").write_text("Hello World 1")
    (files_dir / "file2.txt").write_text("Hello World 2")
    (files_dir / "subdir").mkdir()
    (files_dir / "subdir" / "file3.txt").write_text("Hello World 3")
    return str(files_dir)


# === Snapshot Manager Tests ===

class TestSnapshotStatus:
    def test_status_values(self):
        assert SnapshotStatus.READY.value == "ready"
        assert SnapshotStatus.CORRUPTED.value == "corrupted"


class TestSnapshotManagerInit:
    def test_init(self, temp_storage):
        mgr = SnapshotManager(storage_path=temp_storage)
        assert mgr is not None


class TestCreateSnapshot:
    def test_create_snapshot(self, temp_storage, sample_files):
        mgr = SnapshotManager(storage_path=temp_storage)
        snapshot_id = mgr.create_snapshot(
            name="test_snapshot",
            paths=[sample_files],
            description="Test snapshot"
        )
        assert snapshot_id is not None
        snapshot = mgr.get_snapshot(snapshot_id)
        assert snapshot.status == SnapshotStatus.READY
        assert snapshot.file_count >= 3

    def test_create_snapshot_empty_path(self, temp_storage):
        mgr = SnapshotManager(storage_path=temp_storage)
        snapshot_id = mgr.create_snapshot(
            name="empty",
            paths=[]
        )
        assert snapshot_id is not None

    def test_create_snapshot_nonexistent_path(self, temp_storage):
        mgr = SnapshotManager(storage_path=temp_storage)
        # Should not fail, just skip
        snapshot_id = mgr.create_snapshot(
            name="missing",
            paths=["/nonexistent/path"]
        )
        assert snapshot_id is not None


class TestRestoreSnapshot:
    def test_restore_snapshot(self, temp_storage, sample_files):
        mgr = SnapshotManager(storage_path=temp_storage)
        snapshot_id = mgr.create_snapshot(
            name="restore_test",
            paths=[sample_files]
        )

        # Modify files
        (Path(sample_files) / "file1.txt").write_text("MODIFIED")

        # Restore
        restore_target = Path(temp_storage) / "restored"
        restore_target.mkdir()
        success = mgr.restore_snapshot(snapshot_id, target_dir=str(restore_target))
        assert success is True

    def test_restore_nonexistent(self, temp_storage):
        mgr = SnapshotManager(storage_path=temp_storage)
        success = mgr.restore_snapshot("nonexistent")
        assert success is False


class TestDeleteSnapshot:
    def test_delete_snapshot(self, temp_storage, sample_files):
        mgr = SnapshotManager(storage_path=temp_storage)
        snapshot_id = mgr.create_snapshot(name="to_delete", paths=[sample_files])
        assert mgr.delete_snapshot(snapshot_id) is True
        assert mgr.get_snapshot(snapshot_id) is None

    def test_delete_nonexistent(self, temp_storage):
        mgr = SnapshotManager(storage_path=temp_storage)
        assert mgr.delete_snapshot("nonexistent") is False


class TestSnapshotList:
    def test_list_snapshots(self, temp_storage, sample_files):
        mgr = SnapshotManager(storage_path=temp_storage)
        mgr.create_snapshot(name="snap1", paths=[sample_files])
        mgr.create_snapshot(name="snap2", paths=[sample_files])
        snaps = mgr.list_snapshots()
        assert len(snaps) >= 2

    def test_list_by_status(self, temp_storage, sample_files):
        mgr = SnapshotManager(storage_path=temp_storage)
        mgr.create_snapshot(name="snap1", paths=[sample_files])
        snaps = mgr.list_snapshots(status=SnapshotStatus.READY)
        assert all(s.status == SnapshotStatus.READY for s in snaps)


class TestSnapshotStats:
    def test_stats(self, temp_storage, sample_files):
        mgr = SnapshotManager(storage_path=temp_storage)
        mgr.create_snapshot(name="snap", paths=[sample_files])
        stats = mgr.get_stats()
        assert stats["total_snapshots"] >= 1
        assert stats["total_bytes_saved"] > 0


class TestSnapshotIntegrity:
    def test_verify_snapshot(self, temp_storage, sample_files):
        mgr = SnapshotManager(storage_path=temp_storage)
        snapshot_id = mgr.create_snapshot(name="snap", paths=[sample_files])
        assert mgr._verify_snapshot(snapshot_id) is True


# === Recovery Engine Tests ===

class TestRecoveryStrategy:
    def test_strategy_values(self):
        assert RecoveryStrategy.AUTO_SNAPSHOT.value == "auto_snapshot"
        assert RecoveryStrategy.RESTORE_LAST.value == "restore_last"


class TestRecoveryEngineInit:
    def test_init(self, temp_storage):
        engine = RecoveryEngine(storage_path=temp_storage)
        assert engine is not None


class TestRegisterRecoveryPoint:
    def test_register_recovery_point(self, temp_storage, sample_files):
        engine = RecoveryEngine(storage_path=temp_storage)
        point_id = engine.register_recovery_point(
            name="critical_data",
            paths=[sample_files],
            description="Critical files",
            auto_create=True
        )
        assert point_id is not None
        assert point_id in engine.recovery_points


class TestSnapshotBefore:
    def test_snapshot_before(self, temp_storage, sample_files):
        engine = RecoveryEngine(storage_path=temp_storage)
        snapshot_id = engine.snapshot_before(
            name="pre_operation",
            paths=[sample_files],
            description="Before risky op"
        )
        assert snapshot_id is not None


class TestRecover:
    def test_recover_success(self, temp_storage, sample_files):
        engine = RecoveryEngine(storage_path=temp_storage)
        snapshot_id = engine.snapshot_before(
            name="pre_recovery",
            paths=[sample_files]
        )

        # Modify files
        (Path(sample_files) / "file1.txt").write_text("MODIFIED")

        # Recover
        event = engine.recover(snapshot_id, trigger="test")
        assert event.status == RecoveryStatus.COMPLETED
        assert event.duration_seconds >= 0

    def test_recover_invalid_snapshot(self, temp_storage):
        engine = RecoveryEngine(storage_path=temp_storage)
        event = engine.recover("nonexistent", trigger="test")
        assert event.status == RecoveryStatus.FAILED

    def test_recover_latest(self, temp_storage, sample_files):
        engine = RecoveryEngine(storage_path=temp_storage)
        engine.snapshot_before(name="latest_test", paths=[sample_files])

        event = engine.recover_latest(name_pattern="latest_test")
        assert event is not None

    def test_recover_latest_no_match(self, temp_storage):
        engine = RecoveryEngine(storage_path=temp_storage)
        event = engine.recover_latest(name_pattern="nonexistent")
        assert event is None


class TestRecoveryHistory:
    def test_history_tracked(self, temp_storage, sample_files):
        engine = RecoveryEngine(storage_path=temp_storage)
        snapshot_id = engine.snapshot_before(name="history_test", paths=[sample_files])
        engine.recover(snapshot_id)
        history = engine.get_recovery_history()
        assert len(history) >= 1


class TestRecoveryStats:
    def test_stats(self, temp_storage, sample_files):
        engine = RecoveryEngine(storage_path=temp_storage)
        snapshot_id = engine.snapshot_before(name="stats_test", paths=[sample_files])
        engine.recover(snapshot_id)
        stats = engine.get_stats()
        assert stats["total_recoveries"] >= 1
        assert stats["successful_recoveries"] >= 1


class TestRecoveryPointRecovery:
    def test_recover_recovery_point(self, temp_storage, sample_files):
        engine = RecoveryEngine(storage_path=temp_storage)
        point_id = engine.register_recovery_point(
            name="recovery_target",
            paths=[sample_files],
            auto_create=True
        )
        event = engine.recover_recovery_point(point_id)
        assert event is not None


class TestEdgeCases:
    def test_snapshot_before_failed_path(self, temp_storage):
        engine = RecoveryEngine(storage_path=temp_storage)
        snapshot_id = engine.snapshot_before(name="failed", paths=["/nonexistent"])
        assert snapshot_id is not None  # Should still create empty snapshot

    def test_recover_recovery_point_nonexistent(self, temp_storage):
        engine = RecoveryEngine(storage_path=temp_storage)
        event = engine.recover_recovery_point("nonexistent")
        assert event is None


class TestSingleton:
    def test_get_snapshot_manager(self):
        from swarm.resilience.snapshot_manager import get_snapshot_manager
        mgr = get_snapshot_manager()
        assert isinstance(mgr, SnapshotManager)

    def test_get_recovery_engine(self):
        from swarm.resilience.recovery_engine import get_recovery_engine
        engine = get_recovery_engine()
        assert isinstance(engine, RecoveryEngine)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
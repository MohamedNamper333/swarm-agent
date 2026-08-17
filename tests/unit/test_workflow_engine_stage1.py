"""Tests for Workflow Engine Stage 1 P0 fixes.

- 1.1: _heartbeat_loop exists and fails stale jobs
- 1.2: DurableJob.to_dict/from_dict preserves events
- 1.3: JobQueue.dequeue isolates by tenant_id
"""
import signal
import time
import pytest
from datetime import datetime, timezone, timedelta

from swarm.enterprise.core.job.models import (
    DurableJob, JobQueue, JobStatus, JobConfig, JobPriority, JobResult
)
from swarm.enterprise.core.job.worker import (
    Worker, WorkerConfig, JobExecutor
)


@pytest.fixture(autouse=True)
def restore_signal_handlers():
    """Worker constructor installs SIGTERM/SIGINT handlers — restore after each test."""
    original_term = signal.getsignal(signal.SIGTERM)
    original_int = signal.getsignal(signal.SIGINT)
    yield
    try:
        signal.signal(signal.SIGTERM, original_term)
        signal.signal(signal.SIGINT, original_int)
    except (ValueError, OSError):
        pass


# ============================================================
# 1.1: Heartbeat loop exists and fails stale jobs
# ============================================================

class TestHeartbeatLoop:
    def test_worker_has_heartbeat_loop_method(self):
        """Worker must define _heartbeat_loop (was AttributeError before)."""
        config = WorkerConfig(worker_id="w-1")
        worker = Worker(config=config)
        assert hasattr(worker, "_heartbeat_loop")
        assert callable(worker._heartbeat_loop)

    def test_stale_heartbeat_fails_job(self):
        """Job with stale heartbeat should be marked FAILED by heartbeat loop."""
        config = WorkerConfig(
            worker_id="w-stale",
            heartbeat_interval_sec=1,  # short interval for test
        )
        worker = Worker(config=config)
        worker._running = True  # Mark as started so loop runs

        # Create a job and walk it through to RUNNING state
        job = DurableJob(
            job_id="job-stale-1",
            job_type="noop",
            payload={},
            config=JobConfig(timeout_ms=60000),
        )
        assert job.transition_to(JobStatus.QUEUED), "PENDING -> QUEUED"
        assert job.transition_to(JobStatus.ASSIGNED, "w-stale"), "QUEUED -> ASSIGNED"
        assert job.transition_to(JobStatus.RUNNING, "w-stale"), "ASSIGNED -> RUNNING"
        # Set heartbeat to long ago
        job.last_heartbeat = datetime.now(timezone.utc) - timedelta(seconds=10)

        with worker._lock:
            worker._active_jobs[job.job_id] = job

        # Pre-condition: job is RUNNING with stale heartbeat
        now = datetime.now(timezone.utc)
        timeout_sec = config.heartbeat_interval_sec * 3
        assert (now - job.last_heartbeat).total_seconds() > timeout_sec

        # Set shutdown BEFORE calling the loop so it exits after one iteration
        worker._shutdown_event.set()
        worker._heartbeat_loop()

        # Job should be FAILED
        assert job.status == JobStatus.FAILED


# ============================================================
# 1.2: Job roundtrip preserves events
# ============================================================

class TestJobSerialization:
    def test_roundtrip_preserves_events(self):
        """to_dict/from_dict must preserve all JobEvents."""
        job = DurableJob(
            job_id="job-rt-1",
            job_type="test",
            payload={"x": 1},
            config=JobConfig(),
        )
        job.transition_to(JobStatus.QUEUED)
        job.transition_to(JobStatus.ASSIGNED, "w-1")
        job.transition_to(JobStatus.RUNNING, "w-1")
        # Add a custom event
        job.add_event("custom_event", {"foo": "bar"}, "w-1")

        original_event_count = len(job.events)
        assert original_event_count >= 4  # 3 transitions + 1 custom

        # Serialize and deserialize
        data = job.to_dict()
        restored = DurableJob.from_dict(data)

        assert len(restored.events) == original_event_count, \
            "to_dict must include events"

        # Verify event content
        custom_events = [e for e in restored.events if e.event_type == "custom_event"]
        assert len(custom_events) == 1
        assert custom_events[0].data == {"foo": "bar"}
        assert custom_events[0].worker_id == "w-1"

    def test_roundtrip_preserves_status_change_events(self):
        """Status transitions should roundtrip with from/to/reason."""
        job = DurableJob(
            job_id="job-rt-2",
            job_type="test",
            payload={},
            config=JobConfig(max_retries=0),
        )
        job.transition_to(JobStatus.QUEUED)
        job.transition_to(JobStatus.ASSIGNED, "w-1")
        job.transition_to(JobStatus.RUNNING, "w-1")

        data = job.to_dict()
        restored = DurableJob.from_dict(data)

        status_changes = [e for e in restored.events if e.event_type == "status_change"]
        assert len(status_changes) >= 3
        transitions = [(e.data["from"], e.data["to"]) for e in status_changes]
        assert ("pending", "queued") in transitions
        assert ("queued", "assigned") in transitions
        assert ("assigned", "running") in transitions


# ============================================================
# 1.3: Tenant isolation in dequeue
# ============================================================

class TestTenantIsolation:
    def _make_job(self, job_id: str, tenant_id: str, priority: JobPriority = JobPriority.NORMAL) -> DurableJob:
        job = DurableJob(
            job_id=job_id,
            job_type="test",
            payload={},
            config=JobConfig(tenant_id=tenant_id, priority=priority),
        )
        job.transition_to(JobStatus.QUEUED)
        return job

    def test_dequeue_isolates_by_tenant(self):
        """Worker with tenant_id=A must not get jobs of tenant B."""
        queue = JobQueue()
        job_a = self._make_job("job-a", "tenant-a")
        job_b = self._make_job("job-b", "tenant-b")
        queue.enqueue(job_a)
        queue.enqueue(job_b)

        # Worker for tenant A
        dequeued = queue.dequeue(worker_id="w-a", tenant_id="tenant-a", max_jobs=10)
        assert len(dequeued) == 1
        assert dequeued[0].job_id == "job-a"

        # Worker for tenant B
        dequeued_b = queue.dequeue(worker_id="w-b", tenant_id="tenant-b", max_jobs=10)
        assert len(dequeued_b) == 1
        assert dequeued_b[0].job_id == "job-b"

    def test_dequeue_without_tenant_is_backward_compatible(self):
        """When tenant_id=None, all jobs are returned (back-compat for system workers)."""
        queue = JobQueue()
        job_a = self._make_job("job-a", "tenant-a")
        job_b = self._make_job("job-b", "tenant-b")
        queue.enqueue(job_a)
        queue.enqueue(job_b)

        dequeued = queue.dequeue(worker_id="w-system", tenant_id=None, max_jobs=10)
        assert len(dequeued) == 2
        # Verify both tenants present
        tenants = {j.config.tenant_id for j in dequeued}
        assert tenants == {"tenant-a", "tenant-b"}

    def test_dequeue_preserves_fairness_with_mixed_tenants(self):
        """When tenant filter rejects jobs, they must be re-queued at head (not lost)."""
        queue = JobQueue()
        job_b1 = self._make_job("job-b1", "tenant-b", JobPriority.HIGH)
        job_a = self._make_job("job-a", "tenant-a", JobPriority.HIGH)
        job_b2 = self._make_job("job-b2", "tenant-b", JobPriority.NORMAL)
        queue.enqueue(job_b1)
        queue.enqueue(job_a)
        queue.enqueue(job_b2)

        # Tenant-A worker polls twice
        first = queue.dequeue(worker_id="w-a", tenant_id="tenant-a", max_jobs=10)
        assert len(first) == 1
        assert first[0].job_id == "job-a"

        # Tenant-B jobs must still be there
        pending = queue.get_pending_count()
        assert pending[JobPriority.HIGH] == 1
        assert pending[JobPriority.NORMAL] == 1

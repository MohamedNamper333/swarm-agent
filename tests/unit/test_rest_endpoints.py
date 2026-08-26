"""
End-to-end tests for the real REST endpoints — no demo data fallback.

These tests exercise the actual FastAPI app via httpx ASGI transport,
validating that:

1. /health returns the system health
2. /tasks creates and lists tasks via the real TaskQueue
3. /agents returns the real AgentRegistry state (4 default workers)
4. /queue/stats reports the live queue breakdown

Why this file matters: the rest_server originally contained hard-coded demo
data inside the endpoint bodies. We removed those fallbacks and bound the
endpoints to real components (TaskQueue, _AgentRegistry). This test suite
locks that contract — if anyone reintroduces demo fallbacks, the empty-list
or 503 assertions will catch it.
"""
import os
import tempfile
from pathlib import Path

import pytest

try:
    from httpx import AsyncClient, ASGITransport
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False


pytestmark = pytest.mark.skipif(
    not HTTPX_AVAILABLE, reason="httpx not installed"
)


def _make_client_with_lifespan():
    """Build an AsyncClient against the FastAPI app with isolated queue state
    and full lifespan context (startup + shutdown)."""
    from swarm.api.rest_server import app

    tmp = Path(tempfile.mkdtemp(prefix="swarm_rest_test_"))
    os.environ["SWARM_QUEUE_PATH"] = str(tmp)

    transport = ASGITransport(app=app)
    return transport, AsyncClient(transport=transport, base_url="http://test")


@pytest.fixture
def client():
    """Each test gets its own fresh lifespan startup — the queue is built
    fresh from SWARM_QUEUE_PATH, and global state resets between tests."""
    import asyncio
    from swarm.api.rest_server import app
    from asgi_lifespan import LifespanManager

    class _SyncClient:
        def __init__(self, manager, loop_client):
            self._manager = manager
            self._loop_client = loop_client
            self._closed = False

        def get(self, *a, **kw):
            return self._run("get", *a, **kw)

        def post(self, *a, **kw):
            return self._run("post", *a, **kw)

        def delete(self, *a, **kw):
            return self._run("delete", *a, **kw)

        def _run(self, method, *a, **kw):
            coro = getattr(self._loop_client, method)(*a, **kw)
            return asyncio.run(coro)

        def close(self):
            if self._closed:
                return
            self._closed = True
            try:
                asyncio.run(self._loop_client.aclose())
            except Exception:
                pass
            try:
                asyncio.run(self._manager.__aexit__(None, None, None))
            except Exception:
                pass

    async def _open_client():
        transport, ac = _make_client_with_lifespan()
        manager = LifespanManager(app)
        await manager.__aenter__()
        await ac.get("/health")
        return manager, ac

    manager, sync_client = asyncio.run(_open_client())
    # Authenticate the test client natively: real admin key as a default
    # header so tests exercise the actual security gate.
    from swarm.api.auth import get_auth_manager
    _mgr = get_auth_manager()
    _raw_key, _rec = _mgr.create_api_key("test-suite", ["admin"], owner="pytest")
    sync_client.headers["Authorization"] = f"Bearer {_raw_key}"

    sync = _SyncClient(manager, sync_client)
    try:
        yield sync
    finally:
        sync.close()
        os.environ.pop("SWARM_QUEUE_PATH", None)


# ========== Health ==========

class TestHealthEndpoint:
    def test_health_reports_status(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] in ("healthy", "degraded")
        assert "components" in body or "status" in body


# ========== Agents ==========

class TestAgentsEndpoint:
    def test_agents_returns_real_registry(self, client):
        """The 4 default agents from lifespan startup must be present —
        not the previous demo strings."""
        r = client.get("/agents")
        assert r.status_code == 200
        agents = r.json()
        ids = {a["agent_id"] for a in agents}
        assert "orchestrator-01" in ids
        assert "coder-01" in ids
        assert "reviewer-01" in ids
        assert "researcher-01" in ids

    def test_agent_state_field_shape(self, client):
        r = client.get("/agents")
        agent = r.json()[0]
        for key in ("agent_id", "state", "time_in_state_seconds"):
            assert key in agent, f"missing {key} in agent record"


# ========== Tasks ==========

class TestTasksEndpoint:
    def test_list_tasks_empty_initially(self, client):
        """Brand-new queue — empty list, not the old demo fallback."""
        r = client.get("/tasks")
        assert r.status_code == 200
        assert r.json() == []

    def test_create_task_appears_in_list(self, client):
        payload = {
            "name": "Smoke test task",
            "payload": {"source": "tests"},
            "priority": "high",
        }
        r = client.post("/tasks", json=payload)
        assert r.status_code == 201, r.text
        created = r.json()
        assert created["name"] == "Smoke test task"
        assert created["priority"] == "high"
        assert created["status"] == "queued"  # API maps pending -> queued
        assert created["attempts"] == 0

        r2 = client.get("/tasks")
        assert r2.status_code == 200
        listed = r2.json()
        assert any(t["id"] == created["id"] for t in listed)

    def test_get_task_by_id(self, client):
        payload = {"name": "Round-trip task", "payload": {"k": 1}, "priority": "normal"}
        create = client.post("/tasks", json=payload)
        task_id = create.json()["id"]
        r = client.get(f"/tasks/{task_id}")
        assert r.status_code == 200
        assert r.json()["id"] == task_id

    def test_get_task_not_found(self, client):
        r = client.get("/tasks/does-not-exist")
        assert r.status_code == 404

    def test_filter_tasks_by_priority(self, client):
        client.post("/tasks", json={"name": "low", "payload": {}, "priority": "low"})
        client.post("/tasks", json={"name": "high", "payload": {}, "priority": "high"})

        r = client.get("/tasks?priority=high")
        assert r.status_code == 200
        tasks = r.json()
        assert len(tasks) >= 1
        for t in tasks:
            assert t["priority"] == "high"

    def test_cancel_pending_task(self, client):
        payload = {"name": "Cancellable", "payload": {}, "priority": "normal"}
        create = client.post("/tasks", json=payload)
        task_id = create.json()["id"]

        r = client.delete(f"/tasks/{task_id}")
        assert r.status_code == 200
        assert r.json()["task_id"] == task_id


# ========== Queue Stats ==========

class TestQueueStatsEndpoint:
    def test_queue_stats_reflects_real_state(self, client):
        for name in ("a", "b", "c"):
            client.post("/tasks", json={"name": name, "payload": {}, "priority": "normal"})

        r = client.get("/queue/stats")
        assert r.status_code == 200
        body = r.json()
        assert "size" in body
        assert "status" in body
        assert "breakdown" in body
        assert body["size"] >= 3


# ========== Root / docs ==========

class TestRootAndDocs:
    def test_openapi_json_available(self, client):
        r = client.get("/openapi.json")
        assert r.status_code == 200
        spec = r.json()
        assert spec["info"]["title"] == "Swarm API"
        assert spec["info"]["version"] == "3.0.0"

    def test_swagger_docs_available(self, client):
        r = client.get("/docs")
        assert r.status_code == 200
        assert "swagger" in r.text.lower()

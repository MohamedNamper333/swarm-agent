"""Integration tests for User Service (API + DB + Cache)."""

import json
import os
import subprocess
import time
import urllib.request
import urllib.error
import pytest

BASE = "http://127.0.0.1:8098"
DB_FILE = os.path.join(os.path.dirname(__file__), "users.db")


@pytest.fixture(scope="module", autouse=True)
def server():
    for f in [DB_FILE, DB_FILE + "-wal", DB_FILE + "-shm"]:
        if os.path.exists(f):
            os.remove(f)
    proc = subprocess.Popen(
        ["python3", os.path.join(os.path.dirname(__file__), "api.py")],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    time.sleep(1)
    yield proc
    proc.terminate()
    proc.wait()
    for f in [DB_FILE, DB_FILE + "-wal", DB_FILE + "-shm"]:
        if os.path.exists(f):
            os.remove(f)


def post(path, data, token=None):
    body = json.dumps(data).encode()
    req = urllib.request.Request(f"{BASE}{path}", data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    return urllib.request.urlopen(req)


def get(path, token):
    req = urllib.request.Request(f"{BASE}{path}")
    req.add_header("Authorization", f"Bearer {token}")
    return urllib.request.urlopen(req)


def put(path, data, token):
    body = json.dumps(data).encode()
    req = urllib.request.Request(f"{BASE}{path}", data=body, method="PUT")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {token}")
    return urllib.request.urlopen(req)


def delete(path, token):
    req = urllib.request.Request(f"{BASE}{path}", method="DELETE")
    req.add_header("Authorization", f"Bearer {token}")
    return urllib.request.urlopen(req)


# ── DB Layer Tests ──

class TestDB:
    def test_create_user(self):
        from db import UserDB
        db = UserDB(":memory:")
        user = db.create_user("alice", "alice@test.com", "pass123")
        assert user["username"] == "alice"
        assert user["role"] == "user"
        db.close()

    def test_duplicate_user_returns_none(self):
        from db import UserDB
        db = UserDB(":memory:")
        db.create_user("bob", "bob@test.com", "pass")
        result = db.create_user("bob", "bob2@test.com", "pass2")
        assert result is None
        db.close()

    def test_authenticate(self):
        from db import UserDB
        db = UserDB(":memory:")
        db.create_user("charlie", "c@test.com", "secret")
        user = db.authenticate("charlie", "secret")
        assert user is not None
        assert user["username"] == "charlie"
        bad = db.authenticate("charlie", "wrong")
        assert bad is None
        db.close()

    def test_role_update(self):
        from db import UserDB
        db = UserDB(":memory:")
        u = db.create_user("dave", "d@test.com", "pass")
        updated = db.update_role(u["id"], "admin")
        assert updated["role"] == "admin"
        db.close()


# ── Cache Layer Tests ──

class TestCache:
    def test_set_get(self):
        from cache import Cache
        c = Cache(default_ttl=10)
        c.set("key1", "value1")
        assert c.get("key1") == "value1"

    def test_ttl_expiry(self):
        from cache import Cache
        c = Cache(default_ttl=0)
        c.set("expire", "now")
        time.sleep(0.01)
        assert c.get("expire") is None

    def test_delete(self):
        from cache import Cache
        c = Cache()
        c.set("del", "me")
        assert c.delete("del") is True
        assert c.get("del") is None

    def test_clear(self):
        from cache import Cache
        c = Cache()
        c.set("a", 1)
        c.set("b", 2)
        c.clear()
        assert c.get("a") is None
        assert c.stats()["entries"] == 0

    def test_stats(self):
        from cache import Cache
        c = Cache()
        c.set("x", 10)
        c.get("x")
        c.get("x")
        stats = c.stats()
        assert stats["entries"] == 1
        assert stats["total_hits"] == 2

    def test_invalidate_pattern(self):
        from cache import Cache
        c = Cache()
        c.set("user:1", "a")
        c.set("user:2", "b")
        c.set("post:1", "c")
        deleted = c.invalidate_pattern("user:")
        assert deleted == 2
        assert c.get("post:1") == "c"


# ── Integration Tests (API + DB + Cache) ──

class TestIntegration:
    def test_register_and_login(self):
        resp = post("/register", {"username": "int_user1", "email": "int1@test.com", "password": "pass1"})
        data = json.loads(resp.read())
        assert "token" in data
        assert data["user"]["username"] == "int_user1"

        resp2 = post("/login", {"username": "int_user1", "password": "pass1"})
        data2 = json.loads(resp2.read())
        assert data2["user"]["username"] == "int_user1"

    def test_duplicate_register_fails(self):
        post("/register", {"username": "dup_user", "email": "dup@test.com", "password": "pass"})
        with pytest.raises(urllib.error.HTTPError) as exc:
            post("/register", {"username": "dup_user", "email": "dup2@test.com", "password": "pass2"})
        assert exc.value.code == 409

    def test_me_endpoint(self):
        resp = post("/register", {"username": "me_user", "email": "me@test.com", "password": "pass"})
        token = json.loads(resp.read())["token"]
        resp2 = get("/users/me", token)
        data = json.loads(resp2.read())
        assert data["username"] == "me_user"
        assert "_cached" in data

    def test_cache_hit(self):
        resp = post("/register", {"username": "cache_user", "email": "cache@test.com", "password": "pass"})
        token = json.loads(resp.read())["token"]
        get("/users/me", token)
        resp2 = get("/users/me", token)
        data = json.loads(resp2.read())
        assert data["_cached"] is True

    def test_admin_list_users(self):
        resp = post("/register", {"username": "admin_user", "email": "admin@test.com", "password": "pass", "role": "admin"})
        admin_data = json.loads(resp.read())
        admin_token = admin_data["token"]
        resp2 = get("/users", admin_token)
        users = json.loads(resp2.read())
        assert isinstance(users, list)
        assert len(users) >= 1

    def test_non_admin_cannot_list_users(self):
        resp = post("/register", {"username": "normal_user", "email": "normal@test.com", "password": "pass"})
        token = json.loads(resp.read())["token"]
        with pytest.raises(urllib.error.HTTPError) as exc:
            get("/users", token)
        assert exc.value.code == 403

    def test_cache_stats(self):
        resp = post("/register", {"username": "stats_user", "email": "stats@test.com", "password": "pass"})
        token = json.loads(resp.read())["token"]
        resp2 = get("/cache/stats", token)
        stats = json.loads(resp2.read())
        assert "entries" in stats
        assert "total_hits" in stats

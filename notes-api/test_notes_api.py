"""Tests for Notes REST API."""

import json
import os
import subprocess
import time
import urllib.request
import urllib.error
import pytest

BASE = "http://127.0.0.1:8099"
TOKEN = "secret-token-123"
DATA_FILE = os.path.join(os.path.dirname(__file__), "notes.json")


@pytest.fixture(scope="module", autouse=True)
def server():
    if os.path.exists(DATA_FILE):
        os.remove(DATA_FILE)
    proc = subprocess.Popen(
        ["python3", os.path.join(os.path.dirname(__file__), "app.py")],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    time.sleep(1)
    yield proc
    proc.terminate()
    proc.wait()
    if os.path.exists(DATA_FILE):
        os.remove(DATA_FILE)


def auth_GET(path):
    req = urllib.request.Request(f"{BASE}{path}")
    req.add_header("Authorization", f"Bearer {TOKEN}")
    return urllib.request.urlopen(req)


def auth_POST(path, data):
    body = json.dumps(data).encode()
    req = urllib.request.Request(f"{BASE}{path}", data=body, method="POST")
    req.add_header("Authorization", f"Bearer {TOKEN}")
    req.add_header("Content-Type", "application/json")
    return urllib.request.urlopen(req)


def auth_DELETE(path):
    req = urllib.request.Request(f"{BASE}{path}", method="DELETE")
    req.add_header("Authorization", f"Bearer {TOKEN}")
    return urllib.request.urlopen(req)


def noauth_GET(path):
    req = urllib.request.Request(f"{BASE}{path}")
    return urllib.request.urlopen(req)


class TestAuth:
    def test_no_token_returns_401(self):
        with pytest.raises(urllib.error.HTTPError) as exc:
            noauth_GET("/notes")
        assert exc.value.code == 401

    def test_wrong_token_returns_401(self):
        req = urllib.request.Request(f"{BASE}/notes")
        req.add_header("Authorization", "Bearer wrong-token")
        with pytest.raises(urllib.error.HTTPError) as exc:
            urllib.request.urlopen(req)
        assert exc.value.code == 401

    def test_valid_token_returns_200(self):
        resp = auth_GET("/notes")
        assert resp.status == 200


class TestCreate:
    def test_create_note(self):
        resp = auth_POST("/notes", {"title": "Test", "content": "Hello"})
        assert resp.status == 201
        data = json.loads(resp.read())
        assert data["title"] == "Test"
        assert data["content"] == "Hello"
        assert "id" in data

    def test_create_note_empty(self):
        resp = auth_POST("/notes", {})
        assert resp.status == 201
        data = json.loads(resp.read())
        assert data["title"] == ""


class TestRead:
    def test_list_notes(self):
        auth_POST("/notes", {"title": "A"})
        auth_POST("/notes", {"title": "B"})
        resp = auth_GET("/notes")
        data = json.loads(resp.read())
        assert isinstance(data, list)
        assert len(data) >= 2

    def test_get_single_note(self):
        resp = auth_POST("/notes", {"title": "Single"})
        note = json.loads(resp.read())
        resp2 = auth_GET(f"/notes/{note['id']}")
        assert resp2.status == 200
        data = json.loads(resp2.read())
        assert data["title"] == "Single"

    def test_get_nonexistent_returns_404(self):
        with pytest.raises(urllib.error.HTTPError) as exc:
            auth_GET("/notes/nonexistent123")
        assert exc.value.code == 404


class TestDelete:
    def test_delete_note(self):
        resp = auth_POST("/notes", {"title": "Delete me"})
        note = json.loads(resp.read())
        resp2 = auth_DELETE(f"/notes/{note['id']}")
        assert resp2.status == 200
        with pytest.raises(urllib.error.HTTPError) as exc:
            auth_GET(f"/notes/{note['id']}")
        assert exc.value.code == 404

    def test_delete_nonexistent_returns_404(self):
        with pytest.raises(urllib.error.HTTPError) as exc:
            auth_DELETE("/notes/nonexistent999")
        assert exc.value.code == 404

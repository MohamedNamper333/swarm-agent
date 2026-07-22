"""User API with DB + Cache integration."""

import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
from db import UserDB
from cache import Cache

db = UserDB()
cache = Cache(default_ttl=60)

TOKEN_STORE = {}


def issue_token(user):
    import secrets
    token = secrets.token_hex(16)
    TOKEN_STORE[token] = user["id"]
    return token


def check_auth(handler):
    auth = handler.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:]
        user_id = TOKEN_STORE.get(token)
        if user_id:
            return db.get_user(user_id)
    handler.send_response(401)
    handler.send_header("Content-Type", "application/json")
    handler.end_headers()
    handler.wfile.write(json.dumps({"error": "Unauthorized"}).encode())
    return None


class UserHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length)) if length else {}

        if self.path == "/register":
            user = db.create_user(
                body.get("username", ""),
                body.get("email", ""),
                body.get("password", ""),
                body.get("role", "user")
            )
            if user:
                token = issue_token(user)
                self._json(201, {"user": user, "token": token})
            else:
                self._json(409, {"error": "Username or email exists"})

        elif self.path == "/login":
            user = db.authenticate(body.get("username", ""), body.get("password", ""))
            if user:
                token = issue_token(user)
                self._json(200, {"user": user, "token": token})
            else:
                self._json(401, {"error": "Invalid credentials"})

        else:
            self._json(404, {"error": "Not found"})

    def do_GET(self):
        user = check_auth(self)
        if not user:
            return

        if self.path == "/users/me":
            cache_key = f"user:{user['id']}"
            cached = cache.get(cache_key)
            if cached:
                self._json(200, {**cached, "_cached": True})
            else:
                cache.set(cache_key, user)
                self._json(200, {**user, "_cached": False})

        elif self.path == "/users":
            if user["role"] != "admin":
                self._json(403, {"error": "Admin only"})
                return
            users = db.list_users()
            self._json(200, users)

        elif self.path.startswith("/users/"):
            uid = self.path.split("/")[-1]
            if user["role"] != "admin" and str(user["id"]) != uid:
                self._json(403, {"error": "Cannot view other users"})
                return
            cache_key = f"user:{uid}"
            cached = cache.get(cache_key)
            if cached:
                self._json(200, cached)
            else:
                target = db.get_user(int(uid))
                if target:
                    cache.set(cache_key, target)
                    self._json(200, target)
                else:
                    self._json(404, {"error": "User not found"})

        elif self.path == "/cache/stats":
            self._json(200, cache.stats())

        else:
            self._json(404, {"error": "Not found"})

    def do_PUT(self):
        user = check_auth(self)
        if not user:
            return

        if self.path.startswith("/users/") and self.path.endswith("/role"):
            if user["role"] != "admin":
                self._json(403, {"error": "Admin only"})
                return
            uid = self.path.split("/")[2]
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length)) if length else {}
            updated = db.update_role(int(uid), body.get("role", "user"))
            if updated:
                cache.invalidate_pattern(f"user:{uid}")
                self._json(200, updated)
            else:
                self._json(404, {"error": "User not found"})
        else:
            self._json(404, {"error": "Not found"})

    def do_DELETE(self):
        user = check_auth(self)
        if not user:
            return

        if self.path.startswith("/users/"):
            uid = self.path.split("/")[-1]
            if user["role"] != "admin":
                self._json(403, {"error": "Admin only"})
                return
            if db.delete_user(int(uid)):
                cache.invalidate_pattern(f"user:{uid}")
                self._json(200, {"deleted": int(uid)})
            else:
                self._json(404, {"error": "User not found"})
        else:
            self._json(404, {"error": "Not found"})

    def _json(self, code, data):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def log_message(self, format, *args):
        pass


def run(port=8098):
    server = HTTPServer(("127.0.0.1", port), UserHandler)
    print(f"User API running on http://127.0.0.1:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run()

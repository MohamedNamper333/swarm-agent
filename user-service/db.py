"""SQLite Database layer for user service."""

import sqlite3
import os
import hashlib

DB_PATH = os.path.join(os.path.dirname(__file__), "users.db")


class UserDB:
    def __init__(self, db_path=None):
        self.db_path = db_path or DB_PATH
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'user',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()

    def _hash(self, password):
        return hashlib.sha256(password.encode()).hexdigest()

    def create_user(self, username, email, password, role="user"):
        try:
            cursor = self.conn.execute(
                "INSERT INTO users (username, email, password_hash, role) VALUES (?, ?, ?, ?)",
                (username, email, self._hash(password), role)
            )
            self.conn.commit()
            return {"id": cursor.lastrowid, "username": username, "email": email, "role": role}
        except sqlite3.IntegrityError:
            return None

    def get_user(self, user_id):
        row = self.conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None

    def get_user_by_username(self, username):
        row = self.conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        return dict(row) if row else None

    def authenticate(self, username, password):
        row = self.conn.execute(
            "SELECT * FROM users WHERE username = ? AND password_hash = ?",
            (username, self._hash(password))
        ).fetchone()
        return dict(row) if row else None

    def update_role(self, user_id, role):
        self.conn.execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))
        self.conn.commit()
        return self.get_user(user_id)

    def delete_user(self, user_id):
        cursor = self.conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    def list_users(self):
        rows = self.conn.execute("SELECT * FROM users").fetchall()
        return [dict(r) for r in rows]

    def close(self):
        self.conn.close()

#!/usr/bin/env python3
"""Rollback v2 database to v1 schema (best effort)."""

import sqlite3
import sys


def rollback(v2_path: str, v1_path: str):
    """Rollback v2 database to v1 schema."""
    v2_conn = sqlite3.connect(v2_path)
    v2_conn.row_factory = sqlite3.Row

    v1_conn = sqlite3.connect(v1_path)

    # Create v1 schema
    v1_conn.executescript("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL,
            email TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE posts (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            body TEXT,
            published INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        CREATE TABLE tags (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE
        );
        CREATE TABLE post_tags (
            post_id INTEGER NOT NULL,
            tag_id INTEGER NOT NULL,
            PRIMARY KEY (post_id, tag_id),
            FOREIGN KEY (post_id) REFERENCES posts(id),
            FOREIGN KEY (tag_id) REFERENCES tags(id)
        );
    """)

    # Migrate users (email required in v1, use empty string if null)
    users = v2_conn.execute("SELECT * FROM users").fetchall()
    for u in users:
        email = u['email'] or f"{u['username']}@placeholder.local"
        v1_conn.execute(
            "INSERT INTO users (id, username, email, created_at) VALUES (?, ?, ?, ?)",
            (u['id'], u['username'], email, u['created_at'])
        )

    # Migrate posts (status → published flag)
    posts = v2_conn.execute("SELECT * FROM posts").fetchall()
    for p in posts:
        published = 1 if p['status'] == 'published' else 0
        v1_conn.execute(
            "INSERT INTO posts (id, user_id, title, body, published, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (p['id'], p['user_id'], p['title'], p['body'], published, p['created_at'])
        )

    # Tags — no changes
    tags = v2_conn.execute("SELECT * FROM tags").fetchall()
    for t in tags:
        v1_conn.execute("INSERT INTO tags (id, name) VALUES (?, ?)", (t['id'], t['name']))

    # Post_tags — no changes
    pt = v2_conn.execute("SELECT * FROM post_tags").fetchall()
    for row in pt:
        v1_conn.execute(
            "INSERT INTO post_tags (post_id, tag_id) VALUES (?, ?)",
            (row['post_id'], row['tag_id'])
        )

    v1_conn.commit()
    v2_conn.close()
    v1_conn.close()
    print(f"Rollback complete: {v2_path} → {v1_path}")
    print(f"  Users: {len(users)}, Posts: {len(posts)}, Tags: {len(tags)}")
    print("  Note: comments, user_settings, and migration_log are NOT preserved (v1 has no such tables)")


if __name__ == "__main__":
    v2 = sys.argv[1] if len(sys.argv) > 1 else "v2.db"
    v1 = sys.argv[2] if len(sys.argv) > 2 else "v1_rollback.db"
    rollback(v2, v1)

#!/usr/bin/env python3
"""Test suite for database migration v1 → v2."""

import os
import sqlite3
import sys
import tempfile

sys.path.insert(0, os.path.dirname(__file__))
from migrate import generate_slug, make_unique_slug, migrate
from rollback import rollback

PASS = 0
FAIL = 0


def test(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        print(f"  ❌ {name} — {detail}")


def get_db(path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def setup_v1_db(path):
    conn = sqlite3.connect(path)
    with open(os.path.join(os.path.dirname(__file__), "v1_schema.sql")) as f:
        conn.executescript(f.read())
    conn.close()


def test_slug_generation():
    print("\n[Slug Generation]")
    test("simple title", generate_slug("Hello World") == "hello-world")
    test("special chars removed", generate_slug("Hello! @World#") == "hello-world")
    test("multiple spaces", generate_slug("Hello   World") == "hello-world")
    test("empty title", generate_slug("") == "untitled")
    test("unicode stripped", generate_slug("Café au Lait") == "caf-au-lait")
    test("trailing hyphens stripped", generate_slug("---Hello---") == "hello")

    used = {"hello-world"}
    test("unique slug (first)", make_unique_slug("hello-world", used) == "hello-world-2")
    used.add("hello-world-2")
    test("unique slug (collision)", make_unique_slug("hello-world", used) == "hello-world-3")


def test_migration():
    print("\n[Migration v1 → v2]")
    with tempfile.TemporaryDirectory() as tmp:
        v1_path = os.path.join(tmp, "v1.db")
        v2_path = os.path.join(tmp, "v2.db")
        setup_v1_db(v1_path)
        migrate(v1_path, v2_path)

        v2 = get_db(v2_path)

        # Users preserved
        users = v2.execute("SELECT * FROM users ORDER BY id").fetchall()
        test("users count", len(users) == 2, f"got {len(users)}")
        test("alice preserved", users[0]['username'] == 'alice')
        test("bob preserved", users[1]['username'] == 'bob')
        test("display_name column exists", users[0]['display_name'] is None)
        test("is_active default", users[0]['is_active'] == 1)

        # Posts migrated with status
        posts = v2.execute("SELECT * FROM posts ORDER BY id").fetchall()
        test("posts count", len(posts) == 3, f"got {len(posts)}")
        test("published post status", posts[0]['status'] == 'published')
        test("draft post status", posts[1]['status'] == 'draft')
        test("slug generated", posts[0]['slug'] == 'hello-world')
        test("slug uniqueness", posts[1]['slug'] == 'draft-post')
        test("published_at set for published", posts[0]['published_at'] is not None)
        test("published_at null for draft", posts[1]['published_at'] is None)

        # Tags preserved
        tags = v2.execute("SELECT * FROM tags ORDER BY id").fetchall()
        test("tags count", len(tags) == 2)

        # Post_tags preserved
        pt = v2.execute("SELECT * FROM post_tags ORDER BY post_id, tag_id").fetchall()
        test("post_tags count", len(pt) == 4)

        # New tables exist and empty
        test("comments table exists", v2.execute("SELECT COUNT(*) FROM comments").fetchone()[0] == 0)
        test("user_settings table exists", v2.execute("SELECT COUNT(*) FROM user_settings").fetchone()[0] == 0)

        # Migration log
        log = v2.execute("SELECT * FROM migration_log").fetchall()
        test("migration log entries", len(log) >= 4, f"got {len(log)}")
        test("migration complete logged", any(r['step'] == 'migration_complete' for r in log))

        v2.close()


def test_empty_db():
    print("\n[Edge: Empty DB]")
    with tempfile.TemporaryDirectory() as tmp:
        v1_path = os.path.join(tmp, "v1.db")
        v2_path = os.path.join(tmp, "v2.db")
        conn = sqlite3.connect(v1_path)
        conn.close()
        migrate(v1_path, v2_path)
        v2 = get_db(v2_path)
        test("empty users", v2.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0)
        test("empty posts", v2.execute("SELECT COUNT(*) FROM posts").fetchone()[0] == 0)
        test("schema valid", v2.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall())
        v2.close()


def test_special_chars_title():
    print("\n[Edge: Special Characters]")
    with tempfile.TemporaryDirectory() as tmp:
        v1_path = os.path.join(tmp, "v1.db")
        v2_path = os.path.join(tmp, "v2.db")
        conn = sqlite3.connect(v1_path)
        conn.executescript("""
            CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT, email TEXT, created_at TEXT);
            CREATE TABLE posts (id INTEGER PRIMARY KEY, user_id INTEGER, title TEXT, body TEXT, published INTEGER, created_at TEXT);
            CREATE TABLE tags (id INTEGER PRIMARY KEY, name TEXT);
            CREATE TABLE post_tags (post_id INTEGER, tag_id INTEGER);
            INSERT INTO users VALUES (1, 'test', 'test@test.com', datetime('now'));
            INSERT INTO posts VALUES (1, 1, 'C++ vs C# — What''s the Difference?', 'body', 1, datetime('now'));
            INSERT INTO posts VALUES (2, 1, '🔥 Hot Take: Tabs > Spaces', 'body', 0, datetime('now'));
        """)
        conn.close()
        migrate(v1_path, v2_path)
        v2 = get_db(v2_path)
        posts = v2.execute("SELECT * FROM posts ORDER BY id").fetchall()
        test("special char slug 1", posts[0]['slug'] == 'c-vs-c-whats-the-difference')
        test("emoji slug 2", 'hot-take' in posts[1]['slug'])
        v2.close()


def test_rollback():
    print("\n[Rollback v2 → v1]")
    with tempfile.TemporaryDirectory() as tmp:
        v1_path = os.path.join(tmp, "v1.db")
        v2_path = os.path.join(tmp, "v2.db")
        v1_rb_path = os.path.join(tmp, "v1_rollback.db")
        setup_v1_db(v1_path)
        migrate(v1_path, v2_path)
        rollback(v2_path, v1_rb_path)

        v1 = get_db(v1_rb_path)
        users = v1.execute("SELECT * FROM users ORDER BY id").fetchall()
        test("rollback users count", len(users) == 2)
        test("rollback alice email", users[0]['email'] == 'alice@example.com')

        posts = v1.execute("SELECT * FROM posts ORDER BY id").fetchall()
        test("rollback posts count", len(posts) == 3)
        test("rollback published flag", posts[0]['published'] == 1)
        test("rollback draft flag", posts[1]['published'] == 0)

        tags = v1.execute("SELECT * FROM tags").fetchall()
        test("rollback tags", len(tags) == 2)

        pt = v1.execute("SELECT * FROM post_tags").fetchall()
        test("rollback post_tags", len(pt) == 4)

        v1.close()


if __name__ == "__main__":
    print("=" * 50)
    print("VERY HARD: Database Migration Test Suite")
    print("=" * 50)
    test_slug_generation()
    test_migration()
    test_empty_db()
    test_special_chars_title()
    test_rollback()

    print(f"\n{'=' * 50}")
    print(f"Results: {PASS} passed, {FAIL} failed, {PASS + FAIL} total")
    print(f"{'=' * 50}")
    sys.exit(1 if FAIL > 0 else 0)

#!/usr/bin/env python3
"""Database migration v1 → v2 for blog database."""

import sqlite3
import re
import sys
from datetime import datetime


def generate_slug(title: str) -> str:
    """Generate URL-friendly slug from title."""
    slug = title.lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = slug.strip('-')
    return slug or 'untitled'


def make_unique_slug(slug: str, existing_slugs: set) -> str:
    """Ensure slug is unique by appending -N if needed."""
    if slug not in existing_slugs:
        return slug
    counter = 2
    while f"{slug}-{counter}" in existing_slugs:
        counter += 1
    return f"{slug}-{counter}"


def migrate(v1_path: str, v2_path: str):
    """Migrate v1 database to v2 schema."""
    v1_conn = sqlite3.connect(v1_path)
    v1_conn.row_factory = sqlite3.Row

    # Check if v1 has tables
    v1_tables = {r[0] for r in v1_conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}

    v2_conn = sqlite3.connect(v2_path)

    # Create v2 schema
    v2_conn.executescript("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL,
            email TEXT,
            display_name TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE posts (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            slug TEXT NOT NULL UNIQUE,
            body TEXT,
            status TEXT DEFAULT 'draft' CHECK(status IN ('draft', 'published', 'archived')),
            published_at TEXT,
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
        CREATE TABLE comments (
            id INTEGER PRIMARY KEY,
            post_id INTEGER NOT NULL,
            author_name TEXT NOT NULL,
            body TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (post_id) REFERENCES posts(id)
        );
        CREATE TABLE user_settings (
            user_id INTEGER NOT NULL,
            key TEXT NOT NULL,
            value TEXT,
            PRIMARY KEY (user_id, key),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        CREATE TABLE migration_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            step TEXT NOT NULL,
            status TEXT NOT NULL,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP
        );
    """)

    log = lambda step, status: v2_conn.execute(
        "INSERT INTO migration_log (step, status) VALUES (?, ?)", (step, status)
    )

    # Step 1: Migrate users
    users = v1_conn.execute("SELECT * FROM users").fetchall() if 'users' in v1_tables else []
    for u in users:
        v2_conn.execute(
            "INSERT INTO users (id, username, email, created_at) VALUES (?, ?, ?, ?)",
            (u['id'], u['username'], u['email'], u['created_at'])
        )
    log('migrate_users', f'{len(users)} rows')

    # Step 2: Migrate posts with slug generation + status mapping
    posts = v1_conn.execute("SELECT * FROM posts").fetchall() if 'posts' in v1_tables else []
    used_slugs = set()
    for p in posts:
        slug = make_unique_slug(generate_slug(p['title']), used_slugs)
        used_slugs.add(slug)
        status = 'published' if p['published'] else 'draft'
        published_at = p['created_at'] if p['published'] else None
        v2_conn.execute(
            """INSERT INTO posts (id, user_id, title, slug, body, status, published_at, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (p['id'], p['user_id'], p['title'], slug, p['body'], status, published_at, p['created_at'])
        )
    log('migrate_posts', f'{len(posts)} rows')

    # Step 3: Migrate tags
    tags = v1_conn.execute("SELECT * FROM tags").fetchall() if 'tags' in v1_tables else []
    for t in tags:
        v2_conn.execute("INSERT INTO tags (id, name) VALUES (?, ?)", (t['id'], t['name']))
    log('migrate_tags', f'{len(tags)} rows')

    # Step 4: Migrate post_tags
    pt = v1_conn.execute("SELECT * FROM post_tags").fetchall() if 'post_tags' in v1_tables else []
    for row in pt:
        v2_conn.execute(
            "INSERT INTO post_tags (post_id, tag_id) VALUES (?, ?)",
            (row['post_id'], row['tag_id'])
        )
    log('migrate_post_tags', f'{len(pt)} rows')

    log('migration_complete', 'success')

    v2_conn.commit()
    v1_conn.close()
    v2_conn.close()
    print(f"Migration complete: {v1_path} → {v2_path}")
    print(f"  Users: {len(users)}, Posts: {len(posts)}, Tags: {len(tags)}, Post_Tags: {len(pt)}")


if __name__ == "__main__":
    v1 = sys.argv[1] if len(sys.argv) > 1 else "v1.db"
    v2 = sys.argv[2] if len(sys.argv) > 2 else "v2.db"
    migrate(v1, v2)

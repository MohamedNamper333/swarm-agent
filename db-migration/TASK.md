# VERY HARD: Database Migration v1 → v2

## Context
We have a blog database in v1 (see `v1_schema.sql`). We need to migrate to v2 with these changes:

### v2 Schema Changes
1. **Users table**: Add `display_name` (TEXT, nullable), add `is_active` (INTEGER DEFAULT 1). Make `email` nullable (some users register via OAuth without email).
2. **Posts table**: Add `slug` (TEXT, NOT NULL, UNIQUE), add `status` TEXT (enum: 'draft', 'published', 'archived'), add `published_at` (TEXT, nullable). Remove `published` INTEGER column. Migrate: published=1 → status='published', published=0 → status='draft'.
3. **Tags table**: No changes.
4. **Post_tags table**: No changes.
5. **New table**: `comments` (id, post_id, author_name, body, created_at).
6. **New table**: `user_settings` (user_id, key, value — composite primary key on user_id+key).

## Requirements
1. **Migration script** (`migrate.py`): Reads v1 SQLite DB, transforms data, writes v2 SQLite DB. Must:
   - Handle all data transformations (published → status, etc.)
   - Auto-generate slugs from titles (lowercase, replace spaces with hyphens, strip special chars)
   - Preserve all existing data (no data loss)
   - Create empty v2 tables (comments, user_settings)
   - Create a migration log table `migration_log` (id, step, status, timestamp)

2. **Rollback script** (`rollback.py`): Can restore v2 DB back to v1 format (best effort — new tables data is lost, but existing data preserved).

3. **Test suite** (`test_migration.py`): At least 12 tests covering:
   - All users migrated with correct data
   - All posts migrated with correct status mapping
   - Slugs generated correctly (special chars, spaces, duplicates)
   - Tags and post_tags preserved
   - New tables exist and are empty
   - Migration log recorded
   - Rollback produces valid v1 schema
   - Edge cases: empty DB, special characters in titles, duplicate slugs

## Files
- `v1_schema.sql` — provided (v1 schema + seed data)
- `migrate.py` — YOU create this
- `rollback.py` — YOU create this
- `test_migration.py` — YOU create this

## Verification
```bash
cd /home/kali/.config/opencode/db-migration
python3 -c "import sqlite3; conn=sqlite3.connect(':memory:'); exec(open('v1_schema.sql').read()); print('v1 schema OK')"
python3 test_migration.py
```

All 12+ tests must pass.

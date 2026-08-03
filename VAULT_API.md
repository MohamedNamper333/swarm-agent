---
title: "Vault REST API — Client & Server Reference"
type: "reference"
status: "approved"
version: "2.0.0"
date: "2026-08-03"
author: "swarm-agent"
tags: ["swarm", "vault", "api", "client", "server", "obsidian"]
difficulty: "easy"
pipeline: "LITE"
test_id: "VAULT-API"
related_files: [
  "SWARM-INDEX-000.md",
  "SWARM-PROJECT-MAP.md",
  "vault_client.py",
  "vault_server.py"
]
---

# 🐝 Vault REST API — Client & Server Reference

## Overview

The Swarm Agent System uses **Obsidian Vault** as its persistent memory layer via a REST API. The system consists of:

- **`vault_server.py`** — HTTP server (`localhost:27123`) serving `/home/kali/Documents/Obsidian Vault`
- **`vault_client.py`** — Python REST wrapper for agents to interact with the vault

**Base URL:** `http://localhost:27123`  
**Auth:** Bearer token `swarm-evolution-2025` (configurable via `VAULT_API_KEY`)  
**Vault Path:** `/home/kali/Documents/Obsidian Vault` (configurable via `VAULT_PATH`)

---

## Server: `vault_server.py`

### Quick Start

```bash
# Start server (runs in background)
python3 vault_server.py &

# Verify running
curl http://localhost:27123/health
# {"status": "healthy"}
```

### Configuration (Environment Variables)

| Variable | Default | Description |
|----------|---------|-------------|
| `VAULT_PATH` | `/home/kali/Documents/Obsidian Vault` | Path to Obsidian vault |
| `VAULT_API_KEY` | `swarm-evolution-2025` | Bearer token for auth |
| `VAULT_PORT` | `27123` | Server port |
| `MEILI_URL` | `http://127.0.0.1:7700` | Meilisearch URL |
| `MEILI_ADMIN_KEY` | (from env) | Meilisearch admin key |

### Endpoints

#### Health & Info
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/` | ❌ | Service info + endpoint list |
| GET | `/health` | ❌ | Health check |

#### Vault Operations
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/vault/` | ✅ | List root files/folders |
| GET | `/vault/{path}` | ✅ | Read file OR list directory |
| PUT | `/vault/{path}` | ✅ | Create/overwrite file |
| POST | `/vault/{path}` | ✅ | Append to file |
| PATCH | `/vault/{path}` | ✅ | Patch with JSON operations |
| DELETE | `/vault/{path}` | ✅ | Delete file |

#### Search
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/search/?query=...` | ✅ | Full-text search (MCP format) |
| GET | `/search/simple/?query=...` | ✅ | Simple search |
| POST | `/search/` | ✅ | Advanced search (JSON Logic) |
| POST | `/search/simple/` | ✅ | Simple search (POST) |

#### Metadata
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/tags/` | ✅ | List all tags with counts |
| GET | `/commands/` | ✅ | List Obsidian commands |
| POST | `/commands/{id}` | ✅ | Execute command |

#### Periodic Notes
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/periodic/{period}/` | ✅ | Latest periodic note |
| GET | `/periodic/{period}/{YYYY}/{MM}/{DD}/` | ✅ | Specific date note |

*Periods: `daily`, `weekly`, `monthly`, `quarterly`, `yearly`*

#### Meilisearch Proxy
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| * | `/api/meili/*` | ❌ (Meilisearch handles auth) | Proxy to Meilisearch |

#### Dashboard
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/dashboard/` | ❌ | Meilisearch dashboard HTML |

#### Active File (Obsidian Integration)
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/active/` | ✅ | Currently active file (404 if Obsidian not running) |
| GET | `/open/{path}` | ✅ | Open file in Obsidian |
| POST | `/open/{path}` | ✅ | Open file in Obsidian |

---

### Request/Response Formats

#### List Files (`GET /vault/` or `GET /vault/{dir}/`)
```json
{
  "files": [
    {
      "path": "folder/file.md",
      "basename": "file.md",
      "type": "file",
      "size": 1024,
      "ctime": 1699999999000,
      "mtime": 1699999999000
    },
    {
      "path": "folder/",
      "basename": "folder",
      "type": "directory",
      "size": 0,
      "ctime": 1699999999000,
      "mtime": 1699999999000
    }
  ]
}
```

#### Read Note (`GET /vault/{path}`)
**Default (text/markdown):**
```
# Note Title

Content here...
```

**JSON Format (`Accept: application/vnd.olrapi.note+json`):**
```json
{
  "path": "folder/note.md",
  "content": "# Note Title\n\nContent...",
  "size": 1024,
  "frontmatter": {"title": "Note Title", "tags": ["swarm"]},
  "tags": ["swarm", "test"],
  "stat": {"size": 1024, "ctime": 1699999999000, "mtime": 1699999999000}
}
```

#### Write Note (`PUT /vault/{path}`)
```bash
curl -X PUT -H "Authorization: Bearer swarm-evolution-2025" \
  -H "Content-Type: text/markdown" \
  -d "# New Note\n\nContent here" \
  http://localhost:27123/vault/New%20Note.md
```
**Response:**
```json
{"status": "OK", "path": "New Note.md"}
```

#### Append Note (`POST /vault/{path}`)
```bash
curl -X POST -H "Authorization: Bearer swarm-evolution-2025" \
  -H "Content-Type: text/markdown" \
  -d "\n\nNew entry" \
  http://localhost:27123/vault/Existing%20Note.md
```

#### Patch Note (`PATCH /vault/{path}`)
```bash
curl -X PATCH -H "Authorization: Bearer swarm-evolution-2025" \
  -H "Content-Type: application/json" \
  -H "Operation: replace" \
  -H "Target-Type: heading" \
  -H "Target: ## Section" \
  -d '"New content for section"' \
  http://localhost:27123/vault/Note.md
```

#### Search (`GET /search/?query=...&contextLength=100`)
**MCP Format (default):**
```json
{
  "hits": [
    {
      "matches": [
        {
          "match": {
            "filename": "note.md",
            "path": "folder/note.md",
            "line": 5,
            "text": "search term found here",
            "context": "context around match"
          }
        }
      ]
    }
  ]
}
```

#### Tags (`GET /tags/`)
```json
{
  "tags": [
    {"name": "swarm", "count": 15},
    {"name": "test", "count": 8}
  ]
}
```

#### Periodic Notes (`GET /periodic/daily/`)
```json
{
  "path": "Daily/2026-08-03.md",
  "content": "# Daily Note\n\nContent...",
  "period": "daily",
  "date": "2026-08-03"
}
```

---

## Client: `vault_client.py`

### Quick Start

```python
from vault_client import get_vault_client

client = get_vault_client()

# Check connection
if client.health_check():
    print("✅ Connected to vault server")
else:
    print("❌ Vault server not running")
```

### Class: `VaultClient`

```python
class VaultClient:
    def __init__(self, base_url: str = "http://localhost:27123", 
                 api_key: str = "swarm-evolution-2025"):
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
```

### Vault Operations

| Method | Signature | Returns |
|--------|-----------|---------|
| `list_files` | `list_files(path: str = "")` | `List[Dict]` — files/folders |
| `read_note` | `read_note(path: str, format: str = "text")` | `str` or `Dict` (if format="json") |
| `write_note` | `write_note(path: str, content: str)` | `Dict` — `{"path": "...", "created": true, "currentSizeInBytes": N}` |
| `append_note` | `append_note(path: str, content: str)` | `Dict` |
| `patch_note` | `patch_note(path: str, operations: List[Dict])` | `Dict` |
| `delete_note` | `delete_note(path: str)` | `Dict` |

### Search Operations

| Method | Signature | Returns |
|--------|-----------|---------|
| `search` | `search(query: str, context_length: int = 100, flat: bool = True)` | `List[Dict]` — flattened matches |
| `search_simple` | `search_simple(query: str, context_length: int = 100, flat: bool = True)` | `List[Dict]` — simple format |

**Flat=True** returns standardized list:
```python
[
    {"filename": "note.md", "path": "folder/note.md", "line": 5, "text": "...", "context": "..."},
    ...
]
```

### Metadata

| Method | Signature | Returns |
|--------|-----------|---------|
| `list_tags` | `list_tags()` | `List[Dict]` — `[{"name": "tag", "count": 5}, ...]` |
| `list_commands` | `list_commands()` | `List[Dict]` — Obsidian commands |
| `execute_command` | `execute_command(command_id: str)` | `Dict` |

### Utilities

| Method | Signature | Returns |
|--------|-----------|---------|
| `health_check` | `health_check()` | `bool` — True if server responds |

### Convenience Function

```python
def get_vault_client() -> VaultClient:
    """Get configured vault client with defaults."""
    return VaultClient()
```

---

## Usage Examples

### Python (Recommended)

```python
from vault_client import get_vault_client

client = get_vault_client()

if not client.health_check():
    raise RuntimeError("Vault server not running")

# List files
files = client.list_files("Swarm Agent/")
for f in files:
    print(f"  {f['path']} ({f['type']})")

# Read note
content = client.read_note("Swarm Agent/TEST-RESULTS.md")
print(content[:200])

# Read as JSON (with frontmatter, tags)
note = client.read_note("Swarm Agent/TEST-RESULTS.md", format="json")
print(f"Tags: {note['tags']}")
print(f"Frontmatter: {note['frontmatter']}")

# Write note
result = client.write_note("Swarm Agent/new.md", "# New Note\n\nContent here")
print(f"Created: {result['created']}")

# Append
client.append_note("Swarm Agent/log.md", "\n\nNew entry at " + datetime.now().isoformat())

# Search
results = client.search("swarm", context_length=100)
for r in results[:3]:
    print(f"  {r['path']} line {r['line']}: {r['text'][:80]}")

# Tags
tags = client.list_tags()
for t in tags[:5]:
    print(f"  #{t['name']} ({t['count']})")
```

### Direct HTTP (cURL)

```bash
# List files
curl -H "Authorization: Bearer swarm-evolution-2025" \
  http://localhost:27123/vault/

# Read note
curl -H "Authorization: Bearer swarm-evolution-2025" \
  http://localhost:27123/vault/Swarm%20Agent/TEST-RESULTS.md

# Write note
curl -X PUT -H "Authorization: Bearer swarm-evolution-2025" \
  -H "Content-Type: text/markdown" \
  -d '# New Note\n\nContent' \
  http://localhost:27123/vault/Swarm%20Agent/new.md

# Search
curl -H "Authorization: Bearer swarm-evolution-2025" \
  "http://localhost:27123/search/?query=swarm&contextLength=100"

# Tags
curl -H "Authorization: Bearer swarm-evolution-2025" \
  http://localhost:27123/tags/
```

---

## Quick Test

```bash
cd /home/kali/swarm-agent
python3 vault_client.py
```

**Expected Output:**
```
✅ Vault server connected

📁 Files (N):
  Swarm Agent/ (directory)
  ...

🔍 Search 'swarm' (N results):
  Swarm Agent/TEST-RESULTS.md - score: 15

🏷️ Tags (N):
  #swarm (15)
  #test (8)
  ...
```

---

## Notes for Agents

- **Always use `vault_client.py`** — handles auth, errors, response parsing
- **Path encoding** — spaces become `%20` in URLs (client handles this)
- **Search format** — returns MCP-compatible `hits` structure; `flat=True` flattens to simple list
- **Health check** — call `client.health_check()` before operations
- **Frontmatter** — YAML frontmatter auto-extracted in JSON format
- **Tags** — `#tag` syntax auto-extracted from markdown content
- **Meilisearch** — For production search performance, ensure Meilisearch runs on port 7700

---

## File Locations

| File | Path | Description |
|------|------|-------------|
| Server | `/home/kali/swarm-agent/vault_server.py` | HTTP server |
| Client | `/home/kali/swarm-agent/vault_client.py` | REST wrapper |
| Test | `/home/kali/swarm-agent/test_swarm_routing.py` | Includes vault health check |

---

*Generated by Swarm Vault Writer v2.0.0 — 6-layer methodology*
*Based on actual vault_client.py and vault_server.py implementations*
# Vault REST API - Quick Reference for Agents

## Base URL
```
http://localhost:27123
```

## Headers (Required)
```python
headers = {
    "Authorization": "Bearer swarm-evolution-2025",
    "Content-Type": "application/json"
}
```

## Using the Python Client (Recommended)
```python
from vault_client import get_vault_client

client = get_vault_client()

# Check connection
if client.health_check():
    print("✅ Connected")
```

## Endpoints

### 📁 List Files
```python
# Root
files = client.list_files()

# Subdirectory
files = client.list_files("Swarm Agent/")
```
**Response:** `List[Dict]` with `path`, `basename`, `type` (file/directory), `size`, `ctime`, `mtime`

---

### 📖 Read Note
```python
# As text
content = client.read_note("Swarm Agent/TEST-RESULTS.md")

# As JSON (with frontmatter, tags, stats)
note = client.read_note("Swarm Agent/TEST-RESULTS.md", format="json")
```
**Response:** String (text) or Dict with `path`, `content`, `frontmatter`, `tags`, `stat`

---

### ✏️ Write Note (Create/Overwrite)
```python
result = client.write_note("Swarm Agent/new.md", "# New Note\n\nContent here")
```
**Response:** Dict with `path`, `created`, `currentSizeInBytes`

---

### ➕ Append to Note
```python
result = client.append_note("Swarm Agent/log.md", "\n\nNew entry")
```

---

### 🔍 Search (Full-text)
```python
# Standard format
results = client.search("swarm", context_length=100)

# Returns List[Dict] with:
# - path, filename, matches (list of {line, text, context})
```
**Example result:**
```json
{
  "path": "Swarm Agent/TEST-RESULTS.md",
  "matches": [
    {"line": 1, "text": "# Swarm Agent — Full Test Results", "context": "..."}
  ]
}
```

---

### 🏷️ List Tags
```python
tags = client.list_tags()
# Returns: [{"name": "tag", "count": 5}, ...]
```

---

### ⚡ Commands
```python
commands = client.list_commands()
result = client.execute_command("app:go-back")
```

---

## Direct HTTP (if no Python)

### List files
```bash
curl -H "Authorization: Bearer swarm-evolution-2025" \
  http://localhost:27123/vault/
```

### Read note
```bash
curl -H "Authorization: Bearer swarm-evolution-2025" \
  http://localhost:27123/vault/Swarm%20Agent/TEST-RESULTS.md
```

### Write note
```bash
curl -X POST -H "Authorization: Bearer swarm-evolution-2025" \
  -H "Content-Type: application/json" \
  -d '{"content": "# New Note\n\nContent"}' \
  http://localhost:27123/vault/Swarm%20Agent/new.md
```

### Search
```bash
curl -H "Authorization: Bearer swarm-evolution-2025" \
  "http://localhost:27123/search/?query=swarm&contextLength=100"
```

---

## Quick Test
```bash
cd /home/kali/.config/opencode
python3 vault_client.py
```
Expected: ✅ Vault server connected + file listing + search results

---

## Notes for Agents
- **Always use `vault_client.py`** - handles auth, errors, response parsing
- **Path encoding** - spaces become `%20` in URLs (client handles this)
- **Search format** - returns MCP-compatible `hits` structure
- **Health check** - call `client.health_check()` before operations

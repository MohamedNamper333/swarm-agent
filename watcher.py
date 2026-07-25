#!/usr/bin/env python3
"""
AL-MUKH Enhanced Watcher v2.0
Real-time file system monitor with exclusion patterns, health endpoint, and batch indexing
"""
import os
import sys
import time
import json
import hashlib
import signal
import threading
import http.server
from pathlib import Path
from datetime import datetime, timezone
from collections import deque

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False

import urllib.request
import urllib.error

# ─── Configuration ───────────────────────────────────────────────────────────
MEILI_URL = os.environ.get("MEILI_URL", "http://127.0.0.1:7700")
MEILI_KEY = os.environ.get("MEILI_MASTER_KEY", "mukh-dev-key-change-in-prod")
INDEX_NAME = "mukh-unified"
HEALTH_PORT = 8765

EXCLUDE_PATTERNS = [
    ".obsidian", ".git", ".trash", "__pycache__",
    ".DS_Store", "*.tmp", "*.swp", "*.bak", "*.orig"
]

SPOKE_ROOTS = [
    "/home/kali/Documents/Obsidian Vault"
]

MAX_FILE_SIZE_MB = 100
DEBOUNCE_MS = 200
BATCH_SIZE = 50

# ─── Helpers ─────────────────────────────────────────────────────────────────
def content_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]

def is_excluded(path):
    parts = Path(path).parts
    for pattern in EXCLUDE_PATTERNS:
        if pattern.startswith("*"):
            if any(p.endswith(pattern[1:]) for p in parts):
                return True
        elif pattern in parts or pattern in path:
            return True
    return False

def safe_getsize(path):
    try:
        return os.path.getsize(path)
    except OSError:
        return 0

def parse_frontmatter(content):
    """Extract YAML frontmatter from markdown"""
    if content.startswith("---"):
        end = content.find("---", 3)
        if end > 0:
            return content[3:end].strip(), content[end+3:].strip()
    return "", content

def extract_tags(content):
    """Extract hashtags and frontmatter tags"""
    tags = set()
    # Frontmatter tags
    fm, body = parse_frontmatter(content)
    for line in fm.split("\n"):
        if line.strip().startswith("tags:"):
            for t in line.split(":")[1].split(","):
                t = t.strip().strip("[]\"'")
                if t:
                    tags.add(t)
    # Inline hashtags
    import re
    for match in re.finditer(r"(?<!\w)#([a-zA-Z_]\w*)", body):
        tags.add(match.group(1))
    return list(tags)

def extract_headings(content):
    """Extract markdown headings"""
    import re
    return [m.group(1).strip() for m in re.finditer(r"^#{1,6}\s+(.+)$", content, re.MULTILINE)]

# ─── Vault Handler ───────────────────────────────────────────────────────────
class VaultHandler(FileSystemEventHandler):
    def __init__(self):
        self.pending = {}
        self.stats = {"created": 0, "modified": 0, "deleted": 0, "errors": 0}
        self.lock = threading.Lock()
        self.event_log = deque(maxlen=1000)

    def on_any_event(self, event):
        if event.is_directory:
            return
        src = event.event_type + ":" + event.src_path
        if event.event_type in ("created", "modified", "moved"):
            self.pending[src] = (event.src_path, time.time())
        elif event.event_type == "deleted":
            self.index_deleted(event.src_path)

    def index_deleted(self, path):
        if is_excluded(path) or not path.endswith(".md"):
            return
        doc_id = hashlib.md5(path.encode()).hexdigest()
        try:
            req = urllib.request.Request(
                f"{MEILI_URL}/indexes/{INDEX_NAME}/documents/{doc_id}",
                headers={"Authorization": f"Bearer {MEILI_KEY}"},
                method="DELETE"
            )
            urllib.request.urlopen(req)
            with self.lock:
                self.stats["deleted"] += 1
            self.log_event("deleted", path, "ok")
        except Exception as e:
            self.log_event("deleted", path, f"error: {e}")

    def process_pending(self):
        now = time.time()
        batch = []
        keys_to_remove = []

        for key, (path, ts) in list(self.pending.items()):
            if now - ts > DEBOUNCE_MS / 1000.0:
                keys_to_remove.append(key)
                if not is_excluded(path) and path.endswith(".md"):
                    batch.append(path)

        for k in keys_to_remove:
            del self.pending[k]

        if batch:
            self.index_batch(batch[:BATCH_SIZE])

    def index_batch(self, paths):
        docs = []
        for path in paths:
            try:
                size = safe_getsize(path)
                if size > MAX_FILE_SIZE_MB * 1024 * 1024:
                    self.log_event("skip", path, "too large")
                    continue
                if size == 0:
                    continue

                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    content = fm_content = f.read()

                fm, body = parse_frontmatter(content)
                tags = extract_tags(content)
                headings = extract_headings(body)
                namespace = self.resolve_namespace(path)

                doc = {
                    "id": hashlib.md5(path.encode()).hexdigest(),
                    "path": path,
                    "filename": os.path.basename(path),
                    "content": body[:10000],
                    "frontmatter": fm[:2000] if fm else "",
                    "tags": tags,
                    "headings": headings[:20],
                    "namespace": namespace,
                    "size": size,
                    "modified": datetime.fromtimestamp(os.path.getmtime(path)).isoformat(),
                    "indexed_at": datetime.now(timezone.utc).isoformat(),
                    "content_hash": content_hash(content)
                }
                docs.append(doc)
            except Exception as e:
                self.log_event("error", path, str(e))
                with self.lock:
                    self.stats["errors"] += 1

        if docs:
            self.send_to_meili(docs)

    def send_to_meili(self, docs):
        try:
            data = json.dumps(docs).encode("utf-8")
            req = urllib.request.Request(
                f"{MEILI_URL}/indexes/{INDEX_NAME}/documents",
                data=data,
                headers={
                    "Authorization": f"Bearer {MEILI_KEY}",
                    "Content-Type": "application/json"
                },
                method="POST"
            )
            urllib.request.urlopen(req, timeout=10)
            for doc in docs:
                self.log_event("indexed", doc["path"], "ok")
                with self.lock:
                    self.stats["created" if "created" in doc.get("indexed_at", "") else "modified"] += 1
        except Exception as e:
            self.log_event("batch_error", f"{len(docs)} docs", str(e))
            with self.lock:
                self.stats["errors"] += 1

    def resolve_namespace(self, path):
        for root in SPOKE_ROOTS:
            if path.startswith(root):
                rel = os.path.relpath(path, root)
                parts = Path(rel).parts
                if parts:
                    return parts[0]
        return "unknown"

    def log_event(self, event_type, path, status):
        entry = {
                "ts": datetime.now(timezone.utc).isoformat(),
            "event": event_type,
            "path": path,
            "status": status
        }
        self.event_log.append(entry)

    def get_stats(self):
        with self.lock:
            return dict(self.stats)

# ─── Health Server ───────────────────────────────────────────────────────────
class HealthHandler(http.server.BaseHTTPRequestHandler):
    watcher = None

    def do_GET(self):
        if self.path == "/health":
            stats = self.watcher.get_stats() if self.watcher else {}
            resp = {
                "status": "ok",
                "meilisearch": self.check_meili(),
                "watched_paths": len(SPOKE_ROOTS),
                "stats": stats,
                "uptime": time.time() - START_TIME
            }
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(resp, indent=2).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def check_meili(self):
        try:
            req = urllib.request.Request(
                f"{MEILI_URL}/health",
                headers={"Authorization": f"Bearer {MEILI_KEY}"}
            )
            urllib.request.urlopen(req, timeout=2)
            return "available"
        except Exception:
            return "unavailable"

    def log_message(self, format, *args):
        pass  # Suppress logs

START_TIME = time.time()

# ─── Main ────────────────────────────────────────────────────────────────────
def main():
    print("[AL-MUKH Watcher v2.0] Starting...")

    if not WATCHDOG_AVAILABLE:
        print("[FATAL] watchdog not installed. Run: pip install watchdog")
        sys.exit(1)

    handler = VaultHandler()
    HealthHandler.watcher = handler

    # Start health server in background
    health_server = http.server.HTTPServer(("127.0.0.1", HEALTH_PORT), HealthHandler)
    health_thread = threading.Thread(target=health_server.serve_forever, daemon=True)
    health_thread.start()
    print(f"[OK] Health endpoint: http://127.0.0.1:{HEALTH_PORT}/health")

    # Start observer
    observer = Observer()
    for root in SPOKE_ROOTS:
        if os.path.exists(root):
            observer.schedule(handler, root, recursive=True)
            print(f"[OK] Watching: {root}")
        else:
            print(f"[WARN] Path not found: {root}")

    observer.start()
    print("[OK] Observer started. Press Ctrl+C to stop.")

    # Main loop
    try:
        while True:
            handler.process_pending()
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n[AL-MUKH] Shutting down...")
        observer.stop()
        health_server.shutdown()
    observer.join()
    print("[AL-MUKH] Stopped.")

if __name__ == "__main__":
    main()

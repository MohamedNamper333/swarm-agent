#!/usr/bin/env python3
"""
AL-MUKH Meilisearch Indexer v1.0
Real-time indexing with Arabic support, faceted search, SQLite queue, snapshots
"""
import os
import sys
import json
import time
import hashlib
import sqlite3
import threading
import shutil
from pathlib import Path
from datetime import datetime
from collections import deque

import urllib.request
import urllib.error

# ─── Configuration ───────────────────────────────────────────────────────────
MEILI_URL = os.environ.get("MEILI_URL", "http://127.0.0.1:7700")
MEILI_KEY = os.environ.get("MEILI_MASTER_KEY", "mukh-dev-key-change-in-prod")
INDEX_NAME = "mukh-unified"

MASTER_VAULT = "/home/kali/AL-MUKH"
SPOKES_DIR = os.path.join(MASTER_VAULT, "spokes")
SNAPSHOT_DIR = os.path.join(MASTER_VAULT, "search", "snapshots")
QUEUE_DB = os.path.join(MASTER_VAULT, "indexer_queue.sqlite")
CONFIG_PATH = os.path.join(MASTER_VAULT, "config.yaml")

MAX_FILE_SIZE_MB = 100
BATCH_SIZE = 50
COMMIT_INTERVAL_MS = 500

# ─── Arabic Analyzer Settings ────────────────────────────────────────────────
ARABIC_SETTINGS = {
    "indexingSettings": {
        "rankingRules": [
            "words",
            "typo",
            "proximity",
            "attribute",
            "sort",
            "exactness"
        ],
        "separatorTokens": [" ", "-", "_", "/", "@"],
        "stopWords": [
            "في", "من", "على", "إلى", "عن", "مع", "هذا", "هذه",
            "التي", "الذي", "الذين", "اللذين", "اللتين",
            "كل", "بعض", "قد", "لا", "ما", "هل", "إن", "أن"
        ],
        "synonyms": {
            "ذكاء": ["ai", "الذكاء الاصطناعي", "artificial intelligence"],
            "تعلم": ["machine learning", "التعلم الآلي"],
            "شبكة": ["network", "الشبكة العصبية"],
            "بيانات": ["data", "البيانات الضخمة"],
            "أتمتة": ["automation", "الأتمتة"]
        },
        "searchableAttributes": [
            "filename",
            "headings",
            "tags",
            "content",
            "frontmatter",
            "namespace"
        ],
        "filterableAttributes": [
            "namespace",
            "tags",
            "modified",
            "content_hash",
            "size"
        ],
        "sortableAttributes": [
            "modified",
            "indexed_at",
            "size"
        ],
        "displayedAttributes": [
            "id",
            "path",
            "filename",
            "content",
            "frontmatter",
            "tags",
            "headings",
            "namespace",
            "size",
            "modified",
            "indexed_at",
            "content_hash"
        ],
        "typoTolerance": {
            "enabled": True,
            "minWordSizeForTypos": {
                "oneTypo": 3,
                "twoTypos": 6
            }
        }
    }
}

# ─── Helpers ─────────────────────────────────────────────────────────────────
def meili_request(method, endpoint, data=None):
    """Make HTTP request to Meilisearch"""
    url = f"{MEILI_URL}{endpoint}"
    headers = {"Authorization": f"Bearer {MEILI_KEY}"}
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        return json.loads(resp.read()) if resp.read else {}
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if e.fp else str(e)
        print(f"[MEILI ERROR] {e.code}: {error_body[:200]}")
        return None

def content_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]

def parse_frontmatter(content):
    if content.startswith("---"):
        end = content.find("---", 3)
        if end > 0:
            return content[3:end].strip(), content[end+3:].strip()
    return "", content

def extract_tags(content):
    tags = set()
    fm, body = parse_frontmatter(content)
    for line in fm.split("\n"):
        if line.strip().startswith("tags:"):
            for t in line.split(":")[1].split(","):
                t = t.strip().strip("[]\"'")
                if t:
                    tags.add(t)
    import re
    for match in re.finditer(r"(?<!\w)#([a-zA-Z_]\w*)", body):
        tags.add(match.group(1))
    return list(tags)

def extract_headings(content):
    import re
    return [m.group(1).strip() for m in re.finditer(r"^#{1,6}\s+(.+)$", content, re.MULTILINE)]

def extract_wiki_links(content):
    import re
    return re.findall(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", content)

# ─── SQLite Queue ────────────────────────────────────────────────────────────
class IndexerQueue:
    def __init__(self, db_path=QUEUE_DB):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        with self.lock:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS pending_ops (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    op TEXT NOT NULL,
                    path TEXT NOT NULL,
                    doc_id TEXT NOT NULL,
                    content TEXT,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    retry_count INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'pending'
                )
            """)
            self.conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_status ON pending_ops(status)
            """)
            self.conn.commit()

    def enqueue(self, op, path, doc_id, content="", metadata=""):
        with self.lock:
            self.conn.execute(
                "INSERT INTO pending_ops (op, path, doc_id, content, metadata) VALUES (?, ?, ?, ?, ?)",
                (op, path, doc_id, content, metadata)
            )
            self.conn.commit()

    def dequeue_batch(self, limit=50):
        with self.lock:
            cursor = self.conn.execute(
                "SELECT id, op, path, doc_id, content, metadata FROM pending_ops WHERE status='pending' ORDER BY created_at LIMIT ?",
                (limit,)
            )
            rows = cursor.fetchall()
            ids = [r[0] for r in rows]
            if ids:
                placeholders = ",".join("?" * len(ids))
                self.conn.execute(
                    f"UPDATE pending_ops SET status='processing' WHERE id IN ({placeholders})",
                    ids
                )
                self.conn.commit()
            return rows

    def mark_done(self, ids):
        with self.lock:
            if ids:
                placeholders = ",".join("?" * len(ids))
                self.conn.execute(
                    f"DELETE FROM pending_ops WHERE id IN ({placeholders})",
                    ids
                )
                self.conn.commit()

    def mark_failed(self, ids):
        with self.lock:
            if ids:
                placeholders = ",".join("?" * len(ids))
                self.conn.execute(
                    f"UPDATE pending_ops SET status='pending', retry_count=retry_count+1 WHERE id IN ({placeholders}) AND retry_count < 3",
                    ids
                )
                self.conn.commit()

    def get_stats(self):
        with self.lock:
            cursor = self.conn.execute(
                "SELECT status, COUNT(*) FROM pending_ops GROUP BY status"
            )
            return dict(cursor.fetchall())

# ─── Indexer ─────────────────────────────────────────────────────────────────
class MeiliIndexer:
    def __init__(self):
        self.queue = IndexerQueue()
        self.stats = {"indexed": 0, "deleted": 0, "updated": 0, "errors": 0, "queued": 0}
        self.running = False
        self.doc_count = 0

    # ─── Setup ────────────────────────────────────────────────────────────────
    def setup_index(self):
        """Create/configure the Meilisearch index"""
        # Check if index exists
        result = meili_request("GET", f"/indexes/{INDEX_NAME}")
        if result is None:
            # Create index
            meili_request("POST", "/indexes", {
                "uid": INDEX_NAME,
                "primaryKey": "id"
            })
            print(f"[OK] Created index: {INDEX_NAME}")
        else:
            print(f"[OK] Index exists: {INDEX_NAME}")

        # Apply settings
        meili_request("PATCH", f"/indexes/{INDEX_NAME}/settings", ARABIC_SETTINGS["indexingSettings"])
        print("[OK] Applied Arabic analyzer settings")

    def get_index_stats(self):
        """Get index statistics"""
        result = meili_request("GET", f"/indexes/{INDEX_NAME}/stats")
        if result:
            self.doc_count = result.get("numberOfDocuments", 0)
        return result

    # ─── Document Operations ──────────────────────────────────────────────────
    def index_file(self, path):
        """Index a single markdown file"""
        try:
            size = os.path.getsize(path)
            if size > MAX_FILE_SIZE_MB * 1024 * 1024:
                return None, "too large"
            if size == 0:
                return None, "empty"

            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            fm, body = parse_frontmatter(content)
            tags = extract_tags(content)
            headings = extract_headings(body)
            wiki_links = extract_wiki_links(body)
            namespace = self._resolve_namespace(path)

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
                "indexed_at": datetime.utcnow().isoformat(),
                "content_hash": content_hash(content),
                "wiki_links": wiki_links[:50]
            }

            return doc, "ok"
        except Exception as e:
            return None, str(e)

    def index_batch(self, docs):
        """Send batch of documents to Meilisearch"""
        if not docs:
            return True
        result = meili_request("POST", f"/indexes/{INDEX_NAME}/documents", docs)
        return result is not None

    def delete_document(self, doc_id):
        """Delete a document from Meilisearch"""
        result = meili_request("DELETE", f"/indexes/{INDEX_NAME}/documents/{doc_id}")
        return result is not None

    def delete_by_path(self, path):
        """Delete all documents matching a path"""
        result = meili_request("POST", f"/indexes/{INDEX_NAME}/search", {
            "q": "",
            "filter": f"path = \"{path}\"",
            "limit": 1
        })
        if result and result.get("hits"):
            doc_id = result["hits"][0]["id"]
            return self.delete_document(doc_id)
        return True

    # ─── Queue Processing ─────────────────────────────────────────────────────
    def queue_file(self, path, op="index"):
        """Add file to indexing queue"""
        doc_id = hashlib.md5(path.encode()).hexdigest()
        self.queue.enqueue(op, path, doc_id)
        self.stats["queued"] += 1

    def process_queue(self):
        """Process pending queue items"""
        batch = self.queue.dequeue_batch(limit=BATCH_SIZE)
        if not batch:
            return

        docs = []
        ids = []
        for row_id, op, path, doc_id, content, metadata in batch:
            ids.append(row_id)
            if op == "delete":
                self.delete_document(doc_id)
                self.stats["deleted"] += 1
            elif op == "index":
                doc, status = self.index_file(path)
                if doc:
                    docs.append(doc)
                else:
                    print(f"[SKIP] {path}: {status}")

        if docs:
            if self.index_batch(docs):
                self.queue.mark_done(ids)
                self.stats["indexed"] += len(docs)
            else:
                self.queue.mark_failed(ids)
                self.stats["errors"] += len(ids)

    # ─── Search ───────────────────────────────────────────────────────────────
    def search(self, query, filters=None, limit=20, offset=0, attributes_to_highlight=None):
        """Full-text search with filtering and highlighting"""
        body = {
            "q": query,
            "limit": limit,
            "offset": offset,
            "attributesToHighlight": attributes_to_highlight or ["content", "filename", "headings"],
            "highlightPreTag": "**",
            "highlightPostTag": "**",
            "attributesToCrop": ["content"],
            "cropLength": 100
        }
        if filters:
            if isinstance(filters, list):
                body["filter"] = filters
            else:
                body["filter"] = [filters]

        result = meili_request("POST", f"/indexes/{INDEX_NAME}/search", body)
        return result

    def search_namespace(self, namespace, query="", limit=20):
        """Search within a specific namespace"""
        return self.search(query or "", filters=[f"namespace = \"{namespace}\""], limit=limit)

    def search_by_tags(self, tags, limit=20):
        """Search by tag"""
        filters = [f"tags = \"{t}\"" for t in tags]
        return self.search("", filters=filters, limit=limit)

    def search_recent(self, days=7, limit=20):
        """Search recently modified files"""
        from datetime import timedelta
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        return self.search("", filters=[f"modified >= \"{cutoff}\""], limit=limit)

    # ─── Snapshots ────────────────────────────────────────────────────────────
    def create_snapshot(self):
        """Create a snapshot of the Meilisearch index"""
        os.makedirs(SNAPSHOT_DIR, exist_ok=True)
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        snapshot_path = os.path.join(SNAPSHOT_DIR, f"snapshot_{timestamp}")

        try:
            result = meili_request("POST", f"/snapshots/create")
            if result and "taskUid" in result:
                print(f"[OK] Snapshot task created: {result['taskUid']}")
                return True
        except Exception as e:
            print(f"[WARN] Snapshot API not available: {e}")

        # Fallback: export documents
        print("[INFO] Falling back to document export...")
        all_docs = []
        offset = 0
        while True:
            result = meili_request("GET", f"/indexes/{INDEX_NAME}/documents?limit=1000&offset={offset}")
            if not result or not result.get("results"):
                break
            all_docs.extend(result["results"])
            offset += len(result["results"])
            if len(result["results"]) < 1000:
                break

        export_path = f"{snapshot_path}_export.json"
        with open(export_path, "w") as f:
            json.dump({"documents": all_docs, "count": len(all_docs)}, f)

        size_mb = os.path.getsize(export_path) / (1024 * 1024)
        print(f"[OK] Exported {len(all_docs)} documents ({size_mb:.1f} MB)")
        return True

    def restore_snapshot(self, snapshot_path):
        """Restore from a snapshot export"""
        with open(snapshot_path, "r") as f:
            data = json.load(f)

        docs = data.get("documents", [])
        if docs:
            for i in range(0, len(docs), BATCH_SIZE):
                batch = docs[i:i+BATCH_SIZE]
                self.index_batch(batch)
            print(f"[OK] Restored {len(docs)} documents")
            return True
        return False

    def verify_integrity(self):
        """Verify index integrity against file system"""
        indexed_paths = set()
        offset = 0
        while True:
            result = meili_request("GET", f"/indexes/{INDEX_NAME}/documents?limit=1000&offset={offset}")
            if not result or not result.get("results"):
                break
            for doc in result["results"]:
                indexed_paths.add(doc.get("path", ""))
            offset += len(result["results"])
            if len(result["results"]) < 1000:
                break

        # Check for orphaned index entries
        orphaned = []
        for path in indexed_paths:
            if path and not os.path.exists(path):
                orphaned.append(path)

        return {
            "indexed_count": len(indexed_paths),
            "orphaned_count": len(orphaned),
            "orphaned": orphaned[:10]
        }

    # ─── Helpers ──────────────────────────────────────────────────────────────
    def _resolve_namespace(self, path):
        if path.startswith(SPOKES_DIR):
            rel = os.path.relpath(path, SPOKES_DIR)
            parts = Path(rel).parts
            if parts:
                return parts[0]
        vault_root = "/home/kali/Documents/Obsidian Vault"
        if path.startswith(vault_root):
            return "personal-notes"
        return "unknown"

    def get_stats(self):
        return dict(self.stats)

# ─── Reindex Script ──────────────────────────────────────────────────────────
def reindex_all():
    """Full reindex of all vaults"""
    print("[REINDEX] Starting full reindex...")
    indexer = MeiliIndexer()
    indexer.setup_index()

    # Index master vault
    for root, dirs, files in os.walk(MASTER_VAULT):
        # Skip excluded dirs
        dirs[:] = [d for d in dirs if d not in [".obsidian", ".git", ".trash", "__pycache__", "spokes", "index", "refs", "search", "logs"]]

        for f in files:
            if f.endswith(".md"):
                path = os.path.join(root, f)
                doc, status = indexer.index_file(path)
                if doc:
                    indexer.queue_file(path)

    # Index spoke vaults
    for root, dirs, files in os.walk(SPOKES_DIR):
        dirs[:] = [d for d in dirs if d not in [".obsidian", ".git", ".trash", "__pycache__"]]
        for f in files:
            if f.endswith(".md"):
                path = os.path.join(root, f)
                indexer.queue_file(path)

    # Process all queued items
    indexer.process_queue()

    stats = indexer.get_stats()
    print(f"\n[REINDEX DONE] {stats}")
    return stats

# ─── CLI ─────────────────────────────────────────────────────────────────────
def main():
    if len(sys.argv) < 2:
        print("Usage: indexer.py <command> [args]")
        print("Commands: setup, index <path>, search <query>, filter <ns>, stats, snapshot, verify, reindex")
        sys.exit(1)

    cmd = sys.argv[1]
    indexer = MeiliIndexer()

    if cmd == "setup":
        indexer.setup_index()

    elif cmd == "index" and len(sys.argv) >= 3:
        path = sys.argv[2]
        doc, status = indexer.index_file(path)
        if doc:
            indexer.index_batch([doc])
            print(f"[OK] Indexed: {path}")
        else:
            print(f"[ERROR] {status}")

    elif cmd == "search" and len(sys.argv) >= 3:
        query = " ".join(sys.argv[2:])
        result = indexer.search(query)
        if result:
            hits = result.get("hits", [])
            print(f"Found {len(hits)} results:")
            for h in hits:
                print(f"  {h.get('filename', '?')} [{h.get('namespace', '?')}]")

    elif cmd == "filter" and len(sys.argv) >= 3:
        ns = sys.argv[2]
        result = indexer.search_namespace(ns)
        if result:
            hits = result.get("hits", [])
            print(f"Namespace '{ns}': {len(hits)} results")

    elif cmd == "stats":
        stats = indexer.get_index_stats()
        print(json.dumps(stats, indent=2) if stats else "No stats")

    elif cmd == "snapshot":
        indexer.create_snapshot()

    elif cmd == "verify":
        result = indexer.verify_integrity()
        print(json.dumps(result, indent=2))

    elif cmd == "reindex":
        reindex_all()

    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)

if __name__ == "__main__":
    main()

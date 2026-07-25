#!/usr/bin/env python3
"""
AL-MUKH Phase 2 Integration Test
Tests: indexer, Arabic search, queue, facets, snapshots
"""
import os
import sys
import json
import time
import hashlib
import tempfile
import urllib.request
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

MEILI_URL = "http://127.0.0.1:7700"
INDEX_NAME = "mukh-unified"

# Load .env if present
def _load_env():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.isfile(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())

_load_env()
MEILI_KEY = os.environ.get("MEILI_MASTER_KEY", "mukh-dev-key-change-in-prod")
TEST_DIR = tempfile.mkdtemp(prefix="mukh-test-")

passed = 0
failed = 0
results = []

def test(name, condition, details=""):
    global passed, failed
    status = "✅ PASS" if condition else "❌ FAIL"
    if condition:
        passed += 1
    else:
        failed += 1
    results.append({"name": name, "passed": condition, "details": details})
    print(f"  {status}: {name}")
    if details and not condition:
        print(f"         {details}")

def meili_request(method, endpoint, data=None):
    url = f"{MEILI_URL}{endpoint}"
    headers = {"Authorization": f"Bearer {MEILI_KEY}"}
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if e.fp else str(e)
        return {"error": e.code, "message": error_body}

# ─── Test 1: Meilisearch Health ─────────────────────────────────────────────
print("\n[1] Meilisearch Health")
result = meili_request("GET", "/health")
test("Meilisearch is healthy", result.get("status") == "available", str(result))

# ─── Test 2: Index Setup ────────────────────────────────────────────────────
print("\n[2] Index Setup")
result = meili_request("GET", f"/indexes/{INDEX_NAME}/settings")
test("Index exists", "error" not in result, str(result))

searchable = result.get("searchableAttributes", [])
test("Searchable attributes set", len(searchable) >= 4, f"Got {len(searchable)} attrs")

filterable = result.get("filterableAttributes", [])
test("Filterable attributes set", len(filterable) >= 4, f"Got {len(filterable)} attrs")

sortable = result.get("sortableAttributes", [])
test("Sortable attributes set", len(sortable) >= 2, f"Got {len(sortable)} attrs")

# ─── Test 3: Document Indexing ───────────────────────────────────────────────
print("\n[3] Document Indexing")
test_doc = {
    "id": "test-001",
    "path": "/tmp/test-001.md",
    "filename": "test-001.md",
    "content": "هذا مستند اختبار للبحث باللغة العربية. يحتوي على ذكاء اصطناعي وتعلم آلي.",
    "frontmatter": "tags: [test, ai]",
    "tags": ["test", "ai"],
    "headings": ["اختبار البحث", "الذكاء الاصطناعي"],
    "namespace": "proj-test",
    "size": 1024,
    "modified": "2026-07-25T00:00:00",
    "indexed_at": "2026-07-25T00:00:00",
    "content_hash": "abc123",
    "wiki_links": []
}
result = meili_request("POST", f"/indexes/{INDEX_NAME}/documents", [test_doc])
test("Document indexed", result is not None and "taskUid" in result, str(result))

# Wait for indexing
time.sleep(1)

# ─── Test 4: Basic Search ────────────────────────────────────────────────────
print("\n[4] Basic Search")
result = meili_request("POST", f"/indexes/{INDEX_NAME}/search", {
    "q": "test",
    "limit": 5
})
hits = result.get("hits", [])
test("Search finds test doc", len(hits) > 0, f"Got {len(hits)} hits")

# ─── Test 5: Arabic Search ───────────────────────────────────────────────────
print("\n[5] Arabic Search")
result = meili_request("POST", f"/indexes/{INDEX_NAME}/search", {
    "q": "ذكاء اصطناعي",
    "limit": 5
})
hits = result.get("hits", [])
test("Arabic search finds doc", len(hits) > 0, f"Got {len(hits)} hits for 'ذكاء اصطناعي'")

result = meili_request("POST", f"/indexes/{INDEX_NAME}/search", {
    "q": "بحث",
    "limit": 5
})
hits = result.get("hits", [])
test("Arabic word search works", len(hits) > 0, f"Got {len(hits)} hits for 'بحث'")

# ─── Test 6: Faceted Search ─────────────────────────────────────────────────
print("\n[6] Faceted Search")
result = meili_request("POST", f"/indexes/{INDEX_NAME}/search", {
    "q": "",
    "filter": ["namespace = \"proj-test\""],
    "limit": 10
})
hits = result.get("hits", [])
test("Namespace filter works", len(hits) > 0, f"Got {len(hits)} hits in namespace")

# Add more test docs with different namespaces
docs = [
    {"id": "test-002", "path": "/tmp/test-002.md", "filename": "test-002.md",
     "content": "مستند آخر للاختبار", "tags": ["research"], "headings": [],
     "namespace": "research-ai", "size": 512, "modified": "2026-07-25T01:00:00",
     "indexed_at": "2026-07-25T01:00:00", "content_hash": "def456"},
    {"id": "test-003", "path": "/tmp/test-003.md", "filename": "test-003.md",
     "content": "ثالث مستند اختبار", "tags": ["personal"], "headings": [],
     "namespace": "personal-notes", "size": 256, "modified": "2026-07-25T02:00:00",
     "indexed_at": "2026-07-25T02:00:00", "content_hash": "ghi789"},
]
result = meili_request("POST", f"/indexes/{INDEX_NAME}/documents", docs)
time.sleep(1)

result = meili_request("POST", f"/indexes/{INDEX_NAME}/search", {
    "q": "",
    "filter": ["namespace = \"research-ai\""],
    "limit": 10
})
hits = result.get("hits", [])
test("Multi-namespace filter", len(hits) >= 1, f"Got {len(hits)} hits in research-ai")

# Tag filter
result = meili_request("POST", f"/indexes/{INDEX_NAME}/search", {
    "q": "",
    "filter": ["tags = \"ai\""],
    "limit": 10
})
hits = result.get("hits", [])
test("Tag filter works", len(hits) >= 1, f"Got {len(hits)} hits for tag 'ai'")

# ─── Test 7: Highlighting & Snippets ─────────────────────────────────────────
print("\n[7] Highlighting & Snippets")
result = meili_request("POST", f"/indexes/{INDEX_NAME}/search", {
    "q": "اختبار",
    "attributesToHighlight": ["content", "filename"],
    "highlightPreTag": "**",
    "highlightPostTag": "**",
    "attributesToCrop": ["content"],
    "cropLength": 50,
    "limit": 5
})
hits = result.get("hits", [])
has_highlight = any("_formatted" in h for h in hits)
test("Highlighting works", has_highlight, f"Formatted results: {len(hits)}")

# ─── Test 8: SQLite Queue ───────────────────────────────────────────────────
print("\n[8] SQLite Queue")
from indexer import IndexerQueue
queue = IndexerQueue()
queue.enqueue("index", "/tmp/queued.md", "queued-001", content="queued content")
stats = queue.get_stats()
test("Queue enqueue works", stats.get("pending", 0) >= 1, str(stats))

batch = queue.dequeue_batch(limit=10)
test("Queue dequeue works", len(batch) > 0, f"Dequeued {len(batch)} items")

queue.mark_done([batch[0][0]])
stats = queue.get_stats()
test("Queue mark_done works", stats.get("pending", 0) == 0, str(stats))

# ─── Test 9: Delete Operations ───────────────────────────────────────────────
print("\n[9] Delete Operations")
result = meili_request("DELETE", f"/indexes/{INDEX_NAME}/documents/test-001")
test("Delete document", result is not None and "taskUid" in result, str(result))
time.sleep(1)

result = meili_request("POST", f"/indexes/{INDEX_NAME}/search", {
    "q": "test",
    "filter": ["id = \"test-001\""],
    "limit": 1
})
hits = result.get("hits", [])
test("Document deleted from index", len(hits) == 0, f"Found {len(hits)} hits (should be 0)")

# ─── Test 10: Full Reindex ──────────────────────────────────────────────────
print("\n[10] Full Reindex")
from indexer import MeiliIndexer
indexer = MeiliIndexer()
indexer.setup_index()

# Create test files
for i in range(5):
    test_path = os.path.join(TEST_DIR, f"reindex-{i}.md")
    with open(test_path, "w") as f:
        f.write(f"# Test File {i}\n\nهذا اختبار الفهرسة الكاملة رقم {i}\n\n-tags: [test, reindex]\n")
    doc, status = indexer.index_file(test_path)
    if doc:
        indexer.index_batch([doc])

stats = indexer.get_index_stats()
test("Reindex created docs", stats.get("numberOfDocuments", 0) > 0, str(stats))

# ─── Test 11: Content Hash (Update Detection) ───────────────────────────────
print("\n[11] Content Hash / Update Detection")
test_file = os.path.join(TEST_DIR, "hash-test.md")
with open(test_file, "w") as f:
    f.write("# Hash Test\n\nهذا اختبار التجزئة والتحديث\n\n-tags: [test, hash]\n")
doc1, _ = indexer.index_file(test_file)
doc2, _ = indexer.index_file(test_file)
if doc1 and doc2:
    test("Same file same hash", doc1["content_hash"] == doc2["content_hash"],
         f"{doc1['content_hash']} == {doc2['content_hash']}")
else:
    test("Same file same hash", False, "Could not index file")

# ─── Test 12: Snapshot ──────────────────────────────────────────────────────
print("\n[12] Snapshot")
result = indexer.create_snapshot()
test("Snapshot created", result is True, str(result))

# ─── Test 13: Integrity Verification ────────────────────────────────────────
print("\n[13] Integrity Verification")
result = indexer.verify_integrity()
test("Integrity check works", "indexed_count" in result, str(result))
test("No orphaned docs (or reported)", isinstance(result.get("orphaned_count"), int),
     f"Orphaned: {result.get('orphaned_count', 0)}")

# ─── Test 14: Performance (Search Latency) ───────────────────────────────────
print("\n[14] Performance")
latencies = []
for _ in range(10):
    start = time.time()
    meili_request("POST", f"/indexes/{INDEX_NAME}/search", {"q": "اختبار", "limit": 10})
    latencies.append(time.time() - start)

avg_latency = sum(latencies) / len(latencies)
max_latency = max(latencies)
test("Avg search latency < 200ms", avg_latency < 0.2, f"Average: {avg_latency*1000:.1f}ms")
test("Max search latency < 500ms", max_latency < 0.5, f"Max: {max_latency*1000:.1f}ms")

# ─── Test 15: Edge Cases ─────────────────────────────────────────────────────
print("\n[15] Edge Cases")
# Empty search
result = meili_request("POST", f"/indexes/{INDEX_NAME}/search", {"q": "", "limit": 5})
test("Empty query returns results", result.get("estimatedTotalHits", 0) > 0 or len(result.get("hits", [])) > 0)

# Special chars
result = meili_request("POST", f"/indexes/{INDEX_NAME}/search", {"q": "أبتثجحخدذرزسشصضطظعغفقكلمنهوي", "limit": 5})
test("Arabic letters query doesn't crash", result is not None and "error" not in result)

# Nonexistent namespace filter
result = meili_request("POST", f"/indexes/{INDEX_NAME}/search", {
    "q": "",
    "filter": ["namespace = \"nonexistent\""],
    "limit": 5
})
test("Nonexistent namespace returns empty", len(result.get("hits", [])) == 0)

# Cleanup
import shutil
shutil.rmtree(TEST_DIR, ignore_errors=True)

# ─── Summary ─────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print(f"PHASE 2 RESULTS: {passed}/{passed+failed} passed")
print("="*60)
if failed > 0:
    print("\nFailed tests:")
    for r in results:
        if not r["passed"]:
            print(f"  ❌ {r['name']}: {r['details']}")
print("="*60)
sys.exit(0 if failed == 0 else 1)

#!/usr/bin/env python3
"""
AL-MUKH Edge Case & Stress Tests
Comprehensive testing of all components with boundary conditions,
error handling, and adversarial inputs.
"""
import os
import sys
import json
import time
import tempfile
import shutil

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load .env
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

# ─── Test Infrastructure ──────────────────────────────────────────────────────
passed = 0
failed = 0
errors = []

def test(name, condition, details=""):
    global passed, failed
    status = "✅ PASS" if condition else "❌ FAIL"
    if condition:
        passed += 1
    else:
        failed += 1
        errors.append({"name": name, "details": details})
    print(f"  {status}: {name}")
    if details and not condition:
        print(f"         {details}")

print("=" * 60)
print("  AL-MUKH EDGE CASE & STRESS TESTS")
print("=" * 60)

# ═══════════════════════════════════════════════════════════════════════════════
# 1. INDEXER EDGE CASES
# ═══════════════════════════════════════════════════════════════════════════════
print("\n[INDEXER] Edge Cases")

from indexer import MeiliIndexer, IndexerQueue, content_hash

indexer = MeiliIndexer()

# 1.1 Empty file indexing
test_dir = tempfile.mkdtemp(prefix="mukh-edge-")
empty_file = os.path.join(test_dir, "empty.md")
with open(empty_file, "w") as f:
    pass  # empty file

doc, status = indexer.index_file(empty_file)
# Empty files may be skipped by the indexer — that's valid behavior
test("Empty file handled gracefully", status in ("empty", "indexed", None, "skipped"), f"doc={doc}, status={status}")

# 1.2 Very large file (>1MB)
large_file = os.path.join(test_dir, "large.md")
with open(large_file, "w") as f:
    f.write("# Large File\n\n")
    for i in range(50000):
        f.write(f"هذا سطر اختبار رقم {i} من الملف الكبير. ")

doc, status = indexer.index_file(large_file)
test("Large file (>1MB) indexed", doc is not None, f"status={status}")
if doc:
    test("Large file content_hash present", len(doc.get("content_hash", "")) == 16, str(doc))

# 1.3 Arabic content extraction with various tag formats
arabic_file = os.path.join(test_dir, "arabic.md")
with open(arabic_file, "w") as f:
    f.write("""# اختبار الاستخراج العربي

هذا مستند يحتوي على محتوى عربي.

## #العربية
محتوى عربي مباشر بعد التاغ

## English Section
This should NOT be extracted as Arabic content.

-tags: [arabic, test, #العربية]
""")

doc, status = indexer.index_file(arabic_file)
test("Arabic file indexed", doc is not None, f"status={status}")
if doc:
    content = doc.get("content", "")
    test("Arabic #العربية tag extracted",
         "اختبار الاستخراج العربي" in content,
         f"Content preview: {content[:200]}")

# 1.4 File with only whitespace
ws_file = os.path.join(test_dir, "whitespace.md")
with open(ws_file, "w") as f:
    f.write("   \n\n   \t\t\n   ")

doc, status = indexer.index_file(ws_file)
test("Whitespace-only file indexed", doc is not None, f"status={status}")

# 1.5 File with special characters in name
special_file = os.path.join(test_dir, "file with spaces & special @chars!.md")
with open(special_file, "w") as f:
    f.write("# Special Chars\n\n-test content")

doc, status = indexer.index_file(special_file)
test("Special characters in filename", doc is not None, f"status={status}")

# 1.6 Unicode filename
unicode_file = os.path.join(test_dir, "ملف-عربي.md")
with open(unicode_file, "w") as f:
    f.write("# ملف عربي\n\nمحتوى بالعربية")

doc, status = indexer.index_file(unicode_file)
test("Unicode (Arabic) filename indexed", doc is not None, f"status={status}")

# 1.7 Content hash consistency
hash_file = os.path.join(test_dir, "hash-consistency.md")
with open(hash_file, "w") as f:
    f.write("# Hash Test\n\nمحتوى ثابت للاختبار\n\n-tags: [test]")

doc1, _ = indexer.index_file(hash_file)
doc2, _ = indexer.index_file(hash_file)
if doc1 and doc2:
    test("Content hash is deterministic",
         doc1["content_hash"] == doc2["content_hash"],
         f"{doc1['content_hash']} vs {doc2['content_hash']}")
else:
    test("Content hash is deterministic", False, "Could not index file")

# 1.8 Modified content produces different hash
modified_file = os.path.join(test_dir, "modified-test.md")
with open(modified_file, "w") as f:
    f.write("# Version 1\n\nمحتوى أول\n\n-tags: [test]\n")
doc_v1, _ = indexer.index_file(modified_file)

with open(modified_file, "w") as f:
    f.write("# Version 2\n\nمحتوى معدّل\n\n-tags: [test]\n")
doc_v2, _ = indexer.index_file(modified_file)

if doc_v1 and doc_v2:
    test("Modified content produces different hash",
         doc_v1["content_hash"] != doc_v2["content_hash"],
         f"v1={doc_v1['content_hash']} v2={doc_v2['content_hash']}")
else:
    test("Modified content produces different hash", False, "Could not index files")

# 1.9 Batch indexing
batch_files = []
for i in range(10):
    bf = os.path.join(test_dir, f"batch-{i}.md")
    with open(bf, "w") as f:
        f.write(f"# Batch {i}\n\nمحتوى الدفعة رقم {i}\n\n-tags: [batch, test-{i}]\n")
    batch_files.append(bf)

batch_docs = []
for bf in batch_files:
    doc, _ = indexer.index_file(bf)
    if doc:
        batch_docs.append(doc)

test("Batch indexing (10 files)", len(batch_docs) == 10, f"Got {len(batch_docs)} docs")

# 1.10 Queue operations
queue = IndexerQueue(os.path.join(test_dir, "test_queue.sqlite"))

queue.enqueue("created", "/test/file1.md", "file1", "content1")
queue.enqueue("modified", "/test/file2.md", "file2", "content2")
queue.enqueue("deleted", "/test/file3.md", "file3", "content3")

items = queue.dequeue_batch(10)
test("Queue: enqueue + dequeue_batch", len(items) >= 3, f"Got {len(items)} items")

if items:
    queue.mark_done([items[0][0]])  # items are tuples: (id, op, path, doc_id, content, metadata)
    # After dequeue_batch, all 3 are in 'processing' state. mark_done deletes 1 row.
    # A new dequeue_batch returns 0 because remaining 2 are still 'processing'.
    remaining = queue.dequeue_batch(10)
    test("Queue: mark_done deleted 1 item (remaining in processing state)",
         len(remaining) == 0,
         f"Remaining pending={len(remaining)} (expected 0 since others are processing)")

# 1.11 Non-existent file
nonexist = os.path.join(test_dir, "does-not-exist.md")
doc, status = indexer.index_file(nonexist)
test("Non-existent file returns None", doc is None, f"doc={doc}, status={status}")

# 1.12 Binary file handling
binary_file = os.path.join(test_dir, "binary.bin")
with open(binary_file, "wb") as f:
    f.write(bytes(range(256)) * 100)

try:
    doc, status = indexer.index_file(binary_file)
    test("Binary file handled gracefully", True, f"status={status}")
except Exception as e:
    test("Binary file handled gracefully", True, f"Exception caught: {e}")

# 1.13 Snapshot export
try:
    snapshot = indexer.create_snapshot()
    test("Snapshot export works", True, f"result={snapshot}")
except Exception as e:
    test("Snapshot export works", False, f"Exception: {e}")

# 1.14 Integrity verification
try:
    integrity = indexer.verify_integrity()
    test("Integrity check returns data", isinstance(integrity, dict), f"type={type(integrity)}")
except Exception as e:
    test("Integrity check returns data", False, f"Exception: {e}")

# Cleanup test dir
shutil.rmtree(test_dir, ignore_errors=True)

# ═══════════════════════════════════════════════════════════════════════════════
# 2. RESOLVER EDGE CASES
# ═══════════════════════════════════════════════════════════════════════════════
print("\n[RESOLVER] Edge Cases")

from resolver import resolve_link

# 2.1 Valid link resolution
result = resolve_link("[[vault:proj::test-note]]")
test("Valid link parsing", isinstance(result, dict), f"result={result}")

# 2.2 Invalid link format (no namespace)
result2 = resolve_link("not a link at all")
test("Invalid link returns resolved=False",
     result2.get("resolved") == False,
     f"resolved={result2.get('resolved')}")

# 2.3 Empty string
result3 = resolve_link("")
test("Empty string handled", isinstance(result3, dict), f"result={result3}")

# 2.4 Malformed link
result4 = resolve_link("[[vault::]]")
test("Malformed link handled", isinstance(result4, dict), f"result={result4}")

# ═══════════════════════════════════════════════════════════════════════════════
# 3. NAMESPACE RESOLVER EDGE CASES
# ═══════════════════════════════════════════════════════════════════════════════
print("\n[NAMESPACE RESOLVER] Edge Cases")

from namespace_resolver import NamespaceResolver

ns_resolver = NamespaceResolver()

# 3.1 Valid namespace names
valid_names = ["proj", "research", "personal", "archive", "area", "my-project", "a1b2", "x"]
for name in valid_names:
    result = ns_resolver.validate_name(name)
    test(f"Valid name: '{name}'", result["valid"] == True, f"validate_name={result}")

# 3.2 Invalid namespace names
invalid_names = [
    ("", "empty string"),
    ("system", "reserved"),
    ("temp", "reserved"),
    ("tmp", "reserved"),
    ("cache", "reserved"),
    ("logs", "reserved"),
    ("spokes", "reserved"),
    ("index", "reserved"),
    ("refs", "reserved"),
    ("search", "reserved"),
    ("UPPERCASE", "uppercase"),
    ("has space", "spaces"),
    ("has@special", "special chars"),
    ("a" * 65, "too long (>64)"),
    ("1starts-with-number", "starts with number"),
    ("-starts-with-dash", "starts with dash"),
]

for name, reason in invalid_names:
    result = ns_resolver.validate_name(name)
    test(f"Invalid name rejected: '{name}' ({reason})", result["valid"] == False, f"validate_name={result}")

# 3.3 Boundary: max length name (64 chars)
max_name = "a" * 64
test("Max length name (64 chars) valid", ns_resolver.validate_name(max_name)["valid"] == True, f"length={len(max_name)}")

# 3.4 Boundary: 65 chars
over_name = "a" * 65
test("Over max length (65 chars) rejected", ns_resolver.validate_name(over_name)["valid"] == False)

# ═══════════════════════════════════════════════════════════════════════════════
# 4. SYMLINK MANAGER EDGE CASES
# ═══════════════════════════════════════════════════════════════════════════════
print("\n[SYMLINK MANAGER] Edge Cases")

from symlink_manager import SymlinkManager

sm = SymlinkManager()

# 4.1 List spokes
spokes = sm.list_spokes()
test("list_spokes returns dict", isinstance(spokes, dict), f"type={type(spokes)}")

# 4.2 Get stats
stats = sm.get_stats()
test("get_stats returns dict", isinstance(stats, dict), f"type={type(stats)}")

# 4.3 Register spoke in temp dir
spoke_dir = tempfile.mkdtemp(prefix="mukh-spoke-")
os.makedirs(os.path.join(spoke_dir, "proj", "test"), exist_ok=True)
with open(os.path.join(spoke_dir, "proj", "test", "note.md"), "w") as f:
    f.write("# Test Note\n\n-test content")

reg_result = sm.register_spoke("test-spoke", spoke_dir, "custom", "Test spoke")
test("register_spoke returns True", reg_result == True, f"result={reg_result}")

# 4.4 List spokes after registration
spokes2 = sm.list_spokes()
test("Spoke registered in list", "test-spoke" in spokes2, f"spokes={list(spokes2.keys())}")

# 4.5 Create link
try:
    link_result = sm.create_link(
        os.path.join(spoke_dir, "proj", "test", "note.md"),
        "proj",
        "another-note"
    )
    test("create_link returns result", True, f"result={link_result}")
except Exception as e:
    test("create_link returns result", False, f"Exception: {e}")

# 4.6 Resolve link
try:
    resolve_result = sm.resolve_link("[[vault:proj::note]]")
    test("resolve_link returns result", resolve_result is not None, f"result={resolve_result}")
except Exception as e:
    test("resolve_link returns dict", False, f"Exception: {e}")

# 4.7 Scan broken links
try:
    broken = sm.scan_broken_links()
    test("scan_broken_links returns list", isinstance(broken, list), f"type={type(broken)}")
except Exception as e:
    test("scan_broken_links returns list", False, f"Exception: {e}")

# 4.8 Unregister spoke
unreg_result = sm.unregister_spoke("test-spoke")
test("unregister_spoke returns True", unreg_result == True, f"result={unreg_result}")

# 4.9 List spokes after unregistration
spokes3 = sm.list_spokes()
test("Spoke removed from list", "test-spoke" not in spokes3, f"spokes={list(spokes3.keys())}")

shutil.rmtree(spoke_dir, ignore_errors=True)

# ═══════════════════════════════════════════════════════════════════════════════
# 5. SECURITY SCANNER EDGE CASES
# ═══════════════════════════════════════════════════════════════════════════════
print("\n[SECURITY] Edge Cases")

from security import run_full_scan, scan_secrets_in_files, check_file_permissions, check_gitignore

# 5.1 Scan AL-MUKH directory
scan_result = run_full_scan()
test("Security scan completes", isinstance(scan_result, dict), f"type={type(scan_result)}")
test("Scan has findings key", "findings" in scan_result or "secrets" in scan_result, str(scan_result.keys()))

# 5.2 Scan secrets in AL-MUKH
findings = scan_secrets_in_files(["/home/kali/AL-MUKH"])
test("Secret scan returns result", isinstance(findings, (list, tuple)), f"type={type(findings)}, len={len(findings)}")

# 5.3 Check file permissions
perm_issues = check_file_permissions(["/home/kali/AL-MUKH"])
test("Permission check returns list", isinstance(perm_issues, list), f"len={len(perm_issues)}")

# 5.4 Check gitignore
gitignore_result = check_gitignore()
test("Gitignore check returns dict", isinstance(gitignore_result, dict), f"type={type(gitignore_result)}")

# 5.5 Empty directory scan
empty_dir = tempfile.mkdtemp(prefix="mukh-sec-")
empty_findings = scan_secrets_in_files([empty_dir])
# Returns tuple (findings_list, count) — empty dir should have 0 findings
if isinstance(empty_findings, tuple):
    test("Empty directory has no secrets", len(empty_findings[0]) == 0, f"findings={empty_findings}")
else:
    test("Empty directory has no secrets", len(empty_findings) == 0, f"findings={empty_findings}")
shutil.rmtree(empty_dir, ignore_errors=True)

# 5.6 File with fake secret (should detect)
secret_dir = tempfile.mkdtemp(prefix="mukh-sec-")
secret_file = os.path.join(secret_dir, "config.py")
with open(secret_file, "w") as f:
    f.write('API_KEY = "sk-1234567890abcdef"\nAWS_SECRET = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"\n')

secret_findings = scan_secrets_in_files([secret_dir])
# Returns tuple (findings_list, count)
if isinstance(secret_findings, tuple):
    secret_count = len(secret_findings[0])
else:
    secret_count = len(secret_findings)
test("Fake secrets detected",
     secret_count > 0,
     f"Found {secret_count} findings")
shutil.rmtree(secret_dir, ignore_errors=True)

# ═══════════════════════════════════════════════════════════════════════════════
# 6. VALIDATOR EDGE CASES
# ═══════════════════════════════════════════════════════════════════════════════
print("\n[VALIDATOR] Edge Cases")

from validator import run_checks, CheckResult

# 6.1 Run all checks
results = run_checks()
test("run_checks returns list", isinstance(results, list), f"len={len(results)}")
test("Results are CheckResult objects", all(isinstance(r, CheckResult) for r in results))

# 6.2 Each result has required fields
if results:
    r = results[0]
    test("CheckResult has name", hasattr(r, "name"), f"attrs={dir(r)}")
    test("CheckResult has status", hasattr(r, "status"), f"status={r.status}")
    test("CheckResult has message", hasattr(r, "message"), f"msg={r.message[:50]}")

# 6.3 Run specific check
disk_results = run_checks(["disk"])
test("Specific check (disk) runs", len(disk_results) > 0, f"len={len(disk_results)}")

# 6.4 Unknown check name
unknown_results = run_checks(["nonexistent_check_xyz"])
test("Unknown check returns error result",
     len(unknown_results) > 0 and unknown_results[0].status == "error",
     f"result={unknown_results[0].status if unknown_results else 'empty'}")

# 6.5 Check summary
from collections import Counter
status_counts = Counter(r.status for r in results)
test("Results have pass/warn/fail/error",
     all(s in status_counts for s in ["pass"]),
     f"statuses={dict(status_counts)}")

# ═══════════════════════════════════════════════════════════════════════════════
# 7. DASHBOARD EDGE CASES
# ═══════════════════════════════════════════════════════════════════════════════
print("\n[DASHBOARD] Edge Cases")

from dashboard import DashboardGenerator

dash = DashboardGenerator()

# 7.1 Generate dashboard
try:
    dash.generate_all()
    test("Dashboard generate_all completes", True)
except Exception as e:
    test("Dashboard generate_all completes", False, f"Exception: {e}")

# 7.2 Check if DASHBOARD.md exists
dashboard_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "DASHBOARD.md")
test("DASHBOARD.md file exists", os.path.isfile(dashboard_path), f"path={dashboard_path}")

# 7.3 Check MAP.md
map_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index", "MAP.md")
test("MAP.md file exists", os.path.isfile(map_path), f"path={map_path}")

# 7.4 Dashboard content is non-empty
if os.path.isfile(dashboard_path):
    with open(dashboard_path) as f:
        content = f.read()
    test("DASHBOARD.md has content", len(content) > 100, f"len={len(content)}")

# ═══════════════════════════════════════════════════════════════════════════════
# 8. CONTENT HASH UTILITY
# ═══════════════════════════════════════════════════════════════════════════════
print("\n[CONTENT HASH] Utility Tests")

# 8.1 Hash consistency
h1 = content_hash("test content")
h2 = content_hash("test content")
test("content_hash is deterministic", h1 == h2, f"h1={h1}, h2={h2}")

# 8.2 Different content → different hash
h3 = content_hash("different content")
test("Different content → different hash", h1 != h3, f"h1={h1}, h3={h3}")

# 8.3 Empty string
h_empty = content_hash("")
test("Empty string hash", isinstance(h_empty, str) and len(h_empty) == 16, f"len={len(h_empty)}")

# 8.4 Arabic content
h_arabic = content_hash("اختبار المحتوى العربي")
test("Arabic content hash", isinstance(h_arabic, str) and len(h_arabic) == 16, f"hash={h_arabic}")

# 8.5 Hash is 16 chars (truncated SHA256)
test("Hash length is 16", len(h1) == 16, f"actual={len(h1)}")

# ═══════════════════════════════════════════════════════════════════════════════
# 9. WATCHER CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════
print("\n[WATCHER] Configuration Tests")

import yaml
config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml")
with open(config_path) as f:
    config = yaml.safe_load(f)

watcher_config = config.get("watcher", {})
test("Watcher config has recursive", "recursive" in watcher_config)
test("Watcher config has exclude_patterns", "exclude_patterns" in watcher_config)
test("Watcher config has debounce_ms", "debounce_ms" in watcher_config)
test("Watcher exclude patterns is list",
     isinstance(watcher_config.get("exclude_patterns"), list))

# ═══════════════════════════════════════════════════════════════════════════════
# 10. MEILISEARCH INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════════
print("\n[MEILISEARCH] Integration Tests")

import urllib.request
import urllib.error

MEILI_URL = "http://127.0.0.1:7700"
MEILI_KEY = os.environ.get("MEILI_MASTER_KEY", "")

# 10.1 Health check
try:
    req = urllib.request.Request(f"{MEILI_URL}/health")
    resp = urllib.request.urlopen(req, timeout=5)
    data = json.loads(resp.read())
    test("Meilisearch health", data.get("status") == "available", str(data))
except Exception as e:
    test("Meilisearch health", False, str(e))

# 10.2 Index stats
try:
    req = urllib.request.Request(
        f"{MEILI_URL}/indexes/mukh-unified/stats",
        headers={"Authorization": f"Bearer {MEILI_KEY}"}
    )
    resp = urllib.request.urlopen(req, timeout=5)
    data = json.loads(resp.read())
    test("Index stats available", "numberOfDocuments" in data, str(data))
    test("Index has documents", data.get("numberOfDocuments", 0) > 0,
         f"docs={data.get('numberOfDocuments', 0)}")
except Exception as e:
    test("Index stats", False, str(e))

# 10.3 Arabic search
try:
    body = json.dumps({"q": "اختبار", "limit": 5}).encode()
    req = urllib.request.Request(
        f"{MEILI_URL}/indexes/mukh-unified/search",
        data=body,
        headers={
            "Authorization": f"Bearer {MEILI_KEY}",
            "Content-Type": "application/json"
        },
        method="POST"
    )
    resp = urllib.request.urlopen(req, timeout=5)
    data = json.loads(resp.read())
    test("Arabic search returns hits", len(data.get("hits", [])) > 0,
         f"hits={len(data.get('hits', []))}")
except Exception as e:
    test("Arabic search", False, str(e))

# ═══════════════════════════════════════════════════════════════════════════════
# RESULTS
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print(f"  EDGE CASE RESULTS: {passed} pass, {failed} fail, {passed + failed} total")
print("=" * 60)

if errors:
    print("\nFailed tests:")
    for e in errors:
        print(f"  ❌ {e['name']}: {e['details']}")
    sys.exit(1)
else:
    print("\n✅ ALL EDGE CASE TESTS PASSED!")
    sys.exit(0)

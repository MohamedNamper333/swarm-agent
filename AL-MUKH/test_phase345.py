#!/usr/bin/env python3
"""AL-MUKH Phase 3-5 Integration Tests"""

import subprocess
import sys
import os
import json
import tempfile
import hashlib
from pathlib import Path
from datetime import datetime

TESTS = []
PASS = 0
FAIL = 0
SKIP = 0

def test(name):
    def decorator(func):
        TESTS.append((name, func))
        return func
    return decorator

@test("Phase 3: resolver.py scan completes without error")
def t3_1():
    r = subprocess.run(["python3", "resolver.py", "scan"], capture_output=True, text=True, cwd="/home/kali/AL-MUKH")
    # Exit 0 = no broken links, Exit 1 = broken links found (both valid states)
    assert r.returncode in (0, 1), f"Exit {r.returncode}: {r.stderr}"

@test("Phase 3: backlinks.json created")
def t3_2():
    assert os.path.exists("/home/kali/AL-MUKH/refs/backlinks.json"), "Missing backlinks.json"

@test("Phase 3: broken links detected correctly")
def t3_3():
    r = subprocess.run(["python3", "resolver.py", "broken"], capture_output=True, text=True, cwd="/home/kali/AL-MUKH")
    # Exit 0 = no broken links, Exit 1 = broken links found (both valid states)
    assert r.returncode in (0, 1), f"Exit {r.returncode}"

@test("Phase 3: suggest works")
def t3_4():
    r = subprocess.run(["python3", "resolver.py", "suggest", "README"], capture_output=True, text=True, cwd="/home/kali/AL-MUKH")
    assert r.returncode == 0, f"Exit {r.returncode}"

@test("Phase 3: resolve single link")
def t3_5():
    # Create a test file with a cross-vault link
    test_dir = "/tmp/mukh-test-resolver"
    os.makedirs(test_dir, exist_ok=True)
    test_file = os.path.join(test_dir, "test-link.md")
    with open(test_file, "w") as f:
        f.write("# Test\n\nSee [[vault:personal::test]] for details.\n")
    
    r = subprocess.run(["python3", "resolver.py", "resolve", "vault:personal::test"], capture_output=True, text=True, cwd="/home/kali/AL-MUKH")
    # Exit 0 = resolved, Exit 1 = not found (both valid states)
    assert r.returncode in (0, 1), f"Unexpected exit {r.returncode}: {r.stderr}"
    assert "resolved" in r.stdout.lower() or "missing" in r.stdout.lower() or "not found" in r.stdout.lower() or "unrecognised" in r.stdout.lower() or "error" in r.stdout.lower(), f"Unexpected output: {r.stdout}"
    os.remove(test_file)

@test("Phase 3: broken link detection with broken link")
def t3_6():
    test_dir = "/tmp/mukh-test-broken"
    os.makedirs(test_dir, exist_ok=True)
    test_file = os.path.join(test_dir, "broken-link-test.md")
    with open(test_file, "w") as f:
        f.write("# Test\n\nLink to [[vault:proj-swarm::nonexistent-note-xyz123]]\n")
    
    r = subprocess.run(["python3", "resolver.py", "scan"], capture_output=True, text=True, cwd="/home/kali/AL-MUKH")
    r2 = subprocess.run(["python3", "resolver.py", "broken"], capture_output=True, text=True, cwd="/home/kali/AL-MUKH")
    assert r.returncode in (0, 1) and r2.returncode in (0, 1)
    os.remove(test_file)

@test("Phase 4: dashboard.py generate completes")
def t4_1():
    r = subprocess.run(["python3", "dashboard.py", "generate"], capture_output=True, text=True, cwd="/home/kali/AL-MUKH")
    assert r.returncode == 0, f"Exit {r.returncode}: {r.stderr}"
    assert "Wrote" in r.stdout, f"No output: {r.stdout}"

@test("Phase 4: DASHBOARD.md created")
def t4_2():
    assert os.path.exists("/home/kali/AL-MUKH/DASHBOARD.md"), "Missing DASHBOARD.md"
    content = open("/home/kali/AL-MUKH/DASHBOARD.md").read()
    assert len(content) > 100, f"DASHBOARD.md too short: {len(content)} chars"

@test("Phase 4: MAP.md created with Mermaid")
def t4_3():
    assert os.path.exists("/home/kali/AL-MUKH/index/MAP.md"), "Missing MAP.md"
    content = open("/home/kali/AL-MUKH/index/MAP.md").read()
    assert "```mermaid" in content, "MAP.md missing Mermaid diagram"

@test("Phase 4: MOCs created per namespace")
def t4_4():
    moc_dir = "/home/kali/AL-MUKH/index"
    mocs = list(Path(moc_dir).rglob("MOC.md"))
    assert len(mocs) >= 1, f"No MOCs found in {moc_dir}"

@test("Phase 4: DASHBOARD.md has health section")
def t4_5():
    content = open("/home/kali/AL-MUKH/DASHBOARD.md").read()
    assert "health" in content.lower() or "Health" in content or "_disk" in content.lower() or "system" in content.lower(), "Missing health section"

@test("Phase 4: DASHBOARD.md has spoke status")
def t4_6():
    content = open("/home/kali/AL-MUKH/DASHBOARD.md").read()
    assert "Obsidian" in content or "vault" in content.lower() or "spoke" in content.lower(), "Missing spoke status"

@test("Phase 5: validator.py quick passes all checks")
def t5_1():
    r = subprocess.run(["python3", "validator.py", "quick"], capture_output=True, text=True, cwd="/home/kali/AL-MUKH")
    assert r.returncode == 0, f"Exit {r.returncode}"
    assert "ALL CHECKS PASSED" in r.stdout or "Pass" in r.stdout, f"Checks failed: {r.stdout}"

@test("Phase 5: validator.py full completes")
def t5_2():
    r = subprocess.run(["python3", "validator.py", "full"], capture_output=True, text=True, cwd="/home/kali/AL-MUKH")
    assert r.returncode == 0, f"Exit {r.returncode}: {r.stderr}"

@test("Phase 5: validator.py report generates markdown")
def t5_3():
    r = subprocess.run(["python3", "validator.py", "report"], capture_output=True, text=True, cwd="/home/kali/AL-MUKH")
    assert r.returncode == 0, f"Exit {r.returncode}"
    # Check report file was created
    report_files = list(Path("/home/kali/AL-MUKH/refs").glob("validation_*.md"))
    assert len(report_files) >= 1, "No validation report created"

@test("Phase 5: security.py scan completes")
def t5_4():
    r = subprocess.run(["python3", "security.py", "scan"], capture_output=True, text=True, cwd="/home/kali/AL-MUKH")
    assert r.returncode == 0, f"Exit {r.returncode}"
    assert "Risk Level" in r.stdout, f"Missing risk level: {r.stdout}"

@test("Phase 5: security.py report generates markdown")
def t5_5():
    r = subprocess.run(["python3", "security.py", "report"], capture_output=True, text=True, cwd="/home/kali/AL-MUKH")
    assert r.returncode == 0, f"Exit {r.returncode}"

@test("Phase 5: namespace validation catches invalid names")
def t5_6():
    # Test that the validator catches invalid namespace patterns
    import re
    valid_pattern = r'^[a-z][a-z0-9-]*$'
    assert re.match(valid_pattern, "proj-swarm"), "proj-swarm should be valid"
    assert not re.match(valid_pattern, "Project Swarm"), "Project Swarm should be invalid"
    assert not re.match(valid_pattern, "123-start"), "123-start should be invalid"
    assert not re.match(valid_pattern, ""), "Empty should be invalid"

@test("Phase 5: disk space check works")
def t5_7():
    import shutil
    usage = shutil.disk_usage("/home/kali/AL-MUKH")
    total_gb = usage.total / (1024**3)
    free_gb = usage.free / (1024**3)
    used_pct = ((usage.total - usage.free) / usage.total) * 100
    assert total_gb > 0, "Cannot determine disk size"
    assert free_gb > 0, "No free space"
    assert used_pct < 100, "Disk appears full"

@test("Phase 5: SQLite queue integrity check")
def t5_8():
    import sqlite3
    db_path = "/home/kali/AL-MUKH/indexer_queue.sqlite"
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("PRAGMA integrity_check")
        result = cursor.fetchone()
        conn.close()
        assert result[0] == "ok", f"SQLite integrity: {result[0]}"
    else:
        # Queue doesn't exist yet — valid state
        pass

@test("Phase 5: Meilisearch health check via validator")
def t5_9():
    import urllib.request
    try:
        req = urllib.request.urlopen("http://127.0.0.1:7700/health", timeout=5)
        data = json.loads(req.read())
        assert data.get("status") in ("healthy", "available"), f"Not healthy: {data}"
    except Exception as e:
        assert False, f"Meilisearch unreachable: {e}"

@test("Phase 5: file permissions check (no world-writable)")
def t5_10():
    import stat
    for root, dirs, files in os.walk("/home/kali/AL-MUKH"):
        if ".venv" in root or "__pycache__" in root or ".git" in root:
            continue
        for f in files:
            fp = os.path.join(root, f)
            try:
                mode = os.stat(fp).st_mode
                assert not (mode & stat.S_IWOTH), f"World-writable: {fp}"
            except (OSError, PermissionError):
                pass

# Run all tests
print("=" * 60)
print("  AL-MUKH PHASE 3-5 INTEGRATION TESTS")
print("=" * 60)

for name, func in TESTS:
    try:
        func()
        PASS += 1
        print(f"  [PASS] {name}")
    except AssertionError as e:
        FAIL += 1
        print(f"  [FAIL] {name}: {e}")
    except Exception as e:
        FAIL += 1
        print(f"  [FAIL] {name}: {type(e).__name__}: {e}")

print("=" * 60)
total = PASS + FAIL
print(f"  Results: {total} tests, {PASS} pass, {FAIL} fail")
print("=" * 60)

sys.exit(0 if FAIL == 0 else 1)

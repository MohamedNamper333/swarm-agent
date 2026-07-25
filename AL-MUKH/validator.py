#!/usr/bin/env python3
"""
AL-MUKH Full Validation Suite v1.0
Comprehensive health checks for vaults, Meilisearch, config, symlinks, and more.
"""

import os
import sys
import json
import re
import time
import hashlib
import sqlite3
import socket
import shutil
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

try:
    import urllib.request
    import urllib.error
    URLLIB_AVAILABLE = True
except ImportError:
    URLLIB_AVAILABLE = False

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

# ─── Paths ────────────────────────────────────────────────────────────────────
MASTER_VAULT = os.environ.get("AL_MUKH_ROOT", "/home/kali/AL-MUKH")
CONFIG_PATH = os.path.join(MASTER_VAULT, "config.yaml")
REGISTRY_PATH = os.path.join(MASTER_VAULT, "namespace_registry.json")
QUEUE_DB = os.path.join(MASTER_VAULT, "indexer_queue.sqlite")
SPOKES_DIR = os.path.join(MASTER_VAULT, "spokes")
REFS_DIR = os.path.join(MASTER_VAULT, "refs")
SEARCH_DIR = os.path.join(MASTER_VAULT, "search")
LOGS_DIR = os.path.join(MASTER_VAULT, "logs")

MEILI_URL = os.environ.get("MEILI_URL", "http://127.0.0.1:7700")
MEILI_INDEX = "mukh-unified"

# Spoke root paths discovered from config/registry
SPOKE_ROOTS = ["/home/kali/Documents/Obsidian Vault"]

NS_PATTERN = re.compile(r"^[a-z][a-z0-9-]*$")
NS_MAX_LEN = 64
DISK_WARN_PCT = 80
DISK_CRIT_PCT = 90
CHECKSUM_ALGO = "sha256"

# ─── Helpers ──────────────────────────────────────────────────────────────────
class CheckResult:
    def __init__(self, name, status, message="", details=None):
        self.name = name
        self.status = status  # "pass", "warn", "fail", "error"
        self.message = message
        self.details = details or []
        self.ts = datetime.now(timezone.utc).isoformat()

    def to_dict(self):
        d = {
            "check": self.name,
            "status": self.status,
            "message": self.message,
            "timestamp": self.ts,
        }
        if self.details:
            d["details"] = self.details
        return d

    def icon(self):
        return {"pass": "✓", "warn": "⚠", "fail": "✗", "error": "✗"}.get(self.status, "?")

    def __str__(self):
        prefix = f"  [{self.status.upper():5s}] {self.name}"
        if self.message:
            prefix += f": {self.message}"
        return prefix


def _safe_stat(path):
    try:
        return os.stat(path)
    except OSError:
        return None


def _count_files(root, extensions=None, max_count=100000):
    count = 0
    for dirpath, _, filenames in os.walk(root):
        for f in filenames:
            if extensions is None or any(f.endswith(ext) for ext in extensions):
                count += 1
                if count >= max_count:
                    return count
    return count


def _content_hash(filepath):
    h = hashlib.sha256()
    try:
        with open(filepath, "rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
    except OSError:
        return None
    return h.hexdigest()


def _yaml_load(path):
    if YAML_AVAILABLE:
        with open(path, "r") as f:
            return yaml.safe_load(f)
    # Fallback: minimal YAML-ish parse for top-level keys
    return _minimal_yaml(path)


def _minimal_yaml(path):
    """Very basic YAML loader for config.yaml fallback — handles flat key: value."""
    result = {}
    try:
        with open(path, "r") as f:
            for line in f:
                line = line.rstrip()
                if not line or line.startswith("#"):
                    continue
                if ":" in line and not line.startswith(" "):
                    key, _, val = line.partition(":")
                    val = val.strip().strip('"').strip("'")
                    try:
                        val = int(val)
                    except ValueError:
                        try:
                            val = float(val)
                        except ValueError:
                            if val.lower() in ("true", "yes"):
                                val = True
                            elif val.lower() in ("false", "no"):
                                val = False
                            elif val == "":
                                val = None
                    result[key.strip()] = val
    except OSError:
        pass
    return result


def _json_load(path):
    with open(path, "r") as f:
        return json.load(f)


def _meili_request(endpoint, timeout=5):
    url = f"{MEILI_URL}{endpoint}"
    if not URLLIB_AVAILABLE:
        raise RuntimeError("urllib not available")
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    resp = urllib.request.urlopen(req, timeout=timeout)
    return json.loads(resp.read().decode("utf-8"))


def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ─── Checks ───────────────────────────────────────────────────────────────────

def check_vaults_exist():
    """1. Validate all vaults (master + spokes) exist and are readable."""
    results = []

    # Master vault
    st = _safe_stat(MASTER_VAULT)
    if st is None or not os.path.isdir(MASTER_VAULT):
        results.append(CheckResult("vault_master", "fail",
            f"Master vault missing: {MASTER_VAULT}"))
    elif not os.access(MASTER_VAULT, os.R_OK):
        results.append(CheckResult("vault_master", "fail",
            f"Master vault not readable: {MASTER_VAULT}"))
    else:
        results.append(CheckResult("vault_master", "pass",
            f"Master vault OK: {MASTER_VAULT}"))

    # Spoke vaults
    for root in SPOKE_ROOTS:
        label = os.path.basename(root)
        st = _safe_stat(root)
        if st is None or not os.path.isdir(root):
            results.append(CheckResult(f"vault_spoke_{label}", "warn",
                f"Spoke missing: {root}"))
        elif not os.access(root, os.R_OK):
            results.append(CheckResult(f"vault_spoke_{label}", "fail",
                f"Spoke not readable: {root}"))
        else:
            results.append(CheckResult(f"vault_spoke_{label}", "pass",
                f"Spoke OK: {root}"))

    return results


def check_meilisearch_health():
    """2. Check Meilisearch health and index integrity."""
    results = []
    try:
        health = _meili_request("/health")
        status = health.get("status", "unknown")
        if status == "available":
            results.append(CheckResult("meilisearch_health", "pass",
                "Meilisearch is available"))
        else:
            results.append(CheckResult("meilisearch_health", "warn",
                f"Meilisearch status: {status}"))
    except Exception as e:
        results.append(CheckResult("meilisearch_health", "fail",
            f"Meilisearch unreachable: {e}"))
        return results

    # Index check
    try:
        stats = _meili_request(f"/indexes/{MEILI_INDEX}/stats")
        doc_count = stats.get("numberOfDocuments", 0)
        results.append(CheckResult("meilisearch_index", "pass",
            f"Index '{MEILI_INDEX}' exists ({doc_count} docs)"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            results.append(CheckResult("meilisearch_index", "warn",
                f"Index '{MEILI_INDEX}' not found (will be created on first index)"))
        else:
            results.append(CheckResult("meilisearch_index", "fail",
                f"Index check failed: HTTP {e.code}"))
    except Exception as e:
        results.append(CheckResult("meilisearch_index", "fail",
            f"Index check error: {e}"))

    return results


def check_config_files():
    """3. Verify config files are valid."""
    results = []

    # config.yaml
    if not os.path.isfile(CONFIG_PATH):
        results.append(CheckResult("config_yaml", "fail",
            f"Missing: {CONFIG_PATH}"))
    else:
        try:
            cfg = _yaml_load(CONFIG_PATH)
            if cfg and isinstance(cfg, dict):
                required = ["master_vault", "namespaces", "indexer"]
                missing = [k for k in required if k not in cfg]
                if missing:
                    results.append(CheckResult("config_yaml", "warn",
                        f"Missing top-level keys: {', '.join(missing)}"))
                else:
                    results.append(CheckResult("config_yaml", "pass",
                        f"config.yaml valid ({len(cfg)} top-level keys)"))
            else:
                results.append(CheckResult("config_yaml", "warn",
                    "config.yaml parsed but yielded non-dict"))
        except Exception as e:
            results.append(CheckResult("config_yaml", "fail",
                f"config.yaml parse error: {e}"))

    # namespace_registry.json
    if not os.path.isfile(REGISTRY_PATH):
        results.append(CheckResult("namespace_registry", "fail",
            f"Missing: {REGISTRY_PATH}"))
    else:
        try:
            reg = _json_load(REGISTRY_PATH)
            spokes = reg.get("spokes", {})
            results.append(CheckResult("namespace_registry", "pass",
                f"namespace_registry.json valid ({len(spokes)} spokes)"))
        except json.JSONDecodeError as e:
            results.append(CheckResult("namespace_registry", "fail",
                f"namespace_registry.json JSON error: {e}"))
        except Exception as e:
            results.append(CheckResult("namespace_registry", "fail",
                f"namespace_registry.json error: {e}"))

    return results


def check_broken_symlinks():
    """4. Check for broken symlinks in master vault."""
    broken = []
    count = 0
    for dirpath, _, filenames in os.walk(MASTER_VAULT):
        # Skip hidden dirs and __pycache__
        parts = Path(dirpath).parts
        if any(p.startswith(".") or p == "__pycache__" for p in parts):
            continue
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if os.path.islink(fp):
                count += 1
                if not os.path.exists(fp):
                    broken.append(fp)

    if broken:
        return [CheckResult("broken_symlinks", "warn",
            f"{len(broken)} broken symlink(s) of {count} total",
            details=broken[:20])]
    return [CheckResult("broken_symlinks", "pass",
        f"No broken symlinks ({count} symlinks checked)")]


def check_duplicates():
    """5. Check for duplicate content by content hash."""
    hash_map = defaultdict(list)
    scanned = 0

    search_dirs = [MASTER_VAULT]
    search_dirs.extend(SPOKE_ROOTS)

    for root in search_dirs:
        if not os.path.isdir(root):
            continue
        for dirpath, _, filenames in os.walk(root):
            parts = Path(dirpath).parts
            if any(p.startswith(".") or p in ("__pycache__", "node_modules") for p in parts):
                continue
            for f in filenames:
                if not f.endswith(".md"):
                    continue
                fp = os.path.join(dirpath, f)
                if not os.path.isfile(fp) or os.path.islink(fp):
                    continue
                h = _content_hash(fp)
                if h:
                    hash_map[h].append(fp)
                    scanned += 1

    dupes = {h: paths for h, paths in hash_map.items() if len(paths) > 1}
    total_duped = sum(len(v) for v in dupes.values())

    if dupes:
        details = []
        for h, paths in list(dupes.items())[:10]:
            details.append(f"Hash {h[:12]}...: {', '.join(os.path.basename(p) for p in paths)}")
        return [CheckResult("duplicate_content", "warn",
            f"{total_duped} files share content with {len(dupes)} hash groups ({scanned} scanned)",
            details=details)]
    return [CheckResult("duplicate_content", "pass",
        f"No duplicates ({scanned} files scanned)")]


def check_namespace_naming():
    """6. Validate namespace naming rules."""
    try:
        reg = _json_load(REGISTRY_PATH)
    except Exception:
        return [CheckResult("namespace_naming", "error",
            "Cannot load namespace_registry.json")]

    spokes = reg.get("spokes", {})
    violations = []

    for name in spokes:
        if not NS_PATTERN.match(name):
            violations.append(f"'{name}' — invalid pattern (expected: ^[a-z][a-z0-9-]*$)")
        if len(name) > NS_MAX_LEN:
            violations.append(f"'{name}' — exceeds {NS_MAX_LEN} chars ({len(name)})")

    if violations:
        return [CheckResult("namespace_naming", "fail",
            f"{len(violations)} namespace violation(s)",
            details=violations[:20])]
    return [CheckResult("namespace_naming", "pass",
        f"All {len(spokes)} namespaces follow naming rules")]


def check_disk_space():
    """7. Check disk space (warn at 80%, critical at 90%)."""
    results = []
    usage = shutil.disk_usage(MASTER_VAULT)
    pct_used = (usage.used / usage.total) * 100
    free_gb = usage.free / (1024 ** 3)
    total_gb = usage.total / (1024 ** 3)

    msg = f"{pct_used:.1f}% used, {free_gb:.1f} GB free of {total_gb:.1f} GB"

    if pct_used >= DISK_CRIT_PCT:
        results.append(CheckResult("disk_space", "fail",
            f"CRITICAL: {msg} (>= {DISK_CRIT_PCT}%)"))
    elif pct_used >= DISK_WARN_PCT:
        results.append(CheckResult("disk_space", "warn",
            f"WARNING: {msg} (>= {DISK_WARN_PCT}%)"))
    else:
        results.append(CheckResult("disk_space", "pass", msg))

    return results


def check_network_meilisearch():
    """8. Test network connectivity to Meilisearch."""
    try:
        parsed = urllib.request.urlparse(MEILI_URL) if URLLIB_AVAILABLE else None
        host = parsed.hostname if parsed else "127.0.0.1"
        port = parsed.port if parsed else 7700
    except Exception:
        host, port = "127.0.0.1", 7700

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(3)
    try:
        sock.connect((host, port))
        sock.close()
        return [CheckResult("network_meilisearch", "pass",
            f"TCP {host}:{port} reachable")]
    except (socket.timeout, ConnectionRefusedError, OSError) as e:
        return [CheckResult("network_meilisearch", "fail",
            f"TCP {host}:{port} unreachable: {e}")]
    finally:
        try:
            sock.close()
        except OSError:
            pass


def check_sqlite_queue():
    """9. Verify SQLite queue integrity."""
    if not os.path.isfile(QUEUE_DB):
        return [CheckResult("sqlite_queue", "warn",
            f"Queue DB not found: {QUEUE_DB}")]

    try:
        conn = sqlite3.connect(f"file:{QUEUE_DB}?mode=ro", uri=True)
        cur = conn.cursor()

        # Check WAL mode
        cur.execute("PRAGMA journal_mode")
        journal = cur.fetchone()[0]

        # Count entries
        cur.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
        table_count = cur.fetchone()[0]

        # Try common table names
        total_rows = 0
        tables_with_rows = []
        for tbl_name in ["queue", "pending", "tasks", "jobs"]:
            try:
                cur.execute(f"SELECT COUNT(*) FROM [{tbl_name}]")
                cnt = cur.fetchone()[0]
                total_rows += cnt
                if cnt > 0:
                    tables_with_rows.append(f"{tbl_name}:{cnt}")
            except sqlite3.OperationalError:
                pass

        # Integrity check
        cur.execute("PRAGMA integrity_check")
        integrity = cur.fetchone()[0]

        conn.close()

        details = [
            f"Journal: {journal}",
            f"Tables: {table_count}",
            f"Rows: {total_rows}",
        ]
        if tables_with_rows:
            details.append(f"With data: {', '.join(tables_with_rows)}")

        if integrity == "ok":
            return [CheckResult("sqlite_queue", "pass",
                f"SQLite queue OK ({total_rows} rows)",
                details=details)]
        return [CheckResult("sqlite_queue", "fail",
            f"SQLite integrity check: {integrity}",
            details=details)]

    except Exception as e:
        return [CheckResult("sqlite_queue", "fail",
            f"SQLite queue error: {e}")]


def check_vault_integrity():
    """Supplementary: file count and structure overview."""
    details = []
    dirs_to_check = {
        "master": MASTER_VAULT,
        "spokes": SPOKES_DIR,
        "refs": REFS_DIR,
        "search": SEARCH_DIR,
        "logs": LOGS_DIR,
    }
    for label, path in dirs_to_check.items():
        if os.path.isdir(path):
            md_count = _count_files(path, [".md"])
            total = _count_files(path)
            details.append(f"{label}: {total} files ({md_count} .md)")
        else:
            details.append(f"{label}: MISSING")

    return [CheckResult("vault_structure", "pass",
        f"Directory overview",
        details=details)]


# ─── Runner ───────────────────────────────────────────────────────────────────

ALL_CHECKS = {
    "vaults": check_vaults_exist,
    "meilisearch": check_meilisearch_health,
    "config": check_config_files,
    "symlinks": check_broken_symlinks,
    "duplicates": check_duplicates,
    "namespaces": check_namespace_naming,
    "disk": check_disk_space,
    "network": check_network_meilisearch,
    "sqlite": check_sqlite_queue,
    "structure": check_vault_integrity,
}

QUICK_CHECKS = ["vaults", "config", "disk", "sqlite", "network", "structure"]


def run_checks(check_names=None):
    if check_names is None:
        check_names = list(ALL_CHECKS.keys())

    all_results = []
    for name in check_names:
        fn = ALL_CHECKS.get(name)
        if fn is None:
            all_results.append(CheckResult(name, "error", f"Unknown check: {name}"))
            continue
        try:
            results = fn()
            all_results.extend(results)
        except Exception as e:
            all_results.append(CheckResult(name, "error", f"Unhandled: {e}"))

    return all_results


def print_results(results):
    counts = defaultdict(int)
    for r in results:
        counts[r.status] += 1
        print(r)

    total = len(results)
    passed = counts["pass"]
    warned = counts["warn"]
    failed = counts["fail"] + counts["error"]

    print()
    print(f"  Total: {total}  Pass: {passed}  Warn: {warned}  Fail/Error: {failed}")
    if failed > 0:
        print("  ✗ VALIDATION FAILED")
    elif warned > 0:
        print("  ⚠ PASSED WITH WARNINGS")
    else:
        print("  ✓ ALL CHECKS PASSED")


def generate_json_report(results):
    report = {
        "validator": "AL-MUKH Validation Suite v1.0",
        "generated": _now_iso(),
        "master_vault": MASTER_VAULT,
        "checks": [r.to_dict() for r in results],
        "summary": {
            "total": len(results),
            "pass": sum(1 for r in results if r.status == "pass"),
            "warn": sum(1 for r in results if r.status == "warn"),
            "fail": sum(1 for r in results if r.status in ("fail", "error")),
        },
    }
    report["summary"]["status"] = (
        "FAILED" if report["summary"]["fail"] > 0
        else "WARNINGS" if report["summary"]["warn"] > 0
        else "PASSED"
    )
    return report


def generate_markdown_report(results):
    report = generate_json_report(results)
    s = report["summary"]

    lines = [
        "# AL-MUKH Validation Report",
        "",
        f"**Generated:** {report['generated']}",
        f"**Vault:** `{report['master_vault']}`",
        f"**Status:** {'✓ PASSED' if s['status'] == 'PASSED' else '⚠ WARNINGS' if s['status'] == 'WARNINGS' else '✗ FAILED'}",
        "",
        f"| Metric | Count |",
        f"|--------|-------|",
        f"| Total  | {s['total']} |",
        f"| Pass   | {s['pass']} |",
        f"| Warn   | {s['warn']} |",
        f"| Fail   | {s['fail']} |",
        "",
        "---",
        "",
        "## Check Results",
        "",
    ]

    for r in results:
        lines.append(f"### {r.icon()} {r.name}")
        if r.message:
            lines.append(f"- **{r.message}**")
        if r.details:
            for d in r.details:
                lines.append(f"  - `{d}`")
        lines.append("")

    lines.extend([
        "---",
        f"*Generated by AL-MUKH Validation Suite v1.0*",
    ])
    return "\n".join(lines)


def save_report(results, fmt="json"):
    report_dir = os.path.join(MASTER_VAULT, "refs")
    os.makedirs(report_dir, exist_ok=True)

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    if fmt == "json":
        path = os.path.join(report_dir, f"validation_{ts}.json")
        with open(path, "w") as f:
            json.dump(generate_json_report(results), f, indent=2)
    else:
        path = os.path.join(report_dir, f"validation_{ts}.md")
        with open(path, "w") as f:
            f.write(generate_markdown_report(results))

    print(f"  Report saved: {path}")
    return path


# ─── CLI ──────────────────────────────────────────────────────────────────────

USAGE = """
AL-MUKH Validation Suite v1.0

Usage:
  python validator.py full      Run all checks
  python validator.py quick     Basic health checks only
  python validator.py report    Generate markdown report
  python validator.py json      Generate JSON report
  python validator.py --help    Show this help

Examples:
  python validator.py full
  python validator.py quick
  python validator.py report
"""


def main():
    args = sys.argv[1:]

    if not args or args[0] in ("-h", "--help", "help"):
        print(USAGE)
        return

    cmd = args[0].lower()

    if cmd == "full":
        print("─── AL-MUKH Validation Suite v1.0 ───")
        print()
        results = run_checks()
        print_results(results)
        save_report(results, "json")

    elif cmd == "quick":
        print("─── AL-MUKH Quick Health Check ───")
        print()
        results = run_checks(QUICK_CHECKS)
        print_results(results)

    elif cmd == "report":
        results = run_checks()
        md = generate_markdown_report(results)
        path = save_report(results, "md")
        print()
        print(md)

    elif cmd == "json":
        results = run_checks()
        report = generate_json_report(results)
        print(json.dumps(report, indent=2))
        save_report(results, "json")

    else:
        print(f"Unknown command: {cmd}")
        print(USAGE)
        sys.exit(1)


if __name__ == "__main__":
    main()

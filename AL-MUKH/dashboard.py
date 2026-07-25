#!/usr/bin/env python3
"""
AL-MUKH Dashboard Generator v1.0
Generates DASHBOARD.md, index/MAP.md, and per-namespace MOCs.
Monitors system health, disk usage, sync status, and duplicate detection.

CLI:
  python dashboard.py generate   — generate all dashboard files
  python dashboard.py watch      — auto-update every 5 minutes
  python dashboard.py disk       — check disk space
"""
import os
import sys
import json
import time
import hashlib
import shutil
import threading
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

import urllib.request
import urllib.error

# ─── Configuration ───────────────────────────────────────────────────────────
MASTER_VAULT = "/home/kali/AL-MUKH"
SPOKE_ROOTS = [
    "/home/kali/Documents/Obsidian Vault",
]
MEILI_URL = os.environ.get("MEILI_URL", "http://127.0.0.1:7700")
MEILI_KEY = os.environ.get("MEILI_MASTER_KEY", "mukh-dev-key-change-in-prod")
INDEX_NAME = "mukh-unified"

DASHBOARD_PATH = os.path.join(MASTER_VAULT, "DASHBOARD.md")
MAP_PATH = os.path.join(MASTER_VAULT, "index", "MAP.md")
MOC_DIR = os.path.join(MASTER_VAULT, "index")

WATCHER_HEALTH_URL = "http://127.0.0.1:8765/health"

UPDATE_INTERVAL = 300
WARN_PCT = 80
PAUSE_PCT = 90
MAX_RECENT = 10
TRENDS_WINDOW_DAYS = 30

EXCLUDE_DIRS = {
    ".obsidian", ".git", ".trash", "__pycache__", ".venv",
    "spokes", "index", "refs", "search", "logs", "config",
}


# ─── HTTP Helpers ────────────────────────────────────────────────────────────
def meili_get(endpoint):
    req = urllib.request.Request(
        f"{MEILI_URL}{endpoint}",
        headers={"Authorization": f"Bearer {MEILI_KEY}"},
    )
    try:
        resp = urllib.request.urlopen(req, timeout=5)
        return json.loads(resp.read())
    except Exception:
        return None


def meili_stats():
    return meili_get(f"/indexes/{INDEX_NAME}/stats")


def meili_health():
    result = meili_get("/health")
    if result and result.get("status") == "available":
        return True, "healthy"
    return False, "unavailable"


def watcher_health():
    try:
        req = urllib.request.Request(WATCHER_HEALTH_URL)
        resp = urllib.request.urlopen(req, timeout=2)
        data = json.loads(resp.read())
        return True, data
    except Exception:
        return False, None


# ─── Disk Usage ──────────────────────────────────────────────────────────────
def disk_usage(path="/"):
    usage = shutil.disk_usage(path)
    total = usage.total
    used = usage.used
    free = usage.free
    pct = (used / total * 100) if total else 0
    return {
        "total_gb": round(total / (1024 ** 3), 1),
        "used_gb": round(used / (1024 ** 3), 1),
        "free_gb": round(free / (1024 ** 3), 1),
        "percent": round(pct, 1),
        "status": "pause" if pct >= PAUSE_PCT else ("warn" if pct >= WARN_PCT else "ok"),
    }


def format_size(size_bytes):
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 ** 3):.1f} GB"


# ─── File Discovery ──────────────────────────────────────────────────────────
def content_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def walk_md_files(roots):
    """Walk directories for .md files, yielding (path, mtime, size)."""
    for root in roots:
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
            for f in filenames:
                if f.endswith(".md"):
                    fp = os.path.join(dirpath, f)
                    try:
                        st = os.stat(fp)
                        yield fp, st.st_mtime, st.st_size
                    except OSError:
                        pass


def parse_frontmatter(content):
    if content.startswith("---"):
        end = content.find("---", 3)
        if end > 0:
            return content[3:end].strip(), content[end + 3:].strip()
    return "", content


def extract_tags(content):
    tags = set()
    fm, body = parse_frontmatter(content)
    for line in fm.split("\n"):
        if line.strip().startswith("tags:"):
            for t in line.split(":", 1)[1].split(","):
                t = t.strip().strip("[]\"'")
                if t:
                    tags.add(t)
    import re
    for match in re.finditer(r"(?<!\w)#([a-zA-Z_]\w*)", body):
        tags.add(match.group(1))
    return sorted(tags)


def extract_headings(content, limit=6):
    import re
    return [m.group(1).strip() for m in re.finditer(r"^#{1,6}\s+(.+)$", content, re.MULTILINE)][:limit]


# ─── Spoke Scanner ──────────────────────────────────────────────────────────
def scan_spoke(spoke_path, max_recent=MAX_RECENT):
    """Scan a single spoke directory and return stats."""
    files = []
    total_size = 0
    hash_map = defaultdict(list)
    all_tags = defaultdict(int)
    recent = []

    for fp, mtime, size in walk_md_files([spoke_path]):
        files.append(fp)
        total_size += size
        recent.append((fp, mtime, size))

        try:
            with open(fp, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            h = content_hash(content)
            hash_map[h].append(fp)
            for tag in extract_tags(content):
                all_tags[tag] += 1
        except Exception:
            pass

    recent.sort(key=lambda x: x[1], reverse=True)
    recent = recent[:max_recent]

    duplicates = {h: paths for h, paths in hash_map.items() if len(paths) > 1}

    return {
        "file_count": len(files),
        "total_size": total_size,
        "recent_files": [
            {
                "path": fp,
                "name": os.path.basename(fp),
                "mtime": datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M"),
                "size": format_size(size),
            }
            for fp, mtime, size in recent
        ],
        "duplicates": duplicates,
        "top_tags": dict(sorted(all_tags.items(), key=lambda x: -x[1])[:15]),
    }


def resolve_namespace(spoke_path):
    """Resolve spoke path to namespace name."""
    basename = os.path.basename(spoke_path)
    if basename:
        return basename.lower().replace(" ", "-")
    return "unknown"


def determine_spoke_status(info):
    if info["file_count"] == 0:
        return "error", "empty"
    if info["duplicates"]:
        return "degraded", f"{len(info['duplicates'])} duplicate groups"
    return "healthy", f"{info['file_count']} files"


# ─── Meilisearch Index Stats ────────────────────────────────────────────────
def get_index_breakdown():
    """Get per-namespace document counts from Meilisearch."""
    stats = meili_stats()
    if not stats:
        return None, 0

    total = stats.get("numberOfDocuments", 0)
    return stats, total


def get_namespace_facets():
    """Query Meilisearch for namespace distribution."""
    result = meili_get(f"/indexes/{INDEX_NAME}/search")
    result = meili_get(f"/indexes/{INDEX_NAME}/stats")
    return result


# ─── Duplicate Detection ─────────────────────────────────────────────────────
def find_global_duplicates(roots):
    """Find duplicate files across all roots using content hashes."""
    hash_map = defaultdict(list)
    for fp, mtime, size in walk_md_files(roots):
        try:
            with open(fp, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            h = content_hash(content)
            hash_map[h].append(fp)
        except Exception:
            pass

    return {h: paths for h, paths in hash_map.items() if len(paths) > 1}


# ─── Dashboard Generator ─────────────────────────────────────────────────────
class DashboardGenerator:
    def __init__(self):
        self.last_generated = None
        self.generation_count = 0

    def generate_all(self):
        now = datetime.now()
        print(f"[DASHBOARD] Generating at {now.strftime('%Y-%m-%d %H:%M:%S')}...")

        disk = disk_usage("/")
        meili_ok, meili_status = meili_health()
        watcher_ok, watcher_data = watcher_health()
        index_stats, total_docs = get_index_breakdown()

        spoke_results = {}
        for spoke_path in SPOKE_ROOTS:
            ns = resolve_namespace(spoke_path)
            exists = os.path.isdir(spoke_path)
            if exists:
                info = scan_spoke(spoke_path)
                status, reason = determine_spoke_status(info)
            else:
                info = {"file_count": 0, "total_size": 0, "recent_files": [], "duplicates": {}, "top_tags": {}}
                status, reason = "error", "path not found"
            spoke_results[ns] = {
                "status": status,
                "reason": reason,
                "path": spoke_path,
                "exists": exists,
                **info,
            }

        # Also scan master vault md files
        vault_info = scan_spoke(MASTER_VAULT)
        vault_status, vault_reason = determine_spoke_status(vault_info)
        spoke_results["al-mukh-vault"] = {
            "status": vault_status,
            "reason": vault_reason,
            "path": MASTER_VAULT,
            "exists": True,
            **vault_info,
        }

        self._write_dashboard(disk, meili_ok, meili_status, watcher_ok, watcher_data,
                              index_stats, total_docs, spoke_results)
        self._write_map(spoke_results, meili_ok, total_docs)
        self._write_mocs(spoke_results)

        self.last_generated = now
        self.generation_count += 1
        print(f"[DASHBOARD] Done. Generation #{self.generation_count}")

    def _write_dashboard(self, disk, meili_ok, meili_status, watcher_ok, watcher_data,
                         index_stats, total_docs, spokes):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        disk_icon = "🔴" if disk["status"] == "pause" else ("🟡" if disk["status"] == "warn" else "🟢")
        meili_icon = "🟢" if meili_ok else "🔴"
        watcher_icon = "🟢" if watcher_ok else "🔴"

        lines = [
            "# AL-MUKH Dashboard",
            f"> Auto-generated: {now} | Update #{self.generation_count}",
            "",
            "---",
            "",
            "## System Health",
            "",
            f"| Component | Status | Details |",
            f"|-----------|--------|---------|",
            f"| Meilisearch | {meili_icon} {meili_status} | `{MEILI_URL}` |",
            f"| Watcher | {watcher_icon} {'active' if watcher_ok else 'offline'} | `{WATCHER_HEALTH_URL}` |",
            f"| Disk | {disk_icon} {disk['percent']}% used | {disk['used_gb']} / {disk['total_gb']} GB free: {disk['free_gb']} GB |",
        ]

        if disk["status"] == "warn":
            lines.append("")
            lines.append(f"> **WARNING**: Disk usage at {disk['percent']}% — approaching threshold ({WARN_PCT}%)")
        if disk["status"] == "pause":
            lines.append("")
            lines.append(f"> **CRITICAL**: Disk usage at {disk['percent']}% — indexing should be paused (>{PAUSE_PCT}%)")

        if watcher_ok and watcher_data:
            uptime = watcher_data.get("uptime", 0)
            stats = watcher_data.get("stats", {})
            lines.append("")
            lines.append(f"| Watcher Uptime | {uptime:.0f}s | Created: {stats.get('created',0)} Modified: {stats.get('modified',0)} Errors: {stats.get('errors',0)} |")

        lines.extend([
            "",
            "---",
            "",
            "## Per-Spoke Sync Status",
            "",
            "| Spoke | Status | Files | Size | Duplicate Groups | Top Tags |",
            "|-------|--------|-------|------|------------------|----------|",
        ])

        for ns, info in sorted(spokes.items()):
            status = info["status"]
            icon = {"healthy": "🟢", "degraded": "🟡", "error": "🔴"}.get(status, "⚪")
            dup_count = len(info["duplicates"])
            top_tags = ", ".join(list(info["top_tags"].keys())[:5]) or "-"
            lines.append(
                f"| `{ns}` | {icon} {status} | {info['file_count']} | {format_size(info['total_size'])} | {dup_count} | {top_tags} |"
            )

        lines.extend(["", "---", ""])

        # Recent changes
        lines.append("## Recent Changes")
        lines.append("")
        lines.append("| File | Spoke | Modified | Size |")
        lines.append("|------|-------|----------|------|")

        all_recent = []
        for ns, info in spokes.items():
            for rf in info["recent_files"]:
                all_recent.append((rf, ns))
        all_recent.sort(key=lambda x: x[0]["mtime"], reverse=True)

        for rf, ns in all_recent[:MAX_RECENT]:
            lines.append(f"| `{rf['name']}` | `{ns}` | {rf['mtime']} | {rf['size']} |")

        lines.extend(["", "---", ""])

        # Index Statistics
        lines.append("## Index Statistics")
        lines.append("")
        if index_stats:
            lines.append(f"| Metric | Value |")
            lines.append(f"|--------|-------|")
            lines.append(f"| Total Documents | **{total_docs}** |")
            is_indexing = index_stats.get('isIndexing', False)
            lines.append(f"| Currently Indexing | {'Yes' if is_indexing else 'No'} |")
            for field_stat in index_stats.get("fieldDistribution", {}).items():
                lines.append(f"| Field: `{field_stat[0]}` | {field_stat[1]} docs |")
        else:
            lines.append("*Meilisearch not available*")

        lines.extend(["", "---", ""])

        # Per-Namespace Breakdown
        lines.append("## Per-Namespace Document Count")
        lines.append("")
        lines.append("| Namespace | Files on Disk | Est. Indexed | Status |")
        lines.append("|-----------|---------------|--------------|--------|")
        for ns, info in sorted(spokes.items()):
            est_indexed = f"~{info['file_count']}" if meili_ok else "n/a"
            lines.append(f"| `{ns}` | {info['file_count']} | {est_indexed} | {info['status']} |")

        lines.extend(["", "---", ""])

        # Duplicate Detection
        lines.append("## Duplicate Detection")
        lines.append("")
        all_dups = find_global_duplicates(SPOKE_ROOTS + [MASTER_VAULT])
        if all_dups:
            lines.append(f"Found **{len(all_dups)}** duplicate groups:")
            lines.append("")
            for i, (h, paths) in enumerate(sorted(all_dups.items(), key=lambda x: -len(x[1]))[:10], 1):
                lines.append(f"### Group {i} (`{h}`)")
                lines.append("")
                for p in paths:
                    lines.append(f"- `{p}`")
                lines.append("")
        else:
            lines.append("No duplicates detected.")

        lines.extend(["", "---", ""])

        # Search Trends (placeholder)
        lines.append("## Search Trends")
        lines.append("")
        lines.append(f"*Data window: last {TRENDS_WINDOW_DAYS} days*")
        lines.append("")
        lines.append("| Trend | Count | Direction |")
        lines.append("|-------|-------|-----------|")
        lines.append("| (placeholder) | - | - |")
        lines.append("")
        lines.append("> Search trend data will populate as queries accumulate in Meilisearch logs.")

        lines.extend(["", "---", ""])

        # Footer
        lines.append(f"## Info")
        lines.append("")
        lines.append(f"- **Generated by**: `AL-MUKH Dashboard Generator v1.0`")
        lines.append(f"- **Master vault**: `{MASTER_VAULT}`")
        lines.append(f"- **Spoke roots**: {len(SPOKE_ROOTS)}")
        lines.append(f"- **Update interval**: {UPDATE_INTERVAL}s")
        lines.append(f"- **Disk thresholds**: warn={WARN_PCT}%, pause={PAUSE_PCT}%")
        lines.append("")

        with open(DASHBOARD_PATH, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        print(f"[OK] Wrote {DASHBOARD_PATH}")

    def _write_map(self, spokes, meili_ok, total_docs):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        lines = [
            "# AL-MUKH Global Map",
            f"> Auto-generated: {now}",
            "",
            "---",
            "",
            "## Spoke Network",
            "",
        ]

        # Mermaid diagram
        lines.append("```mermaid")
        lines.append("graph TD")
        lines.append(f"    ALMUKH[\"AL-MUKH<br/>Master Vault<br/>Docs: {total_docs}\"]")
        lines.append("")

        for ns, info in sorted(spokes.items()):
            safe_ns = ns.replace("-", "_").replace(" ", "_")
            icon = {"healthy": "🟢", "degraded": "🟡", "error": "🔴"}.get(info["status"], "⚪")
            label = f"{ns}<br/>{info['file_count']} files<br/>{icon} {info['status']}"
            lines.append(f"    {safe_ns}[\"{label}\"]")
            lines.append(f"    ALMUKH --> {safe_ns}")

        lines.append("```")
        lines.extend(["", "---", ""])

        # Table
        lines.append("## Spoke Details")
        lines.append("")
        lines.append("| Spoke | Path | Files | Size | Status | Last Modified |")
        lines.append("|-------|------|-------|------|--------|---------------|")

        for ns, info in sorted(spokes.items()):
            icon = {"healthy": "🟢", "degraded": "🟡", "error": "🔴"}.get(info["status"], "⚪")
            last_mod = info["recent_files"][0]["mtime"] if info["recent_files"] else "-"
            lines.append(
                f"| `{ns}` | `{info['path']}` | {info['file_count']} | {format_size(info['total_size'])} | {icon} {info['status']} | {last_mod} |"
            )

        lines.extend(["", "---", ""])

        # Namespace hierarchy
        lines.append("## Namespace Hierarchy")
        lines.append("")
        lines.append("```mermaid")
        lines.append("graph LR")
        lines.append("    subgraph Master Vault")
        lines.append("        ROOT[AL-MUKH]")

        # Group by top-level dirs in master vault
        vault_dirs = []
        for entry in os.scandir(MASTER_VAULT):
            if entry.is_dir() and entry.name not in EXCLUDE_DIRS and not entry.name.startswith(".") and entry.name != ".venv":
                vault_dirs.append(entry.name)

        for d in sorted(vault_dirs):
            safe_d = d.replace("-", "_")
            lines.append(f"        {safe_d}[{d}]")
            lines.append(f"        ROOT --> {safe_d}")

        lines.append("    end")

        for ns, info in sorted(spokes.items()):
            if info["exists"]:
                safe_ns = ns.replace("-", "_")
                lines.append(f"    ROOT -.-> {safe_ns}")

        lines.append("```")
        lines.append("")

        with open(MAP_PATH, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        print(f"[OK] Wrote {MAP_PATH}")

    def _write_mocs(self, spokes):
        os.makedirs(MOC_DIR, exist_ok=True)

        for ns, info in sorted(spokes.items()):
            ns_dir = os.path.join(MOC_DIR, ns)
            os.makedirs(ns_dir, exist_ok=True)
            moc_path = os.path.join(ns_dir, "MOC.md")

            icon = {"healthy": "🟢", "degraded": "🟡", "error": "🔴"}.get(info["status"], "⚪")

            lines = [
                f"# MOC: {ns}",
                f"> Map of Content for namespace `{ns}`",
                "",
                "---",
                "",
                "## Overview",
                "",
                f"- **Status**: {icon} {info['status']}",
                f"- **Path**: `{info['path']}`",
                f"- **Total files**: {info['file_count']}",
                f"- **Total size**: {format_size(info['total_size'])}",
                "",
            ]

            if info["top_tags"]:
                lines.append("## Tags")
                lines.append("")
                for tag, count in info["top_tags"].items():
                    lines.append(f"- `{tag}` ({count})")
                lines.append("")

            if info["recent_files"]:
                lines.append("## Recent Files")
                lines.append("")
                lines.append("| File | Modified | Size |")
                lines.append("|------|----------|------|")
                for rf in info["recent_files"]:
                    lines.append(f"| `{rf['name']}` | {rf['mtime']} | {rf['size']} |")
                lines.append("")

            if info["duplicates"]:
                lines.append("## Duplicates Detected")
                lines.append("")
                for i, (h, paths) in enumerate(info["duplicates"].items(), 1):
                    lines.append(f"### Group {i} (`{h}`)")
                    for p in paths:
                        lines.append(f"- `{p}`")
                    lines.append("")

            lines.append("---")
            lines.append(f"*Generated by AL-MUKH Dashboard v1.0*")
            lines.append("")

            with open(moc_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))

        print(f"[OK] Wrote {len(spokes)} MOCs")


# ─── Watch Mode ──────────────────────────────────────────────────────────────
_stop_event = threading.Event()


def watch_loop():
    gen = DashboardGenerator()
    print(f"[WATCH] Generating every {UPDATE_INTERVAL}s. Ctrl+C to stop.")

    while not _stop_event.is_set():
        try:
            gen.generate_all()
        except Exception as e:
            print(f"[WATCH ERROR] {e}")
        _stop_event.wait(UPDATE_INTERVAL)

    print("[WATCH] Stopped.")


# ─── Disk Command ────────────────────────────────────────────────────────────
def disk_check():
    disk = disk_usage("/")
    status_icon = {"ok": "🟢", "warn": "🟡", "pause": "🔴"}[disk["status"]]

    print(f"AL-MUKH Disk Status")
    print(f"===================")
    print(f"  Total:  {disk['total_gb']} GB")
    print(f"  Used:   {disk['used_gb']} GB ({disk['percent']}%)")
    print(f"  Free:   {disk['free_gb']} GB")
    print(f"  Status: {status_icon} {disk['status']}")
    print()

    if disk["status"] == "warn":
        print(f"  ⚠ WARNING: Usage above {WARN_PCT}% threshold")
    elif disk["status"] == "pause":
        print(f"  🔴 CRITICAL: Usage above {PAUSE_PCT}% — indexing should be paused")
    else:
        print(f"  ✅ Healthy — below {WARN_PCT}% threshold")

    return disk


# ─── CLI ─────────────────────────────────────────────────────────────────────
def main():
    if len(sys.argv) < 2:
        print("AL-MUKH Dashboard Generator v1.0")
        print("")
        print("Usage: python dashboard.py <command>")
        print("")
        print("Commands:")
        print("  generate  Generate all dashboard files (DASHBOARD.md, MAP.md, MOCs)")
        print("  watch     Auto-update every 5 minutes in background")
        print("  disk      Check disk space usage")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "generate":
        gen = DashboardGenerator()
        gen.generate_all()

    elif cmd == "watch":
        try:
            watch_loop()
        except KeyboardInterrupt:
            _stop_event.set()
            print("\n[WATCH] Shutting down...")

    elif cmd == "disk":
        disk_check()

    else:
        print(f"Unknown command: {cmd}")
        print("Commands: generate, watch, disk")
        sys.exit(1)


if __name__ == "__main__":
    main()

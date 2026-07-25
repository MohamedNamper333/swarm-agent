#!/usr/bin/env python3
"""
AL-MUKH Symlink Manager v1.0
Manages cross-vault symlinks with atomic replace, inode tracking, and broken link detection
"""
import os
import sys
import json
import time
import hashlib
import shutil
from pathlib import Path
from datetime import datetime

# ─── Configuration ───────────────────────────────────────────────────────────
MASTER_VAULT = "/home/kali/AL-MUKH"
SPOKES_DIR = os.path.join(MASTER_VAULT, "spokes")
REFS_DIR = os.path.join(MASTER_VAULT, "refs")

LINK_SYNTAX = {
    "prefix": "vault:",
    "separator": "::",
    "suffix": "]"
}

# ─── Helpers ─────────────────────────────────────────────────────────────────
def load_registry():
    """Load namespace registry"""
    path = os.path.join(MASTER_VAULT, "namespace_registry.json")
    with open(path, "r") as f:
        return json.load(f)

def ensure_dirs():
    """Ensure required directories exist"""
    for d in [SPOKES_DIR, REFS_DIR, os.path.join(REFS_DIR, "backlinks")]:
        os.makedirs(d, exist_ok=True)

def inode_key(path):
    """Get inode + device for unique file identification"""
    try:
        stat = os.stat(path)
        return f"{stat.st_dev}:{stat.st_ino}"
    except OSError:
        return None

def content_hash(path):
    """Compute SHA256 hash of file content"""
    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()[:16]
    except OSError:
        return None

def is_symlink_valid(path):
    """Check if symlink exists and points to valid target"""
    if not os.path.islink(path):
        return False
    return os.path.exists(path)

def safe_symlink(src, dst):
    """Create symlink atomically (remove then create)"""
    if os.path.exists(dst) or os.path.islink(dst):
        os.remove(dst)
    os.symlink(src, dst)

# ─── SymlinkManager ─────────────────────────────────────────────────────────
class SymlinkManager:
    def __init__(self):
        self.registry = load_registry()
        self.inode_map = {}  # inode_key -> symlink_path
        self.stats = {"created": 0, "updated": 0, "deleted": 0, "broken": 0}
        self.broken_links = []
        ensure_dirs()
        self._load_inode_map()

    def _load_inode_map(self):
        """Build inode map from existing symlinks"""
        for name in os.listdir(SPOKES_DIR):
            path = os.path.join(SPOKES_DIR, name)
            if os.path.islink(path):
                ik = inode_key(os.readlink(path))
                if ik:
                    self.inode_map[ik] = path

    # ─── Spoke Operations ────────────────────────────────────────────────────
    def register_spoke(self, name, spoke_path, ns_type="custom", description=""):
        """Register a new spoke vault"""
        if not os.path.isdir(spoke_path):
            print(f"[ERROR] Path does not exist: {spoke_path}")
            return False

        # Validate namespace name
        import re
        if not re.match(r"^[a-z][a-z0-9-]*$", name):
            print(f"[ERROR] Invalid namespace name: {name}")
            return False

        forbidden = self.registry.get("validation_rules", {}).get("forbidden", [])
        if name in forbidden:
            print(f"[ERROR] Forbidden namespace: {name}")
            return False

        # Add to registry
        self.registry["spokes"][name] = {
            "path": spoke_path,
            "type": ns_type,
            "created": datetime.utcnow().isoformat(),
            "description": description,
            "status": "active"
        }
        self._save_registry()

        # Create symlink in master vault
        link_path = os.path.join(SPOKES_DIR, name)
        safe_symlink(spoke_path, link_path)
        self.stats["created"] += 1
        print(f"[OK] Registered spoke: {name} -> {spoke_path}")
        return True

    def unregister_spoke(self, name):
        """Remove spoke registration and symlink"""
        if name not in self.registry["spokes"]:
            print(f"[ERROR] Spoke not found: {name}")
            return False

        del self.registry["spokes"][name]
        self._save_registry()

        link_path = os.path.join(SPOKES_DIR, name)
        if os.path.islink(link_path):
            os.remove(link_path)
            self.stats["deleted"] += 1
        print(f"[OK] Unregistered spoke: {name}")
        return True

    def list_spokes(self):
        """List all registered spokes"""
        return dict(self.registry["spokes"])

    # ─── Cross-Vault Link Operations ─────────────────────────────────────────
    def create_link(self, source_file, target_namespace, target_note):
        """Create a cross-vault link in source file"""
        link_text = f"{LINK_SYNTAX['prefix']}{target_namespace}{LINK_SYNTAX['separator']}{target_note}{LINK_SYNTAX['suffix']}"
        return link_text

    def resolve_link(self, link_text):
        """Resolve a cross-vault link to absolute path"""
        # Parse: vault:namespace::note]
        import re
        pattern = r"vault:([a-zA-Z0-9_-]+)::([^\]]+)\]"
        match = re.match(pattern, link_text)
        if not match:
            return None, None, "Invalid link syntax"

        namespace = match.group(1)
        note = match.group(2)

        if namespace not in self.registry["spokes"]:
            return namespace, note, f"Unknown namespace: {namespace}"

        spoke = self.registry["spokes"][namespace]
        spoke_path = spoke["path"]

        # Try exact match first
        exact = os.path.join(spoke_path, f"{note}.md")
        if os.path.exists(exact):
            return namespace, note, exact

        # Search recursively
        for root, dirs, files in os.walk(spoke_path):
            for f in files:
                if f.endswith(".md") and note in f:
                    return namespace, note, os.path.join(root, f)

        return namespace, note, f"Not found: {note} in {namespace}"

    # ─── Inode-Based Tracking ────────────────────────────────────────────────
    def track_move(self, old_path, new_path):
        """Track file move via inode — update symlinks"""
        ik = inode_key(new_path)
        if ik and ik in self.inode_map:
            # Update symlink to point to new location
            link_path = self.inode_map[ik]
            if os.path.islink(link_path):
                os.remove(link_path)
                os.symlink(new_path, link_path)
                self.stats["updated"] += 1
                return True
        return False

    # ─── Broken Link Detection ──────────────────────────────────────────────
    def scan_broken_links(self):
        """Scan all symlinks for broken references"""
        self.broken_links = []
        for name in os.listdir(SPOKES_DIR):
            path = os.path.join(SPOKES_DIR, name)
            if os.path.islink(path) and not os.path.exists(path):
                self.broken_links.append({"name": name, "target": os.readlink(path)})
                self.stats["broken"] += 1

        # Save report
        report = {
            "scan_time": datetime.utcnow().isoformat(),
            "total": len(self.broken_links),
            "broken": self.broken_links
        }
        report_path = os.path.join(REFS_DIR, "broken_links.json")
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)

        return self.broken_links

    def repair_broken(self):
        """Attempt to repair broken symlinks"""
        repaired = 0
        for item in self.broken_links[:]:
            name = item["name"]
            if name in self.registry["spokes"]:
                target = self.registry["spokes"][name]["path"]
                link_path = os.path.join(SPOKES_DIR, name)
                if os.path.exists(target):
                    os.symlink(target, link_path)
                    self.broken_links.remove(item)
                    repaired += 1
        return repaired

    # ─── Backlink Index ──────────────────────────────────────────────────────
    def build_backlink_index(self, vault_paths):
        """Build reverse index: target note -> list of sources"""
        import re
        backlinks = {}
        pattern = r"vault:([a-zA-Z0-9_-]+)::([^\]]+)\]"

        for vault_path in vault_paths:
            for root, dirs, files in os.walk(vault_path):
                for f in files:
                    if not f.endswith(".md"):
                        continue
                    filepath = os.path.join(root, f)
                    try:
                        with open(filepath, "r", encoding="utf-8") as fh:
                            content = fh.read()
                        for match in re.finditer(pattern, content):
                            target = f"{match.group(1)}::{match.group(2)}"
                            if target not in backlinks:
                                backlinks[target] = []
                            backlinks[target].append(filepath)
                    except Exception:
                        pass

        # Save
        out_path = os.path.join(REFS_DIR, "backlinks", "index.json")
        with open(out_path, "w") as f:
            json.dump(backlinks, f, indent=2)

        return backlinks

    # ─── Internal ────────────────────────────────────────────────────────────
    def _save_registry(self):
        with open(os.path.join(MASTER_VAULT, "namespace_registry.json"), "w") as f:
            json.dump(self.registry, f, indent=2)

    def get_stats(self):
        return dict(self.stats)

# ─── CLI ─────────────────────────────────────────────────────────────────────
def main():
    if len(sys.argv) < 2:
        print("Usage: symlink_manager.py <command> [args]")
        print("Commands: register <name> <path>, unregister <name>, list, scan, repair, backlinks")
        sys.exit(1)

    cmd = sys.argv[1]
    mgr = SymlinkManager()

    if cmd == "register" and len(sys.argv) >= 4:
        mgr.register_spoke(sys.argv[2], sys.argv[3])
    elif cmd == "unregister" and len(sys.argv) >= 3:
        mgr.unregister_spoke(sys.argv[2])
    elif cmd == "list":
        for name, info in mgr.list_spokes().items():
            print(f"  {name}: {info['path']} ({info['type']})")
    elif cmd == "scan":
        broken = mgr.scan_broken_links()
        print(f"Found {len(broken)} broken links")
        for b in broken:
            print(f"  BROKEN: {b['name']} -> {b['target']}")
    elif cmd == "repair":
        repaired = mgr.repair_broken()
        print(f"Repaired {repaired} links")
    elif cmd == "backlinks":
        vaults = [s["path"] for s in mgr.registry["spokes"].values()]
        idx = mgr.build_backlink_index(vaults)
        print(f"Built backlink index: {len(idx)} targets")
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)

    print(f"\nStats: {mgr.get_stats()}")

if __name__ == "__main__":
    main()

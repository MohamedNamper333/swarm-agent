#!/usr/bin/env python3
"""
AL-MUKH Namespace Resolver v1.0
Maps file paths to namespaces, validates spoke names, and resolves cross-vault references
"""
import os
import sys
import json
import re
from pathlib import Path
from datetime import datetime

# ─── Configuration ───────────────────────────────────────────────────────────
MASTER_VAULT = "/home/kali/AL-MUKH"
SPOKES_DIR = os.path.join(MASTER_VAULT, "spokes")
REGISTRY_PATH = os.path.join(MASTER_VAULT, "namespace_registry.json")

RESERVED_NAMES = {
    "system", "temp", "tmp", "cache", "logs",
    "spokes", "index", "refs", "search", "config"
}

MAX_NS_LENGTH = 64
NS_PATTERN = re.compile(r"^[a-z][a-z0-9-]*$")

# ─── NamespaceResolver ──────────────────────────────────────────────────────
class NamespaceResolver:
    def __init__(self):
        self.registry = self._load_registry()
        self.path_cache = {}  # cached path -> namespace lookups

    def _load_registry(self):
        if os.path.exists(REGISTRY_PATH):
            with open(REGISTRY_PATH, "r") as f:
                return json.load(f)
        return {"version": 1, "reserved_prefixes": [], "spokes": {}}

    def _save_registry(self):
        with open(REGISTRY_PATH, "w") as f:
            json.dump(self.registry, f, indent=2)

    # ─── Path → Namespace ────────────────────────────────────────────────────
    def resolve(self, file_path):
        """Resolve a file path to its namespace"""
        file_path = os.path.abspath(file_path)

        # Check cache
        if file_path in self.path_cache:
            return self.path_cache[file_path]

        # Check each spoke
        for name, spoke in self.registry.get("spokes", {}).items():
            spoke_path = os.path.abspath(spoke["path"])
            if file_path.startswith(spoke_path):
                rel = os.path.relpath(file_path, spoke_path)
                parts = Path(rel).parts

                # Direct spoke root
                if len(parts) == 1:
                    ns = name
                else:
                    # Check if first directory matches namespace
                    first_dir = parts[0]
                    if first_dir == name:
                        ns = name
                    else:
                        ns = first_dir

                self.path_cache[file_path] = ns
                return ns

        # Check if file is inside master vault
        master = os.path.abspath(MASTER_VAULT)
        if file_path.startswith(master):
            rel = os.path.relpath(file_path, master)
            parts = Path(rel).parts
            if parts:
                return parts[0]

        return "unknown"

    # ─── Namespace → Path ────────────────────────────────────────────────────
    def ns_to_path(self, namespace):
        """Get the absolute path for a namespace"""
        if namespace in self.registry.get("spokes", {}):
            return self.registry["spokes"][namespace]["path"]

        # Check if it's a master vault subdirectory
        candidate = os.path.join(MASTER_VAULT, namespace)
        if os.path.isdir(candidate):
            return candidate

        return None

    # ─── Validation ──────────────────────────────────────────────────────────
    def validate_name(self, name):
        """Validate a namespace name"""
        errors = []

        if not name:
            errors.append("Name cannot be empty")
        elif len(name) > MAX_NS_LENGTH:
            errors.append(f"Name too long (max {MAX_NS_LENGTH})")
        elif not NS_PATTERN.match(name):
            errors.append("Must start with lowercase letter, only [a-z0-9-]")
        elif name in RESERVED_NAMES:
            errors.append(f"Reserved name: {name}")

        # Check for duplicates
        if name in self.registry.get("spokes", {}):
            errors.append(f"Namespace already exists: {name}")

        return {"valid": len(errors) == 0, "errors": errors}

    def suggest_name(self, raw_name):
        """Suggest a valid namespace name from raw input"""
        name = raw_name.lower().strip()
        name = re.sub(r"[^a-z0-9-]", "-", name)
        name = re.sub(r"-+", "-", name)
        name = name.strip("-")

        if not name:
            name = "unnamed"

        if name[0].isdigit():
            name = "ns-" + name

        # Ensure uniqueness
        base = name
        counter = 1
        while name in self.registry.get("spokes", {}) or name in RESERVED_NAMES:
            name = f"{base}-{counter}"
            counter += 1

        return name

    # ─── Discovery ───────────────────────────────────────────────────────────
    def discover_spokes(self, search_paths):
        """Auto-discover potential spoke vaults"""
        discovered = []
        for root in search_paths:
            if not os.path.isdir(root):
                continue
            for entry in os.listdir(root):
                entry_path = os.path.join(root, entry)
                if not os.path.isdir(entry_path):
                    continue

                # Check if it matches namespace patterns
                name = entry.lower()
                if NS_PATTERN.match(name) and name not in RESERVED_NAMES:
                    # Check if it has .obsidian (Obsidian vault marker)
                    has_obsidian = os.path.isdir(os.path.join(entry_path, ".obsidian"))
                    discovered.append({
                        "name": name,
                        "path": entry_path,
                        "has_obsidian": has_obsidian,
                        "already_registered": name in self.registry.get("spokes", {})
                    })

        return discovered

    # ─── Cross-Vault Reference Resolution ────────────────────────────────────
    def parse_link(self, link_text):
        """Parse vault link syntax: vault:namespace::note"""
        match = re.match(r"vault:([a-zA-Z0-9_-]+)::([^\]]+)", link_text)
        if match:
            return {"namespace": match.group(1), "note": match.group(2)}
        return None

    def resolve_link(self, link_text):
        """Resolve a vault link to absolute file path"""
        parsed = self.parse_link(link_text)
        if not parsed:
            return None, "Invalid link syntax"

        ns = parsed["namespace"]
        note = parsed["note"]

        ns_path = self.ns_to_path(ns)
        if not ns_path:
            return None, f"Unknown namespace: {ns}"

        # Try exact match
        exact = os.path.join(ns_path, f"{note}.md")
        if os.path.exists(exact):
            return exact, None

        # Search recursively
        for root, dirs, files in os.walk(ns_path):
            for f in files:
                if f.endswith(".md") and note in f:
                    return os.path.join(root, f), None

        return None, f"Note not found: {note} in {ns}"

    def find_references(self, note_name, vault_paths):
        """Find all files that reference a given note"""
        refs = []
        pattern = re.compile(rf"vault:[a-zA-Z0-9_-]+::{re.escape(note_name)}\]")

        for vault_path in vault_paths:
            for root, dirs, files in os.walk(vault_path):
                for f in files:
                    if not f.endswith(".md"):
                        continue
                    filepath = os.path.join(root, f)
                    try:
                        with open(filepath, "r", encoding="utf-8") as fh:
                            if pattern.search(fh.read()):
                                refs.append(filepath)
                    except Exception:
                        pass

        return refs

    # ─── Statistics ──────────────────────────────────────────────────────────
    def get_stats(self):
        spokes = self.registry.get("spokes", {})
        total_files = 0
        total_size = 0

        for name, spoke in spokes.items():
            spoke_path = spoke["path"]
            if os.path.isdir(spoke_path):
                for root, dirs, files in os.walk(spoke_path):
                    for f in files:
                        if f.endswith(".md"):
                            total_files += 1
                            try:
                                total_size += os.path.getsize(os.path.join(root, f))
                            except OSError:
                                pass

        return {
            "namespaces": len(spokes),
            "total_md_files": total_files,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "registered": list(spokes.keys())
        }

    def clear_cache(self):
        self.path_cache.clear()

# ─── CLI ─────────────────────────────────────────────────────────────────────
def main():
    if len(sys.argv) < 2:
        print("Usage: namespace_resolver.py <command> [args]")
        print("Commands: resolve <path>, validate <name>, suggest <name>, discover, stats, parse <link>")
        sys.exit(1)

    cmd = sys.argv[1]
    resolver = NamespaceResolver()

    if cmd == "resolve" and len(sys.argv) >= 3:
        ns = resolver.resolve(sys.argv[2])
        print(f"Namespace: {ns}")

    elif cmd == "validate" and len(sys.argv) >= 3:
        result = resolver.validate_name(sys.argv[2])
        print(json.dumps(result, indent=2))

    elif cmd == "suggest" and len(sys.argv) >= 3:
        name = resolver.suggest_name(sys.argv[2])
        print(f"Suggested: {name}")

    elif cmd == "discover":
        paths = ["/home/kali/Documents/Obsidian Vault"]
        found = resolver.discover_spokes(paths)
        for sp in found:
            status = "registered" if sp["already_registered"] else "new"
            marker = "[OBS]" if sp["has_obsidian"] else ""
            print(f"  {sp['name']}: {sp['path']} ({status}) {marker}")

    elif cmd == "stats":
        stats = resolver.get_stats()
        print(json.dumps(stats, indent=2))

    elif cmd == "parse" and len(sys.argv) >= 3:
        parsed = resolver.parse_link(sys.argv[2])
        print(json.dumps(parsed, indent=2) if parsed else "Invalid link")

    elif cmd == "resolve-link" and len(sys.argv) >= 3:
        path, err = resolver.resolve_link(sys.argv[2])
        if err:
            print(f"Error: {err}")
        else:
            print(f"Resolved: {path}")

    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)

if __name__ == "__main__":
    main()

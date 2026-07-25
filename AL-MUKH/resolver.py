#!/usr/bin/env python3
"""AL-MUKH Cross-Vault Link Resolver v1.0

Resolve [[vault:namespace::note]] links across multiple Obsidian vaults.

Usage:
    python resolver.py resolve "vault:proj-swarm::README"
    python resolver.py scan
    python resolver.py broken
    python resolver.py suggest <name>
"""

import argparse
import difflib
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

SPOKE_ROOTS = [
    Path("/home/kali/AL-MUKH"),
    Path("/home/kali/Documents/Obsidian Vault"),
]

LINK_RE = re.compile(
    r"\[\[vault:([a-zA-Z0-9_-]+)::([^\]|]+)(?:\|[^\]]+)?\]\]"
)

BACKLINK_PATH = Path("/home/kali/AL-MUKH/refs/backlinks.json")


def _md_files():
    """Yield every .md file across all spoke roots."""
    for root in SPOKE_ROOTS:
        if not root.is_dir():
            continue
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                if fn.endswith(".md"):
                    yield Path(dirpath) / fn


def _note_stem(path: Path) -> str:
    return path.stem


def _build_note_index():
    """Map lowercased note name → list of absolute paths."""
    idx = defaultdict(list)
    for p in _md_files():
        idx[_note_stem(p).lower()].append(p)
    return idx


def resolve_link(raw: str) -> dict:
    """Resolve a single [[vault:ns::note]] link string.

    Returns:
        {"resolved": True, "path": "/abs/path", "namespace": "ns"}
        or {"resolved": False, "suggestions": [...], "namespace": "ns"}
    """
    m = LINK_RE.search(raw)
    if not m:
        return {"resolved": False, "error": "unrecognised link syntax", "input": raw}

    namespace = m.group(1)
    note_name = m.group(2).strip()
    idx = _build_note_index()
    key = note_name.lower()

    if key in idx:
        paths = idx[key]
        if len(paths) == 1:
            return {"resolved": True, "path": str(paths[0]), "namespace": namespace}
        return {
            "resolved": True,
            "path": str(paths[0]),
            "namespace": namespace,
            "ambiguous": [str(p) for p in paths],
        }

    candidates = list(idx.keys())
    suggestions = difflib.get_close_matches(key, candidates, n=5, cutoff=0.4)
    return {
        "resolved": False,
        "suggestions": [
            {"name": s, "paths": [str(p) for p in idx[s]]} for s in suggestions
        ],
        "namespace": namespace,
    }


def cmd_resolve(args):
    raw = args.link
    result = resolve_link(raw)
    print(json.dumps(result, indent=2))
    return 0 if result.get("resolved") else 1


def cmd_scan(args):
    """Scan all .md files, parse links, build backlink index."""
    backlinks = defaultdict(list)
    all_links = []
    broken = []

    for md in _md_files():
        try:
            text = md.read_text(errors="replace")
        except OSError:
            continue

        for m in LINK_RE.finditer(text):
            namespace = m.group(1)
            note_name = m.group(2).strip()
            all_links.append(
                {"source": str(md), "namespace": namespace, "target": note_name}
            )

            # resolve target → update backlinks
            resolved = resolve_link(
                f"[[vault:{namespace}::{note_name}]]"
            )
            if resolved["resolved"]:
                target_path = resolved["path"]
                backlinks[target_path].append(
                    {"source": str(md), "namespace": namespace, "target": note_name}
                )
            else:
                broken.append(
                    {
                        "source": str(md),
                        "namespace": namespace,
                        "target": note_name,
                        "suggestions": resolved.get("suggestions", []),
                    }
                )

    BACKLINK_PATH.parent.mkdir(parents=True, exist_ok=True)
    BACKLINK_PATH.write_text(
        json.dumps(dict(backlinks), indent=2, ensure_ascii=False) + "\n"
    )

    summary = {
        "total_links": len(all_links),
        "total_backlinks": len(backlinks),
        "broken": len(broken),
        "backlink_index": str(BACKLINK_PATH),
    }
    print(json.dumps(summary, indent=2))
    if broken:
        print("\n--- broken links ---")
        print(json.dumps(broken, indent=2, ensure_ascii=False))
    return 1 if broken else 0


def cmd_broken(args):
    """List broken links from current scan or rescan."""
    broken = []
    for md in _md_files():
        try:
            text = md.read_text(errors="replace")
        except OSError:
            continue

        for m in LINK_RE.finditer(text):
            namespace = m.group(1)
            note_name = m.group(2).strip()
            resolved = resolve_link(f"[[vault:{namespace}::{note_name}]]")
            if not resolved["resolved"]:
                broken.append(
                    {
                        "source": str(md),
                        "namespace": namespace,
                        "target": note_name,
                        "suggestions": resolved.get("suggestions", []),
                    }
                )

    if broken:
        print(json.dumps(broken, indent=2, ensure_ascii=False))
    else:
        print('{"message": "No broken links found."}')
    return 1 if broken else 0


def cmd_suggest(args):
    """Suggest similar notes for a given name."""
    idx = _build_note_index()
    candidates = list(idx.keys())
    matches = difflib.get_close_matches(args.name.lower(), candidates, n=10, cutoff=0.3)
    if matches:
        results = [
            {"name": m, "paths": [str(p) for p in idx[m]]} for m in matches
        ]
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        print(json.dumps({"message": f"No similar notes found for '{args.name}'."}))
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="AL-MUKH Cross-Vault Link Resolver v1.0"
    )
    sub = parser.add_subparsers(dest="command")

    p_resolve = sub.add_parser("resolve", help="Resolve a single link")
    p_resolve.add_argument("link", help="Link in [[vault:ns::note]] format")

    sub.add_parser("scan", help="Scan all files, build backlink index")
    sub.add_parser("broken", help="List broken links")

    p_suggest = sub.add_parser("suggest", help="Suggest similar notes")
    p_suggest.add_argument("name", help="Note name to match against")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 1

    handlers = {
        "resolve": cmd_resolve,
        "scan": cmd_scan,
        "broken": cmd_broken,
        "suggest": cmd_suggest,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())

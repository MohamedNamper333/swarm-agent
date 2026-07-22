#!/usr/bin/env python3
"""Standalone Obsidian Vault REST Server v2.1 - full MCP obsidian-mcp-server v3.2.9 compatibility."""

import os, json, re, urllib.parse, logging, yaml
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from datetime import datetime, date

VAULT_PATH = Path("/home/kali/Documents/Obsidian Vault")
API_KEY = os.environ.get("VAULT_API_KEY", "swarm-evolution-2025")
PORT = int(os.environ.get("VAULT_PORT", 27123))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("vault")


def extract_tags(content):
    return sorted(set(m.group(1) for m in re.finditer(r'(?:^|\s)#([a-zA-Z][\w\-/]*)', content)))


def extract_frontmatter(content):
    if not content.startswith("---"):
        return {}
    end = content.find("---", 3)
    if end == -1:
        return {}
    try:
        return yaml.safe_load(content[3:end]) or {}
    except Exception:
        fm = {}
        for line in content[3:end].strip().split("\n"):
            if ":" in line:
                k, v = line.split(":", 1)
                fm[k.strip()] = v.strip().strip('"').strip("'")
        return fm


def parse_periodic_path(path):
    """Parse /periodic/{period}/[{YYYY}/{MM}/{DD}/] and return (period, date_str or None)."""
    m = re.match(r'^/periodic/(daily|weekly|monthly|quarterly|yearly)/?$', path)
    if m:
        return m.group(1), None
    m = re.match(r'^/periodic/(daily|weekly|monthly|quarterly|yearly)/(\d{4})/(\d{2})/(\d{2})/?$', path)
    if m:
        return m.group(1), f"{m.group(2)}-{m.group(3)}-{m.group(4)}"
    return None, None


class VaultHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        log.info(fmt % args)

    def _check_auth(self):
        return self.headers.get("Authorization", "") == f"Bearer {API_KEY}"

    def _json(self, code, data):
        body = json.dumps(data, ensure_ascii=False, default=str).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _text(self, code, text):
        body = text.encode() if isinstance(text, str) else text
        self.send_response(code)
        self.send_header("Content-Type", "text/markdown; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        return self.rfile.read(length).decode("utf-8", errors="replace") if length else ""

    def _vault_files(self, dir_path=""):
        base = VAULT_PATH / dir_path if dir_path else VAULT_PATH
        files = []
        for f in sorted(base.iterdir()):
            if f.name == "vault_server.py" or f.name == ".obsidian":
                continue
            if f.is_file():
                s = f.stat()
                files.append({"path": str(f.relative_to(VAULT_PATH)), "basename": f.name,
                              "type": "file", "size": s.st_size, "ctime": int(s.st_ctime * 1000),
                              "mtime": int(s.st_mtime * 1000)})
            elif f.is_dir():
                s = f.stat()
                files.append({"path": str(f.relative_to(VAULT_PATH)) + "/",
                              "basename": f.name, "type": "directory", "size": 0,
                              "ctime": int(s.st_ctime * 1000),
                              "mtime": int(s.st_mtime * 1000)})
        return files

    def _all_tags(self):
        counts = {}
        for f in VAULT_PATH.rglob("*.md"):
            if ".obsidian" in str(f):
                continue
            try:
                for t in extract_tags(f.read_text(errors="replace")):
                    counts[t] = counts.get(t, 0) + 1
            except Exception:
                pass
        return [{"name": t, "count": c} for t, c in sorted(counts.items())]

    def _search(self, query, context_length=100, mcp_format=False):
        results = []
        q = query.lower()
        for f in VAULT_PATH.rglob("*.md"):
            if ".obsidian" in str(f):
                continue
            try:
                content = f.read_text(errors="replace")
            except Exception:
                continue
            if q in content.lower():
                rel = str(f.relative_to(VAULT_PATH))
                lines = content.split("\n")
                matches = []
                for i, line in enumerate(lines):
                    if q in line.lower():
                        start = max(0, i - 1)
                        end = min(len(lines), i + 2)
                        ctx = "\n".join(lines[start:end])
                        if len(ctx) > context_length:
                            idx = ctx.lower().find(q)
                            s = max(0, idx - context_length // 2)
                            ctx = ctx[s:s + context_length]
                        if mcp_format:
                            matches.append({"match": {"filename": f.name, "path": rel, "line": i + 1, "text": line.strip(), "context": ctx}})
                        else:
                            matches.append({"line": i + 1, "text": line.strip(), "context": ctx})
                if mcp_format:
                    results.append({"matches": matches})
                else:
                    results.append({"filename": f.name, "path": rel, "matches": matches, "score": len(matches)})
        results.sort(key=lambda x: x.get("score", len(x.get("matches", []))), reverse=True)
        if mcp_format:
            return {"hits": results}
        return results

    def _resolve_note_content(self, full_path, accept="text/markdown"):
        """Return note content in the requested format."""
        if not full_path.exists():
            return None
        content = full_path.read_text(errors="replace")
        rel = str(full_path.relative_to(VAULT_PATH))

        if "application/vnd.olrapi.note+json" in accept:
            return {"path": rel, "content": content, "size": len(content),
                    "frontmatter": extract_frontmatter(content), "tags": extract_tags(content),
                    "stat": {"size": len(content), "ctime": int(full_path.stat().st_ctime * 1000),
                             "mtime": int(full_path.stat().st_mtime * 1000)}}
        return content

    def _find_periodic_note(self, period, date_str=None):
        """Find a periodic note by convention. Tries common naming patterns."""
        if date_str:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
        else:
            dt = datetime.now()

        patterns = {
            "daily": [dt.strftime("%Y-%m-%d"), dt.strftime("%Y/%m-%d"), dt.strftime("%Y/%m/%Y-%m-%d")],
            "weekly": [f"{dt.isocalendar()[0]}-W{dt.isocalendar()[1]:02d}", dt.strftime("%Y-W%V")],
            "monthly": [dt.strftime("%Y-%m"), dt.strftime("%Y/%m")],
            "quarterly": [f"{dt.year}-Q{(dt.month - 1) // 3 + 1}"],
            "yearly": [str(dt.year)],
        }

        for name_pattern in patterns.get(period, []):
            # Search in common periodic note locations
            for search_dir in [VAULT_PATH / "daily", VAULT_PATH / "Daily",
                               VAULT_PATH / "periodic", VAULT_PATH / "Periodic Notes",
                               VAULT_PATH / "journal", VAULT_PATH / "Journal", VAULT_PATH]:
                for f in search_dir.rglob("*.md"):
                    if ".obsidian" in str(f):
                        continue
                    stem = f.stem.lower()
                    if name_pattern.lower() in stem:
                        return f
        return None

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, PUT, POST, DELETE, PATCH, OPTIONS, HEAD")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type, Accept")
        self.end_headers()

    def do_HEAD(self):
        parsed = urllib.parse.urlparse(self.path)
        path = urllib.parse.unquote(parsed.path)

        if not self._check_auth():
            self.send_response(401)
            self.end_headers()
            return

        if path.startswith("/vault/"):
            rel = path[len("/vault/"):].rstrip("/")
            full = VAULT_PATH / rel
            if full.exists() and full.is_file():
                size = full.stat().st_size
                self.send_response(200)
                self.send_header("Content-Type", "text/markdown")
                self.send_header("Content-Length", str(size))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                return
            self.send_response(404)
            self.end_headers()
            return

        self.send_response(404)
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = urllib.parse.unquote(parsed.path)
        qs = urllib.parse.parse_qs(parsed.query)
        accept = self.headers.get("Accept", "text/markdown")

        # Root
        if path == "/":
            return self._json(200, {"status": "OK", "service": "Vault REST Server",
                "version": "2.1", "endpoints": [
                    "/vault/", "/vault/{path}", "/tags/", "/commands/",
                    "/search/", "/search/simple/", "/open/{path}",
                    "/active/", "/periodic/{period}/", "/periodic/{period}/{YYYY}/{MM}/{DD}/"]})

        # Health
        if path == "/health":
            return self._json(200, {"status": "healthy"})

        # Active file (stub — no Obsidian running)
        if path in ("/active/", "/active"):
            return self._json(404, {"error": "No active file — Obsidian is not running", "reason": "no_active_file"})

        # Periodic notes
        if path.startswith("/periodic/"):
            period, date_str = parse_periodic_path(path)
            if not period:
                return self._json(400, {"error": f"Invalid periodic path: {path}"})
            note = self._find_periodic_note(period, date_str)
            if note:
                content = note.read_text(errors="replace")
                return self._json(200, {"path": str(note.relative_to(VAULT_PATH)),
                    "content": content, "period": period, "date": date_str})
            period_label = f"{period} note"
            if date_str:
                period_label += f" for {date_str}"
            return self._json(404, {"error": f"No {period_label} found", "reason": "periodic_not_found"})

        if not self._check_auth():
            return self._json(401, {"error": "Unauthorized"})

        # List vault root
        if path in ("/vault/", "/vault"):
            files = self._vault_files()
            return self._json(200, {"files": files})

        # Read file / list directory
        if path.startswith("/vault/"):
            rel = path[len("/vault/"):].rstrip("/")
            full = VAULT_PATH / rel if rel else VAULT_PATH
            if not full.exists():
                return self._json(404, {"error": f"Not found: {rel}", "reason": "note_missing"})
            if full.is_dir():
                return self._json(200, {"files": self._vault_files(rel)})
            # Note JSON format
            if "application/vnd.olrapi.note+json" in accept:
                return self._json(200, self._resolve_note_content(full, accept))
            # Document map format (simplified)
            if "application/vnd.olrapi.document-map+json" in accept:
                content = full.read_text(errors="replace")
                headings = [{"level": len(m.group(1)), "text": m.group(2), "line": i + 1}
                            for i, line in enumerate(content.split("\n"))
                            for m in [re.match(r'^(#{1,6})\s+(.+)$', line)] if m]
                return self._json(200, {"path": rel, "headings": headings})
            # Default: markdown
            content = full.read_text(errors="replace")
            return self._text(200, content)

        # Tags
        if path in ("/tags/", "/tags"):
            return self._json(200, {"tags": self._all_tags()})

        # Commands
        if path in ("/commands/", "/commands"):
            cmds = [{"id": "app:go-back", "name": "Go back"}, {"id": "app:go-forward", "name": "Go forward"},
                     {"id": "editor:toggle-bold", "name": "Toggle bold"}, {"id": "editor:toggle-italics", "name": "Toggle italics"},
                     {"id": "editor:insert-link", "name": "Insert link"}, {"id": "editor:delete-paragraph", "name": "Delete paragraph"},
                     {"id": "file-explorer:open", "name": "Open file explorer"}, {"id": "switcher:open", "name": "Quick switcher"},
                     {"id": "tag-pane:open", "name": "Open tag pane"}, {"id": "graph:open", "name": "Open graph view"},
                     {"id": "daily-notes", "name": "Open daily note"}]
            return self._json(200, {"commands": cmds})

        # Search GET
        if path in ("/search/", "/search"):
            q = qs.get("query", qs.get("q", [""]))[0]
            if not q:
                return self._json(400, {"error": "Missing ?query="})
            results = self._search(q, mcp_format=True)
            return self._json(200, results)

        # Simple Search GET
        if path in ("/search/simple/", "/search/simple"):
            q = qs.get("query", qs.get("q", [""]))[0]
            cl = int(qs.get("contextLength", [100])[0])
            if not q:
                return self._json(400, {"error": "Missing ?query="})
            results = self._search(q, cl, mcp_format=True)
            return self._json(200, results)

        # Open
        if path.startswith("/open/"):
            rel = path[len("/open/"):]
            full = VAULT_PATH / urllib.parse.unquote(rel)
            if full.exists():
                return self._json(200, {"status": "opened", "path": rel})
            return self._json(404, {"error": f"Not found: {rel}"})

        self._json(404, {"error": "Not found"})

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = urllib.parse.unquote(parsed.path)
        qs = urllib.parse.parse_qs(parsed.query)
        body = self._read_body()
        content_type = self.headers.get("Content-Type", "")

        if not self._check_auth():
            return self._json(401, {"error": "Unauthorized"})

        # Simple search POST — MCP sends query params: /search/simple/?query=X&contextLength=Y
        if path in ("/search/simple/", "/search/simple"):
            q = qs.get("query", qs.get("q", [""]))[0]
            cl = int(qs.get("contextLength", [100])[0])
            if not q and body:
                try:
                    d = json.loads(body)
                    q = d.get("query", d.get("q", ""))
                except Exception:
                    pass
            if not q:
                return self._json(400, {"error": "Missing query"})
            return self._json(200, self._search(q, cl, mcp_format=True))

        # Advanced search POST (JSON Logic)
        if path in ("/search/", "/search"):
            q = ""
            if body:
                try:
                    d = json.loads(body)
                    # JSON Logic format — extract query if present
                    if "and" in d:
                        for clause in d.get("and", []):
                            if isinstance(clause, dict) and "in" in clause:
                                val = clause["in"]
                                if isinstance(val, list) and len(val) >= 2:
                                    q = val[0]
                    elif "or" in d:
                        for clause in d.get("or", []):
                            if isinstance(clause, dict) and "in" in clause:
                                val = clause["in"]
                                if isinstance(val, list) and len(val) >= 2:
                                    q = val[0]
                    else:
                        q = d.get("query", d.get("q", str(d)))
                except Exception:
                    q = body
            if not q:
                q = qs.get("query", qs.get("q", [""]))[0]
            if not q:
                return self._json(400, {"error": "Missing query"})
            return self._json(200, self._search(q, mcp_format=True))

        # Execute command
        if path.startswith("/commands/"):
            cid = path[len("/commands/"):].rstrip("/")
            return self._json(200, {"status": "executed", "command": cid})

        # Open in UI (POST)
        if path.startswith("/open/"):
            rel = path[len("/open/"):]
            full = VAULT_PATH / urllib.parse.unquote(rel)
            if full.exists():
                return self._json(200, {"status": "opened", "path": rel})
            return self._json(404, {"error": f"Not found: {rel}"})

        # Append to note (POST /vault/{path})
        if path.startswith("/vault/"):
            rel = path[len("/vault/"):].rstrip("/")
            if not rel:
                return self._json(400, {"error": "Missing path"})
            full = VAULT_PATH / rel
            if not full.exists():
                return self._json(404, {"error": f"Not found: {rel}", "reason": "note_missing"})
            existing = full.read_text(errors="replace")
            full.write_text(existing + "\n" + body, encoding="utf-8")
            return self._json(200, {"status": "OK", "path": rel})

        self._json(404, {"error": "Not found"})

    def do_PUT(self):
        parsed = urllib.parse.urlparse(self.path)
        path = urllib.parse.unquote(parsed.path)

        if not self._check_auth():
            return self._json(401, {"error": "Unauthorized"})

        if path.startswith("/vault/"):
            rel = path[len("/vault/"):].rstrip("/")
            if not rel:
                return self._json(400, {"error": "Missing path"})
            full = VAULT_PATH / rel
            full.parent.mkdir(parents=True, exist_ok=True)
            full.write_text(self._read_body(), encoding="utf-8")
            return self._json(200, {"status": "OK", "path": rel})
        self._json(404, {"error": "Not found"})

    def do_PATCH(self):
        parsed = urllib.parse.urlparse(self.path)
        path = urllib.parse.unquote(parsed.path)

        if not self._check_auth():
            return self._json(401, {"error": "Unauthorized"})

        if path.startswith("/vault/"):
            rel = path[len("/vault/"):].rstrip("/")
            if not rel:
                return self._json(400, {"error": "Missing path"})
            full = VAULT_PATH / rel
            if not full.exists():
                return self._json(404, {"error": f"Not found: {rel}", "reason": "note_missing"})

            operation = self.headers.get("Operation", "append")
            target_type = self.headers.get("Target-Type", "")
            target = urllib.parse.unquote(self.headers.get("Target", ""))
            content = self._read_body()

            existing = full.read_text(errors="replace")

            if operation == "replace" and target:
                if target_type == "heading":
                    # Replace section under heading
                    pattern = rf'(^##?\s+{re.escape(target)}.*?)(?=\n##?\s|\Z)'
                    match = re.search(pattern, existing, re.DOTALL | re.MULTILINE)
                    if match:
                        existing = existing[:match.start()] + content + existing[match.end():]
                    else:
                        existing += f"\n\n## {target}\n{content}"
                elif target_type == "frontmatter":
                    # Replace frontmatter key
                    fm_end = existing.find("---", 3)
                    if fm_end > 0:
                        fm = existing[3:fm_end]
                        key = target
                        if f"{key}:" in fm:
                            fm = re.sub(rf'{re.escape(key)}:.*', f'{key}: {content}', fm)
                        else:
                            fm += f"\n{key}: {content}"
                        existing = f"---\n{fm}\n---" + existing[fm_end + 3:]
                elif target_type == "block":
                    # Simple block append
                    existing += f"\n\n{content}"
                else:
                    existing += f"\n\n{content}"
            elif operation == "append":
                existing += f"\n\n{content}"
            elif operation == "prepend":
                existing = content + "\n\n" + existing
            else:
                existing += f"\n\n{content}"

            full.write_text(existing, encoding="utf-8")
            return self._json(200, {"status": "OK", "path": rel, "operation": operation})
        self._json(404, {"error": "Not found"})

    def do_DELETE(self):
        parsed = urllib.parse.urlparse(self.path)
        path = urllib.parse.unquote(parsed.path)
        if not self._check_auth():
            return self._json(401, {"error": "Unauthorized"})
        if path.startswith("/vault/"):
            rel = path[len("/vault/"):].rstrip("/")
            full = VAULT_PATH / rel
            if full.exists():
                full.unlink()
                return self._json(200, {"status": "deleted", "path": rel})
            return self._json(404, {"error": f"Not found: {rel}", "reason": "note_missing"})
        self._json(404, {"error": "Not found"})


if __name__ == "__main__":
    server = HTTPServer(("127.0.0.1", PORT), VaultHandler)
    log.info(f"Vault server v2.1 on http://127.0.0.1:{PORT} (vault={VAULT_PATH})")
    server.serve_forever()

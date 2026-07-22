"""Simple Notes REST API with Token Authentication."""

import json
import os
import hashlib
import secrets
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

DATA_FILE = os.path.join(os.path.dirname(__file__), "notes.json")
API_TOKEN = os.environ.get("NOTES_API_TOKEN", "secret-token-123")


def load_notes():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE) as f:
            return json.load(f)
    return {}


def save_notes(notes):
    with open(DATA_FILE, "w") as f:
        json.dump(notes, f, indent=2)


def check_auth(handler):
    auth = handler.headers.get("Authorization", "")
    if auth == f"Bearer {API_TOKEN}":
        return True
    handler.send_response(401)
    handler.send_header("Content-Type", "application/json")
    handler.end_headers()
    handler.wfile.write(json.dumps({"error": "Unauthorized"}).encode())
    return False


class NotesHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if not check_auth(self):
            return
        parsed = urlparse(self.path)
        if parsed.path == "/notes":
            notes = load_notes()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(list(notes.values())).encode())
        elif parsed.path.startswith("/notes/"):
            note_id = parsed.path.split("/")[-1]
            notes = load_notes()
            if note_id in notes:
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(notes[note_id]).encode())
            else:
                self.send_response(404)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Not found"}).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if not check_auth(self):
            return
        if self.path == "/notes":
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length)) if length else {}
            note_id = secrets.token_hex(8)
            note = {"id": note_id, "title": body.get("title", ""), "content": body.get("content", "")}
            notes = load_notes()
            notes[note_id] = note
            save_notes(notes)
            self.send_response(201)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(note).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_DELETE(self):
        if not check_auth(self):
            return
        if self.path.startswith("/notes/"):
            note_id = self.path.split("/")[-1]
            notes = load_notes()
            if note_id in notes:
                del notes[note_id]
                save_notes(notes)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"deleted": note_id}).encode())
            else:
                self.send_response(404)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Not found"}).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # suppress logs


def run(port=8099):
    server = HTTPServer(("127.0.0.1", port), NotesHandler)
    print(f"Notes API running on http://127.0.0.1:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run()

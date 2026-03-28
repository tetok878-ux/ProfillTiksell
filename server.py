#!/usr/bin/env python3
"""
Portfolio Server
تشغيل: python3 server.py
ثم افتح: http://localhost:8080
"""

import http.server
import json
import os
import mimetypes
from urllib.parse import urlparse

PORT = 8080
UPLOADS_DIR = "uploads"
DATA_FILE   = "portfolio_data.json"

os.makedirs(UPLOADS_DIR, exist_ok=True)


class Handler(http.server.BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        print(f"[{self.address_string()}] {fmt % args}")

    # ──────────────────────────────────────────
    # GET
    # ──────────────────────────────────────────
    def do_GET(self):
        parsed = urlparse(self.path)
        path   = parsed.path

        if path == "/api/data":
            if os.path.exists(DATA_FILE):
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    content = f.read()
            else:
                content = "{}"
            self._send_json(content)
            return

        if path.startswith("/uploads/"):
            fname = os.path.basename(path)
            fpath = os.path.join(UPLOADS_DIR, fname)
            if os.path.exists(fpath):
                mime, _ = mimetypes.guess_type(fpath)
                with open(fpath, "rb") as f:
                    data = f.read()
                self.send_response(200)
                self.send_header("Content-Type", mime or "application/octet-stream")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            else:
                self._not_found()
            return

        if path in ("/", "/index.html", "/portfolio.html"):
            self._serve_file("portfolio.html", "text/html; charset=utf-8")
            return

        self._not_found()

    # ──────────────────────────────────────────
    # POST
    # ──────────────────────────────────────────
    def do_POST(self):
        parsed = urlparse(self.path)
        path   = parsed.path

        # Save portfolio data
        if path == "/api/save":
            length = int(self.headers.get("Content-Length", 0))
            body   = self.rfile.read(length)
            try:
                json.loads(body)
            except Exception:
                self._send_response(400, '{"error":"invalid json"}')
                return
            with open(DATA_FILE, "wb") as f:
                f.write(body)
            self._send_json('{"ok":true}')
            return

        # Upload image - multipart parser بدون cgi
        if path == "/api/upload-image":
            content_type = self.headers.get("Content-Type", "")
            if "multipart/form-data" in content_type:
                # استخرج الـ boundary
                boundary = None
                for part in content_type.split(";"):
                    part = part.strip()
                    if part.startswith("boundary="):
                        boundary = part[9:].strip().encode()
                        break

                if boundary:
                    length = int(self.headers.get("Content-Length", 0))
                    body   = self.rfile.read(length)

                    parts = body.split(b"--" + boundary)
                    for p in parts:
                        if b'filename="' in p:
                            header_end = p.find(b"\r\n\r\n")
                            if header_end == -1:
                                continue
                            file_data = p[header_end + 4:]
                            if file_data.endswith(b"\r\n"):
                                file_data = file_data[:-2]

                            header_str  = p[:header_end].decode(errors="ignore")
                            fname_start = header_str.find('filename="') + 10
                            fname_end   = header_str.find('"', fname_start)
                            filename    = header_str[fname_start:fname_end]

                            ext  = os.path.splitext(filename)[1].lower() or ".jpg"
                            name = "avatar" + ext
                            dest = os.path.join(UPLOADS_DIR, name)
                            with open(dest, "wb") as f:
                                f.write(file_data)
                            url = f"/uploads/{name}"
                            self._send_json(json.dumps({"ok": True, "url": url}))
                            return

            self._send_response(400, '{"error":"no file"}')
            return

        # Delete avatar
        if path == "/api/delete-image":
            for ext in [".jpg", ".jpeg", ".png", ".webp", ".gif"]:
                p = os.path.join(UPLOADS_DIR, "avatar" + ext)
                if os.path.exists(p):
                    os.remove(p)
            self._send_json('{"ok":true}')
            return

        self._not_found()

    # ──────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────
    def _serve_file(self, filename, content_type):
        if not os.path.exists(filename):
            self._not_found()
            return
        with open(filename, "rb") as f:
            data = f.read()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_json(self, content):
        self._send_response(200, content, "application/json")

    def _send_response(self, code, body, ctype="application/json"):
        b = body.encode() if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def _not_found(self):
        self._send_response(404, '{"error":"not found"}')


if __name__ == "__main__":
    server = http.server.HTTPServer(("", PORT), Handler)
    print(f"""
╔══════════════════════════════════╗
║  🚀 Portfolio Server            ║
║  http://localhost:{PORT}           ║
║  Ctrl+C للإيقاف                 ║
╚══════════════════════════════════╝
""")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n⛔ Server stopped.")


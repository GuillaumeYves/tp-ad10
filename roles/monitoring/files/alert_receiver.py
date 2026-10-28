#!/usr/bin/env python3
"""Enregistrer localement les notifications Alertmanager."""

from http.server import BaseHTTPRequestHandler, HTTPServer
import json


class Receiver(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/alerts":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > 1048576:
            self.send_error(413)
            return
        try:
            payload = json.loads(self.rfile.read(length))
        except (ValueError, UnicodeDecodeError):
            self.send_error(400)
            return
        print(json.dumps(payload, ensure_ascii=False), flush=True)
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok\n")


HTTPServer(("127.0.0.1", 9080), Receiver).serve_forever()

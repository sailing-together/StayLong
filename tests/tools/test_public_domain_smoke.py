from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from tools.public_domain_smoke import SmokeTestError, run_smoke


class _Handler(BaseHTTPRequestHandler):
    mode = "success"

    def log_message(self, *_args: object) -> None:
        return

    def _write(self, status: int, body: bytes, content_type: str = "application/json") -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/":
            if self.mode == "redirect":
                self.send_response(302)
                self.send_header("Location", f"http://localhost:{self.server.server_port}/")
                self.end_headers()
                return
            self._write(200, b'<script src="/assets/app.js"></script>', "text/html")
            return
        if self.path == "/assets/app.js":
            self._write(200, b'fetch("/v1/public/workflows")', "application/javascript")
            return
        self._write(404, b"{}")

    def do_POST(self) -> None:  # noqa: N802
        if self.path == "/v1/public/workflows":
            self.send_response(201)
            self.send_header("Set-Cookie", "staylong_session=test; HttpOnly")
            body = json.dumps({"case_id": "case-public-edge"}).encode()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self._write(401, json.dumps({"detail": "private route"}).encode())


@pytest.fixture
def smoke_server() -> str:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        thread.join()


def test_public_domain_smoke_checks_page_asset_and_public_workflow(smoke_server: str) -> None:
    assert run_smoke(smoke_server, require_https=False) == "case-public-edge"


def test_public_domain_smoke_rejects_noncanonical_redirect(smoke_server: str) -> None:
    _Handler.mode = "redirect"
    try:
        with pytest.raises(SmokeTestError, match="canonical"):
            run_smoke(smoke_server, require_https=False)
    finally:
        _Handler.mode = "success"


def test_public_domain_smoke_rejects_private_route(smoke_server: str) -> None:
    import requests

    response = requests.post(f"{smoke_server}/v1/private/workflows", timeout=5)
    assert response.status_code == 401

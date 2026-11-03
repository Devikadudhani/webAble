"""Browser integration tests against local fixtures only."""

import asyncio
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from app.capture.runner import BrowserCapture
from app.capture.storage import LocalScreenshotStorage


FIXTURES = Path(__file__).parent / "fixtures"


class LocalhostValidator:
    async def validate(self, url):
        return url


@pytest.fixture
def fixture_site():
    routes = {
        "/normal": "normal.html",
        "/captcha": "captcha.html",
        "/akamai-denied": "access_denied.html",
        "/empty": "empty.html",
        "/skeleton": "skeleton.html",
        "/failed-resource": "failed_resource.html",
    }

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/akamai-denied":
                body = (
                    b"<html><title>Access Denied</title><body>Access Denied. "
                    b"You don't have permission to access this server. "
                    b"Reference #18.5d6a3717.1793626490.389a730f "
                    b"https://errors.edgesuite.net/18.5d6a3717.1793626490.389a730f"
                    b"</body></html>"
                )
                self.send_response(403)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            fixture = routes.get(self.path, "normal.html")
            body = (FIXTURES / fixture).read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


@pytest.fixture
def capture(tmp_path):
    return BrowserCapture(
        storage=LocalScreenshotStorage(tmp_path),
        url_validator=LocalhostValidator(),
        settling_period_ms=0,
    )


@pytest.mark.browser_integration
def test_local_successful_page_is_eligible_and_persists_a_baseline(
    fixture_site, capture
):
    """Uses real Chromium, local HTML, and filesystem screenshot storage."""
    evidence = asyncio.run(capture.capture(f"{fixture_site}/normal", 1365, 768))

    assert evidence.navigation_status == "completed"
    assert evidence.readiness_status == "ready"
    assert evidence.analysis_eligible is True
    assert evidence.screenshot_ref is not None
    assert (capture._storage._directory.parent / evidence.screenshot_ref).is_file()


@pytest.mark.browser_integration
@pytest.mark.parametrize("path", ["captcha", "akamai-denied"])
def test_local_challenge_pages_are_not_analyzer_eligible(fixture_site, capture, path):
    """Challenge fixtures never invoke target-site analyzer callbacks."""
    analyzed = []

    async def analyzer(_page):
        analyzed.append(True)

    evidence = asyncio.run(
        capture.capture(f"{fixture_site}/{path}", 1365, 768, page_callback=analyzer)
    )

    assert evidence.access_status == "restricted"
    assert evidence.analysis_eligible is False
    assert evidence.screenshot_ref is None
    assert analyzed == []

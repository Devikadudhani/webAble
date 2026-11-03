"""Deployment checks, including a real Playwright protocol browser session."""

import asyncio
from fnmatch import fnmatchcase
import json
from pathlib import Path
import shutil
import subprocess
import sys
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from playwright._impl._driver import compute_driver_executable

from app.capture.runner import BrowserCapture, BrowserCaptureError
from app.capture.storage import LocalScreenshotStorage
from tests.test_capture import LocalhostValidator, fixture_server


def test_vercel_bundles_wcag_inventory(tmp_path):
    root = Path(__file__).resolve().parents[1]
    asset = "docs/wcag-22-coverage-inventory.json"
    config = json.loads((root / "vercel.json").read_text())
    function = config["functions"]["app/main.py"]
    assert function["includeFiles"] == asset
    exclusions = function.get("excludeFiles", "").strip("{}").split(",")
    assert not any(fnmatchcase(asset, pattern) for pattern in exclusions)

    # Check both the asset and its parent directories against upload ignores.
    paths = [asset, "docs", "docs/"]
    ignored = False
    for line in (root / ".vercelignore").read_text().splitlines():
        pattern = line.strip()
        if not pattern or pattern.startswith("#"):
            continue
        negated = pattern.startswith("!")
        pattern = pattern.removeprefix("!").lstrip("/").rstrip("/")
        if any(fnmatchcase(path.rstrip("/"), pattern) for path in paths):
            ignored = not negated
    assert not ignored, "The WCAG inventory must be uploaded to Vercel"

    # Reproduce the deployed relative layout, with no source docs to fall back to.
    for relative in ("app/analyzers/hybrid_evaluation.py", asset):
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / relative, destination)
    result = subprocess.run(
        [sys.executable, "-c", """
import json
import runpy
module = runpy.run_path('app/analyzers/hybrid_evaluation.py')
with open('docs/wcag-22-coverage-inventory.json') as source:
    inventory = json.load(source)
catalog = module['WCAG_CRITERIA_CATALOG']
assert len(catalog) == 55
assert {item['criterion_id'] for item in catalog} == {
    item['id'] for item in inventory['criteria']
}
"""],
        cwd=tmp_path, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr


def test_remote_playwright_capture(fixture_server, tmp_path, monkeypatch):
    node, cli = compute_driver_executable()
    package = str(Path(cli).parent)
    script = """
const { chromium } = require(process.argv[1]);
(async () => {
  const server = await chromium.launchServer({headless: true});
  console.log(server.wsEndpoint());
  process.stdin.resume();
  process.stdin.on('end', async () => { await server.close(); process.exit(0); });
})().catch(error => { console.error(error); process.exit(1); });
"""
    process = subprocess.Popen(
        [str(node), "-e", script, package],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True,
    )
    try:
        endpoint = process.stdout.readline().strip()
        assert endpoint.startswith("ws://")
        monkeypatch.setenv("WEBABLE_PLAYWRIGHT_WS_ENDPOINT", endpoint)
        monkeypatch.setenv("VERCEL", "1")
        service = BrowserCapture(
            LocalScreenshotStorage(tmp_path), LocalhostValidator(),
            settling_period_ms=0,
        )
        result = asyncio.run(service.capture(f"{fixture_server}/normal.html", 1280, 720))
        assert result.outcome == "completed"
        assert (tmp_path / result.screenshot_ref).is_file()
    finally:
        process.stdin.close()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def test_vercel_requires_remote_browser(tmp_path, monkeypatch):
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.delenv("WEBABLE_PLAYWRIGHT_WS_ENDPOINT", raising=False)
    service = BrowserCapture(LocalScreenshotStorage(tmp_path), LocalhostValidator())
    with pytest.raises(BrowserCaptureError, match="WS_ENDPOINT is required"):
        asyncio.run(service.capture("http://127.0.0.1/normal.html", 1280, 720))


@pytest.mark.parametrize("failure", [False, True])
def test_vercel_request_cleans_screenshots(monkeypatch, failure, tmp_path):
    from app import main

    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setattr(main.url_validator, "validate", AsyncMock())
    # Test cleanup must not depend on pre-existing user screenshots in output/.
    monkeypatch.setattr(
        main,
        "capture_service",
        BrowserCapture(LocalScreenshotStorage(tmp_path), main.url_validator),
    )
    outputs = []

    async def audit(url, capture, **kwargs):
        reference = capture.__self__._storage.save(b"temporary screenshot")
        directory = capture.__self__._storage._directory
        assert (directory.parent / reference).is_file()
        outputs.append(directory)
        if failure:
            raise BrowserCaptureError("test failure")
        return []

    monkeypatch.setattr(main, "capture_responsive_viewports", audit)
    with TestClient(main.app) as client:
        assert client.get("/accessibility/questionnaire").status_code == 200
        response = client.post("/captures", json={"url": "https://example.com"})
    assert response.status_code == (502 if failure else 200)
    assert outputs and all(not directory.exists() for directory in outputs)


def test_bundled_axe_matches_npm():
    root = Path(__file__).resolve().parents[1]
    # Git may check the vendored text file out as CRLF on Windows while npm
    # retains LF. Compare the JavaScript content, not checkout line endings.
    assert (root / "app/vendor/axe.min.js").read_text(encoding="utf-8") == (
        root / "node_modules/axe-core/axe.min.js"
    ).read_text(encoding="utf-8")

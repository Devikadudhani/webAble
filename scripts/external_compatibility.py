"""Opt-in external Playwright compatibility preflight.

This script performs one Chromium capture first. If the environment blocks it,
the benchmark is stopped and reported as blocked_by_test_environment.
"""

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.capture.runner import BrowserCapture
from app.capture.url_safety import PublicURLSafetyValidator


class MemoryStorage:
    def save(self, _image: bytes) -> str:
        return "memory.png"

    def save_scenario(self, _image: bytes, **_kwargs) -> str:
        return "memory-scenario.png"


BENCHMARK = {
    "Wikipedia": "https://www.wikipedia.org/",
    "Amazon": "https://www.amazon.com/",
    "Etsy": "https://www.etsy.com/",
    "Zara": "https://www.zara.com/",
    "Pinterest": "https://www.pinterest.com/",
    "YouTube": "https://www.youtube.com/",
}


def status_for(evidence) -> str:
    if evidence.final_url and evidence.final_url.startswith("chrome-error://"):
        return "blocked_by_test_environment"
    if evidence.access_status == "restricted":
        return "blocked_by_target"
    if evidence.analysis_eligible:
        return "passed"
    return "inconclusive"


async def capture_one(service, name: str, url: str) -> dict:
    started = time.monotonic()
    evidence = await service.capture(url, 1365, 768)
    return {
        "site": name,
        "status": status_for(evidence),
        "navigation_status": evidence.navigation_status,
        "readiness_status": evidence.readiness_status,
        "access_status": evidence.access_status,
        "http_status": evidence.main_document_http_status,
        "final_url": evidence.final_url,
        "restriction_provider": evidence.access_restriction_provider,
        "analyzer_eligible": evidence.analysis_eligible,
        "duration_ms": round((time.monotonic() - started) * 1000),
    }


async def main(run_benchmark: bool) -> None:
    service = BrowserCapture(MemoryStorage(), PublicURLSafetyValidator(), reuse_browser=True)
    try:
        first_name, first_url = next(iter(BENCHMARK.items()))
        first = await capture_one(service, first_name, first_url)
        print(json.dumps(first))
        if first["status"] == "blocked_by_test_environment":
            return
        if run_benchmark:
            for name, url in list(BENCHMARK.items())[1:]:
                print(json.dumps(await capture_one(service, name, url)))
    finally:
        await service.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", action="store_true")
    args = parser.parse_args()
    asyncio.run(main(args.benchmark))

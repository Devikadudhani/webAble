import asyncio
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app import main


def test_job_api_returns_before_audit_finishes(monkeypatch):
    monkeypatch.setattr(main, "capture_jobs", {})

    async def blocked_capture(request):
        await asyncio.sleep(60)

    monkeypatch.setattr(main, "create_capture", blocked_capture)
    with TestClient(main.app) as client:
        response = client.post("/captures/jobs", json={"url": "https://example.com"})
        assert response.status_code == 202
        job_id = response.json()["job_id"]
        assert client.get(f"/captures/jobs/{job_id}").json() == {"status": "pending"}
        assert client.get("/health").json() == {"status": "ok"}
        assert client.get("/captures/jobs/missing").status_code == 404
        assert client.post("/captures/jobs", json={}).status_code == 422


def test_two_users_queue_without_spending_execution_timeout(monkeypatch):
    async def run():
        monkeypatch.setattr(main, "capture_jobs", {})
        monkeypatch.setattr(main, "capture_slots", asyncio.Semaphore(1))
        monkeypatch.setattr(main, "CAPTURE_TIMEOUT_SECONDS", 0.1)
        monkeypatch.setattr(main.url_validator, "validate", AsyncMock())
        entered = asyncio.Event()
        release = asyncio.Event()
        calls = []

        async def capture(url, *args, **kwargs):
            calls.append(url)
            if len(calls) == 1:
                entered.set()
                await release.wait()
            return []

        monkeypatch.setattr(main, "capture_responsive_viewports", capture)
        # Occupy the slot longer than an audit's execution budget.
        await main.capture_slots.acquire()
        first = await main.submit_capture_job(main.CaptureRequest(url="https://example.com/a"))
        second = await main.submit_capture_job(main.CaptureRequest(url="https://example.com/b"))
        await asyncio.sleep(0.15)
        assert (await main.get_capture_job(first["job_id"]))["status"] == "pending"
        assert calls == []
        main.capture_slots.release()
        await asyncio.wait_for(entered.wait(), 1)
        assert len(calls) == 1
        release.set()
        await asyncio.gather(*main.capture_tasks)
        reports = [await main.get_capture_job(item["job_id"]) for item in (first, second)]
        assert all(report["status"] == "completed" for report in reports)
        assert [report["result"]["requested_url"] for report in reports] == calls
        assert len(calls) == 2

    asyncio.run(run())


def test_queue_full_expired_and_failed_jobs(monkeypatch):
    async def run():
        monkeypatch.setattr(main, "capture_jobs", {"busy": {"status": "pending"}})
        monkeypatch.setattr(main, "MAX_PENDING_CAPTURES", 1)
        request = main.CaptureRequest(url="https://example.com")
        with pytest.raises(HTTPException) as full:
            await main.submit_capture_job(request)
        assert full.value.status_code == 429
        main.capture_jobs["old"] = {"status": "completed", "finished_at": -main.JOB_RETENTION_SECONDS}
        with pytest.raises(HTTPException) as expired:
            await main.get_capture_job("old")
        assert expired.value.status_code == 404
        monkeypatch.setattr(main, "create_capture", AsyncMock(side_effect=HTTPException(400, {"detail": "Unsafe URL"})))
        await main._run_capture_job("busy", request)
        assert (await main.get_capture_job("busy"))["error"]["detail"] == "Unsafe URL"

    asyncio.run(run())

import asyncio
import logging
import re
import struct
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Protocol, TypeVar

from playwright.async_api import (
    Browser,
    BrowserContext,
    Error as PlaywrightError,
    Page,
    Playwright,
    Request,
    TimeoutError as PlaywrightTimeoutError,
    async_playwright,
)

from app.capture.models import (
    BrowserEvidence,
    DocumentDimensions,
    FailedRequest,
    ViewportDimensions,
)
from app.capture.storage import ScreenshotStorage
from app.capture.url_safety import UnsafeURL, sanitize_url

logger = logging.getLogger(__name__)
MAX_EVIDENCE_EVENTS = 200
EvidenceEvent = TypeVar("EvidenceEvent", str, FailedRequest)
_URL_IN_ERROR = re.compile(r"https?://[^\s\"'<>]+")


class URLValidator(Protocol):
    async def validate(self, url: str) -> str:
        ...


class BrowserCaptureError(RuntimeError):
    """Raised when Chromium cannot create or operate a capture session."""


PageCallback = Callable[[Page], Awaitable[None]]


class BrowserCapture:
    def __init__(
        self,
        storage: ScreenshotStorage,
        url_validator: URLValidator,
        navigation_timeout_ms: int = 15_000,
        settling_period_ms: int = 1_500,
        reuse_browser: bool = False,
    ) -> None:
        self._storage = storage
        self._url_validator = url_validator
        self._navigation_timeout_ms = navigation_timeout_ms
        self._settling_period_ms = settling_period_ms
        self._reuse_browser = reuse_browser
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._browser_lock = asyncio.Lock()

    @asynccontextmanager
    async def _browser_session(self) -> AsyncIterator[tuple[Browser, bool]]:
        if self._reuse_browser:
            yield await self._get_reusable_browser(), False
            return

        async with async_playwright() as playwright:
            try:
                browser = await playwright.chromium.launch()
            except PlaywrightError as error:
                raise BrowserCaptureError(
                    "Chromium could not start a capture session."
                ) from error
            yield browser, True

    async def _get_reusable_browser(self) -> Browser:
        async with self._browser_lock:
            if self._browser is not None and self._browser.is_connected():
                return self._browser

            if self._playwright is not None:
                await self._playwright.stop()
            try:
                self._playwright = await async_playwright().start()
                browser = await self._playwright.chromium.launch()
                self._browser = browser
            except PlaywrightError as error:
                if self._playwright is not None:
                    await self._playwright.stop()
                self._playwright = None
                self._browser = None
                raise BrowserCaptureError(
                    "Chromium could not start a capture session."
                ) from error
            return browser

    async def close(self) -> None:
        browser, self._browser = self._browser, None
        playwright, self._playwright = self._playwright, None
        errors = await _close_resources(None, None, browser)
        if playwright is not None:
            try:
                await playwright.stop()
            except Exception as error:
                errors.append(error)
        if errors:
            raise BrowserCaptureError(
                "The shared Chromium browser could not be closed cleanly."
            ) from errors[0]

    async def save_scenario_screenshot(
        self,
        page: Page,
        capture_id: str,
        viewport_name: str,
        scenario_id: str,
        width: int,
        height: int,
    ) -> str:
        dimensions = await page.evaluate(
            "() => ({width: window.innerWidth, height: window.innerHeight})"
        )
        if dimensions != {"width": width, "height": height}:
            raise RuntimeError("Scenario viewport changed before screenshot capture.")

        image = await page.screenshot(
            type="png",
            full_page=False,
            scale="css",
        )
        if image[:8] != b"\x89PNG\r\n\x1a\n" or len(image) < 24:
            raise RuntimeError("Scenario screenshot is not a valid PNG image.")
        image_width, image_height = struct.unpack(">II", image[16:24])
        if (image_width, image_height) != (width, height):
            raise RuntimeError("Scenario screenshot dimensions do not match its viewport.")
        return self._storage.save_scenario(
            image,
            capture_id=capture_id,
            viewport_name=viewport_name,
            scenario_id=scenario_id,
            width=width,
            height=height,
        )

    async def capture(
        self,
        url: str,
        width: int,
        height: int,
        *,
        page_callback: PageCallback | None = None,
    ) -> BrowserEvidence:
        await self._url_validator.validate(url)
        requested_url = sanitize_url(url)
        viewport = ViewportDimensions(width, height)
        evidence = BrowserEvidence(
            requested_url=requested_url,
            final_url=None,
            page_title=None,
            viewport=viewport,
            document=DocumentDimensions(None, None, None, None),
            screenshot_ref=None,
            navigation_duration_ms=0,
            settling_duration_ms=0,
            browser_name="Chromium",
            scanned_at=datetime.now(timezone.utc),
        )

        context: BrowserContext | None = None
        page: Page | None = None
        async with self._browser_session() as (browser, close_browser):
            primary_error: BaseException | None = None
            try:
                try:
                    context = await browser.new_context(
                        viewport={"width": width, "height": height},
                        service_workers="block",
                    )
                    page = await context.new_page()
                except PlaywrightError as error:
                    raise BrowserCaptureError(
                        "Chromium could not start a capture session."
                    ) from error

                page.on(
                    "console",
                    lambda message: _append_event(
                        evidence.console_errors, _limit(message.text), evidence
                    )
                    if message.type == "error"
                    else None,
                )
                page.on(
                    "pageerror",
                    lambda error: _append_event(
                        evidence.uncaught_page_errors, _limit(str(error)), evidence
                    ),
                )
                page.on(
                    "requestfailed",
                    lambda request: _append_event(
                        evidence.failed_requests, _failed_request(request), evidence
                    ),
                )
                page.on(
                    "response",
                    lambda response: _append_event(
                        evidence.failed_requests,
                        FailedRequest(
                            url=sanitize_url(response.url),
                            resource_type=response.request.resource_type,
                            error=f"HTTP {response.status}",
                        ),
                        evidence,
                    )
                    if response.status >= 400
                    else None,
                )
                await page.route("**/*", self._guard_request(evidence))
                await self._navigate(page, url, evidence)
                await self._settle_and_collect(page, evidence)
                self._set_outcome(evidence)
                if (
                    page_callback is not None
                    and evidence.outcome == "completed"
                    and evidence.readiness_status == "ready"
                ):
                    await page_callback(page)
            except PlaywrightError as error:
                primary_error = BrowserCaptureError(
                    "Chromium failed while preparing the capture."
                )
                raise primary_error from error
            except BaseException as error:
                primary_error = error
                raise
            finally:
                cleanup_errors = await _close_resources(
                    page,
                    context,
                    browser if close_browser else None,
                )
                if cleanup_errors:
                    if primary_error is None:
                        raise BrowserCaptureError(
                            "The browser capture resources could not be closed cleanly."
                        ) from cleanup_errors[0]
                    logger.error(
                        "Browser capture cleanup failed after a capture error: %s",
                        cleanup_errors[0],
                    )
        return evidence

    def _guard_request(self, evidence: BrowserEvidence):
        async def guard(route) -> None:
            try:
                await self._url_validator.validate(route.request.url)
            except UnsafeURL as error:
                _append_event(
                    evidence.failed_requests,
                    FailedRequest(
                        url=sanitize_url(route.request.url),
                        resource_type=route.request.resource_type,
                        error=str(error),
                    ),
                    evidence,
                )
                if "A request to a prohibited destination was blocked." not in evidence.details:
                    evidence.details.append(
                        "A request to a prohibited destination was blocked."
                    )
                await route.abort("blockedbyclient")
                return
            await route.continue_()

        return guard

    async def _navigate(
        self, page: Page, url: str, evidence: BrowserEvidence
    ) -> None:
        started = time.monotonic()
        try:
            await page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=self._navigation_timeout_ms,
            )
            evidence.navigation_status = "completed"
        except PlaywrightTimeoutError:
            evidence.navigation_status = "timeout"
            evidence.details.append(
                f"Navigation did not reach DOMContentLoaded within "
                f"{self._navigation_timeout_ms} ms."
            )
        except PlaywrightError as error:
            evidence.navigation_status = "failed"
            evidence.details.append(
                f"Navigation failed: {_limit(_safe_browser_error(error))}"
            )
        finally:
            evidence.navigation_duration_ms = round(
                (time.monotonic() - started) * 1000
            )

    async def _settle_and_collect(
        self, page: Page, evidence: BrowserEvidence
    ) -> None:
        settle_started = time.monotonic()
        settling_completed = False
        try:
            await page.wait_for_timeout(self._settling_period_ms)
            settling_completed = True
        except PlaywrightError as error:
            evidence.readiness_status = "unavailable"
            evidence.details.append(
                f"The page could not settle: {_limit(_safe_browser_error(error))}"
            )
        finally:
            evidence.settling_duration_ms = round(
                (time.monotonic() - settle_started) * 1000
            )

        if settling_completed:
            try:
                metadata = await page.evaluate(
                    """() => ({
                        title: document.title || null,
                        scrollWidth: document.documentElement?.scrollWidth ?? null,
                        scrollHeight: document.documentElement?.scrollHeight ?? null,
                        visibleWidth: window.innerWidth || null,
                        visibleHeight: window.innerHeight || null
                    })"""
                )
                evidence.final_url = sanitize_url(page.url) if page.url else None
                evidence.page_title = metadata["title"]
                evidence.document = DocumentDimensions(
                    scroll_width=metadata["scrollWidth"],
                    scroll_height=metadata["scrollHeight"],
                    visible_width=metadata["visibleWidth"],
                    visible_height=metadata["visibleHeight"],
                )
                evidence.readiness_status = "ready"
            except PlaywrightError as error:
                evidence.readiness_status = "unavailable"
                evidence.details.append(
                    f"Page metadata could not be collected: "
                    f"{_limit(_safe_browser_error(error))}"
                )

        if evidence.readiness_status != "unavailable":
            try:
                image = await page.screenshot(type="png", full_page=False)
                evidence.screenshot_ref = self._storage.save(image)
            except (PlaywrightError, OSError) as error:
                evidence.details.append(
                    f"Screenshot capture failed: {_limit(_safe_browser_error(error))}"
                )
            if evidence.navigation_status != "completed":
                evidence.readiness_status = "partial"

    @staticmethod
    def _set_outcome(evidence: BrowserEvidence) -> None:
        if evidence.navigation_status == "timeout":
            evidence.outcome = "navigation_timeout"
        elif (
            evidence.navigation_status == "completed"
            and evidence.readiness_status == "ready"
            and evidence.screenshot_ref is not None
            and not evidence.details
        ):
            evidence.outcome = "completed"
        else:
            evidence.outcome = "partial"


def _failed_request(request: Request) -> FailedRequest:
    return FailedRequest(
        url=sanitize_url(request.url),
        resource_type=request.resource_type,
        error=_limit(request.failure) if request.failure else None,
    )


def _safe_browser_error(error: Exception) -> str:
    message = str(error).splitlines()[0]
    message = _URL_IN_ERROR.sub(
        lambda match: sanitize_url(match.group()), message
    )
    return message.replace("\x00", "")[:500]


def _limit(value: str) -> str:
    return value[:1_000]


def _append_event(
    collection: list[EvidenceEvent], value: EvidenceEvent, evidence: BrowserEvidence
) -> None:
    if len(collection) < MAX_EVIDENCE_EVENTS:
        collection.append(value)
    elif "Browser evidence event lists were capped at 200 entries." not in evidence.details:
        evidence.details.append("Browser evidence event lists were capped at 200 entries.")


async def _close_resources(
    page: Page | None,
    context: BrowserContext | None,
    browser: Browser | None,
) -> list[Exception]:
    errors: list[Exception] = []
    for resource in (page, context, browser):
        if resource is None:
            continue
        try:
            await resource.close()
        except Exception as error:
            errors.append(error)
    return errors

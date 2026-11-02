import asyncio
import logging
import re
import struct
import time
import os
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


def _bounded_env_int(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        value = default
    return max(minimum, min(maximum, value))


NAVIGATION_TIMEOUT_MS = _bounded_env_int("WEBABLE_NAVIGATION_TIMEOUT_MS", 20_000, 1_000, 60_000)
SETTLING_PERIOD_MS = _bounded_env_int("WEBABLE_SETTLING_PERIOD_MS", 4_000, 250, 15_000)
READINESS_TIMEOUT_MS = _bounded_env_int("WEBABLE_READINESS_TIMEOUT_MS", 30_000, 500, 45_000)
NETWORK_IDLE_SIGNAL_MS = _bounded_env_int("WEBABLE_NETWORK_IDLE_SIGNAL_MS", 400, 0, 5_000)
LAZY_SCROLL_MAX_STEPS = _bounded_env_int("WEBABLE_LAZY_SCROLL_MAX_STEPS", 24, 0, 60)
LAZY_SCROLL_STEP_WAIT_MS = _bounded_env_int("WEBABLE_LAZY_SCROLL_STEP_WAIT_MS", 150, 50, 500)
LAZY_SCROLL_MAX_MS = _bounded_env_int("WEBABLE_LAZY_SCROLL_MAX_MS", 5_000, 0, 10_000)

_READINESS_SNAPSHOT = """() => {
  const visible = (element) => {
    const rect = element.getBoundingClientRect(), style = getComputedStyle(element);
    return rect.width > 0 && rect.height > 0 && style.display !== 'none' &&
      style.visibility !== 'hidden' && style.visibility !== 'collapse';
  };
  const main = document.querySelector('main,[role=main]');
  const appRoot = document.querySelector('#app,#root');
  const article = document.querySelector('article');
  const primary = main || appRoot || article || document.body;
  const bodyText = (document.body?.innerText || '').trim();
  let primaryText = (primary?.innerText || '').trim();
  if (primary === document.body) {
    const content = document.body.cloneNode(true);
    content.querySelectorAll('header,nav,footer,[role=navigation]').forEach((el) => el.remove());
    primaryText = (content.innerText || '').trim();
  }
  const inPrimary = (selector) => Array.from(primary?.querySelectorAll(selector) || []).filter(visible);
  const loaderSelector = '[aria-busy=true],[role=progressbar],.skeleton,[class*=skeleton],[class*=loading]';
  const loadingNodes = inPrimary(loaderSelector);
  if (primary?.matches(loaderSelector)) loadingNodes.unshift(primary);
  const skeletonCount = inPrimary('.skeleton,[class*=skeleton]').length;
  const listingItems = inPrimary('article,li,[role=listitem],[data-product-id],[data-testid*=product],[class*=product-card],[class*=product-item],[class*=product-grid__item]').length;
  const contentNodes = inPrimary('h1,h2,h3,p,button,a[href],img,[role=button],[role=link],article,li,[role=listitem]');
  const images = inPrimary('img');
  const loaderOnly = /^(loading|loading products|please wait|fetching|fetching products|updating|one moment)([ .…!]+)?$/i.test(primaryText);
  const hasContent = primaryText.length > 0 || images.length > 0 || listingItems > 0;
  const hasSubstantialContent = primaryText.length >= 120 || listingItems > 0;
  const primaryReady = hasContent && !loaderOnly &&
    (loadingNodes.length === 0 || hasSubstantialContent);
  return {
    title: document.title || null,
    url: location.href,
    readyState: document.readyState,
    bodyText,
    primaryText,
    primaryCharacters: primaryText.length,
    primaryItems: listingItems,
    primaryVisibleElements: contentNodes.length,
    primaryImages: images.length,
    loadingIndicators: loadingNodes.length,
    skeletons: skeletonCount,
    primaryReady,
    scrollWidth: document.documentElement?.scrollWidth ?? null,
    scrollHeight: document.documentElement?.scrollHeight ?? null,
    visibleWidth: window.innerWidth || null,
    visibleHeight: window.innerHeight || null,
    unloadedImages: Array.from(document.images).filter((image) => {
      const style = getComputedStyle(image);
      return image.getClientRects().length > 0 && style.display !== 'none' &&
        style.visibility !== 'hidden' && style.visibility !== 'collapse' &&
        (!image.complete || image.naturalWidth === 0);
    }).length,
    height: document.documentElement?.scrollHeight || 0
  };
}"""

_BROWSER_ERROR_MARKERS = (
    "this site can’t be reached",
    "this site can't be reached",
    "webpage is not available",
    "problem loading page",
    "err_connection_",
    "err_name_not_resolved",
    "server not found",
    "this page isn’t working",
    "this page isn't working",
)
_ACCESS_RESTRICTION_PHRASES = {
    "captcha_or_human_verification": ("captcha", "verify you are human", "prove you are human"),
    "possible_bot_protection": ("unusual traffic", "automated requests", "access denied", "request blocked", "you don't have permission to access", "you do not have permission to access"),
    "authentication_required": ("sign in to continue", "log in to continue", "authentication required"),
    "consent_dialog": ("cookie settings", "cookie preferences", "consent preferences"),
}


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
        navigation_timeout_ms: int = NAVIGATION_TIMEOUT_MS,
        settling_period_ms: int = SETTLING_PERIOD_MS,
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
                endpoint = os.getenv("WEBABLE_PLAYWRIGHT_WS_ENDPOINT")
                if os.getenv("VERCEL") and not endpoint:
                    raise BrowserCaptureError(
                        "WEBABLE_PLAYWRIGHT_WS_ENDPOINT is required on Vercel."
                    )
                browser = (
                    await playwright.chromium.connect(endpoint)
                    if endpoint
                    else await playwright.chromium.launch()
                )
            except BrowserCaptureError:
                raise
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
                endpoint = os.getenv("WEBABLE_PLAYWRIGHT_WS_ENDPOINT")
                if os.getenv("VERCEL") and not endpoint:
                    raise BrowserCaptureError(
                        "WEBABLE_PLAYWRIGHT_WS_ENDPOINT is required on Vercel."
                    )
                browser = (
                    await self._playwright.chromium.connect(endpoint)
                    if endpoint
                    else await self._playwright.chromium.launch()
                )
                self._browser = browser
            except BrowserCaptureError:
                if self._playwright is not None:
                    await self._playwright.stop()
                self._playwright = None
                self._browser = None
                raise
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
                    lambda response: _record_response(response, evidence, page),
                )
                await page.route("**/*", self._guard_request(evidence))
                await self._navigate(page, url, evidence)
                await self._settle_and_collect(page, evidence)
                self._set_outcome(evidence)
                if page_callback is not None and evidence.analysis_eligible:
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
        try:
            state = await self._wait_for_readiness(page, evidence)
        except PlaywrightError as error:
            evidence.readiness_status = "unavailable"
            evidence.access_status = "unavailable"
            evidence.details.append(
                f"The page could not settle: {_limit(_safe_browser_error(error))}"
            )
            state = None
        finally:
            evidence.settling_duration_ms = round(
                (time.monotonic() - settle_started) * 1000
            )

        if state is not None:
            try:
                self._record_page_state(state, page, evidence)
            except PlaywrightError as error:
                evidence.readiness_status = "unavailable"
                evidence.access_status = "unavailable"
                evidence.details.append(
                    f"Page metadata could not be collected: "
                    f"{_limit(_safe_browser_error(error))}"
                )

        if evidence.analysis_eligible:
            await self._load_lazy_content(page, evidence)
            try:
                refreshed = await page.evaluate(_READINESS_SNAPSHOT)
                self._record_page_state(refreshed, page, evidence)
                if not evidence.analysis_eligible:
                    return
                image = await page.screenshot(type="png", full_page=False)
                evidence.screenshot_ref = self._storage.save(image)
            except (PlaywrightError, OSError) as error:
                evidence.details.append(
                    f"Screenshot capture failed: {_limit(_safe_browser_error(error))}"
                )
        else:
            if not evidence.details:
                evidence.details.append(
                    "The target website's primary content did not render sufficiently for evaluation."
                )
        if evidence.navigation_status != "completed" and evidence.analysis_eligible:
            evidence.readiness_status = "partial"
            evidence.access_status = "partial"

    async def _wait_for_readiness(self, page: Page, evidence: BrowserEvidence) -> dict:
        started = time.monotonic()
        deadline = started + READINESS_TIMEOUT_MS / 1_000
        previous = None
        stable_since = None
        state = None
        while time.monotonic() < deadline:
            try:
                state = await page.evaluate(_READINESS_SNAPSHOT)
            except PlaywrightError:
                await page.wait_for_timeout(200)
                continue
            body_text = (state["bodyText"] or "").lower()
            if self._has_access_restriction(body_text, state["url"], evidence):
                break
            signature = (
                state["primaryCharacters"],
                state["primaryItems"],
                state["height"],
                state["loadingIndicators"],
            )
            if signature == previous and state["readyState"] != "loading":
                stable_since = stable_since or time.monotonic()
            else:
                stable_since = None
            previous = signature
            if (
                state["primaryReady"]
                and stable_since is not None
                and time.monotonic() - stable_since >= 0.5
            ):
                break
            await page.wait_for_timeout(200)
        # networkidle is a bounded supporting signal only; persistent requests
        # cannot prevent analysis once usable content is present.
        if NETWORK_IDLE_SIGNAL_MS:
            try:
                await page.wait_for_load_state("networkidle", timeout=NETWORK_IDLE_SIGNAL_MS)
            except PlaywrightError:
                pass
        elapsed = round((time.monotonic() - started) * 1000)
        evidence.readiness_elapsed_ms = elapsed
        if elapsed < self._settling_period_ms:
            await page.wait_for_timeout(min(self._settling_period_ms - elapsed, 1_000))
        if state is None:
            raise PlaywrightError("The page state could not be inspected.")
        return state

    @staticmethod
    def _has_access_restriction(
        body_text: str, page_url: str, evidence: BrowserEvidence
    ) -> bool:
        if page_url.startswith(("chrome-error://", "edge-error://")) or any(
            marker in body_text for marker in _BROWSER_ERROR_MARKERS
        ):
            evidence.access_status = "unavailable"
            detail = "The browser displayed a navigation error instead of the target website."
            if detail not in evidence.details:
                evidence.details.append(detail)
            return True
        page_text = body_text[:20_000]
        if "errors.edgesuite.net" in page_text or "akamai" in page_text:
            evidence.access_restriction_provider = "Akamai EdgeSuite"
            reference = re.search(
                r"(?:reference\s*#|errors\.edgesuite\.net/)([a-z0-9.-]{6,100})",
                page_text,
                re.IGNORECASE,
            )
            if reference:
                evidence.access_restriction_reference = reference.group(1)
            if "cdn_access_denied" not in evidence.access_restriction_signals:
                evidence.access_restriction_signals.append("cdn_access_denied")
        for signal, phrases in _ACCESS_RESTRICTION_PHRASES.items():
            if any(phrase in page_text for phrase in phrases) and signal not in evidence.access_restriction_signals:
                evidence.access_restriction_signals.append(signal)
        http_restricted = (
            evidence.main_document_http_status is not None
            and evidence.main_document_http_status >= 400
        )
        challenge_restricted = any(
            signal != "consent_dialog"
            for signal in evidence.access_restriction_signals
        )
        if http_restricted or challenge_restricted:
            evidence.access_status = "restricted"
            if evidence.access_restriction_provider:
                reference_text = (
                    f" Reference: {evidence.access_restriction_reference}."
                    if evidence.access_restriction_reference else ""
                )
                detail = (
                    f"The target returned an access-denied page from {evidence.access_restriction_provider}. "
                    "WebAble could not inspect the actual website, so page analyzers were not run. "
                    "If you control the site, ask its administrator/CDN operator to allow the scan or use an authorized staging copy."
                    + reference_text
                )
            elif http_restricted:
                detail = f"The main document returned HTTP {evidence.main_document_http_status}; page analyzers were not run."
            else:
                detail = (
                    "Possible CAPTCHA, bot-protection, or authentication screen detected; "
                    "page analyzers were not run. This is a text-based diagnostic signal."
                )
            if detail not in evidence.details:
                evidence.details.append(detail)
            return True
        return False

    def _record_page_state(self, state: dict, page: Page, evidence: BrowserEvidence) -> None:
        body_text = (state.get("bodyText") or "").lower()
        was_restricted = self._has_access_restriction(
            body_text, state.get("url") or page.url, evidence
        )
        evidence.final_url = sanitize_url(state.get("url") or page.url) if page.url else None
        evidence.page_title = state.get("title")
        evidence.document = DocumentDimensions(
            scroll_width=state.get("scrollWidth"),
            scroll_height=state.get("scrollHeight"),
            visible_width=state.get("visibleWidth"),
            visible_height=state.get("visibleHeight"),
        )
        evidence.visible_content_characters = len(state.get("bodyText") or "")
        evidence.primary_content_characters = state.get("primaryCharacters", 0)
        evidence.primary_content_items = state.get("primaryItems", 0)
        evidence.loading_indicator_count = state.get("loadingIndicators", 0)
        evidence.unloaded_image_count = state.get("unloadedImages", 0)
        if evidence.access_restriction_signals:
            detail = (
                "Page state includes possible access/consent signals: "
                + ", ".join(dict.fromkeys(evidence.access_restriction_signals))
                + "."
            )
            if detail not in evidence.details:
                evidence.details.append(detail)
        if was_restricted and evidence.access_status == "unavailable":
            evidence.analysis_eligible = False
            evidence.readiness_status = "unavailable"
            return
        if was_restricted:
            evidence.analysis_eligible = False
            evidence.readiness_status = "unavailable"
            return
        evidence.analysis_eligible = bool(state.get("primaryReady"))
        if evidence.analysis_eligible:
            evidence.access_status = (
                "partial" if evidence.navigation_status != "completed" else "accessible"
            )
            evidence.readiness_status = (
                "partial" if evidence.access_status == "partial" else "ready"
            )
        else:
            evidence.access_status = "unavailable"
            evidence.readiness_status = "unavailable"

    async def _load_lazy_content(self, page: Page, evidence: BrowserEvidence) -> None:
        if not LAZY_SCROLL_MAX_STEPS or not LAZY_SCROLL_MAX_MS:
            return
        started = time.monotonic()
        try:
            dimensions = await page.evaluate("() => ({height:document.documentElement.scrollHeight, step:Math.max(300,window.innerHeight*0.75)})")
            target = min(dimensions["height"], dimensions["step"] * LAZY_SCROLL_MAX_STEPS)
            position = 0
            while position < target and (time.monotonic() - started) * 1000 < LAZY_SCROLL_MAX_MS:
                position = min(target, position + dimensions["step"])
                await page.evaluate("y => window.scrollTo(0,y)", position)
                await page.wait_for_timeout(LAZY_SCROLL_STEP_WAIT_MS)
                current = await page.evaluate("() => document.documentElement.scrollHeight")
                if current > dimensions["height"]:
                    dimensions["height"] = current
                    target = min(current, dimensions["step"] * LAZY_SCROLL_MAX_STEPS)
        except PlaywrightError as error:
            evidence.details.append(f"Lazy-content scrolling was incomplete: {_limit(_safe_browser_error(error))}")
        finally:
            try:
                await page.evaluate("() => window.scrollTo(0,0)")
                await page.wait_for_timeout(150)
            except PlaywrightError as error:
                evidence.details.append(
                    f"The page could not return to the baseline viewport: {_limit(_safe_browser_error(error))}"
                )

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


def _record_response(response, evidence: BrowserEvidence, page: Page) -> None:
    request = response.request
    if request.is_navigation_request() and request.frame == page.main_frame:
        evidence.main_document_http_status = response.status
    if response.status >= 400:
        _append_event(
            evidence.failed_requests,
            FailedRequest(
                url=sanitize_url(response.url),
                resource_type=request.resource_type,
                error=f"HTTP {response.status}",
            ),
            evidence,
        )
    if request.redirected_from is not None:
        chain = []
        current = request
        while current is not None and len(chain) < 10:
            chain.append(sanitize_url(current.url))
            current = current.redirected_from
        chain.reverse()
        if chain not in evidence.redirect_chains:
            evidence.redirect_chains.append(chain)


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

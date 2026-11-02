from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Literal, Protocol
from urllib.parse import urljoin, urlsplit, urlunsplit

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from app.capture.url_safety import UnsafeURL, sanitize_url


FunctionalUXStatus = Literal["available", "partial", "unavailable", "not_attempted"]
FunctionalUXFindingStatus = Literal["observed_failure", "inconclusive", "untested"]
LinkCheckStatus = Literal[
    "verified", "observed_failure", "inconclusive", "untested"
]
FunctionalUXFailureCategory = Literal[
    "http_error",
    "network_failure",
    "timeout",
    "blocked_destination",
    "missing_source",
    "resource_load_failure",
    "inconclusive",
    "redirect_limit",
]

MAX_LINKS = 15
MAX_IMAGES = 50
MAX_REDIRECTS = 5
REQUEST_TIMEOUT_MS = 1_200
LINK_CHECK_TIMEOUT_SECONDS = 3
MAX_CONCURRENT_LINK_CHECKS = 5
MAX_LINK_AUDIT_DURATION_SECONDS = (
    (MAX_LINKS + MAX_CONCURRENT_LINK_CHECKS - 1)
    // MAX_CONCURRENT_LINK_CHECKS
) * LINK_CHECK_TIMEOUT_SECONDS


@dataclass(frozen=True)
class FunctionalUXFinding:
    rule_id: Literal["broken_link", "failed_image"]
    element_selector: str
    accessible_label: str | None
    destination_url: str | None
    failure_category: FunctionalUXFailureCategory
    status: FunctionalUXFindingStatus
    evidence: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class FunctionalUXAuditResult:
    status: FunctionalUXStatus
    findings: list[FunctionalUXFinding] = field(default_factory=list)
    inconclusive: list[FunctionalUXFinding] = field(default_factory=list)
    checked_links: int = 0
    checked_images: int = 0
    excluded_non_http_links: int = 0
    details: list[str] = field(default_factory=list)


class DestinationValidator(Protocol):
    async def validate(self, url: str) -> str:
        ...


class APIResponse(Protocol):
    status: int
    headers: dict[str, str]

    async def dispose(self) -> None:
        ...


class APIRequestContext(Protocol):
    async def head(
        self,
        url: str,
        *,
        timeout: int,
        max_redirects: int,
        fail_on_status_code: bool = False,
    ) -> APIResponse:
        ...

    async def get(
        self,
        url: str,
        *,
        timeout: int,
        max_redirects: int,
        fail_on_status_code: bool = False,
        headers: dict[str, str] | None = None,
    ) -> APIResponse:
        ...


class FunctionalPage(Protocol):
    request: APIRequestContext

    async def evaluate(self, expression: str, arg: dict) -> dict:
        ...


@dataclass(frozen=True)
class LinkCheckResult:
    status: LinkCheckStatus
    category: FunctionalUXFailureCategory
    evidence: list[str]
    limitations: list[str] = field(default_factory=list)


_COLLECT_RENDERED_ELEMENTS = """({maxLinks, maxImages}) => {
    const selectorFor = (element) => {
        if (element.id) return `#${CSS.escape(element.id)}`;
        const path = [];
        for (let current = element; current && current.nodeType === 1;
             current = current.parentElement) {
            if (current.id) {
                path.unshift(`#${CSS.escape(current.id)}`);
                break;
            }
            const tag = current.tagName.toLowerCase();
            const siblings = current.parentElement
                ? Array.from(current.parentElement.children)
                    .filter((sibling) => sibling.tagName === current.tagName)
                : [];
            path.unshift(
                siblings.length > 1
                    ? `${tag}:nth-of-type(${siblings.indexOf(current) + 1})`
                    : tag
            );
        }
        return path.join(" > ");
    };
    const rendered = (element) => {
        const style = getComputedStyle(element);
        return element.getClientRects().length > 0 &&
            style.display !== "none" &&
            style.visibility !== "hidden" &&
            style.visibility !== "collapse" &&
            style.contentVisibility !== "hidden" &&
            Number(style.opacity) !== 0;
    };
    const labelFor = (element) => {
        const label = element.getAttribute("aria-label") ||
            element.getAttribute("alt") ||
            element.getAttribute("title") ||
            element.innerText ||
            "";
        return label.trim().replace(/\\s+/g, " ").slice(0, 160) || null;
    };

    const allLinks = Array.from(document.querySelectorAll("a[href]"))
        .filter(rendered);
    const allImages = Array.from(document.querySelectorAll("img"))
        .filter(rendered);
    return {
        links: allLinks.slice(0, maxLinks).map((element) => ({
            selector: selectorFor(element),
            label: labelFor(element),
            href: element.href,
        })),
        images: allImages.slice(0, maxImages).map((element) => ({
            selector: selectorFor(element),
            label: labelFor(element),
            source: element.currentSrc || element.src || "",
            sourceAttribute: element.getAttribute("src"),
            hasAlt: element.hasAttribute("alt"),
            altAttribute: element.getAttribute("alt"),
            complete: element.complete,
            naturalWidth: element.naturalWidth,
            role: element.getAttribute("role"),
            ariaHidden: element.getAttribute("aria-hidden")
        })),
        linksTruncated: allLinks.length > maxLinks,
        imagesTruncated: allImages.length > maxImages
    };
}"""


async def audit_functional_ux(
    page: FunctionalPage,
    destination_validator: DestinationValidator | None,
) -> FunctionalUXAuditResult:
    """Audit rendered links with bounded HEAD/ranged-GET checks and image state."""
    try:
        rendered = await page.evaluate(
            _COLLECT_RENDERED_ELEMENTS,
            {"maxLinks": MAX_LINKS, "maxImages": MAX_IMAGES},
        )
    except Exception as error:
        return FunctionalUXAuditResult(
            status="unavailable",
            details=[f"Functional UX evidence could not be collected ({type(error).__name__})."],
        )

    details: list[str] = []
    if rendered.get("linksTruncated"):
        details.append(f"Link collection was limited to {MAX_LINKS} rendered elements.")
    if rendered.get("imagesTruncated"):
        details.append(
            f"Image collection was limited to {MAX_IMAGES} rendered elements."
        )

    links = rendered.get("links", [])
    checked_link_candidates = []
    excluded_non_http_links = 0
    for link in links:
        if _request_url(link.get("href", "")) is None:
            excluded_non_http_links += 1
        else:
            checked_link_candidates.append(link)
    check_by_url: dict[str, LinkCheckResult] = {}
    if destination_validator is not None:
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_LINK_CHECKS)

        async def check_limited(url: str) -> LinkCheckResult:
            async with semaphore:
                try:
                    return await asyncio.wait_for(
                        _check_link(page.request, url, destination_validator),
                        timeout=LINK_CHECK_TIMEOUT_SECONDS,
                    )
                except TimeoutError:
                    return LinkCheckResult(
                        status="inconclusive",
                        category="timeout",
                        evidence=["The bounded link check timed out."],
                        limitations=["A timeout does not establish that the destination is broken."],
                    )
                except Exception as error:
                    return LinkCheckResult(
                        status="inconclusive",
                        category="inconclusive",
                        evidence=[
                            f"The link check could not be completed ({type(error).__name__})."
                        ],
                        limitations=["The destination's availability could not be determined."],
                    )

        unique_urls = list(
            dict.fromkeys(
                url
                for link in checked_link_candidates
                if (url := _request_url(link.get("href", ""))) is not None
            )
        )
        checked_results = await asyncio.gather(
            *(check_limited(url) for url in unique_urls)
        )
        check_by_url = dict(zip(unique_urls, checked_results))

    findings: list[FunctionalUXFinding] = []
    inconclusive: list[FunctionalUXFinding] = []
    checked_links = 0
    for link in checked_link_candidates:
        href = link.get("href", "")
        request_url = _request_url(href)
        if request_url is None:
            continue
        if destination_validator is None:
            result = LinkCheckResult(
                status="untested",
                category="inconclusive",
                evidence=["No destination validator was available for a safe link check."],
                limitations=["The destination was not requested."],
            )
        else:
            checked_links += 1
            result = check_by_url[request_url]

        if result.status == "observed_failure":
            findings.append(
                _finding("broken_link", link, request_url, result)
            )
        elif result.status in ("inconclusive", "untested"):
            inconclusive.append(_finding("broken_link", link, request_url, result))

    image_findings, image_inconclusive, checked_images = _image_findings(
        rendered.get("images", [])
    )
    findings.extend(image_findings)
    inconclusive.extend(image_inconclusive)

    if details or inconclusive:
        status: FunctionalUXStatus = "partial"
    else:
        status = "available"
    return FunctionalUXAuditResult(
        status=status,
        findings=findings,
        inconclusive=inconclusive,
        checked_links=checked_links,
        checked_images=checked_images,
        excluded_non_http_links=excluded_non_http_links,
        details=details,
    )


def _image_findings(
    images: list[dict],
) -> tuple[list[FunctionalUXFinding], list[FunctionalUXFinding], int]:
    findings: list[FunctionalUXFinding] = []
    inconclusive: list[FunctionalUXFinding] = []
    checked_images = 0
    for image in images:
        source_attribute = image.get("sourceAttribute")
        source = image.get("source") or ""
        label = image.get("label")
        non_content = (
            image.get("role") == "presentation"
            or image.get("ariaHidden") == "true"
            or (
                image.get("hasAlt")
                and not (image.get("altAttribute") or "").strip()
                and not image.get("label")
            )
        )
        if not source_attribute or not source_attribute.strip():
            if not non_content and label:
                finding = FunctionalUXFinding(
                    rule_id="failed_image",
                    element_selector=image["selector"],
                    accessible_label=label,
                    destination_url=None,
                    failure_category="missing_source",
                    status="observed_failure",
                    evidence=["The rendered image has an accessible label but no non-empty src attribute."],
                )
                findings.append(finding)
            elif not non_content:
                inconclusive.append(
                    FunctionalUXFinding(
                        rule_id="failed_image",
                        element_selector=image["selector"],
                        accessible_label=label,
                        destination_url=None,
                        failure_category="missing_source",
                        status="inconclusive",
                        evidence=["The rendered image has no non-empty src attribute."],
                        limitations=["Without a content label, the element may be intentionally empty or decorative."],
                    )
                )
            continue

        if image.get("complete") and image.get("naturalWidth", 0) == 0:
            checked_images += 1
            findings.append(
                FunctionalUXFinding(
                    rule_id="failed_image",
                    element_selector=image["selector"],
                    accessible_label=label,
                    destination_url=sanitize_url(source),
                    failure_category="resource_load_failure",
                    status="observed_failure",
                    evidence=["The image finished loading with naturalWidth equal to zero."],
                )
            )
        elif image.get("naturalWidth", 0) > 0:
            checked_images += 1
        else:
            inconclusive.append(
                FunctionalUXFinding(
                    rule_id="failed_image",
                    element_selector=image["selector"],
                    accessible_label=label,
                    destination_url=sanitize_url(source),
                    failure_category="inconclusive",
                    status="inconclusive",
                    evidence=["The image has not reached a conclusive loaded or failed state."],
                    limitations=["The settling interval may be shorter than the image's load time."],
                )
            )
    return findings, inconclusive, checked_images


async def _check_link(
    request: APIRequestContext,
    url: str,
    validator: DestinationValidator,
) -> LinkCheckResult:
    current_url = url
    for redirect_count in range(MAX_REDIRECTS + 1):
        try:
            current_url = await validator.validate(current_url)
        except UnsafeURL:
            return LinkCheckResult(
                status="untested",
                category="blocked_destination",
                evidence=["Destination safety validation prohibited this URL."],
                limitations=["The destination was not requested."],
            )
        method = "HEAD"
        try:
            response = await request.head(
                current_url,
                timeout=REQUEST_TIMEOUT_MS,
                max_redirects=0,
                fail_on_status_code=False,
            )
        except PlaywrightTimeoutError:
            return LinkCheckResult(
                status="inconclusive",
                category="timeout",
                evidence=["The HEAD request exceeded its timeout."],
                limitations=["A timeout does not establish that the destination is broken."],
            )
        except PlaywrightError:
            return LinkCheckResult(
                status="observed_failure",
                category="network_failure",
                evidence=["The browser request failed before receiving an HTTP response."],
            )

        status_code = response.status
        location = response.headers.get("location")
        await response.dispose()
        if status_code in (405, 501):
            # Some valid destinations reject HEAD. A one-byte range GET can
            # establish reachability without intentionally fetching the full body.
            method = "GET"
            try:
                response = await request.get(
                    current_url,
                    timeout=REQUEST_TIMEOUT_MS,
                    max_redirects=0,
                    fail_on_status_code=False,
                    headers={"Range": "bytes=0-0"},
                )
            except PlaywrightTimeoutError:
                return LinkCheckResult(
                    status="inconclusive",
                    category="timeout",
                    evidence=["The ranged GET fallback exceeded its timeout."],
                    limitations=["A timeout does not establish that the destination is broken."],
                )
            except PlaywrightError:
                return LinkCheckResult(
                    status="inconclusive",
                    category="inconclusive",
                    evidence=["The ranged GET fallback failed before receiving an HTTP response."],
                    limitations=["The destination could not be conclusively checked."],
                )
            status_code = response.status
            location = response.headers.get("location")
            await response.dispose()
        if status_code in (301, 302, 303, 307, 308):
            if not location:
                return LinkCheckResult(
                    status="inconclusive",
                    category="inconclusive",
                    evidence=[f"HTTP {status_code} redirect did not include a Location header."],
                )
            if redirect_count == MAX_REDIRECTS:
                return LinkCheckResult(
                    status="inconclusive",
                    category="redirect_limit",
                    evidence=[f"The destination exceeded {MAX_REDIRECTS} redirects."],
                    limitations=["The final destination was not checked."],
                )
            current_url = urljoin(current_url, location)
            continue
        if 200 <= status_code < 300:
            return LinkCheckResult(
                status="verified",
                category="inconclusive",
                evidence=[f"{method} request returned HTTP {status_code}."],
            )
        if status_code in (401, 403, 405, 408, 429, 501):
            return LinkCheckResult(
                status="inconclusive",
                category="inconclusive",
                evidence=[f"{method} request returned HTTP {status_code}."],
                limitations=["Access restrictions, rate limiting, or unsupported HEAD requests can prevent a conclusive check."],
            )
        if status_code >= 400:
            return LinkCheckResult(
                status="observed_failure",
                category="http_error",
                evidence=[f"Destination returned HTTP {status_code} to a {method} request."],
                limitations=["The destination may respond differently to other methods or user-specific requests."],
            )
        return LinkCheckResult(
            status="inconclusive",
            category="inconclusive",
            evidence=[f"{method} request returned HTTP {status_code}."],
            limitations=["The response status does not establish whether the destination is usable."],
        )

    raise AssertionError("Redirect loop exited without returning a result.")


def _finding(
    rule_id: Literal["broken_link", "failed_image"],
    element: dict,
    destination_url: str | None,
    result: LinkCheckResult,
) -> FunctionalUXFinding:
    return FunctionalUXFinding(
        rule_id=rule_id,
        element_selector=element["selector"],
        accessible_label=element.get("label"),
        destination_url=sanitize_url(destination_url) if destination_url else None,
        failure_category=result.category,
        status=result.status,
        evidence=result.evidence,
        limitations=result.limitations,
    )


def _request_url(url: str) -> str | None:
    if not url:
        return None
    parts = urlsplit(url)
    if parts.scheme.lower() not in ("http", "https") or not parts.netloc:
        return None
    return urlunsplit((parts.scheme, parts.netloc, parts.path, parts.query, ""))

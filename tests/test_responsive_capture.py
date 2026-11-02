import asyncio
from datetime import datetime, timezone

import pytest

import app.capture.responsive as responsive
from app.analyzers.element_horizontal_overflow import (
    ElementHorizontalOverflowEvidence,
)
from app.capture.models import (
    BrowserEvidence,
    DocumentDimensions,
    ViewportDimensions,
)
from app.capture.runner import BrowserCaptureError
from app.capture.url_safety import UnsafeURL


class FakePage:
    def __init__(self):
        self.width = 1365
        self.height = 768

    async def add_script_tag(self, *, content):
        assert content

    async def evaluate(self, _expression, argument):
        if isinstance(argument, dict):
            if "maxElements" in argument:
                return {
                    "viewport": {"width": self.width, "height": self.height},
                    "document": {
                        "scrollWidth": self.width,
                        "scrollHeight": self.height,
                    },
                    "inspectedTextElements": 0,
                    "candidatesTruncated": False,
                    "elements": [],
                    "overflowBoundaries": [],
                    "overlapPairs": [],
                }
            if "tags" in argument or "rules" in argument:
                return {
                    "testEngine": {"version": "4.14.0"},
                    "violations": [],
                    "incomplete": [],
                    "passes": [],
                    "inapplicable": [],
                }
            return {
                "links": [],
                "images": [],
                "linksTruncated": False,
                "imagesTruncated": False,
            }
        if isinstance(argument, list):
            return {
                "testEngine": {"version": "4.14.0"},
                "violations": [],
                "incomplete": [],
                "passes": [],
                "inapplicable": [],
            }
        return []

    async def set_viewport_size(self, viewport_size):
        self.width = viewport_size["width"]
        self.height = viewport_size["height"]


async def finish_diagnosis(page_callback):
    if page_callback is not None:
        await page_callback(FakePage())


def make_evidence(
    width: int,
    height: int,
    *,
    scroll_width: int | None,
    visible_width: int | None,
    screenshot_ref: str | None,
    outcome: str = "completed",
    readiness_status: str = "ready",
) -> BrowserEvidence:
    return BrowserEvidence(
        requested_url="https://example.test/",
        final_url="https://example.test/",
        page_title="fixture",
        viewport=ViewportDimensions(width=width, height=height),
        document=DocumentDimensions(
            scroll_width=scroll_width,
            scroll_height=height,
            visible_width=visible_width,
            visible_height=height,
        ),
        screenshot_ref=screenshot_ref,
        navigation_duration_ms=10,
        settling_duration_ms=5,
        browser_name="Chromium",
        scanned_at=datetime.now(timezone.utc),
        navigation_status="completed",
        readiness_status=readiness_status,
        outcome=outcome,
    )


def test_uses_standard_viewports_and_same_url_for_each_capture():
    url = "https://example.test/path?keep=yes"
    calls = []

    async def capture(requested_url, width, height, *, page_callback=None):
        calls.append((requested_url, width, height))
        await finish_diagnosis(page_callback)
        return make_evidence(
            width,
            height,
            scroll_width=width,
            visible_width=width,
            screenshot_ref=f"{width}x{height}.png",
        )

    results = asyncio.run(responsive.capture_responsive_viewports(url, capture))

    assert calls == [
        (url, 1365, 768),
        (url, 768, 1024),
        (url, 390, 844),
    ]
    assert [(result.name, result.viewport) for result in results] == [
        ("desktop", ViewportDimensions(1365, 768)),
        ("tablet", ViewportDimensions(768, 1024)),
        ("mobile", ViewportDimensions(390, 844)),
    ]


def test_analyzes_each_successful_capture_using_its_dimensions(monkeypatch):
    analyzer_calls = []

    def analyzer(*, scroll_width, visible_width):
        analyzer_calls.append((scroll_width, visible_width))
        return responsive.HorizontalOverflowResult(
            scroll_width=scroll_width,
            visible_width=visible_width,
            overflow_px=max(0, scroll_width - visible_width),
            potential_horizontal_overflow=scroll_width > visible_width,
        )

    monkeypatch.setattr(responsive, "analyze_horizontal_overflow", analyzer)

    async def capture(_url, width, height, *, page_callback=None):
        await finish_diagnosis(page_callback)
        return make_evidence(
            width,
            height,
            scroll_width=width + 10,
            visible_width=width,
            screenshot_ref=f"{width}.png",
        )

    results = asyncio.run(
        responsive.capture_responsive_viewports("https://example.test", capture)
    )

    assert analyzer_calls == [(1375, 1365), (778, 768), (400, 390)]
    assert all(result.horizontal_overflow is not None for result in results)


def test_overflow_can_be_detected_on_mobile_but_not_desktop():
    async def capture(_url, width, height, *, page_callback=None):
        await finish_diagnosis(page_callback)
        return make_evidence(
            width,
            height,
            scroll_width=500 if width == 390 else width,
            visible_width=width,
            screenshot_ref=f"{width}.png",
        )

    results = asyncio.run(
        responsive.capture_responsive_viewports("https://example.test", capture)
    )

    assert results[0].horizontal_overflow.potential_horizontal_overflow is False
    assert results[2].horizontal_overflow.potential_horizontal_overflow is True
    assert results[2].horizontal_overflow.overflow_px == 110


@pytest.mark.parametrize("failure", [BrowserCaptureError("browser failed"), RuntimeError()])
def test_failed_viewport_does_not_prevent_later_captures(failure):
    calls = []

    async def capture(_url, width, height, *, page_callback=None):
        calls.append(width)
        if width == 768:
            raise failure
        await finish_diagnosis(page_callback)
        return make_evidence(
            width,
            height,
            scroll_width=width,
            visible_width=width,
            screenshot_ref=f"{width}.png",
        )

    results = asyncio.run(
        responsive.capture_responsive_viewports("https://example.test", capture)
    )

    assert calls == [1365, 768, 390]
    assert results[1].capture_outcome == "capture_failed"
    assert results[1].horizontal_overflow is None
    assert results[2].name == "mobile"
    assert results[2].horizontal_overflow.potential_horizontal_overflow is False
    assert results[1].functional_ux_audit.status == "not_attempted"


def test_prohibited_url_prevents_repeated_capture_attempts():
    calls = []

    async def capture(_url, width, _height, *, page_callback=None):
        calls.append(width)
        raise UnsafeURL("The URL resolves to a prohibited destination.")

    results = asyncio.run(
        responsive.capture_responsive_viewports("http://127.0.0.1", capture)
    )

    assert calls == [1365]
    assert [result.capture_outcome for result in results] == [
        "capture_failed",
        "not_attempted",
        "not_attempted",
    ]
    assert all(result.horizontal_overflow is None for result in results)


@pytest.mark.parametrize(
    ("scroll_width", "visible_width", "outcome", "readiness", "status"),
    [
        (None, 390, "completed", "ready", "missing_dimensions"),
        (400, None, "completed", "ready", "missing_dimensions"),
        (390, 390, "partial", "partial", "available"),
        (390, 390, "navigation_timeout", "partial", "available"),
    ],
)
def test_missing_dimensions_or_incomplete_capture_is_not_reported_clean(
    scroll_width, visible_width, outcome, readiness, status
):
    async def capture(_url, width, height, *, page_callback=None):
        await finish_diagnosis(page_callback)
        return make_evidence(
            width,
            height,
            scroll_width=scroll_width,
            visible_width=visible_width,
            screenshot_ref="partial.png",
            outcome=outcome,
            readiness_status=readiness,
        )

    results = asyncio.run(
        responsive.capture_responsive_viewports("https://example.test", capture)
    )

    if scroll_width is None or visible_width is None:
        assert all(result.horizontal_overflow is None for result in results)
    else:
        assert all(result.horizontal_overflow is not None for result in results)
    assert all(result.overflow_analysis_status == status for result in results)
    expected_functional_status = "available"
    assert all(
        result.functional_ux_audit.status == expected_functional_status
        for result in results
    )
    assert all(result.details for result in results)


def test_functional_audit_failure_does_not_discard_capture_or_overflow(monkeypatch):
    async def fail_audit(_page, _validator):
        raise RuntimeError("audit failure")

    monkeypatch.setattr(responsive, "audit_functional_ux", fail_audit)

    async def capture(_url, width, height, *, page_callback=None):
        await finish_diagnosis(page_callback)
        return make_evidence(
            width,
            height,
            scroll_width=width + 10,
            visible_width=width,
            screenshot_ref=f"{width}.png",
        )

    results = asyncio.run(
        responsive.capture_responsive_viewports("https://example.test", capture)
    )

    assert all(result.capture_outcome == "completed" for result in results)
    assert all(result.horizontal_overflow.overflow_px == 10 for result in results)
    assert all(result.screenshot_ref for result in results)
    assert all(result.functional_ux_audit.status == "unavailable" for result in results)
    assert all(result.functional_ux_audit.details for result in results)


def test_accessibility_scan_failure_preserves_existing_capture_results(monkeypatch):
    async def fail_scan(_page):
        raise RuntimeError("engine failed")

    monkeypatch.setattr(responsive, "scan_accessibility", fail_scan)

    async def capture(_url, width, height, *, page_callback=None):
        await finish_diagnosis(page_callback)
        return make_evidence(
            width,
            height,
            scroll_width=width + 10,
            visible_width=width,
            screenshot_ref=f"{width}.png",
        )

    results = asyncio.run(
        responsive.capture_responsive_viewports("https://example.test", capture)
    )

    assert all(result.capture_outcome == "completed" for result in results)
    assert all(result.horizontal_overflow.overflow_px == 10 for result in results)
    assert all(result.screenshot_ref for result in results)
    assert all(result.functional_ux_audit.status == "available" for result in results)
    assert all(result.accessibility_scan.status == "unavailable" for result in results)
    assert all(result.accessibility_scan.details for result in results)


def test_keyboard_audit_failure_preserves_capture_and_other_audits(monkeypatch):
    async def fail_keyboard_audit(_page):
        raise RuntimeError("keyboard audit failed")

    monkeypatch.setattr(responsive, "audit_keyboard_focus", fail_keyboard_audit)

    async def capture(_url, width, height, *, page_callback=None):
        await finish_diagnosis(page_callback)
        return make_evidence(
            width,
            height,
            scroll_width=width + 10,
            visible_width=width,
            screenshot_ref=f"screenshots/{width}.png",
        )

    results = asyncio.run(
        responsive.capture_responsive_viewports("https://example.test", capture)
    )

    assert all(result.capture_outcome == "completed" for result in results)
    assert all(result.screenshot_ref for result in results)
    assert all(result.horizontal_overflow.overflow_px == 10 for result in results)
    assert all(result.functional_ux_audit.status == "available" for result in results)
    assert all(result.accessibility_scan.status == "available" for result in results)
    assert all(result.keyboard_focus_audit.status == "unavailable" for result in results)
    assert all(result.keyboard_focus_audit.details for result in results)


def test_text_reflow_failure_preserves_existing_capture_and_audits(monkeypatch):
    async def fail_text_reflow(*_args, **_kwargs):
        raise RuntimeError("reflow evaluator failed")

    monkeypatch.setattr(responsive, "audit_text_reflow", fail_text_reflow)

    async def capture(_url, width, height, *, page_callback=None):
        await finish_diagnosis(page_callback)
        return make_evidence(
            width,
            height,
            scroll_width=width + 10,
            visible_width=width,
            screenshot_ref=f"screenshots/{width}.png",
        )

    results = asyncio.run(
        responsive.capture_responsive_viewports("https://example.test", capture)
    )

    assert all(result.capture_outcome == "completed" for result in results)
    assert all(result.screenshot_ref for result in results)
    assert all(result.horizontal_overflow.overflow_px == 10 for result in results)
    assert all(result.functional_ux_audit.status == "available" for result in results)
    assert all(result.accessibility_scan.status == "available" for result in results)
    assert all(result.keyboard_focus_audit.status == "unavailable" for result in results)
    assert all(result.text_reflow_audit.status == "unavailable" for result in results)
    assert all(result.text_reflow_audit.details for result in results)


def test_results_keep_viewport_screenshot_and_outcome_associated():
    async def capture(_url, width, height, *, page_callback=None):
        await finish_diagnosis(page_callback)
        return make_evidence(
            width,
            height,
            scroll_width=width,
            visible_width=width,
            screenshot_ref=f"screenshots/{width}.png",
        )

    results = asyncio.run(
        responsive.capture_responsive_viewports("https://example.test", capture)
    )

    assert [
        (result.name, result.viewport.width, result.screenshot_ref)
        for result in results
    ] == [
        ("desktop", 1365, "screenshots/1365.png"),
        ("tablet", 768, "screenshots/768.png"),
        ("mobile", 390, "screenshots/390.png"),
    ]
    assert all(result.capture_outcome == "completed" for result in results)
    assert all(
        result.element_overflow_diagnosis.status == "available"
        for result in results
    )
    for result in results:
        baseline = next(
            scenario
            for scenario in result.text_reflow_audit.scenarios
            if scenario.scenario_id == "baseline"
        )
        assert baseline.screenshot_ref == result.screenshot_ref
        assert all(
            scenario.screenshot_ref is None
            for scenario in result.text_reflow_audit.scenarios
            if scenario.scenario_id != "baseline"
        )


def test_element_findings_are_associated_with_correct_viewport():
    async def diagnoser(_page, viewport_width):
        if viewport_width == 1365:
            return []
        from app.analyzers.element_horizontal_overflow import (
            ElementHorizontalOverflowEvidence,
        )

        return [
            ElementHorizontalOverflowEvidence(
                tag_name="div",
                selector=f"#viewport-{viewport_width}",
                left=0,
                right=900,
                width=900,
                viewport_width=viewport_width,
                overflow_px=900 - viewport_width,
                status="potential_overflow_source",
                scrollable_context_detected=False,
                scrollable_container_selector=None,
            )
        ]

    async def capture(_url, width, height, *, page_callback=None):
        await finish_diagnosis(page_callback)
        return make_evidence(
            width,
            height,
            scroll_width=900,
            visible_width=width,
            screenshot_ref=f"{width}.png",
        )

    results = asyncio.run(
        responsive.capture_responsive_viewports(
            "https://example.test", capture, diagnoser=diagnoser
        )
    )

    assert results[0].element_overflow_diagnosis.findings == []
    assert results[0].element_overflow_diagnosis.status == "available"
    for result in results[1:]:
        finding = result.element_overflow_diagnosis.findings[0]
        assert finding.viewport_width == result.viewport.width
        assert finding.selector == f"#viewport-{result.viewport.width}"


def test_diagnosis_failure_preserves_successful_capture():
    async def diagnoser(_page, _viewport_width):
        raise RuntimeError("diagnosis failed")

    async def capture(_url, width, height, *, page_callback=None):
        await finish_diagnosis(page_callback)
        return make_evidence(
            width,
            height,
            scroll_width=width,
            visible_width=width,
            screenshot_ref=f"screenshots/{width}.png",
        )

    results = asyncio.run(
        responsive.capture_responsive_viewports(
            "https://example.test", capture, diagnoser=diagnoser
        )
    )

    assert all(result.capture_outcome == "completed" for result in results)
    assert all(result.screenshot_ref for result in results)
    assert all(
        result.element_overflow_diagnosis.status == "unavailable"
        for result in results
    )
    assert all(result.element_overflow_diagnosis.findings == [] for result in results)
    assert all(result.element_overflow_diagnosis.details for result in results)


def test_capture_failure_does_not_report_diagnosis_as_clean():
    async def capture(_url, width, _height, *, page_callback=None):
        if width == 1365:
            raise RuntimeError("capture failed")
        await finish_diagnosis(page_callback)
        return make_evidence(
            width,
            1024,
            scroll_width=width,
            visible_width=width,
            screenshot_ref=f"{width}.png",
        )

    results = asyncio.run(
        responsive.capture_responsive_viewports("https://example.test", capture)
    )

    assert results[0].element_overflow_diagnosis.status == "not_attempted"
    assert results[0].element_overflow_diagnosis.findings == []
    assert results[1].element_overflow_diagnosis.status == "available"
    assert results[1].element_overflow_diagnosis.findings == []


def test_normalization_failure_preserves_capture_and_raw_diagnosis(monkeypatch):
    raw_finding = ElementHorizontalOverflowEvidence(
        tag_name="div",
        selector="#wide",
        left=0,
        right=500,
        width=500,
        viewport_width=390,
        overflow_px=110,
        status="potential_overflow_source",
        scrollable_context_detected=False,
        scrollable_container_selector=None,
    )

    async def diagnoser(_page, _viewport_width):
        return [raw_finding]

    def fail_normalization(*_args, **_kwargs):
        raise RuntimeError("normalization failed")

    monkeypatch.setattr(
        responsive, "normalize_horizontal_overflow_findings", fail_normalization
    )

    async def capture(_url, width, height, *, page_callback=None):
        await finish_diagnosis(page_callback)
        return make_evidence(
            width,
            height,
            scroll_width=width + 110,
            visible_width=width,
            screenshot_ref=f"screenshots/{width}.png",
        )

    results = asyncio.run(
        responsive.capture_responsive_viewports(
            "https://example.test", capture, diagnoser=diagnoser
        )
    )

    mobile = results[2]
    assert mobile.capture_outcome == "completed"
    assert mobile.screenshot_ref == "screenshots/390.png"
    assert mobile.element_overflow_diagnosis.status == "available"
    preserved_finding = mobile.element_overflow_diagnosis.findings[0]
    assert preserved_finding.selector == raw_finding.selector
    assert preserved_finding.left == raw_finding.left
    assert preserved_finding.right == raw_finding.right
    assert mobile.finding_normalization.status == "unavailable"
    assert mobile.finding_normalization.findings == []
    assert mobile.finding_normalization.details

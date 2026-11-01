import asyncio
import struct
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from playwright.async_api import async_playwright

from app.analyzers.element_horizontal_overflow import (
    diagnose_element_horizontal_overflow,
)
from app.analyzers.element_layout_evidence import enrich_element_layout_evidence
from app.analyzers.keyboard_focus import audit_keyboard_focus
from app.analyzers.text_reflow import audit_text_reflow
from app.capture.runner import BrowserCapture
from app.capture.responsive import capture_responsive_viewports
from app.capture.storage import LocalScreenshotStorage
from app.capture.url_safety import PublicURLSafetyValidator, UnsafeURL, sanitize_url


FIXTURES = Path(__file__).parent / "fixtures"


class FixtureHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/missing.png":
            self.send_error(404)
            return
        if path == "/valid.svg":
            body = b'<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12"></svg>'
            self.send_response(200)
            self.send_header("Content-Type", "image/svg+xml")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if path == "/timeout":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><head><title>Slow</title>")
            self.wfile.flush()
            threading.Event().wait(1)
            return

        fixture = {
            "/normal": "normal.html",
            "/overflow": "overflow.html",
            "/responsive-overflow": "responsive_overflow.html",
            "/layout-fixed-width": "layout_fixed_width.html",
            "/layout-oversized-descendant": "layout_oversized_descendant.html",
            "/layout-flex-grid": "layout_flex_grid.html",
            "/layout-horizontal-scroll": "layout_horizontal_scroll.html",
            "/delayed": "delayed.html",
            "/failed-resource": "failed_resource.html",
            "/javascript-error": "javascript_error.html",
            "/blocked-resource": "blocked_resource.html",
            "/functional-ux": "functional_ux.html",
            "/accessibility": "accessibility.html",
            "/non-text-contrast": "non_text_contrast.html",
            "/non-text-contrast-adequate": "non_text_contrast_adequate.html",
            "/target-size-small": "target_size_small.html",
            "/target-size-adequate": "target_size_adequate.html",
            "/keyboard-visible": "keyboard_focus_visible.html",
            "/keyboard-absent": "keyboard_focus_absent.html",
            "/keyboard-skipped": "keyboard_focus_skipped.html",
            "/keyboard-trap": "keyboard_focus_trap.html",
            "/keyboard-one-way-block": "keyboard_focus_one_way_block.html",
            "/keyboard-many-controls": "keyboard_focus_many_controls.html",
            "/keyboard-wrapping-cycle": "keyboard_focus_wrapping_cycle.html",
            "/keyboard-overlay": "keyboard_focus_overlay.html",
            "/keyboard-overlay-opaque": "keyboard_focus_overlay_opaque.html",
            "/keyboard-dialog": "keyboard_focus_dialog.html",
            "/keyboard-sticky-partial": "keyboard_focus_sticky_partial.html",
            "/keyboard-unobscured": "keyboard_focus_unobscured.html",
            "/keyboard-none": "keyboard_focus_none.html",
            "/keyboard-unsafe": "keyboard_focus_unsafe.html",
            "/keyboard-edge-cases": "keyboard_focus_edge_cases.html",
            "/text-reflow-usable": "text_reflow_usable.html",
            "/text-reflow-clipped": "text_reflow_clipped.html",
            "/text-reflow-overlap": "text_reflow_overlap.html",
            "/text-reflow-wide": "text_reflow_wide.html",
            "/text-reflow-table": "text_reflow_table.html",
            "/text-reflow-unbreakable": "text_reflow_unbreakable.html",
            "/text-reflow-dynamic": "text_reflow_dynamic.html",
            "/text-reflow-review": "text_reflow_review.html",
            "/text-reflow-responsive": "text_reflow_responsive.html",
            "/text-spacing-usable": "text_spacing_usable.html",
            "/text-spacing-clipped": "text_spacing_clipped.html",
            "/text-spacing-overlap": "text_spacing_overlap.html",
            "/text-spacing-control": "text_spacing_control.html",
            "/text-spacing-obscured-control": "text_spacing_obscured_control.html",
            "/text-spacing-scrollable": "text_spacing_scrollable.html",
            "/hover-focus-compliant": "hover_focus_compliant.html",
            "/hover-focus-not-hoverable": "hover_focus_not_hoverable.html",
            "/hover-focus-undismissable": "hover_focus_undismissable.html",
            "/hover-focus-style-only": "hover_focus_style_only.html",
            "/orientation-flexible": "orientation_flexible.html",
            "/orientation-restricted": "orientation_restricted.html",
        }.get(path, "normal.html")
        body = (FIXTURES / fixture).read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_HEAD(self):
        path = urlparse(self.path).path
        if path == "/redirect-to-ok":
            self.send_response(302)
            self.send_header("Location", "/normal")
            self.end_headers()
            return
        if path == "/redirect-to-private":
            self.send_response(302)
            self.send_header("Location", "http://private.invalid/private-link")
            self.end_headers()
            return
        if path == "/broken-link":
            self.send_error(404)
            return
        if path == "/slow-link":
            threading.Event().wait(2)
        if path == "/missing.png":
            self.send_error(404)
            return
        if path == "/valid.svg":
            self.send_response(200)
            self.send_header("Content-Type", "image/svg+xml")
            self.end_headers()
            return
        if path == "/private-link":
            self.send_response(200)
            self.end_headers()
            return
        if path == "/normal":
            self.send_response(200)
            self.end_headers()
            return
        self.send_error(404)

    def log_message(self, format, *args):
        pass


class LocalhostValidator:
    async def validate(self, url: str) -> str:
        return url


class BlocksTestExternalHost(LocalhostValidator):
    async def validate(self, url: str) -> str:
        if urlparse(url).hostname == "private.invalid":
            raise UnsafeURL("The URL resolves to a prohibited network destination.")
        return url


@pytest.fixture(scope="module")
def fixture_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    thread.join()
    server.server_close()


@pytest.fixture
def capture(tmp_path):
    return BrowserCapture(
        storage=LocalScreenshotStorage(tmp_path),
        url_validator=LocalhostValidator(),
        navigation_timeout_ms=300,
        settling_period_ms=50,
    )


def test_normal_fixture_collects_metadata_and_screenshot(fixture_server, capture):
    evidence = asyncio.run(
        capture.capture(f"{fixture_server}/normal?token=private#section", 800, 600)
    )
    assert evidence.outcome == "completed"
    assert evidence.page_title == "Normal fixture"
    assert evidence.requested_url.endswith("?token=%5Bredacted%5D")
    assert evidence.final_url.endswith("?token=%5Bredacted%5D")
    assert evidence.viewport.width == 800
    assert evidence.document.visible_width == 800
    assert evidence.screenshot_ref is not None
    assert (capture._storage._directory.parent / evidence.screenshot_ref).is_file()


def test_capture_endpoint_returns_200_for_local_fixture(
    fixture_server, tmp_path, monkeypatch
):
    import app.main as main

    monkeypatch.setattr(
        main,
        "capture_service",
        BrowserCapture(
            storage=LocalScreenshotStorage(tmp_path),
            url_validator=LocalhostValidator(),
            navigation_timeout_ms=1_000,
            settling_period_ms=50,
        ),
    )
    monkeypatch.setattr(main, "url_validator", LocalhostValidator())
    with TestClient(main.app) as client:
        response = client.post(
            "/captures",
            json={
                "url": f"{fixture_server}/responsive-overflow",
                "accessibility_context": {
                    "representative_page_urls": [f"{fixture_server}/normal"],
                    "user_journeys": [
                        {
                            "name": "Review a page",
                            "page_urls": [f"{fixture_server}/normal"],
                        }
                    ],
                    "feature_presence": {"forms": True},
                    "feature_inventory_completed": True,
                    "answers": [
                        {
                            "question_id": "forms.error_identification",
                            "answer": "not_sure",
                            "explanation": "Please review validation behavior.",
                        }
                    ],
                },
            },
        )
    assert response.status_code == 200
    response_body = response.json()
    scoring = response_body["scoring"]
    assert scoring["scoring_configuration_version"] == "1.0.0"
    assert scoring["overall_score_type"] == "partial_audit_score"
    assert {dimension["dimension_id"] for dimension in scoring["dimensions"]} == {
        "accessibility",
        "responsive_quality",
        "functional_reliability",
        "technical_reliability",
        "visual_ux",
    }
    assert next(
        criterion
        for criterion in scoring["criteria"]
        if criterion["criterion_id"] == "functional.forms"
    )["status"] == "unsupported"
    viewports = response_body["viewports"]
    assert [item["name"] for item in viewports] == ["desktop", "tablet", "mobile"]
    assert [item["viewport"] for item in viewports] == [
        {"width": 1365, "height": 768},
        {"width": 768, "height": 1024},
        {"width": 390, "height": 844},
    ]
    assert all(item["capture_outcome"] == "completed" for item in viewports)
    assert all(item["screenshot_ref"] for item in viewports)
    assert all("horizontal_overflow" in item for item in viewports)
    assert all("overflow_analysis_status" in item for item in viewports)
    assert all("element_overflow_diagnosis" in item for item in viewports)
    assert all("functional_ux_audit" in item for item in viewports)
    assert all(item["functional_ux_audit"]["status"] == "available" for item in viewports)
    assert all("accessibility_scan" in item for item in viewports)
    assert all("technical_evidence" in item for item in viewports)
    assert all(item["accessibility_scan"]["status"] == "available" for item in viewports)
    assert all(item["accessibility_scan"]["axe_version"] == "4.14.0" for item in viewports)
    assert all("text_reflow_audit" in item for item in viewports)
    assert all(
        next(
            scenario for scenario in item["text_reflow_audit"]["scenarios"]
            if scenario["scenario_id"] == "orientation"
        )["criterion_ids"] == ["1.3.4"]
        for item in viewports
    )
    assert all(
        any(
            scenario["scenario_id"] == "text_spacing"
            and "1.4.12" in scenario["criterion_ids"]
            for scenario in item["text_reflow_audit"]["scenarios"]
        )
        for item in viewports
    )
    assert all("target_size_audit" in item for item in viewports)
    assert all(
        item["browser_feature_discovery"]["status"] == "available"
        for item in viewports
    )
    assert all(
        item["target_size_audit"]["status"] == "available" for item in viewports
    )
    assert all(
        next(
            scenario for scenario in item["text_reflow_audit"]["scenarios"]
            if scenario["scenario_id"] == "browser_zoom_200_percent"
        )["status"] == "unsupported"
        for item in viewports
    )
    assert all(
        next(
            scenario for scenario in item["text_reflow_audit"]["scenarios"]
            if scenario["scenario_id"] == "baseline"
        )["screenshot_ref"] == item["screenshot_ref"]
        for item in viewports
    )
    assert all("keyboard_focus_audit" in item for item in viewports)
    assert all(
        item["keyboard_focus_audit"]["status"] in {
            "available", "partial", "unavailable", "not_tested"
        }
        for item in viewports
    )
    assert all("finding_normalization" in item for item in viewports)
    audit_findings = response.json()["audit_findings"]
    assert audit_findings["status"] == "available"
    assert len(audit_findings["findings"]) == 1
    assert audit_findings["findings"][0]["selector"] == "#oversized"
    assert audit_findings["findings"][0]["affected_viewports"] == [
        "tablet",
        "mobile",
    ]
    audit_summary = response.json()["audit_summary"]
    assert audit_summary["status"] == "available"
    assert audit_summary["horizontal_overflow_detected"] is True
    assert audit_summary["affected_viewports"] == ["tablet", "mobile"]
    assert [issue["selector"] for issue in audit_summary["issues"]] == [
        "#oversized"
    ]
    hybrid_evaluation = response.json()["hybrid_evaluation"]
    assert hybrid_evaluation["browser_discovery_status"] == "available"
    assert len(hybrid_evaluation["criteria"]) == 55
    assert any(
        criterion["status"] == "browser_observed"
        for criterion in hybrid_evaluation["criteria"]
    )
    assert all(
        criterion["compliance_conclusion"] is None
        for criterion in hybrid_evaluation["criteria"]
    )
    form_criterion = next(
        criterion
        for criterion in hybrid_evaluation["criteria"]
        if criterion["criterion_id"] == "3.3.1"
    )
    assert form_criterion["status"] == "owner_reported"
    assert form_criterion["manual_review_required"] is True
    assert form_criterion["owner_reported"][0]["question_id"] == "forms.error_identification"
    assert hybrid_evaluation["representative_page_urls"] == [
        f"{fixture_server}/normal"
    ]
    assert hybrid_evaluation["user_journeys"][0]["name"] == "Review a page"
    assert len({item["screenshot_ref"] for item in viewports}) == 3
    for item in viewports:
        screenshot_path = tmp_path / item["screenshot_ref"]
        assert screenshot_path.is_file()
        assert screenshot_path.stat().st_size > 0
    assert viewports[0]["finding_normalization"]["findings"] == []
    for viewport in viewports[1:]:
        element_finding = viewport["element_overflow_diagnosis"]["findings"][0]
        assert element_finding["layout_diagnosis_status"] == "available"
        assert element_finding["layout_evidence"]["computed_width"] == "900px"
        assert element_finding["layout_evidence"]["display_type"] == "block"
        finding = viewport["finding_normalization"]["findings"][0]
        assert finding["selector"] == "#oversized"
        assert finding["viewport_name"] == viewport["name"]
        assert finding["evidence_correlation"] == "direct_geometry_match"


def test_accessibility_questionnaire_api_exposes_conditional_questions_and_feature_labels():
    from app.main import app

    with TestClient(app) as client:
        response = client.get("/accessibility/questionnaire")
    assert response.status_code == 200
    payload = response.json()
    assert "Do not submit passwords" in payload["safety_notice"]
    assert "forms.error_identification" in {
        question["question_id"] for question in payload["conditional_questions"]
    }


def test_playwright_reflow_failure_preserves_results_and_closes_contexts(
    fixture_server, tmp_path, monkeypatch
):
    import app.capture.runner as runner
    import app.capture.responsive as responsive

    closed_resources = []
    original_close_resources = runner._close_resources

    async def track_resource_cleanup(page, context, browser):
        closed_resources.append((page, context, browser))
        return await original_close_resources(page, context, browser)

    original_keyboard_audit = responsive.audit_keyboard_focus

    async def cause_browser_evaluation_failure(page):
        result = await original_keyboard_audit(page)
        await page.evaluate(
            "window.getComputedStyle = () => { throw new Error('fixture failure'); }"
        )
        return result

    monkeypatch.setattr(runner, "_close_resources", track_resource_cleanup)
    monkeypatch.setattr(
        responsive, "audit_keyboard_focus", cause_browser_evaluation_failure
    )
    service = BrowserCapture(
        storage=LocalScreenshotStorage(tmp_path),
        url_validator=LocalhostValidator(),
        settling_period_ms=25,
    )
    results = asyncio.run(
        responsive.capture_responsive_viewports(
            f"{fixture_server}/normal", service.capture
        )
    )

    assert len(results) == 3
    assert all(result.capture_outcome == "completed" for result in results)
    assert all(result.screenshot_ref for result in results)
    assert all(result.overflow_analysis_status == "available" for result in results)
    assert all(result.accessibility_scan.status == "available" for result in results)
    assert all(result.text_reflow_audit.status == "unavailable" for result in results)
    assert len(closed_resources) == 3
    assert all(page.is_closed() for page, _context, _browser in closed_resources)
    assert all(not browser.is_connected() for _page, _context, browser in closed_resources)


def test_responsive_pipeline_analyzes_local_overflow_fixture(capture, fixture_server):
    results = asyncio.run(
        capture_responsive_viewports(
            f"{fixture_server}/responsive-overflow",
            capture.capture,
            destination_validator=LocalhostValidator(),
        )
    )

    assert [
        (result.name, result.viewport.width, result.viewport.height)
        for result in results
    ] == [
        ("desktop", 1365, 768),
        ("tablet", 768, 1024),
        ("mobile", 390, 844),
    ]

    for result in results:
        assert result.capture_outcome == "completed", result.details
        assert result.overflow_analysis_status == "available"
        assert result.element_overflow_diagnosis.status == "available"
        assert result.finding_normalization.status == "available"
        assert result.horizontal_overflow is not None
        assert result.horizontal_overflow.overflow_px == (
            result.horizontal_overflow.scroll_width
            - result.horizontal_overflow.visible_width
        )
        assert result.horizontal_overflow.potential_horizontal_overflow is (
            result.horizontal_overflow.scroll_width
            > result.horizontal_overflow.visible_width
        )
        assert result.screenshot_ref is not None
        screenshot_path = capture._storage._directory.parent / result.screenshot_ref
        assert screenshot_path.is_file()
        assert screenshot_path.stat().st_size > 0

    assert results[0].horizontal_overflow.potential_horizontal_overflow is False
    assert results[1].horizontal_overflow.potential_horizontal_overflow is True
    assert results[2].horizontal_overflow.potential_horizontal_overflow is True
    assert results[0].element_overflow_diagnosis.findings == []
    for result in results[1:]:
        findings = result.element_overflow_diagnosis.findings
        assert len(findings) == 1
        assert findings[0].selector == "#oversized"
        assert findings[0].viewport_width == result.viewport.width
        assert findings[0].layout_diagnosis_status == "available"
        assert findings[0].layout_evidence.computed_width == "900px"
        normalized = result.finding_normalization.findings
        assert len(normalized) == 1
        assert normalized[0].selector == "#oversized"
        assert normalized[0].viewport_name == result.name
        assert normalized[0].evidence_correlation == "direct_geometry_match"


def test_functional_ux_audit_checks_links_and_images_locally(
    capture, fixture_server
):
    results = asyncio.run(
        capture_responsive_viewports(
            f"{fixture_server}/functional-ux",
            capture.capture,
            destination_validator=BlocksTestExternalHost(),
        )
    )

    from app.main import ResponsiveCaptureResponse

    response = ResponsiveCaptureResponse.from_results(
        f"{fixture_server}/functional-ux", results
    )
    serialized_audit = response.model_dump()["viewports"][0]["functional_ux_audit"]
    assert serialized_audit["findings"]
    assert serialized_audit["inconclusive"]

    for viewport in results:
        audit = viewport.functional_ux_audit
        assert audit.status == "partial"
        assert audit.checked_links == 7
        assert audit.checked_images == 2
        observed = {
            (finding.rule_id, finding.element_selector): finding
            for finding in audit.findings
        }
        broken = observed[("broken_link", "#broken-link")]
        assert broken.failure_category == "http_error"
        assert broken.status == "observed_failure"
        assert broken.accessible_label == "Broken destination"

        assert ("broken_link", "#redirect-link") not in observed
        assert ("broken_link", "#successful-link") not in observed
        assert ("failed_image", "#successful-image") not in observed

        inconclusive = {
            finding.element_selector: finding for finding in audit.inconclusive
        }
        assert inconclusive["#slow-link"].failure_category == "timeout"
        assert inconclusive["#private-link"].failure_category == "blocked_destination"
        assert inconclusive["#unsafe-redirect"].failure_category == "blocked_destination"
        assert observed[("broken_link", "#network-link")].failure_category == "network_failure"
        assert inconclusive["#empty-source"].failure_category == "missing_source"
        assert ("failed_image", "#missing-source") in observed
        assert observed[("failed_image", "#missing-source")].failure_category == "missing_source"
        assert ("failed_image", "#broken-image") in observed
        assert observed[("failed_image", "#broken-image")].failure_category == "resource_load_failure"
        assert "#decorative-empty" not in {
            finding.element_selector for finding in audit.inconclusive + audit.findings
        }


def test_accessibility_scan_preserves_axe_results_and_specific_evidence(
    capture, fixture_server
):
    from app.analyzers.accessibility import scan_accessibility
    from app.analyzers.accessibility import WCAG_AA_TAGS

    scans = []
    tagged_criteria = []

    async def run_scan():
        async def scan_live_page(page):
            scans.append(await scan_accessibility(page))
            tagged_criteria.extend(
                await page.evaluate(
                    """tags => [...new Set(
                        axe.getRules(tags)
                            .filter(rule => rule.enabled)
                            .flatMap(rule => rule.tags)
                            .filter(tag => /^wcag\\d{3,4}$/.test(tag))
                    )].sort()""",
                    list(WCAG_AA_TAGS),
                )
            )

        evidence = await capture.capture(
            f"{fixture_server}/accessibility",
            1365,
            768,
            page_callback=scan_live_page,
        )
        return evidence

    evidence = asyncio.run(run_scan())
    assert evidence.outcome == "completed"
    assert len(scans) == 1
    result = scans[0]
    assert result.status == "available", result.details
    assert result.axe_version == "4.14.0"
    assert tagged_criteria == [
        "wcag111",
        "wcag122",
        "wcag131",
        "wcag135",
        "wcag141",
        "wcag1412",
        "wcag142",
        "wcag143",
        "wcag144",
        "wcag211",
        "wcag213",
        "wcag221",
        "wcag222",
        "wcag241",
        "wcag242",
        "wcag244",
        "wcag253",
        "wcag311",
        "wcag312",
        "wcag332",
        "wcag412",
    ]
    assert result.inapplicable
    assert result.incomplete
    assert result.passes
    assert result.non_text_contrast.status == "partial"

    violations = {rule.rule_id: rule for rule in result.violations}
    assert "label" in violations
    assert any(
        "#unlabeled-input" in node.target
        for node in violations["label"].nodes
    )
    assert "button-name" in violations
    assert any(
        "#unnamed-button" in node.target
        for node in violations["button-name"].nodes
    )
    assert "aria-required-parent" in violations
    assert any(
        "#orphaned-listitem" in node.target
        for node in violations["aria-required-parent"].nodes
    )
    assert "image-alt" in violations
    assert any("#missing-alt" in node.target for node in violations["image-alt"].nodes)
    assert not any(
        "#subjective-alt" in node.target
        for node in violations["image-alt"].nodes
    )
    contrast = {
        rule.rule_id: rule for rule in result.incomplete
    }["color-contrast"]
    assert any("#low-contrast" in node.target for node in contrast.nodes)
    assert any(node.failure_summary for node in contrast.nodes)
    assert all(rule.impact for rule in result.violations)
    assert all(rule.help_url.startswith("https://") for rule in result.violations)
    assert all(rule.tags for rule in result.violations)
    assert all(
        node.html and node.target
        for rule in result.violations
        for node in rule.nodes
    )


    unlabeled_node = next(
        node
        for node in violations["label"].nodes
        if "#unlabeled-input" in node.target
    )
    assert "[redacted]" in unlabeled_node.html
    assert "fixture-secret" not in unlabeled_node.html
    assert violations["label"].description
    assert violations["label"].help
    assert any(
        rule.rule_id == "label"
        and any("#valid-input" in node.target for node in rule.nodes)
        for rule in result.passes
    )
    assert any(
        rule.rule_id == "image-alt"
        and any("#valid-image" in node.target for node in rule.nodes)
        for rule in result.passes
    )
    assert any(
        rule.rule_id == "color-contrast"
        and any("#sufficient-contrast" in node.target for node in rule.nodes)
        for rule in result.passes
    )
    assert any(
        any(tag == "wcag111" for tag in rule.tags)
        for rule in result.violations
    )
    assert "complete" not in result.status

    from app.main import ResponsiveCaptureResponse
    from app.capture.responsive import (
        ElementOverflowDiagnosisResult,
        FindingNormalizationResult,
        ViewportCaptureResult,
    )
    from app.capture.models import ViewportDimensions

    api_result = ViewportCaptureResult(
        name="desktop",
        viewport=ViewportDimensions(1365, 768),
        capture_outcome=evidence.outcome,
        horizontal_overflow=None,
        overflow_analysis_status="missing_dimensions",
        screenshot_ref=evidence.screenshot_ref,
        element_overflow_diagnosis=ElementOverflowDiagnosisResult(
            status="not_attempted"
        ),
        finding_normalization=FindingNormalizationResult(
            status="not_attempted"
        ),
        accessibility_scan=result,
    )
    serialized = ResponsiveCaptureResponse.from_results(
        evidence.requested_url, [api_result]
    ).model_dump()["viewports"][0]["accessibility_scan"]
    assert serialized["violations"][0]["nodes"][0]["target"]
    assert serialized["violations"][0]["tags"]
    assert serialized["non_text_contrast"]["status"] == "partial"
    assert all(
        collection in serialized
        for collection in ("violations", "incomplete", "passes", "inapplicable")
    )
    assert serialized["non_text_contrast"]["status"] == "partial"


@pytest.mark.parametrize(
    ("path", "expected_low_contrast"),
    [
        ("non-text-contrast", True),
        ("non-text-contrast-adequate", False),
    ],
)
def test_non_text_contrast_reports_solid_color_candidates_for_review(
    capture, fixture_server, path, expected_low_contrast
):
    from app.analyzers.accessibility import scan_accessibility

    scans = []

    async def run_scan():
        async def scan_live_page(page):
            scans.append(await scan_accessibility(page))

        return await capture.capture(
            f"{fixture_server}/{path}",
            800,
            600,
            page_callback=scan_live_page,
        )

    evidence = asyncio.run(run_scan())
    assert evidence.outcome == "completed"
    assert len(scans) == 1
    result = scans[0]
    audit = result.non_text_contrast

    assert audit.status == "partial"
    assert audit.inspected_components > 0
    assert all(finding.classification == "needs_review" for finding in audit.findings)
    assert all(
        finding.potential_issue_detected
        and not finding.confirmed_violation
        and finding.manual_review_required
        for finding in audit.findings
    )
    if expected_low_contrast:
        findings = {finding.selector: finding for finding in audit.findings}
        assert "#low-boundary" in findings
        assert any(
            pair["contrast_ratio"] < pair["required_ratio"]
            for pair in findings["#low-boundary"].color_pairs
        )
        assert "#low-circle" in findings
        assert findings["#low-circle"].color_pairs[0]["visual_part"] == "svg_fill"
        assert "#high-boundary" not in findings
        assert "#high-circle" not in findings
        assert "#hidden-control" not in findings
        assert audit.inspected_graphics == 2
        assert any("were not pixel-sampled" in item for item in audit.details)
        assert all(
            finding.limitations for finding in audit.findings
        )
    else:
        assert audit.findings == []
        assert audit.inspected_graphics == 0
        assert any("not a pass" in item for item in audit.details)


def test_target_size_audit_reports_small_visible_target_for_review(
    capture, fixture_server
):
    from app.analyzers.target_size import audit_target_size

    scans = []

    async def run_scan():
        async def scan_live_page(page):
            scans.append(await audit_target_size(page))

        return await capture.capture(
            f"{fixture_server}/target-size-small",
            800,
            600,
            page_callback=scan_live_page,
        )

    evidence = asyncio.run(run_scan())
    assert evidence.outcome == "completed"
    assert scans[0].status == "available"
    assert scans[0].inspected_targets == 2
    assert [finding.selector for finding in scans[0].findings] == ["#small-target"]
    finding = scans[0].findings[0]
    assert finding.criterion_id == "2.5.8"
    assert finding.width_css_px == 16
    assert finding.height_css_px == 16
    assert finding.accessible_name == "Small link"
    assert finding.classification == "needs_review"
    assert "exceptions are not evaluated" in scans[0].details[0]


def test_target_size_audit_does_not_flag_adequate_target(capture, fixture_server):
    from app.analyzers.target_size import audit_target_size

    scans = []

    async def run_scan():
        async def scan_live_page(page):
            scans.append(await audit_target_size(page))

        return await capture.capture(
            f"{fixture_server}/target-size-adequate",
            800,
            600,
            page_callback=scan_live_page,
        )

    evidence = asyncio.run(run_scan())
    assert evidence.outcome == "completed"
    assert scans[0].status == "available"
    assert scans[0].inspected_targets == 1
    assert scans[0].findings == []


def _run_keyboard_audit(fixture_server, path):
    async def run():
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            try:
                page = await browser.new_page(viewport={"width": 800, "height": 600})
                await page.goto(f"{fixture_server}/{path}", wait_until="domcontentloaded")
                return await audit_keyboard_focus(page)
            finally:
                await browser.close()

    return asyncio.run(run())


def _run_text_reflow_audit(
    fixture_server,
    path,
    *,
    width=1365,
    height=768,
    viewport_name="test",
    capture_id=None,
    capture_screenshot=None,
):
    async def run():
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            try:
                page = await browser.new_page(viewport={"width": width, "height": height})
                await page.goto(f"{fixture_server}/{path}", wait_until="domcontentloaded")
                if path == "text-reflow-dynamic":
                    await page.wait_for_timeout(300)
                return await audit_text_reflow(
                    page,
                    baseline_width=width,
                    baseline_height=height,
                    viewport_name=viewport_name,
                    capture_id=capture_id,
                    capture_screenshot=capture_screenshot,
                )
            finally:
                await browser.close()

    return asyncio.run(run())


def _scenario_screenshot_capture(storage):
    screenshot_capture_service = BrowserCapture(
        storage=storage,
        url_validator=LocalhostValidator(),
        settling_period_ms=0,
    )
    return screenshot_capture_service.save_scenario_screenshot


def test_text_reflow_usable_fixture_has_no_detected_clipping(fixture_server):
    result = _run_text_reflow_audit(fixture_server, "text-reflow-usable")
    text_scenario = next(
        scenario for scenario in result.scenarios
        if scenario.scenario_id == "text_200_percent"
    )

    assert result.status == "partial"
    assert text_scenario.status == "completed"
    assert text_scenario.classification == "no_violation_detected"
    assert text_scenario.criterion_ids == ["1.4.4"]
    assert text_scenario.measurement.window_inner_width == 1365
    assert text_scenario.baseline_measurement.window_inner_width == 1365


def test_text_reflow_clipped_text_requires_availability_review(fixture_server):
    result = _run_text_reflow_audit(fixture_server, "text-reflow-clipped")
    scenario = next(
        scenario for scenario in result.scenarios
        if scenario.scenario_id == "text_200_percent"
    )

    assert scenario.classification == "needs_review"
    finding = next(
        finding for finding in scenario.findings
        if finding.selector == "#clipped"
    )
    assert finding.criterion_id == "1.4.4"
    assert finding.level == "AA"
    assert finding.classification == "needs_review"
    assert finding.confidence == "medium"
    assert finding.evidence["fontSize"] == "32px"
    assert finding.evidence["scrollHeight"] > finding.evidence["clientHeight"]
    assert finding.evidence["text_availability"] == "not_evaluated"
    assert finding.baseline_evidence["fontSize"] == "16px"


def test_text_reflow_reports_box_overlap_without_claiming_obscuration(fixture_server):
    result = _run_text_reflow_audit(fixture_server, "text-reflow-overlap")
    scenario = next(
        scenario for scenario in result.scenarios
        if scenario.scenario_id == "text_200_percent"
    )

    assert scenario.classification == "needs_review"
    overlap = next(
        finding for finding in scenario.findings
        if "overlap" in finding.observation
    )
    assert overlap.evidence["overlapHeight"] > 0
    assert "requires review" in overlap.observation
    assert all(finding.classification != "violation" for finding in scenario.findings)


def _text_spacing_scenario(result):
    return next(
        scenario for scenario in result.scenarios
        if scenario.scenario_id == "text_spacing"
    )


def test_text_spacing_usable_fixture_has_no_detected_geometry_issue(fixture_server):
    scenario = _text_spacing_scenario(
        _run_text_reflow_audit(fixture_server, "text-spacing-usable")
    )

    assert scenario.status == "completed"
    assert scenario.criterion_ids == ["1.4.12"]
    assert scenario.classification == "no_violation_detected"
    assert scenario.findings == []
    assert scenario.measurement.viewport_width == 1365


def _hover_focus_scenario(result):
    return next(
        scenario for scenario in result.scenarios
        if scenario.scenario_id == "hover_focus_content"
    )


def test_hover_focus_compliant_tooltip_records_behavior_and_restores_focus(
    fixture_server,
):
    screenshot_calls = []

    async def run():
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            try:
                page = await browser.new_page(viewport={"width": 800, "height": 600})
                await page.goto(
                    f"{fixture_server}/hover-focus-compliant",
                    wait_until="domcontentloaded",
                )
                await page.locator("#help").focus()

                async def capture_visible_tooltip(
                    screenshot_page, capture_id, viewport_name, scenario_id, width, height
                ):
                    screenshot_calls.append(
                        (
                            scenario_id,
                            await screenshot_page.locator("#tip").is_visible(),
                            width,
                            height,
                        )
                    )
                    return "hover-focus.png"

                result = await audit_text_reflow(
                    page,
                    baseline_width=800,
                    baseline_height=600,
                    capture_screenshot=capture_visible_tooltip,
                )
                restored_focus = await page.evaluate(
                    "() => document.activeElement?.id"
                )
                return result, restored_focus
            finally:
                await browser.close()

    result, restored_focus = asyncio.run(run())
    scenario = _hover_focus_scenario(result)
    hover = next(
        finding for finding in scenario.findings
        if finding.evidence["interaction"] == "hover"
    )
    focus = next(
        finding for finding in scenario.findings
        if finding.evidence["interaction"] == "focus"
    )

    assert scenario.criterion_ids == ["1.4.13"]
    assert scenario.classification == "needs_review"
    assert hover.selector == "#help"
    assert hover.evidence["content_selector"] == "#tip"
    assert hover.evidence["pointer_entered_content_remained_visible"] is True
    assert hover.evidence["visible_after_pointer_left_trigger_and_content"] is False
    assert hover.evidence["escape_dismissed_content"] is True
    assert hover.evidence["potential_issue_detected"] is False
    assert hover.evidence["confirmed_violation"] is False
    assert hover.evidence["manual_review_required"] is True
    assert focus.evidence["escape_dismissed_content"] is True
    assert hover.evidence["viewport"] == {"width": 800, "height": 600}
    assert hover.evidence["content_geometry"]["width"] > 0
    assert scenario.screenshot_ref == "hover-focus.png"
    assert hover.screenshot_ref == "hover-focus.png"
    assert (
        "hover_focus_content",
        True,
        800,
        600,
    ) in screenshot_calls
    assert restored_focus == "help"


def test_hover_focus_reports_content_that_pointer_cannot_enter(fixture_server):
    scenario = _hover_focus_scenario(
        _run_text_reflow_audit(fixture_server, "hover-focus-not-hoverable")
    )
    hover = next(
        finding for finding in scenario.findings
        if finding.evidence["interaction"] == "hover"
    )

    assert scenario.classification == "needs_review"
    assert hover.evidence["pointer_entered_content_remained_visible"] is False
    assert hover.evidence["potential_issue_detected"] is True
    assert hover.evidence["content_selector"] == "#tip"


def test_hover_focus_reports_undismissable_overlapping_focus_content(fixture_server):
    scenario = _hover_focus_scenario(
        _run_text_reflow_audit(fixture_server, "hover-focus-undismissable")
    )
    focus = next(
        finding for finding in scenario.findings
        if finding.evidence["interaction"] == "focus"
    )

    assert scenario.classification == "needs_review"
    assert focus.evidence["content_selector"] == "#dialog"
    assert focus.evidence["potentially_overlapped_content"]
    assert focus.evidence["dismissibility_required_by_overlap_heuristic"] is True
    assert focus.evidence["escape_dismissed_content"] is False
    assert focus.evidence["potential_issue_detected"] is True
    assert focus.classification == "needs_review"


def test_hover_focus_ignores_style_only_hover_changes(fixture_server):
    scenario = _hover_focus_scenario(
        _run_text_reflow_audit(fixture_server, "hover-focus-style-only")
    )

    assert scenario.status == "completed"
    assert scenario.classification == "no_violation_detected"
    assert scenario.findings == []
    assert any("No new visible DOM content" in item for item in scenario.details)


def _orientation_scenario(result):
    return next(
        scenario for scenario in result.scenarios
        if scenario.scenario_id == "orientation"
    )


def test_orientation_flexible_fixture_preserves_content_and_restores_viewport(
    fixture_server,
):
    async def run():
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            try:
                page = await browser.new_page(viewport={"width": 390, "height": 844})
                await page.goto(
                    f"{fixture_server}/orientation-flexible",
                    wait_until="domcontentloaded",
                )
                result = await audit_text_reflow(
                    page, baseline_width=390, baseline_height=844
                )
                return result, page.viewport_size
            finally:
                await browser.close()

    result, restored_viewport = asyncio.run(run())
    scenario = _orientation_scenario(result)

    assert scenario.status == "completed"
    assert scenario.criterion_ids == ["1.3.4"]
    assert scenario.classification == "no_violation_detected"
    assert scenario.findings == []
    assert scenario.baseline_measurement.viewport_width == 390
    assert scenario.baseline_measurement.viewport_height == 844
    assert scenario.measurement.viewport_width == 844
    assert scenario.measurement.viewport_height == 390
    assert restored_viewport == {"width": 390, "height": 844}
    assert any("does not emulate physical device rotation" in item for item in scenario.details)


def test_orientation_reports_content_and_control_changes_for_manual_review(
    fixture_server,
):
    scenario = _orientation_scenario(
        _run_text_reflow_audit(fixture_server, "orientation-restricted")
    )
    findings = {finding.selector: finding for finding in scenario.findings}

    assert scenario.classification == "needs_review"
    assert findings["#portrait-only"].evidence["orientation_change"] == (
        "not_visible_in_landscape"
    )
    assert findings["#landscape-only"].evidence["orientation_change"] == (
        "not_visible_in_portrait"
    )
    assert findings["#portrait-details"].evidence["orientation_change"] == (
        "not_visible_in_landscape"
    )
    assert findings["#landscape-details"].evidence["orientation_change"] == (
        "not_visible_in_portrait"
    )
    assert all(
        finding.classification == "needs_review"
        and finding.evidence["potential_issue_detected"] is True
        and finding.evidence["confirmed_violation"] is False
        and finding.evidence["manual_review_required"] is True
        and finding.evidence["exception_essentiality_evaluated"] is False
        for finding in scenario.findings
    )


def test_text_spacing_reports_fixed_height_clipping_for_review(fixture_server):
    scenario = _text_spacing_scenario(
        _run_text_reflow_audit(fixture_server, "text-spacing-clipped")
    )
    finding = next(
        finding for finding in scenario.findings
        if finding.selector == "#clipped"
    )

    assert scenario.classification == "needs_review"
    assert finding.criterion_id == "1.4.12"
    assert finding.classification == "needs_review"
    assert "possible_text_clipping" in finding.evidence["observations"]
    assert finding.evidence["viewport"] == {"width": 1365, "height": 768}
    assert finding.evidence["geometry"]["height"] > 0
    assert finding.evidence["applied_spacing"]["lineHeight"] == "24px"
    assert finding.evidence["applied_spacing"]["letterSpacing"] == "1.92px"
    assert finding.evidence["applied_spacing"]["wordSpacing"] == "2.56px"
    assert finding.evidence["applied_spacing"]["paragraphSpacing"] == "32px"
    assert finding.baseline_evidence["container_measurements"]["scrollHeight"] <= (
        finding.baseline_evidence["container_measurements"]["clientHeight"] + 1
    )


def test_text_spacing_reports_new_overlap_without_claiming_violation(fixture_server):
    scenario = _text_spacing_scenario(
        _run_text_reflow_audit(fixture_server, "text-spacing-overlap")
    )

    assert scenario.classification == "needs_review"
    overlap = next(
        finding for finding in scenario.findings
        if "overlap" in finding.observation
    )
    assert overlap.criterion_id == "1.4.12"
    assert overlap.classification == "needs_review"
    assert overlap.evidence["overlapHeight"] > 0
    assert overlap.evidence["viewport"] == {"width": 1365, "height": 768}


def test_text_spacing_reports_control_label_clipping_for_review(fixture_server):
    scenario = _text_spacing_scenario(
        _run_text_reflow_audit(fixture_server, "text-spacing-control")
    )

    assert scenario.classification == "needs_review"
    finding = next(
        finding for finding in scenario.findings
        if finding.selector == "#submit"
    )
    assert "possible_text_clipping" in finding.evidence["observations"]
    assert finding.evidence["geometry"]["width"] == 180
    assert finding.classification == "needs_review"


def test_text_spacing_reports_control_obscured_after_content_reflows(fixture_server):
    scenario = _text_spacing_scenario(
        _run_text_reflow_audit(
            fixture_server, "text-spacing-obscured-control"
        )
    )
    finding = next(
        finding for finding in scenario.findings
        if finding.selector == "#continue"
    )

    assert scenario.classification == "needs_review"
    assert finding.observation.startswith("A control had more sampled hit-test")
    assert finding.evidence["total_hit_samples"] > 0
    assert finding.evidence["occluded_samples"] > 0
    assert finding.evidence["viewport"] == {"width": 1365, "height": 768}
    assert finding.evidence["geometry"]["width"] > 0


def test_text_spacing_keeps_scrollable_region_as_review_not_failure(fixture_server):
    scenario = _text_spacing_scenario(
        _run_text_reflow_audit(fixture_server, "text-spacing-scrollable")
    )

    assert scenario.classification == "needs_review"
    finding = next(
        finding for finding in scenario.findings
        if finding.selector == "#long-content"
    )
    assert finding.evidence["container_measurements"]["scrollContainer"] == (
        "#scroll-region"
    )
    assert finding.classification == "needs_review"
    assert "scrollable container" in " ".join(scenario.details)


def test_text_spacing_overrides_restore_after_screenshot_failure(fixture_server):
    async def run():
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            try:
                page = await browser.new_page(viewport={"width": 800, "height": 600})
                await page.goto(
                    f"{fixture_server}/text-spacing-clipped",
                    wait_until="domcontentloaded",
                )
                original = await page.locator("#clipped").evaluate(
                    """element => ({
                        lineHeight: element.style.getPropertyValue("line-height"),
                        lineHeightPriority: element.style.getPropertyPriority("line-height"),
                        marginBottom: element.style.getPropertyValue("margin-bottom"),
                        marginBottomPriority: element.style.getPropertyPriority("margin-bottom"),
                        letterSpacing: element.style.getPropertyValue("letter-spacing"),
                        letterSpacingPriority: element.style.getPropertyPriority("letter-spacing"),
                        wordSpacing: element.style.getPropertyValue("word-spacing"),
                        wordSpacingPriority: element.style.getPropertyPriority("word-spacing")
                    })"""
                )

                async def fail_screenshot(
                    screenshot_page, *_args, **_kwargs
                ):
                    observed = await screenshot_page.locator("#clipped").evaluate(
                        """element => ({
                            lineHeight: getComputedStyle(element).lineHeight,
                            letterSpacing: getComputedStyle(element).letterSpacing,
                            wordSpacing: getComputedStyle(element).wordSpacing
                        })"""
                    )
                    assert observed == {
                        "lineHeight": "24px",
                        "letterSpacing": "1.92px",
                        "wordSpacing": "2.56px",
                    }
                    raise OSError("screenshot storage unavailable")

                result = await audit_text_reflow(
                    page,
                    baseline_width=800,
                    baseline_height=600,
                    capture_screenshot=fail_screenshot,
                )
                restored = await page.locator("#clipped").evaluate(
                    """element => ({
                        lineHeight: element.style.getPropertyValue("line-height"),
                        lineHeightPriority: element.style.getPropertyPriority("line-height"),
                        marginBottom: element.style.getPropertyValue("margin-bottom"),
                        marginBottomPriority: element.style.getPropertyPriority("margin-bottom"),
                        letterSpacing: element.style.getPropertyValue("letter-spacing"),
                        letterSpacingPriority: element.style.getPropertyPriority("letter-spacing"),
                        wordSpacing: element.style.getPropertyValue("word-spacing"),
                        wordSpacingPriority: element.style.getPropertyPriority("word-spacing")
                    })"""
                )
                return result, original, restored
            finally:
                await browser.close()

    result, original, restored = asyncio.run(run())
    scenario = _text_spacing_scenario(result)
    assert original == restored
    assert any("screenshot capture failed" in item for item in scenario.details)
    assert all(finding.classification == "needs_review" for finding in scenario.findings)


def test_text_reflow_flags_320px_overflow_for_review(fixture_server):
    result = _run_text_reflow_audit(fixture_server, "text-reflow-wide")
    scenario = next(
        scenario for scenario in result.scenarios
        if scenario.scenario_id == "reflow_320_css_px"
    )

    assert scenario.status == "completed"
    assert scenario.viewport_width == 320
    assert scenario.measurement.window_inner_width == 320
    assert scenario.baseline_measurement.window_inner_width == 1365
    assert scenario.measurement.document_horizontal_overflow_px > 0
    assert scenario.classification == "needs_review"
    assert scenario.findings[0].criterion_id == "1.4.10"
    assert all(finding.classification != "violation" for finding in scenario.findings)


def test_text_reflow_does_not_fail_legitimate_table_scrolling(fixture_server):
    result = _run_text_reflow_audit(fixture_server, "text-reflow-table")
    scenario = next(
        scenario for scenario in result.scenarios
        if scenario.scenario_id == "reflow_320_css_px"
    )

    assert scenario.classification == "needs_review"
    assert scenario.findings
    assert all(
        finding.evidence["twoDimensionalRegion"] == "#data-table"
        for finding in scenario.findings
    )
    assert any(
        scenario.scenario_id == "reflow_256_css_px_height"
        for scenario in result.scenarios
    )


def test_text_reflow_reports_unbreakable_text_overflow(fixture_server):
    result = _run_text_reflow_audit(fixture_server, "text-reflow-unbreakable")
    scenario = next(
        scenario for scenario in result.scenarios
        if scenario.scenario_id == "reflow_320_css_px"
    )

    assert scenario.classification == "needs_review"
    assert scenario.findings[0].criterion_id == "1.4.10"
    evidence = scenario.findings[0].evidence
    assert (
        evidence["right"] > 320
        or evidence["scrollWidth"] > evidence["clientWidth"]
    )


def test_text_reflow_uses_post_load_dynamic_content(fixture_server):
    result = _run_text_reflow_audit(fixture_server, "text-reflow-dynamic")
    baseline = result.scenarios[0]

    assert baseline.status == "completed"
    assert baseline.measurement.inspected_text_elements == 1
    assert next(
        scenario for scenario in result.scenarios
        if scenario.scenario_id == "browser_zoom_200_percent"
    ).status == "unsupported"


def test_text_reflow_ellipsis_disclosure_and_nested_sizes_need_review(fixture_server):
    result = _run_text_reflow_audit(fixture_server, "text-reflow-review")
    scenario = next(
        scenario for scenario in result.scenarios
        if scenario.scenario_id == "text_200_percent"
    )
    findings = {finding.selector: finding for finding in scenario.findings}

    assert findings["#ellipsis"].classification == "needs_review"
    assert findings["#ellipsis"].evidence["text_availability"] == "not_evaluated"
    assert findings["#disclosed"].classification == "needs_review"
    assert findings["#disclosed"].evidence["text_availability"] == "not_evaluated"
    assert findings["#nested"].evidence["fontSize"] == "45px"
    assert all(finding.classification != "violation" for finding in findings.values())


def test_suspicious_text_scenario_shares_one_screenshot_and_preserves_baseline(
    fixture_server, tmp_path
):
    storage = LocalScreenshotStorage(tmp_path)
    baseline_ref = storage.save(b"baseline screenshot")
    baseline_path = tmp_path / baseline_ref
    baseline_bytes = baseline_path.read_bytes()
    save_screenshot = _scenario_screenshot_capture(storage)
    saved_scenarios = []

    async def record_screenshot(
        page, capture_id, viewport_name, scenario_id, width, height
    ):
        saved_scenarios.append((viewport_name, scenario_id))
        return await save_screenshot(
            page,
            capture_id=capture_id,
            viewport_name=viewport_name,
            scenario_id=scenario_id,
            width=width,
            height=height,
        )

    result = _run_text_reflow_audit(
        fixture_server,
        "text-reflow-review",
        viewport_name="desktop",
        capture_id="capture01",
        capture_screenshot=record_screenshot,
    )
    scenario = next(
        item for item in result.scenarios if item.scenario_id == "text_200_percent"
    )

    assert len(scenario.findings) > 1
    assert scenario.screenshot_ref is not None
    assert {finding.screenshot_ref for finding in scenario.findings} == {
        scenario.screenshot_ref
    }
    assert saved_scenarios.count(("desktop", "text_200_percent")) == 1
    screenshot_path = tmp_path / scenario.screenshot_ref
    image = screenshot_path.read_bytes()
    assert image[:8] == b"\x89PNG\r\n\x1a\n"
    assert struct.unpack(">II", image[16:24]) == (1365, 768)
    assert "scenario_capture01_desktop_text_200_percent_1365x768.png" in str(
        screenshot_path
    )
    assert baseline_path.read_bytes() == baseline_bytes


def test_text_reflow_measurements_do_not_require_screenshot_capture(fixture_server):
    result = _run_text_reflow_audit(fixture_server, "text-reflow-clipped")
    scenario = next(
        item for item in result.scenarios if item.scenario_id == "text_200_percent"
    )

    assert scenario.status == "completed"
    assert scenario.measurement is not None
    assert scenario.findings
    assert scenario.screenshot_ref is None
    assert all(finding.screenshot_ref is None for finding in scenario.findings)

    screenshot_calls = []

    async def record_screenshot(*args, **kwargs):
        screenshot_calls.append((args, kwargs))
        return "unexpected.png"

    usable_result = _run_text_reflow_audit(
        fixture_server,
        "text-reflow-usable",
        capture_screenshot=record_screenshot,
    )
    usable_scenario = next(
        item for item in usable_result.scenarios
        if item.scenario_id == "text_200_percent"
    )
    assert usable_scenario.measurement is not None
    assert usable_scenario.findings == []
    assert usable_scenario.screenshot_ref is None
    assert screenshot_calls == []


def test_reflow_screenshots_match_320_and_applicable_256_viewports(
    fixture_server, tmp_path
):
    storage = LocalScreenshotStorage(tmp_path)
    save_screenshot = _scenario_screenshot_capture(storage)

    def run_with_screenshots(path, *, width, height, viewport_name):
        return _run_text_reflow_audit(
            fixture_server,
            path,
            width=width,
            height=height,
            viewport_name=viewport_name,
            capture_id=f"{viewport_name}scan",
            capture_screenshot=save_screenshot,
        )

    wide_result = run_with_screenshots(
        "text-reflow-wide",
        width=1365,
        height=768,
        viewport_name="desktop",
    )
    narrow_scenario = next(
        item for item in wide_result.scenarios
        if item.scenario_id == "reflow_320_css_px"
    )
    assert narrow_scenario.findings
    assert narrow_scenario.screenshot_ref is not None
    narrow_image = (tmp_path / narrow_scenario.screenshot_ref).read_bytes()
    assert struct.unpack(">II", narrow_image[16:24]) == (320, 768)
    assert all(
        finding.screenshot_ref == narrow_scenario.screenshot_ref
        for finding in narrow_scenario.findings
    )

    table_result = run_with_screenshots(
        "text-reflow-table",
        width=1365,
        height=768,
        viewport_name="tablet",
    )
    height_scenario = next(
        item for item in table_result.scenarios
        if item.scenario_id == "reflow_256_css_px_height"
    )
    if height_scenario.status == "completed" and height_scenario.findings:
        assert height_scenario.screenshot_ref is not None
        height_image = (tmp_path / height_scenario.screenshot_ref).read_bytes()
        assert struct.unpack(">II", height_image[16:24]) == (1365, 256)
        assert all(
            finding.screenshot_ref == height_scenario.screenshot_ref
            for finding in height_scenario.findings
        )
    else:
        assert height_scenario.screenshot_ref is None


def test_screenshot_failure_preserves_measurements_and_restores_page(
    fixture_server,
):
    async def fail_screenshot(*_args, **_kwargs):
        raise OSError("storage unavailable")

    async def run():
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            try:
                page = await browser.new_page(viewport={"width": 1365, "height": 768})
                await page.goto(
                    f"{fixture_server}/text-reflow-clipped",
                    wait_until="domcontentloaded",
                )
                original_styles = await page.locator("#clipped").evaluate(
                    """element => ({
                        value: element.style.getPropertyValue("font-size"),
                        priority: element.style.getPropertyPriority("font-size")
                    })"""
                )
                result = await audit_text_reflow(
                    page,
                    baseline_width=1365,
                    baseline_height=768,
                    viewport_name="desktop",
                    capture_screenshot=fail_screenshot,
                )
                restored_styles = await page.locator("#clipped").evaluate(
                    """element => ({
                        value: element.style.getPropertyValue("font-size"),
                        priority: element.style.getPropertyPriority("font-size")
                    })"""
                )
                await page.goto(
                    f"{fixture_server}/text-reflow-wide",
                    wait_until="domcontentloaded",
                )
                narrow_result = await audit_text_reflow(
                    page,
                    baseline_width=1365,
                    baseline_height=768,
                    viewport_name="desktop",
                    capture_screenshot=fail_screenshot,
                )
                return (
                    result,
                    narrow_result,
                    page.viewport_size,
                    original_styles,
                    restored_styles,
                )
            finally:
                await browser.close()

    (
        result,
        narrow_result,
        viewport_size,
        original_styles,
        restored_styles,
    ) = asyncio.run(run())
    scenario = next(
        item for item in result.scenarios if item.scenario_id == "text_200_percent"
    )
    narrow_scenario = next(
        item for item in narrow_result.scenarios
        if item.scenario_id == "reflow_320_css_px"
    )

    assert scenario.status == "completed"
    assert scenario.measurement is not None
    assert scenario.findings
    assert scenario.screenshot_ref is None
    assert any("screenshot capture failed (OSError)" in item for item in scenario.details)
    assert narrow_scenario.status == "completed"
    assert narrow_scenario.measurement is not None
    assert narrow_scenario.findings
    assert narrow_scenario.screenshot_ref is None
    assert any(
        "screenshot capture failed (OSError)" in item
        for item in narrow_scenario.details
    )
    assert viewport_size == {"width": 1365, "height": 768}
    assert restored_styles == original_styles


def test_text_reflow_disclosure_remains_operable_when_clipping_is_reported(
    fixture_server,
):
    async def verify_disclosure():
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            try:
                page = await browser.new_page(viewport={"width": 1365, "height": 768})
                await page.goto(
                    f"{fixture_server}/text-reflow-review",
                    wait_until="domcontentloaded",
                )
                accessible_link_count = await page.get_by_role(
                    "link",
                    name="The full text remains available to assistive technology",
                ).count()
                result = await audit_text_reflow(
                    page, baseline_width=1365, baseline_height=768
                )
                await page.locator("#full-disclosure summary").click()
                disclosed_text = await page.locator("#full-content").inner_text()
                return result, disclosed_text, accessible_link_count
            finally:
                await browser.close()

    result, disclosed_text, accessible_link_count = asyncio.run(verify_disclosure())
    scenario = next(
        scenario for scenario in result.scenarios
        if scenario.scenario_id == "text_200_percent"
    )

    assert "complete disclosure text" in disclosed_text
    assert accessible_link_count == 1
    assert any(
        finding.selector == "#disclosed"
        and finding.classification == "needs_review"
        for finding in scenario.findings
    )


def test_text_reflow_responsive_content_replacement_needs_review(fixture_server):
    result = _run_text_reflow_audit(fixture_server, "text-reflow-responsive")
    scenario = next(
        scenario for scenario in result.scenarios
        if scenario.scenario_id == "reflow_320_css_px"
    )

    assert scenario.classification == "needs_review"
    assert any(
        finding.selector == "#desktop-copy"
        and finding.evidence["visible_in_test"] is False
        for finding in scenario.findings
    )


def test_text_reflow_marks_viewport_resize_unsupported_without_page_support():
    class PageWithoutResize:
        async def evaluate(self, _expression, _argument):
            return {
                "viewport": {"width": 800, "height": 600},
                "document": {"scrollWidth": 800, "scrollHeight": 600},
                "inspectedTextElements": 0,
                "elements": [],
                "overflowBoundaries": [],
                "overlapPairs": [],
            }

    result = asyncio.run(
        audit_text_reflow(
            PageWithoutResize(), baseline_width=800, baseline_height=600
        )
    )
    assert next(
        scenario for scenario in result.scenarios
        if scenario.scenario_id == "reflow_320_css_px"
    ).status == "unsupported"
    assert next(
        scenario for scenario in result.scenarios
        if scenario.scenario_id == "browser_zoom_200_percent"
    ).status == "unsupported"


def test_text_reflow_baseline_failure_is_explicit():
    class BrokenPage:
        async def evaluate(self, _expression, _argument):
            raise RuntimeError("evaluation failed")

    result = asyncio.run(
        audit_text_reflow(BrokenPage(), baseline_width=800, baseline_height=600)
    )
    assert result.status == "unavailable"
    assert result.scenarios[0].scenario_id == "baseline"
    assert result.scenarios[0].status == "error"
    assert result.scenarios[0].classification == "error"


def test_text_reflow_restores_styles_and_viewport_after_scenarios(
    fixture_server, tmp_path
):
    async def run():
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            try:
                page = await browser.new_page(viewport={"width": 1365, "height": 768})
                await page.goto(
                    f"{fixture_server}/text-reflow-table",
                    wait_until="domcontentloaded",
                )
                original_style = await page.locator("td").first.evaluate(
                    """(element) => ({
                        value: element.style.getPropertyValue("font-size"),
                        priority: element.style.getPropertyPriority("font-size")
                    })"""
                )
                await page.locator("td").nth(1).evaluate(
                    "(element) => element.style.setProperty('font-size', '19px', 'important')"
                )
                explicit_style = await page.locator("td").nth(1).evaluate(
                    """(element) => ({
                        value: element.style.getPropertyValue("font-size"),
                        priority: element.style.getPropertyPriority("font-size")
                    })"""
                )
                result = await audit_text_reflow(
                    page,
                    baseline_width=1365,
                    baseline_height=768,
                    viewport_name="desktop",
                    capture_screenshot=_scenario_screenshot_capture(
                        LocalScreenshotStorage(tmp_path)
                    ),
                )
                restored_style = await page.locator("td").first.evaluate(
                    """(element) => ({
                        value: element.style.getPropertyValue("font-size"),
                        priority: element.style.getPropertyPriority("font-size")
                    })"""
                )
                restored_explicit_style = await page.locator("td").nth(1).evaluate(
                    """(element) => ({
                        value: element.style.getPropertyValue("font-size"),
                        priority: element.style.getPropertyPriority("font-size")
                    })"""
                )
                return (
                    result,
                    page.viewport_size,
                    original_style,
                    restored_style,
                    explicit_style,
                    restored_explicit_style,
                )
            finally:
                await browser.close()

    (
        result,
        viewport_size,
        original_style,
        restored_style,
        explicit_style,
        restored_explicit_style,
    ) = asyncio.run(run())
    height_scenario = next(
        scenario for scenario in result.scenarios
        if scenario.scenario_id == "reflow_256_css_px_height"
    )
    assert viewport_size == {"width": 1365, "height": 768}
    assert restored_style == original_style
    assert restored_explicit_style == explicit_style
    assert height_scenario.status == "completed"
    assert height_scenario.viewport_width == 1365
    assert height_scenario.measurement.viewport_height == 256
    assert any(
        scenario.screenshot_ref
        for scenario in result.scenarios
        if scenario.findings
    )


def test_text_reflow_candidate_limit_prevents_clean_classification(
    fixture_server, monkeypatch
):
    monkeypatch.setattr("app.analyzers.text_reflow.MAX_INSPECTED_ELEMENTS", 1)
    result = _run_text_reflow_audit(fixture_server, "text-reflow-usable")
    text_scenario = next(
        scenario for scenario in result.scenarios
        if scenario.scenario_id == "text_200_percent"
    )

    assert text_scenario.status == "completed"
    assert text_scenario.classification == "needs_review"
    assert text_scenario.findings == []
    assert any("capped at 1 candidates" in detail for detail in text_scenario.details)


def test_text_reflow_reports_document_overflow_without_text_candidates():
    class PageWithDocumentOverflow:
        def __init__(self):
            self.width = 390
            self.height = 844

        async def evaluate(self, _expression, argument):
            overflow = self.width == 320 and not argument["enlargeText"]
            return {
                "viewport": {"width": self.width, "height": self.height},
                "document": {
                    "scrollWidth": self.width + (180 if overflow else 0),
                    "scrollHeight": self.height,
                },
                "inspectedTextElements": 0,
                "candidatesTruncated": False,
                "elements": [],
                "overlapPairs": [],
                "overflowBoundaries": [],
            }

        async def set_viewport_size(self, viewport_size):
            self.width = viewport_size["width"]
            self.height = viewport_size["height"]

    page = PageWithDocumentOverflow()
    result = asyncio.run(
        audit_text_reflow(page, baseline_width=390, baseline_height=844)
    )
    scenario = next(
        scenario for scenario in result.scenarios
        if scenario.scenario_id == "reflow_320_css_px"
    )

    assert scenario.classification == "needs_review"
    assert scenario.findings[0].selector == "html"
    assert scenario.findings[0].evidence["document_horizontal_overflow_px"] == 180
    assert scenario.findings[0].classification == "needs_review"
    assert page.width == 390
    assert page.height == 844


def test_keyboard_audit_records_visible_keyboard_focus(fixture_server):
    result = _run_keyboard_audit(fixture_server, "keyboard-visible")
    sequence_check = next(
        check for check in result.checks if check.check_id == "sequential_navigation"
    )
    indicator_check = next(
        check for check in result.checks if check.check_id == "focus_indicator"
    )

    assert result.status == "partial"
    assert sequence_check.status == "needs_review"
    assert indicator_check.status == "needs_review"
    assert all(check.status != "pass" for check in result.checks)
    assert result.tab_actions > 0
    assert result.shift_tab_actions == 2
    assert [finding.selector for finding in result.findings] == [
        "#first-link",
        "#second-button",
        "#third-input",
    ]
    assert result.findings[0].accessible_name == "Skip to content"
    assert result.findings[0].role == "link"
    assert all(
        finding.focus_indicator_detected is True for finding in result.findings
    )
    assert all(finding.focus_visible_pseudo_class is True for finding in result.findings)


def test_keyboard_audit_marks_missing_focus_indicator_for_review(fixture_server):
    result = _run_keyboard_audit(fixture_server, "keyboard-absent")
    indicator = next(check for check in result.checks if check.check_id == "focus_indicator")

    assert indicator.status == "needs_review"
    assert result.findings[0].focus_indicator_detected is False
    assert "other indicator techniques" in indicator.summary


def test_keyboard_audit_reports_interactive_candidate_skipped_by_tab(fixture_server):
    result = _run_keyboard_audit(fixture_server, "keyboard-skipped")
    sequence = next(
        check for check in result.checks if check.check_id == "sequential_navigation"
    )

    assert sequence.status == "needs_review"
    assert "#skipped" in sequence.evidence[0]["unobserved_candidates"]


def test_keyboard_audit_does_not_assume_candidate_count_proves_tab_order(
    fixture_server,
):
    result = _run_keyboard_audit(fixture_server, "keyboard-edge-cases")
    sequence = next(
        check for check in result.checks if check.check_id == "sequential_navigation"
    )
    focus_order = next(
        check for check in result.checks if check.check_id == "focus_order"
    )

    assert sequence.status == "needs_review"
    assert focus_order.status == "needs_review"
    assert all(check.status != "pass" for check in result.checks)
    evidence = sequence.evidence[0]
    assert evidence["candidate_list_truncated"] is False
    assert evidence["shift_tab_sequence"]
    assert any(
        "positive tabindex" in item.lower() and "#positive-tabindex" in item
        for item in result.candidate_limitations
    )
    assert any("radio group" in item for item in result.candidate_limitations)
    assert any("shadow roots" in item for item in result.candidate_limitations)
    assert "#dynamic" in result.late_candidates
    assert "#dynamic" in result.unexpected_focus_targets
    dynamic = next(item for item in result.findings if item.selector == "#dynamic")
    assert dynamic.discovery_status == "outside_initial_snapshot"
    assert any("#dynamic" in item for item in result.candidate_limitations)


def test_keyboard_audit_reports_potential_focus_trap_for_review(fixture_server):
    result = _run_keyboard_audit(fixture_server, "keyboard-trap")
    trap = next(
        check for check in result.checks if check.check_id == "keyboard_trap"
    )

    assert trap.status == "needs_review"
    assert "possible keyboard trap" in trap.summary
    assert trap.evidence[0]["tab_stalled_target"] == "#trapped"
    assert trap.evidence[0]["shift_tab_focus_after_stall"] == "#trapped"
    assert trap.evidence[0]["shift_tab_progress_observed"] is False
    assert result.tab_actions <= 51
    assert result.shift_tab_actions <= 2


def test_keyboard_audit_distinguishes_one_way_tab_block_from_trap(fixture_server):
    result = _run_keyboard_audit(fixture_server, "keyboard-one-way-block")
    trap = next(
        check for check in result.checks if check.check_id == "keyboard_trap"
    )

    assert trap.status == "needs_review"
    assert "does not demonstrate a two-direction" in trap.summary
    assert trap.evidence[0]["tab_stalled_target"] == "#blocked-forward"
    assert trap.evidence[0]["shift_tab_progress_observed"] is True
    assert trap.evidence[0]["shift_tab_focus_after_stall"] == "#before"


def test_keyboard_audit_reports_wrapping_cycle_for_manual_review(fixture_server):
    result = _run_keyboard_audit(fixture_server, "keyboard-wrapping-cycle")
    trap = next(
        check for check in result.checks if check.check_id == "keyboard_trap"
    )

    assert trap.status == "needs_review"
    assert "intentional wrapping or a widget-level trap" in trap.summary
    assert set(trap.evidence[0]["tab_cycle_selectors"]) == {
        "#first-in-cycle",
        "#second-in-cycle",
    }
    assert trap.evidence[0]["shift_tab_stayed_within_tab_cycle"] is True


def test_keyboard_audit_traverses_more_than_twenty_sequential_targets(fixture_server):
    result = _run_keyboard_audit(fixture_server, "keyboard-many-controls")
    sequence = next(
        check for check in result.checks if check.check_id == "sequential_navigation"
    )

    assert result.tab_actions > 20
    assert result.tab_actions <= 51
    assert "#last-control" in [finding.selector for finding in result.findings]
    assert sequence.evidence[0]["unobserved_candidates"] == []


def test_keyboard_audit_reports_focus_obscuration_for_review(fixture_server):
    result = _run_keyboard_audit(fixture_server, "keyboard-overlay")
    obscuration = next(
        check for check in result.checks if check.check_id == "focus_obscuration"
    )

    assert obscuration.status == "needs_review"
    assert result.findings[0].obscured is True
    assert result.findings[0].occluding_selector == "#cover"
    assert result.findings[0].occlusion_status == "potential_issue"
    assert result.findings[0].target_rect["width"] > 0
    assert result.findings[0].viewport == {"width": 800, "height": 600}
    assert result.findings[0].occluding_evidence


def test_keyboard_audit_confirms_opaque_full_cover_with_evidence(fixture_server):
    result = _run_keyboard_audit(fixture_server, "keyboard-overlay-opaque")
    obscuration = next(
        check for check in result.checks if check.check_id == "focus_obscuration"
    )

    assert obscuration.status == "fail"
    finding = result.findings[0]
    assert finding.occlusion_status == "confirmed_failure"
    assert finding.obscured is True
    evidence = next(
        item for item in finding.occluding_evidence
        if item["selector"] == "#opaque-cover"
    )
    assert evidence["coversTarget"] is True
    assert evidence["backgroundAlpha"] == 1
    assert evidence["targetHitSamples"] == evidence["totalTargetSamples"]
    assert finding.target_rect["left"] >= 0
    assert finding.viewport == {"width": 800, "height": 600}


def test_keyboard_audit_classifies_sticky_header_overlap_as_potential(
    fixture_server,
):
    result = _run_keyboard_audit(fixture_server, "keyboard-sticky-partial")
    obscuration = next(
        check for check in result.checks if check.check_id == "focus_obscuration"
    )

    assert obscuration.status == "needs_review"
    finding = result.findings[0]
    assert finding.occlusion_status == "potential_issue"
    assert finding.partially_obscured is True
    assert finding.occluding_selector == "#sticky-header"


def test_keyboard_audit_detects_opaque_dialog_cover(fixture_server):
    result = _run_keyboard_audit(fixture_server, "keyboard-dialog")
    obscuration = next(
        check for check in result.checks if check.check_id == "focus_obscuration"
    )

    assert obscuration.status == "fail"
    finding = result.findings[0]
    assert finding.selector == "#covered"
    assert finding.occlusion_status == "confirmed_failure"
    assert any(
        item["tagName"] == "dialog" and item["selector"] == "#cover-dialog"
        for item in finding.occluding_evidence
    )


def test_keyboard_audit_reports_no_sampled_occlusion_without_overlay(
    fixture_server,
):
    result = _run_keyboard_audit(fixture_server, "keyboard-unobscured")
    obscuration = next(
        check for check in result.checks if check.check_id == "focus_obscuration"
    )

    assert obscuration.status == "needs_review"
    assert result.findings[0].occlusion_status == "no_issue_detected"
    assert result.findings[0].occluding_evidence == []


def test_keyboard_audit_skips_pages_without_interactive_controls(fixture_server):
    result = _run_keyboard_audit(fixture_server, "keyboard-none")

    assert result.status == "not_tested"
    assert result.tab_actions == 0
    assert all(check.status == "not_tested" for check in result.checks)


def test_keyboard_audit_respects_page_safety_opt_out(fixture_server):
    result = _run_keyboard_audit(fixture_server, "keyboard-unsafe")

    assert result.status == "not_tested"
    assert result.tab_actions == 0
    assert result.checks[0].status == "not_tested"
    assert "opted out" in result.checks[0].summary


def test_keyboard_audit_reports_evaluation_errors_and_timeouts(monkeypatch):
    from app.analyzers import keyboard_focus

    class Keyboard:
        async def press(self, _key):
            return None

    class BrokenPage:
        keyboard = Keyboard()

        async def evaluate(self, _expression, _argument=None):
            raise RuntimeError("evaluation failed")

    result = asyncio.run(audit_keyboard_focus(BrokenPage()))
    assert result.status == "unavailable"
    assert all(check.status == "error" for check in result.checks)

    class SlowPage:
        keyboard = Keyboard()

        async def evaluate(self, _expression, _argument=None):
            await asyncio.sleep(0.1)
            return {}

    monkeypatch.setattr(keyboard_focus, "ACTION_TIMEOUT_SECONDS", 0.01)
    timed_out = asyncio.run(audit_keyboard_focus(SlowPage()))
    assert timed_out.status == "unavailable"
    assert all(check.status == "error" for check in timed_out.checks)
    assert "timed out" in timed_out.details[0]


def test_keyboard_audit_cancellation_removes_temporary_network_route(monkeypatch):
    from app.analyzers import keyboard_focus

    class Keyboard:
        async def press(self, _key):
            await asyncio.Event().wait()

    class BlockingPage:
        keyboard = Keyboard()

        def __init__(self):
            self.routes = []
            self.unroutes = []

        async def evaluate(self, _expression, _argument=None):
            return {
                "candidates": [
                    {
                        "selector": "#control",
                        "expectedInSequentialNavigation": True,
                        "baselineStyles": {},
                    }
                ],
                "active": None,
            }

        async def route(self, pattern, handler):
            self.routes.append((pattern, handler))

        async def unroute(self, pattern, handler):
            self.unroutes.append((pattern, handler))

    async def run():
        page = BlockingPage()
        monkeypatch.setattr(keyboard_focus, "AUDIT_TIMEOUT_SECONDS", 0.02)
        result = await audit_keyboard_focus(page)
        return page, result

    page, result = asyncio.run(run())
    assert result.status == "unavailable"
    assert len(page.routes) == 1
    assert page.unroutes == page.routes


def test_keyboard_audit_cancellation_during_evaluation_removes_network_route(
    monkeypatch,
):
    from app.analyzers import keyboard_focus

    class Keyboard:
        async def press(self, _key):
            return None

    class BlockingEvaluationPage:
        keyboard = Keyboard()

        def __init__(self):
            self.evaluations = 0
            self.routes = []
            self.unroutes = []

        async def evaluate(self, _expression, _argument=None):
            self.evaluations += 1
            if self.evaluations == 1:
                return {
                    "candidates": [
                        {
                            "selector": "#control",
                            "expectedInSequentialNavigation": True,
                            "baselineStyles": {},
                        }
                    ],
                    "active": None,
                }
            await asyncio.Event().wait()

        async def route(self, pattern, handler):
            self.routes.append((pattern, handler))

        async def unroute(self, pattern, handler):
            self.unroutes.append((pattern, handler))

    page = BlockingEvaluationPage()
    monkeypatch.setattr(keyboard_focus, "AUDIT_TIMEOUT_SECONDS", 0.02)
    result = asyncio.run(audit_keyboard_focus(page))

    assert result.status == "unavailable"
    assert page.evaluations == 2
    assert page.unroutes == page.routes


def test_capture_closes_disposable_context_when_keyboard_audit_is_cancelled(
    tmp_path, monkeypatch
):
    import app.capture.runner as runner

    closed = []

    class FakePage:
        def __init__(self):
            self.callback_started = asyncio.Event()

        def on(self, *_args):
            pass

        async def route(self, *_args):
            pass

        async def close(self):
            closed.append("page")

    page = FakePage()

    class FakeContext:
        async def new_page(self):
            return page

        async def close(self):
            closed.append("context")

    class FakeBrowser:
        async def new_context(self, **_kwargs):
            return FakeContext()

        async def close(self):
            closed.append("browser")

    class FakeChromium:
        async def launch(self):
            return FakeBrowser()

    class FakePlaywright:
        chromium = FakeChromium()

    class FakeManager:
        async def __aenter__(self):
            return FakePlaywright()

        async def __aexit__(self, *_args):
            return False

    monkeypatch.setattr(runner, "async_playwright", lambda: FakeManager())
    service = BrowserCapture(
        storage=LocalScreenshotStorage(tmp_path),
        url_validator=LocalhostValidator(),
    )

    async def skip_navigation(_page, _url, _evidence):
        return None

    async def skip_collection(_page, _evidence):
        return None

    def mark_ready(evidence):
        evidence.outcome = "completed"
        evidence.readiness_status = "ready"

    monkeypatch.setattr(service, "_navigate", skip_navigation)
    monkeypatch.setattr(service, "_settle_and_collect", skip_collection)
    monkeypatch.setattr(service, "_set_outcome", mark_ready)

    async def callback(_page):
        page.callback_started.set()
        await asyncio.Event().wait()

    async def run_capture():
        task = asyncio.create_task(
            service.capture(
                "http://example.test/",
                800,
                600,
                page_callback=callback,
            )
        )
        await page.callback_started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(run_capture())
    assert closed == ["page", "context", "browser"]


def test_real_playwright_evaluation_cancellation_cleans_audit_route_and_context(
    tmp_path, monkeypatch
):
    import app.capture.runner as runner

    async def run_capture():
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()

            class FakeChromium:
                async def launch(self):
                    return browser

            class FakePlaywright:
                chromium = FakeChromium()

            class FakeManager:
                async def __aenter__(self):
                    return FakePlaywright()

                async def __aexit__(self, *_args):
                    return False

            monkeypatch.setattr(runner, "async_playwright", lambda: FakeManager())
            original_close_resources = runner._close_resources
            resources_at_close = []

            async def close_resources(page, context, browser_resource):
                resources_at_close.append((page, context, browser_resource))
                return await original_close_resources(page, context, browser_resource)

            monkeypatch.setattr(runner, "_close_resources", close_resources)
            service = BrowserCapture(
                storage=LocalScreenshotStorage(tmp_path),
                url_validator=LocalhostValidator(),
            )

            async def prepare_page(page, _url, _evidence):
                await page.set_content("<button id='control'>Control</button>")

            async def skip_collection(_page, _evidence):
                return None

            def mark_ready(evidence):
                evidence.outcome = "completed"
                evidence.readiness_status = "ready"

            monkeypatch.setattr(service, "_navigate", prepare_page)
            monkeypatch.setattr(service, "_settle_and_collect", skip_collection)
            monkeypatch.setattr(service, "_set_outcome", mark_ready)
            evaluation_started = asyncio.Event()
            registered_routes = []
            removed_routes = []

            async def callback(page):
                original_evaluate = page.evaluate
                original_route = page.route
                original_unroute = page.unroute
                evaluate_count = 0

                async def block_second_evaluation(expression, argument=None):
                    nonlocal evaluate_count
                    evaluate_count += 1
                    if evaluate_count == 2:
                        evaluation_started.set()
                        return await original_evaluate(
                            "() => new Promise(() => {})"
                        )
                    return await original_evaluate(expression, argument)

                async def track_route_removal(pattern, handler=None, *args, **kwargs):
                    removed_routes.append((pattern, handler))
                    return await original_unroute(
                        pattern, handler, *args, **kwargs
                    )

                async def track_route_installation(
                    pattern, handler, *args, **kwargs
                ):
                    registered_routes.append((pattern, handler))
                    return await original_route(
                        pattern, handler, *args, **kwargs
                    )

                page.evaluate = block_second_evaluation
                page.route = track_route_installation
                page.unroute = track_route_removal
                await audit_keyboard_focus(page)

            task = asyncio.create_task(
                service.capture(
                    "http://example.test/",
                    800,
                    600,
                    page_callback=callback,
                )
            )
            await evaluation_started.wait()
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task

            assert len(resources_at_close) == 1
            page, context, closed_browser = resources_at_close[0]
            assert page.is_closed()
            assert all(open_page.is_closed() for open_page in context.pages)
            assert closed_browser is browser
            assert not browser.is_connected()
            assert len(registered_routes) == 1
            assert removed_routes == registered_routes

    asyncio.run(run_capture())


def test_element_overflow_diagnosis_uses_real_geometry_and_filters_candidates(
    fixture_server,
):
    async def diagnose_at_viewports():
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            results_by_width = {}
            try:
                for width, height in (
                    (1365, 768),
                    (768, 1024),
                    (390, 844),
                ):
                    context = await browser.new_context(
                        viewport={"width": width, "height": height}
                    )
                    try:
                        page = await context.new_page()
                        response = await page.goto(
                            f"{fixture_server}/responsive-overflow",
                            wait_until="domcontentloaded",
                        )
                        assert response is not None and response.ok
                        results_by_width[width] = (
                            await diagnose_element_horizontal_overflow(page, width)
                        )
                    finally:
                        await context.close()
            finally:
                await browser.close()
        return results_by_width

    results_by_width = asyncio.run(diagnose_at_viewports())

    assert not any(
        result.selector == "#oversized" for result in results_by_width[1365]
    )
    for width, expected_overflow in ((768, 132), (390, 510)):
        findings = results_by_width[width]
        oversized = [item for item in findings if item.selector == "#oversized"]
        assert len(oversized) == 1
        finding = oversized[0]
        assert finding.tag_name == "div"
        assert finding.viewport_width == width
        assert finding.left == pytest.approx(0, abs=1)
        assert finding.right == pytest.approx(900, abs=1)
        assert finding.width == pytest.approx(900, abs=1)
        assert finding.overflow_px == pytest.approx(expected_overflow, abs=1)
        assert finding.status == "potential_overflow_source"
        assert finding.scrollable_context_detected is False
        assert finding.scrollable_container_selector is None

    mobile_findings = results_by_width[390]
    assert all(item.selector != "#in-bounds" for item in mobile_findings)
    assert all(item.selector != "#hidden" for item in mobile_findings)
    assert all(item.selector != "#nested" for item in mobile_findings)
    assert [item.selector for item in mobile_findings].count("#oversized") == 1


def test_layout_evidence_covers_fixed_width_descendants_layout_and_scrolling(
    fixture_server,
):
    async def inspect_fixtures():
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            results = {}
            try:
                for path in (
                    "/layout-fixed-width",
                    "/layout-oversized-descendant",
                    "/layout-flex-grid",
                    "/layout-horizontal-scroll",
                ):
                    context = await browser.new_context(
                        viewport={"width": 390, "height": 844}
                    )
                    try:
                        page = await context.new_page()
                        response = await page.goto(
                            f"{fixture_server}{path}",
                            wait_until="domcontentloaded",
                        )
                        assert response is not None and response.ok
                        raw = await diagnose_element_horizontal_overflow(page, 390)
                        results[path] = await enrich_element_layout_evidence(
                            page, raw, 390
                        )
                    finally:
                        await context.close()
            finally:
                await browser.close()
        return results

    results = asyncio.run(inspect_fixtures())

    fixed = next(item for item in results["/layout-fixed-width"] if item.selector == "#fixed-width")
    assert fixed.layout_diagnosis_status == "available"
    assert fixed.layout_evidence.computed_width == "900px"
    assert fixed.layout_evidence.width == pytest.approx(900)
    assert fixed.layout_evidence.scroll_width >= fixed.layout_evidence.client_width
    assert fixed.layout_evidence.position == "static"

    parent = next(
        item
        for item in results["/layout-oversized-descendant"]
        if item.selector == "#oversized-parent"
    )
    assert parent.layout_diagnosis_status == "available"
    assert any(
        child.selector == "#oversized-child"
        for child in parent.layout_evidence.oversized_children
    )
    assert any(
        hypothesis.label == "oversized_descendant"
        for hypothesis in parent.layout_evidence.hypotheses
    )

    flex_item = next(
        item
        for item in results["/layout-flex-grid"]
        if item.selector == "#flex-item"
    )
    assert any(
        ancestor.display_type == "flex"
        for ancestor in flex_item.layout_evidence.ancestors
    )
    assert any(
        hypothesis.label == "flex_or_grid_layout_context"
        for hypothesis in flex_item.layout_evidence.hypotheses
    )
    grid_item = next(
        item
        for item in results["/layout-flex-grid"]
        if item.selector == "#grid-item"
    )
    assert any(
        ancestor.display_type == "grid"
        for ancestor in grid_item.layout_evidence.ancestors
    )

    scroll_content = next(
        item
        for item in results["/layout-horizontal-scroll"]
        if item.selector == "#scroll-content"
    )
    assert scroll_content.layout_evidence.horizontal_scrolling_enabled is True
    assert "#scroll-container" in scroll_content.layout_evidence.scrollable_context_selectors
    assert any(
        hypothesis.label == "horizontal_scrolling_enabled"
        for hypothesis in scroll_content.layout_evidence.hypotheses
    )


def test_removed_selector_reports_layout_evidence_unavailable(fixture_server):
    async def inspect_removed_element():
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            try:
                page = await browser.new_page(viewport={"width": 390, "height": 844})
                response = await page.goto(
                    f"{fixture_server}/layout-fixed-width",
                    wait_until="domcontentloaded",
                )
                assert response is not None and response.ok
                raw = await diagnose_element_horizontal_overflow(page, 390)
                await page.evaluate(
                    "() => document.querySelector('#fixed-width').remove()"
                )
                return await enrich_element_layout_evidence(page, raw, 390)
            finally:
                await browser.close()

    results = asyncio.run(inspect_removed_element())
    fixed = next(item for item in results if item.selector == "#fixed-width")

    assert fixed.layout_diagnosis_status == "unavailable"
    assert fixed.layout_evidence is None
    assert fixed.layout_diagnosis_details == ["Element no longer exists."]


def test_horizontal_overflow_is_recorded(fixture_server, capture):
    evidence = asyncio.run(capture.capture(f"{fixture_server}/overflow", 800, 600))
    assert evidence.document.scroll_width > evidence.document.visible_width


def test_delayed_dom_update_is_seen_after_settling(fixture_server, capture):
    evidence = asyncio.run(capture.capture(f"{fixture_server}/delayed", 800, 600))
    assert evidence.page_title == "Delayed fixture updated"


def test_failed_resource_is_captured(fixture_server, capture):
    evidence = asyncio.run(
        capture.capture(f"{fixture_server}/failed-resource", 800, 600)
    )
    assert any("/missing.png" in request.url for request in evidence.failed_requests)


def test_request_guard_blocks_prohibited_subresource(fixture_server, tmp_path):
    service = BrowserCapture(
        storage=LocalScreenshotStorage(tmp_path),
        url_validator=BlocksTestExternalHost(),
        settling_period_ms=50,
    )
    evidence = asyncio.run(
        service.capture(f"{fixture_server}/blocked-resource", 800, 600)
    )
    assert evidence.outcome == "partial"
    assert any("private.invalid" in request.url for request in evidence.failed_requests)


def test_uncaught_javascript_error_is_captured(fixture_server, capture):
    evidence = asyncio.run(
        capture.capture(f"{fixture_server}/javascript-error", 800, 600)
    )
    assert any("fixture boom" in error for error in evidence.uncaught_page_errors)


def test_navigation_timeout_returns_explicit_outcome(fixture_server, capture):
    evidence = asyncio.run(capture.capture(f"{fixture_server}/timeout", 800, 600))
    assert evidence.outcome == "navigation_timeout"
    assert evidence.navigation_status == "timeout"
    assert evidence.details


def test_capture_failure_still_closes_browser_resources(tmp_path, monkeypatch):
    import app.capture.runner as runner

    closed = []

    class FakeResource:
        async def close(self):
            closed.append(type(self).__name__)

    class FakePage(FakeResource):
        def on(self, *_args):
            pass

        async def route(self, *_args):
            pass

    class FakeContext(FakeResource):
        async def new_page(self):
            return FakePage()

    class FakeBrowser(FakeResource):
        async def new_context(self, **_kwargs):
            return FakeContext()

    class FakeChromium:
        async def launch(self):
            return FakeBrowser()

    class FakePlaywright:
        chromium = FakeChromium()

    class FakeManager:
        async def __aenter__(self):
            return FakePlaywright()

        async def __aexit__(self, *_args):
            return False

    monkeypatch.setattr(runner, "async_playwright", lambda: FakeManager())
    service = BrowserCapture(
        storage=LocalScreenshotStorage(tmp_path),
        url_validator=LocalhostValidator(),
    )
    with pytest.raises(AttributeError):
        asyncio.run(service.capture("http://example.com", 800, 600))
    assert closed == ["FakePage", "FakeContext", "FakeBrowser"]


def test_public_url_validator_rejects_embedded_credentials():
    with pytest.raises(UnsafeURL, match="credentials"):
        asyncio.run(
            PublicURLSafetyValidator().validate("https://user:pass@example.com/")
        )


def test_public_url_validator_rejects_loopback():
    with pytest.raises(UnsafeURL, match="prohibited network destination"):
        asyncio.run(PublicURLSafetyValidator().validate("http://127.0.0.1/"))


def test_recorded_urls_remove_credentials_and_redact_tokens():
    recorded = sanitize_url(
        "https://user:pass@example.com/path?token=secret&view=full#fragment"
    )
    assert recorded == (
        "https://example.com/path?token=%5Bredacted%5D&view=full"
    )


def test_api_returns_structured_invalid_url_outcome():
    from app.main import CaptureRequest, create_capture

    with pytest.raises(HTTPException) as raised:
        asyncio.run(create_capture(CaptureRequest(url="ftp://example.com")))
    assert raised.value.status_code == 400
    assert raised.value.detail["outcome"] == "invalid_or_prohibited_url"

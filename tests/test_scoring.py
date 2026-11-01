from dataclasses import replace
from typing import Any

from app.analyzers.accessibility import (
    AccessibilityScanResult,
    AxeRuleEvidence,
    NonTextContrastAuditResult,
)
from app.analyzers.horizontal_overflow import HorizontalOverflowResult
from app.analyzers.keyboard_focus import (
    KeyboardCheck,
    KeyboardFocusAuditResult,
)
from app.analyzers.scoring import build_audit_scoring
from app.analyzers.target_size import TargetSizeAuditResult, TargetSizeFinding
from app.analyzers.text_reflow import TextReflowAuditResult, TextReflowScenario
from app.capture.models import ViewportDimensions
from app.capture.responsive import (
    ElementOverflowDiagnosisResult,
    FindingNormalizationResult,
    TechnicalEvidenceResult,
    ViewportCaptureResult,
)

_VIEWPORTS = (
    ("desktop", 1365, 768),
    ("tablet", 768, 1024),
    ("mobile", 390, 844),
)


def _result(name: str, width: int, height: int) -> ViewportCaptureResult:
    return ViewportCaptureResult(
        name=name,
        viewport=ViewportDimensions(width, height),
        capture_outcome="completed",
        horizontal_overflow=HorizontalOverflowResult(width, width, 0, False),
        overflow_analysis_status="available",
        screenshot_ref=None,
        element_overflow_diagnosis=ElementOverflowDiagnosisResult(
            status="available"
        ),
        finding_normalization=FindingNormalizationResult(status="available"),
        accessibility_scan=AccessibilityScanResult(
            status="available",
            non_text_contrast=NonTextContrastAuditResult(
                status="available", inspected_components=1
            ),
        ),
        technical_evidence=TechnicalEvidenceResult(status="available"),
    )


def _results() -> list[ViewportCaptureResult]:
    return [_result(*viewport) for viewport in _VIEWPORTS]


def _replace_all(
    results: list[ViewportCaptureResult], **changes: Any
) -> list[ViewportCaptureResult]:
    return [replace(result, **changes) for result in results]


def _criterion(scoring: dict, criterion_id: str) -> dict:
    return next(
        criterion
        for criterion in scoring["criteria"]
        if criterion["criterion_id"] == criterion_id
    )


def _axe_rule(rule_id: str, impact: str | None = "serious") -> AxeRuleEvidence:
    return AxeRuleEvidence(
        rule_id=rule_id,
        description=f"{rule_id} description",
        impact=impact,
        help=f"{rule_id} help",
        help_url=f"https://example.test/{rule_id}",
        tags=["wcag412"],
        nodes=[],
        failure_summaries=[],
    )


def test_keyboard_passes_are_normalized_and_aggregated_across_viewports():
    results = _replace_all(
        _results(),
        keyboard_focus_audit=KeyboardFocusAuditResult(
            status="available",
            checks=[
                KeyboardCheck(
                    "sequential_navigation", ["2.1.1"], "pass", "Tab navigation passed."
                ),
                KeyboardCheck(
                    "keyboard_trap", ["2.1.2"], "pass", "No keyboard trap detected."
                ),
                KeyboardCheck(
                    "focus_indicator", ["2.4.7"], "pass", "Focus was visible."
                ),
                KeyboardCheck(
                    "focus_obscuration", ["2.4.11"], "pass", "Focus was unobscured."
                ),
            ],
        ),
    )

    scoring = build_audit_scoring(results)

    keyboard = _criterion(scoring, "accessibility.keyboard_operability")
    assert keyboard["status"] == "pass"
    assert [item["status"] for item in keyboard["viewport_results"]] == [
        "pass",
        "pass",
        "pass",
    ]


def test_missing_keyboard_check_is_not_treated_as_a_pass():
    results = _replace_all(
        _results(),
        keyboard_focus_audit=KeyboardFocusAuditResult(
            status="available",
            checks=[
                KeyboardCheck(
                    "sequential_navigation", ["2.1.1"], "pass", "Tab navigation passed."
                ),
                KeyboardCheck(
                    "keyboard_trap", ["2.1.2"], "not_tested", "Trap check not run."
                ),
            ],
        ),
    )

    criterion = _criterion(
        build_audit_scoring(results), "accessibility.keyboard_operability"
    )

    assert criterion["status"] == "needs_review"
    assert all(
        item["status"] == "needs_review" for item in criterion["viewport_results"]
    )


def test_axe_violation_takes_precedence_over_passes_in_other_viewports():
    results = _results()
    results[0] = replace(
        results[0],
        accessibility_scan=AccessibilityScanResult(
            status="available",
            violations=[_axe_rule("button-name")],
        ),
    )
    results[1] = replace(
        results[1],
        accessibility_scan=AccessibilityScanResult(
            status="available",
            passes=[_axe_rule("button-name", impact=None)],
        ),
    )
    results[2] = replace(
        results[2],
        accessibility_scan=AccessibilityScanResult(status="available"),
    )

    criterion = _criterion(
        build_audit_scoring(results), "accessibility.accessible_names"
    )

    assert criterion["status"] == "fail"
    assert criterion["affected_viewports"] == ["desktop"]
    assert [item["status"] for item in criterion["viewport_results"]] == [
        "fail",
        "pass",
        "not_tested",
    ]


def test_identical_findings_across_viewports_share_deduplicated_evidence():
    results = _replace_all(
        _results(),
        target_size_audit=TargetSizeAuditResult(
            status="available",
            inspected_targets=1,
            findings=[
                TargetSizeFinding(
                    criterion_id="2.5.8",
                    selector="#small-target",
                    tag_name="button",
                    role="button",
                    accessible_name="Open",
                    width_css_px=18,
                    height_css_px=18,
                    left_css_px=10,
                    top_css_px=10,
                )
            ],
        ),
    )

    criterion = _criterion(
        build_audit_scoring(results), "accessibility.target_size"
    )

    assert criterion["status"] == "needs_review"
    assert len(criterion["evidence"]) == 1
    assert criterion["evidence"][0]["viewports"] == [
        "desktop",
        "tablet",
        "mobile",
    ]


def test_unimplemented_criteria_report_unsupported_per_viewport():
    criterion = _criterion(build_audit_scoring(_results()), "functional.forms")

    assert criterion["status"] == "unsupported"
    assert criterion["tested_viewports"] == []
    assert [item["status"] for item in criterion["viewport_results"]] == [
        "unsupported",
        "unsupported",
        "unsupported",
    ]


def test_partially_unsupported_scenario_is_not_aggregated_as_a_pass():
    results = _results()
    statuses = ("completed", "unsupported", "completed")
    classifications = ("no_violation_detected", "unsupported", "no_violation_detected")
    for index, result in enumerate(results):
        scenario = TextReflowScenario(
            scenario_id="text_200_percent",
            status=statuses[index],
            classification=classifications[index],
            condition="200% text enlargement.",
            method="Per-element font-size override.",
            criterion_ids=["1.4.4"],
        )
        results[index] = replace(
            result,
            text_reflow_audit=TextReflowAuditResult(
                status="available",
                scenarios=[scenario],
            ),
        )

    criterion = _criterion(
        build_audit_scoring(results), "accessibility.text_resizing"
    )

    assert criterion["status"] == "needs_review"
    assert [item["status"] for item in criterion["viewport_results"]] == [
        "pass",
        "unsupported",
        "pass",
    ]


def test_missing_viewport_and_empty_scan_do_not_become_passes():
    results = _replace_all(
        _results()[:2],
        accessibility_scan=AccessibilityScanResult(status="available"),
    )

    scoring = build_audit_scoring(results)

    assert _criterion(scoring, "accessibility.accessible_names")["status"] == "not_tested"
    assert _criterion(scoring, "accessibility.automated_checks")["status"] == "needs_review"
    assert scoring["overall_score"] is None
    assert scoring["overall_scoring_status"] == "insufficient_evidence"


def test_distinct_scenario_evidence_is_not_collapsed():
    results = _results()
    results[0] = replace(
        results[0],
        accessibility_scan=AccessibilityScanResult(
            status="available",
            violations=[_axe_rule("color-contrast")],
        ),
    )
    results[1] = replace(
        results[1],
        accessibility_scan=AccessibilityScanResult(
            status="available",
            violations=[
                replace(_axe_rule("color-contrast"), description="Different evidence")
            ],
        ),
    )

    criterion = _criterion(
        build_audit_scoring(results), "accessibility.color_contrast"
    )

    assert criterion["status"] == "fail"
    assert len(criterion["evidence"]) == 2
    assert criterion["evidence"][0]["viewports"] == ["desktop"]
    assert criterion["evidence"][1]["viewports"] == ["tablet"]

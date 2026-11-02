from dataclasses import replace
from dataclasses import dataclass
from typing import Any

from app.analyzers.accessibility import (
    AccessibilityScanResult,
    AxeRuleEvidence,
    NonTextContrastAuditResult,
)
from app.analyzers.element_horizontal_overflow import ElementHorizontalOverflowEvidence
from app.analyzers.functional_ux import FunctionalUXAuditResult, FunctionalUXFinding
from app.analyzers.horizontal_overflow import HorizontalOverflowResult
from app.analyzers.horizontal_overflow import HorizontalOverflowResult
from app.analyzers.keyboard_focus import (
    KeyboardCheck,
    KeyboardFocusAuditResult,
)
from app.analyzers.scoring import (
    DEFAULT_SCORING_CONFIGURATION,
    DimensionConfig,
    _Observation,
    _evidence_reference,
    _plain,
    _score_dimension,
    build_audit_scoring,
)
from app.analyzers.target_size import TargetSizeAuditResult, TargetSizeFinding
from app.analyzers.text_reflow import TextReflowAuditResult, TextReflowScenario
from app.capture.models import FailedRequest, ViewportDimensions
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
    assert criterion["affected_viewports"] == ["desktop", "tablet"]
    assert [item["status"] for item in criterion["viewport_results"]] == [
        "fail",
        "needs_review",
        "not_tested",
    ]


def test_partial_axe_scan_does_not_downgrade_complete_rules_or_pass_missing_rules():
    from app.analyzers.scoring import _NAME_RULES

    complete_passes = [_axe_rule(rule_id, impact=None) for rule_id in _NAME_RULES]
    complete = _replace_all(
        _results(),
        accessibility_scan=AccessibilityScanResult(
            status="partial",
            passes=complete_passes,
            details=["Another axe result collection was truncated."],
        ),
    )
    partial_rules = _replace_all(
        _results(),
        accessibility_scan=AccessibilityScanResult(
            status="partial",
            passes=[_axe_rule("button-name", impact=None)],
        ),
    )

    complete_criterion = _criterion(
        build_audit_scoring(complete), "accessibility.accessible_names"
    )
    partial_criterion = _criterion(
        build_audit_scoring(partial_rules), "accessibility.accessible_names"
    )

    assert complete_criterion["status"] == "pass"
    assert all(
        "Another axe result collection was truncated." in item["limitations"]
        for item in complete_criterion["evidence"]
    )
    assert partial_criterion["status"] == "needs_review"
    assert all(
        item["status"] == "needs_review"
        for item in partial_criterion["viewport_results"]
    )


def test_partial_keyboard_audit_uses_completed_check_results_but_requires_each_check():
    completed = KeyboardFocusAuditResult(
        status="partial",
        checks=[
            KeyboardCheck("sequential_navigation", ["2.1.1"], "pass", "Traversal completed."),
            KeyboardCheck("keyboard_trap", ["2.1.2"], "pass", "Trap check completed."),
        ],
    )
    missing = KeyboardFocusAuditResult(
        status="partial",
        checks=[
            KeyboardCheck("sequential_navigation", ["2.1.1"], "pass", "Traversal completed."),
        ],
    )

    complete_scoring = build_audit_scoring(
        _replace_all(_results(), keyboard_focus_audit=completed)
    )
    missing_scoring = build_audit_scoring(
        _replace_all(_results(), keyboard_focus_audit=missing)
    )

    assert _criterion(
        complete_scoring, "accessibility.keyboard_operability"
    )["status"] == "pass"
    assert _criterion(
        missing_scoring, "accessibility.keyboard_operability"
    )["status"] == "needs_review"


def test_functional_partial_evidence_is_normalized_per_criterion():
    inconclusive_link = FunctionalUXFinding(
        rule_id="broken_link",
        element_selector="a#blocked",
        accessible_label="Blocked destination",
        destination_url="https://example.test/blocked",
        failure_category="inconclusive",
        status="inconclusive",
    )
    results = _replace_all(
        _results(),
        functional_ux_audit=FunctionalUXAuditResult(
            status="partial",
            checked_links=5,
            checked_images=3,
            inconclusive=[inconclusive_link],
            details=["One sampled link could not be verified."],
        ),
    )

    scoring = build_audit_scoring(results)

    assert _criterion(scoring, "functional.broken_links")["status"] == "needs_review"
    assert _criterion(scoring, "functional.broken_images")["status"] == "pass"

    empty_checks = build_audit_scoring(
        _replace_all(
            _results(),
            functional_ux_audit=FunctionalUXAuditResult(status="available"),
        )
    )
    assert _criterion(empty_checks, "functional.broken_links")["status"] == "not_applicable"
    assert _criterion(empty_checks, "functional.broken_images")["status"] == "not_applicable"


def test_document_overflow_is_deterministic_and_element_candidates_stay_review_only():
    element_candidate = ElementHorizontalOverflowEvidence(
        tag_name="div",
        selector="#wide",
        left=380,
        right=410,
        width=30,
        viewport_width=390,
        overflow_px=20,
        status="potential_overflow_source",
        scrollable_context_detected=False,
        scrollable_container_selector=None,
    )
    zero_overflow = _replace_all(
        _results(),
        horizontal_overflow=HorizontalOverflowResult(390, 390, 0, False),
        element_overflow_diagnosis=ElementOverflowDiagnosisResult(
            status="available", findings=[element_candidate]
        ),
    )
    measured_overflow = _replace_all(
        _results(),
        horizontal_overflow=HorizontalOverflowResult(410, 390, 20, True),
    )

    zero_scoring = build_audit_scoring(zero_overflow)
    measured_scoring = build_audit_scoring(measured_overflow)

    assert _criterion(zero_scoring, "responsive.document_overflow")["status"] == "pass"
    assert _criterion(zero_scoring, "responsive.element_overflow")["status"] == "needs_review"
    assert _criterion(measured_scoring, "responsive.document_overflow")["status"] == "fail"


def test_low_coverage_dimension_score_is_explicitly_based_on_conclusive_checks():
    results = _replace_all(
        _results(),
        technical_evidence=TechnicalEvidenceResult(
            status="available",
            page_url="https://example.test/",
            console_errors=["A browser console error was recorded."],
            failed_requests=[
                FailedRequest("https://cdn.example.net/app.js", "script", "HTTP 503")
            ],
        ),
    )

    dimension = next(
        item
        for item in build_audit_scoring(results)["dimensions"]
        if item["dimension_id"] == "technical_reliability"
    )

    assert dimension["score"] == 100
    assert dimension["score_basis"] == "conclusive_checks"
    assert dimension["coverage_percentage"] == 50
    assert dimension["score_range"] == {"min": 38.46, "max": 100.0}
    assert dimension["scoring_status"] == "provisional"


def test_scoring_debug_log_traces_criterion_and_dimension_calculations(caplog):
    import logging

    with caplog.at_level(logging.DEBUG, logger="app.analyzers.scoring"):
        build_audit_scoring(_results())

    diagnostic = next(
        record.message
        for record in caplog.records
        if "audit_scoring_diagnostics=" in record.message
    )
    assert '"aggregated_status":"needs_review"' in diagnostic
    assert '"analyzer_id":"document_overflow"' in diagnostic
    assert '"applicable_weight":' in diagnostic
    assert '"conclusive_weight":' in diagnostic
    assert '"scoring_status":' in diagnostic


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
    assert scoring["minimum_overall_coverage"] == 40.0


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


def test_axe_rule_reference_includes_target_before_generic_rule_id():
    observation = _Observation("desktop", "fail", "axe_core")
    first = _evidence_reference(observation, {"rule_id": "label", "target": ["#first"]})
    second = _evidence_reference(observation, {"rule_id": "label", "target": ["#second"]})

    assert first == 'label:["#first"]'
    assert second == 'label:["#second"]'
    assert first != second


def test_plain_dataclass_type_is_not_passed_to_asdict():
    @dataclass
    class Evidence:
        message: str

    assert isinstance(_plain(Evidence), str)


def test_dimension_score_range_handles_resolved_and_unresolved_states():
    statuses = ("pass", "fail", "needs_review", "not_tested", "error", "unsupported", "not_applicable")
    criteria = [
        {
            "criterion_id": status,
            "dimension": "test",
            "status": status,
            "weight": 1,
            "implemented": status != "unsupported",
        }
        for status in statuses
    ]
    dimension = DimensionConfig("test", "Test", 100, True, "Test dimension.")

    scored = _score_dimension(dimension, criteria, DEFAULT_SCORING_CONFIGURATION)

    assert scored["score_range"] == {"min": 20.0, "max": 80.0}
    assert scored["total_applicable_criteria"] == 5
    assert scored["not_applicable_criteria"] == 1
    assert scored["unsupported_criteria"] == 1


def test_empty_scan_reports_viewport_gaps_and_score_unavailable_requirements():
    scoring = build_audit_scoring([])

    assert scoring["viewport_coverage"]["desktop"]["capture_outcome"] == "not_returned"
    assert not scoring["viewport_coverage"]["desktop"]["capture_completed"]
    assert not scoring["viewport_coverage"]["desktop"]["analyzer_evidence_returned"]
    accessibility = next(
        item for item in scoring["score_unavailable"]["dimensions"]
        if item["dimension_id"] == "accessibility"
    )
    assert accessibility["required_conclusive_criteria"] == 4
    assert accessibility["additional_conclusive_criteria_needed"] == 4
    assert accessibility["unresolved_criteria"]
    assert all(
        item["action"] == "Run the missing check."
        for item in accessibility["unresolved_criteria"]
        if item["status"] == "not_tested"
    )
    assert "does not guarantee" in scoring["score_unavailable"]["reason"]
    assert scoring["dimensions"][-1]["score_range"] == {"min": None, "max": None}


def test_score_weight_basis_and_excluded_dimensions_use_dimension_ids():
    scoring = build_audit_scoring(_results())
    eligible = [
        item for item in scoring["dimensions"]
        if item["implemented"]
        and item["score"] is not None
        and item["coverage_percentage"] is not None
        and item["coverage_percentage"] >= scoring["minimum_overall_coverage"]
    ]
    implemented_weight = sum(
        item["weight"] for item in scoring["dimensions"] if item["implemented"]
    )
    included_weight = sum(item["weight"] for item in eligible)

    assert scoring["score_weight_basis"]["implemented_weight"] == implemented_weight
    assert scoring["score_weight_basis"]["included_weight"] == included_weight
    assert scoring["score_weight_basis"]["percentage"] == round(
        included_weight / implemented_weight * 100, 2
    )
    excluded_ids = {item["dimension_id"] for item in scoring["excluded_dimensions"]}
    assert "visual_ux" in excluded_ids
    assert scoring["overall_score_type"] == "partial_audit_score"


def test_technical_failed_requests_classify_first_party_third_party_and_non_http():
    cases = (
        (FailedRequest("https://example.test/missing", "document", "HTTP 404"), "fail"),
        (FailedRequest("https://cdn.example.net/app.js", "script", "HTTP 503"), "needs_review"),
        (FailedRequest("https://example.test/api", "fetch", "net::ERR_FAILED"), "needs_review"),
    )
    for request, expected in cases:
        results = _replace_all(
            _results(),
            technical_evidence=TechnicalEvidenceResult(
                status="available",
                page_url="https://example.test/page",
                failed_requests=[request],
            ),
        )
        criterion = _criterion(build_audit_scoring(results), "technical.failed_requests")
        assert criterion["status"] == expected


def test_unknown_request_origin_is_review_and_navigation_timeout_is_not_error():
    results = _replace_all(
        _results(),
        technical_evidence=TechnicalEvidenceResult(
            status="available",
            failed_requests=[
                FailedRequest("https://example.test/missing", "document", "HTTP 404")
            ],
        ),
    )
    scoring = build_audit_scoring(results)
    assert _criterion(scoring, "technical.failed_requests")["status"] == "needs_review"

    results[0] = replace(results[0], capture_outcome="navigation_timeout")
    capture = _criterion(
        build_audit_scoring(results), "technical.capture_reliability"
    )
    assert capture["viewport_results"][0]["status"] == "needs_review"


def test_score_unavailable_actions_distinguish_review_not_tested_and_error():
    results = _replace_all(
        _results(),
        accessibility_scan=AccessibilityScanResult(status="not_attempted"),
        keyboard_focus_audit=KeyboardFocusAuditResult(
            status="partial",
            checks=[
                KeyboardCheck(
                    "sequential_navigation", ["2.1.1"], "needs_review", "Review needed."
                )
            ],
        ),
        target_size_audit=TargetSizeAuditResult(status="unavailable"),
    )
    scoring = build_audit_scoring(results)
    accessibility = next(
        item for item in scoring["score_unavailable"]["dimensions"]
        if item["dimension_id"] == "accessibility"
    )
    actions = {
        item["status"]: item["action"]
        for item in accessibility["unresolved_criteria"]
    }

    assert actions["needs_review"] == "Existing evidence needs manual review."
    assert actions["not_tested"] == "Run the missing check."
    assert actions["error"] == "Resolve the analyzer or capture error."


def test_scoring_emits_wcag_metadata_evidence_strength_counts_and_version():
    scoring = build_audit_scoring(_results())
    keyboard = _criterion(scoring, "accessibility.keyboard_operability")
    target_size = _criterion(scoring, "accessibility.target_size")

    assert keyboard["wcag_references"] == ["2.1.1", "2.1.2"]
    assert keyboard["level"] == "A"
    assert keyboard["principle"] == "Operable"
    assert keyboard["evidence_strength"] == "bounded_probe"
    assert target_size["evidence_strength"] == "heuristic"
    assert scoring["scoring_configuration_version"] == "1.2.0"
    assert sum(scoring["status_counts"].values()) == len(scoring["criteria"])

    next_version = replace(DEFAULT_SCORING_CONFIGURATION, version="1.3.0")
    rescored = build_audit_scoring(_results(), next_version)
    assert rescored["scoring_configuration_version"] != scoring["scoring_configuration_version"]


def test_missing_required_viewport_remains_not_tested_in_viewport_coverage():
    scoring = build_audit_scoring(_results()[:2])
    keyboard = _criterion(scoring, "accessibility.keyboard_operability")

    assert keyboard["status"] != "pass"
    assert keyboard["viewport_results"][2]["status"] == "not_tested"
    assert scoring["viewport_coverage"]["mobile"]["capture_outcome"] == "not_returned"
    assert scoring["viewport_coverage"]["desktop"]["analyzer_evidence_returned"]


def test_overall_scoring_status_uses_configured_thresholds():
    from app.analyzers.scoring import _score_overall

    configuration = replace(
        DEFAULT_SCORING_CONFIGURATION,
        score_validity_thresholds=(
            (75.0, "valid_high_coverage"),
            (50.0, "provisional"),
            (0.0, "insufficient_evidence"),
        ),
    )
    dimensions = [
        {
            "dimension_id": "test",
            "name": "Test",
            "weight": 100,
            "implemented": True,
            "score": 80.0,
            "coverage_percentage": 80.0,
        }
    ]

    result = _score_overall(dimensions, [], configuration)

    assert result["overall_scoring_status"] == "valid_high_coverage"

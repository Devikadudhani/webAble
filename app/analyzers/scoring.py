from __future__ import annotations

import hashlib
import json
import logging
import math
from collections.abc import Iterable
from dataclasses import asdict, dataclass, is_dataclass
from typing import Any, Literal
from urllib.parse import urlsplit

from app.analyzers.accessibility import AccessibilityScanResult, AxeRuleEvidence
from app.analyzers.keyboard_focus import KeyboardFocusAuditResult
from app.analyzers.text_reflow import TextReflowAuditResult, TextReflowScenario
from app.analyzers.target_size import TargetSizeAuditResult
from app.capture.responsive import ViewportCaptureResult

logger = logging.getLogger(__name__)

CriterionStatus = Literal[
    "pass",
    "fail",
    "needs_review",
    "not_tested",
    "not_applicable",
    "unsupported",
    "error",
]
Confidence = Literal["high", "medium", "low"]
EvidenceStrength = Literal["deterministic", "bounded_probe", "heuristic"]
ScoringStatus = Literal[
    "insufficient_evidence",
    "provisional",
    "low_evidence",
    "very_limited_evidence",
    "valid_moderate_coverage",
    "valid_high_coverage",
    "not_implemented",
    "not_scored",
]

SCORING_CONFIGURATION_VERSION = "1.4.2"
VIEWPORT_ORDER = ("desktop", "tablet", "mobile")

_NAME_RULES = frozenset(
    {
        "aria-input-field-name",
        "aria-toggle-field-name",
        "button-name",
        "input-button-name",
        "label",
        "link-name",
        "select-name",
        "summary-name",
    }
)
_CONTRAST_RULES = frozenset({"color-contrast"})
_DEDICATED_AXE_RULES = _NAME_RULES | _CONTRAST_RULES | {"target-size"}


@dataclass(frozen=True)
class DimensionConfig:
    dimension_id: str
    name: str
    weight: float
    implemented: bool
    description: str


@dataclass(frozen=True)
class CriterionConfig:
    criterion_id: str
    name: str
    dimension: str
    weight: float
    description: str
    analyzer_ids: tuple[str, ...]
    implemented: bool = True
    required_viewports: tuple[str, ...] = VIEWPORT_ORDER
    applicable_conditions: str | None = None
    default_severity_guidance: str | None = None
    wcag_references: tuple[str, ...] = ()
    level: str | None = None
    principle: str | None = None
    evidence_strength: EvidenceStrength = "bounded_probe"


@dataclass(frozen=True)
class ScoringConfiguration:
    version: str
    dimensions: tuple[DimensionConfig, ...]
    criteria: tuple[CriterionConfig, ...]
    coverage_thresholds: tuple[tuple[float, str], ...] = (
        (90.0, "high"),
        (70.0, "moderate"),
        (30.0, "limited"),
        (0.0, "very_limited"),
    )
    score_validity_thresholds: tuple[tuple[float, ScoringStatus], ...] = (
        (90.0, "valid_high_coverage"),
        (70.0, "valid_moderate_coverage"),
        (30.0, "low_evidence"),
        (0.0, "very_limited_evidence"),
    )
    # Quality warning boundary only; never a score eligibility requirement.
    minimum_overall_coverage: float = 70.0
    score_labels: tuple[tuple[float, str], ...] = (
        (90.0, "excellent"),
        (80.0, "good"),
        (70.0, "fair"),
        (50.0, "poor"),
        (0.0, "critical"),
    )


DIMENSIONS = (
    DimensionConfig(
        "accessibility",
        "Accessibility",
        35,
        True,
        "Selected automated accessibility checks and bounded browser probes.",
    ),
    DimensionConfig(
        "responsive_quality",
        "Responsive quality",
        25,
        True,
        "Measured viewport overflow and text reflow evidence.",
    ),
    DimensionConfig(
        "functional_reliability",
        "Functional reliability",
        15,
        True,
        "Bounded checks of rendered links and images.",
    ),
    DimensionConfig(
        "technical_reliability",
        "Technical reliability",
        15,
        True,
        "Browser console, runtime, network, and capture observations.",
    ),
    DimensionConfig(
        "visual_ux",
        "Visual and UX quality",
        10,
        False,
        "No dedicated visual and UX quality analyzer is implemented.",
    ),
)

CRITERIA = (
    CriterionConfig(
        "accessibility.accessible_names",
        "Accessible names and labels",
        "accessibility",
        5,
        "Selected axe checks for accessible names and form labels.",
        ("axe_core",),
        wcag_references=("4.1.2",),
        level="A",
        principle="Robust",
        evidence_strength="bounded_probe",
    ),
    CriterionConfig(
        "accessibility.keyboard_operability",
        "Keyboard operability",
        "accessibility",
        5,
        "Bounded Tab and Shift+Tab navigation observations.",
        ("keyboard_focus",),
        wcag_references=("2.1.1", "2.1.2"),
        level="A",
        principle="Operable",
        evidence_strength="bounded_probe",
    ),
    CriterionConfig(
        "accessibility.focus_visibility",
        "Focus visibility and behavior",
        "accessibility",
        4,
        "Sampled focus indicators and focus obscuration checks.",
        ("keyboard_focus",),
        wcag_references=("2.4.7", "2.4.11"),
        level="AA",
        principle="Operable",
        evidence_strength="bounded_probe",
    ),
    CriterionConfig(
        "accessibility.text_resizing",
        "Text resizing",
        "accessibility",
        4,
        "Per-element computed-font-size doubling probe; not actual browser zoom.",
        ("text_reflow",),
        applicable_conditions="Requires a completed text_200_percent scenario.",
        wcag_references=("1.4.4",),
        level="AA",
        principle="Perceivable",
        evidence_strength="bounded_probe",
    ),
    CriterionConfig(
        "accessibility.color_contrast",
        "Text color contrast",
        "accessibility",
        4,
        "axe color-contrast rule results; incomplete results require review.",
        ("axe_core",),
        wcag_references=("1.4.3",),
        level="AA",
        principle="Perceivable",
        evidence_strength="bounded_probe",
    ),
    CriterionConfig(
        "accessibility.target_size",
        "Pointer target size",
        "accessibility",
        3,
        "Bounded measurement of undersized pointer-target candidates.",
        ("target_size",),
        wcag_references=("2.5.8",),
        level="AA",
        principle="Operable",
        evidence_strength="heuristic",
    ),
    CriterionConfig(
        "accessibility.automated_checks",
        "Other automated accessibility checks",
        "accessibility",
        5,
        "Selected axe WCAG A/AA rules not mapped to another criterion.",
        ("axe_core",),
    ),
    CriterionConfig(
        "accessibility.non_text_contrast",
        "Non-text contrast",
        "accessibility",
        2,
        "Heuristic non-text contrast candidate detection; findings require review.",
        ("non_text_contrast",),
        wcag_references=("1.4.11",),
        level="AA",
        principle="Perceivable",
        evidence_strength="heuristic",
    ),
    CriterionConfig(
        "responsive.document_overflow",
        "Document horizontal overflow",
        "responsive_quality",
        5,
        "Document scroll width compared with viewport width.",
        ("document_overflow",),
        evidence_strength="deterministic",
    ),
    CriterionConfig(
        "responsive.element_overflow",
        "Element-level horizontal overflow",
        "responsive_quality",
        4,
        "Bounded element geometry and layout evidence.",
        ("element_overflow",),
        evidence_strength="heuristic",
    ),
    CriterionConfig(
        "responsive.layout_clipping",
        "Element layout and clipping",
        "responsive_quality",
        4,
        "No complete criterion-level layout and clipping verdict is currently produced.",
        (),
        implemented=False,
    ),
    CriterionConfig(
        "responsive.text_reflow",
        "Text reflow at 320 CSS pixels",
        "responsive_quality",
        4,
        "Bounded 320 CSS-pixel viewport probe.",
        ("text_reflow",),
        applicable_conditions="Requires a completed reflow_320_css_px scenario.",
        wcag_references=("1.4.10",),
        level="AA",
        principle="Perceivable",
        evidence_strength="bounded_probe",
    ),
    CriterionConfig(
        "responsive.cross_viewport_behavior",
        "Responsive behavior across viewports",
        "responsive_quality",
        4,
        "Visual and content equivalence across arbitrary breakpoints is not tested.",
        (),
        implemented=False,
    ),
    CriterionConfig(
        "responsive.orientation",
        "Orientation and viewport-specific behavior",
        "responsive_quality",
        2,
        "No orientation lock or content-usability audit is currently implemented.",
        (),
        implemented=False,
    ),
    CriterionConfig(
        "functional.broken_links",
        "Broken or invalid links",
        "functional_reliability",
        4,
        "Bounded HEAD checks, with a ranged GET fallback for destinations that reject HEAD, on up to 15 rendered links per viewport.",
        ("functional_ux",),
        evidence_strength="bounded_probe",
    ),
    CriterionConfig(
        "functional.broken_images",
        "Broken images and media",
        "functional_reliability",
        2,
        "Rendered image loading checks; other media and functionality are not covered.",
        ("functional_ux",),
        evidence_strength="bounded_probe",
    ),
    CriterionConfig(
        "functional.interactive_controls",
        "Interactive control behavior",
        "functional_reliability",
        4,
        "Controls are not activated or behaviorally verified.",
        (),
        implemented=False,
    ),
    CriterionConfig(
        "functional.forms",
        "Form behavior",
        "functional_reliability",
        3,
        "Form submission and validation behavior are not tested.",
        (),
        implemented=False,
    ),
    CriterionConfig(
        "functional.user_journeys",
        "User journey execution",
        "functional_reliability",
        2,
        "Submitted journeys are context only and are not executed.",
        (),
        implemented=False,
    ),
    CriterionConfig(
        "technical.console_errors",
        "JavaScript console errors",
        "technical_reliability",
        4,
        "Recorded console.error events during the usable browser capture window; uncaught page exceptions are evaluated separately.",
        ("browser_console",),
        evidence_strength="deterministic",
    ),
    CriterionConfig(
        "technical.failed_requests",
        "Failed network requests",
        "technical_reliability",
        4,
        "Recorded HTTP errors and failed requests; blocked or ambiguous failures require review.",
        ("browser_network",),
        evidence_strength="bounded_probe",
    ),
    CriterionConfig(
        "technical.runtime_errors",
        "Browser runtime errors",
        "technical_reliability",
        3,
        "Uncaught page errors recorded by the browser capture.",
        ("browser_runtime",),
        evidence_strength="deterministic",
    ),
    CriterionConfig(
        "technical.resource_failures",
        "Resource loading failures",
        "technical_reliability",
        2,
        "Not separately scored to avoid double-counting the failed-network-request criterion.",
        (),
        implemented=False,
    ),
    CriterionConfig(
        "technical.capture_reliability",
        "Page loading and capture reliability",
        "technical_reliability",
        2,
        "Navigation, readiness, and capture completion status.",
        ("browser_capture",),
        evidence_strength="bounded_probe",
    ),
    CriterionConfig(
        "visual.visual_consistency",
        "Visual consistency and UX quality",
        "visual_ux",
        10,
        "Dedicated visual and UX analyzers are not implemented.",
        (),
        implemented=False,
    ),
)

DEFAULT_SCORING_CONFIGURATION = ScoringConfiguration(
    version=SCORING_CONFIGURATION_VERSION,
    dimensions=DIMENSIONS,
    criteria=CRITERIA,
)


@dataclass(frozen=True)
class _Observation:
    viewport: str
    status: CriterionStatus
    analyzer_id: str
    reference: str | None = None
    details: str | None = None
    data: Any = None
    confidence: Confidence | None = None
    limitations: tuple[str, ...] = ()


def build_audit_scoring(
    results: list[ViewportCaptureResult],
    configuration: ScoringConfiguration = DEFAULT_SCORING_CONFIGURATION,
) -> dict[str, Any]:
    """Normalize viewport analyzer outputs and compute evidence-based scores."""
    observations: dict[str, list[_Observation]] = {
        criterion.criterion_id: [] for criterion in configuration.criteria
    }
    results_by_viewport = {result.name: result for result in results}
    criterion_diagnostics = []

    for viewport in VIEWPORT_ORDER:
        result = results_by_viewport.get(viewport)
        if result is None:
            continue
        _normalize_viewport(result, observations)

    criterion_results = []
    for criterion in configuration.criteria:
        if not criterion.implemented:
            status: CriterionStatus = "unsupported"
            criterion_observations = [
                _Observation(
                    viewport=viewport,
                    status="unsupported",
                    analyzer_id="scoring_registry",
                    details=criterion.description,
                )
                for viewport in criterion.required_viewports
            ]
        else:
            criterion_observations = observations[criterion.criterion_id]
            observed_by_viewport = {
                observation.viewport: observation
                for observation in criterion_observations
            }
            for viewport in criterion.required_viewports:
                if viewport not in observed_by_viewport:
                    criterion_observations.append(
                        _Observation(
                            viewport=viewport,
                            status="not_tested",
                            analyzer_id="scoring_registry",
                            details="Required viewport result was not returned.",
                        )
                    )
            status = _aggregate_status(
                observation.status for observation in criterion_observations
            )

        evidence = _merge_evidence(
            criterion.criterion_id, criterion_observations
        )
        score_exclusion_reason = _manual_review_score_exclusion(
            criterion.criterion_id, status
        )
        tested_viewports = _ordered_unique(
            observation.viewport
            for observation in criterion_observations
            if observation.status not in ("not_tested", "unsupported")
        )
        affected_viewports = _ordered_unique(
            observation.viewport
            for observation in criterion_observations
            if observation.status in ("fail", "needs_review")
        )
        limitations = _ordered_unique(
            limitation
            for observation in criterion_observations
            for limitation in observation.limitations
        )
        criterion_results.append(
            {
                "criterion_id": criterion.criterion_id,
                "criterion_name": criterion.name,
                "dimension": criterion.dimension,
                "implemented": criterion.implemented,
                "status": status,
                "score_eligible": criterion.implemented and score_exclusion_reason is None,
                "score_exclusion_reason": score_exclusion_reason,
                "weight": criterion.weight,
                "evidence_strength": criterion.evidence_strength,
                "wcag_references": list(criterion.wcag_references),
                "level": criterion.level,
                "principle": criterion.principle,
                "tested_viewports": tested_viewports,
                "affected_viewports": affected_viewports,
                "evidence_count": len(evidence),
                "failure_count": sum(
                    item["status"] == "fail" for item in evidence
                ),
                "review_count": sum(
                    item["status"] == "needs_review" for item in evidence
                ),
                "confidence": _criterion_confidence(
                    status, criterion_observations
                ),
                "evidence": evidence,
                "limitations": limitations,
                "analyzer_ids": list(criterion.analyzer_ids),
                "viewport_results": _viewport_results(
                    criterion_observations, criterion.required_viewports
                ),
                "description": criterion.description,
                "applicable_conditions": criterion.applicable_conditions,
            }
        )
        criterion_diagnostics.append(
            {
                "criterion_id": criterion.criterion_id,
                "dimension": criterion.dimension,
                "weight": criterion.weight,
                "observations": [
                    {
                        "viewport": observation.viewport,
                        "status": observation.status,
                        "analyzer_id": observation.analyzer_id,
                        "details": observation.details,
                        "confidence": observation.confidence,
                    }
                    for observation in criterion_observations
                ],
                "aggregated_status": status,
            }
        )

    dimensions = [
        _score_dimension(
            dimension,
            criterion_results,
            configuration,
        )
        for dimension in configuration.dimensions
    ]
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            "audit_scoring_diagnostics=%s",
            json.dumps(
                {
                    "criteria": criterion_diagnostics,
                    "dimensions": [
                        _dimension_diagnostics(dimension, criterion_results)
                        for dimension in dimensions
                    ],
                },
                sort_keys=True,
                separators=(",", ":"),
            ),
        )
    overall = _score_overall(dimensions, criterion_results, configuration)
    status_counts = {
        output_key: sum(item["status"] == status for item in criterion_results)
        for output_key, status in (
            ("passed", "pass"),
            ("failed", "fail"),
            ("needs_review", "needs_review"),
            ("not_tested", "not_tested"),
            ("unsupported", "unsupported"),
            ("not_applicable", "not_applicable"),
            ("error", "error"),
        )
    }
    return {
        **overall,
        "dimensions": dimensions,
        "criteria": criterion_results,
        "status_counts": status_counts,
        "viewport_coverage": _viewport_coverage(results, observations),
        "scoring_configuration_version": configuration.version,
        "limitations": [
            "Scores summarize configured criteria, not WCAG conformance or total website quality.",
            "A criterion is counted once across required viewports; viewport-level evidence remains attached.",
            "Owner-declared features, representative URLs, and journeys are contextual inputs and are not treated as tested browser evidence.",
            "Functional checks are bounded to sampled rendered links and images; forms, control activation, and user journeys are not executed.",
            "Text resizing uses a deterministic computed-font-size override, not actual browser zoom.",
            "Keyboard traversal and visual candidate detection are bounded; partial probes do not establish full accessibility.",
            "Axe incomplete results, target-size candidates, overflow geometry, and other ambiguous evidence remain review-only.",
            "WCAG checks that require human review are excluded from score coverage; their findings remain available for review.",
            "Severity and fix priority are not inferred from scores; source analyzer evidence is preserved without applying severity-based score penalties.",
            "Visual and UX quality is registered but unsupported and does not contribute to any score.",
        ],
    }


def _manual_review_score_exclusion(
    criterion_id: str, status: CriterionStatus
) -> str | None:
    if criterion_id == "accessibility.non_text_contrast":
        return "Non-text contrast findings require human review."
    if criterion_id == "accessibility.target_size" and status == "needs_review":
        return "Potential target-size failures require human review."
    return None


def _normalize_viewport(
    result: ViewportCaptureResult,
    observations: dict[str, list[_Observation]],
) -> None:
    viewport = result.name
    if result.technical_evidence.access_status == "restricted":
        return  # Challenge or access-denied page evidence cannot score the website.
    _normalize_axe(result.accessibility_scan, viewport, observations)
    _normalize_keyboard(result.keyboard_focus_audit, viewport, observations)
    _normalize_text_reflow(result.text_reflow_audit, viewport, observations)
    _normalize_target_size(result.target_size_audit, viewport, observations)
    # axe target-size violations are conclusive; geometric candidates remain review-only.
    target_violations = [
        rule for rule in result.accessibility_scan.violations
        if rule.rule_id == "target-size"
    ]
    if target_violations:
        observations["accessibility.target_size"].append(_Observation(
            viewport, "fail", "axe_core", details="axe target-size reported a violation.",
            data=[_rule_data(rule) for rule in target_violations], confidence="high",
        ))
    _normalize_overflow(result, viewport, observations)
    _normalize_functional(result, viewport, observations)
    _normalize_technical(result, viewport, observations)


def _normalize_axe(
    audit: AccessibilityScanResult,
    viewport: str,
    observations: dict[str, list[_Observation]],
) -> None:
    rule_collections = {
        "fail": audit.violations,
        "needs_review": audit.incomplete,
        "pass": audit.passes,
        "not_applicable": audit.inapplicable,
    }
    for criterion_id, rule_ids in (
        ("accessibility.accessible_names", _NAME_RULES),
        ("accessibility.color_contrast", _CONTRAST_RULES),
    ):
        matching = [
            (status, rule)
            for status, rules in rule_collections.items()
            for rule in rules
            if rule.rule_id in rule_ids
        ]
        if audit.status == "unavailable":
            observation = _Observation(
                viewport,
                "error",
                "axe_core",
                details="Accessibility scan was unavailable.",
                limitations=tuple(audit.details),
            )
        elif audit.status == "not_attempted":
            observation = _Observation(
                viewport, "not_tested", "axe_core", details="Accessibility scan was not attempted."
            )
        elif any(status == "fail" for status, _ in matching):
            observation = _Observation(
                viewport,
                "fail",
                "axe_core",
                details="A relevant axe rule reported a violation.",
                data=[_rule_data(rule) for status, rule in matching if status == "fail"],
                confidence="high",
            )
        elif any(status == "needs_review" for status, _ in matching):
            observation = _Observation(
                viewport,
                "needs_review",
                "axe_core",
                details="A relevant axe rule returned incomplete evidence.",
                data=[
                    _rule_data(rule)
                    for status, rule in matching
                    if status == "needs_review"
                ],
                limitations=("axe incomplete results require manual review.",),
            )
        elif not matching:
            observation = _Observation(
                viewport,
                "needs_review" if audit.status == "partial" else "not_tested",
                "axe_core",
                details="No relevant axe rule result established this criterion.",
                limitations=("Absence of a relevant rule result is not a pass.",),
            )
        elif all(status == "not_applicable" for status, _ in matching) and {
            rule.rule_id for _, rule in matching
        } == rule_ids:
            observation = _Observation(
                viewport,
                "not_applicable",
                "axe_core",
                details="Relevant axe rules reported no applicable nodes.",
                data=[_rule_data(rule) for _, rule in matching],
            )
        elif {rule.rule_id for _, rule in matching} != rule_ids:
            observation = _Observation(
                viewport,
                "needs_review",
                "axe_core",
                details="One or more relevant axe rules did not return a result.",
                data=[_rule_data(rule) for _, rule in matching],
                limitations=tuple(audit.details),
            )
        else:
            observation = _Observation(
                viewport,
                "pass",
                "axe_core",
                details="Relevant axe rules completed without a reported violation.",
                data=[_rule_data(rule) for _, rule in matching],
                confidence="medium",
                limitations=tuple(audit.details) if audit.status == "partial" else (),
            )
        observations[criterion_id].append(observation)

    excluded = _DEDICATED_AXE_RULES
    other_results = [
        (status, rule)
        for status, rules in rule_collections.items()
        for rule in rules
        if rule.rule_id not in excluded
    ]
    violations = [
        rule for rule in audit.violations if rule.rule_id not in excluded
    ]
    incomplete = [
        rule for rule in audit.incomplete if rule.rule_id not in excluded
    ]
    if audit.status == "unavailable":
        status: CriterionStatus = "error"
    elif audit.status == "not_attempted":
        status = "not_tested"
    elif violations:
        status = "fail"
    elif incomplete or audit.status == "partial":
        status = "needs_review"
    elif other_results and all(
        result_status == "not_applicable"
        for result_status, _ in other_results
    ):
        status = "not_applicable"
    elif any(result_status == "pass" for result_status, _ in other_results):
        status = "pass"
    else:
        status = "needs_review" if audit.status == "available" else "not_tested"
    observations["accessibility.automated_checks"].append(
        _Observation(
            viewport,
            status,
            "axe_core",
            details=(
                "Other selected axe rules reported violations."
                if violations
                else "Other selected axe rules completed."
                if status == "pass"
                else "Other selected axe evidence is incomplete or unavailable."
            ),
            data=[_rule_data(rule) for _, rule in other_results],
            confidence="high" if violations else "medium" if status == "pass" else None,
            limitations=tuple(audit.details),
        )
    )

    non_text = audit.non_text_contrast
    if non_text.status == "unavailable":
        status = "error"
    elif non_text.status == "not_tested":
        status = "not_tested"
    elif non_text.findings or non_text.status == "partial":
        status = "needs_review"
    elif non_text.status == "available":
        status = (
            "not_applicable"
            if non_text.inspected_components + non_text.inspected_graphics == 0
            else "needs_review"
        )
    else:
        status = "not_tested"
    observations["accessibility.non_text_contrast"].append(
        _Observation(
            viewport,
            status,
            "non_text_contrast",
            details=(
                "Potential non-text contrast candidates require review."
                if non_text.findings
                else "No potential contrast candidates were detected; the heuristic probe does not establish conformance."
                if status == "needs_review"
                else "No applicable non-text contrast candidates were found."
                if status == "not_applicable"
                else "The non-text contrast probe was incomplete or unavailable."
            ),
            data=[_plain(item) for item in non_text.findings],
            limitations=tuple(non_text.details),
        )
    )


def _normalize_keyboard(
    audit: KeyboardFocusAuditResult,
    viewport: str,
    observations: dict[str, list[_Observation]],
) -> None:
    base_status: CriterionStatus | None = None
    if audit.status == "unavailable":
        base_status = "error"
    elif audit.status == "not_tested":
        base_status = "not_tested"
    groups = {
        "accessibility.keyboard_operability": {"sequential_navigation", "keyboard_trap"},
        "accessibility.focus_visibility": {"focus_indicator", "focus_obscuration"},
    }
    for criterion_id, check_ids in groups.items():
        checks = [check for check in audit.checks if check.check_id in check_ids]
        if base_status is not None:
            status = base_status
        elif not checks:
            status = "needs_review" if audit.status == "partial" else "not_tested"
        elif any(check.status == "fail" for check in checks):
            status = "fail"
        elif any(check.status == "error" for check in checks):
            status = "error"
        elif any(check.status == "needs_review" for check in checks):
            status = "needs_review"
        elif all(check.status == "not_tested" for check in checks):
            status = "not_tested"
        elif (
            {check.check_id for check in checks} != check_ids
            or any(check.status == "not_tested" for check in checks)
        ):
            status = "needs_review"
        elif all(check.status == "pass" for check in checks):
            status = "pass"
        else:
            status = "not_tested"
        observations[criterion_id].append(
            _Observation(
                viewport,
                status,
                "keyboard_focus",
                details="; ".join(check.summary for check in checks) or None,
                data=[_plain(check) for check in checks],
                confidence="high" if status == "fail" else "medium" if status == "pass" else None,
                limitations=tuple(audit.details) if status == "needs_review" else (),
            )
        )


def _normalize_text_reflow(
    audit: TextReflowAuditResult,
    viewport: str,
    observations: dict[str, list[_Observation]],
) -> None:
    scenarios = {scenario.scenario_id: scenario for scenario in audit.scenarios}
    for criterion_id, scenario_id in (
        ("accessibility.text_resizing", "text_200_percent"),
        ("responsive.text_reflow", "reflow_320_css_px"),
    ):
        scenario = scenarios.get(scenario_id)
        status = _scenario_status(scenario)
        observations[criterion_id].append(
            _Observation(
                viewport,
                status,
                "text_reflow",
                reference=scenario_id,
                details=(
                    scenario.classification
                    if scenario is not None
                    else "Required text-reflow scenario was not returned."
                ),
                data=_plain(scenario) if scenario is not None else None,
                confidence=(
                    "high"
                    if status == "fail"
                    else "medium"
                    if status == "pass"
                    else None
                ),
                limitations=tuple(scenario.details) if scenario is not None else (),
            )
        )


def _scenario_status(scenario: TextReflowScenario | None) -> CriterionStatus:
    if scenario is None:
        return "not_tested"
    if scenario.status == "error" or scenario.classification == "error":
        return "error"
    if scenario.status == "unsupported" or scenario.classification == "unsupported":
        return "unsupported"
    if scenario.status == "not_tested" or scenario.classification == "not_tested":
        return "not_tested"
    if scenario.status != "completed":
        return "not_tested"
    if scenario.classification == "violation":
        return "fail"
    if scenario.classification == "needs_review" or scenario.findings:
        return "needs_review"
    if scenario.classification == "no_violation_detected":
        return "pass"
    return "not_tested"


def _normalize_target_size(
    audit: TargetSizeAuditResult,
    viewport: str,
    observations: dict[str, list[_Observation]],
) -> None:
    if audit.status == "unavailable":
        status: CriterionStatus = "error"
    elif audit.status == "not_tested":
        status = "not_tested"
    elif audit.findings or audit.status == "partial":
        status = "needs_review"
    elif audit.status == "available" and audit.inspected_targets == 0:
        status = "not_applicable"
    elif audit.status == "available":
        status = "pass"
    else:
        status = "not_tested"
    observations["accessibility.target_size"].append(
        _Observation(
            viewport,
            status,
            "target_size",
            details="Undersized targets are candidates only; spacing and exceptions require review."
            if audit.findings
            else "Bounded target-size candidate scan completed."
            if status == "pass"
            else None,
            data=[_plain(item) for item in audit.findings],
            limitations=tuple(audit.details),
        )
    )


def _normalize_overflow(
    result: ViewportCaptureResult,
    viewport: str,
    observations: dict[str, list[_Observation]],
) -> None:
    if result.overflow_analysis_status == "available" and result.horizontal_overflow:
        overflow = result.horizontal_overflow
        status: CriterionStatus = "fail" if overflow.overflow_px > 0 else "pass"
        data = _plain(overflow)
    elif result.overflow_analysis_status in ("capture_incomplete", "missing_dimensions"):
        status, data = "not_tested", None
    elif result.overflow_analysis_status == "not_attempted":
        status, data = "not_tested", None
    else:
        status, data = "error", None
    observations["responsive.document_overflow"].append(
        _Observation(
            viewport,
            status,
            "document_overflow",
            details="Document width exceeded the viewport width."
            if status == "fail"
            else "Document and viewport widths were measured."
            if status == "pass"
            else None,
            data=data,
            confidence="high" if status in ("pass", "fail") else None,
        )
    )

    diagnosis = result.element_overflow_diagnosis
    if diagnosis.status == "unavailable":
        status = "error"
    elif diagnosis.status == "not_attempted":
        status = "not_tested"
    elif diagnosis.findings:
        status = "needs_review"
    elif diagnosis.status == "available":
        status = "pass"
    else:
        status = "not_tested"
    observations["responsive.element_overflow"].append(
        _Observation(
            viewport,
            status,
            "element_overflow",
            details="Element geometry suggests possible overflow; cause and impact require review."
            if diagnosis.findings
            else "Bounded element overflow diagnosis completed."
            if status == "pass"
            else None,
            data=[_plain(item) for item in diagnosis.findings],
            limitations=tuple(diagnosis.details)
            + tuple(
                detail
                for item in diagnosis.findings
                for detail in item.layout_diagnosis_details
            ),
        )
    )


def _normalize_functional(
    result: ViewportCaptureResult,
    viewport: str,
    observations: dict[str, list[_Observation]],
) -> None:
    audit = result.functional_ux_audit
    for criterion_id, rule_id, checked_count in (
        ("functional.broken_links", "broken_link", audit.checked_links),
        ("functional.broken_images", "failed_image", audit.checked_images),
    ):
        failures = [
            item
            for item in audit.findings
            if item.rule_id == rule_id and item.status == "observed_failure"
        ]
        inconclusive = [
            item
            for item in (*audit.inconclusive, *audit.findings)
            if item.rule_id == rule_id
            and item.status in ("inconclusive", "untested")
        ]
        if audit.status == "unavailable":
            status: CriterionStatus = "error"
        elif audit.status == "not_attempted":
            status = "not_tested"
        elif failures:
            status = "fail"
        elif inconclusive:
            status = "needs_review"
        elif audit.status == "available" and checked_count == 0:
            status = "not_applicable"
        elif audit.status in ("available", "partial") and checked_count > 0:
            status = "pass"
        elif audit.status == "partial":
            status = "needs_review"
        else:
            status = "not_tested"
        observations[criterion_id].append(
            _Observation(
                viewport,
                status,
                "functional_ux",
                details=(
                    f"{len(failures)} observed {rule_id.replace('_', ' ')} failure(s)."
                    if failures
                    else "Bounded sampled check completed."
                    if status == "pass"
                    else None
                ),
                data=[_plain(item) for item in (*failures, *inconclusive)],
                confidence="high" if failures else "medium" if status == "pass" else None,
                limitations=tuple(audit.details)
                + (
                    (
                        f"{audit.excluded_non_http_links} non-HTTP link(s) were excluded from destination checks.",
                    )
                    if audit.excluded_non_http_links
                    else ()
                )
                + tuple(
                    limitation
                    for item in (*failures, *inconclusive)
                    for limitation in item.limitations
                ),
            )
        )


def _normalize_technical(
    result: ViewportCaptureResult,
    viewport: str,
    observations: dict[str, list[_Observation]],
) -> None:
    technical = result.technical_evidence
    observation_window_available = technical.status == "available" or (
        result.analyzer_execution_status in ("completed", "partial")
        and technical.status == "partial"
        and technical.access_status in ("accessible", "partial")
        and technical.readiness_status in ("ready", "partial")
    )
    observation_limitations = tuple(technical.details)
    if observation_window_available and technical.status == "partial":
        observation_limitations += (
            "No-error conclusions cover the usable portion of a partial capture, not events outside that observation window.",
        )
    categories = (
        (
            "technical.console_errors",
            "browser_console",
            technical.console_errors,
            False,
        ),
        (
            "technical.runtime_errors",
            "browser_runtime",
            technical.runtime_errors,
            True,
        ),
    )
    for criterion_id, analyzer_id, issues, definitive in categories:
        if issues:
            status: CriterionStatus = "fail" if definitive else "needs_review"
        elif technical.status == "unavailable":
            status = "error"
        elif technical.status == "not_tested":
            status = "not_tested"
        elif observation_window_available:
            status = "pass"
        else:
            status = "needs_review"
        observations[criterion_id].append(
            _Observation(
                viewport,
                status,
                analyzer_id,
                details=f"{len(issues)} browser error event(s) were recorded."
                if issues
                else "No browser error events were recorded during the observed capture window."
                if status == "pass"
                else "Browser error evidence is incomplete.",
                data=list(issues),
                confidence="high" if issues else "medium" if status == "pass" else None,
                limitations=observation_limitations
                + (
                    (
                        "A console.error event alone does not establish a user-facing defect; review its context. Uncaught page exceptions are tracked separately.",
                    )
                    if analyzer_id == "browser_console" and issues
                    else ()
                ),
            )
        )

    failed = technical.failed_requests
    first_party_http_failures = []
    review_failures = []
    for item in failed:
        if item.error and item.error.upper().startswith("HTTP "):
            if _same_origin(technical.page_url, item.url) is True:
                first_party_http_failures.append(item)
            else:
                review_failures.append(item)
        else:
            review_failures.append(item)
    if first_party_http_failures:
        network_status: CriterionStatus = "fail"
    elif review_failures:
        network_status = "needs_review"
    elif observation_window_available:
        network_status = "pass"
    elif technical.status == "unavailable":
        network_status = "error"
    elif technical.status == "not_tested":
        network_status = "not_tested"
    else:
        network_status = "needs_review"
    observations["technical.failed_requests"].append(
        _Observation(
            viewport,
            network_status,
            "browser_network",
            details=(
                f"{len(first_party_http_failures)} first-party HTTP failure(s), "
                f"{len(review_failures)} third-party or ambiguous request failure(s) were recorded."
                if failed
                else "No failed requests were recorded during the observed capture window."
                if network_status == "pass"
                else "Network request evidence is incomplete."
            ),
            data=[_plain(item) for item in failed],
            confidence="high" if first_party_http_failures else None,
            limitations=observation_limitations
            + (
                (
                    "Third-party HTTP failures, non-HTTP failures, and requests whose origin could not be established require review.",
                )
                if review_failures
                else ()
            ),
        )
    )

    capture_outcome = result.capture_outcome
    if capture_outcome == "capture_failed":
        capture_status: CriterionStatus = "error"
    elif capture_outcome in ("partial", "navigation_timeout"):
        capture_status = "needs_review"
    elif technical.status == "unavailable":
        capture_status = "error"
    elif capture_outcome == "completed" and technical.status == "available":
        capture_status = "pass"
    else:
        capture_status = "not_tested"
    observations["technical.capture_reliability"].append(
        _Observation(
            viewport,
            capture_status,
            "browser_capture",
            details=f"Capture outcome: {capture_outcome}.",
            data={
                "capture_outcome": capture_outcome,
                "technical_evidence": _plain(technical),
            },
            confidence="medium" if capture_status == "pass" else None,
            limitations=tuple(technical.details),
        )
    )


def _same_origin(page_url: str | None, request_url: str) -> bool | None:
    if not page_url:
        return None
    try:
        page = urlsplit(page_url)
        request = urlsplit(request_url)
        if page.scheme not in ("http", "https") or request.scheme not in ("http", "https"):
            return None
        if not page.hostname or not request.hostname:
            return None
        page_port = page.port or (443 if page.scheme == "https" else 80)
        request_port = request.port or (443 if request.scheme == "https" else 80)
    except ValueError:
        return None
    return (
        page.scheme.lower(),
        page.hostname.lower(),
        page_port,
    ) == (
        request.scheme.lower(),
        request.hostname.lower(),
        request_port,
    )


def _viewport_coverage(
    results: list[ViewportCaptureResult],
    observations: dict[str, list[_Observation]],
) -> dict[str, dict[str, Any]]:
    results_by_name = {result.name: result for result in results}
    coverage = {}
    for viewport in VIEWPORT_ORDER:
        result = results_by_name.get(viewport)
        if result is None:
            coverage[viewport] = {
                "name": viewport,
                "capture_outcome": "not_returned",
                "capture_completed": False,
                "analyzer_evidence_returned": False,
                "limitations": ["No capture result was returned for this viewport."],
            }
            continue
        viewport_observations = [
            observation
            for criterion_observations in observations.values()
            for observation in criterion_observations
            if observation.viewport == viewport
        ]
        analyzer_evidence_returned = any(
            item.status not in ("not_tested", "unsupported")
            for item in viewport_observations
        )
        limitations = _ordered_unique(
            [
                *result.details,
                *result.technical_evidence.details,
                *(
                    limitation
                    for observation in viewport_observations
                    for limitation in observation.limitations
                ),
            ]
        )
        if result.capture_outcome != "completed":
            limitations.append(
                f"Capture outcome was {result.capture_outcome}; viewport evidence may be incomplete."
            )
            limitations = _ordered_unique(limitations)
        coverage[viewport] = {
            "name": viewport,
            "capture_outcome": result.capture_outcome,
            "capture_completed": result.capture_outcome == "completed",
            "analyzer_evidence_returned": analyzer_evidence_returned,
            "limitations": limitations,
        }
    return coverage


def _score_dimension(
    dimension: DimensionConfig,
    criteria: list[dict[str, Any]],
    configuration: ScoringConfiguration,
) -> dict[str, Any]:
    selected = [item for item in criteria if item["dimension"] == dimension.dimension_id]
    applicable_items = [
        item for item in selected
        if dimension.implemented and item["implemented"]
        and item.get("score_eligible", True)
        and item["status"] != "not_applicable"
    ]
    counts = {status: 0 for status in _all_statuses()}
    for criterion in selected:
        counts[criterion["status"]] += 1
    applicable = len(applicable_items)
    conclusive = sum(item["status"] in ("pass", "fail") for item in applicable_items)
    coverage = round(conclusive / applicable * 100, 2) if applicable else None
    score_denominator = sum(
        item["weight"] for item in applicable_items if item["status"] in ("pass", "fail")
    )
    range_denominator = sum(
        item["weight"]
        for item in selected
        if dimension.implemented
        and item["implemented"]
        and item.get("score_eligible", True)
        and item["status"]
        in ("pass", "fail", "needs_review", "not_tested", "error", "unsupported")
    )
    passed_weight = sum(
        item["weight"] for item in applicable_items if item["status"] == "pass"
    )
    unresolved_weight = sum(
        item["weight"]
        for item in selected
        if item["implemented"]
        and item.get("score_eligible", True)
        and item["status"] in ("needs_review", "not_tested", "error", "unsupported")
    )
    raw_score = (
        round(
            sum(
                item["weight"]
                for item in applicable_items
                if item["status"] == "pass"
            )
            / score_denominator
            * 100,
            2,
        )
        if score_denominator
        else None
    )
    scoring_status = _dimension_status(
        dimension,
        coverage,
        raw_score,
        configuration,
    )
    score = raw_score if dimension.implemented else None
    return {
        "dimension_id": dimension.dimension_id,
        "name": dimension.name,
        "weight": dimension.weight,
        "implemented": dimension.implemented,
        "score": score,
        "score_basis": "conclusive_checks" if score is not None else None,
        "score_range": {
            "min": round(passed_weight / range_denominator * 100, 2)
            if range_denominator
            else None,
            "max": round(
                (passed_weight + unresolved_weight) / range_denominator * 100, 2
            )
            if range_denominator
            else None,
        },
        "coverage_percentage": coverage,
        "total_applicable_criteria": applicable,
        "conclusive_criteria": conclusive,
        "passed_criteria": counts["pass"],
        "failed_criteria": counts["fail"],
        "needs_review_criteria": counts["needs_review"],
        "not_tested_criteria": counts["not_tested"],
        "not_applicable_criteria": counts["not_applicable"],
        "unsupported_criteria": counts["unsupported"],
        "error_criteria": counts["error"],
        "coverage_label": (
            _threshold_label(coverage, configuration.coverage_thresholds)
            if coverage is not None
            else "not_available"
        ),
        "score_label": (
            _threshold_label(score, configuration.score_labels)
            if score is not None
            else None
        ),
        "scoring_status": scoring_status,
        "description": dimension.description,
    }


def _score_overall(
    dimensions: list[dict[str, Any]],
    criteria: list[dict[str, Any]],
    configuration: ScoringConfiguration,
) -> dict[str, Any]:
    implemented = [item for item in dimensions if item["implemented"]]
    # Coverage counts implemented applicable criteria, independently of score weights.
    coverage_denominator = sum(item["total_applicable_criteria"] for item in implemented)
    overall_coverage = (
        round(sum(item["conclusive_criteria"] for item in implemented)
              / coverage_denominator * 100, 2)
        if coverage_denominator else None
    )
    included = [
        item
        for item in implemented
        if item["score"] is not None
        and item["coverage_percentage"] is not None
        and item["conclusive_criteria"] > 0
    ]
    included_ids = {item["dimension_id"] for item in included}
    excluded = [
        {
            "dimension_id": item["dimension_id"],
            "reason": (
                "Dimension is not implemented."
                if not item["implemented"]
                else "Dimension has no applicable criteria."
                if item["coverage_percentage"] is None
                else "Dimension has no conclusive evidence."
                if item["conclusive_criteria"] == 0
                else "Dimension was excluded by configuration."
            ),
        }
        for item in dimensions
        if item["dimension_id"] not in included_ids
    ]
    denominator = sum(item["weight"] for item in included)
    aggregation_valid = all(
        math.isfinite(item["weight"]) and item["weight"] > 0
        and math.isfinite(item["score"]) and 0 <= item["score"] <= 100
        for item in included
    ) and all(
        math.isfinite(item["weight"]) and item["weight"] > 0
        for item in criteria
        if item["implemented"] and item["status"] in ("pass", "fail")
    )
    candidate_score = (
        round(
            sum(item["weight"] * item["score"] for item in included) / denominator,
            2,
        )
        if denominator > 0 and aggregation_valid
        else None
    )
    overall_score = candidate_score if (
        candidate_score is not None and math.isfinite(candidate_score)
        and 0 <= candidate_score <= 100 and denominator > 0
    ) else None
    all_dimensions_implemented = all(item["implemented"] for item in dimensions)
    overall_score_type = (
        "full_audit_score"
        if all_dimensions_implemented
        else "partial_audit_score"
    )
    overall_scoring_status = (
        "insufficient_evidence"
        if overall_score is None
        else _threshold_label(
            overall_coverage,
            tuple(
                (threshold, status)
                for threshold, status in configuration.score_validity_thresholds
            ),
        )
    )
    implemented_weight = sum(item["weight"] for item in implemented)
    included_weight = sum(item["weight"] for item in included)
    output = {
        "overall_score": overall_score,
        "overall_score_type": overall_score_type,
        "overall_coverage": overall_coverage,
        "minimum_overall_coverage": configuration.minimum_overall_coverage,
        "overall_scoring_status": overall_scoring_status,
        "included_dimensions": [item["dimension_id"] for item in included],
        "excluded_dimensions": excluded,
        "overall_score_label": (
            _threshold_label(overall_score, configuration.score_labels)
            if overall_score is not None
            else None
        ),
        "score_weight_basis": {
            "implemented_weight": implemented_weight,
            "included_weight": included_weight,
            "percentage": round(included_weight / implemented_weight * 100, 2)
            if implemented_weight
            else None,
        },
    }
    if overall_score is None:
        output["score_unavailable"] = _score_unavailable(
            dimensions, criteria, included, output, configuration
        )
    return output


def _dimension_diagnostics(
    dimension: dict[str, Any],
    criteria: list[dict[str, Any]],
) -> dict[str, Any]:
    selected = [
        item
        for item in criteria
        if item["dimension"] == dimension["dimension_id"]
    ]
    applicable = [
        item
        for item in selected
        if item["implemented"]
        and item["status"]
        in ("pass", "fail", "needs_review", "not_tested", "error", "unsupported")
    ]
    conclusive = [
        item for item in applicable if item["status"] in ("pass", "fail")
    ]
    conclusive_weight = sum(item["weight"] for item in conclusive)
    passed_weight = sum(
        item["weight"] for item in conclusive if item["status"] == "pass"
    )
    return {
        "dimension_id": dimension["dimension_id"],
        "applicable_weight": sum(item["weight"] for item in applicable),
        "conclusive_weight": conclusive_weight,
        "passed_weight": passed_weight,
        "failed_weight": sum(
            item["weight"] for item in conclusive if item["status"] == "fail"
        ),
        "coverage": dimension["coverage_percentage"],
        "raw_score": (
            round(passed_weight / conclusive_weight * 100, 2)
            if conclusive_weight
            else None
        ),
        "scoring_status": dimension["scoring_status"],
    }


def _score_unavailable(
    dimensions: list[dict[str, Any]],
    criteria: list[dict[str, Any]],
    included: list[dict[str, Any]],
    overall: dict[str, Any],
    configuration: ScoringConfiguration,
) -> dict[str, Any]:
    reasons = []
    if overall["overall_coverage"] is None:
        reasons.append("Overall coverage could not be calculated from available evidence.")
    reasons.append("No valid conclusive scoring evidence is available or aggregation is invalid.")
    if not included:
        reasons.append("No dimension currently meets the inclusion requirements.")
    dimension_details = []
    for dimension in dimensions:
        if not dimension["implemented"]:
            continue
        applicable_count = dimension["total_applicable_criteria"]
        conclusive_count = dimension["conclusive_criteria"]
        required_count = min(1, applicable_count)
        unresolved = [
            {
                "criterion_id": criterion["criterion_id"],
                "name": criterion["criterion_name"],
                "status": criterion["status"],
                "action": {
                    "needs_review": "Existing evidence needs manual review.",
                    "not_tested": "Run the missing check.",
                    "error": "Resolve the analyzer or capture error.",
                    "unsupported": "Run this implemented check in a supported environment.",
                }[criterion["status"]],
                "diagnostic": " ".join(criterion.get("limitations", []))[:500]
                if criterion["status"] == "error"
                else None,
            }
            for criterion in criteria
            if criterion["dimension"] == dimension["dimension_id"]
            and criterion["implemented"]
            and criterion["status"] in ("needs_review", "not_tested", "error", "unsupported")
        ]
        dimension_details.append(
            {
                "dimension_id": dimension["dimension_id"],
                "name": dimension["name"],
                "coverage_percentage": dimension["coverage_percentage"],
                "conclusive_criteria": conclusive_count,
                "required_conclusive_criteria": required_count,
                "additional_conclusive_criteria_needed": max(
                    0, required_count - conclusive_count
                ),
                "unresolved_criteria": unresolved,
            }
        )
    reasons.append(
        "Resolving the listed evidence gaps does not guarantee that an overall score will be available."
    )
    return {"reason": " ".join(reasons), "dimensions": dimension_details}


def _dimension_status(
    dimension: DimensionConfig,
    coverage: float | None,
    score: float | None,
    configuration: ScoringConfiguration,
) -> ScoringStatus:
    if not dimension.implemented:
        return "not_implemented"
    if coverage is None:
        return "not_scored"
    if score is None:
        return "insufficient_evidence"
    for threshold, status in configuration.score_validity_thresholds:
        if coverage >= threshold:
            return status
    return configuration.score_validity_thresholds[-1][1]


def _aggregate_status(statuses: Iterable[CriterionStatus]) -> CriterionStatus:
    values = list(statuses)
    for status in ("fail", "error", "needs_review", "not_tested"):
        if status in values:
            return status  # type: ignore[return-value]
    if "unsupported" in values and "pass" in values:
        return "needs_review"
    if "pass" in values:
        return "pass"
    if values and all(status == "not_applicable" for status in values):
        return "not_applicable"
    if values and all(status == "unsupported" for status in values):
        return "unsupported"
    return "not_tested"


def _criterion_confidence(
    status: CriterionStatus,
    observations: list[_Observation],
) -> Confidence | None:
    confidences = [
        item.confidence
        for item in observations
        if item.confidence is not None and item.status == status
    ]
    if not confidences:
        return "low" if status == "needs_review" else None
    if "low" in confidences:
        return "low"
    if "medium" in confidences:
        return "medium"
    return "high"


def _viewport_results(
    observations: list[_Observation],
    required_viewports: tuple[str, ...],
) -> list[dict[str, Any]]:
    by_viewport = {observation.viewport: observation for observation in observations}
    output = []
    for viewport in required_viewports:
        observation = by_viewport.get(viewport)
        if observation is None:
            output.append({"viewport": viewport, "status": "not_tested"})
            continue
        output.append(
            {
                "viewport": viewport,
                "status": observation.status,
                "analyzer_id": observation.analyzer_id,
                "reference": observation.reference,
                "details": observation.details,
                "confidence": observation.confidence,
                "limitations": list(observation.limitations),
            }
        )
    return output


def _merge_evidence(
    criterion_id: str,
    observations: list[_Observation],
) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for observation in observations:
        if observation.status in ("not_tested", "unsupported", "not_applicable"):
            continue
        values = _evidence_items(observation.data)
        if not values:
            values = [None]
        for value in values:
            reference = _evidence_reference(observation, value)
            normalized_value = _plain(value) if value is not None else None
            identity = {
                "criterion": criterion_id,
                "analyzer": observation.analyzer_id,
                "reference": reference,
                "status": observation.status,
                "data": normalized_value,
            }
            digest = hashlib.sha256(
                json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()[:20]
            current = merged.get(digest)
            if current is None:
                current = {
                    "evidence_id": f"{criterion_id}:{digest}",
                    "analyzer_id": observation.analyzer_id,
                    "reference": reference,
                    "status": observation.status,
                    "viewports": [],
                    "details": observation.details,
                    "data": normalized_value,
                    "confidence": observation.confidence,
                    "limitations": list(observation.limitations),
                }
                merged[digest] = current
            else:
                current["limitations"] = _ordered_unique(
                    [*current["limitations"], *observation.limitations]
                )
            if observation.viewport not in current["viewports"]:
                current["viewports"].append(observation.viewport)
    return sorted(
        merged.values(),
        key=lambda item: (
            tuple(VIEWPORT_ORDER.index(vp) for vp in item["viewports"]),
            item["evidence_id"],
        ),
    )


def _evidence_items(data: Any) -> list[Any]:
    if data is None:
        return []
    if isinstance(data, (list, tuple)):
        return list(data)
    return [data]


def _evidence_reference(observation: _Observation, value: Any) -> str | None:
    if observation.reference:
        return observation.reference
    if isinstance(value, dict):
        if value.get("rule_id") is not None and value.get("target") is not None:
            return f"{value['rule_id']}:{json.dumps(value['target'], sort_keys=True)}"
        for key in ("selector", "rule_id", "finding_id", "destination_url"):
            candidate = value.get(key)
            if candidate:
                return str(candidate)
    return observation.analyzer_id if value is None else None


def _rule_data(rule: AxeRuleEvidence) -> dict[str, Any]:
    return _plain(rule)


def _plain(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return _plain(asdict(value))
    if isinstance(value, dict):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _threshold_label(value: float, thresholds: tuple[tuple[float, str], ...]) -> str:
    for threshold, label in thresholds:
        if value >= threshold:
            return label
    return thresholds[-1][1]


def _ordered_unique(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    return [
        value
        for value in values
        if not (value in seen or seen.add(value))
    ]


def _all_statuses() -> tuple[str, ...]:
    return (
        "pass",
        "fail",
        "needs_review",
        "not_tested",
        "not_applicable",
        "unsupported",
        "error",
    )

import asyncio
import os
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from playwright.async_api import Error as PlaywrightError

from app.analyzers.audit_aggregation import (
    AggregationStatus,
    EvidencePriority,
    aggregate_audit_findings,
)
from app.analyzers.audit_summary import (
    build_audit_summary,
)
from app.analyzers.accessibility import AccessibilityScanStatus
from app.analyzers.accessibility import NonTextContrastStatus
from app.analyzers.element_horizontal_overflow import (
    ElementHorizontalOverflowEvidence,
)
from app.analyzers.finding_normalization import (
    NormalizedHorizontalOverflowFinding,
)
from app.analyzers.functional_ux import (
    FunctionalUXFailureCategory,
    FunctionalUXFindingStatus,
    FunctionalUXStatus,
    MAX_LINK_AUDIT_DURATION_SECONDS,
)
from app.analyzers.keyboard_focus import (
    AUDIT_TIMEOUT_SECONDS as KEYBOARD_AUDIT_TIMEOUT_SECONDS,
    KeyboardAuditStatus,
    KeyboardCheckStatus,
)
from app.analyzers.text_reflow import (
    HOVER_FOCUS_SCENARIO_TIMEOUT_SECONDS,
    SCENARIO_TIMEOUT_SECONDS as TEXT_REFLOW_SCENARIO_TIMEOUT_SECONDS,
    ScenarioClassification,
    ScenarioStatus,
    TextReflowAuditStatus,
)
from app.analyzers.accessibility import ACCESSIBILITY_SCAN_TIMEOUT_SECONDS
from app.analyzers.hybrid_evaluation import (
    FEATURE_IDS,
    FEATURE_LABELS,
    FEATURE_DISCOVERY_TIMEOUT_SECONDS,
    INITIAL_QUESTIONS,
    MAX_ANSWERS,
    MAX_JOURNEYS,
    MAX_CONTEXT_URLS,
    QUESTIONNAIRE_QUESTIONS,
    BrowserCriterionEvidence,
    OwnerAnswer,
    WCAG_CRITERION_IDS,
    build_hybrid_evaluation,
    sanitize_context_url,
    validate_owner_text,
    validate_questionnaire_inputs,
)
from app.analyzers.target_size import (
    AUDIT_TIMEOUT_SECONDS as TARGET_SIZE_AUDIT_TIMEOUT_SECONDS,
)
from app.capture.responsive import (
    ElementDiagnosisStatus,
    FindingNormalizationStatus,
    OverflowAnalysisStatus,
    ViewportCaptureOutcome,
    ViewportCaptureResult,
    capture_responsive_viewports,
)
from app.capture.runner import BrowserCapture, BrowserCaptureError
from app.capture.storage import LocalScreenshotStorage
from app.capture.url_safety import PublicURLSafetyValidator, UnsafeURL

OUTPUT_DIR = Path(os.getenv("WEBABLE_OUTPUT_DIR", "output"))
NAVIGATION_TIMEOUT_MS = int(os.getenv("WEBABLE_NAVIGATION_TIMEOUT_MS", "15000"))
SETTLING_PERIOD_MS = int(os.getenv("WEBABLE_SETTLING_PERIOD_MS", "1500"))
CAPTURE_TIMEOUT_SECONDS = (
    3
    * (
        NAVIGATION_TIMEOUT_MS
        + SETTLING_PERIOD_MS
        + MAX_LINK_AUDIT_DURATION_SECONDS * 1_000
        + 2 * ACCESSIBILITY_SCAN_TIMEOUT_SECONDS * 1_000
        + TARGET_SIZE_AUDIT_TIMEOUT_SECONDS * 1_000
        + KEYBOARD_AUDIT_TIMEOUT_SECONDS * 1_000
        + 17 * TEXT_REFLOW_SCENARIO_TIMEOUT_SECONDS * 1_000
        + HOVER_FOCUS_SCENARIO_TIMEOUT_SECONDS * 1_000
        + FEATURE_DISCOVERY_TIMEOUT_SECONDS * 1_000
    )
    / 1_000
    + 15
)
MAX_CONCURRENT_CAPTURES = 2

if sys.platform == "win32":
    asyncio.set_event_loop_policy(
        asyncio.WindowsProactorEventLoopPolicy()
    )

app = FastAPI(title="WebAble Browser Capture", version="0.1.0")
capture_slots = asyncio.Semaphore(MAX_CONCURRENT_CAPTURES)
url_validator = PublicURLSafetyValidator()
capture_service = BrowserCapture(
    storage=LocalScreenshotStorage(OUTPUT_DIR),
    url_validator=url_validator,
    navigation_timeout_ms=NAVIGATION_TIMEOUT_MS,
    settling_period_ms=SETTLING_PERIOD_MS,
)


class CaptureRequest(BaseModel):
    url: str = Field(min_length=1, max_length=4_096)
    accessibility_context: "AccessibilityContextRequest" = Field(
        default_factory=lambda: AccessibilityContextRequest()
    )


class OwnerAnswerRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_id: str = Field(min_length=1, max_length=100)
    answer: Literal["yes", "no", "not_sure", "not_applicable"]
    explanation: str | None = Field(default=None, max_length=2_000)
    page_urls: list[str] = Field(default_factory=list, max_length=MAX_CONTEXT_URLS)

    @field_validator("explanation")
    @classmethod
    def safe_explanation(cls, value: str | None) -> str | None:
        return validate_owner_text(value)

    @field_validator("page_urls")
    @classmethod
    def safe_page_urls(cls, values: list[str]) -> list[str]:
        return [sanitize_context_url(value) for value in values]


class UserJourneyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2_000)
    page_urls: list[str] = Field(default_factory=list, max_length=MAX_CONTEXT_URLS)

    @field_validator("name", "description")
    @classmethod
    def safe_journey_text(cls, value: str | None) -> str | None:
        return validate_owner_text(value)

    @field_validator("page_urls")
    @classmethod
    def safe_page_urls(cls, values: list[str]) -> list[str]:
        return [sanitize_context_url(value) for value in values]


class AccessibilityContextRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    representative_page_urls: list[str] = Field(
        default_factory=list, max_length=MAX_CONTEXT_URLS
    )
    user_journeys: list[UserJourneyRequest] = Field(
        default_factory=list, max_length=MAX_JOURNEYS
    )
    feature_presence: dict[str, bool | None] = Field(
        default_factory=dict, max_length=len(FEATURE_IDS)
    )
    feature_inventory_completed: bool = False
    answers: list[OwnerAnswerRequest] = Field(
        default_factory=list, max_length=MAX_ANSWERS
    )
    free_text: str | None = Field(default=None, max_length=2_000)

    @field_validator("representative_page_urls")
    @classmethod
    def safe_representative_urls(cls, values: list[str]) -> list[str]:
        return [sanitize_context_url(value) for value in values]

    @field_validator("free_text")
    @classmethod
    def safe_free_text(cls, value: str | None) -> str | None:
        return validate_owner_text(value)

    @model_validator(mode="after")
    def validate_questionnaire(self) -> "AccessibilityContextRequest":
        validate_questionnaire_inputs(
            answers=tuple(
                OwnerAnswer(
                    question_id=answer.question_id,
                    answer=answer.answer,
                    explanation=answer.explanation,
                    page_urls=tuple(answer.page_urls),
                )
                for answer in self.answers
            ),
            declared_features=self.feature_presence,
        )
        return self


CaptureRequest.model_rebuild()


class ViewportSchema(BaseModel):
    width: int
    height: int


class HorizontalOverflowSchema(BaseModel):
    scroll_width: int
    visible_width: int
    overflow_px: int
    potential_horizontal_overflow: bool


class ElementOverflowDiagnosisSchema(BaseModel):
    status: ElementDiagnosisStatus
    findings: list[ElementHorizontalOverflowEvidence]
    details: list[str]


class FunctionalUXFindingSchema(BaseModel):
    rule_id: Literal["broken_link", "failed_image"]
    element_selector: str
    accessible_label: str | None
    destination_url: str | None
    failure_category: FunctionalUXFailureCategory
    status: FunctionalUXFindingStatus
    evidence: list[str]
    limitations: list[str]


class FunctionalUXAuditSchema(BaseModel):
    status: FunctionalUXStatus
    findings: list[FunctionalUXFindingSchema]
    inconclusive: list[FunctionalUXFindingSchema]
    checked_links: int
    checked_images: int
    details: list[str]


class AxeCheckSchema(BaseModel):
    check_id: str
    impact: str | None
    message: str
    data: dict | list | str | int | float | bool | None
    related_nodes: list[dict]


class AxeNodeSchema(BaseModel):
    target: list[str | list[str]]
    html: str
    impact: str | None
    failure_summary: str | None
    any_checks: list[AxeCheckSchema]
    all_checks: list[AxeCheckSchema]
    none_checks: list[AxeCheckSchema]


class AxeRuleSchema(BaseModel):
    rule_id: str
    description: str
    impact: str | None
    help: str
    help_url: str
    tags: list[str]
    nodes: list[AxeNodeSchema]
    failure_summaries: list[str]


class NonTextContrastFindingSchema(BaseModel):
    classification: Literal["needs_review"]
    potential_issue_detected: Literal[True]
    confirmed_violation: Literal[False]
    manual_review_required: Literal[True]
    selector: str
    tag_name: str
    role: str | None
    geometry: dict[str, float]
    viewport: dict[str, int]
    color_pairs: list[dict]
    limitations: list[str]


class NonTextContrastAuditSchema(BaseModel):
    status: NonTextContrastStatus
    inspected_components: int
    inspected_graphics: int
    findings: list[NonTextContrastFindingSchema]
    details: list[str]


class AccessibilityScanSchema(BaseModel):
    status: AccessibilityScanStatus
    axe_version: str | None
    violations: list[AxeRuleSchema]
    incomplete: list[AxeRuleSchema]
    passes: list[AxeRuleSchema]
    inapplicable: list[AxeRuleSchema]
    non_text_contrast: NonTextContrastAuditSchema
    details: list[str]


class KeyboardFocusEvidenceSchema(BaseModel):
    selector: str
    tag_name: str
    accessible_name: str | None
    role: str | None
    discovery_status: Literal["initial_candidate", "outside_initial_snapshot"]
    sequence_index: int
    focus_indicator_detected: bool | None
    focus_visible_pseudo_class: bool | None
    focus_indicator_evidence: dict[str, str]
    obscured: bool | None
    partially_obscured: bool
    occluding_selector: str | None
    target_rect: dict[str, float]
    viewport: dict[str, int]
    occlusion_status: Literal[
        "confirmed_failure",
        "potential_issue",
        "no_issue_detected",
        "not_evaluated",
    ]
    occluding_evidence: list[dict]
    details: list[str]


class KeyboardCheckSchema(BaseModel):
    check_id: str
    criterion_ids: list[str]
    status: KeyboardCheckStatus
    summary: str
    evidence: list[dict]


class KeyboardFocusAuditSchema(BaseModel):
    status: KeyboardAuditStatus
    checks: list[KeyboardCheckSchema]
    findings: list[KeyboardFocusEvidenceSchema]
    details: list[str]
    candidate_limitations: list[str]
    late_candidates: list[str]
    unexpected_focus_targets: list[str]
    tab_actions: int
    shift_tab_actions: int


class TextReflowMeasurementSchema(BaseModel):
    viewport_width: int
    viewport_height: int
    window_inner_width: int
    window_inner_height: int
    document_scroll_width: int
    document_scroll_height: int
    document_horizontal_overflow_px: int
    overflow_boundaries: list[dict]
    inspected_text_elements: int


class TextReflowFindingSchema(BaseModel):
    criterion_id: str
    level: Literal["AA"]
    classification: Literal["violation", "needs_review"]
    selector: str
    tag_name: str
    observation: str
    evidence: dict
    baseline_evidence: dict | None
    confidence: Literal["high", "medium", "low"]
    remediation: str
    screenshot_ref: str | None


class TextReflowScenarioSchema(BaseModel):
    scenario_id: str
    status: ScenarioStatus
    classification: ScenarioClassification
    condition: str
    method: str
    criterion_ids: list[str]
    viewport_width: int | None
    viewport_height: int | None
    measurement: TextReflowMeasurementSchema | None
    baseline_measurement: TextReflowMeasurementSchema | None
    findings: list[TextReflowFindingSchema]
    screenshot_ref: str | None
    details: list[str]


class TextReflowAuditSchema(BaseModel):
    status: TextReflowAuditStatus
    scenarios: list[TextReflowScenarioSchema]
    details: list[str]


class TargetSizeFindingSchema(BaseModel):
    criterion_id: Literal["2.5.8"]
    selector: str
    tag_name: str
    role: str | None
    accessible_name: str | None
    width_css_px: float
    height_css_px: float
    left_css_px: float
    top_css_px: float
    classification: Literal["needs_review"]


class TargetSizeAuditSchema(BaseModel):
    status: Literal["available", "partial", "unavailable", "not_tested"]
    inspected_targets: int
    findings: list[TargetSizeFindingSchema]
    details: list[str]


class BrowserFeatureEvidenceSchema(BaseModel):
    feature_id: str
    detected: bool
    count: int
    viewport: str
    evidence: list[str]


class BrowserFeatureDiscoverySchema(BaseModel):
    status: Literal["available", "partial", "unavailable", "not_attempted"]
    features: list[BrowserFeatureEvidenceSchema]
    details: list[str]


class NormalizedFindingsSchema(BaseModel):
    status: FindingNormalizationStatus
    findings: list[NormalizedHorizontalOverflowFinding]
    details: list[str]


class AuditFindingGroupSchema(BaseModel):
    group_id: str
    rule_id: str
    selector: str
    priority: EvidencePriority
    explanation: str
    affected_viewports: list[str]
    findings: list[NormalizedHorizontalOverflowFinding]


class AuditFindingAggregationSchema(BaseModel):
    status: AggregationStatus
    findings: list[AuditFindingGroupSchema]
    details: list[str]


class ViewportMeasurementSchema(BaseModel):
    name: str
    width: int
    overflow_px: int


class DocumentOverflowSummarySchema(BaseModel):
    status: Literal["available", "partial", "unavailable"]
    detected: bool | None
    affected_viewports: list[str]
    measurements: list[ViewportMeasurementSchema]


class IssueViewportSchema(BaseModel):
    name: str
    width: int


class IssueMeasurementSchema(BaseModel):
    finding_id: str
    viewport_name: str
    viewport_width: int
    element_overflow_px: float
    document_overflow_px: int | None
    evidence_correlation: Literal[
        "direct_geometry_match", "possible_contributor", "unmatched"
    ]


class AuditSummaryIssueSchema(BaseModel):
    group_id: str
    rule_id: str
    selector: str
    priority: EvidencePriority
    title: str
    affected_viewports: list[IssueViewportSchema]
    measurements: list[IssueMeasurementSchema]
    explanation: str


class AuditSummarySchema(BaseModel):
    status: Literal["available", "partial", "unavailable"]
    horizontal_overflow_detected: bool | None
    affected_viewports: list[str]
    document_level_overflow: DocumentOverflowSummarySchema
    issues: list[AuditSummaryIssueSchema]
    limitations: list[str]


class ResponsiveViewportResponse(BaseModel):
    name: str
    viewport: ViewportSchema
    capture_outcome: ViewportCaptureOutcome
    horizontal_overflow: HorizontalOverflowSchema | None
    overflow_analysis_status: OverflowAnalysisStatus
    element_overflow_diagnosis: ElementOverflowDiagnosisSchema
    functional_ux_audit: FunctionalUXAuditSchema
    accessibility_scan: AccessibilityScanSchema
    keyboard_focus_audit: KeyboardFocusAuditSchema
    text_reflow_audit: TextReflowAuditSchema
    target_size_audit: TargetSizeAuditSchema
    browser_feature_discovery: BrowserFeatureDiscoverySchema
    finding_normalization: NormalizedFindingsSchema
    screenshot_ref: str | None
    details: list[str]


class ResponsiveCaptureResponse(BaseModel):
    requested_url: str
    viewports: list[ResponsiveViewportResponse]
    hybrid_evaluation: dict
    audit_findings: AuditFindingAggregationSchema
    audit_summary: AuditSummarySchema

    @classmethod
    def from_results(
        cls,
        requested_url: str,
        results: list[ViewportCaptureResult],
        accessibility_context: AccessibilityContextRequest | None = None,
    ) -> "ResponsiveCaptureResponse":
        accessibility_context = accessibility_context or AccessibilityContextRequest()
        aggregation = aggregate_audit_findings(
            [
                finding
                for result in results
                for finding in result.finding_normalization.findings
            ],
            normalization_statuses=[
                result.finding_normalization.status for result in results
            ],
        )
        summary = build_audit_summary(aggregation, results)
        browser_discoveries = tuple(
            result.browser_feature_discovery for result in results
        )
        browser_checks = _browser_criterion_evidence(results)
        hybrid_evaluation = build_hybrid_evaluation(
            declared_features=accessibility_context.feature_presence,
            feature_inventory_completed=(
                accessibility_context.feature_inventory_completed
            ),
            answers=tuple(
                OwnerAnswer(
                    question_id=answer.question_id,
                    answer=answer.answer,
                    explanation=answer.explanation,
                    page_urls=tuple(answer.page_urls),
                )
                for answer in accessibility_context.answers
            ),
            browser_discoveries=browser_discoveries,
            browser_checks=browser_checks,
            representative_page_urls=tuple(
                accessibility_context.representative_page_urls
            ),
            journeys=tuple(
                journey.model_dump()
                for journey in accessibility_context.user_journeys
            ),
            free_text=accessibility_context.free_text,
        )
        return cls(
            requested_url=requested_url,
            hybrid_evaluation=hybrid_evaluation,
            audit_summary=AuditSummarySchema(
                status=summary.status,
                horizontal_overflow_detected=summary.horizontal_overflow_detected,
                affected_viewports=summary.affected_viewports,
                document_level_overflow=DocumentOverflowSummarySchema(
                    status=summary.document_level_overflow.status,
                    detected=summary.document_level_overflow.detected,
                    affected_viewports=summary.document_level_overflow.affected_viewports,
                    measurements=[
                        ViewportMeasurementSchema(
                            name=measurement.name,
                            width=measurement.width,
                            overflow_px=measurement.overflow_px,
                        )
                        for measurement in summary.document_level_overflow.measurements
                    ],
                ),
                issues=[
                    AuditSummaryIssueSchema(
                        group_id=issue.group_id,
                        rule_id=issue.rule_id,
                        selector=issue.selector,
                        priority=issue.priority,
                        title=issue.title,
                        affected_viewports=[
                            IssueViewportSchema(
                                name=viewport.name, width=viewport.width
                            )
                            for viewport in issue.affected_viewports
                        ],
                        measurements=[
                            IssueMeasurementSchema(
                                finding_id=measurement.finding_id,
                                viewport_name=measurement.viewport_name,
                                viewport_width=measurement.viewport_width,
                                element_overflow_px=measurement.element_overflow_px,
                                document_overflow_px=measurement.document_overflow_px,
                                evidence_correlation=measurement.evidence_correlation,
                            )
                            for measurement in issue.measurements
                        ],
                        explanation=issue.explanation,
                    )
                    for issue in summary.issues
                ],
                limitations=summary.limitations,
            ),
            audit_findings=AuditFindingAggregationSchema(
                status=aggregation.status,
                findings=[
                    AuditFindingGroupSchema(
                        group_id=group.group_id,
                        rule_id=group.rule_id,
                        selector=group.selector,
                        priority=group.priority,
                        explanation=group.explanation,
                        affected_viewports=group.affected_viewports,
                        findings=group.findings,
                    )
                    for group in aggregation.findings
                ],
                details=aggregation.details,
            ),
            viewports=[
                ResponsiveViewportResponse(
                    name=result.name,
                    viewport=ViewportSchema(
                        width=result.viewport.width, height=result.viewport.height
                    ),
                    capture_outcome=result.capture_outcome,
                    horizontal_overflow=(
                        HorizontalOverflowSchema(
                            scroll_width=result.horizontal_overflow.scroll_width,
                            visible_width=result.horizontal_overflow.visible_width,
                            overflow_px=result.horizontal_overflow.overflow_px,
                            potential_horizontal_overflow=(
                                result.horizontal_overflow.potential_horizontal_overflow
                            ),
                        )
                        if result.horizontal_overflow is not None
                        else None
                    ),
                    overflow_analysis_status=result.overflow_analysis_status,
                    element_overflow_diagnosis=ElementOverflowDiagnosisSchema(
                        status=result.element_overflow_diagnosis.status,
                        findings=result.element_overflow_diagnosis.findings,
                        details=result.element_overflow_diagnosis.details,
                    ),
                    functional_ux_audit=FunctionalUXAuditSchema(
                        status=result.functional_ux_audit.status,
                        findings=[
                            FunctionalUXFindingSchema(**asdict(finding))
                            for finding in result.functional_ux_audit.findings
                        ],
                        inconclusive=[
                            FunctionalUXFindingSchema(**asdict(finding))
                            for finding in result.functional_ux_audit.inconclusive
                        ],
                        checked_links=result.functional_ux_audit.checked_links,
                        checked_images=result.functional_ux_audit.checked_images,
                        details=result.functional_ux_audit.details,
                    ),
                    accessibility_scan=AccessibilityScanSchema(
                        status=result.accessibility_scan.status,
                        axe_version=result.accessibility_scan.axe_version,
                        violations=[
                            AxeRuleSchema(**asdict(rule))
                            for rule in result.accessibility_scan.violations
                        ],
                        incomplete=[
                            AxeRuleSchema(**asdict(rule))
                            for rule in result.accessibility_scan.incomplete
                        ],
                        passes=[
                            AxeRuleSchema(**asdict(rule))
                            for rule in result.accessibility_scan.passes
                        ],
                        inapplicable=[
                            AxeRuleSchema(**asdict(rule))
                            for rule in result.accessibility_scan.inapplicable
                        ],
                        non_text_contrast=NonTextContrastAuditSchema(
                            **asdict(result.accessibility_scan.non_text_contrast)
                        ),
                        details=result.accessibility_scan.details,
                    ),
                    keyboard_focus_audit=KeyboardFocusAuditSchema(
                        status=result.keyboard_focus_audit.status,
                        checks=[
                            KeyboardCheckSchema(**asdict(check))
                            for check in result.keyboard_focus_audit.checks
                        ],
                        findings=[
                            KeyboardFocusEvidenceSchema(**asdict(finding))
                            for finding in result.keyboard_focus_audit.findings
                        ],
                        details=result.keyboard_focus_audit.details,
                        candidate_limitations=(
                            result.keyboard_focus_audit.candidate_limitations
                        ),
                        late_candidates=result.keyboard_focus_audit.late_candidates,
                        unexpected_focus_targets=(
                            result.keyboard_focus_audit.unexpected_focus_targets
                        ),
                        tab_actions=result.keyboard_focus_audit.tab_actions,
                        shift_tab_actions=result.keyboard_focus_audit.shift_tab_actions,
                    ),
                    text_reflow_audit=TextReflowAuditSchema(
                        status=result.text_reflow_audit.status,
                        scenarios=[
                            TextReflowScenarioSchema(**asdict(scenario))
                            for scenario in result.text_reflow_audit.scenarios
                        ],
                        details=result.text_reflow_audit.details,
                    ),
                    target_size_audit=TargetSizeAuditSchema(
                        status=result.target_size_audit.status,
                        inspected_targets=result.target_size_audit.inspected_targets,
                        findings=[
                            TargetSizeFindingSchema(**asdict(finding))
                            for finding in result.target_size_audit.findings
                        ],
                        details=result.target_size_audit.details,
                    ),
                    browser_feature_discovery=BrowserFeatureDiscoverySchema(
                        status=result.browser_feature_discovery.status,
                        features=[
                            BrowserFeatureEvidenceSchema(
                                feature_id=feature.feature_id,
                                detected=feature.detected,
                                count=feature.count,
                                viewport=feature.viewport,
                                evidence=list(feature.evidence),
                            )
                            for feature in result.browser_feature_discovery.features
                        ],
                        details=list(result.browser_feature_discovery.details),
                    ),
                    finding_normalization=NormalizedFindingsSchema(
                        status=result.finding_normalization.status,
                        findings=result.finding_normalization.findings,
                        details=result.finding_normalization.details,
                    ),
                    screenshot_ref=result.screenshot_ref,
                    details=result.details,
                )
                for result in results
            ],
        )


def _browser_criterion_evidence(
    results: list[ViewportCaptureResult],
) -> tuple[BrowserCriterionEvidence, ...]:
    criterion_tags = {
        criterion_id: f"wcag{criterion_id.replace('.', '')}"
        for criterion_id in WCAG_CRITERION_IDS
    }
    evidence: list[BrowserCriterionEvidence] = []
    for result in results:
        viewport = result.name
        accessibility = result.accessibility_scan
        for result_kind in ("violations", "incomplete", "passes", "inapplicable"):
            for rule in getattr(accessibility, result_kind):
                matched_criteria = [
                    criterion_id
                    for criterion_id, tag in criterion_tags.items()
                    if tag in rule.tags
                ]
                for criterion_id in matched_criteria:
                    evidence.append(
                        BrowserCriterionEvidence(
                            criterion_id=criterion_id,
                            analyzer_id=f"axe:{rule.rule_id}",
                            result_status=result_kind,
                            viewport=viewport,
                            summary=rule.description,
                            evidence_count=len(rule.nodes),
                        )
                    )

        for check in result.keyboard_focus_audit.checks:
            if check.status in ("error", "not_tested"):
                continue
            for criterion_id in check.criterion_ids:
                evidence.append(
                    BrowserCriterionEvidence(
                        criterion_id=criterion_id,
                        analyzer_id=f"keyboard_focus:{check.check_id}",
                        result_status=check.status,
                        viewport=viewport,
                        summary=check.summary,
                        evidence_count=len(check.evidence),
                    )
                )

        for scenario in result.text_reflow_audit.scenarios:
            if scenario.status != "completed":
                continue
            for criterion_id in scenario.criterion_ids:
                evidence.append(
                    BrowserCriterionEvidence(
                        criterion_id=criterion_id,
                        analyzer_id=f"text_reflow:{scenario.scenario_id}",
                        result_status=scenario.classification,
                        viewport=viewport,
                        summary=scenario.condition,
                        evidence_count=len(scenario.findings),
                    )
                )

        if result.accessibility_scan.non_text_contrast.status not in (
            "not_tested",
            "unavailable",
        ):
            evidence.append(
                BrowserCriterionEvidence(
                    criterion_id="1.4.11",
                    analyzer_id="non_text_contrast",
                    result_status=result.accessibility_scan.non_text_contrast.status,
                    viewport=viewport,
                    summary="Supplemental computed-color sampling; findings require manual review.",
                    evidence_count=len(
                        result.accessibility_scan.non_text_contrast.findings
                    ),
                )
            )

        if result.target_size_audit.status not in ("not_tested", "unavailable"):
            evidence.append(
                BrowserCriterionEvidence(
                    criterion_id="2.5.8",
                    analyzer_id="target_size",
                    result_status=result.target_size_audit.status,
                    viewport=viewport,
                    summary="Measured pointer target dimensions; exceptions and spacing are not fully evaluated.",
                    evidence_count=len(result.target_size_audit.findings),
                )
            )
    return tuple(evidence)


class CaptureErrorResponse(BaseModel):
    outcome: Literal["invalid_or_prohibited_url", "browser_failure"]
    detail: str


class CaptureErrorEnvelope(BaseModel):
    detail: CaptureErrorResponse


@app.post(
    "/captures",
    response_model=ResponsiveCaptureResponse,
    responses={
        400: {"model": CaptureErrorEnvelope},
        502: {"model": CaptureErrorEnvelope},
    },
)
async def create_capture(request: CaptureRequest) -> ResponsiveCaptureResponse:
    try:
        await url_validator.validate(request.url)

        async def run_responsive_capture():
            async with capture_slots:
                return await capture_responsive_viewports(
                    request.url,
                    capture_service.capture,
                    destination_validator=url_validator,
                    scenario_screenshot_capture=(
                        capture_service.save_scenario_screenshot
                    ),
                )

        results = await asyncio.wait_for(
            run_responsive_capture(),
            timeout=CAPTURE_TIMEOUT_SECONDS,
        )
    except UnsafeURL as error:
        raise HTTPException(
            status_code=400,
            detail=CaptureErrorResponse(
                outcome="invalid_or_prohibited_url", detail=str(error)
            ).model_dump(),
        ) from error
    except TimeoutError as error:
        raise HTTPException(
            status_code=502,
            detail=CaptureErrorResponse(
                outcome="browser_failure",
                detail="The capture exceeded its overall time limit.",
            ).model_dump(),
        ) from error
    except BrowserCaptureError as error:
        raise HTTPException(
            status_code=502,
            detail=CaptureErrorResponse(
                outcome="browser_failure", detail=str(error)
            ).model_dump(),
        ) from error
    except PlaywrightError as error:
        raise HTTPException(
            status_code=502,
            detail=CaptureErrorResponse(
                outcome="browser_failure",
                detail="Chromium failed while preparing the capture.",
            ).model_dump(),
        ) from error
    return ResponsiveCaptureResponse.from_results(
        request.url,
        results,
        accessibility_context=request.accessibility_context,
    )


@app.get("/accessibility/questionnaire")
async def get_accessibility_questionnaire() -> dict:
    return {
        "version": "1.0",
        "features": [
            {"feature_id": feature_id, "label": FEATURE_LABELS[feature_id]}
            for feature_id in FEATURE_IDS
        ],
        "feature_inventory_completed_field": "accessibility_context.feature_inventory_completed",
        "initial_questions": [
            {
                "question_id": question.question_id,
                "criterion_ids": list(question.criterion_ids),
                "feature_id": question.feature_id,
                "prompt": question.prompt,
                "answer_options": list(question.answer_options),
                "helper_text": question.helper_text,
            }
            for question in INITIAL_QUESTIONS
        ],
        "conditional_questions": [
            {
                "question_id": question.question_id,
                "criterion_ids": list(question.criterion_ids),
                "feature_id": question.feature_id,
                "prompt": question.prompt,
                "answer_options": list(question.answer_options),
                "helper_text": question.helper_text,
            }
            for question in QUESTIONNAIRE_QUESTIONS
        ],
        "safety_notice": (
            "Do not submit passwords, credentials, personal or customer data, "
            "access tokens, or secrets. Answers are contextual information and "
            "are not proof of WCAG conformance."
        ),
    }


app.mount(
    "/static",
    StaticFiles(directory=Path(__file__).resolve().parent / "static"),
    name="static",
)
app.mount(
    "/",
    StaticFiles(directory=Path(__file__).resolve().parent / "static", html=True),
    name="frontend",
)

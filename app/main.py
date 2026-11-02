import asyncio
import os
import re
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import time
import logging
from uuid import uuid4
from dataclasses import asdict
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
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
    question_answer_interpretation,
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
from app.capture.models import AccessStatus, NavigationStatus, ReadinessStatus
from app.analyzers.scoring import build_audit_scoring
from app.capture.runner import (
    BrowserCapture,
    BrowserCaptureError,
    NAVIGATION_TIMEOUT_MS as DEFAULT_NAVIGATION_TIMEOUT_MS,
    SETTLING_PERIOD_MS as DEFAULT_SETTLING_PERIOD_MS,
    READINESS_TIMEOUT_MS,
    NETWORK_IDLE_SIGNAL_MS,
    LAZY_SCROLL_MAX_MS,
)
from app.capture.storage import LocalScreenshotStorage
from app.capture.url_safety import PublicURLSafetyValidator, UnsafeURL

OUTPUT_DIR = Path(os.getenv("WEBABLE_OUTPUT_DIR", "output"))
def _bounded_timeout(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        value = default
    return max(minimum, min(maximum, value))


NAVIGATION_TIMEOUT_MS = _bounded_timeout("WEBABLE_NAVIGATION_TIMEOUT_MS", DEFAULT_NAVIGATION_TIMEOUT_MS, 1_000, 60_000)
SETTLING_PERIOD_MS = _bounded_timeout("WEBABLE_SETTLING_PERIOD_MS", DEFAULT_SETTLING_PERIOD_MS, 250, 15_000)
_DEFAULT_CAPTURE_TIMEOUT_SECONDS = int((
    3
    * (
        NAVIGATION_TIMEOUT_MS
        + SETTLING_PERIOD_MS
        + READINESS_TIMEOUT_MS
        + NETWORK_IDLE_SIGNAL_MS
        + LAZY_SCROLL_MAX_MS
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
))
CAPTURE_TIMEOUT_SECONDS = _bounded_timeout(
    "WEBABLE_CAPTURE_TIMEOUT_SECONDS", _DEFAULT_CAPTURE_TIMEOUT_SECONDS, 60, 600
)
MAX_CONCURRENT_CAPTURES = max(1, int(os.getenv("WEBABLE_MAX_CONCURRENT_CAPTURES", "1")))
MAX_PENDING_CAPTURES = max(1, int(os.getenv("WEBABLE_MAX_PENDING_CAPTURES", "20")))
JOB_RETENTION_SECONDS = 900
capture_jobs: dict[str, dict] = {}
capture_tasks: set[asyncio.Task] = set()

if sys.platform == "win32":
    asyncio.set_event_loop_policy(
        asyncio.WindowsProactorEventLoopPolicy()
    )

capture_slots = asyncio.Semaphore(MAX_CONCURRENT_CAPTURES)
url_validator = PublicURLSafetyValidator()
capture_service = BrowserCapture(
    storage=LocalScreenshotStorage(OUTPUT_DIR),
    url_validator=url_validator,
    navigation_timeout_ms=NAVIGATION_TIMEOUT_MS,
    settling_period_ms=SETTLING_PERIOD_MS,
    reuse_browser=True,
)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    try:
        yield
    finally:
        await capture_service.close()


app = FastAPI(
    title="WebAble Browser Capture",
    version="0.1.0",
    lifespan=lifespan,
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
    excluded_non_http_links: int
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
    discovered_text_elements: int
    max_inspected_elements: int
    candidates_truncated: bool


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
    findings_truncated: bool
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


class FailedRequestSchema(BaseModel):
    url: str
    resource_type: str
    error: str | None


class TechnicalEvidenceSchema(BaseModel):
    status: Literal["available", "partial", "unavailable", "not_tested"]
    page_url: str | None = None
    navigation_status: NavigationStatus | None
    readiness_status: ReadinessStatus | None
    console_errors: list[str]
    runtime_errors: list[str]
    failed_requests: list[FailedRequestSchema]
    redirect_chains: list[list[str]] = Field(default_factory=list)
    unloaded_image_count: int | None = None
    loading_indicator_count: int | None = None
    visible_content_characters: int = 0
    access_restriction_signals: list[str] = Field(default_factory=list)
    access_restriction_provider: str | None = None
    access_restriction_reference: str | None = None
    main_document_http_status: int | None = None
    access_status: AccessStatus = "unavailable"
    primary_content_characters: int = 0
    primary_content_items: int = 0
    readiness_elapsed_ms: int = 0
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


class ScoringDimensionSchema(BaseModel):
    dimension_id: str
    name: str
    weight: float
    implemented: bool
    score: float | None
    score_basis: Literal["conclusive_checks"] | None
    score_range: dict[str, float | None]
    coverage_percentage: float | None
    total_applicable_criteria: int
    conclusive_criteria: int
    passed_criteria: int
    failed_criteria: int
    needs_review_criteria: int
    not_tested_criteria: int
    not_applicable_criteria: int
    unsupported_criteria: int
    error_criteria: int
    coverage_label: str
    score_label: str | None
    scoring_status: str
    description: str


class ScoringCriterionEvidenceSchema(BaseModel):
    evidence_id: str
    analyzer_id: str
    reference: str | None
    status: str
    viewports: list[str]
    details: str | None
    data: dict | list | str | int | float | bool | None
    confidence: str | None
    limitations: list[str] = Field(default_factory=list)


class ScoringViewportResultSchema(BaseModel):
    viewport: str
    status: str
    analyzer_id: str | None = None
    reference: str | None = None
    details: str | None = None
    confidence: str | None = None
    limitations: list[str] = Field(default_factory=list)


class ScoringCriterionSchema(BaseModel):
    criterion_id: str
    criterion_name: str
    dimension: str
    status: str
    implemented: bool
    weight: float
    evidence_strength: Literal["deterministic", "bounded_probe", "heuristic"]
    wcag_references: list[str]
    level: str | None
    principle: str | None
    tested_viewports: list[str]
    affected_viewports: list[str]
    evidence_count: int
    failure_count: int
    review_count: int
    confidence: str | None
    evidence: list[ScoringCriterionEvidenceSchema]
    limitations: list[str]
    analyzer_ids: list[str]
    viewport_results: list[ScoringViewportResultSchema]
    description: str
    applicable_conditions: str | None


class ExcludedDimensionSchema(BaseModel):
    dimension_id: str
    reason: str


class AuditScoringSchema(BaseModel):
    overall_score: float | None
    overall_score_type: Literal["full_audit_score", "partial_audit_score"]
    overall_coverage: float | None
    minimum_overall_coverage: float
    score_weight_basis: dict[str, float | None]
    score_unavailable: dict | None = None
    status_counts: dict[str, int]
    viewport_coverage: dict[str, dict]
    overall_scoring_status: str
    included_dimensions: list[str]
    excluded_dimensions: list[ExcludedDimensionSchema]
    overall_score_label: str | None
    dimensions: list[ScoringDimensionSchema]
    criteria: list[ScoringCriterionSchema]
    scoring_configuration_version: str
    limitations: list[str]


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
    analyzer_execution_status: Literal["completed", "partial", "not_run"] = "not_run"
    horizontal_overflow: HorizontalOverflowSchema | None
    overflow_analysis_status: OverflowAnalysisStatus
    element_overflow_diagnosis: ElementOverflowDiagnosisSchema
    functional_ux_audit: FunctionalUXAuditSchema
    accessibility_scan: AccessibilityScanSchema
    keyboard_focus_audit: KeyboardFocusAuditSchema
    text_reflow_audit: TextReflowAuditSchema
    target_size_audit: TargetSizeAuditSchema
    technical_evidence: TechnicalEvidenceSchema
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
    scoring: AuditScoringSchema

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
        scoring = build_audit_scoring(results)
        return cls(
            requested_url=requested_url,
            hybrid_evaluation=hybrid_evaluation,
            scoring=AuditScoringSchema(**scoring),
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
                    analyzer_execution_status=result.analyzer_execution_status,
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
                        excluded_non_http_links=(
                            result.functional_ux_audit.excluded_non_http_links
                        ),
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
                    technical_evidence=TechnicalEvidenceSchema(
                        **asdict(result.technical_evidence)
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
    screenshot_dir = capture_service._storage._directory
    existing_screenshots = (
        {path.name for path in screenshot_dir.iterdir() if path.is_file()}
        if screenshot_dir.is_dir()
        else set()
    )
    retained_screenshots: set[str] = set()
    try:
        await url_validator.validate(request.url)

        # Queue waiting must not consume the browser execution time budget.
        async with capture_slots:
            results = await asyncio.wait_for(
                capture_responsive_viewports(
                    request.url,
                    capture_service.capture,
                    destination_validator=url_validator,
                    scenario_screenshot_capture=(
                        capture_service.save_scenario_screenshot
                    ),
                ),
                timeout=CAPTURE_TIMEOUT_SECONDS,
            )
        response = ResponsiveCaptureResponse.from_results(
            request.url,
            results,
            accessibility_context=request.accessibility_context,
        )
        retained_screenshots = _screenshot_references(response.model_dump(mode="json"))
        return response
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
    finally:
        if os.getenv("VERCEL"):
            _cleanup_unreferenced_screenshots(
                screenshot_dir, existing_screenshots, retained_screenshots
            )


def _screenshot_references(value) -> set[str]:
    references: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            if key.endswith("screenshot_ref") and isinstance(item, str):
                references.add(Path(item).name)
            else:
                references.update(_screenshot_references(item))
    elif isinstance(value, list):
        for item in value:
            references.update(_screenshot_references(item))
    return references


def _cleanup_unreferenced_screenshots(
    directory: Path, existing: set[str], retained: set[str]
) -> None:
    if not directory.is_dir():
        return
    for path in directory.iterdir():
        if path.is_file() and path.name not in existing and path.name not in retained:
            try:
                path.unlink()
            except OSError:
                logging.getLogger(__name__).warning(
                    "Could not remove temporary screenshot %s", path.name
                )
    try:
        directory.rmdir()
    except OSError:
        pass


async def _run_capture_job(job_id: str, request: CaptureRequest) -> None:
    job = capture_jobs[job_id]
    try:
        result = await create_capture(request)
        job.update(status="completed", result=result.model_dump(mode="json"))
    except HTTPException as error:
        job.update(status="failed", error=error.detail)
    except Exception:
        logging.getLogger(__name__).exception("Audit job failed: %s", job_id)
        job.update(status="failed", error={"detail": "The audit failed. Please try again."})
    finally:
        job["finished_at"] = time.monotonic()


@app.post("/captures/jobs", status_code=202)
async def submit_capture_job(request: CaptureRequest) -> dict:
    now = time.monotonic()
    for job_id, job in list(capture_jobs.items()):
        if job.get("finished_at") is not None and now - job["finished_at"] > JOB_RETENTION_SECONDS:
            del capture_jobs[job_id]
    if sum(job["status"] == "pending" for job in capture_jobs.values()) >= MAX_PENDING_CAPTURES:
        raise HTTPException(429, "The audit queue is full. Please try again shortly.", headers={"Retry-After": "10"})
    # Bound retained reports as well as queued work.
    if len(capture_jobs) >= 100:
        completed = next((key for key, job in capture_jobs.items() if job["status"] != "pending"), None)
        if completed is not None:
            del capture_jobs[completed]
    job_id = uuid4().hex
    capture_jobs[job_id] = {"status": "pending"}
    task = asyncio.create_task(_run_capture_job(job_id, request))
    capture_tasks.add(task)
    task.add_done_callback(capture_tasks.discard)
    return {"job_id": job_id, "status": "pending"}


@app.get("/captures/jobs/{job_id}")
async def get_capture_job(job_id: str) -> dict:
    job = capture_jobs.get(job_id)
    if job is None or (job.get("finished_at") is not None and time.monotonic() - job["finished_at"] > JOB_RETENTION_SECONDS):
        raise HTTPException(404, "This audit expired or the server restarted. Please start a new audit.")
    return {key: value for key, value in job.items() if key != "finished_at"}


@app.get("/captures/screenshots/{filename}")
async def get_capture_screenshot(filename: str) -> FileResponse:
    if not re.fullmatch(
        r"(?:[a-f0-9]{32}|scenario_[A-Za-z0-9_-]+_[A-Za-z0-9_-]+_"
        r"[A-Za-z0-9_-]+_[0-9]+x[0-9]+)\.png",
        filename,
    ):
        raise HTTPException(status_code=404, detail="Screenshot not found.")
    screenshot_path = OUTPUT_DIR / "screenshots" / filename
    if not screenshot_path.is_file():
        raise HTTPException(status_code=404, detail="Screenshot not found.")
    return FileResponse(screenshot_path, media_type="image/png")


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
                "answer_interpretation": question_answer_interpretation(
                    question.question_id
                ),
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
                "answer_interpretation": question_answer_interpretation(
                    question.question_id
                ),
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


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/scan/{job_id}", include_in_schema=False)
async def scan_page(job_id: str) -> FileResponse:
    return FileResponse(Path(__file__).resolve().parent / "static" / "index.html")


@app.get("/report/{scan_id}", include_in_schema=False)
async def report_page(scan_id: str) -> FileResponse:
    return FileResponse(Path(__file__).resolve().parent / "static" / "index.html")


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

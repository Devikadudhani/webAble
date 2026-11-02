from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field, replace
from typing import Literal, Protocol
from uuid import uuid4

from app.analyzers.accessibility import (
    AccessibilityScanResult,
    scan_accessibility,
)
from app.analyzers.element_horizontal_overflow import (
    ElementHorizontalOverflowEvidence,
    PageEvaluator,
    diagnose_element_horizontal_overflow,
)
from app.analyzers.element_layout_evidence import enrich_element_layout_evidence
from app.analyzers.finding_normalization import (
    NormalizedHorizontalOverflowFinding,
    normalize_horizontal_overflow_findings,
)
from app.analyzers.functional_ux import (
    DestinationValidator,
    FunctionalUXAuditResult,
    audit_functional_ux,
)
from app.analyzers.hybrid_evaluation import (
    BrowserFeatureDiscovery,
    discover_browser_features,
)
from app.analyzers.keyboard_focus import (
    KeyboardFocusAuditResult,
    audit_keyboard_focus,
)
from app.analyzers.text_reflow import (
    ScenarioScreenshotCapture,
    TextReflowAuditResult,
    audit_text_reflow,
)
from app.analyzers.target_size import TargetSizeAuditResult, audit_target_size
from app.analyzers.horizontal_overflow import (
    HorizontalOverflowResult,
    analyze_horizontal_overflow,
)
from app.capture.models import (
    AccessStatus,
    BrowserEvidence,
    CaptureOutcome,
    FailedRequest,
    NavigationStatus,
    ReadinessStatus,
    ViewportDimensions,
)
from app.capture.runner import BrowserCaptureError, PageCallback
from app.capture.url_safety import UnsafeURL


class CaptureFunction(Protocol):
    async def __call__(
        self,
        url: str,
        width: int,
        height: int,
        *,
        page_callback: PageCallback | None = None,
    ) -> BrowserEvidence:
        ...


ElementDiagnoser = Callable[
    [PageEvaluator, int], Awaitable[list[ElementHorizontalOverflowEvidence]]
]
ViewportCaptureOutcome = CaptureOutcome | Literal[
    "capture_failed", "not_attempted"
]
AnalyzerExecutionStatus = Literal["completed", "partial", "not_run"]
OverflowAnalysisStatus = Literal[
    "available", "missing_dimensions", "capture_incomplete", "not_attempted"
]
ElementDiagnosisStatus = Literal["available", "unavailable", "not_attempted"]
FindingNormalizationStatus = Literal["available", "unavailable", "not_attempted"]
TechnicalEvidenceStatus = Literal[
    "available", "partial", "unavailable", "not_tested"
]


@dataclass(frozen=True)
class TechnicalEvidenceResult:
    status: TechnicalEvidenceStatus = "not_tested"
    page_url: str | None = None
    navigation_status: NavigationStatus | None = None
    readiness_status: ReadinessStatus | None = None
    console_errors: list[str] = field(default_factory=list)
    runtime_errors: list[str] = field(default_factory=list)
    failed_requests: list[FailedRequest] = field(default_factory=list)
    redirect_chains: list[list[str]] = field(default_factory=list)
    unloaded_image_count: int | None = None
    loading_indicator_count: int | None = None
    visible_content_characters: int = 0
    access_restriction_signals: list[str] = field(default_factory=list)
    access_restriction_provider: str | None = None
    access_restriction_reference: str | None = None
    main_document_http_status: int | None = None
    access_status: AccessStatus = "unavailable"
    primary_content_characters: int = 0
    primary_content_items: int = 0
    readiness_elapsed_ms: int = 0
    details: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ElementOverflowDiagnosisResult:
    status: ElementDiagnosisStatus
    findings: list[ElementHorizontalOverflowEvidence] = field(default_factory=list)
    details: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class FindingNormalizationResult:
    status: FindingNormalizationStatus
    findings: list[NormalizedHorizontalOverflowFinding] = field(default_factory=list)
    details: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ViewportCaptureResult:
    name: str
    viewport: ViewportDimensions
    capture_outcome: ViewportCaptureOutcome
    horizontal_overflow: HorizontalOverflowResult | None
    overflow_analysis_status: OverflowAnalysisStatus
    screenshot_ref: str | None
    element_overflow_diagnosis: ElementOverflowDiagnosisResult
    finding_normalization: FindingNormalizationResult
    analyzer_execution_status: AnalyzerExecutionStatus = "not_run"
    details: list[str] = field(default_factory=list)
    functional_ux_audit: FunctionalUXAuditResult = field(
        default_factory=lambda: FunctionalUXAuditResult(
            status="not_attempted",
            details=["Functional UX audit was not attempted."],
        )
    )
    accessibility_scan: AccessibilityScanResult = field(
        default_factory=lambda: AccessibilityScanResult(
            status="not_attempted",
            details=["Accessibility scan was not attempted."],
        )
    )
    keyboard_focus_audit: KeyboardFocusAuditResult = field(
        default_factory=lambda: KeyboardFocusAuditResult(
            status="not_tested",
            details=["Keyboard/focus audit was not attempted."],
        )
    )
    text_reflow_audit: TextReflowAuditResult = field(
        default_factory=lambda: TextReflowAuditResult(
            status="not_tested",
            details=["Text scaling and reflow audit was not attempted."],
        )
    )
    target_size_audit: TargetSizeAuditResult = field(
        default_factory=lambda: TargetSizeAuditResult(
            status="not_tested",
            details=["Target-size audit was not attempted."],
        )
    )
    technical_evidence: TechnicalEvidenceResult = field(
        default_factory=TechnicalEvidenceResult
    )
    browser_feature_discovery: BrowserFeatureDiscovery = field(
        default_factory=lambda: BrowserFeatureDiscovery(
            status="not_attempted",
            details=("Browser feature discovery was not attempted.",),
        )
    )


VIEWPORTS = (
    ("desktop", ViewportDimensions(width=1365, height=768)),
    ("tablet", ViewportDimensions(width=768, height=1024)),
    ("mobile", ViewportDimensions(width=390, height=844)),
)


async def capture_responsive_viewports(
    url: str,
    capture: CaptureFunction,
    diagnoser: ElementDiagnoser = diagnose_element_horizontal_overflow,
    destination_validator: DestinationValidator | None = None,
    scenario_screenshot_capture: ScenarioScreenshotCapture | None = None,
) -> list[ViewportCaptureResult]:
    """Capture one URL at the standard viewports and analyze complete measurements."""
    results: list[ViewportCaptureResult] = []
    stop_after_unsafe_url = False
    capture_id = uuid4().hex

    for name, viewport in VIEWPORTS:
        if stop_after_unsafe_url:
            results.append(
                ViewportCaptureResult(
                    name=name,
                    viewport=viewport,
                    capture_outcome="not_attempted",
                    horizontal_overflow=None,
                    overflow_analysis_status="not_attempted",
                    screenshot_ref=None,
                    element_overflow_diagnosis=ElementOverflowDiagnosisResult(
                        status="not_attempted",
                        details=["Capture was not attempted because the URL was prohibited."],
                    ),
                    finding_normalization=FindingNormalizationResult(
                        status="not_attempted",
                        details=["Normalization was not attempted because capture was not attempted."],
                    ),
                    details=[
                        "Capture was not attempted because the URL was prohibited."
                    ],
                    technical_evidence=TechnicalEvidenceResult(
                        status="not_tested",
                        details=["The requested page was prohibited and not captured."],
                    ),
                )
            )
            continue

        diagnosis = ElementOverflowDiagnosisResult(
            status="not_attempted",
            details=["Diagnosis was not attempted because capture was incomplete."],
        )
        functional_audit = FunctionalUXAuditResult(
            status="not_attempted",
            details=["Functional UX audit was not attempted because capture was incomplete."],
        )
        accessibility = AccessibilityScanResult(
            status="not_attempted",
            details=["Accessibility scan was not attempted because capture was incomplete."],
        )
        keyboard_focus = KeyboardFocusAuditResult(
            status="not_tested",
            details=["Keyboard/focus audit was not attempted because capture was incomplete."],
        )
        target_size = TargetSizeAuditResult(
            status="not_tested",
            details=["Target-size audit was not attempted because capture was incomplete."],
        )
        feature_discovery = BrowserFeatureDiscovery(
            status="not_attempted",
            details=("Browser feature discovery was not attempted because capture was incomplete.",),
        )
        analysis_attempted = False
        text_reflow = TextReflowAuditResult(
            status="not_tested",
            details=["Text scaling and reflow audit was not attempted because capture was incomplete."],
        )

        async def diagnose_live_page(page: PageEvaluator) -> None:
            nonlocal diagnosis, functional_audit, accessibility, keyboard_focus, text_reflow, target_size, feature_discovery, analysis_attempted
            analysis_attempted = True
            try:
                feature_discovery = await discover_browser_features(
                    page,
                    viewport=name,
                )
            except Exception as error:
                feature_discovery = BrowserFeatureDiscovery(
                    status="unavailable",
                    details=(f"Browser feature discovery failed ({type(error).__name__}).",),
                )
            try:
                findings = await diagnoser(page, viewport.width)
            except Exception as error:
                diagnosis = ElementOverflowDiagnosisResult(
                    status="unavailable",
                    details=[
                        f"Element-level diagnosis failed ({type(error).__name__})."
                    ],
                )
            else:
                try:
                    findings = await enrich_element_layout_evidence(
                        page, findings, viewport.width
                    )
                except Exception:
                    findings = [
                        replace(
                            finding,
                            layout_diagnosis_status="unavailable",
                            layout_diagnosis_details=[
                                "Detailed layout evidence could not be collected."
                            ],
                        )
                        for finding in findings
                    ]
                diagnosis = ElementOverflowDiagnosisResult(
                    status="available", findings=findings
                )
            try:
                functional_audit = await audit_functional_ux(
                    page, destination_validator
                )
            except Exception as error:
                functional_audit = FunctionalUXAuditResult(
                    status="unavailable",
                    details=[
                        f"Functional UX audit failed ({type(error).__name__})."
                    ],
                )
            try:
                accessibility = await scan_accessibility(page)
            except Exception as error:
                accessibility = AccessibilityScanResult(
                    status="unavailable",
                    details=[
                        f"The accessibility engine could not complete ({type(error).__name__})."
                    ],
                )
            try:
                keyboard_focus = await audit_keyboard_focus(page)
            except Exception as error:
                keyboard_focus = KeyboardFocusAuditResult(
                    status="unavailable",
                    details=[
                        f"Keyboard/focus audit failed ({type(error).__name__})."
                    ],
                )
            try:
                target_size = await audit_target_size(page)
            except Exception as error:
                target_size = TargetSizeAuditResult(
                    status="unavailable",
                    details=[f"Target-size audit failed ({type(error).__name__})."],
                )
            try:
                text_reflow = await audit_text_reflow(
                    page,
                    baseline_width=viewport.width,
                    baseline_height=viewport.height,
                    viewport_name=name,
                    capture_id=capture_id,
                    capture_screenshot=scenario_screenshot_capture,
                )
            except Exception as error:
                text_reflow = TextReflowAuditResult(
                    status="unavailable",
                    details=[
                        f"Text scaling and reflow audit failed ({type(error).__name__})."
                    ],
                )

        try:
            evidence = await capture(
                url,
                viewport.width,
                viewport.height,
                page_callback=diagnose_live_page,
            )
        except UnsafeURL as error:
            results.append(
                ViewportCaptureResult(
                    name=name,
                    viewport=viewport,
                    capture_outcome="capture_failed",
                    horizontal_overflow=None,
                    overflow_analysis_status="not_attempted",
                    screenshot_ref=None,
                    element_overflow_diagnosis=ElementOverflowDiagnosisResult(
                        status="not_attempted",
                        details=["Diagnosis was not attempted because capture failed."],
                    ),
                    finding_normalization=FindingNormalizationResult(
                        status="not_attempted",
                        details=["Normalization was not attempted because capture failed."],
                    ),
                    details=[str(error)],
                    technical_evidence=TechnicalEvidenceResult(
                        status="not_tested",
                        details=["The requested page was prohibited and not captured."],
                    ),
                )
            )
            stop_after_unsafe_url = True
            continue
        except BrowserCaptureError as error:
            results.append(
                ViewportCaptureResult(
                    name=name,
                    viewport=viewport,
                    capture_outcome="capture_failed",
                    horizontal_overflow=None,
                    overflow_analysis_status="not_attempted",
                    screenshot_ref=None,
                    element_overflow_diagnosis=ElementOverflowDiagnosisResult(
                        status="not_attempted",
                        details=["Diagnosis was not attempted because capture failed."],
                    ),
                    finding_normalization=FindingNormalizationResult(
                        status="not_attempted",
                        details=["Normalization was not attempted because capture failed."],
                    ),
                    details=[f"Capture failed: {str(error)[:300]}"],
                    technical_evidence=TechnicalEvidenceResult(
                        status="unavailable",
                        details=[f"Capture failed ({type(error).__name__})."],
                    ),
                )
            )
            continue
        except Exception as error:
            results.append(
                ViewportCaptureResult(
                    name=name,
                    viewport=viewport,
                    capture_outcome="capture_failed",
                    horizontal_overflow=None,
                    overflow_analysis_status="not_attempted",
                    screenshot_ref=None,
                    element_overflow_diagnosis=ElementOverflowDiagnosisResult(
                        status="not_attempted",
                        details=["Diagnosis was not attempted because capture failed."],
                    ),
                    finding_normalization=FindingNormalizationResult(
                        status="not_attempted",
                        details=["Normalization was not attempted because capture failed."],
                    ),
                    details=[f"Capture failed ({type(error).__name__})."],
                    technical_evidence=TechnicalEvidenceResult(
                        status="unavailable",
                        details=[f"Capture failed ({type(error).__name__})."],
                    ),
                )
            )
            continue

        details = list(evidence.details)
        capture_is_complete = (
            evidence.outcome == "completed"
            and evidence.readiness_status == "ready"
        )
        analyzer_execution_status = (
            "not_run" if not analysis_attempted
            else "completed" if capture_is_complete
            else "partial"
        )
        technical_evidence = TechnicalEvidenceResult(
            status="available" if capture_is_complete else "partial",
            page_url=evidence.final_url or evidence.requested_url,
            navigation_status=evidence.navigation_status,
            readiness_status=evidence.readiness_status,
            console_errors=list(evidence.console_errors),
            runtime_errors=list(evidence.uncaught_page_errors),
            failed_requests=list(evidence.failed_requests),
            redirect_chains=list(evidence.redirect_chains),
            unloaded_image_count=evidence.unloaded_image_count,
            loading_indicator_count=evidence.loading_indicator_count,
            visible_content_characters=evidence.visible_content_characters,
            access_restriction_signals=list(evidence.access_restriction_signals),
            access_restriction_provider=evidence.access_restriction_provider,
            access_restriction_reference=evidence.access_restriction_reference,
            main_document_http_status=evidence.main_document_http_status,
            access_status=evidence.access_status,
            primary_content_characters=evidence.primary_content_characters,
            primary_content_items=evidence.primary_content_items,
            readiness_elapsed_ms=evidence.readiness_elapsed_ms,
            details=list(evidence.details),
        )
        if analysis_attempted and evidence.screenshot_ref:
            text_reflow = replace(
                text_reflow,
                scenarios=[
                    replace(scenario, screenshot_ref=evidence.screenshot_ref)
                    if scenario.scenario_id == "baseline"
                    else scenario
                    for scenario in text_reflow.scenarios
                ],
            )
        if not analysis_attempted:
            functional_audit = FunctionalUXAuditResult(
                status="not_attempted",
                details=[
                    "Functional UX audit was not attempted because capture was incomplete."
                ],
            )
            accessibility = AccessibilityScanResult(
                status="not_attempted",
                details=[
                    "Accessibility scan was not attempted because capture was incomplete."
                ],
            )
            keyboard_focus = KeyboardFocusAuditResult(
                status="not_tested",
                details=[
                    "Keyboard/focus audit was not attempted because capture was incomplete."
                ],
            )
            target_size = TargetSizeAuditResult(
                status="not_tested",
                details=[
                    "Target-size audit was not attempted because capture was incomplete."
                ],
            )
            text_reflow = TextReflowAuditResult(
                status="not_tested",
                details=["Text scaling and reflow audit was not attempted because capture was incomplete."],
            )
        if not analysis_attempted:
            analysis_status: OverflowAnalysisStatus = "capture_incomplete"
            details.append(
                "Horizontal-overflow analysis was skipped because the capture was incomplete."
            )
            overflow = None
        elif (
            evidence.document.scroll_width is None
            or evidence.document.visible_width is None
        ):
            analysis_status = "missing_dimensions"
            details.append(
                "Horizontal-overflow analysis was unavailable because width measurements were missing."
            )
            overflow = None
        else:
            analysis_status = "available"
            if not capture_is_complete:
                details.append(
                    "Document overflow was measured on a partial capture; interpret it as partial evidence."
                )
            overflow = analyze_horizontal_overflow(
                scroll_width=evidence.document.scroll_width,
                visible_width=evidence.document.visible_width,
            )

        normalization = FindingNormalizationResult(
            status="not_attempted",
            details=["Normalization was not attempted because diagnosis was unavailable."],
        )
        if diagnosis.status == "available":
            try:
                normalized_findings = normalize_horizontal_overflow_findings(
                    diagnosis.findings,
                    viewport_name=name,
                    viewport_width=viewport.width,
                    document_overflow=overflow,
                )
            except Exception as error:
                normalization = FindingNormalizationResult(
                    status="unavailable",
                    details=[
                        f"Finding normalization failed ({type(error).__name__})."
                    ],
                )
            else:
                normalization = FindingNormalizationResult(
                    status="available",
                    findings=normalized_findings,
                )

        results.append(
            ViewportCaptureResult(
                name=name,
                viewport=viewport,
                capture_outcome=evidence.outcome,
                analyzer_execution_status=analyzer_execution_status,
                horizontal_overflow=overflow,
                overflow_analysis_status=analysis_status,
                screenshot_ref=evidence.screenshot_ref,
                element_overflow_diagnosis=diagnosis,
                finding_normalization=normalization,
                details=details,
                functional_ux_audit=functional_audit,
                accessibility_scan=accessibility,
                keyboard_focus_audit=keyboard_focus,
                text_reflow_audit=text_reflow,
                target_size_audit=target_size,
                browser_feature_discovery=feature_discovery,
                technical_evidence=technical_evidence,
            )
        )

    return results

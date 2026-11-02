from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal


NavigationStatus = Literal["completed", "timeout", "failed"]
ReadinessStatus = Literal["ready", "partial", "unavailable"]
CaptureOutcome = Literal["completed", "partial", "navigation_timeout"]
AccessStatus = Literal["accessible", "partial", "restricted", "unavailable"]


@dataclass(frozen=True)
class ViewportDimensions:
    width: int
    height: int


@dataclass(frozen=True)
class DocumentDimensions:
    scroll_width: int | None
    scroll_height: int | None
    visible_width: int | None
    visible_height: int | None


@dataclass(frozen=True)
class FailedRequest:
    url: str
    resource_type: str
    error: str | None


@dataclass
class BrowserEvidence:
    requested_url: str
    final_url: str | None
    page_title: str | None
    viewport: ViewportDimensions
    document: DocumentDimensions
    screenshot_ref: str | None
    navigation_duration_ms: int
    settling_duration_ms: int
    browser_name: str
    scanned_at: datetime
    console_errors: list[str] = field(default_factory=list)
    uncaught_page_errors: list[str] = field(default_factory=list)
    failed_requests: list[FailedRequest] = field(default_factory=list)
    redirect_chains: list[list[str]] = field(default_factory=list)
    unloaded_image_count: int | None = None
    loading_indicator_count: int | None = None
    visible_content_characters: int = 0
    analysis_eligible: bool = False
    access_restriction_signals: list[str] = field(default_factory=list)
    access_restriction_provider: str | None = None
    access_restriction_reference: str | None = None
    main_document_http_status: int | None = None
    access_status: AccessStatus = "unavailable"
    primary_content_characters: int = 0
    primary_content_items: int = 0
    readiness_elapsed_ms: int = 0
    navigation_status: NavigationStatus = "failed"
    readiness_status: ReadinessStatus = "unavailable"
    outcome: CaptureOutcome = "partial"
    details: list[str] = field(default_factory=list)

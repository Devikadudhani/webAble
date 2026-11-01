from __future__ import annotations

import asyncio
from dataclasses import dataclass, field, replace
from typing import Any, Awaitable, Callable, Literal, Protocol
from uuid import uuid4

ScenarioStatus = Literal["completed", "unsupported", "not_tested", "error"]
ScenarioClassification = Literal[
    "violation",
    "no_violation_detected",
    "needs_review",
    "not_tested",
    "unsupported",
    "error",
]
TextReflowAuditStatus = Literal[
    "available", "partial", "unavailable", "not_tested"
]

MAX_INSPECTED_ELEMENTS = 300
MAX_FINDINGS = 50
SCENARIO_TIMEOUT_SECONDS = 8


@dataclass(frozen=True)
class TextReflowMeasurement:
    viewport_width: int
    viewport_height: int
    window_inner_width: int
    window_inner_height: int
    document_scroll_width: int
    document_scroll_height: int
    document_horizontal_overflow_px: int
    overflow_boundaries: list[dict] = field(default_factory=list)
    inspected_text_elements: int = 0


@dataclass(frozen=True)
class TextReflowFinding:
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
    screenshot_ref: str | None = None


@dataclass(frozen=True)
class TextReflowScenario:
    scenario_id: str
    status: ScenarioStatus
    classification: ScenarioClassification
    condition: str
    method: str
    criterion_ids: list[str]
    viewport_width: int | None = None
    viewport_height: int | None = None
    measurement: TextReflowMeasurement | None = None
    baseline_measurement: TextReflowMeasurement | None = None
    findings: list[TextReflowFinding] = field(default_factory=list)
    screenshot_ref: str | None = None
    details: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class TextReflowAuditResult:
    status: TextReflowAuditStatus
    scenarios: list[TextReflowScenario] = field(default_factory=list)
    details: list[str] = field(default_factory=list)


class TextReflowPage(Protocol):
    async def evaluate(self, expression: str, argument: dict) -> Any:
        ...

    async def set_viewport_size(self, viewport_size: dict[str, int]) -> None:
        ...


ScenarioScreenshotCapture = Callable[
    [TextReflowPage, str, str, str, int, int], Awaitable[str]
]


_MEASURE_PAGE = """async (options) => {
    const maxElements = options.maxElements;
    const selectorFor = (element) => {
      if (element.id) {
        const idSelector = `#${CSS.escape(element.id)}`;
        if (document.querySelectorAll(idSelector).length === 1) return idSelector;
      }
      const parts = [];
      let node = element;
      while (node && node.nodeType === Node.ELEMENT_NODE) {
        let part = node.tagName.toLowerCase();
        if (node.parentElement) {
          const sameTag = [...node.parentElement.children]
            .filter(child => child.tagName === node.tagName);
          if (sameTag.length > 1) part += `:nth-of-type(${sameTag.indexOf(node) + 1})`;
        }
        parts.unshift(part);
        const candidate = parts.join(" > ");
        if (document.querySelectorAll(candidate).length === 1) return candidate;
        node = node.parentElement;
      }
      return parts.join(" > ");
    };
    const contentSignatureFor = (element) => {
      const controlValue = element.matches("input,textarea,select")
        ? element.value
        : "";
      const content = `${element.getAttribute("aria-label") || ""} ${controlValue} ${element.textContent || ""}`
        .replace(/\s+/g, " ")
        .trim();
      let hash = 2166136261;
      for (let index = 0; index < content.length; index += 1) {
        hash = Math.imul(hash ^ content.charCodeAt(index), 16777619);
      }
      return `${content.length}:${(hash >>> 0).toString(16)}`;
    };
    const visible = (element) => {
      const style = getComputedStyle(element);
      return element.getClientRects().length > 0 &&
        style.display !== "none" &&
        style.visibility !== "hidden" &&
        style.visibility !== "collapse" &&
        Number(style.opacity) !== 0 &&
        !element.closest("[hidden],[inert]");
    };
    const textBearing = (element) =>
      [...element.childNodes].some(node =>
        node.nodeType === Node.TEXT_NODE && node.textContent.trim().length > 0
      ) || element.matches("input,textarea,select,button,[role=button]");
    const originalViewport = {
      width: window.innerWidth,
      height: window.innerHeight
    };
    const doc = document.documentElement;
    const body = document.body;
    const all = [...document.querySelectorAll("*")];
    const textCandidates = all.filter(element => visible(element) && textBearing(element));
    const originalInlineStyles = [];
    let retainInlineStyles = false;
    try {
      if (options.enlargeText) {
        for (const element of textCandidates.slice(0, maxElements)) {
          const style = getComputedStyle(element);
          const computedSize = parseFloat(style.fontSize);
          if (!Number.isFinite(computedSize) || computedSize <= 0) continue;
          originalInlineStyles.push({
            element,
            computedSize,
            value: element.style.getPropertyValue("font-size"),
            priority: element.style.getPropertyPriority("font-size")
          });
        }
        for (const original of originalInlineStyles) {
          original.element.style.setProperty(
            "font-size",
            `${original.computedSize * 2}px`,
            "important"
          );
        }
        if (options.holdFontStyles && originalInlineStyles.length) {
          window[options.restoreKey] = originalInlineStyles;
          retainInlineStyles = true;
        }
      }

      if (options.stabilizeLayout) {
        await new Promise(resolve =>
          requestAnimationFrame(() =>
            requestAnimationFrame(resolve)
          )
        );
      }

      const textElements = textCandidates.slice(0, maxElements);
      const elementEvidence = [];
      const elementReferences = [];
      const overflowBoundaries = [];
      for (const element of textElements) {
        const style = getComputedStyle(element);
        const rect = element.getBoundingClientRect();
        const selector = selectorFor(element);
        let scrollContainer = null;
        let twoDimensionalRegion = null;
        for (let ancestor = element.parentElement; ancestor; ancestor = ancestor.parentElement) {
          const ancestorStyle = getComputedStyle(ancestor);
          if (!scrollContainer &&
              ["auto", "scroll", "overlay"].includes(ancestorStyle.overflowX) &&
              ancestor.scrollWidth > ancestor.clientWidth + 1) {
            scrollContainer = selectorFor(ancestor);
          }
          if (!twoDimensionalRegion &&
              (ancestor.tagName === "TABLE" ||
               ancestor.matches('[role="table"],[role="grid"],[role="treegrid"]'))) {
            twoDimensionalRegion = selectorFor(ancestor);
          }
        }
        const evidence = {
          selector,
          tagName: element.tagName.toLowerCase(),
          contentSignature: contentSignatureFor(element),
          left: rect.left,
          right: rect.right,
          top: rect.top,
          bottom: rect.bottom,
          width: rect.width,
          height: rect.height,
          fontSize: style.fontSize,
          clientWidth: element.clientWidth,
          scrollWidth: element.scrollWidth,
          clientHeight: element.clientHeight,
          scrollHeight: element.scrollHeight,
          overflowX: style.overflowX,
          overflowY: style.overflowY,
          textOverflow: style.textOverflow,
          lineClamp: style.webkitLineClamp || style.lineClamp || "none",
          position: style.position,
          clippedText: ["hidden", "clip"].includes(style.overflowY) &&
            element.scrollHeight > element.clientHeight + 1,
          ellipsisTruncated: style.textOverflow === "ellipsis" &&
            element.scrollWidth > element.clientWidth + 1,
          horizontalTextOverflow: element.scrollWidth > element.clientWidth + 1 ||
            rect.left < -1 || rect.right > window.innerWidth + 1,
          scrollContainer,
          twoDimensionalRegion,
          fixedOutsideViewport: style.position === "fixed" &&
            (rect.left < -1 || rect.right > window.innerWidth + 1 ||
             rect.top < -1 || rect.bottom > window.innerHeight + 1)
        };
        elementEvidence.push(evidence);
        elementReferences.push(element);
        if (evidence.horizontalTextOverflow) {
          overflowBoundaries.push({
            selector,
            left: rect.left,
            right: rect.right,
            overflowPx: Math.max(0, rect.right - window.innerWidth, -rect.left),
            scrollContainer,
            twoDimensionalRegion
          });
        }
      }
      const overlapPairs = [];
      for (let first = 0; first < elementEvidence.length; first += 1) {
        const a = elementEvidence[first];
        const aElement = elementReferences[first];
        for (let second = first + 1;
             second < elementEvidence.length && overlapPairs.length < 50;
             second += 1) {
          const b = elementEvidence[second];
          const bElement = elementReferences[second];
          if (!aElement || !bElement ||
              aElement.contains(bElement) || bElement.contains(aElement)) continue;
          const overlapWidth = Math.min(a.right, b.right) - Math.max(a.left, b.left);
          const overlapHeight = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
          if (overlapWidth > 2 && overlapHeight > 2) {
            overlapPairs.push({
              firstSelector: a.selector,
              secondSelector: b.selector,
              overlapWidth,
              overlapHeight
            });
          }
        }
      }

      return {
        viewport: originalViewport,
        document: {
          scrollWidth: Math.max(doc.scrollWidth, body ? body.scrollWidth : 0),
          scrollHeight: Math.max(doc.scrollHeight, body ? body.scrollHeight : 0)
        },
        inspectedTextElements: elementEvidence.length,
        candidatesTruncated: textCandidates.length > maxElements,
        elements: elementEvidence,
        overlapPairs,
        overflowBoundaries: overflowBoundaries.slice(0, 20)
      };
    } finally {
      if (!retainInlineStyles) {
        for (const original of originalInlineStyles) {
          if (original.value) {
            original.element.style.setProperty("font-size", original.value, original.priority);
          } else {
            original.element.style.removeProperty("font-size");
          }
        }
      }
    }
}"""

_RESTORE_FONT_STYLES = """(options) => {
  const originals = window[options.restoreKey];
  if (!Array.isArray(originals)) return false;
  try {
    for (const original of originals) {
      if (original.value) {
        original.element.style.setProperty(
          "font-size",
          original.value,
          original.priority
        );
      } else {
        original.element.style.removeProperty("font-size");
      }
    }
    return true;
  } finally {
    delete window[options.restoreKey];
  }
}"""


def _measurement(raw: dict) -> TextReflowMeasurement:
    viewport = raw["viewport"]
    document = raw["document"]
    width = int(viewport["width"])
    height = int(viewport["height"])
    scroll_width = int(document["scrollWidth"])
    return TextReflowMeasurement(
        viewport_width=width,
        viewport_height=height,
        window_inner_width=width,
        window_inner_height=height,
        document_scroll_width=scroll_width,
        document_scroll_height=int(document["scrollHeight"]),
        document_horizontal_overflow_px=max(0, scroll_width - width),
        overflow_boundaries=raw.get("overflowBoundaries", []),
        inspected_text_elements=int(raw.get("inspectedTextElements", 0)),
    )


def _analyze(
    scenario_id: str,
    raw: dict,
    baseline: dict | None,
    criterion_id: str,
) -> tuple[ScenarioClassification, list[TextReflowFinding]]:
    baseline_elements = {
        item["selector"]: item for item in (baseline or {}).get("elements", [])
    }
    findings: list[TextReflowFinding] = []
    for element in raw.get("elements", []):
        selector = str(element.get("selector", ""))
        prior = baseline_elements.get(selector)
        if criterion_id == "1.4.4" and element.get("clippedText"):
            findings.append(
                TextReflowFinding(
                    criterion_id="1.4.4",
                    level="AA",
                    classification="needs_review",
                    selector=selector,
                    tag_name=str(element.get("tagName", "")),
                    observation=(
                        "Measurements suggest text may be vertically clipped; "
                        "whether the complete text remains available through "
                        "another usable mechanism was not determined."
                    ),
                    evidence={
                        **{
                            key: element.get(key)
                            for key in (
                                "fontSize",
                                "clientHeight",
                                "scrollHeight",
                                "overflowY",
                            )
                        },
                        "content_signature": element.get("contentSignature"),
                        "text_availability": "not_evaluated",
                    },
                    baseline_evidence=(
                        {
                            **{
                                key: prior.get(key)
                                for key in (
                                    "fontSize",
                                    "clientHeight",
                                    "scrollHeight",
                                    "overflowY",
                                )
                            },
                            "content_signature": prior.get("contentSignature"),
                        }
                        if prior
                        else None
                    ),
                    confidence="medium",
                    remediation=(
                        "Review the enlarged text in context and verify that the "
                        "complete text remains available; allow the container to "
                        "grow or provide a usable disclosure if needed."
                    ),
                )
            )
        elif criterion_id == "1.4.4" and element.get("ellipsisTruncated"):
            findings.append(
                TextReflowFinding(
                    criterion_id="1.4.4",
                    level="AA",
                    classification="needs_review",
                    selector=selector,
                    tag_name=str(element.get("tagName", "")),
                    observation=(
                        "The text-overflow ellipsis style is paired with content "
                        "wider than its element; availability of the complete text "
                        "through another usable mechanism was not determined."
                    ),
                    evidence={
                        **{
                            key: element.get(key)
                            for key in (
                                "fontSize",
                                "clientWidth",
                                "scrollWidth",
                                "textOverflow",
                            )
                        },
                        "content_signature": element.get("contentSignature"),
                        "text_availability": "not_evaluated",
                    },
                    baseline_evidence=(
                        {
                            key: prior.get(key)
                            for key in ("fontSize", "clientWidth", "scrollWidth")
                        }
                        | {"content_signature": prior.get("contentSignature")}
                        if prior
                        else None
                    ),
                    confidence="medium",
                    remediation=(
                        "Review whether the full text remains available at 200%; "
                        "remove truncation or provide a usable way to reveal it."
                    ),
                )
            )
        elif criterion_id == "1.4.10" and (
            element.get("horizontalTextOverflow") or element.get("fixedOutsideViewport")
        ):
            two_dimensional = bool(element.get("twoDimensionalRegion"))
            in_scroll_container = bool(element.get("scrollContainer"))
            findings.append(
                TextReflowFinding(
                    criterion_id="1.4.10",
                    level="AA",
                    classification="needs_review",
                    selector=selector,
                    tag_name=str(element.get("tagName", "")),
                    observation=(
                        "Text-bearing content extends beyond the tested viewport."
                        if not two_dimensional
                        else "Overflow occurs within a potentially two-dimensional region."
                    ),
                    evidence={
                        **{
                            key: element.get(key)
                            for key in (
                                "left",
                                "right",
                                "width",
                                "clientWidth",
                                "scrollWidth",
                                "position",
                                "scrollContainer",
                                "twoDimensionalRegion",
                            )
                        },
                        "content_signature": element.get("contentSignature"),
                    },
                    baseline_evidence=(
                        {
                            **{
                                key: prior.get(key)
                                for key in ("left", "right", "width", "scrollWidth")
                            },
                            "content_signature": prior.get("contentSignature"),
                        }
                        if prior
                        else None
                    ),
                    confidence="medium" if in_scroll_container or two_dimensional else "low",
                    remediation=(
                        "Review whether this content needs two-dimensional layout; "
                        "otherwise constrain text and reflow the surrounding content "
                        "within the viewport."
                    ),
                )
            )
    for element in raw.get("elements", []):
        selector = str(element.get("selector", ""))
        prior = baseline_elements.get(selector)
        current_signature = element.get("contentSignature")
        if (
            selector
            and prior
            and current_signature
            and current_signature != prior.get("contentSignature")
            and not any(finding.selector == selector for finding in findings)
        ):
            findings.append(
                TextReflowFinding(
                    criterion_id=criterion_id,
                    level="AA",
                    classification="needs_review",
                    selector=selector,
                    tag_name=str(element.get("tagName", "")),
                    observation=(
                        "Content associated with this selector changed between "
                        "baseline and test; dynamic updates or element replacement "
                        "require review."
                    ),
                    evidence={
                        "content_changed": True,
                        "content_signature": current_signature,
                    },
                    baseline_evidence={
                        "content_signature": prior.get("contentSignature"),
                    },
                    confidence="low",
                    remediation=(
                        "Confirm that equivalent text and functionality remain "
                        "available after the tested viewport or enlargement change."
                    ),
                )
            )
    if baseline and not baseline.get("candidatesTruncated") and not raw.get(
        "candidatesTruncated"
    ):
        visible_selectors = {
            str(item.get("selector"))
            for item in raw.get("elements", [])
            if item.get("selector")
        }
        for prior in baseline.get("elements", []):
            selector = str(prior.get("selector", ""))
            if selector and selector not in visible_selectors:
                findings.append(
                    TextReflowFinding(
                        criterion_id=criterion_id,
                        level="AA",
                        classification="needs_review",
                        selector=selector,
                        tag_name=str(prior.get("tagName", "")),
                        observation=(
                            "A text-bearing element measured at baseline was not "
                            "visible in the tested condition; it may be hidden or "
                            "replaced by responsive content."
                        ),
                        evidence={
                            "scenario_id": scenario_id,
                            "visible_in_test": False,
                        },
                        baseline_evidence={
                            key: prior.get(key)
                            for key in ("left", "right", "width", "fontSize")
                        },
                        confidence="low",
                        remediation=(
                            "Confirm equivalent content and functionality remain "
                            "available in the tested state."
                        ),
                    )
                )
    if criterion_id == "1.4.4":
        baseline_overlaps = {
            (item["firstSelector"], item["secondSelector"])
            for item in (baseline or {}).get("overlapPairs", [])
        }
        for overlap in raw.get("overlapPairs", []):
            pair = (overlap["firstSelector"], overlap["secondSelector"])
            if pair in baseline_overlaps:
                continue
            findings.append(
                TextReflowFinding(
                    criterion_id="1.4.4",
                    level="AA",
                    classification="needs_review",
                    selector=str(overlap["firstSelector"]),
                    tag_name="",
                    observation=(
                        "Two text-bearing elements overlap after text enlargement; "
                        "whether content or functionality is lost requires review."
                    ),
                    evidence=overlap,
                    baseline_evidence=None,
                    confidence="medium",
                    remediation=(
                        "Review the overlapping elements at enlarged text size and "
                        "allow the layout to grow or reflow if content is obscured."
                    ),
                )
            )
    if criterion_id == "1.4.10":
        document = raw.get("document", {})
        viewport = raw.get("viewport", {})
        document_width = document.get("scrollWidth")
        viewport_width = viewport.get("width")
        if (
            document_width is not None
            and viewport_width is not None
            and document_width > viewport_width + 1
            and not findings
        ):
            baseline_document = (baseline or {}).get("document", {})
            baseline_viewport = (baseline or {}).get("viewport", {})
            findings.append(
                TextReflowFinding(
                    criterion_id="1.4.10",
                    level="AA",
                    classification="needs_review",
                    selector="html",
                    tag_name="html",
                    observation=(
                        "Document-level horizontal overflow was measured at the "
                        "tested width; its source and any applicable exception "
                        "require review."
                    ),
                    evidence={
                        "viewport_width": viewport_width,
                        "document_scroll_width": document_width,
                        "document_horizontal_overflow_px": (
                            document_width - viewport_width
                        ),
                        "text_overflow_candidates_inspected": len(
                            raw.get("elements", [])
                        ),
                    },
                    baseline_evidence=(
                        {
                            "viewport_width": baseline_viewport.get("width"),
                            "document_scroll_width": baseline_document.get(
                                "scrollWidth"
                            ),
                        }
                        if baseline
                        else None
                    ),
                    confidence="low",
                    remediation=(
                        "Review the source of page-level horizontal scrolling and "
                        "whether the affected content qualifies for an exception."
                    ),
                )
            )
    findings = findings[:MAX_FINDINGS]
    if any(finding.classification == "violation" for finding in findings):
        return "violation", findings
    if findings or (baseline or {}).get("candidatesTruncated") or raw.get(
        "candidatesTruncated"
    ):
        return "needs_review", findings
    return "no_violation_detected", []


async def _capture_scenario_evidence(
    page: TextReflowPage,
    scenario: TextReflowScenario,
    *,
    viewport_name: str,
    capture_id: str,
    capture_screenshot: ScenarioScreenshotCapture | None,
) -> TextReflowScenario:
    if not scenario.findings:
        return scenario
    if capture_screenshot is None:
        return replace(
            scenario,
            details=[
                *scenario.details,
                "A scenario screenshot was not captured because screenshot storage is unavailable; measurements and findings are retained.",
            ],
        )
    try:
        screenshot_ref = await capture_screenshot(
            page,
            capture_id,
            viewport_name,
            scenario.scenario_id,
            scenario.viewport_width or 0,
            scenario.viewport_height or 0,
        )
    except Exception as error:
        return replace(
            scenario,
            details=[
                *scenario.details,
                f"Scenario screenshot capture failed ({type(error).__name__}); measurements and findings are retained.",
            ],
        )
    return replace(
        scenario,
        screenshot_ref=screenshot_ref,
        findings=[
            replace(finding, screenshot_ref=screenshot_ref)
            for finding in scenario.findings
        ],
    )


async def audit_text_reflow(
    page: TextReflowPage,
    *,
    baseline_width: int,
    baseline_height: int,
    screenshot_ref: str | None = None,
    viewport_name: str = "viewport",
    capture_id: str | None = None,
    capture_screenshot: ScenarioScreenshotCapture | None = None,
) -> TextReflowAuditResult:
    """Measure text enlargement and reflow without replacing the live capture page."""
    scenarios: list[TextReflowScenario] = []
    capture_id = capture_id or uuid4().hex
    details = [
        "Text enlargement captures each eligible candidate's computed font size before changes and applies twice that pixel value per element. Nested and inherited styles therefore become explicit overrides; this is not equivalent to every browser's text-only zoom behavior.",
        "No scenario result establishes WCAG conformance. Clipping, ellipsis, overlap, and overflow are observations requiring review because this analyzer cannot determine whether information remains available or whether an exception applies. Opaque content signatures flag text changes without returning the text itself.",
    ]
    try:
        baseline = await asyncio.wait_for(
            page.evaluate(
                _MEASURE_PAGE,
                {
                    "maxElements": MAX_INSPECTED_ELEMENTS,
                    "enlargeText": False,
                },
            ),
            timeout=SCENARIO_TIMEOUT_SECONDS,
        )
    except Exception as error:
        return TextReflowAuditResult(
            status="unavailable",
            scenarios=[
                TextReflowScenario(
                    scenario_id="baseline",
                    status="error",
                    classification="error",
                    condition="Existing captured CSS viewport before any audit adjustments.",
                    method="Read CSS viewport, document dimensions, and bounded text-element geometry.",
                    criterion_ids=[],
                    viewport_width=baseline_width,
                    viewport_height=baseline_height,
                    screenshot_ref=screenshot_ref,
                    details=[f"Baseline measurement failed ({type(error).__name__})."],
                )
            ],
            details=["Text scaling and reflow scenarios were not run because baseline measurement failed."],
        )

    scenarios.append(
        TextReflowScenario(
            scenario_id="baseline",
            status="completed",
            classification="not_tested",
            condition="Existing captured CSS viewport before any audit adjustments.",
            method="Measure window.innerWidth/innerHeight, document dimensions, and bounded text geometry.",
            criterion_ids=[],
            viewport_width=baseline_width,
            viewport_height=baseline_height,
            measurement=_measurement(baseline),
            screenshot_ref=screenshot_ref,
        )
    )

    restore_key = f"__webAbleTextReflow_{uuid4().hex}"
    text_scenario: TextReflowScenario | None = None
    measurement_completed = False
    try:
        enlarged = await asyncio.wait_for(
            page.evaluate(
                _MEASURE_PAGE,
                {
                    "maxElements": MAX_INSPECTED_ELEMENTS,
                    "enlargeText": True,
                    "holdFontStyles": True,
                    "restoreKey": restore_key,
                    "stabilizeLayout": True,
                },
            ),
            timeout=SCENARIO_TIMEOUT_SECONDS,
        )
        classification, findings = _analyze(
            "text_200_percent", enlarged, baseline, "1.4.4"
        )
        scenario_details = [
            "This is a deterministic per-element computed-font-size override, not browser text-only zoom. It does not evaluate whether clipped or truncated content remains available. Pseudo-element text, canvas text, images of text, and content beyond the bounded element sample may not be represented."
        ]
        if baseline.get("candidatesTruncated"):
            scenario_details.append(
                f"Baseline text-element discovery was capped at {MAX_INSPECTED_ELEMENTS} candidates."
            )
        if enlarged.get("candidatesTruncated"):
            scenario_details.append(
                f"Text-element inspection was capped at {MAX_INSPECTED_ELEMENTS} candidates."
            )
        text_scenario = TextReflowScenario(
            scenario_id="text_200_percent",
            status="completed",
            classification=classification,
            condition="Increase text to 200% without changing the CSS viewport or scaling the whole page.",
            method="Temporarily set each discovered visible text-bearing element's computed font size to twice its baseline value, measure, capture any suspicious state, then restore styles.",
            criterion_ids=["1.4.4"],
            viewport_width=baseline_width,
            viewport_height=baseline_height,
            measurement=_measurement(enlarged),
            baseline_measurement=_measurement(baseline),
            findings=findings,
            details=scenario_details,
        )
        measurement_completed = True
        text_scenario = await _capture_scenario_evidence(
            page,
            text_scenario,
            viewport_name=viewport_name,
            capture_id=capture_id,
            capture_screenshot=capture_screenshot,
        )
    except Exception as error:
        text_scenario = TextReflowScenario(
            scenario_id="text_200_percent",
            status="error",
            classification="error",
            condition="Increase each discovered visible text-bearing element's computed font size to 200%.",
            method="Temporarily set per-element computed font sizes to twice their original size, measure the page, then restore inline styles.",
            criterion_ids=["1.4.4"],
            viewport_width=baseline_width,
            viewport_height=baseline_height,
            baseline_measurement=_measurement(baseline),
            details=[f"Text enlargement scenario failed ({type(error).__name__})."],
        )
    finally:
        try:
            styles_restored = await asyncio.wait_for(
                page.evaluate(
                    _RESTORE_FONT_STYLES,
                    {"restoreKey": restore_key},
                ),
                timeout=SCENARIO_TIMEOUT_SECONDS,
            )
            if (
                measurement_completed
                and not styles_restored
                and text_scenario is not None
            ):
                text_scenario = replace(
                    text_scenario,
                    details=[
                        *text_scenario.details,
                        "The temporary font-size overrides were not present when restoration ran.",
                    ],
                )
        except Exception as error:
            if text_scenario is not None:
                text_scenario = replace(
                    text_scenario,
                    details=[
                        *text_scenario.details,
                        f"Temporary font-size styles could not be restored ({type(error).__name__}).",
                    ],
                )
    assert text_scenario is not None
    scenarios.append(text_scenario)

    if not callable(getattr(page, "set_viewport_size", None)):
        scenarios.append(
            TextReflowScenario(
                scenario_id="reflow_320_css_px",
                status="unsupported",
                classification="unsupported",
                condition="Reflow at a 320 CSS-pixel viewport width and the captured viewport height.",
                method="Playwright CSS viewport resizing is unavailable on this page adapter.",
                criterion_ids=["1.4.10"],
                viewport_width=320,
                viewport_height=baseline_height,
                baseline_measurement=_measurement(baseline),
                details=["The page adapter does not support viewport resizing."],
            )
        )
    else:
        viewport_error: str | None = None
        narrow: dict | None = None
        narrow_scenario: TextReflowScenario | None = None
        try:
            await asyncio.wait_for(
                page.set_viewport_size({"width": 320, "height": baseline_height}),
                timeout=SCENARIO_TIMEOUT_SECONDS,
            )
            narrow = await asyncio.wait_for(
                page.evaluate(
                    _MEASURE_PAGE,
                    {
                        "maxElements": MAX_INSPECTED_ELEMENTS,
                        "enlargeText": False,
                        "stabilizeLayout": True,
                    },
                ),
                timeout=SCENARIO_TIMEOUT_SECONDS,
            )
            classification, findings = _analyze(
                "reflow_320_css_px", narrow, baseline, "1.4.10"
            )
            scenario_details = [
                "The 320 CSS-pixel condition checks vertical-scrolling content. Document or element overflow alone is not classified as a confirmed violation; two-dimensional content and scrolling exceptions require review."
            ]
            if narrow.get("candidatesTruncated"):
                scenario_details.append(
                    f"Text-element inspection was capped at {MAX_INSPECTED_ELEMENTS} candidates."
                )
            if baseline.get("candidatesTruncated"):
                scenario_details.append(
                    f"Baseline text-element discovery was capped at {MAX_INSPECTED_ELEMENTS} candidates."
                )
            narrow_scenario = TextReflowScenario(
                scenario_id="reflow_320_css_px",
                status="completed",
                classification=classification,
                condition="320 CSS-pixel viewport width at the captured viewport height.",
                method="Resize the existing page viewport, measure CSS-pixel geometry, capture any suspicious state, then restore the original viewport.",
                criterion_ids=["1.4.10"],
                viewport_width=320,
                viewport_height=baseline_height,
                measurement=_measurement(narrow),
                baseline_measurement=_measurement(baseline),
                findings=findings,
                details=scenario_details,
            )
            narrow_scenario = await _capture_scenario_evidence(
                page,
                narrow_scenario,
                viewport_name=viewport_name,
                capture_id=capture_id,
                capture_screenshot=capture_screenshot,
            )
        except Exception as error:
            viewport_error = f"Narrow-viewport scenario failed ({type(error).__name__})."
        finally:
            try:
                await asyncio.wait_for(
                    page.set_viewport_size(
                        {"width": baseline_width, "height": baseline_height}
                    ),
                    timeout=SCENARIO_TIMEOUT_SECONDS,
                )
            except Exception as error:
                viewport_error = (
                    "The original viewport could not be restored "
                    f"({type(error).__name__})."
                )
        if narrow is None or viewport_error:
            scenarios.append(
                TextReflowScenario(
                    scenario_id="reflow_320_css_px",
                    status="error",
                    classification="error",
                    condition="Reflow at a 320 CSS-pixel viewport width and the captured viewport height.",
                    method="Temporarily resize the existing Playwright page viewport to 320 CSS pixels wide, then restore its original dimensions.",
                    criterion_ids=["1.4.10"],
                    viewport_width=320,
                    viewport_height=baseline_height,
                    baseline_measurement=_measurement(baseline),
                    details=[viewport_error or "Narrow-viewport measurements were unavailable."],
                )
            )
        else:
            assert narrow_scenario is not None
            scenarios.append(narrow_scenario)

            two_dimensional_content = any(
                element.get("twoDimensionalRegion")
                for element in baseline.get("elements", [])
            )
            if two_dimensional_content:
                short_height: dict | None = None
                short_height_error: str | None = None
                short_height_scenario: TextReflowScenario | None = None
                try:
                    await asyncio.wait_for(
                        page.set_viewport_size({"width": baseline_width, "height": 256}),
                        timeout=SCENARIO_TIMEOUT_SECONDS,
                    )
                    short_height = await asyncio.wait_for(
                        page.evaluate(
                            _MEASURE_PAGE,
                            {
                                "maxElements": MAX_INSPECTED_ELEMENTS,
                                "enlargeText": False,
                                "stabilizeLayout": True,
                            },
                        ),
                        timeout=SCENARIO_TIMEOUT_SECONDS,
                    )
                    classification, findings = _analyze(
                        "reflow_256_css_px_height",
                        short_height,
                        baseline,
                        "1.4.10",
                    )
                    short_height_scenario = TextReflowScenario(
                        scenario_id="reflow_256_css_px_height",
                        status="completed",
                        classification=classification,
                        condition="256 CSS-pixel viewport height at the captured CSS width for detected two-dimensional content.",
                        method="Temporarily resize the existing page viewport height, measure text geometry, capture any suspicious state, then restore the original dimensions.",
                        criterion_ids=["1.4.10"],
                        viewport_width=baseline_width,
                        viewport_height=256,
                        baseline_measurement=_measurement(baseline),
                        measurement=_measurement(short_height),
                        findings=findings,
                        details=[
                            "Detection of two-dimensional content is heuristic. The 256-pixel height condition does not decide whether a specific table, diagram, or other region qualifies for the WCAG exception."
                        ],
                    )
                    short_height_scenario = await _capture_scenario_evidence(
                        page,
                        short_height_scenario,
                        viewport_name=viewport_name,
                        capture_id=capture_id,
                        capture_screenshot=capture_screenshot,
                    )
                except Exception as error:
                    short_height_error = (
                        f"256 CSS-pixel height scenario failed ({type(error).__name__})."
                    )
                finally:
                    try:
                        await asyncio.wait_for(
                            page.set_viewport_size(
                                {"width": baseline_width, "height": baseline_height}
                            ),
                            timeout=SCENARIO_TIMEOUT_SECONDS,
                        )
                    except Exception as error:
                        short_height_error = (
                            "The original viewport could not be restored after the 256-pixel "
                            f"height scenario ({type(error).__name__})."
                        )
                if short_height is None or short_height_error:
                    scenarios.append(
                        TextReflowScenario(
                            scenario_id="reflow_256_css_px_height",
                            status="error",
                            classification="error",
                            condition="256 CSS-pixel viewport height for detected two-dimensional content.",
                            method="Temporarily resize the existing page viewport height to 256 CSS pixels, then restore its original dimensions.",
                            criterion_ids=["1.4.10"],
                            viewport_width=baseline_width,
                            viewport_height=256,
                            baseline_measurement=_measurement(baseline),
                            details=[short_height_error or "Height measurements were unavailable."],
                        )
                    )
                else:
                    assert short_height_scenario is not None
                    scenarios.append(short_height_scenario)
            else:
                scenarios.append(
                    TextReflowScenario(
                        scenario_id="reflow_256_css_px_height",
                        status="not_tested",
                        classification="not_tested",
                        condition="256 CSS-pixel viewport height for horizontally scrolling two-dimensional content.",
                        method="No detected table or ARIA table/grid content made this condition applicable in the bounded baseline sample.",
                        criterion_ids=["1.4.10"],
                        viewport_width=baseline_width,
                        viewport_height=256,
                        baseline_measurement=_measurement(baseline),
                        details=["No qualifying two-dimensional region was detected; this is not proof that none exists."],
                    )
                )

    scenarios.append(
        TextReflowScenario(
            scenario_id="browser_zoom_200_percent",
            status="unsupported",
            classification="unsupported",
            condition="Actual browser zoom at 200%.",
            method="Not simulated: Playwright Chromium in this capture configuration does not expose a reliable, verified browser-zoom control. CSS transforms, device scale factor changes, and altered screenshot dimensions are not substitutes.",
            criterion_ids=["1.4.4"],
            viewport_width=baseline_width,
            viewport_height=baseline_height,
            baseline_measurement=_measurement(baseline),
            details=["Actual browser zoom was not tested; no proxy simulation was used."],
        )
    )
    scenario_statuses = {scenario.status for scenario in scenarios}
    status: TextReflowAuditStatus = (
        "unavailable"
        if all(scenario.status in ("error", "not_tested") for scenario in scenarios)
        else "partial"
        if "error" in scenario_statuses or "unsupported" in scenario_statuses
        else "available"
    )
    if status != "available":
        details.append(
            "One or more scenarios are unsupported or could not complete; inspect each scenario status."
        )
    return TextReflowAuditResult(status=status, scenarios=scenarios, details=details)

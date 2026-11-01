from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Literal, Protocol

TargetSizeAuditStatus = Literal[
    "available", "partial", "unavailable", "not_tested"
]
TARGET_SIZE_THRESHOLD_CSS_PX = 24
MAX_TARGETS = 500
AUDIT_TIMEOUT_SECONDS = 5


@dataclass(frozen=True)
class TargetSizeFinding:
    criterion_id: Literal["2.5.8"]
    selector: str
    tag_name: str
    role: str | None
    accessible_name: str | None
    width_css_px: float
    height_css_px: float
    left_css_px: float
    top_css_px: float
    classification: Literal["needs_review"] = "needs_review"


@dataclass(frozen=True)
class TargetSizeAuditResult:
    status: TargetSizeAuditStatus
    inspected_targets: int = 0
    findings: list[TargetSizeFinding] = field(default_factory=list)
    details: list[str] = field(default_factory=list)


class TargetSizePage(Protocol):
    async def evaluate(self, expression: str, argument: object = None) -> dict:
        ...


async def audit_target_size(
    page: TargetSizePage,
    *,
    timeout_seconds: int = AUDIT_TIMEOUT_SECONDS,
) -> TargetSizeAuditResult:
    """Report measurable undersized pointer-target candidates for human review."""
    try:
        result = await asyncio.wait_for(
            page.evaluate(
                """(limits) => {
                    const selector = [
                      "a[href]", "area[href]", "button",
                      "input:not([type=hidden])", "select", "textarea",
                      "summary", "audio[controls]", "video[controls]",
                      "[role=button]", "[role=link]",
                      "[tabindex]:not([tabindex='-1'])"
                    ].join(",");
                    const isVisibleTarget = element => {
                      const style = getComputedStyle(element);
                      return element.getClientRects().length > 0 &&
                        style.display !== "none" &&
                        style.visibility !== "hidden" &&
                        style.visibility !== "collapse" &&
                        Number(style.opacity) !== 0 &&
                        style.pointerEvents !== "none" &&
                        !element.matches(":disabled") &&
                        !element.closest("[hidden],[inert]");
                    };
                    const selectorFor = element => {
                      if (element.id) return `#${CSS.escape(element.id)}`;
                      const parts = [];
                      let node = element;
                      while (node && node.nodeType === Node.ELEMENT_NODE &&
                             parts.length < 5) {
                        let part = node.tagName.toLowerCase();
                        if (node.parentElement) {
                          const sameTag = [...node.parentElement.children]
                            .filter(child => child.tagName === node.tagName);
                          if (sameTag.length > 1) {
                            part += `:nth-of-type(${sameTag.indexOf(node) + 1})`;
                          }
                        }
                        parts.unshift(part);
                        node = node.parentElement;
                      }
                      return parts.join(" > ");
                    };
                    const nameFor = element => {
                      const labelledBy = element.getAttribute("aria-labelledby");
                      const referencedName = labelledBy
                        ? labelledBy.split(/\\s+/)
                            .map(id => document.getElementById(id)?.innerText || "")
                            .join(" ")
                        : "";
                      const labels = element.labels
                        ? [...element.labels].map(label => label.innerText || "").join(" ")
                        : "";
                      const value = element.getAttribute("aria-label") ||
                        referencedName || labels ||
                        element.getAttribute("alt") ||
                        element.getAttribute("title") || element.innerText || "";
                      return value.replace(/\\s+/g, " ").trim().slice(0, 120) || null;
                    };
                    const candidates = [...document.querySelectorAll(selector)]
                      .filter(isVisibleTarget);
                    const inspected = candidates.slice(0, limits.maxTargets);
                    const undersized = [];
                    for (const element of inspected) {
                      const rect = element.getBoundingClientRect();
                      if (rect.width >= limits.threshold &&
                          rect.height >= limits.threshold) continue;
                      undersized.push({
                        selector: selectorFor(element),
                        tag_name: element.tagName.toLowerCase(),
                        role: element.getAttribute("role"),
                        accessible_name: nameFor(element),
                        width_css_px: Math.round(rect.width * 100) / 100,
                        height_css_px: Math.round(rect.height * 100) / 100,
                        left_css_px: Math.round(rect.left * 100) / 100,
                        top_css_px: Math.round(rect.top * 100) / 100
                      });
                    }
                    return {
                      inspected_targets: inspected.length,
                      candidate_targets: candidates.length,
                      undersized
                    };
                }""",
                {
                    "maxTargets": MAX_TARGETS,
                    "threshold": TARGET_SIZE_THRESHOLD_CSS_PX,
                },
            ),
            timeout=timeout_seconds,
        )
        if not isinstance(result, dict):
            raise TypeError("target-size audit result must be an object.")
        inspected_targets = result["inspected_targets"]
        candidate_targets = result["candidate_targets"]
        raw_findings = result["undersized"]
        if (
            not isinstance(inspected_targets, int)
            or not isinstance(candidate_targets, int)
            or not isinstance(raw_findings, list)
            or inspected_targets < 0
            or candidate_targets < inspected_targets
        ):
            raise TypeError("target-size audit returned invalid measurements.")
        findings = [
            TargetSizeFinding(criterion_id="2.5.8", **finding)
            for finding in raw_findings
            if isinstance(finding, dict)
        ]
        if len(findings) != len(raw_findings):
            raise TypeError("target-size audit returned an invalid finding.")
        details = [
            "Undersized measurements are review candidates, not confirmed WCAG failures. "
            "The spacing, inline, equivalent-control, user-agent, and essential exceptions "
            "are not evaluated."
        ]
        if candidate_targets > MAX_TARGETS:
            details.append(
                f"Target discovery was limited to the first {MAX_TARGETS} visible targets."
            )
        return TargetSizeAuditResult(
            status="partial" if candidate_targets > MAX_TARGETS else "available",
            inspected_targets=inspected_targets,
            findings=findings,
            details=details,
        )
    except TimeoutError:
        return TargetSizeAuditResult(
            status="unavailable",
            details=["The target-size audit exceeded its time limit."],
        )
    except Exception as error:
        return TargetSizeAuditResult(
            status="unavailable",
            details=[f"The target-size audit failed ({type(error).__name__})."],
        )

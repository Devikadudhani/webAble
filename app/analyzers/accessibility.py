from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Protocol

from app.capture.url_safety import sanitize_url

AccessibilityScanStatus = Literal[
    "available", "partial", "unavailable", "not_attempted"
]
NonTextContrastStatus = Literal[
    "available", "partial", "unavailable", "not_tested"
]

AXE_CORE_VERSION = "4.14.0"
AXE_CORE_SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "node_modules"
    / "axe-core"
    / "axe.min.js"
)
WCAG_AA_TAGS = (
    "wcag2a",
    "wcag2aa",
    "wcag21a",
    "wcag21aa",
    "wcag22aa",
)
SCAN_TIMEOUT_SECONDS = 20
ACCESSIBILITY_SCAN_TIMEOUT_SECONDS = SCAN_TIMEOUT_SECONDS
MAX_RULES_PER_RESULT = 500
MAX_NODES_PER_RULE = 100
MAX_CHECKS_PER_NODE = 30
MAX_TOTAL_NODES = 1_000
MAX_RELATED_NODES_PER_CHECK = 20
MAX_SNIPPET_LENGTH = 2_000
MAX_NON_TEXT_CONTRAST_ELEMENTS = 300
MAX_NON_TEXT_CONTRAST_FINDINGS = 50
_VALUE_ATTRIBUTE = re.compile(
    r"""(\bvalue\s*=\s*)(["']).*?\2""", re.IGNORECASE | re.DOTALL
)
_URL_ATTRIBUTE = re.compile(
    r"""(\b(?:href|src|action)\s*=\s*)(["'])(.*?)\2""",
    re.IGNORECASE | re.DOTALL,
)


@dataclass(frozen=True)
class AxeCheckEvidence:
    check_id: str
    impact: str | None
    message: str
    data: dict | list | str | int | float | bool | None
    related_nodes: list[dict]


@dataclass(frozen=True)
class AxeNodeEvidence:
    target: list[str | list[str]]
    html: str
    impact: str | None
    failure_summary: str | None
    any_checks: list[AxeCheckEvidence]
    all_checks: list[AxeCheckEvidence]
    none_checks: list[AxeCheckEvidence]


@dataclass(frozen=True)
class AxeRuleEvidence:
    rule_id: str
    description: str
    impact: str | None
    help: str
    help_url: str
    tags: list[str]
    nodes: list[AxeNodeEvidence]
    failure_summaries: list[str]


@dataclass(frozen=True)
class NonTextContrastFinding:
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


@dataclass(frozen=True)
class NonTextContrastAuditResult:
    status: NonTextContrastStatus
    inspected_components: int = 0
    inspected_graphics: int = 0
    findings: list[NonTextContrastFinding] = field(default_factory=list)
    details: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class AccessibilityScanResult:
    status: AccessibilityScanStatus
    axe_version: str | None = None
    violations: list[AxeRuleEvidence] = field(default_factory=list)
    incomplete: list[AxeRuleEvidence] = field(default_factory=list)
    passes: list[AxeRuleEvidence] = field(default_factory=list)
    inapplicable: list[AxeRuleEvidence] = field(default_factory=list)
    non_text_contrast: NonTextContrastAuditResult = field(
        default_factory=lambda: NonTextContrastAuditResult(
            status="not_tested",
            details=["Non-text contrast audit was not attempted."],
        )
    )
    details: list[str] = field(default_factory=list)


class AccessibilityPage(Protocol):
    async def add_script_tag(self, *, content: str) -> object:
        ...

    async def evaluate(self, expression: str, argument: Any) -> dict:
        ...


_AUDIT_NON_TEXT_CONTRAST = """({maxElements, maxFindings}) => {
  const selectorFor = element => {
    if (element.id &&
        document.querySelectorAll(`#${CSS.escape(element.id)}`).length === 1) {
      return `#${CSS.escape(element.id)}`;
    }
    const parts = [];
    for (let node = element; node && node.nodeType === Node.ELEMENT_NODE;
         node = node.parentElement) {
      let part = node.tagName.toLowerCase();
      if (node.parentElement) {
        const sameTag = [...node.parentElement.children]
          .filter(child => child.tagName === node.tagName);
        if (sameTag.length > 1) {
          part += `:nth-of-type(${sameTag.indexOf(node) + 1})`;
        }
      }
      parts.unshift(part);
    }
    return parts.join(" > ");
  };
  const visible = element => {
    const style = getComputedStyle(element);
    const rect = element.getBoundingClientRect();
    return element.getClientRects().length > 0 &&
      rect.width > 0 && rect.height > 0 &&
      style.display !== "none" &&
      style.visibility !== "hidden" &&
      style.visibility !== "collapse" &&
      style.contentVisibility !== "hidden" &&
      Number(style.opacity) !== 0 &&
      !element.closest("[hidden],[inert]");
  };
  const canvas = document.createElement("canvas");
  canvas.width = 1;
  canvas.height = 1;
  const context = canvas.getContext("2d", {willReadFrequently: true});
  const colorFor = value => {
    if (!value || !context || !CSS.supports("color", value)) return null;
    context.clearRect(0, 0, 1, 1);
    context.fillStyle = "#000";
    try {
      context.fillStyle = value;
      context.fillRect(0, 0, 1, 1);
      return [...context.getImageData(0, 0, 1, 1).data]
        .map((channel, index) => index === 3 ? channel / 255 : channel);
    } catch (_error) {
      return null;
    }
  };
  const composite = (foreground, background) => {
    if (!foreground || !background) return null;
    const alpha = foreground[3] + background[3] * (1 - foreground[3]);
    if (alpha <= 0) return null;
    return [
      (foreground[0] * foreground[3] +
       background[0] * background[3] * (1 - foreground[3])) / alpha,
      (foreground[1] * foreground[3] +
       background[1] * background[3] * (1 - foreground[3])) / alpha,
      (foreground[2] * foreground[3] +
       background[2] * background[3] * (1 - foreground[3])) / alpha,
      alpha
    ];
  };
  const solidBackdrop = element => {
    const ancestors = [];
    for (let node = element.parentElement; node; node = node.parentElement) {
      const style = getComputedStyle(node);
      if (style.backgroundImage !== "none") return null;
      const color = colorFor(style.backgroundColor);
      if (color && color[3] > 0) ancestors.push(color);
    }
    let result = [255, 255, 255, 1];
    for (let index = ancestors.length - 1; index >= 0; index -= 1) {
      result = composite(ancestors[index], result);
      if (!result) return null;
    }
    return result;
  };
  const opacityThrough = (element, stopAt) => {
    let opacity = 1;
    for (let node = element; node; node = node.parentElement) {
      opacity *= Number(getComputedStyle(node).opacity);
      if (node === stopAt) break;
    }
    return opacity;
  };
  const rgbOver = (color, backdrop, opacity) => {
    if (!color || !backdrop || opacity < 1) return null;
    const result = composite(color, backdrop);
    if (!result || result[3] < 0.999) return null;
    return result.slice(0, 3).map(channel => channel / 255);
  };
  const luminance = color => {
    const linear = color.map(channel =>
      channel <= 0.04045 ? channel / 12.92 :
        ((channel + 0.055) / 1.055) ** 2.4
    );
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2];
  };
  const ratio = (first, second) => {
    if (!first || !second) return null;
    const firstLuminance = luminance(first);
    const secondLuminance = luminance(second);
    return (Math.max(firstLuminance, secondLuminance) + 0.05) /
      (Math.min(firstLuminance, secondLuminance) + 0.05);
  };
  const elements = [...document.querySelectorAll([
    "button", "input:not([type=hidden])", "select", "textarea",
    "a[href]", "summary", "[role=button]", "[role=link]",
    "[role=checkbox]", "[role=radio]", "[role=switch]", "[role=slider]",
    "[role=tab]", "[role=combobox]", "[role=menuitem]",
    "svg path", "svg circle", "svg rect", "svg line",
    "svg polyline", "svg polygon", "svg ellipse"
  ].join(","))].filter(visible);
  const findings = [];
  for (const element of elements.slice(0, maxElements)) {
    const style = getComputedStyle(element);
    const rect = element.getBoundingClientRect();
    const backdrop = solidBackdrop(element);
    const effectiveOpacity = opacityThrough(element, null);
    const pairs = [];
    const addPair = (part, colorValue, adjacent, opacity) => {
      if (!backdrop || !colorValue || opacity < 1) return;
      const rendered = rgbOver(colorFor(colorValue), backdrop, opacity);
      const adjacentColor = rgbOver(adjacent, backdrop, 1);
      const contrast = ratio(rendered, adjacentColor);
      if (contrast !== null && contrast < 3) {
        pairs.push({
          visual_part: part,
          foreground_color: colorValue,
          adjacent_color: `rgb(${adjacentColor.map(value => Math.round(value * 255)).join(", ")})`,
          contrast_ratio: Math.round(contrast * 100) / 100,
          required_ratio: 3
        });
      }
    };
    const elementBackground = colorFor(style.backgroundColor);
    const backgroundOpaque = elementBackground && elementBackground[3] > 0;
    const isSvgShape = element.namespaceURI === "http://www.w3.org/2000/svg";
    if (!isSvgShape && backgroundOpaque &&
        style.backgroundImage === "none" &&
        style.appearance !== "auto") {
      addPair("component_background_boundary", style.backgroundColor, backdrop, effectiveOpacity);
    }
    if (isSvgShape) {
      const fill = style.fill;
      const stroke = style.stroke;
      const fillOpacity = effectiveOpacity * Number(style.fillOpacity);
      const strokeOpacity = effectiveOpacity * Number(style.strokeOpacity);
      if (fill !== "none" && !fill.startsWith("url(")) {
        addPair("svg_fill", fill, backdrop, fillOpacity);
      }
      if (stroke !== "none" && !stroke.startsWith("url(")) {
        addPair("svg_stroke", stroke, backdrop, strokeOpacity);
      }
    } else {
      for (const side of ["Top", "Right", "Bottom", "Left"]) {
        const borderWidth = parseFloat(style[`border${side}Width`]) || 0;
        const borderStyle = style[`border${side}Style`];
        if (borderWidth > 0 && borderStyle !== "none" && borderStyle !== "hidden") {
          addPair(
            `border_${side.toLowerCase()}`,
            style[`border${side}Color`],
            backdrop,
            effectiveOpacity
          );
        }
      }
      const outlineWidth = parseFloat(style.outlineWidth) || 0;
      if (outlineWidth > 0 && style.outlineStyle !== "none") {
        addPair("outline", style.outlineColor, backdrop, effectiveOpacity);
      }
    }
    if (pairs.length) {
      findings.push({
        selector: selectorFor(element),
        tag_name: element.tagName.toLowerCase(),
        role: element.getAttribute("role"),
        geometry: {
          left: rect.left, top: rect.top, right: rect.right,
          bottom: rect.bottom, width: rect.width, height: rect.height
        },
        color_pairs: pairs
      });
      if (findings.length >= maxFindings) break;
    }
  }
  const graphics = [...document.querySelectorAll("img,canvas,video:not([controls])")]
    .filter(visible);
  return {
    viewport: {width: innerWidth, height: innerHeight},
    inspected_components: Math.min(elements.length, maxElements),
    component_count: elements.length,
    inspected_graphics: graphics.length,
    candidates_truncated: elements.length > maxElements,
    findings
  };
}""";


async def audit_non_text_contrast(
    page: AccessibilityPage,
    *,
    timeout_seconds: int = SCAN_TIMEOUT_SECONDS,
) -> NonTextContrastAuditResult:
    """Collect bounded CSS-color contrast candidates for manual evaluation."""
    try:
        raw = await asyncio.wait_for(
            page.evaluate(
                _AUDIT_NON_TEXT_CONTRAST,
                {
                    "maxElements": MAX_NON_TEXT_CONTRAST_ELEMENTS,
                    "maxFindings": MAX_NON_TEXT_CONTRAST_FINDINGS,
                },
            ),
            timeout=timeout_seconds,
        )
    except TimeoutError:
        return NonTextContrastAuditResult(
            status="unavailable",
            details=["The non-text contrast probe exceeded its time limit."],
        )
    except Exception as error:
        return NonTextContrastAuditResult(
            status="unavailable",
            details=[
                f"The non-text contrast probe could not complete ({type(error).__name__})."
            ],
        )
    try:
        viewport = raw["viewport"]
        findings = [
            NonTextContrastFinding(
                classification="needs_review",
                potential_issue_detected=True,
                confirmed_violation=False,
                manual_review_required=True,
                selector=item["selector"],
                tag_name=item["tag_name"],
                role=item.get("role"),
                geometry=item["geometry"],
                viewport=viewport,
                color_pairs=item["color_pairs"],
                limitations=[
                    "A low computed-color ratio is a potential issue only; automation cannot determine whether this visual part is necessary to identify a component, state, or graphical object.",
                    "CSS geometry and solid colors do not represent every rendered pixel, gradient, image, canvas, blend mode, or overlapping layer.",
                ],
            )
            for item in raw["findings"]
        ]
        details = [
            "The probe compares selected solid CSS component boundaries and SVG fills/strokes against an estimated adjacent solid background and reports ratios below 3:1 for manual review only."
        ]
        if raw["inspected_graphics"]:
            details.append(
                f"{raw['inspected_graphics']} visible image, canvas, or video elements were not pixel-sampled and require separate visual review."
            )
        if raw["candidates_truncated"]:
            details.append(
                f"Component discovery was capped at {MAX_NON_TEXT_CONTRAST_ELEMENTS}; absence of additional findings is inconclusive."
            )
        details.extend(
            [
                "Color pairs at or above 3:1 are not a pass: the probe does not establish that it found every required boundary or graphical object.",
                "Potential low-contrast pairs are not confirmed violations because semantic necessity, applicable exceptions, and the complete rendered appearance require human evaluation.",
            ]
        )
        return NonTextContrastAuditResult(
            status="partial",
            inspected_components=raw["inspected_components"],
            inspected_graphics=raw["inspected_graphics"],
            findings=findings,
            details=details,
        )
    except (KeyError, TypeError, ValueError):
        return NonTextContrastAuditResult(
            status="unavailable",
            details=[
                "The non-text contrast probe returned an invalid evidence structure."
            ],
        )


async def scan_accessibility(
    page: AccessibilityPage,
    *,
    script_path: Path = AXE_CORE_SCRIPT,
    timeout_seconds: int = SCAN_TIMEOUT_SECONDS,
) -> AccessibilityScanResult:
    """Run WCAG A/AA tagged axe rules on an already loaded Playwright page."""
    try:
        script = script_path.read_text(encoding="utf-8")
    except OSError:
        return AccessibilityScanResult(
            status="unavailable",
            details=[
                "The pinned axe-core script is unavailable; install JavaScript dependencies with npm ci."
            ],
        )

    try:
        await page.add_script_tag(content=script)
        raw_result = await asyncio.wait_for(
            page.evaluate(
                """async (tags) => {
                    if (!window.axe || typeof window.axe.run !== "function") {
                        throw new Error("axe-core did not initialize.");
                    }
                    return window.axe.run(document, {
                        runOnly: {type: "tag", values: tags}
                    });
                }""",
                list(WCAG_AA_TAGS),
            ),
            timeout=timeout_seconds,
        )
    except TimeoutError:
        return AccessibilityScanResult(
            status="unavailable",
            details=["The accessibility engine exceeded its time limit."],
        )
    except Exception as error:
        return AccessibilityScanResult(
            status="unavailable",
            details=[
                f"The accessibility engine could not complete ({type(error).__name__})."
            ],
        )

    try:
        details: list[str] = []
        collections = {
            key: raw_result[key]
            for key in ("violations", "incomplete", "passes", "inapplicable")
        }
        normalized = {}
        remaining_nodes = MAX_TOTAL_NODES
        for key, rules in collections.items():
            if not isinstance(rules, list):
                raise TypeError("axe result collections must be lists.")
            if len(rules) > MAX_RULES_PER_RESULT:
                details.append(
                    f"The {key} collection was limited to {MAX_RULES_PER_RESULT} rules."
                )
            normalized_rules = []
            for rule in rules[:MAX_RULES_PER_RESULT]:
                node_limit = min(MAX_NODES_PER_RULE, remaining_nodes)
                normalized_rule = _rule_evidence(rule, details, node_limit)
                normalized_rules.append(normalized_rule)
                remaining_nodes -= len(normalized_rule.nodes)
            normalized[key] = normalized_rules
        axe_version = raw_result.get("testEngine", {}).get("version")
        if axe_version != AXE_CORE_VERSION:
            details.append(
                "The reported axe-core version did not match the pinned package version."
            )
        non_text_contrast = await audit_non_text_contrast(
            page,
            timeout_seconds=timeout_seconds,
        )
        return AccessibilityScanResult(
            status="partial" if details else "available",
            axe_version=axe_version,
            violations=normalized["violations"],
            incomplete=normalized["incomplete"],
            passes=normalized["passes"],
            inapplicable=normalized["inapplicable"],
            non_text_contrast=non_text_contrast,
            details=details,
        )
    except (KeyError, TypeError, ValueError):
        return AccessibilityScanResult(
            status="unavailable",
            details=["The accessibility engine returned an invalid result structure."],
        )


def _rule_evidence(
    rule: dict, details: list[str], node_limit: int
) -> AxeRuleEvidence:
    if not isinstance(rule, dict):
        raise TypeError("axe rule result must be an object.")
    raw_nodes = rule.get("nodes", [])
    if not isinstance(raw_nodes, list):
        raise TypeError("axe rule nodes must be a list.")
    if len(raw_nodes) > node_limit:
        details.append(
            f"Rule {rule.get('id', 'unknown')} node evidence was limited to {node_limit} nodes."
        )
    nodes = [
        _node_evidence(node, details)
        for node in raw_nodes[:node_limit]
    ]
    return AxeRuleEvidence(
        rule_id=str(rule["id"]),
        description=str(rule.get("description", "")),
        impact=rule.get("impact"),
        help=str(rule.get("help", "")),
        help_url=str(rule.get("helpUrl", "")),
        tags=[str(tag) for tag in rule.get("tags", [])],
        nodes=nodes,
        failure_summaries=[
            node.failure_summary for node in nodes if node.failure_summary
        ],
    )


def _node_evidence(node: dict, details: list[str]) -> AxeNodeEvidence:
    if not isinstance(node, dict):
        raise TypeError("axe node result must be an object.")
    html = _bounded_html(str(node.get("html", "")), details)

    checks = {
        key: [
            _check_evidence(check, details)
            for check in node.get(key, [])[:MAX_CHECKS_PER_NODE]
        ]
        for key in ("any", "all", "none")
    }
    if any(len(node.get(key, [])) > MAX_CHECKS_PER_NODE for key in checks):
        details.append("One or more axe check lists were truncated.")
    return AxeNodeEvidence(
        target=node.get("target", []),
        html=html,
        impact=node.get("impact"),
        failure_summary=node.get("failureSummary"),
        any_checks=checks["any"],
        all_checks=checks["all"],
        none_checks=checks["none"],
    )


def _sanitize_snippet_url(value: str) -> str:
    return sanitize_url(value)


def _sanitize_html(html: str) -> str:
    html = _VALUE_ATTRIBUTE.sub(r"\1\2[redacted]\2", html)
    return _URL_ATTRIBUTE.sub(
        lambda match: (
            f"{match.group(1)}{match.group(2)}"
            f"{_sanitize_snippet_url(match.group(3))}{match.group(2)}"
        ),
        html,
    )


def _bounded_html(html: str, details: list[str]) -> str:
    html = _sanitize_html(html)
    if len(html) > MAX_SNIPPET_LENGTH:
        details.append("One or more HTML evidence snippets were truncated.")
        return html[:MAX_SNIPPET_LENGTH] + "..."
    return html


def _check_evidence(check: dict, details: list[str]) -> AxeCheckEvidence:
    if not isinstance(check, dict):
        raise TypeError("axe check result must be an object.")
    raw_related_nodes = check.get("relatedNodes", [])
    if len(raw_related_nodes) > MAX_RELATED_NODES_PER_CHECK:
        details.append("One or more axe related-node lists were truncated.")
    return AxeCheckEvidence(
        check_id=str(check.get("id", "")),
        impact=check.get("impact"),
        message=str(check.get("message", "")),
        data=check.get("data"),
        related_nodes=[
            {
                **related_node,
                "html": _bounded_html(
                    str(related_node.get("html", "")), details
                ),
            }
            for related_node in raw_related_nodes[:MAX_RELATED_NODES_PER_CHECK]
            if isinstance(related_node, dict)
        ],
    )

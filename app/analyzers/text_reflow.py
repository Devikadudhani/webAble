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
HOVER_FOCUS_SCENARIO_TIMEOUT_SECONDS = 20
MAX_HOVER_FOCUS_CANDIDATES = 4
MAX_HOVER_FOCUS_ELEMENTS = 800


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
    mouse: HoverFocusMouse
    keyboard: HoverFocusKeyboard

    async def evaluate(self, expression: str, argument: Any) -> Any:
        ...

    async def set_viewport_size(self, viewport_size: dict[str, int]) -> None:
        ...

    async def wait_for_timeout(self, timeout: float) -> None:
        ...


class HoverFocusMouse(Protocol):
    async def move(self, x: float, y: float) -> None:
        ...


class HoverFocusKeyboard(Protocol):
    async def press(self, key: str) -> None:
        ...


ScenarioScreenshotCapture = Callable[
    [TextReflowPage, str, str, str, int, int], Awaitable[str]
]


_MEASURE_PAGE = """async (options) => {
    const maxElements = options.maxElements;
    const all = document.querySelectorAll("*");
    const idCounts = new Map();
    const textCandidates = [];
    const selectorCache = new WeakMap();
    const selectorFor = (element) => {
      const cached = selectorCache.get(element);
      if (cached) return cached;

      const chain = [];
      let node = element;
      while (
        node &&
        node.nodeType === Node.ELEMENT_NODE &&
        !selectorCache.has(node)
      ) {
        if (node.id && idCounts.get(node.id) === 1) {
          selectorCache.set(node, `#${CSS.escape(node.id)}`);
          break;
        }
        chain.push(node);
        node = node.parentElement;
      }

      let selector = node ? selectorCache.get(node) || "" : "";
      for (let index = chain.length - 1; index >= 0; index -= 1) {
        const current = chain[index];
        let part = current.tagName.toLowerCase();
        const parent = current.parentElement;
        if (parent && parent.children.length > 1) {
          const childIndex = [...parent.children].indexOf(current) + 1;
          part += `:nth-child(${childIndex})`;
        }
        selector = selector ? `${selector} > ${part}` : part;
        selectorCache.set(current, selector);
      }
      return selectorCache.get(element) || "";
    };
    const contentSignatureFor = (element) => {
      const controlValue = element.matches("input,textarea,select")
        ? element.value
        : "";
      const content = `${element.getAttribute("aria-label") || ""} ${controlValue} ${element.textContent || ""}`
        .replace(/\\s+/g, " ")
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
    for (const element of all) {
      if (element.id) {
        idCounts.set(element.id, (idCounts.get(element.id) || 0) + 1);
      }
      if (
        textCandidates.length <= maxElements &&
        visible(element) &&
        textBearing(element)
      ) {
        textCandidates.push(element);
      }
    }
    const originalViewport = {
      width: window.innerWidth,
      height: window.innerHeight
    };
    const doc = document.documentElement;
    const body = document.body;
    const originalInlineStyles = [];
    const originalSpacingStyles = [];
    let retainInlineStyles = false;
    let retainSpacingStyles = false;
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
      if (options.applyTextSpacing) {
        const spacingProperties = [
          "line-height", "margin-bottom", "letter-spacing", "word-spacing"
        ];
        const spacingCandidates = textCandidates.slice(0, maxElements);
        for (const element of spacingCandidates) {
          originalSpacingStyles.push({
            element,
            properties: Object.fromEntries(spacingProperties.map(property => [
              property,
              {
                value: element.style.getPropertyValue(property),
                priority: element.style.getPropertyPriority(property)
              }
            ]))
          });
        }
        if (options.holdSpacingStyles && originalSpacingStyles.length) {
          window[options.spacingRestoreKey] = originalSpacingStyles;
          retainSpacingStyles = true;
        }
        for (const original of originalSpacingStyles) {
          const element = original.element;
          element.style.setProperty("line-height", "1.5", "important");
          element.style.setProperty("letter-spacing", "0.12em", "important");
          element.style.setProperty("word-spacing", "0.16em", "important");
          if (element.matches("p")) {
            element.style.setProperty("margin-bottom", "2em", "important");
          }
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
        let scrollContainerMetrics = null;
        let twoDimensionalRegion = null;
        for (let ancestor = element.parentElement; ancestor; ancestor = ancestor.parentElement) {
          const ancestorStyle = getComputedStyle(ancestor);
          const clipsOrScrollsX = ["auto", "scroll", "overlay", "hidden", "clip"]
            .includes(ancestorStyle.overflowX);
          const clipsOrScrollsY = ["auto", "scroll", "overlay", "hidden", "clip"]
            .includes(ancestorStyle.overflowY);
          const overflowsX = ancestor.scrollWidth > ancestor.clientWidth + 1;
          const overflowsY = ancestor.scrollHeight > ancestor.clientHeight + 1;
          if (!scrollContainer &&
              ((clipsOrScrollsX && overflowsX) ||
               (clipsOrScrollsY && overflowsY))) {
            scrollContainer = selectorFor(ancestor);
            const containerRect = ancestor.getBoundingClientRect();
            scrollContainerMetrics = {
              selector: scrollContainer,
              overflowX: ancestorStyle.overflowX,
              overflowY: ancestorStyle.overflowY,
              clientWidth: ancestor.clientWidth,
              scrollWidth: ancestor.scrollWidth,
              clientHeight: ancestor.clientHeight,
              scrollHeight: ancestor.scrollHeight,
              rect: {
                left: containerRect.left,
                top: containerRect.top,
                right: containerRect.right,
                bottom: containerRect.bottom,
                width: containerRect.width,
                height: containerRect.height
              }
            };
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
          visible: visible(element),
          contentSignature: contentSignatureFor(element),
          left: rect.left,
          right: rect.right,
          top: rect.top,
          bottom: rect.bottom,
          width: rect.width,
          height: rect.height,
          fontSize: style.fontSize,
          lineHeight: style.lineHeight,
          letterSpacing: style.letterSpacing,
          wordSpacing: style.wordSpacing,
          paragraphSpacing: element.matches("p") ? style.marginBottom : null,
          clientWidth: element.clientWidth,
          scrollWidth: element.scrollWidth,
          clientHeight: element.clientHeight,
          scrollHeight: element.scrollHeight,
          containerOverflowX: element.scrollWidth > element.clientWidth + 1,
          containerOverflowY: element.scrollHeight > element.clientHeight + 1,
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
          scrollContainerMetrics,
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
      const controlQuery = [
        "a[href]", "area[href]", "button", "input:not([type=hidden])",
        "select", "textarea", "summary", "[role=button]", "[role=link]",
        "[tabindex]:not([tabindex='-1'])"
      ].join(",");
      const controls = [...document.querySelectorAll(controlQuery)]
        .slice(0, maxElements)
        .map(element => {
          const rect = element.getBoundingClientRect();
          const isVisible = visible(element);
          const points = isVisible && rect.width > 0 && rect.height > 0
            ? [
                [rect.left + rect.width / 2, rect.top + rect.height / 2],
                [rect.left + Math.min(2, rect.width / 2), rect.top + Math.min(2, rect.height / 2)],
                [rect.right - Math.min(2, rect.width / 2), rect.top + Math.min(2, rect.height / 2)],
                [rect.left + Math.min(2, rect.width / 2), rect.bottom - Math.min(2, rect.height / 2)],
                [rect.right - Math.min(2, rect.width / 2), rect.bottom - Math.min(2, rect.height / 2)]
              ].filter(([x, y]) =>
                x >= 0 && y >= 0 &&
                x < window.innerWidth && y < window.innerHeight
              )
            : [];
          const occluders = points.map(([x, y]) => document.elementFromPoint(x, y))
            .filter(hit => hit && hit !== element && !element.contains(hit))
            .map(selectorFor);
          const style = getComputedStyle(element);
          return {
            selector: selectorFor(element),
            parentSelector: element.parentElement
              ? selectorFor(element.parentElement)
              : null,
            tagName: element.tagName.toLowerCase(),
            visible: isVisible,
            rect: {
              left: rect.left, top: rect.top, right: rect.right,
              bottom: rect.bottom, width: rect.width, height: rect.height
            },
            occludedSamples: occluders.length,
            totalHitSamples: points.length,
            occluders: [...new Set(occluders)],
            overflowX: style.overflowX,
            overflowY: style.overflowY
          };
        });
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
        appliedSpacingElements: originalSpacingStyles.length,
        candidatesTruncated: textCandidates.length > maxElements,
        elements: elementEvidence,
        controls,
        controlsTruncated: document.querySelectorAll(controlQuery).length > maxElements,
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
      if (!retainSpacingStyles) {
        for (const original of originalSpacingStyles) {
          for (const [property, value] of Object.entries(original.properties)) {
            if (value.value) {
              original.element.style.setProperty(
                property, value.value, value.priority
              );
            } else {
              original.element.style.removeProperty(property);
            }
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

_RESTORE_TEXT_SPACING_STYLES = """(options) => {
  const originals = window[options.restoreKey];
  if (!Array.isArray(originals)) return false;
  try {
    for (const original of originals) {
      for (const [property, value] of Object.entries(original.properties)) {
        if (value.value) {
          original.element.style.setProperty(
            property, value.value, value.priority
          );
        } else {
          original.element.style.removeProperty(property);
        }
      }
    }
    return true;
  } finally {
    delete window[options.restoreKey];
  }
}"""

_HOVER_FOCUS_CANDIDATES = """({maxCandidates}) => {
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
    return element.getClientRects().length > 0 &&
      style.display !== "none" &&
      style.visibility !== "hidden" &&
      style.visibility !== "collapse" &&
      style.contentVisibility !== "hidden" &&
      Number(style.opacity) !== 0 &&
      !element.closest("[hidden],[inert]");
  };
  const selector = [
    "a[href]", "area[href]", "button", "input:not([type=hidden])",
    "select", "textarea", "summary", "[role=button]", "[role=link]",
    "[tabindex]", "[title]", "[aria-describedby]", "[aria-haspopup]",
    "[data-tooltip]", "[data-toggle]"
  ].join(",");
  const all = [...new Set(document.querySelectorAll(selector))]
    .filter(element => visible(element) && !element.matches(":disabled"));
  const candidates = all.slice(0, maxCandidates).map(element => {
    const rect = element.getBoundingClientRect();
    return {
      selector: selectorFor(element),
      parentSelector: element.parentElement
        ? selectorFor(element.parentElement)
        : null,
      tagName: element.tagName.toLowerCase(),
      role: element.getAttribute("role"),
      label: (
        element.getAttribute("aria-label") ||
        element.getAttribute("title") ||
        element.innerText ||
        ""
      ).replace(/\\s+/g, " ").trim().slice(0, 120),
      rect: {
        left: rect.left, top: rect.top, right: rect.right,
        bottom: rect.bottom, width: rect.width, height: rect.height
      }
    };
  });
  const active = document.activeElement;
  return {
    candidates,
    candidateCount: all.length,
    candidatesTruncated: all.length > maxCandidates,
    originalFocus: active && active !== document.body &&
      active !== document.documentElement ? selectorFor(active) : null,
    viewport: {width: innerWidth, height: innerHeight}
  };
}""";

_HOVER_FOCUS_SNAPSHOT = """({maxElements}) => {
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
    return element.getClientRects().length > 0 &&
      style.display !== "none" &&
      style.visibility !== "hidden" &&
      style.visibility !== "collapse" &&
      style.contentVisibility !== "hidden" &&
      Number(style.opacity) !== 0 &&
      !element.closest("[hidden],[inert]");
  };
  const signature = value => {
    let hash = 2166136261;
    for (let index = 0; index < value.length; index += 1) {
      hash = Math.imul(hash ^ value.charCodeAt(index), 16777619);
    }
    return `${value.length}:${(hash >>> 0).toString(16)}`;
  };
  const all = [...document.querySelectorAll("*")];
  const visibleElements = all.filter(element =>
    visible(element) && element.getAttribute("aria-hidden") !== "true"
  );
  const elements = visibleElements.slice(0, maxElements).map(element => {
    const rect = element.getBoundingClientRect();
    const text = (
      element.innerText ||
      element.getAttribute("aria-label") ||
      element.getAttribute("title") ||
      ""
    ).replace(/\\s+/g, " ").trim();
    const style = getComputedStyle(element);
    return {
      selector: selectorFor(element),
      tagName: element.tagName.toLowerCase(),
      role: element.getAttribute("role"),
      title: element.getAttribute("title"),
      ariaLabel: element.getAttribute("aria-label"),
      textLength: text.length,
      contentSignature: signature(text),
      position: style.position,
      zIndex: style.zIndex,
      rect: {
        left: rect.left, top: rect.top, right: rect.right,
        bottom: rect.bottom, width: rect.width, height: rect.height
      }
    };
  });
  return {
    elements,
    elementsTruncated: visibleElements.length > maxElements
  };
}""";

_HOVER_FOCUS_CONTENT_OVERLAP = """({contentSelector, triggerSelector}) => {
  const content = document.querySelector(contentSelector);
  const trigger = document.querySelector(triggerSelector);
  if (!content || !trigger) return {overlaps: [], unavailable: true};
  const rect = content.getBoundingClientRect();
  const overlaps = [];
  for (const element of document.querySelectorAll("p,li,button,a[href],label,h1,h2,h3,h4,h5,h6,[role=button],[role=link]")) {
    if (element === content || element === trigger ||
        content.contains(element) || element.contains(content) ||
        trigger.contains(element) || element.contains(trigger) ||
        !element.getClientRects().length) continue;
    const other = element.getBoundingClientRect();
    const width = Math.min(rect.right, other.right) - Math.max(rect.left, other.left);
    const height = Math.min(rect.bottom, other.bottom) - Math.max(rect.top, other.top);
    if (width > 2 && height > 2) {
      overlaps.push({
        selector: element.id
          ? `#${CSS.escape(element.id)}`
          : (() => {
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
            })(),
        tagName: element.tagName.toLowerCase(),
        overlapWidth: width,
        overlapHeight: height,
        rect: {
          left: other.left, top: other.top, right: other.right,
          bottom: other.bottom, width: other.width, height: other.height
        }
      });
    }
    if (overlaps.length >= 20) break;
  }
  const controls = [...content.querySelectorAll("button,a[href],[role=button]")]
    .map(element => ({
      selector: element.id ? `#${CSS.escape(element.id)}` : element.tagName.toLowerCase(),
      label: (
        element.getAttribute("aria-label") ||
        element.getAttribute("title") ||
        element.innerText ||
        ""
      ).replace(/\\s+/g, " ").trim().slice(0, 80)
    }))
    .filter(item => /close|dismiss|hide|cancel/i.test(item.label))
    .slice(0, 10);
  return {overlaps, possibleDismissControls: controls};
}""";

_FOCUS_ELEMENT = """(selector) => {
  const element = document.querySelector(selector);
  if (!element) return false;
  element.focus({preventScroll: true});
  return document.activeElement === element;
}""";

_RESTORE_HOVER_FOCUS = """(selector) => {
  const active = document.activeElement;
  if (active && active !== document.body &&
      active !== document.documentElement && typeof active.blur === "function") {
    active.blur();
  }
  if (!selector) return true;
  const original = document.querySelector(selector);
  if (!original) return false;
  original.focus({preventScroll: true});
  return document.activeElement === original;
}""";

_ORIENTATION_SNAPSHOT = """({maxElements}) => {
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
    return element.getClientRects().length > 0 &&
      style.display !== "none" &&
      style.visibility !== "hidden" &&
      style.visibility !== "collapse" &&
      style.contentVisibility !== "hidden" &&
      Number(style.opacity) !== 0 &&
      !element.closest("[hidden],[inert],[aria-hidden='true']");
  };
  const signature = value => {
    let hash = 2166136261;
    for (let index = 0; index < value.length; index += 1) {
      hash = Math.imul(hash ^ value.charCodeAt(index), 16777619);
    }
    return `${value.length}:${(hash >>> 0).toString(16)}`;
  };
  const interactive = [
    "a[href]", "area[href]", "button", "input:not([type=hidden])",
    "select", "textarea", "summary", "[role=button]", "[role=link]",
    "[tabindex]:not([tabindex='-1'])"
  ].join(",");
  const candidates = [...document.querySelectorAll("*")].filter(element =>
    visible(element) &&
    (
      [...element.childNodes].some(node =>
        node.nodeType === Node.TEXT_NODE && node.textContent.trim().length > 0
      ) ||
      element.matches(interactive) ||
      element.matches("img[alt],svg[aria-label],canvas[aria-label],video[controls],audio[controls]")
    )
  );
  const elements = candidates.slice(0, maxElements).map(element => {
    const rect = element.getBoundingClientRect();
    const label = (
      element.innerText ||
      element.getAttribute("aria-label") ||
      element.getAttribute("title") ||
      element.getAttribute("alt") ||
      ""
    ).replace(/\\s+/g, " ").trim();
    const style = getComputedStyle(element);
    return {
      selector: selectorFor(element),
      tagName: element.tagName.toLowerCase(),
      role: element.getAttribute("role"),
      textLength: label.length,
      contentSignature: signature(label),
      position: style.position,
      rect: {
        left: rect.left, top: rect.top, right: rect.right,
        bottom: rect.bottom, width: rect.width, height: rect.height
      }
    };
  });
  return {
    viewport: {width: innerWidth, height: innerHeight},
    orientation: innerWidth >= innerHeight ? "landscape" : "portrait",
    document: {
      scrollWidth: Math.max(
        document.documentElement.scrollWidth,
        document.body ? document.body.scrollWidth : 0
      ),
      scrollHeight: Math.max(
        document.documentElement.scrollHeight,
        document.body ? document.body.scrollHeight : 0
      )
    },
    elements,
    candidateCount: candidates.length,
    candidatesTruncated: candidates.length > maxElements
  };
}""";


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
        if criterion_id == "1.4.12":
            spacing_effects = []
            if element.get("clippedText") and not (
                prior and prior.get("clippedText")
            ):
                spacing_effects.append("possible_text_clipping")
            if element.get("ellipsisTruncated") and not (
                prior and prior.get("ellipsisTruncated")
            ):
                spacing_effects.append("possible_text_truncation")
            for dimension, current_key, baseline_key in (
                ("horizontal", "scrollWidth", "scrollWidth"),
                ("vertical", "scrollHeight", "scrollHeight"),
            ):
                current_overflow = max(
                    0, int(element.get(current_key, 0))
                    - int(element.get(
                        "clientWidth" if dimension == "horizontal" else "clientHeight",
                        0,
                    ))
                )
                previous_overflow = max(
                    0,
                    int(prior.get(baseline_key, 0))
                    - int(prior.get(
                        "clientWidth" if dimension == "horizontal" else "clientHeight",
                        0,
                    ))
                ) if prior else 0
                if current_overflow > previous_overflow + 1 and not spacing_effects:
                    spacing_effects.append(
                        f"content_extends_beyond_{dimension}_container"
                    )
            current_scroll_container = element.get("scrollContainerMetrics")
            prior_scroll_container = (
                prior.get("scrollContainerMetrics") if prior else None
            )
            if (
                current_scroll_container
                and (
                    not prior_scroll_container
                    or current_scroll_container.get("scrollWidth", 0)
                    > prior_scroll_container.get("scrollWidth", 0) + 1
                    or current_scroll_container.get("scrollHeight", 0)
                    > prior_scroll_container.get("scrollHeight", 0) + 1
                )
                and not spacing_effects
            ):
                spacing_effects.append(
                    "content_extends_beyond_scrollable_container"
                )
            if prior and prior.get("visible", True) and not element.get("visible", True):
                spacing_effects.append("text_element_became_hidden")
            if spacing_effects:
                findings.append(
                    TextReflowFinding(
                        criterion_id="1.4.12",
                        level="AA",
                        classification="needs_review",
                        selector=selector,
                        tag_name=str(element.get("tagName", "")),
                        observation=(
                            "Text-spacing overrides produced geometry associated "
                            "with possible clipping, truncation, hiding, or content "
                            "extending beyond its container; actual loss of "
                            "information or functionality was not established."
                        ),
                        evidence={
                            "scenario_id": scenario_id,
                            "observations": spacing_effects,
                            "viewport": raw.get("viewport"),
                            "geometry": {
                                key: element.get(key)
                                for key in ("left", "top", "right", "bottom", "width", "height")
                            },
                            "container_measurements": {
                                key: element.get(key)
                                for key in (
                                    "clientWidth", "scrollWidth", "clientHeight",
                                    "scrollHeight", "overflowX", "overflowY",
                                    "scrollContainer", "scrollContainerMetrics",
                                    "twoDimensionalRegion",
                                )
                            },
                            "applied_spacing": {
                                key: element.get(key)
                                for key in (
                                    "fontSize", "lineHeight", "letterSpacing",
                                    "wordSpacing", "paragraphSpacing",
                                )
                            },
                            "content_signature": element.get("contentSignature"),
                        },
                        baseline_evidence=(
                            {
                                "viewport": (baseline or {}).get("viewport"),
                                "geometry": {
                                    key: prior.get(key)
                                    for key in ("left", "top", "right", "bottom", "width", "height")
                                },
                                "container_measurements": {
                                    key: prior.get(key)
                                    for key in (
                                        "clientWidth", "scrollWidth", "clientHeight",
                                        "scrollHeight", "overflowX", "overflowY",
                                        "scrollContainer", "scrollContainerMetrics",
                                    )
                                },
                                "visible": prior.get("visible"),
                            }
                            if prior
                            else None
                        ),
                        confidence="medium",
                        remediation=(
                            "Review the affected content and control in the tested "
                            "spacing state; allow the layout to grow or reflow and "
                            "verify that all information and functionality remain available."
                        ),
                    )
                )
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
    if criterion_id == "1.4.12":
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
                    criterion_id="1.4.12",
                    level="AA",
                    classification="needs_review",
                    selector=str(overlap["firstSelector"]),
                    tag_name="",
                    observation=(
                        "Text-bearing elements overlap after text-spacing overrides; "
                        "whether information or functionality is obscured requires review."
                    ),
                    evidence={
                        **overlap,
                        "viewport": raw.get("viewport"),
                        "geometry": {
                            selector: {
                                key: element.get(key)
                                for key in ("left", "top", "right", "bottom", "width", "height")
                            }
                            for selector in pair
                            for element in raw.get("elements", [])
                            if element.get("selector") == selector
                        },
                    },
                    baseline_evidence=None,
                    confidence="medium",
                    remediation=(
                        "Review both elements in the tested spacing state and adjust "
                        "layout or containment if text or controls are obscured."
                    ),
                )
            )
        baseline_controls = {
            item["selector"]: item
            for item in (baseline or {}).get("controls", [])
            if item.get("selector")
        }
        for control in raw.get("controls", []):
            selector = str(control.get("selector", ""))
            prior = baseline_controls.get(selector)
            if not selector or not prior:
                continue
            hidden = prior.get("visible") and not control.get("visible")
            new_occlusion = (
                control.get("occludedSamples", 0)
                > prior.get("occludedSamples", 0)
            )
            if not hidden and not new_occlusion:
                continue
            findings.append(
                TextReflowFinding(
                    criterion_id="1.4.12",
                    level="AA",
                    classification="needs_review",
                    selector=selector,
                    tag_name=str(control.get("tagName", "")),
                    observation=(
                        "A control became hidden after text-spacing overrides."
                        if hidden
                        else "A control had more sampled hit-test points intercepted "
                        "after text-spacing overrides."
                    ),
                    evidence={
                        "scenario_id": scenario_id,
                        "viewport": raw.get("viewport"),
                        "geometry": control.get("rect"),
                        "visible": control.get("visible"),
                        "occluded_samples": control.get("occludedSamples"),
                        "total_hit_samples": control.get("totalHitSamples"),
                        "occluders": control.get("occluders"),
                    },
                    baseline_evidence={
                        "geometry": prior.get("rect"),
                        "visible": prior.get("visible"),
                        "occluded_samples": prior.get("occludedSamples"),
                        "total_hit_samples": prior.get("totalHitSamples"),
                        "occluders": prior.get("occluders"),
                    },
                    confidence="medium",
                    remediation=(
                        "Review whether the control remains visible, reachable, and "
                        "operable after spacing changes."
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


def _new_hover_content(before: dict, after: dict, trigger_selector: str) -> list[dict]:
    previous = {
        item["selector"]: item
        for item in before.get("elements", [])
        if item.get("selector")
    }
    current = {
        item["selector"]: item
        for item in after.get("elements", [])
        if item.get("selector")
    }
    added = {
        selector
        for selector, item in current.items()
        if selector not in previous and item.get("textLength", 0) > 0
    }
    revealed = []
    for selector, item in current.items():
        if selector == trigger_selector or item.get("tagName") in {
            "html", "body", "main"
        }:
            continue
        prior = previous.get(selector)
        is_new = selector in added
        is_changed_popup = (
            prior is not None
            and prior.get("contentSignature") != item.get("contentSignature")
            and (
                item.get("role") in {"tooltip", "dialog", "alert", "status"}
                or item.get("title")
                or item.get("ariaLabel")
            )
        )
        if not is_new and not is_changed_popup:
            continue
        if is_new and item.get("parentSelector") in added:
            continue
        revealed.append(item)
    return revealed[:10]


async def _settle_hover_focus_state(page: TextReflowPage) -> None:
    await page.evaluate(
        "() => new Promise(resolve => requestAnimationFrame(() => "
        "requestAnimationFrame(resolve)))",
        {},
    )
    wait_for_timeout = getattr(page, "wait_for_timeout", None)
    if wait_for_timeout is not None:
        await wait_for_timeout(80)


async def _snapshot_hover_focus_state(page: TextReflowPage) -> dict:
    return await page.evaluate(
        _HOVER_FOCUS_SNAPSHOT,
        {"maxElements": MAX_HOVER_FOCUS_ELEMENTS},
    )


async def _audit_hover_focus_content(
    page: TextReflowPage,
    *,
    viewport_width: int,
    viewport_height: int,
    viewport_name: str,
    capture_id: str,
    capture_screenshot: ScenarioScreenshotCapture | None,
) -> tuple[list[TextReflowFinding], list[str], str | None, bool]:
    findings: list[TextReflowFinding] = []
    details: list[str] = []
    screenshot_ref: str | None = None
    discovery_truncated = False
    original_focus: str | None = None
    try:
        mouse = getattr(page, "mouse", None)
        keyboard = getattr(page, "keyboard", None)
        if mouse is None or keyboard is None:
            return [], [
                "The page adapter does not provide non-activating pointer and keyboard interaction."
            ], None, True

        initial_candidates = await page.evaluate(
            _HOVER_FOCUS_CANDIDATES,
            {"maxCandidates": MAX_HOVER_FOCUS_CANDIDATES},
        )
        original_focus = initial_candidates.get("originalFocus")
        await mouse.move(-5, -5)
        await page.evaluate("() => document.activeElement?.blur()", {})
        await _settle_hover_focus_state(page)
        candidates_result = await page.evaluate(
            _HOVER_FOCUS_CANDIDATES,
            {"maxCandidates": MAX_HOVER_FOCUS_CANDIDATES},
        )
        candidates = candidates_result.get("candidates", [])
        discovery_truncated = bool(
            candidates_result.get("candidatesTruncated")
            or initial_candidates.get("candidatesTruncated")
        )
        viewport = candidates_result.get("viewport") or {
            "width": viewport_width,
            "height": viewport_height,
        }
        neutral_state = await _snapshot_hover_focus_state(page)
        if neutral_state.get("elementsTruncated"):
            discovery_truncated = True

        for trigger in candidates:
            trigger_selector = trigger.get("selector")
            rect = trigger.get("rect") or {}
            if not trigger_selector or rect.get("width", 0) <= 0 or rect.get("height", 0) <= 0:
                continue
            center_x = (rect.get("left", 0) + rect.get("right", 0)) / 2
            center_y = (rect.get("top", 0) + rect.get("bottom", 0)) / 2
            if not (
                0 <= center_x < viewport.get("width", viewport_width)
                and 0 <= center_y < viewport.get("height", viewport_height)
            ):
                continue

            await mouse.move(center_x, center_y)
            await _settle_hover_focus_state(page)
            hovered_state = await _snapshot_hover_focus_state(page)
            if hovered_state.get("elementsTruncated"):
                discovery_truncated = True
            hover_content = _new_hover_content(
                neutral_state, hovered_state, trigger_selector
            )
            for content in hover_content:
                content_selector = content["selector"]
                overlap = await page.evaluate(
                    _HOVER_FOCUS_CONTENT_OVERLAP,
                    {
                        "contentSelector": content_selector,
                        "triggerSelector": trigger_selector,
                    },
                )
                if capture_screenshot is not None and screenshot_ref is None:
                    try:
                        screenshot_ref = await capture_screenshot(
                            page,
                            capture_id,
                            viewport_name,
                            "hover_focus_content",
                            viewport_width,
                            viewport_height,
                        )
                    except Exception as error:
                        details.append(
                            "Hover/focus scenario screenshot capture failed "
                            f"({type(error).__name__}); measurements and findings are retained."
                        )
                content_rect = content.get("rect") or {}
                content_x = (content_rect.get("left", 0) + content_rect.get("right", 0)) / 2
                content_y = (content_rect.get("top", 0) + content_rect.get("bottom", 0)) / 2
                can_enter_content = (
                    content_rect.get("width", 0) > 0
                    and content_rect.get("height", 0) > 0
                    and 0 <= content_x < viewport.get("width", viewport_width)
                    and 0 <= content_y < viewport.get("height", viewport_height)
                )
                hoverable = False
                if can_enter_content:
                    await mouse.move(content_x, content_y)
                    await _settle_hover_focus_state(page)
                    entered_state = await _snapshot_hover_focus_state(page)
                    hoverable = content_selector in {
                        item.get("selector")
                        for item in entered_state.get("elements", [])
                    }
                    if entered_state.get("elementsTruncated"):
                        discovery_truncated = True
                await mouse.move(-5, -5)
                await _settle_hover_focus_state(page)
                after_pointer_leaves = await _snapshot_hover_focus_state(page)
                persists_after_pointer_leaves = content_selector in {
                    item.get("selector")
                    for item in after_pointer_leaves.get("elements", [])
                }
                await mouse.move(center_x, center_y)
                await _settle_hover_focus_state(page)
                await keyboard.press("Escape")
                await _settle_hover_focus_state(page)
                after_escape = await _snapshot_hover_focus_state(page)
                escape_dismissed = content_selector not in {
                    item.get("selector")
                    for item in after_escape.get("elements", [])
                }
                overlaps = overlap.get("overlaps", [])
                potential_issue_indicators = []
                if can_enter_content and not hoverable:
                    potential_issue_indicators.append(
                        "The revealed content was not visible after the pointer moved into its bounds."
                    )
                if overlaps:
                    potential_issue_indicators.append(
                        "The revealed content rectangle intersects other text or controls; actual obscuration needs review."
                    )
                if overlaps and not escape_dismissed:
                    potential_issue_indicators.append(
                        "Escape did not dismiss content with a geometric overlap candidate."
                    )
                evidence = {
                    "scenario_id": "hover_focus_content",
                    "interaction": "hover",
                    "viewport": viewport,
                    "trigger_selector": trigger_selector,
                    "trigger_geometry": trigger.get("rect"),
                    "content_selector": content_selector,
                    "content_role": content.get("role"),
                    "content_geometry": content_rect,
                    "content_position": content.get("position"),
                    "content_z_index": content.get("zIndex"),
                    "content_text_signature": content.get("contentSignature"),
                    "content_text_length": content.get("textLength"),
                    "potentially_overlapped_content": overlaps,
                    "possible_dismiss_controls": overlap.get(
                        "possibleDismissControls", []
                    ),
                    "pointer_entered_content_remained_visible": hoverable,
                    "visible_after_pointer_left_trigger_and_content": (
                        persists_after_pointer_leaves
                    ),
                    "escape_dismissed_content": escape_dismissed,
                    "dismissibility_required_by_overlap_heuristic": bool(overlaps),
                    "overlap_is_geometric_and_requires_review": True,
                    "potential_issue_detected": bool(potential_issue_indicators),
                    "potential_issue_indicators": potential_issue_indicators,
                    "confirmed_violation": False,
                    "manual_review_required": True,
                }
                findings.append(
                    TextReflowFinding(
                        criterion_id="1.4.13",
                        level="AA",
                        classification="needs_review",
                        selector=trigger_selector,
                        tag_name=trigger.get("tagName", ""),
                        observation=(
                            "Content became visible on hover; pointer persistence, "
                            "dismissal, and possible overlap were sampled but require "
                            "manual evaluation."
                        ),
                        evidence=evidence,
                        baseline_evidence={
                            "content_visible": content_selector in {
                                item.get("selector")
                                for item in neutral_state.get("elements", [])
                            },
                            "viewport": viewport,
                        },
                        confidence=(
                            "medium"
                            if content.get("role") in {"tooltip", "dialog", "alert"}
                            else "low"
                        ),
                        remediation=(
                            "Verify the content can be dismissed when required, "
                            "remains available while the pointer moves over it, and "
                            "persists for the required interaction."
                        ),
                    )
                )
            await mouse.move(-5, -5)
            await page.evaluate("() => document.activeElement?.blur()", {})
            await _settle_hover_focus_state(page)
            before_focus = await _snapshot_hover_focus_state(page)
            focused = await page.evaluate(_FOCUS_ELEMENT, trigger_selector)
            if not focused:
                continue
            await _settle_hover_focus_state(page)
            focused_state = await _snapshot_hover_focus_state(page)
            if focused_state.get("elementsTruncated"):
                discovery_truncated = True
            focus_content = _new_hover_content(
                before_focus, focused_state, trigger_selector
            )
            for content in focus_content:
                content_selector = content["selector"]
                overlap = await page.evaluate(
                    _HOVER_FOCUS_CONTENT_OVERLAP,
                    {
                        "contentSelector": content_selector,
                        "triggerSelector": trigger_selector,
                    },
                )
                if capture_screenshot is not None and screenshot_ref is None:
                    try:
                        screenshot_ref = await capture_screenshot(
                            page,
                            capture_id,
                            viewport_name,
                            "hover_focus_content",
                            viewport_width,
                            viewport_height,
                        )
                    except Exception as error:
                        details.append(
                            "Hover/focus scenario screenshot capture failed "
                            f"({type(error).__name__}); measurements and findings are retained."
                        )
                await keyboard.press("Escape")
                await _settle_hover_focus_state(page)
                after_escape = await _snapshot_hover_focus_state(page)
                escape_dismissed = content_selector not in {
                    item.get("selector")
                    for item in after_escape.get("elements", [])
                }
                await page.evaluate(
                    "(selector) => document.querySelector(selector)?.blur()",
                    trigger_selector,
                )
                await _settle_hover_focus_state(page)
                after_blur = await _snapshot_hover_focus_state(page)
                overlaps = overlap.get("overlaps", [])
                potential_issue_indicators = []
                if overlaps:
                    potential_issue_indicators.append(
                        "The revealed content rectangle intersects other text or controls; actual obscuration needs review."
                    )
                if overlaps and not escape_dismissed:
                    potential_issue_indicators.append(
                        "Escape did not dismiss content with a geometric overlap candidate."
                    )
                evidence = {
                    "scenario_id": "hover_focus_content",
                    "interaction": "focus",
                    "viewport": viewport,
                    "trigger_selector": trigger_selector,
                    "trigger_geometry": trigger.get("rect"),
                    "content_selector": content_selector,
                    "content_role": content.get("role"),
                    "content_geometry": content.get("rect"),
                    "content_position": content.get("position"),
                    "content_z_index": content.get("zIndex"),
                    "content_text_signature": content.get("contentSignature"),
                    "content_text_length": content.get("textLength"),
                    "potentially_overlapped_content": overlaps,
                    "possible_dismiss_controls": overlap.get(
                        "possibleDismissControls", []
                    ),
                    "escape_dismissed_content": escape_dismissed,
                    "remained_visible_after_trigger_blur": content_selector in {
                        item.get("selector")
                        for item in after_blur.get("elements", [])
                    },
                    "dismissibility_required_by_overlap_heuristic": bool(overlaps),
                    "overlap_is_geometric_and_requires_review": True,
                    "potential_issue_detected": bool(potential_issue_indicators),
                    "potential_issue_indicators": potential_issue_indicators,
                    "confirmed_violation": False,
                    "manual_review_required": True,
                }
                findings.append(
                    TextReflowFinding(
                        criterion_id="1.4.13",
                        level="AA",
                        classification="needs_review",
                        selector=trigger_selector,
                        tag_name=trigger.get("tagName", ""),
                        observation=(
                            "Content became visible on focus; dismissal, persistence, "
                            "and possible overlap were sampled but require manual "
                            "evaluation."
                        ),
                        evidence=evidence,
                        baseline_evidence={
                            "content_visible": content_selector in {
                                item.get("selector")
                                for item in before_focus.get("elements", [])
                            },
                            "viewport": viewport,
                        },
                        confidence=(
                            "medium"
                            if content.get("role") in {"tooltip", "dialog", "alert"}
                            else "low"
                        ),
                        remediation=(
                            "Verify the revealed content remains available and can "
                            "be dismissed when it obscures or replaces other content."
                        ),
                    )
                )
            await page.evaluate(
                "(selector) => document.querySelector(selector)?.blur()",
                trigger_selector,
            )
            await _settle_hover_focus_state(page)

        if candidates_result.get("candidateCount", 0) == 0:
            details.append(
                "No visible candidate trigger was found by the bounded selector set; custom and non-DOM triggers may still exist."
            )
        else:
            details.append(
                f"Sampled {len(candidates)} of {candidates_result.get('candidateCount', 0)} visible candidate triggers without activating them."
            )
        if discovery_truncated:
            details.append(
                "Candidate or visible-element discovery reached its configured limit; absence of findings is inconclusive."
            )
        if not findings:
            details.append(
                "No new visible DOM content was detected in the sampled hover/focus states. Native browser tooltips, pseudo-element content, delayed states, and custom triggers are not reliably detected."
            )
        return findings[:MAX_FINDINGS], details, screenshot_ref, discovery_truncated
    finally:
        mouse = getattr(page, "mouse", None)
        if mouse is not None:
            try:
                await mouse.move(-5, -5)
            except Exception as error:
                details.append(
                    "The pointer could not be returned outside the page after the "
                    f"hover/focus probe ({type(error).__name__})."
                )
        try:
            focus_restored = await page.evaluate(
                _RESTORE_HOVER_FOCUS, original_focus
            )
            if not focus_restored:
                details.append(
                    "The original focused element was unavailable when focus restoration ran."
                )
        except Exception as error:
            details.append(
                "The page's original focus state could not be restored after the "
                f"hover/focus probe ({type(error).__name__})."
            )


async def _settle_orientation_layout(page: TextReflowPage) -> None:
    await page.evaluate(
        "() => new Promise(resolve => requestAnimationFrame(() => "
        "requestAnimationFrame(resolve)))",
        {},
    )
    wait_for_timeout = getattr(page, "wait_for_timeout", None)
    if wait_for_timeout is not None:
        await wait_for_timeout(80)


async def _snapshot_orientation(page: TextReflowPage) -> dict:
    return await page.evaluate(
        _ORIENTATION_SNAPSHOT,
        {"maxElements": MAX_INSPECTED_ELEMENTS},
    )


def _orientation_findings(
    portrait: dict,
    landscape: dict,
) -> tuple[list[TextReflowFinding], bool]:
    portrait_elements = {
        item["selector"]: item
        for item in portrait.get("elements", [])
        if item.get("selector")
    }
    landscape_elements = {
        item["selector"]: item
        for item in landscape.get("elements", [])
        if item.get("selector")
    }
    findings: list[TextReflowFinding] = []
    for selector in sorted(set(portrait_elements) | set(landscape_elements)):
        portrait_item = portrait_elements.get(selector)
        landscape_item = landscape_elements.get(selector)
        if portrait_item is None:
            change = "not_visible_in_portrait"
            observation = (
                "A text-bearing element or control was visible in landscape "
                "but not found in portrait."
            )
        elif landscape_item is None:
            change = "not_visible_in_landscape"
            observation = (
                "A text-bearing element or control was visible in portrait "
                "but not found in landscape."
            )
        elif (
            portrait_item.get("contentSignature")
            != landscape_item.get("contentSignature")
        ):
            change = "content_changed_between_orientations"
            observation = (
                "A text-bearing element or control had a different content "
                "signature between portrait and landscape."
            )
        else:
            continue
        reference = portrait_item or landscape_item
        assert reference is not None
        findings.append(
            TextReflowFinding(
                criterion_id="1.3.4",
                level="AA",
                classification="needs_review",
                selector=selector,
                tag_name=str(reference.get("tagName", "")),
                observation=observation,
                evidence={
                    "scenario_id": "orientation",
                    "potential_issue_detected": True,
                    "confirmed_violation": False,
                    "manual_review_required": True,
                    "orientation_change": change,
                    "portrait": {
                        "viewport": portrait.get("viewport"),
                        "visible": portrait_item is not None,
                        "element": portrait_item,
                    },
                    "landscape": {
                        "viewport": landscape.get("viewport"),
                        "visible": landscape_item is not None,
                        "element": landscape_item,
                    },
                    "exception_essentiality_evaluated": False,
                    "equivalent_content_evaluated": False,
                },
                baseline_evidence={
                    "portrait_visible": portrait_item is not None,
                    "landscape_visible": landscape_item is not None,
                    "portrait_content_signature": (
                        portrait_item.get("contentSignature")
                        if portrait_item
                        else None
                    ),
                    "landscape_content_signature": (
                        landscape_item.get("contentSignature")
                        if landscape_item
                        else None
                    ),
                },
                confidence="medium" if portrait_item is None or landscape_item is None else "low",
                remediation=(
                    "Review whether the content or functionality remains "
                    "available in both orientations, or whether the orientation "
                    "restriction is essential."
                ),
            )
        )
        if len(findings) >= MAX_FINDINGS:
            break
    truncated = bool(
        portrait.get("candidatesTruncated")
        or landscape.get("candidatesTruncated")
        or len(findings) >= MAX_FINDINGS
    )
    return findings, truncated


async def _audit_orientation(
    page: TextReflowPage,
    *,
    baseline_width: int,
    baseline_height: int,
    viewport_name: str,
    capture_id: str,
    capture_screenshot: ScenarioScreenshotCapture | None,
) -> TextReflowScenario:
    original_viewport = {"width": baseline_width, "height": baseline_height}
    landscape_viewport = {
        "width": max(baseline_width, baseline_height),
        "height": min(baseline_width, baseline_height),
    }
    portrait_viewport = {
        "width": min(baseline_width, baseline_height),
        "height": max(baseline_width, baseline_height),
    }
    portrait: dict | None = None
    landscape: dict | None = None
    findings: list[TextReflowFinding] = []
    details = [
        "This probe switches the CSS viewport between portrait and landscape dimensions. It does not emulate physical device rotation, orientation sensors, or every browser orientation-change event."
    ]
    scenario: TextReflowScenario | None = None
    screenshot_ref: str | None = None
    try:
        for label, viewport in (
            ("portrait", portrait_viewport),
            ("landscape", landscape_viewport),
        ):
            await asyncio.wait_for(
                page.set_viewport_size(viewport),
                timeout=SCENARIO_TIMEOUT_SECONDS,
            )
            await asyncio.wait_for(
                _settle_orientation_layout(page),
                timeout=SCENARIO_TIMEOUT_SECONDS,
            )
            state = await asyncio.wait_for(
                _snapshot_orientation(page),
                timeout=SCENARIO_TIMEOUT_SECONDS,
            )
            if label == "portrait":
                portrait = state
            else:
                landscape = state
        assert portrait is not None and landscape is not None
        findings, truncated = _orientation_findings(portrait, landscape)
        if truncated:
            details.append(
                f"Text/control discovery reached the {MAX_INSPECTED_ELEMENTS}-element limit in at least one orientation; an empty result is inconclusive."
            )
        if not findings:
            details.append(
                "No sampled text-bearing element or control disappeared or changed its opaque content signature between the two tested CSS viewport orientations. This does not establish that all functionality is available."
            )
        if findings and capture_screenshot is not None:
            evidence_state = next(
                (
                    (label, state)
                    for label, state in (
                        ("portrait", portrait),
                        ("landscape", landscape),
                    )
                    if any(
                        finding.evidence[label]["visible"]
                        is False
                        or finding.evidence["orientation_change"]
                        == "content_changed_between_orientations"
                        for finding in findings
                    )
                ),
                None,
            )
            if evidence_state is not None:
                label, state = evidence_state
                viewport = state["viewport"]
                try:
                    screenshot_ref = await capture_screenshot(
                        page,
                        capture_id,
                        viewport_name,
                        "orientation",
                        viewport["width"],
                        viewport["height"],
                    )
                except Exception as error:
                    details.append(
                        "Orientation scenario screenshot capture failed "
                        f"({type(error).__name__}); measurements and findings are retained."
                    )
        if screenshot_ref:
            findings = [
                replace(finding, screenshot_ref=screenshot_ref)
                for finding in findings
            ]
        scenario = TextReflowScenario(
            scenario_id="orientation",
            status="completed",
            classification=(
                "needs_review"
                if findings or truncated
                else "no_violation_detected"
            ),
            condition=(
                "Compare content and controls in portrait and landscape CSS viewport orientations."
            ),
            method=(
                "Resize the captured page to paired portrait and landscape CSS viewport dimensions, wait for layout stabilization, and compare bounded visible text-bearing elements and controls by selector and opaque content signature. Restore the original viewport after measurement."
            ),
            criterion_ids=["1.3.4"],
            viewport_width=landscape_viewport["width"],
            viewport_height=landscape_viewport["height"],
            measurement=(
                _measurement(
                    {
                        "viewport": landscape["viewport"],
                        "document": landscape["document"],
                        "inspectedTextElements": len(landscape["elements"]),
                        "overflowBoundaries": [],
                    }
                )
                if landscape
                else None
            ),
            baseline_measurement=(
                _measurement(
                    {
                        "viewport": portrait["viewport"],
                        "document": portrait["document"],
                        "inspectedTextElements": len(portrait["elements"]),
                        "overflowBoundaries": [],
                    }
                )
                if portrait
                else None
            ),
            findings=findings,
            screenshot_ref=screenshot_ref,
            details=details,
        )
    except Exception as error:
        scenario = TextReflowScenario(
            scenario_id="orientation",
            status="error",
            classification="error",
            condition="Compare content and controls in portrait and landscape CSS viewport orientations.",
            method="Resize the existing page viewport, measure bounded visible content, and restore the original dimensions.",
            criterion_ids=["1.3.4"],
            viewport_width=landscape_viewport["width"],
            viewport_height=landscape_viewport["height"],
            details=[
                *details,
                f"Orientation comparison failed ({type(error).__name__}); criterion evaluation is incomplete.",
            ],
        )
    finally:
        try:
            await asyncio.wait_for(
                page.set_viewport_size(original_viewport),
                timeout=SCENARIO_TIMEOUT_SECONDS,
            )
        except Exception as error:
            restore_detail = (
                "The original viewport could not be restored after orientation "
                f"testing ({type(error).__name__})."
            )
            if scenario is None:
                details.append(restore_detail)
            else:
                scenario = replace(
                    scenario,
                    status="error",
                    classification="error",
                    details=[*scenario.details, restore_detail],
                )
    assert scenario is not None
    return scenario


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

    spacing_restore_key = f"__webAbleTextSpacing_{uuid4().hex}"
    spacing_scenario: TextReflowScenario | None = None
    spacing_measurement_completed = False
    try:
        spaced = await asyncio.wait_for(
            page.evaluate(
                _MEASURE_PAGE,
                {
                    "maxElements": MAX_INSPECTED_ELEMENTS,
                    "applyTextSpacing": True,
                    "holdSpacingStyles": True,
                    "spacingRestoreKey": spacing_restore_key,
                    "stabilizeLayout": True,
                },
            ),
            timeout=SCENARIO_TIMEOUT_SECONDS,
        )
        classification, findings = _analyze(
            "text_spacing", spaced, baseline, "1.4.12"
        )
        scenario_details = [
            "Applies line-height 1.5, paragraph margin after 2em, letter-spacing 0.12em, and word-spacing 0.16em to bounded visible text candidates. Geometry changes are review evidence only; this probe does not establish that text, information, or functionality is unavailable."
        ]
        if baseline.get("candidatesTruncated") or spaced.get("candidatesTruncated"):
            scenario_details.append(
                f"Text discovery or inspection was capped at {MAX_INSPECTED_ELEMENTS} candidates."
            )
        if spaced.get("controlsTruncated"):
            scenario_details.append(
                f"Interactive-control inspection was capped at {MAX_INSPECTED_ELEMENTS} candidates."
            )
        if any(
            finding.evidence.get("container_measurements", {}).get("scrollContainer")
            for finding in findings
        ):
            scenario_details.append(
                "Some reported content is inside a scrollable container; scrolling may be intentional and is not classified as a failure."
            )
        spacing_scenario = TextReflowScenario(
            scenario_id="text_spacing",
            status="completed",
            classification=classification,
            condition=(
                "Apply WCAG text-spacing values at the captured CSS viewport: "
                "line height 1.5, paragraph spacing 2em, letter spacing 0.12em, "
                "and word spacing 0.16em."
            ),
            method=(
                "Capture baseline geometry, temporarily apply inline-important "
                "spacing overrides to up to 300 visible text-bearing elements, "
                "measure content/control geometry and overlap, capture suspicious "
                "state, then restore original inline properties."
            ),
            criterion_ids=["1.4.12"],
            viewport_width=baseline_width,
            viewport_height=baseline_height,
            measurement=_measurement(spaced),
            baseline_measurement=_measurement(baseline),
            findings=findings,
            details=scenario_details,
        )
        spacing_measurement_completed = True
        spacing_scenario = await _capture_scenario_evidence(
            page,
            spacing_scenario,
            viewport_name=viewport_name,
            capture_id=capture_id,
            capture_screenshot=capture_screenshot,
        )
    except Exception as error:
        spacing_scenario = TextReflowScenario(
            scenario_id="text_spacing",
            status="error",
            classification="error",
            condition="Apply the specified WCAG 1.4.12 text-spacing values.",
            method=(
                "Temporarily apply spacing properties, measure changed geometry, "
                "then restore original inline styles."
            ),
            criterion_ids=["1.4.12"],
            viewport_width=baseline_width,
            viewport_height=baseline_height,
            baseline_measurement=_measurement(baseline),
            details=[f"Text-spacing scenario failed ({type(error).__name__})."],
        )
    finally:
        try:
            styles_restored = await asyncio.wait_for(
                page.evaluate(
                    _RESTORE_TEXT_SPACING_STYLES,
                    {"restoreKey": spacing_restore_key},
                ),
                timeout=SCENARIO_TIMEOUT_SECONDS,
            )
            if (
                spacing_measurement_completed
                and spaced.get("appliedSpacingElements", 0) > 0
                and not styles_restored
                and spacing_scenario is not None
            ):
                spacing_scenario = replace(
                    spacing_scenario,
                    details=[
                        *spacing_scenario.details,
                        "The temporary text-spacing overrides were not present when restoration ran.",
                    ],
                )
        except Exception as error:
            if spacing_scenario is not None:
                spacing_scenario = replace(
                    spacing_scenario,
                    details=[
                        *spacing_scenario.details,
                        f"Temporary text-spacing styles could not be restored ({type(error).__name__}).",
                    ],
                )
    assert spacing_scenario is not None
    scenarios.append(spacing_scenario)

    try:
        orientation_scenario = await _audit_orientation(
            page,
            baseline_width=baseline_width,
            baseline_height=baseline_height,
            viewport_name=viewport_name,
            capture_id=capture_id,
            capture_screenshot=capture_screenshot,
        )
    except Exception as error:
        orientation_scenario = TextReflowScenario(
            scenario_id="orientation",
            status="error",
            classification="error",
            condition="Compare content and controls in portrait and landscape CSS viewport orientations.",
            method="Resize the existing page viewport, measure bounded visible content, and restore the original dimensions.",
            criterion_ids=["1.3.4"],
            viewport_width=max(baseline_width, baseline_height),
            viewport_height=min(baseline_width, baseline_height),
            baseline_measurement=_measurement(baseline),
            details=[
                f"Orientation comparison failed ({type(error).__name__}); criterion evaluation is incomplete."
            ],
        )
    scenarios.append(orientation_scenario)

    hover_focus_mouse = getattr(page, "mouse", None)
    hover_focus_keyboard = getattr(page, "keyboard", None)
    if hover_focus_mouse is None or hover_focus_keyboard is None:
        scenarios.append(
            TextReflowScenario(
                scenario_id="hover_focus_content",
                status="unsupported",
                classification="unsupported",
                condition="Content revealed by non-activating pointer hover or keyboard focus.",
                method="This page adapter does not expose both pointer movement and keyboard Escape input.",
                criterion_ids=["1.4.13"],
                viewport_width=baseline_width,
                viewport_height=baseline_height,
                baseline_measurement=_measurement(baseline),
                details=[
                    "The interaction probe requires a real browser pointer and keyboard; this adapter cannot execute it safely."
                ],
            )
        )
    else:
        try:
            (
                hover_focus_findings,
                hover_focus_details,
                hover_focus_screenshot,
                hover_focus_truncated,
            ) = await asyncio.wait_for(
                _audit_hover_focus_content(
                    page,
                    viewport_width=baseline_width,
                    viewport_height=baseline_height,
                    viewport_name=viewport_name,
                    capture_id=capture_id,
                    capture_screenshot=capture_screenshot,
                ),
                timeout=HOVER_FOCUS_SCENARIO_TIMEOUT_SECONDS,
            )
            has_sampled_candidates = any(
                item.startswith("Sampled ")
                for item in hover_focus_details
            )
            if hover_focus_findings or hover_focus_truncated:
                hover_focus_classification: ScenarioClassification = "needs_review"
            elif has_sampled_candidates:
                hover_focus_classification = "no_violation_detected"
            else:
                hover_focus_classification = "needs_review"
            if hover_focus_screenshot:
                hover_focus_findings = [
                    replace(finding, screenshot_ref=hover_focus_screenshot)
                    for finding in hover_focus_findings
                ]
            scenarios.append(
                TextReflowScenario(
                    scenario_id="hover_focus_content",
                    status="completed",
                    classification=hover_focus_classification,
                    condition="Trigger visible custom content with pointer hover and non-activating keyboard focus.",
                    method=(
                        "Sample a bounded set of visible likely triggers; compare visible DOM content before and after hover/focus; test pointer entry, Escape dismissal, and blur behavior; record geometry, viewport, and possible overlaps. No controls are activated."
                    ),
                    criterion_ids=["1.4.13"],
                    viewport_width=baseline_width,
                    viewport_height=baseline_height,
                    baseline_measurement=_measurement(baseline),
                    findings=hover_focus_findings,
                    screenshot_ref=hover_focus_screenshot,
                    details=hover_focus_details,
                )
            )
        except Exception as error:
            scenarios.append(
                TextReflowScenario(
                    scenario_id="hover_focus_content",
                    status="error",
                    classification="error",
                    condition="Content revealed by non-activating pointer hover or keyboard focus.",
                    method="Sample bounded visible triggers and compare DOM visibility and geometry across hover/focus states.",
                    criterion_ids=["1.4.13"],
                    viewport_width=baseline_width,
                    viewport_height=baseline_height,
                    baseline_measurement=_measurement(baseline),
                    details=[
                        f"Hover/focus content scenario failed ({type(error).__name__}); criterion evaluation is incomplete."
                    ],
                )
            )

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

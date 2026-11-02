from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Literal, Protocol

KeyboardCheckStatus = Literal[
    "pass", "fail", "needs_review", "not_tested", "error"
]
KeyboardAuditStatus = Literal[
    "available", "partial", "unavailable", "not_tested"
]

MAX_CANDIDATES = 50
MAX_TAB_ACTIONS = MAX_CANDIDATES + 1
MAX_SHIFT_TAB_ACTIONS = 2
ACTION_TIMEOUT_SECONDS = 1
AUDIT_TIMEOUT_SECONDS = 8


@dataclass(frozen=True)
class KeyboardFocusEvidence:
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
    occluding_selector: str | None = None
    target_rect: dict[str, float] = field(default_factory=dict)
    viewport: dict[str, int] = field(default_factory=dict)
    occlusion_status: Literal[
        "confirmed_failure",
        "potential_issue",
        "no_issue_detected",
        "not_evaluated",
    ] = "not_evaluated"
    occluding_evidence: list[dict] = field(default_factory=list)
    details: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class KeyboardCheck:
    check_id: str
    criterion_ids: list[str]
    status: KeyboardCheckStatus
    summary: str
    evidence: list[dict] = field(default_factory=list)


@dataclass(frozen=True)
class KeyboardFocusAuditResult:
    status: KeyboardAuditStatus
    checks: list[KeyboardCheck] = field(default_factory=list)
    findings: list[KeyboardFocusEvidence] = field(default_factory=list)
    details: list[str] = field(default_factory=list)
    candidate_limitations: list[str] = field(default_factory=list)
    late_candidates: list[str] = field(default_factory=list)
    unexpected_focus_targets: list[str] = field(default_factory=list)
    tab_actions: int = 0
    shift_tab_actions: int = 0


class KeyboardPage(Protocol):
    keyboard: KeyboardInput

    async def evaluate(self, expression: str, argument: object = None) -> object:
        ...

    async def route(self, url: str, handler: object) -> None:
        ...

    async def unroute(self, url: str, handler: object) -> None:
        ...


class KeyboardInput(Protocol):
    async def press(self, key: str) -> None:
        ...


_SNAPSHOT = """(baselineStylesBySelector) => {
    const selectorFor = (element) => {
      if (element.id) return `#${CSS.escape(element.id)}`;
      const parts = [];
      let node = element;
      while (node && node.nodeType === Node.ELEMENT_NODE && parts.length < 5) {
        let part = node.tagName.toLowerCase();
        if (node.parentElement) {
          const sameTag = [...node.parentElement.children]
            .filter(child => child.tagName === node.tagName);
          if (sameTag.length > 1) part += `:nth-of-type(${sameTag.indexOf(node) + 1})`;
        }
        parts.unshift(part);
        node = node.parentElement;
      }
      return parts.join(" > ");
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
    const nameFor = (element) => {
      const labelledBy = element.getAttribute("aria-labelledby");
      const labelText = labelledBy
        ? labelledBy.split(/\\s+/).map(id => document.getElementById(id)?.innerText || "").join(" ")
        : "";
      const labels = element.labels
        ? [...element.labels].map(label => label.innerText || "").join(" ")
        : "";
      const value = element.getAttribute("aria-label") || labelText ||
        labels || element.getAttribute("alt") || element.getAttribute("title") ||
        (element.matches("a,button,summary,[role=button],[role=link]")
          ? element.innerText : "");
      return value ? value.replace(/\\s+/g, " ").trim().slice(0, 120) : null;
    };
    const indicatorStylesFor = (element) => {
      const style = getComputedStyle(element);
      return {
        outlineStyle: style.outlineStyle,
        outlineWidth: style.outlineWidth,
        outlineColor: style.outlineColor,
        boxShadow: style.boxShadow,
        borderColor: style.borderColor
      };
    };
    const roleFor = (element) => {
      if (element.getAttribute("role")) return element.getAttribute("role");
      const tag = element.tagName.toLowerCase();
      if (tag === "a" && element.hasAttribute("href")) return "link";
      if (tag === "button") return "button";
      if (tag === "select") return "combobox";
      if (tag === "textarea") return "textbox";
      if (tag === "input") return ({checkbox:"checkbox",radio:"radio",button:"button",
        submit:"button",reset:"button",range:"slider"}[element.type] || "textbox");
      return null;
    };
    const query = [
      "a[href]", "area[href]", "button", "input:not([type=hidden])",
      "select", "textarea", "iframe", "summary",
      "[contenteditable]:not([contenteditable=false])",
      "audio[controls]", "video[controls]", "[tabindex]"
    ].join(",");
    const rawCandidates = [...document.querySelectorAll(query)]
      .filter(element => visible(element) && !element.matches(":disabled"))
    const allCandidates = rawCandidates.slice(0, __MAX_CANDIDATES__);
    const radioGroups = new Map();
    for (const radio of document.querySelectorAll('input[type="radio"]')) {
      if (!visible(radio) || radio.disabled) continue;
      if (!radio.name) continue;
      const key = `${radio.form ? selectorFor(radio.form) : "document"}:${radio.name}`;
      if (!radioGroups.has(key)) radioGroups.set(key, []);
      radioGroups.get(key).push(radio);
    }
    const candidates = allCandidates.map(element => {
      const selector = selectorFor(element);
      const radioKey = element.type === "radio" && element.name
        ? `${element.form ? selectorFor(element.form) : "document"}:${element.name}`
        : null;
      const radioGroup = radioKey ? radioGroups.get(radioKey) || [] : [];
      const selectedRadio = radioGroup.find(radio => radio.checked) || radioGroup[0];
      return {
        selector,
        tagName: element.tagName.toLowerCase(),
        role: roleFor(element),
        accessibleName: nameFor(element),
        tabIndex: element.tabIndex,
        expectedInSequentialNavigation: element.tabIndex >= 0 &&
          (element.type !== "radio" || radioGroup.length < 2 || element === selectedRadio),
        radioGroupSize: radioGroup.length,
        radioGroupTabStop: element.type === "radio" && radioGroup.length > 1
          ? selectorFor(selectedRadio) : null,
        baselineStyles: baselineStylesBySelector[selector] || indicatorStylesFor(element)
      };
    });
    const shadowRootHosts = [...document.querySelectorAll("*")]
      .filter(element => element.shadowRoot)
      .map(selectorFor)
      .slice(0, 50);
    const frameCount = document.querySelectorAll("iframe,frame").length;
    const positiveTabindex = candidates
      .filter(candidate => candidate.tabIndex > 0)
      .map(candidate => candidate.selector);
    const active = document.activeElement;
    if (document.documentElement.getAttribute("data-webable-keyboard-audit") === "unsafe") {
      return {
        unsafeReason: "The page explicitly opted out of keyboard interaction testing.",
        candidates,
        candidatesTruncated: rawCandidates.length > __MAX_CANDIDATES__,
        shadowRootHosts,
        frameCount,
        positiveTabindex,
        active: null
      };
    }
    if (!active || active === document.body || active === document.documentElement) {
      return {
        candidates,
        candidatesTruncated: rawCandidates.length > __MAX_CANDIDATES__,
        shadowRootHosts,
        frameCount,
        positiveTabindex,
        active: null
      };
    }
    const rect = active.getBoundingClientRect();
    const width = Math.max(0, rect.width);
    const height = Math.max(0, rect.height);
    const targetRect = {
      left: rect.left, top: rect.top, right: rect.right, bottom: rect.bottom,
      width: rect.width, height: rect.height
    };
    const viewport = {
      width: window.innerWidth, height: window.innerHeight
    };
    const insideViewport = rect.left >= 0 && rect.top >= 0 &&
      rect.right <= window.innerWidth && rect.bottom <= window.innerHeight;
    const ratios = [0.1, 0.3, 0.5, 0.7, 0.9];
    const points = [];
    for (const xRatio of ratios) {
      for (const yRatio of ratios) {
        const x = rect.left + width * xRatio;
        const y = rect.top + height * yRatio;
        if (x >= 0 && y >= 0 && x < window.innerWidth && y < window.innerHeight) {
          points.push([x, y]);
        }
      }
    }
    const samples = points.map(([x, y]) => {
      const hit = document.elementFromPoint(x, y);
      const covered = Boolean(hit && hit !== active && !active.contains(hit));
      const chain = [];
      let node = hit;
      while (node && node !== document.documentElement) {
        const style = getComputedStyle(node);
        const bounds = node.getBoundingClientRect();
        const layered = style.position === "fixed" || style.position === "sticky" ||
          style.zIndex !== "auto" || node.matches("dialog:modal");
        const coversTarget = bounds.left <= rect.left && bounds.top <= rect.top &&
          bounds.right >= rect.right && bounds.bottom >= rect.bottom;
        if (layered && coversTarget) chain.push(node);
        node = node.parentElement;
      }
      return {x, y, hit, covered, chain};
    });
    const occluders = samples.filter(sample => sample.covered);
    const occludingElements = new Map();
    for (const sample of occluders) {
      const hit = sample.hit;
      const selector = selectorFor(hit);
      if (!occludingElements.has(selector)) {
        const style = getComputedStyle(hit);
        const bounds = hit.getBoundingClientRect();
        occludingElements.set(selector, {
          selector,
          tagName: hit.tagName.toLowerCase(),
          role: hit.getAttribute("role"),
          position: style.position,
          zIndex: style.zIndex,
          opacity: style.opacity,
          backgroundColor: style.backgroundColor,
          targetHitSamples: 0,
          rect: {
            left: bounds.left, top: bounds.top, right: bounds.right,
            bottom: bounds.bottom, width: bounds.width, height: bounds.height
          }
        });
      }
      occludingElements.get(selector).targetHitSamples += 1;
    }
    const fullCoverCandidates = new Map(
      samples.length > 0
        ? samples[0].chain.map(node => [selectorFor(node), node])
        : []
    );
    for (const sample of samples.slice(1)) {
      const selectors = new Set(sample.chain.map(selectorFor));
      for (const selector of [...fullCoverCandidates.keys()]) {
        if (!selectors.has(selector)) fullCoverCandidates.delete(selector);
      }
    }
    const coveringElements = [...fullCoverCandidates.values()].map(candidate => {
      const style = getComputedStyle(candidate);
      const bounds = candidate.getBoundingClientRect();
      const color = style.backgroundColor;
      const alphaMatch = color.match(/rgba?\\([^)]*[,/]\\s*([\\d.]+)\\s*\\)$/);
      const backgroundAlpha = color.startsWith("rgb(") ? 1 :
        alphaMatch ? Number(alphaMatch[1]) : 0;
      let effectiveOpacity = 1;
      let ancestor = candidate;
      while (ancestor) {
        effectiveOpacity *= Number(getComputedStyle(ancestor).opacity);
        ancestor = ancestor.parentElement;
      }
      const candidateSelector = selectorFor(candidate);
      const hitSamples = samples.filter(sample =>
        sample.chain.some(node => selectorFor(node) === candidateSelector)
      ).length;
      return {
        selector: candidateSelector,
        tagName: candidate.tagName.toLowerCase(),
        role: candidate.getAttribute("role"),
        position: style.position,
        zIndex: style.zIndex,
        opacity: effectiveOpacity,
        backgroundColor: color,
        backgroundAlpha,
        clipPath: style.clipPath,
        maskImage: style.maskImage,
        coversTarget: bounds.left <= rect.left && bounds.top <= rect.top &&
          bounds.right >= rect.right && bounds.bottom >= rect.bottom,
        targetHitSamples: hitSamples,
        totalTargetSamples: samples.length,
        rect: {
          left: bounds.left, top: bounds.top, right: bounds.right,
          bottom: bounds.bottom, width: bounds.width, height: bounds.height
        }
      };
    }).filter(Boolean);
    const opaqueFullCover = coveringElements.find(element =>
      element.coversTarget &&
      element.targetHitSamples === samples.length &&
      element.backgroundAlpha === 1 &&
      element.opacity === 1 &&
      element.clipPath === "none" &&
      element.maskImage === "none"
    );
    const allSamplesCovered = points.length > 0 && occluders.length === points.length;
    const styles = indicatorStylesFor(active);
    const candidate = candidates.find(item => item.selector === selectorFor(active));
    const outlineChanged = candidate &&
      (styles.outlineStyle !== candidate.baselineStyles.outlineStyle ||
       styles.outlineWidth !== candidate.baselineStyles.outlineWidth ||
       styles.outlineColor !== candidate.baselineStyles.outlineColor);
    const shadowChanged = candidate &&
      styles.boxShadow !== candidate.baselineStyles.boxShadow;
    const borderChanged = candidate &&
      styles.borderColor !== candidate.baselineStyles.borderColor;
    const outlinePresent = styles.outlineStyle !== "none" &&
      parseFloat(styles.outlineWidth) > 0;
    const shadowPresent = styles.boxShadow !== "none";
    const borderPresent = borderChanged &&
      styles.borderColor !== candidate?.baselineStyles?.borderColor;
    const indicatorDetected = Boolean(outlinePresent || shadowPresent ||
      outlineChanged || shadowChanged || borderPresent);
    return {
      candidates,
      candidatesTruncated: rawCandidates.length > __MAX_CANDIDATES__,
      shadowRootHosts,
      frameCount,
      positiveTabindex,
      active: {
        selector: selectorFor(active),
        tagName: active.tagName.toLowerCase(),
        role: roleFor(active),
        accessibleName: nameFor(active),
        focusVisiblePseudoClass: active.matches(":focus-visible"),
        focusIndicatorDetected: indicatorDetected,
        focusIndicatorEvidence: styles,
        focusIndicatorUncertain: !indicatorDetected,
        obscured: allSamplesCovered,
        partiallyOccluded: occluders.length > 0 && occluders.length < points.length,
        occlusionEvaluated: points.length > 0,
        occludingSelector: occluders.length ? selectorFor(occluders[0].hit) : null,
        targetRect,
        viewport,
        insideViewport,
        occludingEvidence: [...occludingElements.values()],
        coveringEvidence: coveringElements,
        occlusionStatus: opaqueFullCover && insideViewport
          ? "confirmed_failure"
          : occluders.length
            ? "potential_issue"
            : insideViewport && points.length > 0
              ? "no_issue_detected"
              : "not_evaluated"
      }
    };
}"""


def _snapshot_expression() -> str:
    return _SNAPSHOT.replace("__MAX_CANDIDATES__", str(MAX_CANDIDATES))


def _check(
    check_id: str,
    criteria: list[str],
    status: KeyboardCheckStatus,
    summary: str,
    evidence: list[dict] | None = None,
) -> KeyboardCheck:
    return KeyboardCheck(
        check_id=check_id,
        criterion_ids=criteria,
        status=status,
        summary=summary,
        evidence=evidence or [],
    )


async def audit_keyboard_focus(page: KeyboardPage) -> KeyboardFocusAuditResult:
    try:
        return await asyncio.wait_for(
            _audit_keyboard_focus(page), timeout=AUDIT_TIMEOUT_SECONDS
        )
    except TimeoutError:
        return _error_result("Keyboard audit exceeded its overall time limit.")


async def _audit_keyboard_focus(page: KeyboardPage) -> KeyboardFocusAuditResult:
    """Observe bounded Tab navigation without activating focused controls.

    The page belongs to a disposable, isolated capture context. Only Tab and
    Shift+Tab are sent. Focus/blur handlers can still have page-defined effects;
    callers must discard the context after capture.
    """
    try:
        initial = await asyncio.wait_for(
            page.evaluate(_snapshot_expression(), {}),
            timeout=ACTION_TIMEOUT_SECONDS,
        )
    except TimeoutError:
        return _error_result("Initial keyboard-audit inspection timed out.")
    except Exception as error:
        return _error_result(
            f"Keyboard-audit inspection failed ({type(error).__name__})."
        )

    if not isinstance(initial, dict):
        return _error_result("Keyboard-audit inspection returned invalid evidence.")
    if initial.get("unsafeReason"):
        return KeyboardFocusAuditResult(
            status="not_tested",
            checks=[
                _check(
                    "sequential_navigation",
                    ["2.1.1", "2.4.3", "2.4.7", "2.4.11"],
                    "not_tested",
                    str(initial["unsafeReason"]),
                ),
                _check(
                    "keyboard_trap",
                    ["2.1.2"],
                    "not_tested",
                    str(initial["unsafeReason"]),
                ),
            ],
            details=[str(initial["unsafeReason"])],
        )

    candidates = initial.get("candidates")
    keyboard = getattr(page, "keyboard", None)
    if not isinstance(candidates, list) or keyboard is None:
        return _error_result("Keyboard input or candidate evidence is unavailable.")
    if not candidates:
        return KeyboardFocusAuditResult(
            status="not_tested",
            checks=[
                _check(
                    "sequential_navigation",
                    ["2.1.1"],
                    "not_tested",
                    "No visible enabled interactive candidates were found to traverse.",
                ),
                _check(
                    "keyboard_trap",
                    ["2.1.2"],
                    "not_tested",
                    "No visible enabled interactive candidates were found to test for a keyboard trap.",
                ),
                _check(
                    "focus_indicator",
                    ["2.4.7"],
                    "not_tested",
                    "No focusable candidate was available for focus-indicator observation.",
                ),
                _check(
                    "focus_obscuration",
                    ["2.4.11"],
                    "not_tested",
                    "No focusable candidate was available for obscuration observation.",
                ),
            ],
            details=["No visible enabled interactive candidates were found."],
        )
    if not callable(getattr(page, "route", None)) or not callable(
        getattr(page, "unroute", None)
    ):
        return KeyboardFocusAuditResult(
            status="not_tested",
            checks=[
                _check(
                    "sequential_navigation",
                    ["2.1.1", "2.4.3", "2.4.7", "2.4.11"],
                    "not_tested",
                    "Keyboard testing was skipped because network side effects could not be blocked.",
                ),
                _check(
                    "keyboard_trap",
                    ["2.1.2"],
                    "not_tested",
                    "Keyboard trap testing was skipped because network side effects could not be blocked.",
                ),
            ],
            details=[
                "Keyboard testing requires temporary network interception; it was skipped because the page cannot safely isolate requests."
            ],
        )

    by_selector = {
        str(candidate["selector"]): candidate
        for candidate in candidates
        if isinstance(candidate, dict) and candidate.get("selector")
    }
    baseline_styles = {
        selector: candidate.get("baselineStyles", {})
        for selector, candidate in by_selector.items()
    }
    candidate_limitations: list[str] = []
    positive_tabindex = initial.get("positiveTabindex", [])
    if positive_tabindex:
        candidate_limitations.append(
            "Positive tabindex candidates were found; the recorded sequence is not "
            "compared with their browser-defined ordering: "
            + ", ".join(str(selector) for selector in positive_tabindex)
        )
    radio_groups = {
        (
            str(candidate.get("radioGroupTabStop")),
            int(candidate.get("radioGroupSize", 0)),
        )
        for candidate in by_selector.values()
        if candidate.get("radioGroupSize", 0) > 1
    }
    for tab_stop, size in sorted(radio_groups):
        candidate_limitations.append(
            f"A {size}-member radio group is treated as one expected sequential "
            f"tab stop ({tab_stop}); individual radio navigation is not evaluated."
        )
    shadow_hosts = initial.get("shadowRootHosts", [])
    if shadow_hosts:
        candidate_limitations.append(
            "Open shadow roots were found; their descendants are outside the "
            "document-level candidate snapshot: "
            + ", ".join(str(selector) for selector in shadow_hosts)
        )
    frame_count = initial.get("frameCount", 0)
    if frame_count:
        candidate_limitations.append(
            f"{frame_count} frame(s) were found; focus inside embedded documents "
            "is not enumerated."
        )
    if initial.get("candidatesTruncated"):
        candidate_limitations.append(
            f"Candidate discovery was capped at {MAX_CANDIDATES} elements."
        )
    sequence: list[KeyboardFocusEvidence] = []
    seen: set[str] = set()
    first_seen_index: dict[str, int] = {}
    late_candidates: list[str] = []
    unexpected_focus_targets: list[str] = []
    tab_actions = 0
    shift_tab_actions = 0
    repeated_active = False
    reverse_stuck = False
    reverse_sequence: list[str] = []
    repeated_selector: str | None = None
    tab_stalled_selector: str | None = None
    tab_cycle_selectors: list[str] = []
    tab_action_limit_reached = False
    timeout_detail: str | None = None
    blocked_requests = 0

    async def block_network(route) -> None:
        nonlocal blocked_requests
        blocked_requests += 1
        await route.abort("blockedbyclient")

    async def press_and_read(key: str) -> dict | None:
        nonlocal tab_actions, shift_tab_actions
        try:
            await asyncio.wait_for(
                keyboard.press(key), timeout=ACTION_TIMEOUT_SECONDS
            )
            if key == "Tab":
                tab_actions += 1
            else:
                shift_tab_actions += 1
            snapshot = await asyncio.wait_for(
                page.evaluate(_snapshot_expression(), baseline_styles),
                timeout=ACTION_TIMEOUT_SECONDS,
            )
        except TimeoutError:
            return None
        if not isinstance(snapshot, dict):
            raise TypeError("Keyboard snapshot returned an invalid structure.")
        for candidate in snapshot.get("candidates", []):
            if not isinstance(candidate, dict) or not candidate.get("selector"):
                continue
            selector = str(candidate["selector"])
            if selector not in by_selector and selector not in late_candidates:
                late_candidates.append(selector)
                candidate_limitations.append(
                    f"Candidate {selector} appeared after the initial snapshot; "
                    "its focusability and traversal position are not assumed."
                )
        return snapshot

    route_installed = False
    interaction_error: str | None = None
    route_cleanup_error: str | None = None
    try:
        await page.route("**/*", block_network)
        route_installed = True
        for index in range(MAX_TAB_ACTIONS):
            snapshot = await press_and_read("Tab")
            if snapshot is None:
                timeout_detail = "Keyboard navigation exceeded the per-action time limit."
                break
            active = snapshot.get("active")
            if not isinstance(active, dict):
                if sequence:
                    repeated_active = True
                break
            selector = str(active.get("selector", ""))
            if not selector:
                break
            if selector in seen:
                repeated_active = True
                repeated_selector = selector
                if sequence and sequence[-1].selector == selector:
                    tab_stalled_selector = selector
                else:
                    tab_cycle_selectors = [
                        item.selector
                        for item in sequence[first_seen_index[selector]:]
                    ]
                break
            seen.add(selector)
            first_seen_index[selector] = len(sequence)
            outside_snapshot = selector not in by_selector
            if outside_snapshot and selector not in unexpected_focus_targets:
                unexpected_focus_targets.append(selector)
                candidate_limitations.append(
                    f"Focused target {selector} was absent from the initial candidate "
                    "snapshot; it may have appeared dynamically or be inside a "
                    "shadow/embedded context."
                )
            sequence.append(
                KeyboardFocusEvidence(
                    selector=selector,
                    tag_name=str(active.get("tagName", "")),
                    accessible_name=active.get("accessibleName"),
                    role=active.get("role"),
                    discovery_status=(
                        "outside_initial_snapshot"
                        if outside_snapshot
                        else "initial_candidate"
                    ),
                    sequence_index=index + 1,
                    focus_indicator_detected=active.get(
                        "focusIndicatorDetected"
                    ),
                    focus_visible_pseudo_class=active.get(
                        "focusVisiblePseudoClass"
                    ),
                    focus_indicator_evidence=active.get(
                        "focusIndicatorEvidence", {}
                    ),
                    obscured=(
                        active.get("obscured")
                        if active.get("occlusionEvaluated")
                        else None
                    ),
                    partially_obscured=bool(active.get("partiallyOccluded")),
                    occluding_selector=active.get("occludingSelector"),
                    target_rect=active.get("targetRect", {}),
                    viewport=active.get("viewport", {}),
                    occlusion_status=active.get(
                        "occlusionStatus", "not_evaluated"
                    ),
                    occluding_evidence=active.get("coveringEvidence", [])
                    + active.get("occludingEvidence", []),
                    details=(
                        (
                            ["Focus indicator could not be evaluated reliably."]
                            if active.get("focusIndicatorUncertain")
                            else []
                        )
                        + (
                            ["Focused target extends outside the viewport; full obscuration cannot be classified."]
                            if not active.get("insideViewport", False)
                            else []
                        )
                    ),
                )
            )
        else:
            tab_action_limit_reached = True
        for _ in range(MAX_SHIFT_TAB_ACTIONS):
            snapshot = await press_and_read("Shift+Tab")
            if snapshot is None:
                timeout_detail = (
                    "Reverse keyboard navigation exceeded the per-action time limit."
                )
                break
            active = snapshot.get("active")
            if not isinstance(active, dict):
                break
            selector = str(active.get("selector", ""))
            if selector:
                reverse_sequence.append(selector)
                if (
                    len(reverse_sequence) > 1
                    and reverse_sequence[-1] == reverse_sequence[-2]
                    and len(by_selector) > 1
                ):
                    reverse_stuck = True
    except Exception as error:
        interaction_error = f"Keyboard interaction failed ({type(error).__name__})."
    finally:
        if route_installed:
            try:
                await page.unroute("**/*", block_network)
            except Exception as error:
                route_cleanup_error = (
                    "Keyboard network isolation could not be removed "
                    f"({type(error).__name__})."
                )

    if route_cleanup_error:
        return _error_result(
            route_cleanup_error,
            tab_actions=tab_actions,
            shift_tab_actions=shift_tab_actions,
        )
    if interaction_error:
        return _error_result(
            interaction_error,
            tab_actions=tab_actions,
            shift_tab_actions=shift_tab_actions,
        )

    if timeout_detail:
        checks = [
            _check(
                "sequential_navigation",
                ["2.1.1"],
                "error",
                timeout_detail,
            ),
            _check(
                "keyboard_trap",
                ["2.1.2"],
                "error",
                "Keyboard trap evidence is incomplete because traversal timed out.",
            ),
            _check(
                "focus_indicator",
                ["2.4.7"],
                "needs_review",
                "Some focus states may not have been observed before the audit timed out.",
            ),
            _check(
                "focus_obscuration",
                ["2.4.11"],
                "needs_review",
                "Focus obscuration could not be fully evaluated before timeout.",
            ),
        ]
    else:
        expected = {
            selector
            for selector, candidate in by_selector.items()
            if candidate.get("expectedInSequentialNavigation")
        }
        omitted = sorted(expected - seen)
        sequence_status: KeyboardCheckStatus = "needs_review"
        if not sequence:
            sequence_status = "not_tested"
            sequence_summary = (
                "No focus target was successfully traversed; sequential navigation "
                "could not be evaluated."
            )
        elif tab_stalled_selector:
            sequence_summary = (
                "Tab remained on the same focus target in the sample; this may "
                "indicate blocked keyboard operation, but does not by itself prove "
                "a keyboard trap."
            )
        elif repeated_active or reverse_stuck:
            sequence_summary = (
                "The sampled sequence revisited a focus target; this may reflect "
                "normal wrapping or application-managed focus and is not by itself "
                "evidence of a keyboard trap."
            )
        elif (
            omitted
            or initial.get("candidatesTruncated")
            or late_candidates
            or unexpected_focus_targets
            or tab_action_limit_reached
        ):
            sequence_summary = (
                "The observed sequence did not include every initially discovered "
                "candidate; radio groups, positive tabindex, shadow DOM, embedded "
                "contexts, dynamic changes, or custom navigation can explain differences."
            )
        else:
            sequence_status = "pass"
            sequence_summary = (
                "The bounded Tab/Shift+Tab sample advanced through the observed focus "
                "targets without a detected repeat. This pass applies only to the "
                "tested sequence; widget operation and undiscovered controls were "
                "not evaluated."
            )
        checks = [
            _check(
                "sequential_navigation",
                ["2.1.1"],
                sequence_status,
                sequence_summary,
                [
                    {
                        "unobserved_candidates": omitted[:MAX_CANDIDATES],
                        "candidate_list_truncated": bool(
                            initial.get("candidatesTruncated")
                        ),
                        "candidate_limitations": candidate_limitations,
                        "late_candidates": late_candidates,
                        "unexpected_focus_targets": unexpected_focus_targets,
                        "shift_tab_sequence": reverse_sequence,
                        "reverse_navigation_stalled": reverse_stuck,
                        "repeated_selector": repeated_selector,
                        "tab_action_limit_reached": tab_action_limit_reached,
                    }
                ],
            ),
            _check(
                "keyboard_trap",
                ["2.1.2"],
                (
                    "not_tested"
                    if not sequence
                    else "needs_review"
                    if tab_stalled_selector or tab_cycle_selectors or reverse_stuck
                    else "pass"
                ),
                (
                    "Focus remained on the same target after both Tab and Shift+Tab; "
                    "this is a possible keyboard trap and requires review of the "
                    "containing widget, dismissal method, and applicable exceptions."
                    if tab_stalled_selector
                    and reverse_sequence
                    and reverse_sequence[0] == tab_stalled_selector
                    else (
                        "A repeated Tab cycle remained within the same sampled focus "
                        "targets during reverse navigation; this may be intentional "
                        "wrapping or a widget-level trap and requires review."
                        if tab_cycle_selectors
                        and reverse_sequence
                        and all(
                            selector in tab_cycle_selectors
                            for selector in reverse_sequence
                        )
                        else (
                            "Tab did not advance from a sampled target, but Shift+Tab "
                            "moved focus; this does not demonstrate a two-direction "
                            "keyboard trap."
                            if tab_stalled_selector and reverse_sequence
                            else (
                                "No same-target Tab stall or repeated focus cycle "
                                "persisting during reverse navigation was observed in "
                                "the tested sequence; undiscovered controls and widget "
                                "behavior were not evaluated."
                            )
                        )
                    )
                ),
                [
                    {
                        "tab_stalled_target": tab_stalled_selector,
                        "repeated_selector": repeated_selector,
                        "tab_cycle_selectors": tab_cycle_selectors,
                        "shift_tab_focus_after_stall": (
                            reverse_sequence[0] if reverse_sequence else None
                        ),
                        "shift_tab_progress_observed": (
                            reverse_sequence[0] != tab_stalled_selector
                            if tab_stalled_selector and reverse_sequence
                            else None
                        ),
                        "shift_tab_stayed_within_tab_cycle": (
                            all(
                                selector in tab_cycle_selectors
                                for selector in reverse_sequence
                            )
                            if tab_cycle_selectors and reverse_sequence
                            else None
                        ),
                        "reverse_navigation_stalled": reverse_stuck,
                        "candidate_limitations": candidate_limitations,
                    }
                ],
            ),
            _check(
                "focus_order",
                ["2.4.3"],
                "needs_review" if len(sequence) > 1 else "not_tested",
                "Tab order was recorded, but whether it preserves meaning and operation "
                "requires contextual review.",
                [
                    {
                        "sequence": [item.selector for item in sequence],
                        "initial_dom_candidate_order_not_expected_tab_order": [
                            selector
                            for selector, candidate in by_selector.items()
                            if candidate.get("expectedInSequentialNavigation")
                        ],
                        "candidate_limitations": candidate_limitations,
                        "late_candidates": late_candidates,
                    }
                ],
            ),
        ]

        indicator_evidence = [
            {
                "selector": item.selector,
                "indicator_detected": item.focus_indicator_detected,
                "focus_visible_pseudo_class": item.focus_visible_pseudo_class,
                "indicator_evidence": item.focus_indicator_evidence,
                "details": item.details,
            }
            for item in sequence
        ]
        if any(item.focus_indicator_detected is False for item in sequence):
            indicator_status: KeyboardCheckStatus = "needs_review"
            indicator_summary = (
                "One or more sampled keyboard focus states had no indicator detected in "
                "the limited CSS properties inspected; other indicator techniques may "
                "not be observable."
            )
        elif sequence and all(
            item.focus_indicator_detected is True for item in sequence
        ):
            indicator_status = "needs_review"
            indicator_summary = (
                "A possible focus style change was detected for each sampled element; "
                "perceptibility, persistence, contrast, and sufficiency need review."
            )
        else:
            indicator_status = "not_tested"
            indicator_summary = "No reliable keyboard focus-indicator observation was available."
        checks.append(
            _check(
                "focus_indicator",
                ["2.4.7"],
                indicator_status,
                indicator_summary,
                indicator_evidence,
            )
        )

        partial = [item for item in sequence if item.obscured is None or item.details]
        confirmed = [
            item for item in sequence
            if item.occlusion_status == "confirmed_failure"
        ]
        potential = [
            item for item in sequence
            if item.occlusion_status == "potential_issue"
        ]
        if confirmed:
            obscuration_status: KeyboardCheckStatus = "fail"
            obscuration_summary = (
                "An opaque, layered element covered the full measured bounds of a "
                "sampled focused component and intercepted all interior hit-test "
                "samples. This is a high-confidence WCAG 2.4.11 failure candidate."
            )
        elif potential:
            obscuration_status = "needs_review"
            obscuration_summary = (
                "Hit-testing found an unrelated element over a sampled focused "
                "component; full visual obscuration could not be confirmed and "
                "manual review is required."
            )
        elif sequence and not partial:
            obscuration_status = "needs_review"
            obscuration_summary = (
                "No complete occlusion was detected at sampled points, but the "
                "component's meaningful visible area and focus indicator were not "
                "evaluated; review is required."
            )
        else:
            obscuration_status = "needs_review"
            obscuration_summary = (
                "The bounded hit-test could not establish whether sampled focus is obscured."
            )
        checks.append(
            _check(
                "focus_obscuration",
                ["2.4.11"],
                obscuration_status,
                obscuration_summary,
                [
                    {
                        "selector": item.selector,
                        "obscured": item.obscured,
                        "occluding_selector": item.occluding_selector,
                        "target_rect": item.target_rect,
                        "viewport": item.viewport,
                        "occlusion_status": item.occlusion_status,
                        "occluding_evidence": item.occluding_evidence,
                    }
                    for item in sequence
                ],
            )
        )

    status: KeyboardAuditStatus = (
        "unavailable"
        if all(check.status == "error" for check in checks)
        else "partial"
    )
    details = [
        "Only Tab and Shift+Tab were sent; controls were not activated.",
        "The capture uses a disposable isolated browser context; it is closed after all audits.",
        "HTTP requests during keyboard interaction are temporarily intercepted and aborted. Other page-defined side effects cannot be fully ruled out.",
        "Tab traversal does not prove operation of every widget, intended focus order, focus indicator sufficiency, or WCAG conformance.",
    ]
    details.extend(candidate_limitations)
    if blocked_requests:
        details.append(
            f"{blocked_requests} network request(s) were blocked during keyboard interaction."
        )
    if timeout_detail:
        details.append(timeout_detail)
    return KeyboardFocusAuditResult(
        status=status,
        checks=checks,
        findings=sequence,
        details=details,
        candidate_limitations=candidate_limitations,
        late_candidates=late_candidates,
        unexpected_focus_targets=unexpected_focus_targets,
        tab_actions=tab_actions,
        shift_tab_actions=shift_tab_actions,
    )


def _error_result(
    detail: str, *, tab_actions: int = 0, shift_tab_actions: int = 0
) -> KeyboardFocusAuditResult:
    checks = [
        _check(
            "sequential_navigation",
            ["2.1.1"],
            "error",
            detail,
        ),
        _check("keyboard_trap", ["2.1.2"], "error", detail),
        _check("focus_order", ["2.4.3"], "error", detail),
        _check("focus_indicator", ["2.4.7"], "error", detail),
        _check("focus_obscuration", ["2.4.11"], "error", detail),
    ]
    return KeyboardFocusAuditResult(
        status="unavailable",
        checks=checks,
        details=[detail],
        tab_actions=tab_actions,
        shift_tab_actions=shift_tab_actions,
    )

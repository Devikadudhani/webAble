from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Protocol
from urllib.parse import urlsplit, urlunsplit


EvidenceSource = Literal["owner_reported", "browser_observed"]
EvaluationStatus = Literal[
    "owner_reported",
    "browser_observed",
    "manual_review_needed",
    "not_evaluated",
]
OwnerAnswerValue = Literal["yes", "no", "not_sure", "not_applicable"]

MAX_CONTEXT_URLS = 20
MAX_JOURNEYS = 20
MAX_ANSWERS = 100
MAX_TEXT_LENGTH = 2_000
MAX_DISCOVERY_CANDIDATES = 1_000
FEATURE_DISCOVERY_TIMEOUT_SECONDS = 3

WCAG_CRITERION_IDS = (
    "1.1.1", "1.2.1", "1.2.2", "1.2.3", "1.2.4", "1.2.5",
    "1.3.1", "1.3.2", "1.3.3", "1.3.4", "1.3.5",
    "1.4.1", "1.4.2", "1.4.3", "1.4.4", "1.4.5",
    "1.4.10", "1.4.11", "1.4.12", "1.4.13",
    "2.1.1", "2.1.2", "2.1.4", "2.2.1", "2.2.2", "2.3.1",
    "2.4.1", "2.4.2", "2.4.3", "2.4.4", "2.4.5", "2.4.6",
    "2.4.7", "2.4.11", "2.5.1", "2.5.2", "2.5.3", "2.5.4",
    "2.5.7", "2.5.8", "3.1.1", "3.1.2", "3.2.1", "3.2.2",
    "3.2.3", "3.2.4", "3.2.6", "3.3.1", "3.3.2", "3.3.3",
    "3.3.4", "3.3.7", "3.3.8", "4.1.2", "4.1.3",
)

_COVERAGE_INVENTORY_PATH = (
    Path(__file__).resolve().parents[2] / "docs" / "wcag-22-coverage-inventory.json"
)
with _COVERAGE_INVENTORY_PATH.open(encoding="utf-8") as inventory_file:
    _coverage_inventory = json.load(inventory_file)
WCAG_CRITERIA_CATALOG = tuple(
    {
        "criterion_id": item["id"],
        "title": item["title"],
        "level": item["level"],
        "principle": item["principle"],
        "intent": item["intent"],
        "coverage_classification": item["coverage_classification"],
        "criterion_url": item["criterion_url"],
        "understanding_url": item["understanding_url"],
    }
    for item in _coverage_inventory["criteria"]
)
if {item["criterion_id"] for item in WCAG_CRITERIA_CATALOG} != set(WCAG_CRITERION_IDS):
    raise RuntimeError("WCAG coverage inventory must match the 55 in-scope A/AA criteria.")
_CRITERION_METADATA = {
    item["criterion_id"]: item for item in WCAG_CRITERIA_CATALOG
}

FEATURE_IDS = (
    "prerecorded_media",
    "live_media",
    "forms",
    "authentication",
    "time_limits",
    "moving_content",
    "custom_widgets",
    "pointer_gestures",
    "dragging",
    "motion_controls",
    "transactions",
    "multiple_pages",
    "alternate_languages",
    "color_coded_content",
    "text_in_images",
    "two_dimensional_content",
    "structured_content",
)
FEATURE_LABELS = {
    "prerecorded_media": "Prerecorded audio or video",
    "live_media": "Live audio or video",
    "forms": "Forms and data entry",
    "authentication": "Sign-in or authentication",
    "time_limits": "Timed tasks, sessions, or content",
    "moving_content": "Moving, flashing, or auto-updating content",
    "custom_widgets": "Custom interactive widgets or status updates",
    "pointer_gestures": "Multi-point or path-based pointer gestures",
    "dragging": "Dragging interactions",
    "motion_controls": "Device-motion or gesture-triggered features",
    "transactions": "Legal, financial, or user-data transactions",
    "multiple_pages": "A multi-page website with repeated navigation or help",
    "alternate_languages": "Pages or passages in multiple languages",
    "color_coded_content": "Color used to convey status or meaning",
    "text_in_images": "Images or graphics containing text",
    "two_dimensional_content": "Tables, maps, diagrams, or other two-dimensional content",
    "structured_content": "Structured content, headings, or reading order",
}

FEATURE_CRITERIA: dict[str, tuple[str, ...]] = {
    "prerecorded_media": ("1.2.1", "1.2.2", "1.2.3", "1.2.5", "1.4.2"),
    "live_media": ("1.2.4", "1.4.2"),
    "forms": ("1.3.3", "1.3.5", "2.4.6", "2.5.3", "2.5.8", "3.2.2", "3.3.1", "3.3.2", "3.3.3", "3.3.7"),
    "authentication": ("3.3.8",),
    "time_limits": ("2.2.1",),
    "moving_content": ("2.2.2", "2.3.1"),
    "custom_widgets": ("1.3.1", "1.3.3", "1.4.13", "2.1.1", "2.1.2", "2.1.4", "2.4.3", "2.4.6", "2.4.7", "2.4.11", "2.5.3", "2.5.8", "3.2.1", "3.2.2", "4.1.2", "4.1.3"),
    "pointer_gestures": ("2.5.1", "2.5.2"),
    "dragging": ("2.5.7",),
    "motion_controls": ("2.5.4",),
    "transactions": ("3.3.4", "3.3.7", "3.3.8"),
    "multiple_pages": ("2.4.1", "2.4.2", "2.4.4", "2.4.5", "3.2.3", "3.2.4", "3.2.6"),
    "alternate_languages": ("3.1.1", "3.1.2"),
    "color_coded_content": ("1.4.1", "1.4.3", "1.4.11"),
    "text_in_images": ("1.1.1", "1.4.5"),
    "two_dimensional_content": ("1.3.2", "1.4.10"),
    "structured_content": ("1.3.2", "1.3.4", "1.4.4", "1.4.12", "2.4.2", "2.4.6"),
}


@dataclass(frozen=True)
class QuestionnaireQuestion:
    question_id: str
    criterion_ids: tuple[str, ...]
    feature_id: str | None
    prompt: str
    answer_options: tuple[OwnerAnswerValue, ...] = (
        "yes", "no", "not_sure", "not_applicable"
    )
    helper_text: str = (
        "This is contextual information, not evidence of WCAG conformance. "
        "Do not enter passwords, personal data, customer data, or secrets."
    )


@dataclass(frozen=True)
class OwnerAnswer:
    question_id: str
    answer: OwnerAnswerValue
    explanation: str | None = None
    page_urls: tuple[str, ...] = ()


@dataclass(frozen=True)
class BrowserFeatureEvidence:
    feature_id: str
    detected: bool
    count: int
    viewport: str
    evidence: tuple[str, ...] = ()


@dataclass(frozen=True)
class BrowserCriterionEvidence:
    criterion_id: str
    analyzer_id: str
    result_status: str
    viewport: str
    summary: str
    evidence_count: int = 0


@dataclass(frozen=True)
class BrowserFeatureDiscovery:
    status: Literal["available", "partial", "unavailable", "not_attempted"]
    features: tuple[BrowserFeatureEvidence, ...] = ()
    details: tuple[str, ...] = ()


class FeatureDiscoveryPage(Protocol):
    async def evaluate(self, expression: str, argument: int) -> object:
        ...


QUESTIONNAIRE_QUESTIONS = (
    QuestionnaireQuestion(
        "media.prerecorded_alternatives",
        ("1.2.1",),
        "prerecorded_media",
        "For prerecorded audio-only items, is an equivalent transcript or text alternative available? For prerecorded video-only items, is an equivalent text or audio alternative available? Identify representative public pages and any exceptions.",
    ),
    QuestionnaireQuestion(
        "media.prerecorded_audio_description_or_alternative",
        ("1.2.3",),
        "prerecorded_media",
        "For prerecorded synchronized video, is important visual information that is absent from the soundtrack described in audio description or a complete text alternative? Identify representative videos and exceptions.",
    ),
    QuestionnaireQuestion(
        "media.live_captions",
        ("1.2.4",),
        "live_media",
        "For live synchronized audio and video, are synchronized captions provided during the live presentation? Identify the public page or event and any scheduled/live exceptions.",
    ),
    QuestionnaireQuestion(
        "media.prerecorded_captions",
        ("1.2.2",),
        "prerecorded_media",
        "For prerecorded synchronized audio/video, do captions include the spoken dialogue and meaningful sounds? Identify representative media and where captions can be enabled.",
    ),
    QuestionnaireQuestion(
        "media.prerecorded_audio_description",
        ("1.2.5",),
        "prerecorded_media",
        "For prerecorded video with meaningful visual information missing from its soundtrack, is audio description available? Identify representative videos and any exceptions.",
    ),
    QuestionnaireQuestion(
        "media.audio_control",
        ("1.4.2",),
        "prerecorded_media",
        "Does any audio play automatically for more than three seconds, and where can users pause, stop, or control its volume?",
    ),
    QuestionnaireQuestion(
        "forms.field_purpose",
        ("1.3.5",),
        "forms",
        "Which form fields collect personal information or need special instructions? Identify the relevant page and purpose only; do not provide actual personal data.",
    ),
    QuestionnaireQuestion(
        "forms.labels_and_instructions",
        ("3.3.2",),
        "forms",
        "Before users enter data, does each form control have a visible or programmatically available label and any instructions needed to complete it? Identify unclear fields and pages.",
    ),
    QuestionnaireQuestion(
        "forms.error_identification",
        ("3.3.1",),
        "forms",
        "When a form submission has an error, does text identify the affected field and describe the error? Identify representative form flows, error states and any exceptions.",
    ),
    QuestionnaireQuestion(
        "forms.error_suggestions",
        ("3.3.3",),
        "forms",
        "When a form error has a known correction, does the message suggest how to fix it without creating a security risk? Identify examples, pages and any exceptions.",
    ),
    QuestionnaireQuestion(
        "forms.repeated_entry",
        ("3.3.7",),
        "forms",
        "Does a multi-step process ask users to re-enter information already supplied in that process? If so, where and why?",
    ),
    QuestionnaireQuestion(
        "authentication.cognitive_steps",
        ("3.3.8",),
        "authentication",
        "Can users complete each authentication step without a cognitive function test (such as memorizing or transcribing a code), or use a permitted accessible alternative? Do not share credentials.",
    ),
    QuestionnaireQuestion(
        "timing.adjustment",
        ("2.2.1",),
        "time_limits",
        "Which user flows have time limits, and how can users turn them off, adjust them, or request more time?",
    ),
    QuestionnaireQuestion(
        "motion.pause_and_flash",
        ("2.2.2",),
        "moving_content",
        "Which content moves, scrolls, or updates automatically for more than five seconds, and where can users pause, stop, or hide it? Identify relevant pages and exceptions.",
    ),
    QuestionnaireQuestion(
        "motion.flash_threshold",
        ("2.3.1",),
        "moving_content",
        "Does any content flash more than three times in one second, or exceed the general- or red-flash thresholds? Identify videos/animations and any measured review results.",
    ),
    QuestionnaireQuestion(
        "widgets.keyboard_operation",
        ("1.3.1", "2.1.1", "2.1.2", "2.4.3", "2.4.7"),
        "custom_widgets",
        "Which custom widgets are important to the main tasks? For each, describe the keyboard operation, expected focus order, visible focus indicator and how users exit the widget.",
    ),
    QuestionnaireQuestion(
        "widgets.status_messages",
        ("4.1.3",),
        "custom_widgets",
        "Are status messages (such as saved, submitted, loading, result, or error updates) programmatically exposed to assistive technology without requiring focus to move? Identify relevant pages and examples.",
    ),
    QuestionnaireQuestion(
        "widgets.accessible_name_role_state",
        ("4.1.2",),
        "custom_widgets",
        "For each custom control, are its accessible name, role, and current state available to assistive technology and updated when it changes? Identify controls and relevant states.",
    ),
    QuestionnaireQuestion(
        "widgets.hover_focus_content",
        ("1.4.13",),
        "custom_widgets",
        "When additional content appears on hover or focus, can users dismiss it without moving focus, move the pointer onto it, and keep it visible while relevant? Identify examples.",
    ),
    QuestionnaireQuestion(
        "widgets.focus_not_obscured",
        ("2.4.11",),
        "custom_widgets",
        "Can sticky headers, dialogs, banners, or other author content fully cover a keyboard-focused control? Identify likely overlays and affected pages.",
    ),
    QuestionnaireQuestion(
        "widgets.label_in_accessible_name",
        ("2.5.3",),
        "custom_widgets",
        "For controls with visible text labels, does the accessible name include that visible wording so speech-input users can address the control? Identify mismatches.",
    ),
    QuestionnaireQuestion(
        "widgets.target_size_exceptions",
        ("2.5.8",),
        "custom_widgets",
        "Are any small controls essential, equivalent, inline, or within a qualifying spacing arrangement? Identify the controls and exception rationale; browser measurements do not decide exceptions.",
    ),
    QuestionnaireQuestion(
        "content.orientation",
        ("1.3.4",),
        "structured_content",
        "Does any page or task require a particular screen orientation? If so, is that restriction essential, and which content or function is affected when orientation changes?",
    ),
    QuestionnaireQuestion(
        "content.text_resize",
        ("1.4.4",),
        "structured_content",
        "At 200% text enlargement or browser zoom, which pages or controls are most important to review for lost content or functionality? Note any exceptions and representative URLs.",
    ),
    QuestionnaireQuestion(
        "content.text_spacing",
        ("1.4.12",),
        "structured_content",
        "When users increase line, paragraph, letter, and word spacing, which pages or components may clip, overlap, or hide content? Identify representative pages and exceptions.",
    ),
    QuestionnaireQuestion(
        "pages.bypass_repeated_blocks",
        ("2.4.1",),
        "multiple_pages",
        "Across pages with repeated content blocks, what mechanism lets keyboard users skip to the main content or bypass those blocks? Identify pages where it may be missing.",
    ),
    QuestionnaireQuestion(
        "pages.descriptive_titles",
        ("2.4.2",),
        "structured_content",
        "Do representative pages have unique titles that identify their topic or purpose? Identify pages with missing, repeated, or vague titles.",
    ),
    QuestionnaireQuestion(
        "pages.link_purpose",
        ("2.4.4",),
        "multiple_pages",
        "For links with generic text such as 'more' or 'read more', does surrounding programmatically associated context make each destination clear? Identify representative links and pages.",
    ),
    QuestionnaireQuestion(
        "controls.target_size_context",
        ("2.5.8",),
        "forms",
        "Which frequently used form controls or actions are difficult to activate on touch screens? Identify any small-target exceptions or adjacent spacing that should be reviewed.",
    ),
    QuestionnaireQuestion(
        "content.meaningful_sequence",
        ("1.3.2",),
        "structured_content",
        "On which pages does visual order convey a meaningful reading or task sequence (for example, multi-column content, product details, or steps)? Does the DOM and reading order preserve that sequence at other viewports?",
    ),
    QuestionnaireQuestion(
        "forms.sensory_instructions",
        ("1.3.3",),
        "forms",
        "Do instructions for forms or tasks identify controls by more than their shape, size, location, or color? Which pages or steps should be reviewed?",
    ),
    QuestionnaireQuestion(
        "keyboard.character_shortcuts",
        ("2.1.4",),
        "custom_widgets",
        "If the site has single-character keyboard shortcuts, can users turn them off, remap them to include a non-printable key, or limit them to the relevant component while it has focus?",
    ),
    QuestionnaireQuestion(
        "content.headings_and_labels",
        ("2.4.6",),
        "structured_content",
        "On representative pages, do headings describe their section topic and do labels describe each control's purpose? Identify unclear examples and the relevant public pages.",
    ),
    QuestionnaireQuestion(
        "content.sensory_instructions",
        ("1.3.3",),
        "forms",
        "Do form or task instructions identify controls using more than shape, size, location, sound, or color alone? Identify examples, pages and alternate cues.",
    ),
    QuestionnaireQuestion(
        "widgets.sensory_instructions",
        ("1.3.3",),
        "custom_widgets",
        "Do instructions for custom interactions identify controls or actions using more than shape, location, sound, or color alone? Identify examples, pages and alternate cues.",
    ),
    QuestionnaireQuestion(
        "widgets.no_unexpected_change_on_focus",
        ("3.2.1",),
        "custom_widgets",
        "When a custom component receives keyboard focus, does it avoid unexpectedly changing page, opening a new window, moving focus, or submitting a form? Identify components and pages.",
    ),
    QuestionnaireQuestion(
        "forms.no_unexpected_change_on_input",
        ("3.2.2",),
        "forms",
        "When users change a form control, does the page avoid unexpectedly navigating or submitting? If a change of context occurs, are users told beforehand? Identify controls and pages.",
    ),
    QuestionnaireQuestion(
        "pointer.gesture_alternative",
        ("2.5.1",),
        "pointer_gestures",
        "Can every task that uses a multipoint or path-based pointer gesture (such as pinch or a drawn path) also be completed with a single pointer? Identify any task without an alternative.",
    ),
    QuestionnaireQuestion(
        "pointer.cancellation",
        ("2.5.2",),
        "pointer_gestures",
        "For pointer actions, do users avoid accidental activation by triggering on release, cancelling before release, undoing after release, or using another permitted safeguard? Identify key controls and flows.",
    ),
    QuestionnaireQuestion(
        "dragging.alternative",
        ("2.5.7",),
        "dragging",
        "Which tasks use dragging, and what single-pointer alternative is available?",
    ),
    QuestionnaireQuestion(
        "motion.actuation_alternative",
        ("2.5.4",),
        "motion_controls",
        "For each feature activated by device motion or user movement, can users perform the same action with an on-screen control and disable motion activation? Identify any exceptions.",
    ),
    QuestionnaireQuestion(
        "transactions.error_prevention",
        ("3.3.4",),
        "transactions",
        "Before legal, financial, or user-data submissions, can users review and correct the information, reverse the action, or confirm it? Identify transaction pages and applicable exceptions.",
    ),
    QuestionnaireQuestion(
        "pages.multiple_ways_to_find",
        ("2.4.5",),
        "multiple_pages",
        "For pages in this site, are there at least two ways to locate them (such as navigation, search, or a site map), subject to the criterion's exceptions? Identify any pages or exceptions.",
    ),
    QuestionnaireQuestion(
        "pages.consistent_navigation_order",
        ("3.2.3",),
        "multiple_pages",
        "Across pages with repeated navigation, does its relative order remain consistent unless the user changes it? Identify representative page pairs and exceptions.",
    ),
    QuestionnaireQuestion(
        "pages.consistent_identification",
        ("3.2.4",),
        "multiple_pages",
        "Are components that perform the same function identified consistently across pages? Identify examples where labels, names, or alternatives differ.",
    ),
    QuestionnaireQuestion(
        "pages.consistent_help_location",
        ("3.2.6",),
        "multiple_pages",
        "Where the site provides contact, help, self-help, or human-contact mechanisms, do repeated mechanisms appear in a consistent relative order across pages? Identify examples or exceptions.",
    ),
    QuestionnaireQuestion(
        "language.parts",
        ("3.1.1", "3.1.2"),
        "alternate_languages",
        "Which pages or passages use a language other than the site's default language?",
    ),
    QuestionnaireQuestion(
        "visual.color_and_contrast",
        ("1.4.1", "1.4.3", "1.4.11"),
        "color_coded_content",
        "Where does color convey status, meaning, or control state, and what additional visual cues are intended?",
    ),
    QuestionnaireQuestion(
        "visual.images_of_text",
        ("1.1.1", "1.4.5"),
        "text_in_images",
        "Is text presented as real text rather than images of text, except for logos, essential presentations, or customizable presentations? Identify any images of text and exceptions.",
    ),
    QuestionnaireQuestion(
        "layout.two_dimensional_content",
        ("1.3.2", "1.4.10"),
        "two_dimensional_content",
        "Which tables, maps, diagrams, or other regions require two-dimensional presentation, and why is that presentation essential?",
    ),
)

INITIAL_QUESTIONS = (
    QuestionnaireQuestion(
        "scope.representative_pages",
        (),
        None,
        "Which additional page URLs are representative of this site? Provide public URLs only; do not include query strings, fragments, credentials, or private access tokens.",
    ),
    QuestionnaireQuestion(
        "scope.user_journeys",
        (),
        None,
        "Which user journeys should be considered, and which public pages are involved? Do not include account details or customer data.",
    ),
    QuestionnaireQuestion(
        "scope.features",
        (),
        None,
        "Which features are present? Select all that apply; browser discovery may reveal additional features.",
    ),
)

_DISCOVERY_FOLLOWUP_PROMPTS = {
    "prerecorded_media": "The browser found audio/video media although it may not know whether it is prerecorded. Is prerecorded media in scope? Identify a representative public page or explain why the candidate is not relevant.",
    "live_media": "The browser found a possible live-media feature. Is live synchronized audio/video actually offered? Identify the public page/event or explain why the candidate is not live media.",
    "forms": "The browser found a form candidate. Is it an intended user form or transaction? Identify its public page and purpose, or explain why it is not in scope.",
    "authentication": "The browser found a password field although sign-in was reported absent. Is this part of an authentication flow? Identify the public page or explain the field's purpose without sharing credentials.",
    "time_limits": "The browser found a possible timeout, refresh, or time-limit signal. Which user flow is affected, and how can users disable, adjust, extend, or avoid the limit?",
    "moving_content": "The browser found an animation or moving-content candidate. Is it meaningful moving, flashing, scrolling, or auto-updating content? Identify controls, timing, and any exception.",
    "custom_widgets": "The browser found a custom role, tabindex, or widget candidate. Which interactive component is intended, and how should it behave for keyboard and assistive-technology users?",
    "pointer_gestures": "The browser found a possible gesture-controlled component. Does it require multipoint or path-based input? Identify its single-pointer alternative and cancellation behavior.",
    "dragging": "The browser found a draggable or grab-style control. Is dragging required for a task? Identify the control and its single-pointer alternative.",
    "motion_controls": "The browser found a possible motion-triggered control. Does a task use device motion or movement? Identify its on-screen alternative and how to disable motion activation.",
    "transactions": "The browser found possible payment, checkout, or data-submission controls. Does this flow create a legal commitment, financial transaction, or change/delete user data? Identify the public flow and safeguards.",
    "multiple_pages": "The browser found multiple same-site navigation destinations. Is this a multi-page site or process? Identify representative pages and navigation/help mechanisms.",
    "alternate_languages": "The browser found a language-marked passage that differs from the page language. Is it a genuine language change? Identify the text and page, or explain the markup.",
    "color_coded_content": "The browser found status, alert, or state indicators. Does color convey meaning or identify a component? Describe the other visual cue and the relevant page.",
    "text_in_images": "The browser found image or graphic candidates. Which contain meaningful text or information, and what text alternative should convey their purpose? Identify pages.",
    "two_dimensional_content": "The browser found a table, grid, canvas, map, or horizontally scrollable region. Is two-dimensional presentation essential, or can the content reflow? Identify the region and page.",
    "structured_content": "The browser found headings or structured content. Which pages have meaningful reading order or headings/labels to review? Identify representative pages and any layout-dependent order.",
}
DISCOVERY_FOLLOWUP_QUESTIONS = tuple(
    QuestionnaireQuestion(
        question_id=f"discovery.{feature_id}",
        criterion_ids=FEATURE_CRITERIA[feature_id],
        feature_id=feature_id,
        prompt=prompt,
    )
    for feature_id, prompt in _DISCOVERY_FOLLOWUP_PROMPTS.items()
)
_DISCOVERY_QUESTION_BY_FEATURE = {
    question.feature_id: question for question in DISCOVERY_FOLLOWUP_QUESTIONS
}
_QUESTION_BY_ID = {
    question.question_id: question
    for question in (
        *INITIAL_QUESTIONS,
        *QUESTIONNAIRE_QUESTIONS,
        *DISCOVERY_FOLLOWUP_QUESTIONS,
    )
}
_SENSITIVE_TEXT_PATTERNS = (
    re.compile(r"(?i)\b(?:password|passcode|api[_ -]?key|access[_ -]?token|secret)\s*[:=]"),
    re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE),
    re.compile(r"\b(?:ghp_[A-Za-z0-9]{20,}|AKIA[A-Z0-9]{16})\b"),
)


_DISCOVER_FEATURES = """(maxCandidates) => {
  const all = selector => document.querySelectorAll(selector);
  const first = selector => Array.from(all(selector)).slice(0, maxCandidates);
  const wasTruncated = selector => all(selector).length > maxCandidates;
  const visible = element => {
    const style = getComputedStyle(element);
    const rect = element.getBoundingClientRect();
    return rect.width > 0 && rect.height > 0 &&
      style.display !== "none" && style.visibility !== "hidden" &&
      style.visibility !== "collapse" && Number(style.opacity) !== 0 &&
      !element.closest("[hidden],[inert]");
  };
  const media = first("video,audio").filter(visible);
  const visibleText = (element) =>
    `${element.innerText || ""} ${element.getAttribute("aria-label") || ""} ${element.title || ""}`.toLowerCase();
  const liveMedia = media.filter(element =>
    Boolean(element.srcObject) || element.hasAttribute("data-live") ||
    /\\b(live|livestream|streaming)\\b/.test(visibleText(element))
  );
  const statusCandidates = first("[role=status],[role=alert],[aria-current],[aria-invalid],[class*=status i],[class*=badge i]").filter(visible);
  const transactionCandidates = first("input,button,a,[role=button]").filter(visible).filter(element => {
    const autocomplete = (element.getAttribute("autocomplete") || "").toLowerCase();
    return /cc-number|cc-exp|cc-csc|transaction-amount/.test(autocomplete) ||
      /\\b(check ?out|place order|pay now|purchase|donate|submit payment)\\b/.test(visibleText(element));
  });
  const sameSitePaths = new Set(first("a[href]").filter(visible).flatMap(element => {
    try {
      const url = new URL(element.href, location.href);
      return url.origin === location.origin ? [url.pathname] : [];
    } catch (_) { return []; }
  }));
  const scrollableRegions = first("body *").filter(element => {
    if (!visible(element)) return false;
    const style = getComputedStyle(element);
    return /(auto|scroll)/.test(style.overflowX) && element.scrollWidth > element.clientWidth + 2;
  });
  const features = {
    prerecorded_media: {
      count: media.filter(element => !liveMedia.includes(element)).length,
      evidence: ["Visible audio/video candidates were found; the browser cannot determine whether every item is prerecorded."]
    },
    live_media: {
      count: liveMedia.length,
      evidence: ["Live/media-stream candidates were found; owner confirmation is needed to distinguish live from prerecorded content."]
    },
    forms: {
      count: first("form").filter(form =>
        visible(form) && form.querySelector("input,select,textarea,button")
      ).length,
      evidence: ["Visible forms with interactive fields or controls were found."]
    },
    authentication: {
      count: first("input[type=password]").filter(visible).length,
      evidence: ["Visible password input candidates were found; this does not establish an authentication flow."]
    },
    time_limits: {
      count: all("meta[http-equiv='refresh']").length + first("body *").filter(visible).filter(element =>
        /\\b(session expires|time remaining|minutes? left|seconds? left|countdown|automatically log ?out)\\b/.test(visibleText(element))
      ).length,
      evidence: ["Meta refresh and visible timer/session-expiry text are candidate signals; scripted time limits may not be detectable."]
    },
    moving_content: {
      count: first("body *").filter(element => {
        if (!visible(element)) return false;
        const style = getComputedStyle(element);
        return style.animationName !== "none" ||
          (style.animationDuration !== "0s" && style.animationDuration !== "") ||
          element.tagName.toLowerCase() === "marquee" ||
          Boolean(element.querySelector("animate,animateTransform"));
      }).length,
      evidence: ["Visible animation/marquee candidates were found; animation does not establish that content moves, flashes, or needs a control."]
    },
    custom_widgets: {
      count: first(
        "[role],button,input,select,textarea,[tabindex]"
      ).filter(element => visible(element) &&
        (element.hasAttribute("role") || element.hasAttribute("tabindex"))).length,
      evidence: ["Visible custom-role or tabindex candidates were found."]
    },
    alternate_languages: {
      count: first("[lang]").filter(element =>
        visible(element) && element.lang &&
        element.lang.toLowerCase() !== (document.documentElement.lang || "").toLowerCase()
      ).length,
      evidence: ["Visible elements with a language attribute different from the document language were found."]
    },
    text_in_images: {
      count: first("img,svg,canvas").filter(visible).length,
      evidence: ["Visible image/graphic candidates were found; text content and purpose require review."]
    },
    pointer_gestures: {
      count: first("[style*=touch-action],[data-gesture],[data-pinch],[data-swipe]").filter(visible).filter(element =>
        getComputedStyle(element).touchAction === "none" || element.hasAttribute("data-gesture") || element.hasAttribute("data-pinch") || element.hasAttribute("data-swipe")
      ).length,
      evidence: ["Touch-action or gesture-attribute candidates were found; event-handler behavior needs review."]
    },
    dragging: {
      count: first("[draggable=true],[data-drag],.draggable").filter(visible).length +
        first("body *").filter(element => visible(element) && getComputedStyle(element).cursor === "grab").length,
      evidence: ["Draggable/grab-style candidates were found; the browser cannot determine whether a non-drag alternative exists."]
    },
    motion_controls: {
      count: first("[data-motion],[data-tilt],[data-shake],[aria-label],[title]").filter(visible).filter(element =>
        element.hasAttribute("data-motion") || element.hasAttribute("data-tilt") || element.hasAttribute("data-shake") || /\\b(tilt|shake|motion control|device movement)\\b/.test(visibleText(element))
      ).length,
      evidence: ["Motion-related labels/attributes are candidates only; device-motion listeners are not reliably discoverable."]
    },
    transactions: {
      count: transactionCandidates.length,
      evidence: ["Payment and transaction language/field candidates were found; transaction purpose and review safeguards require context."]
    },
    multiple_pages: {
      count: sameSitePaths.size,
      evidence: ["Distinct same-site navigation destinations were found; this does not prove site-wide page coverage."]
    },
    color_coded_content: {
      count: statusCandidates.length,
      evidence: ["Status/current/error/badge candidates were found; the browser cannot determine whether color is the only cue."]
    },
    two_dimensional_content: {
      count: first("table,[role=grid],[role=table],canvas,[role=img]").filter(visible).length + scrollableRegions.length,
      evidence: ["Table/grid/canvas/scrollable-region candidates were found; essentiality and appropriate reflow require review."]
    },
    structured_content: {
      count: first("h1,h2,h3,h4,h5,h6,main,[role=main],article,ol,ul").filter(visible).length,
      evidence: ["Headings, landmarks, or ordered content candidates were found; their meaning and sequence require review."]
    }
  };
  const truncated = [
    "video,audio", "form", "input[type=password]", "body *",
    "[role],button,input,select,textarea,[tabindex]", "[lang]",
    "img,svg,canvas", "[style*=touch-action],[data-gesture],[data-pinch],[data-swipe]",
    "[draggable=true],[data-drag],.draggable", "[data-motion],[data-tilt],[data-shake],[aria-label],[title]",
    "input,button,a,[role=button]", "a[href]", "[role=status],[role=alert],[aria-current],[aria-invalid],[class*=status i],[class*=badge i]",
    "table,[role=grid],[role=table],canvas,[role=img]", "h1,h2,h3,h4,h5,h6,main,[role=main],article,ol,ul"
  ].some(wasTruncated);
  return {features, truncated};
}"""


def sanitize_context_url(value: str) -> str:
    if len(value) > 2_048:
        raise ValueError("Context URLs must be 2,048 characters or fewer.")
    parsed = urlsplit(value.strip())
    if (
        parsed.scheme not in ("http", "https")
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(
            "Use an absolute public HTTP(S) URL without credentials, query strings, or fragments."
        )
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path or "/", "", ""))


def validate_owner_text(value: str | None) -> str | None:
    if value is None:
        return None
    if len(value) > MAX_TEXT_LENGTH:
        raise ValueError(f"Text must be {MAX_TEXT_LENGTH} characters or fewer.")
    if any(pattern.search(value) for pattern in _SENSITIVE_TEXT_PATTERNS):
        raise ValueError(
            "Do not include passwords, personal contact details, access tokens, or secrets."
        )
    return value


_OWNER_ASSESSMENT_YES_MEANING_BY_QUESTION: dict[
    str, Literal["support", "concern"]
] = {
    "media.prerecorded_alternatives": "support",
    "media.prerecorded_audio_description_or_alternative": "support",
    "media.live_captions": "support",
    "media.prerecorded_audio_description": "support",
    "forms.labels_and_instructions": "support",
    "forms.error_identification": "support",
    "forms.error_suggestions": "support",
    "forms.repeated_entry": "concern",
    "authentication.cognitive_steps": "support",
    "motion.flash_threshold": "concern",
    "widgets.status_messages": "support",
    "content.meaningful_sequence": "support",
    "visual.images_of_text": "support",
    "forms.sensory_instructions": "support",
    "widgets.sensory_instructions": "support",
    "keyboard.character_shortcuts": "support",
    "content.headings_and_labels": "support",
    "widgets.no_unexpected_change_on_focus": "support",
    "forms.no_unexpected_change_on_input": "support",
    "pointer.gesture_alternative": "support",
    "pointer.cancellation": "support",
    "dragging.alternative": "support",
    "motion.actuation_alternative": "support",
    "transactions.error_prevention": "support",
    "pages.multiple_ways_to_find": "support",
    "pages.consistent_navigation_order": "support",
    "pages.consistent_identification": "support",
    "pages.consistent_help_location": "support",
}


_OWNER_ASSESSMENT_YES_MEANING = {
    (question.question_id, criterion_id): yes_meaning
    for question in QUESTIONNAIRE_QUESTIONS
    if (yes_meaning := _OWNER_ASSESSMENT_YES_MEANING_BY_QUESTION.get(
        question.question_id
    ))
    for criterion_id in question.criterion_ids
    if not (
        question.question_id == "visual.images_of_text"
        and criterion_id == "1.1.1"
    )
}


def _interpret_owner_answer(
    answer: OwnerAnswer, criterion_id: str
) -> dict[str, str]:
    yes_meaning = _OWNER_ASSESSMENT_YES_MEANING.get(
        (answer.question_id, criterion_id)
    )
    if answer.answer == "not_sure":
        outcome = "inconclusive"
    elif answer.answer == "not_applicable":
        outcome = "not_applicable"
    elif yes_meaning is None:
        outcome = "context_only"
    elif answer.answer == "yes":
        outcome = (
            "supports"
            if yes_meaning == "support"
            else "indicates_concern"
        )
    else:
        outcome = (
            "indicates_concern"
            if yes_meaning == "support"
            else "supports"
        )
    return {
        "outcome": outcome,
        "basis": (
            "The questionnaire answer polarity is defined for this prompt; "
            "this remains an unverified owner report."
            if yes_meaning is not None
            else "The answer is retained as context because the prompt has no reliable yes/no polarity."
        ),
    }


def question_answer_interpretation(question_id: str) -> dict[str, str]:
    question = _QUESTION_BY_ID[question_id]
    return {
        "by_criterion": {
            criterion_id: {
                "yes": _interpret_owner_answer(
                    OwnerAnswer(question_id=question_id, answer="yes"),
                    criterion_id,
                )["outcome"],
                "no": _interpret_owner_answer(
                    OwnerAnswer(question_id=question_id, answer="no"),
                    criterion_id,
                )["outcome"],
                "not_sure": "inconclusive",
                "not_applicable": "not_applicable",
            }
            for criterion_id in question.criterion_ids
        }
    }


def get_questions(
    declared_features: dict[str, bool | None],
    browser_features: tuple[BrowserFeatureEvidence, ...] = (),
    answered_question_ids: set[str] | None = None,
    negative_features: set[str] | None = None,
) -> tuple[QuestionnaireQuestion, ...]:
    observed = {item.feature_id for item in browser_features if item.detected}
    answered_question_ids = answered_question_ids or set()
    negative_features = set(negative_features or ())
    negative_features.update(
        feature_id
        for feature_id, present in declared_features.items()
        if present is False
    )
    relevant_questions = tuple(
        question
        for question in (*INITIAL_QUESTIONS, *QUESTIONNAIRE_QUESTIONS)
        if question.question_id not in answered_question_ids
        and (
            question.feature_id is None
            or declared_features.get(question.feature_id) is True
            or question.feature_id in observed
        )
    )
    discovery_followups = tuple(
        question
        for feature_id, question in _DISCOVERY_QUESTION_BY_FEATURE.items()
        if feature_id in observed
        and feature_id in negative_features
        and question.question_id not in answered_question_ids
    )
    return relevant_questions + discovery_followups


async def discover_browser_features(
    page: FeatureDiscoveryPage,
    *,
    viewport: str,
    timeout_seconds: int = FEATURE_DISCOVERY_TIMEOUT_SECONDS,
) -> BrowserFeatureDiscovery:
    try:
        raw = await asyncio.wait_for(
            page.evaluate(
                _DISCOVER_FEATURES,
                MAX_DISCOVERY_CANDIDATES,
            ),
            timeout=timeout_seconds,
        )
        if not isinstance(raw, dict):
            raise TypeError("Browser feature discovery must return an object.")
        raw_features = raw.get("features")
        truncated = raw.get("truncated")
        if not isinstance(raw_features, dict) or not isinstance(truncated, bool):
            raise TypeError("Browser feature discovery returned invalid coverage details.")
        features = []
        for feature_id, details in raw_features.items():
            if feature_id not in FEATURE_IDS or not isinstance(details, dict):
                raise TypeError("Browser feature discovery returned an unknown feature.")
            count = details.get("count")
            evidence = details.get("evidence", [])
            if not isinstance(count, int) or count < 0 or not isinstance(evidence, list):
                raise TypeError("Browser feature discovery returned invalid measurements.")
            features.append(
                BrowserFeatureEvidence(
                    feature_id=feature_id,
                    detected=count > 0,
                    count=count,
                    viewport=viewport,
                    evidence=tuple(str(item) for item in evidence[:5]),
                )
            )
        return BrowserFeatureDiscovery(
            status="partial" if truncated else "available",
            features=tuple(features),
            details=(
                (
                    f"Discovery was limited to the first {MAX_DISCOVERY_CANDIDATES} candidates per selector."
                    " Counts are lower bounds when a selector was truncated."
                )
                if truncated
                else ()
            ),
        )
    except Exception as error:
        return BrowserFeatureDiscovery(
            status="unavailable",
            details=(f"Browser feature discovery failed ({type(error).__name__}).",),
        )


def build_hybrid_evaluation(
    *,
    declared_features: dict[str, bool | None],
    feature_inventory_completed: bool = False,
    answers: tuple[OwnerAnswer, ...],
    browser_discoveries: tuple[BrowserFeatureDiscovery, ...],
    browser_checks: tuple[BrowserCriterionEvidence, ...] = (),
    representative_page_urls: tuple[str, ...] = (),
    journeys: tuple[dict, ...] = (),
    free_text: str | None = None,
) -> dict:
    browser_evidence = tuple(
        evidence
        for discovery in browser_discoveries
        for evidence in discovery.features
    )
    answered_questions = {answer.question_id for answer in answers}
    if representative_page_urls:
        answered_questions.add("scope.representative_pages")
    if journeys:
        answered_questions.add("scope.user_journeys")
    if feature_inventory_completed or any(
        present is not None for present in declared_features.values()
    ):
        answered_questions.add("scope.features")
    negative_features = {
        feature_id
        for feature_id, present in declared_features.items()
        if present is False
    }
    questions = get_questions(
        declared_features,
        browser_evidence,
        answered_questions,
        negative_features,
    )
    answers_by_criterion: dict[str, list[dict]] = {
        criterion_id: [] for criterion_id in WCAG_CRITERION_IDS
    }
    self_assessment_by_criterion: dict[str, list[dict]] = {
        criterion_id: [] for criterion_id in WCAG_CRITERION_IDS
    }
    browser_by_criterion: dict[str, list[dict]] = {
        criterion_id: [] for criterion_id in WCAG_CRITERION_IDS
    }

    for answer in answers:
        question = _QUESTION_BY_ID[answer.question_id]
        evidence = {
            "source": "owner_reported",
            "question_id": answer.question_id,
            "answer": answer.answer,
            "explanation": answer.explanation,
            "page_urls": list(answer.page_urls),
            "verified": False,
            "interpretation": "Context supplied by the website owner; not proof of conformance.",
        }
        for criterion_id in question.criterion_ids:
            answers_by_criterion[criterion_id].append(evidence)
            self_assessment_by_criterion[criterion_id].append(
                {
                    "source": "owner_reported",
                    "question_id": answer.question_id,
                    "question": question.prompt,
                    "answer": answer.answer,
                    "reported_interpretation": _interpret_owner_answer(
                        answer, criterion_id
                    ),
                    "explanation": answer.explanation,
                    "page_urls": list(answer.page_urls),
                    "independent_review": False,
                    "interpretation": (
                        "Owner self-assessment input only. The answer is recorded as reported; "
                        "it is not independently verified and does not establish WCAG conformance."
                    ),
                }
            )

    for feature_id, present in declared_features.items():
        if present is None:
            continue
        evidence = {
            "source": "owner_reported",
            "feature_id": feature_id,
            "present": present,
            "verified": False,
            "interpretation": "Owner-declared feature scope; not proof of conformance or absence.",
        }
        for criterion_id in FEATURE_CRITERIA.get(feature_id, ()):
            answers_by_criterion[criterion_id].append(evidence)

    for feature in browser_evidence:
        if not feature.detected:
            continue
        evidence = {
            "source": "browser_observed",
            "feature_id": feature.feature_id,
            "detected": True,
            "count": feature.count,
            "viewport": feature.viewport,
            "evidence": list(feature.evidence),
            "interpretation": "Feature discovery routes evaluation; presence does not establish a WCAG failure.",
        }
        for criterion_id in FEATURE_CRITERIA.get(feature.feature_id, ()):
            browser_by_criterion[criterion_id].append(evidence)

    for check in browser_checks:
        if check.criterion_id not in browser_by_criterion:
            continue
        browser_by_criterion[check.criterion_id].append(
            {
                "source": "browser_observed",
                "analyzer_id": check.analyzer_id,
                "result_status": check.result_status,
                "viewport": check.viewport,
                "summary": check.summary,
                "evidence_count": check.evidence_count,
                "interpretation": (
                    "Bounded browser evidence; this result alone does not establish criterion conformance."
                ),
            }
        )

    criteria = []
    for criterion_id in WCAG_CRITERION_IDS:
        owner_evidence = answers_by_criterion[criterion_id]
        observed_evidence = browser_by_criterion[criterion_id]
        # All 55 in-scope criteria have at most partial automated coverage.
        # Keep human review required even when a bounded scanner check ran.
        manual_review_needed = True
        if owner_evidence and observed_evidence:
            status = "manual_review_needed"
        elif owner_evidence:
            status = "owner_reported"
        elif observed_evidence:
            status = "browser_observed"
        else:
            status = "not_evaluated"
        assessment_responses = self_assessment_by_criterion[criterion_id]
        assessment_outcomes = {
            response["reported_interpretation"]["outcome"]
            for response in assessment_responses
        }
        directional_outcomes = assessment_outcomes & {
            "supports",
            "indicates_concern",
        }
        if not assessment_responses:
            reported_outcome = None
            assessment_status = "not_provided"
        elif len(directional_outcomes) > 1:
            reported_outcome = "mixed"
            assessment_status = "assessed_from_owner_answers"
        elif directional_outcomes and assessment_outcomes & {
            "inconclusive",
            "not_applicable",
        }:
            reported_outcome = "mixed_or_inconclusive"
            assessment_status = "assessed_from_owner_answers"
        elif directional_outcomes:
            reported_outcome = next(iter(directional_outcomes))
            assessment_status = "assessed_from_owner_answers"
        elif assessment_outcomes == {"not_applicable"}:
            reported_outcome = "owner_marked_not_applicable"
            assessment_status = "assessed_from_owner_answers"
        elif assessment_outcomes == {"inconclusive"}:
            reported_outcome = "inconclusive"
            assessment_status = "assessed_from_owner_answers"
        else:
            reported_outcome = "context_only"
            assessment_status = "context_only"
        criteria.append(
            {
                "criterion_id": criterion_id,
                **_CRITERION_METADATA[criterion_id],
                "status": status,
                "manual_review_required": manual_review_needed,
                "owner_reported": owner_evidence,
                "owner_self_assessment": {
                    "status": assessment_status,
                    "reported_outcome": reported_outcome,
                    "responses": assessment_responses,
                    "criterion_conclusion": None,
                    "interpretation": (
                        "This is an owner-reported assessment, not an independent "
                        "manual review or a WCAG pass/failure. Directional outcomes "
                        "are inferred only for questions whose wording has a defined "
                        "answer polarity; contextual answers are not interpreted."
                    ),
                },
                "browser_observed": observed_evidence,
                "conflicts": [],
                "compliance_conclusion": None,
            }
        )

    criteria_by_id = {criterion["criterion_id"]: criterion for criterion in criteria}
    conflicts = []
    resolved_feature_presence = dict(declared_features)
    for answer in answers:
        if not answer.question_id.startswith("discovery."):
            continue
        feature_id = _QUESTION_BY_ID[answer.question_id].feature_id
        if feature_id is None:
            continue
        resolved_feature_presence[feature_id] = (
            True if answer.answer == "yes" else
            False if answer.answer == "no" else
            None
        )

    for feature_id, owner_says_present in resolved_feature_presence.items():
        if owner_says_present is not False:
            continue
        detections = [
            item for item in browser_evidence
            if item.feature_id == feature_id and item.detected
        ]
        if not detections:
            continue
        conflict = {
            "type": "owner_browser_feature_conflict",
            "feature_id": feature_id,
            "owner_reported_present": False,
            "browser_observed_present": True,
            "summary": "You initially marked this feature absent, but the browser found a candidate. Confirm whether it belongs to the site and provide the relevant public page.",
            "browser_evidence": [
                {
                    "count": item.count,
                    "viewport": item.viewport,
                    "evidence": list(item.evidence),
                }
                for item in detections
            ],
            "resolution": "Review the feature scope; browser discovery is a candidate signal, not a compliance conclusion.",
        }
        conflicts.append(conflict)
        for criterion_id in FEATURE_CRITERIA.get(feature_id, ()):
            criteria_by_id[criterion_id]["conflicts"].append(conflict)

    browser_concern_statuses = {
        "fail",
        "violation",
        "violations",
        "confirmed_failure",
    }
    for criterion in criteria:
        supporting_answers = [
            answer
            for answer in criterion["owner_self_assessment"]["responses"]
            if answer["reported_interpretation"]["outcome"] == "supports"
        ]
        browser_concerns = [
            evidence
            for evidence in criterion["browser_observed"]
            if evidence.get("result_status") in browser_concern_statuses
        ]
        if not supporting_answers or not browser_concerns:
            continue
        conflict = {
            "type": "owner_support_browser_concern",
            "criterion_id": criterion["criterion_id"],
            "summary": (
                "The owner reported support for this criterion, while a bounded "
                "browser check reported a violation candidate. Review the same "
                "page and state; neither source alone settles the criterion."
            ),
            "owner_answers": [
                {
                    "question_id": answer["question_id"],
                    "answer": answer["answer"],
                    "page_urls": answer["page_urls"],
                }
                for answer in supporting_answers
            ],
            "browser_evidence": [
                {
                    "analyzer_id": evidence.get("analyzer_id"),
                    "result_status": evidence["result_status"],
                    "viewport": evidence["viewport"],
                    "summary": evidence["summary"],
                    "evidence_count": evidence["evidence_count"],
                }
                for evidence in browser_concerns
            ],
            "resolution": (
                "Review the affected page/state and reconcile the owner report with "
                "the browser finding; this is a source disagreement, not a final "
                "criterion conclusion."
            ),
        }
        conflicts.append(conflict)
        criterion["conflicts"].append(conflict)

    available_discoveries = [
        item for item in browser_discoveries if item.status == "available"
    ]
    partial_discoveries = [
        item for item in browser_discoveries if item.status == "partial"
    ]
    unavailable_discoveries = [
        item for item in browser_discoveries if item.status == "unavailable"
    ]
    if partial_discoveries or (
        available_discoveries and unavailable_discoveries
    ):
        discovery_status = "partial"
    elif available_discoveries:
        discovery_status = "available"
    elif unavailable_discoveries:
        discovery_status = "unavailable"
    else:
        discovery_status = "not_attempted"

    return {
        "status": "partial",
        "questionnaire_version": "2.0",
        "representative_page_urls": list(representative_page_urls),
        "user_journeys": list(journeys),
        "declared_features": declared_features,
        "feature_inventory_completed": feature_inventory_completed,
        "owner_answers": [
            {
                "source": "owner_reported",
                "question_id": answer.question_id,
                "answer": answer.answer,
                "explanation": answer.explanation,
                "page_urls": list(answer.page_urls),
                "verified": False,
            }
            for answer in answers
        ],
        "optional_context": free_text,
        "questions_to_ask": [
            {
                "question_id": question.question_id,
                "criterion_ids": list(question.criterion_ids),
                "feature_id": question.feature_id,
                "prompt": question.prompt,
                "answer_options": list(question.answer_options),
                "helper_text": question.helper_text,
            }
            for question in questions
        ],
        "criteria": criteria,
        "conflicts": conflicts,
        "browser_discovery_status": discovery_status,
        "details": [
            "Questionnaire information is scoped to this audit response; it is not durably stored by the current stateless API.",
            "Owner-reported answers are not verified claims and cannot establish WCAG conformance.",
            "Browser feature discovery is incomplete and is used to route follow-up questions, not to infer compliance.",
            "Criteria without relevant evidence remain not_evaluated, not passed.",
        ],
    }


def validate_questionnaire_inputs(
    *,
    answers: tuple[OwnerAnswer, ...],
    declared_features: dict[str, bool | None],
) -> None:
    if len(answers) > MAX_ANSWERS:
        raise ValueError(f"At most {MAX_ANSWERS} questionnaire answers are allowed.")
    unknown_features = set(declared_features) - set(FEATURE_IDS)
    if unknown_features:
        raise ValueError(f"Unknown feature identifiers: {', '.join(sorted(unknown_features))}.")
    seen_question_ids: set[str] = set()
    for answer in answers:
        if answer.question_id not in _QUESTION_BY_ID:
            raise ValueError(f"Unknown questionnaire question: {answer.question_id}.")
        if answer.question_id in seen_question_ids:
            raise ValueError(f"Duplicate questionnaire answer: {answer.question_id}.")
        seen_question_ids.add(answer.question_id)
        validate_owner_text(answer.explanation)
        for page_url in answer.page_urls:
            sanitize_context_url(page_url)

# Browser capture foundation

Run `npm ci` to install the pinned local axe-core rules bundle. Then run the API
with `python run_server.py` after installing `requirements.txt` and
installing Playwright's Chromium browser with
`python -m playwright install chromium`. On Windows, the launcher selects the
Proactor event-loop policy and runs Uvicorn without reload; restart it manually
after backend code changes. The capture endpoint is `POST /captures` and accepts
a URL. Each request captures desktop (1365x768), tablet (768x1024), and mobile
(390x844) sequentially, returning a distinct screenshot reference for each
successful viewport. At most two multi-viewport requests run concurrently. The
overall request deadline allows for all three configured navigation and settling
periods, bounded link-check budget, and accessibility scan budget. Each successful
viewport response includes document-level horizontal overflow measurements and a separate
element-level diagnosis from the same live page; diagnosis failures do not
discard a successful capture or screenshot.
Each raw element candidate also carries bounded layout evidence when available:
its scroll/client widths, bounding geometry, computed sizing and positioning
styles, up to five ancestors, and up to eight oversized descendants from a bounded
three-level/50-node descendant scan. Flex/grid context and enabled horizontal
scrolling are recorded. Possible layout explanations are explicitly hypotheses
supported by these measurements, not root-cause claims. Stale selectors and
per-element style errors are reported as layout-evidence limitations without
discarding the raw candidate or failing the capture.
Normalized overflow findings preserve the raw element measurements and classify
their geometric relationship to document overflow. A direct geometry match requires
both the element's right edge and overflow amount to agree with the document-level
measurement within 2 px; it is not proof of causation. Other measured candidates
are marked `possible_contributor`, while missing page-level evidence is `unmatched`.
The finding ID is deterministic for the rule, selector, viewport name, and width.
Normalization removes only repeated measurements with the same tag and geometry
whose selectors are identical or one is an ancestor path of the other. It does not
deduplicate merely overlapping elements, and selector path equivalence is
conservative: semantically equivalent CSS selectors that use different syntax may
remain separate.
The response also includes audit-level `audit_findings`, grouping normalized
findings by exact rule identifier and selector across viewports while retaining
each viewport-specific finding and its measurements. A group is prioritized as
`direct_geometry_match` if any member has that classification; otherwise it uses
`possible_contributor` when present, or `unmatched`. These labels express
relative evidential support, not severity or a numeric score. Incomplete
normalization yields partial aggregation while preserving groups from available
viewports.
The response's `audit_summary` separately summarizes document-level overflow by
viewport and lists normalized element candidates as issues. Issues are ordered by
evidence class (`direct_geometry_match`, `possible_contributor`, then `unmatched`),
with rule, selector, and group ID as deterministic tie-breakers. Each issue includes
viewport widths, measured element/document overflow, its evidence classification,
and cautious wording that avoids claiming causation. Capture and analysis
limitations are listed separately from findings; missing measurements are not
reported as clean results.

Each successfully loaded viewport also includes a read-only `functional_ux_audit`.
It inspects rendered anchors and images from the existing live page. HTTP(S) link
destinations receive bounded `HEAD` checks; redirects are followed manually with
destination validation on every hop, up to five redirects. `404` and other
conclusive `4xx`/`5xx` responses and network failures are reported as observed
broken-link findings. Successful `2xx` responses are omitted. Authentication or
access denials, rate limiting, unsupported `HEAD`, timeouts, non-web URL schemes,
and prohibited destinations remain in the separate `inconclusive` list; they are
not represented as confirmed broken links. Checks are limited to 15 rendered
links and run concurrently with per-link deadlines; the API deadline accounts
for this bounded per-viewport check time.

Rendered images are reported as failed only when a non-empty source finishes with
`naturalWidth` equal to zero, or when an image with an accessible label has no
source. Images without a source and without enough content context are kept
inconclusive; explicitly decorative or hidden images are not flagged. Resources
that are still loading remain inconclusive. The audit never clicks links or uses
GET to check link destinations, and it does not submit forms. Because some servers
reject or handle `HEAD` differently from normal navigation, results are cautious
indicators rather than proof that a user-facing navigation will fail. Only
rendered anchors are checked, and the audit is repeated per viewport.

Each successfully loaded viewport also includes `accessibility_scan`, produced by
axe-core 4.14.0 on the same live Playwright page. It runs only rules tagged with
WCAG 2.0/2.1/2.2 Level A or AA tags; best-practice-only and AAA-only rules are
not selected. Rule tags, impact, descriptions, help, help URL, node selectors,
bounded/redacted HTML snippets, checks, and failure summaries are retained in
separate `violations`, `incomplete`, `passes`, and `inapplicable` collections.
An incomplete axe result is for human review, never a confirmed violation.
`available` means the engine completed, not that the page passed or conforms.
Execution failures and missing local axe assets are explicitly `unavailable`;
they do not discard capture, screenshot, overflow, layout, or functional UX
results. The full WCAG 2.2 A/AA criterion inventory and limitations are in
[WCAG 2.2 coverage inventory](./wcag-22-coverage-inventory.md).

The `accessibility_scan.non_text_contrast` object adds a bounded supplemental
probe for WCAG 1.4.11. It inspects visible native controls, links, selected ARIA
controls, and SVG shapes for computed solid-color backgrounds, borders,
outlines, fills, and strokes whose estimated contrast against the adjacent
solid background is below 3:1. Evidence includes the selector, role, geometry,
viewport, color pair, measured ratio, and the 3:1 threshold. Findings are
always `needs_review`; the result is `partial` even when no candidates are
reported as low contrast.

This probe does not establish which boundary or graphical object is needed to
identify a component or state, so low ratios are potential issues rather than
confirmed failures and adequate sampled ratios are not a pass. It does not
pixel-sample images, canvas, video, gradients, or complex layered/blended
rendering, and it does not inspect pseudo-element graphics or box shadows;
those cases need visual review. It can miss custom components or graphical
objects not in its bounded selector set. axe's `color-contrast`
rule concerns text contrast and is not by itself coverage of non-text contrast.

Each successful viewport also includes a separate `keyboard_focus_audit`. It
samples visible interactive candidates with at most 51 `Tab` and 2
`Shift+Tab` key presses, matching the 50-candidate discovery bound plus one
boundary action. It records bounded selectors, role/name, focus state,
computed-style indicator evidence, and hit-test evidence for possible
obscuration. It never presses Enter or Space or clicks controls. The audit
temporarily blocks network requests during key interaction and runs in the
disposable isolated capture context, which is closed after all audits. Pages can
opt out with `data-webable-keyboard-audit="unsafe"` on the root element.

Each keyboard check has its own `pass`, `fail`, `needs_review`, `not_tested`,
or `error` status and remains separate from axe results. Bounded progression,
focus-order, and focus-indicator observations remain `needs_review`; absent
candidates are `not_tested`. A complete opaque full-cover result for criterion
2.4.11 can be a high-confidence failure candidate, while ambiguous occlusion
remains review-only. For criterion 2.1.2, a consecutive same-target Tab stall
is distinguished from a focus sequence that cycles among targets. When a Tab
stall occurs, the bounded reverse sample records whether Shift+Tab moved focus
from that target. Neither observation establishes whether the containing
component can be exited or whether a modal/widget exception and dismissal
method applies, so keyboard-trap evidence always requires review. Repeated
multi-target Tab cycles are compared against the sampled reverse sequence and
reported as possible widget-level trapping when focus remains in that cycle;
intentional dialog wrapping is not treated as a confirmed failure. This avoids
treating a bounded observation as proof of conformance or failure. A suspected
trap, missing focus style, skipped candidate, or possible overlay is sent for
review. A sampled Tab order does
not establish correct semantic focus order, keyboard operation of every widget,
indicator contrast/size, or complete non-obscuration. The hit test samples only
a bounded 5x5 interior grid; computed-style comparison cannot discover every focus indicator
technique. For WCAG 2.4.11, focused-target evidence includes its measured rectangle,
viewport dimensions, sampled occluders, and their geometry and computed styles.
The analyzer reports a high-confidence failure candidate only when a layered,
opaque element covers the entire in-viewport target and intercepts every grid
sample. Partial or translucent overlap and other ambiguous cases remain
`needs_review`; no sampled occlusion is not a pass because the complete visible
area and all focus states are not evaluated. This check is part of the keyboard
focus audit and is not a separate duplicate analyzer. Focus/blur handlers can
have other page-defined effects, so network
interception and blocking service workers are not a guarantee that arbitrary
script is side-effect-free.

The candidate list is a heuristic snapshot, not the browser's authoritative
sequential focus order. Per-scan evidence identifies detected positive
`tabindex` elements, treats each named radio group as one expected sequential
tab stop, reports open shadow-root hosts and frames, identifies candidates
appearing after the initial snapshot, and marks focused targets absent from the
initial snapshot. The 51-action bound covers the 50 discovered candidates and
one extra boundary action, but the candidate list is still heuristic and may
be truncated. These are explicit limitations, not proof that a candidate was
unreachable. Closed shadow roots, inaccessible frame
contents, and custom widgets may remain undiscovered. Observed elements are
not treated as complete merely because their count matches the snapshot. Tab
and Shift+Tab traversal stops on a repeat, the action limit, or an observed
end; a repeat among different targets may represent normal wrapping rather
than a trap and is checked against reverse traversal. The audit's
outer and per-action timeouts return explicit error or review states;
cancellation unwinds the temporary route handler and the capture runner closes
the page, context, and browser in its `finally` cleanup.

Each successfully loaded viewport includes `target_size_audit` for WCAG 2.5.8.
It measures visible, enabled links and controls (including explicit button/link
roles) and reports targets narrower or shorter than 24 CSS pixels, with their
selector, accessible name when available, and measured bounds. These are
`needs_review` candidates, not confirmed failures: the scan does not evaluate
the spacing, inline, equivalent-control, user-agent, or essential exceptions,
and does not discover every custom pointer interaction or determine the full
effective hit area. Targets meeting the measured dimensions are not proof that
the criterion passes. Discovery is bounded to 500 targets per viewport, and
the inventory records this as partial coverage requiring manual review.

The inventory distinguishes existing axe mappings from this WebAble keyboard
probe. axe-core 4.14.0 has enabled, selected rules tagged to 2.1.1, but none for
2.1.2, 2.4.3, 2.4.7, or 2.4.11. The probe adds bounded partial evidence for
those criteria without replacing contextual evaluation. WCAG 2.2 criterion
2.4.13 Focus Appearance is Level AAA (not AA) and remains out of scope; this
audit does not measure its perimeter-area or contrast requirements.

Each successful viewport also includes `text_reflow_audit` with separately
identified baseline, WCAG 1.3.4 orientation, 200% text-enlargement, WCAG
text-spacing, WCAG 1.4.13 hover/focus-content, 320 CSS-pixel reflow, and browser
zoom scenarios. The text
scenario temporarily doubles each discovered visible
text-bearing element's computed font size, measures clipping and new text
overlaps, optionally captures the suspicious state, and restores inline font
styles in a cleanup evaluation. All eligible candidates' original computed
sizes are read before any style is changed. Nested and inherited sizes are
then set as explicit doubled pixel values, so this deterministic method does
not reproduce relative-unit cascading or every browser's text-only zoom
behavior. The 320 CSS-pixel scenario resizes the existing page using CSS
viewport dimensions, measures and optionally captures before restoring the
original viewport in a `finally` path. A 256 CSS-pixel height probe at the
captured width runs only when a table or ARIA table/grid is detected.

Playwright Chromium in this configuration does not provide a reliable
verified control for actual browser zoom, so 200% browser zoom is explicitly
`unsupported`; no CSS transform, device-scale-factor, or screenshot-size proxy
is used. Measured clipping, ellipsis, overlap, and horizontal overflow are
reported as `needs_review`: geometry alone does not establish that text is
unavailable, that overlap obscures information, or that a two-dimensional
content exception applies. Ellipsis and clipping measurements explicitly leave
complete-text availability unevaluated. Document-level horizontal overflow is
also surfaced for review when no text-element finding accounts for it.
Truncated candidate discovery prevents a `no_violation_detected` result.
Confidence labels are qualitative descriptions of the strength of the
measurement evidence, not probabilities or calibrated scores.

The bounded scan does not inspect generated pseudo-element content, canvas
text, or text embedded in images; it does not evaluate every dynamic or
interactive state, and it samples at most 300 text-bearing elements. A
responsive replacement or missing baseline element is reported for review,
not treated as proof of lost content. Desktop, tablet, and mobile baseline
screenshots retain their existing capture behavior. A separate scenario
screenshot is captured only when the 1.3.4 orientation, 200% text, 1.4.13
hover/focus-content, 320 CSS-pixel reflow, or executed 256 CSS-pixel-height
measurement produces findings. Each qualifying scenario gets at most one
viewport-sized PNG, shared by its scenario and all its findings; no image is
generated for a clean or untested scenario.

The 200% text override remains applied through measurement and optional
screenshot capture, then is restored in a `finally` path. Scenario
measurements wait for two animation frames after applying the font override or
resizing the viewport; screenshots are taken immediately after those
measurements and before the override or viewport is restored. Capture verifies
the live CSS viewport and uses CSS-pixel image scaling rather than a full-page
image. Scenario files include a unique capture identifier plus the viewport
and scenario identifiers, so they do not overwrite the baseline screenshot or
another capture. Screenshot errors are reported in scenario details and do
not erase measurements or findings.
Screenshots are supporting visual evidence only: disabling capture or a
failed image save does not disable detection. `no_violation_detected` means
only that these bounded checks did not detect a problem; it is not a
conformance claim.

The `text_spacing` scenario extends this analyzer for WCAG 1.4.12. It captures
baseline measurements, then applies line-height `1.5`, paragraph bottom spacing
`2em`, letter spacing `0.12em`, and word spacing `0.16em` to up to 300 visible
text-bearing elements. It compares text geometry and overlap, container
overflow, visibility, and sampled hit-testing for interactive controls against
that baseline. Findings include selectors, measured geometry, viewport
dimensions, relevant baseline/current measurements, and control occluders when
detected. All findings are `needs_review`: geometry cannot prove actual loss of
text or functionality. Existing scrollable containers are identified and are
not automatically treated as failures; spacing-induced changes within them
remain review evidence. Original inline values and priorities for all four CSS
properties are restored in a `finally` path, including after measurement or
screenshot errors. This is a deterministic CSS override, not native browser
text-spacing or zoom behavior, and custom controls, pseudo-element text, canvas,
images of text, dynamic states, and content beyond the candidate limit may not
be covered.

The `orientation` scenario extends this analyzer for WCAG 1.3.4. It resizes the
live CSS viewport to paired portrait and landscape dimensions, waits for the
layout to settle, and compares up to 300 visible text-bearing elements and
controls by selector and opaque content signature. Findings include both
viewport dimensions, per-orientation visibility and geometry, and whether the
content signature changed. A disappearing element or changed signature is
`needs_review`, not a confirmed failure: the probe cannot judge whether
replacement content is equivalent or whether an orientation restriction is
essential. Elements outside the viewport but still in normal document flow are
not treated as missing merely because scrolling is needed.

This is a CSS viewport/responsive-layout test, not physical device rotation. It
does not emulate orientation sensors, every native `orientationchange` event,
or all dynamic application states. Images without text alternatives, canvas
content without an accessible label, pseudo-element content, and content past
the candidate limit are not fully assessed. The captured viewport is restored
in a `finally` path, including when measurement or screenshot capture fails.
The inventory records criterion 1.3.4 as partial and retains manual review.

The `hover_focus_content` scenario extends this analyzer for WCAG 1.4.13. It
samples up to four visible likely triggers (links, controls, titled or
ARIA-described elements, and common tooltip/data-toggle hooks) without
activating them. For each candidate it compares bounded visible-DOM snapshots
before and after pointer hover and focus, then records newly revealed content,
trigger/content selectors and geometry, viewport dimensions, role, position,
z-index, and an opaque text signature. It samples whether pointer entry keeps
hover content visible, whether Escape dismisses it, whether focus-revealed
content remains after blur, and whether the content rectangle overlaps other
text or controls. One viewport-sized screenshot is captured while the first
revealed state is still visible when screenshot storage is available.

Every discovered reveal is `needs_review`, not a confirmed WCAG failure:
rectangle intersections do not prove that content is obscured, and automation
cannot determine applicability, equivalent information, or all exceptions.
When no reveal is detected, `no_violation_detected` applies only to the sampled
states, not to the criterion as a whole. Candidate discovery is bounded;
custom JavaScript triggers outside the selector set, CSS pseudo-elements,
native browser tooltips, delayed content, and states requiring activation are
not reliably detected. Escape behavior and focus/hover persistence are sampled
once and do not exhaustively cover browser or assistive-technology behavior.
The pointer is moved outside the page and the original focused element is
restored in cleanup where possible; no control is clicked or activated.

For a three-viewport scan, the five always-run probes can add at most fifteen
scenario screenshots (one orientation, one text-enlargement, one text-spacing,
one 1.4.13 hover/focus, and one 320px image per viewport).
The conditional 256px-height probe can add at most three more, only where it
was actually run and produced findings. Pages without suspicious findings
add none. The 18 existing local PNGs measured for this change averaged 187,456
bytes (~183 KiB); at that observed average, fifteen additional images are about
2.81 MB and the eighteen-image upper bound is about 3.37 MB. These are estimates,
not a guaranteed image size. Each screenshot adds one viewport-sized PNG
capture and storage write. Existing geometry scenarios wait for two animation
frames after applying their override or viewport change; the interaction probe
also performs bounded pointer, focus, and Escape actions with settling waits,
and orientation checks wait for the viewport layout to settle in each
orientation, so added runtime depends on the number of interactions and
orientation transitions. These are not measured wall-clock guarantees. No
extra browser navigation or full-page rendering is performed.

Orientation fixtures validate the 1.3.4 scenario:

| Fixture | Observable result | Expected classification |
|---|---|---|
| [orientation_flexible.html](../tests/fixtures/orientation_flexible.html) | Responsive layout changes between portrait and landscape while sampled text and controls remain present. | `no_violation_detected` for the bounded comparison only. |
| [orientation_restricted.html](../tests/fixtures/orientation_restricted.html) | Orientation-specific CSS hides a control in each orientation and presents separate controls. | `needs_review`; equivalence and whether the restriction is essential require human evaluation. |

Hover/focus fixtures validate the 1.4.13 scenario independently:

| Fixture | Observable result | Expected classification |
|---|---|---|
| [hover_focus_compliant.html](../tests/fixtures/hover_focus_compliant.html) | A tooltip is revealed on hover and focus, remains visible when the pointer enters it, and can be dismissed with Escape. | `needs_review` with observed behavior; manual review is still required. |
| [hover_focus_not_hoverable.html](../tests/fixtures/hover_focus_not_hoverable.html) | A tooltip with `pointer-events: none` disappears when the pointer leaves its trigger. | `needs_review`; pointer-entry behavior is evidence, not a standalone conformance conclusion. |
| [hover_focus_undismissable.html](../tests/fixtures/hover_focus_undismissable.html) | Focus reveals a fixed dialog-like panel overlapping underlying content; Escape does not dismiss it. | `needs_review`; overlap is geometric and must be confirmed by a reviewer. |
| [hover_focus_style_only.html](../tests/fixtures/hover_focus_style_only.html) | Hover and focus change button styling without revealing additional DOM content. | `no_violation_detected` for the bounded sampled states only. |

Non-text contrast fixtures exercise the supplemental `accessibility_scan` probe:

| Fixture | Observable result | Expected classification |
|---|---|---|
| [non_text_contrast.html](../tests/fixtures/non_text_contrast.html) | Includes a low-contrast CSS button boundary/fill and SVG shape, high-contrast counterparts, a hidden control, plus an image and canvas that are not pixel-sampled. | Low solid-color candidates are `needs_review`; high-contrast and hidden controls are not reported as low contrast. Image/canvas remain for manual review. |
| [non_text_contrast_adequate.html](../tests/fixtures/non_text_contrast_adequate.html) | A high-contrast CSS control and SVG shape are sampled. | No low-ratio candidates for these samples; overall result remains `partial`, not a pass. |

Text-spacing fixtures validate the `text_spacing` scenario independently of
the 200% resize and 320 CSS-pixel reflow scenarios:

| Fixture | Observable result | Expected classification |
|---|---|---|
| [text_spacing_usable.html](../tests/fixtures/text_spacing_usable.html) | Flexible paragraphs and a control remain within their containers under the prescribed overrides. | `no_violation_detected` for the bounded probe. |
| [text_spacing_clipped.html](../tests/fixtures/text_spacing_clipped.html) | A two-line paragraph in a fixed-height clipped box overflows after line height grows. | `needs_review`; actual text loss is not inferred. |
| [text_spacing_overlap.html](../tests/fixtures/text_spacing_overlap.html) | Absolute-positioned text blocks gain rectangle overlap after line-height changes. | `needs_review`; rectangle intersection is not proof of obscured content. |
| [text_spacing_control.html](../tests/fixtures/text_spacing_control.html) | A fixed-height button label clips after line height changes. | `needs_review`; keyboard and assistive-technology operation are not inferred. |
| [text_spacing_obscured_control.html](../tests/fixtures/text_spacing_obscured_control.html) | Paragraph spacing shifts a button beneath a fixed overlay, increasing intercepted interior hit-test samples. | `needs_review`; the interaction impact requires human review. |
| [text_spacing_scrollable.html](../tests/fixtures/text_spacing_scrollable.html) | A long inline text string grows inside a horizontal scroll container. | `needs_review`, not a confirmed failure; the scroll container is explicitly identified. |

The checked-in text-reflow fixtures have these observed behaviors and test
expectations:

| Fixture | HTML/CSS behavior and observable result | Expected classification | Criterion | Deterministic |
|---|---|---|---|---|
| [text_reflow_usable.html](../tests/fixtures/text_reflow_usable.html) | A wrapping paragraph grows without clipped text after the font-size override. | `no_violation_detected` for the 200% probe. | 1.4.4 | Yes |
| [text_reflow_clipped.html](../tests/fixtures/text_reflow_clipped.html) | A fixed-height paragraph has `overflow-y: hidden`; its measured scroll height exceeds its client height after enlargement. The fixture has no disclosure, but the analyzer does not establish that text is unavailable. | `needs_review`, never a confirmed violation. | 1.4.4 | Yes |
| [text_reflow_review.html](../tests/fixtures/text_reflow_review.html) | An ellipsized link has a full accessible name, a clipped preview has a working `<details>` disclosure, and a nested `1.25em` span is clipped after its computed size is doubled. | `needs_review` for each geometry signal; text availability is not inferred. | 1.4.4 | Yes |
| [text_reflow_overlap.html](../tests/fixtures/text_reflow_overlap.html) | Absolute-positioned link boxes gain geometric overlap from the enlarged font and bottom padding, while their short glyph strings remain visually separated. | `needs_review`; rectangle intersection alone does not establish obscuration. | 1.4.4 | Yes |
| [text_reflow_dynamic.html](../tests/fixtures/text_reflow_dynamic.html) | A paragraph is inserted 100 ms after navigation; the test waits 300 ms before the baseline measurement. The sampled paragraph is present. | `no_violation_detected` for the measured 200% and 320 px states; later dynamic states are not evaluated. | 1.4.4, 1.4.10 | Yes, with the test's explicit wait |
| [text_reflow_wide.html](../tests/fixtures/text_reflow_wide.html) | A 700 px main region and its paragraph extend beyond the 320 CSS px viewport, producing document and element overflow. | `needs_review`; page overflow is not itself a violation. | 1.4.10 | Yes |
| [text_reflow_unbreakable.html](../tests/fixtures/text_reflow_unbreakable.html) | A `white-space: nowrap` string extends past the 320 CSS px viewport. | `needs_review`. | 1.4.10 | Yes |
| [text_reflow_table.html](../tests/fixtures/text_reflow_table.html) | A 700 px data table sits in an `overflow-x: auto` wrapper; table cells remain in a potentially two-dimensional region. The test also measures a 256 CSS px height at the captured width. | `needs_review`, not an assumed exception or violation; the height probe completes. | 1.4.10 | Yes |
| [text_reflow_responsive.html](../tests/fixtures/text_reflow_responsive.html) | A media query hides desktop-specific instructions and displays different mobile-specific instructions at 320 CSS px. | `needs_review` for the baseline text that disappears; equivalent meaning is not determined. | 1.4.10 | Yes |

These fixtures prove only their stated browser observations and bounded
classifications. They do not prove criterion conformance or that a potential
two-dimensional exception is applicable.

Automated checks cannot decide whether alternative text is meaningful, whether
content order or instructions make sense, whether all keyboard flows work, or
whether media and dynamic interactions are accessible. Actual browser zoom,
live media, assistive-technology output, and cross-page criteria are not evaluated
by this scan. A clean or empty violations collection is not evidence of WCAG
conformance. This use of axe-core is locally hosted and makes no service request
to Deque; however, the scanned site is untrusted content running in Chromium, and
the tool is not a substitute for expert/manual evaluation.

Each scan launches an isolated Chromium browser context, records browser errors,
waits for `DOMContentLoaded` with a 15-second default timeout, then waits 1.5 seconds
before collecting page dimensions and an initial-viewport screenshot. Configure these
intervals with `WEBABLE_NAVIGATION_TIMEOUT_MS` and `WEBABLE_SETTLING_PERIOD_MS`.
The settling period is a practical baseline for allowing common delayed updates; it is
not a guarantee that every dynamic page has finished loading.

Screenshots are stored locally under the ignored `output/screenshots/` directory.
The API returns only a relative screenshot reference; the storage interface can be
replaced with object storage later. Do not serve the output directory publicly.

URL checks reject non-HTTP(S) URLs, embedded credentials, local/internal hostnames,
and DNS results that are not public IP addresses. The same check runs before
navigation and for each browser request, including redirects. This is a useful
development safeguard, **not a public-deployment security guarantee**: Chromium
performs its own DNS resolution after the check, so DNS rebinding/time-of-check
versus time-of-use attacks are not fully prevented. Functional UX `HEAD` checks
validate every redirect hop, but the request client resolves the destination
again after validation, so the same network-level limitation applies. Deployments exposed to
untrusted users still need network-level egress controls or a validating proxy that
pins approved destinations and blocks private/internal address ranges. DNS lookups
also run in the application process. Browser HTTP interception does not validate
WebSocket connections or other browser-managed network paths. This implementation
has no authentication or multi-tenant screenshot isolation.

Evidence intentionally excludes HTML documents, response bodies, cookies, and
headers. URL fragments and embedded URL credentials are removed from recorded URLs,
and common credential-like query parameter values are redacted. Other query values
are preserved because they may be required to reproduce the requested page.

## Hybrid accessibility evaluation foundation

The browser UI is served from the same API origin at `/` (for example,
`http://localhost:8000/` after starting the server). It is an integrated view of
the capture workflow, not a separate questionnaire submission path. Users enter
the audit URL, representative public URLs, journey descriptions, feature
presence, and optional context before starting the capture. Relevant follow-up
questions appear immediately for owner-selected features and are updated after
the browser returns feature discoveries. Answer values and explanations stay
in page state and are resubmitted with each audit update; answered follow-ups
are not shown again as pending questions, while their owner-reported evidence
remains visible in the results.

The UI presents owner-reported information and browser-observed information in
separate panels with a compact criterion evidence summary instead of 55 outcome
cards. Browser findings are labeled as evidence rather than criterion
conclusions. Conflicts between an owner-declared absent feature and a browser
candidate are shown for review and trigger a discovery follow-up even if an
owner answered a related criterion question negatively. Owner statements are
unverified context, never proof of compliance. Criteria requiring further
evaluation are never presented as WCAG failures or passes. The UI does not
request passwords and explains that protected pages require a separately
authorized review; the current capture flow does not support entering
credentials for protected pages.

`GET /accessibility/questionnaire` returns the initial scope questions, supported
feature identifiers, and a privacy notice. `POST /captures` accepts an optional
`accessibility_context` object alongside the URL:

- `representative_page_urls` identifies pages owners consider representative;
- `user_journeys` records task names, descriptions, and relevant public page URLs;
- `feature_presence` records owner-declared feature presence (`true`, `false`, or
  `null` for unknown);
- `answers` stores structured answers by questionnaire question ID and may
  associate answers with public page URLs;
- `free_text` is an optional, bounded context field.

Example request context:

```json
{
  "representative_page_urls": ["https://example.org/contact"],
  "user_journeys": [
    {
      "name": "Submit a contact form",
      "page_urls": ["https://example.org/contact"]
    }
  ],
  "feature_presence": {"forms": true, "authentication": false},
  "feature_inventory_completed": true,
  "answers": [
    {
      "question_id": "forms.error_identification",
      "answer": "not_sure",
      "page_urls": ["https://example.org/contact"]
    }
  ]
}
```

Only public absolute HTTP(S) context URLs without credentials, query strings, or
fragments are accepted. Text fields are bounded, reject common credential/email
patterns, and explicitly instruct users not to submit passwords, credentials,
personal or customer data, access tokens, or secrets. These checks are safeguards,
not a guarantee that every sensitive value can be detected. Do not use ordinary
questionnaire fields for credentials or personal data.

Questionnaire follow-ups are conditional on owner-declared features and read-only
browser feature discovery. All 55 criteria map to questions, with criterion-
specific prompts for the 26 manual-evaluation criteria. Questions accept Yes,
No, Not sure, or Not applicable, with optional explanation and public page URLs.
The browser probe looks for a bounded set of candidates
such as forms, password inputs, media, CSS animations, custom roles, language
attributes, and images/graphics. It is intentionally a feature router: presence
does not prove a WCAG failure, and absence does not prove a feature is absent.
If browser evidence finds a feature the owner declared absent, the hybrid report
records a conflict and returns the relevant questions for follow-up. Discovery is
limited to 1,000 candidates per selector and reports partial coverage when
truncated. Representative URLs and journeys are recorded as context; this
foundation does not automatically crawl those additional pages or execute the
described journeys.

The response includes `hybrid_evaluation.criteria`, a criterion-indexed collection
with separate `owner_reported` and `browser_observed` evidence.
The initial adapter carries exact-tagged axe rule outcomes, keyboard/focus checks,
text/reflow scenarios, non-text contrast and target-size probes, plus feature
discovery observations. Each item retains its analyzer, viewport, and bounded
summary/count; a rule association or empty finding set is not a criterion-level
pass. Additional analyzers can add criterion-indexed evidence through the same
source model without defining a separate questionnaire.
Statuses distinguish `owner_reported`, `browser_observed`,
`manual_review_needed`, and `not_evaluated`. Contradictory
feature declarations are surfaced in `conflicts`; neither source silently
overwrites the other. `compliance_conclusion` remains unset, owner answers carry
`verified: false`, and criteria without evidence are `not_evaluated`, never
implicitly passed.

The capture response also exposes a top-level `scoring` summary. Its versioned
registry is centralized in `app/analyzers/scoring.py`; each criterion includes
its normalized status, configured weight, viewport results, evidence references,
confidence, and limitations. Evidence from multiple viewports is aggregated at
the criterion level while retaining viewport-specific results. `fail` takes
precedence over other viewport outcomes; missing or inconclusive evidence is
never treated as a pass; observed console errors require review rather than being
treated as definitive failures. Unsupported capabilities (including forms,
executed journeys, and visual/UX quality) are identified but excluded from scoring.

Dimension scores use only conclusive `pass`/`fail` criteria, and are withheld
when their evidence coverage is below 40%. The weighted overall score is
reported as `partial_audit_score`, since visual/UX quality is not implemented;
it is withheld when overall coverage is below 40%. The score and coverage labels
are summaries of the configured checks, not WCAG conformance, a severity ranking,
or a measure of total website quality. Existing per-viewport analyzer results
remain in the response as the source evidence, and `scoring.limitations`
describes the bounds of interpretation.

The capture API is currently stateless: questionnaire answers are scoped to the
request/response and are not durably stored across audits. Deployments should add
authenticated, access-controlled persistence and an explicit retention policy
before retaining owner context. The questionnaire maps contextual questions to
all criteria but is not a substitute for human, assistive-technology, and content
review.

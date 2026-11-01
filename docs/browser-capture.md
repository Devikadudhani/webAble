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

Each successful viewport also includes a separate `keyboard_focus_audit`. It
samples visible interactive candidates with at most 20 `Tab` and 2
`Shift+Tab` key presses, recording bounded selectors, role/name, focus state,
computed-style indicator evidence, and hit-test evidence for possible
obscuration. It never presses Enter or Space or clicks controls. The audit
temporarily blocks network requests during key interaction and runs in the
disposable isolated capture context, which is closed after all audits. Pages can
opt out with `data-webable-keyboard-audit="unsafe"` on the root element.

Each keyboard check has its own `pass`, `fail`, `needs_review`, `not_tested`,
or `error` status and remains separate from axe results. The current heuristic
does not emit `pass` or `fail`: observed sequences and possible style/occlusion
signals are classified `needs_review`, while absent candidates are
`not_tested`. This avoids treating a bounded observation as proof of
conformance or failure. A suspected trap, missing focus style, skipped
candidate, or possible overlay is sent for review. A sampled Tab order does
not establish correct semantic focus order, keyboard operation of every widget,
indicator contrast/size, or complete non-obscuration. The hit test samples only
a few points; computed-style comparison cannot discover every focus indicator
technique. Focus/blur handlers can have other page-defined effects, so network
interception and blocking service workers are not a guarantee that arbitrary
script is side-effect-free.

The candidate list is a heuristic snapshot, not the browser's authoritative
sequential focus order. Per-scan evidence identifies detected positive
`tabindex` elements, treats each named radio group as one expected sequential
tab stop, reports open shadow-root hosts and frames, identifies candidates
appearing after the initial snapshot, and marks focused targets absent from the
initial snapshot. These are explicit limitations, not proof that a candidate
was unreachable. Closed shadow roots, inaccessible frame
contents, and custom widgets may remain undiscovered. Observed elements are
not treated as complete merely because their count matches the snapshot. Tab
and Shift+Tab traversal stops on a repeat, the action limit, or an observed
end; the repeat may represent normal wrapping rather than a trap. The audit's
outer and per-action timeouts return explicit error or review states;
cancellation unwinds the temporary route handler and the capture runner closes
the page, context, and browser in its `finally` cleanup.

The inventory distinguishes existing axe mappings from this WebAble keyboard
probe. axe-core 4.14.0 has enabled, selected rules tagged to 2.1.1, but none for
2.1.2, 2.4.3, 2.4.7, or 2.4.11. The probe adds bounded partial evidence for
those criteria without replacing contextual evaluation. WCAG 2.2 criterion
2.4.13 Focus Appearance is Level AAA (not AA) and remains out of scope; this
audit does not measure its perimeter-area or contrast requirements.

Each successful viewport also includes `text_reflow_audit` with separately
identified baseline, 200% text-enlargement, 320 CSS-pixel reflow, and browser
zoom scenarios. The text scenario temporarily doubles each discovered visible
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
screenshot is captured only when the 200% text, 320 CSS-pixel reflow, or
executed 256 CSS-pixel-height measurement produces findings. Each qualifying
scenario gets at most one viewport-sized PNG, shared by its scenario and all
its findings; no image is generated for a clean or untested scenario.

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

For a three-viewport scan, the two always-run probes can add at most six
scenario screenshots (one text-enlargement and one 320px image per viewport).
The conditional 256px-height probe can add at most three more, only where it
was actually run and produced findings. Pages without suspicious findings
add none. The 18 existing local PNGs measured for this change averaged 187,456
bytes (~183 KiB); at that observed average, six additional images are about
1.12 MB and the nine-image upper bound is about 1.69 MB. These are estimates,
not a guaranteed image size. Each screenshot adds one viewport-sized PNG
capture and storage write. Each measured scenario also waits for two animation
frames after applying its override or viewport change, whether or not a
screenshot is ultimately needed: nominally about 33 ms per scenario at 60 Hz,
or about 200 ms for the six unconditional probes and 300 ms if all three
conditional height probes also run. These are frame-rate estimates, not
measured wall-clock guarantees. No extra browser navigation or full-page
rendering is performed.

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

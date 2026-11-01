# WCAG 2.2 Level A/AA Coverage Inventory

**Inventory version:** 2.0  
**Standards baseline:** [WCAG 2.2 W3C Recommendation](https://www.w3.org/TR/WCAG22/)  
**Engine:** axe-core 4.14.0 (pinned package metadata)  
**In-scope criteria:** 55 (all A and AA criteria; AAA excluded; obsolete 4.1.1 excluded)  
**Criteria with at least one enabled, scanner-selected exact WCAG criterion tag:** 20 of 55
**Criteria mapped to initial or conditional questionnaire questions:** 55 of 55 (manual-evaluation criteria: 26 of 26)

This inventory is evidence of rule associations and current checks, not a WCAG conformance statement. A WCAG tag on an axe rule is an association published in the rule metadata, not proof that the rule covers the whole success criterion. A rule result applies only to its documented test conditions and reported nodes.

## Classification definitions

- `automated`: an implemented check fully evaluates the success criterion within its declared scope. None are assigned: no current axe tag mapping establishes full criterion coverage.
- `partial`: one or more bounded automated probes or enabled rules selected by the current scan provide evidence for part of the criterion; the checks cover only their documented test conditions.
- `manual_evaluation_required`: no enabled selected axe rule carries the exact criterion tag and representative human, assistive-technology, content, media, or interaction review is necessary.
- `not_implemented`: no enabled selected exact-tag check exists; a bounded technical or interaction check may be developed, but none is implemented.

A criterion may need manual review even when classified `partial`. `automated_check_exists` includes bounded WebAble keyboard/focus, orientation, non-text contrast, hover/focus-content, and text/reflow probes when listed, while `axe_check_exists` records exact-tagged axe coverage separately. Neither means the whole criterion is automated. The scanner runs with these exact configuration tags: `wcag2a`, `wcag2aa`, `wcag21a`, `wcag21aa`, `wcag22aa`. Effective rule selection requires both package `enabled: true` and a matching runOnly tag.

## Summary

| Classification | Count |
|---|---:|
| `automated` | 0 |
| `partial` | 29 |
| `manual_evaluation_required` | 26 |
| `not_implemented` | 0 |

The 55 is the number of applicable WCAG 2.2 A/AA success criteria, not a scanner coverage percentage. The mapped-criterion count measures enabled, configured axe rules that carry the exact criterion tag; it is not a conformance rate or completeness measure.

## Criterion inventory

The checked-in criterion baseline is `tests/fixtures/wcag22_criteria_source.json`, independently transcribed from the normative Recommendation. Axe rule IDs, full tags, enabled status, descriptions, and help links below are generated from the installed pinned package metadata. To regenerate after a deliberate baseline or axe update, run `python scripts/generate_wcag22_coverage_inventory.py` after `npm ci`.

### 1.1.1 — Non-text Content

- **Level / principle:** A / Perceivable
- **Intent:** Provide text alternatives for non-text content, except where an exception applies.
- **Coverage:** `partial`
- **Questionnaire question IDs:** `visual.images_of_text`
- **Automated check exists:** true
- **Axe check exists:** true
- **WebAble keyboard/focus check exists:** false
- **WebAble text/reflow check exists:** false
- **WebAble text-spacing check exists:** false
- **WebAble orientation check exists:** false
- **WebAble non-text contrast check exists:** false
- **WebAble hover/focus-content check exists:** false
- **WebAble target-size check exists:** false
- **Exact criterion tag:** `wcag111`
- **Manual / keyboard / interaction / assistive-technology testing needed:** true / false / false / true
- **Normative criterion:** [1.1.1 Non-text Content](https://www.w3.org/TR/WCAG22/#non-text-content)
- **Understanding:** [Understanding 1.1.1](https://www.w3.org/WAI/WCAG22/Understanding/non-text-content.html)
- **Associated axe rules** (all exact WCAG-tagged rules in package metadata):
  - [`aria-meter-name`](https://dequeuniversity.com/rules/axe/4.14/aria-meter-name?application=axeAPI) — package enabled: `true`; scanner: `selected`; effective: `true`; tags: `cat.aria`, `wcag2a`, `wcag111`, `EN-301-549`, `EN-9.1.1.1`, `RGAAv4`, `RGAA-11.1.1`
  - [`aria-progressbar-name`](https://dequeuniversity.com/rules/axe/4.14/aria-progressbar-name?application=axeAPI) — package enabled: `true`; scanner: `selected`; effective: `true`; tags: `cat.aria`, `wcag2a`, `wcag111`, `EN-301-549`, `EN-9.1.1.1`, `RGAAv4`, `RGAA-11.1.1`
  - [`image-alt`](https://dequeuniversity.com/rules/axe/4.14/image-alt?application=axeAPI) — package enabled: `true`; scanner: `selected`; effective: `true`; tags: `cat.text-alternatives`, `wcag2a`, `wcag111`, `section508`, `section508.22.a`, `TTv5`, `TT7.a`, `TT7.b`, `EN-301-549`, `EN-9.1.1.1`, `ACT`, `RGAAv4`, `RGAA-1.1.1`
  - [`input-image-alt`](https://dequeuniversity.com/rules/axe/4.14/input-image-alt?application=axeAPI) — package enabled: `true`; scanner: `selected`; effective: `true`; tags: `cat.text-alternatives`, `wcag2a`, `wcag111`, `wcag412`, `section508`, `section508.22.a`, `TTv5`, `TT7.a`, `EN-301-549`, `EN-9.1.1.1`, `EN-9.4.1.2`, `ACT`, `RGAAv4`, `RGAA-1.1.3`
  - [`object-alt`](https://dequeuniversity.com/rules/axe/4.14/object-alt?application=axeAPI) — package enabled: `true`; scanner: `selected`; effective: `true`; tags: `cat.text-alternatives`, `wcag2a`, `wcag111`, `section508`, `section508.22.a`, `EN-301-549`, `EN-9.1.1.1`, `RGAAv4`, `RGAA-1.1.6`
  - [`role-img-alt`](https://dequeuniversity.com/rules/axe/4.14/role-img-alt?application=axeAPI) — package enabled: `true`; scanner: `selected`; effective: `true`; tags: `cat.text-alternatives`, `wcag2a`, `wcag111`, `section508`, `section508.22.a`, `TTv5`, `TT7.a`, `EN-301-549`, `EN-9.1.1.1`, `ACT`, `RGAAv4`, `RGAA-1.1.1`
  - [`svg-img-alt`](https://dequeuniversity.com/rules/axe/4.14/svg-img-alt?application=axeAPI) — package enabled: `true`; scanner: `selected`; effective: `true`; tags: `cat.text-alternatives`, `wcag2a`, `wcag111`, `section508`, `section508.22.a`, `TTv5`, `TT7.a`, `EN-301-549`, `EN-9.1.1.1`, `ACT`, `RGAAv4`, `RGAA-1.1.5`
- **Implemented failure patterns (rule-description scope, not exhaustive):**
  - `aria-meter-name`: Ensure every ARIA meter node has an accessible name ([rule help](https://dequeuniversity.com/rules/axe/4.14/aria-meter-name?application=axeAPI))
  - `aria-progressbar-name`: Ensure every ARIA progressbar node has an accessible name ([rule help](https://dequeuniversity.com/rules/axe/4.14/aria-progressbar-name?application=axeAPI))
  - `image-alt`: Ensure <img> elements have alternative text or a role of none or presentation ([rule help](https://dequeuniversity.com/rules/axe/4.14/image-alt?application=axeAPI))
  - `input-image-alt`: Ensure <input type="image"> elements have alternative text ([rule help](https://dequeuniversity.com/rules/axe/4.14/input-image-alt?application=axeAPI))
  - `object-alt`: Ensure <object> elements have alternative text ([rule help](https://dequeuniversity.com/rules/axe/4.14/object-alt?application=axeAPI))
  - `role-img-alt`: Ensure [role="img"] and [role="image"] elements have alternative text ([rule help](https://dequeuniversity.com/rules/axe/4.14/role-img-alt?application=axeAPI))
  - `svg-img-alt`: Ensure <svg> elements with an img, image, graphics-document or graphics-symbol role have accessible text ([rule help](https://dequeuniversity.com/rules/axe/4.14/svg-img-alt?application=axeAPI))
- **Limitations:**
  - A WCAG tag records the axe rule author's criterion association; it is not evidence that the rule covers the full success criterion.
  - The scanner records rule outcomes only when the rule runs and reports them. An absent result does not establish that the criterion passed.
- **Relevant existing tests:** `tests/test_capture.py::test_accessibility_scan_preserves_axe_results_and_specific_evidence`
- **Outstanding gaps / next step:**
  - Validate the implemented checks with criterion-specific counterexamples against the criterion's Understanding guidance; retain manual review for aspects beyond their bounded scope.
  - No result from this scan may be described as WCAG conformance.
- **Evidence links:** [1](https://www.w3.org/TR/WCAG22/#non-text-content), [2](https://www.w3.org/WAI/WCAG22/Understanding/non-text-content.html), [3](https://dequeuniversity.com/rules/axe/4.14/aria-meter-name?application=axeAPI), [4](https://dequeuniversity.com/rules/axe/4.14/aria-progressbar-name?application=axeAPI), [5](https://dequeuniversity.com/rules/axe/4.14/image-alt?application=axeAPI), [6](https://dequeuniversity.com/rules/axe/4.14/input-image-alt?application=axeAPI), [7](https://dequeuniversity.com/rules/axe/4.14/object-alt?application=axeAPI), [8](https://dequeuniversity.com/rules/axe/4.14/role-img-alt?application=axeAPI), [9](https://dequeuniversity.com/rules/axe/4.14/svg-img-alt?application=axeAPI)

### 1.2.1 — Audio-only and Video-only (Prerecorded)

- **Level / principle:** A / Perceivable
- **Intent:** Provide an equivalent alternative for prerecorded audio-only and video-only content.
- **Coverage:** `manual_evaluation_required`
- **Questionnaire question IDs:** `media.prerecorded_alternatives`
- **Automated check exists:** false
- **Axe check exists:** false
- **WebAble keyboard/focus check exists:** false
- **WebAble text/reflow check exists:** false
- **WebAble text-spacing check exists:** false
- **WebAble orientation check exists:** false
- **WebAble non-text contrast check exists:** false
- **WebAble hover/focus-content check exists:** false
- **WebAble target-size check exists:** false
- **Exact criterion tag:** `wcag121`
- **Manual / keyboard / interaction / assistive-technology testing needed:** true / false / false / false
- **Normative criterion:** [1.2.1 Audio-only and Video-only (Prerecorded)](https://www.w3.org/TR/WCAG22/#audio-only-and-video-only-prerecorded)
- **Understanding:** [Understanding 1.2.1](https://www.w3.org/WAI/WCAG22/Understanding/audio-only-and-video-only-prerecorded.html)
- **Associated axe rules** (all exact WCAG-tagged rules in package metadata):
  - [`audio-caption`](https://dequeuniversity.com/rules/axe/4.14/audio-caption?application=axeAPI) — package enabled: `false`; scanner: `selected`; effective: `false`; tags: `cat.time-and-media`, `wcag2a`, `wcag121`, `EN-301-549`, `EN-9.1.2.1`, `section508`, `section508.22.a`, `deprecated`
- **Implemented failure patterns:** none mapped by an enabled, selected rule carrying this criterion's exact tag.
- **Limitations:**
  - No enabled axe rule selected by the current scanner carries this criterion's exact WCAG tag.
  - A WCAG tag records the axe rule author's criterion association; it is not evidence that the rule covers the full success criterion.
  - The scanner records rule outcomes only when the rule runs and reports them. An absent result does not establish that the criterion passed.
- **Relevant existing tests:** No focused criterion-specific fixture assertion currently exists.
- **Outstanding gaps / next step:**
  - Evaluate representative content and states with a trained reviewer and, where applicable, assistive technology; define bounded automated support only after validating it against WCAG guidance.
  - No result from this scan may be described as WCAG conformance.
- **Evidence links:** [1](https://www.w3.org/TR/WCAG22/#audio-only-and-video-only-prerecorded), [2](https://www.w3.org/WAI/WCAG22/Understanding/audio-only-and-video-only-prerecorded.html)

### 1.2.2 — Captions (Prerecorded)

- **Level / principle:** A / Perceivable
- **Intent:** Provide captions for prerecorded synchronized audio and video content.
- **Coverage:** `partial`
- **Questionnaire question IDs:** `media.prerecorded_captions`
- **Automated check exists:** true
- **Axe check exists:** true
- **WebAble keyboard/focus check exists:** false
- **WebAble text/reflow check exists:** false
- **WebAble text-spacing check exists:** false
- **WebAble orientation check exists:** false
- **WebAble non-text contrast check exists:** false
- **WebAble hover/focus-content check exists:** false
- **WebAble target-size check exists:** false
- **Exact criterion tag:** `wcag122`
- **Manual / keyboard / interaction / assistive-technology testing needed:** true / false / true / false
- **Normative criterion:** [1.2.2 Captions (Prerecorded)](https://www.w3.org/TR/WCAG22/#captions-prerecorded)
- **Understanding:** [Understanding 1.2.2](https://www.w3.org/WAI/WCAG22/Understanding/captions-prerecorded.html)
- **Associated axe rules** (all exact WCAG-tagged rules in package metadata):
  - [`video-caption`](https://dequeuniversity.com/rules/axe/4.14/video-caption?application=axeAPI) — package enabled: `true`; scanner: `selected`; effective: `true`; tags: `cat.text-alternatives`, `wcag2a`, `wcag122`, `section508`, `section508.22.a`, `TTv5`, `TT17.a`, `EN-301-549`, `EN-9.1.2.2`, `RGAAv4`, `RGAA-4.3.1`
- **Implemented failure patterns (rule-description scope, not exhaustive):**
  - `video-caption`: Ensure <video> elements have captions ([rule help](https://dequeuniversity.com/rules/axe/4.14/video-caption?application=axeAPI))
- **Limitations:**
  - A WCAG tag records the axe rule author's criterion association; it is not evidence that the rule covers the full success criterion.
  - The scanner records rule outcomes only when the rule runs and reports them. An absent result does not establish that the criterion passed.
- **Relevant existing tests:** No focused criterion-specific fixture assertion currently exists.
- **Outstanding gaps / next step:**
  - Validate the implemented checks with criterion-specific counterexamples against the criterion's Understanding guidance; retain manual review for aspects beyond their bounded scope.
  - No result from this scan may be described as WCAG conformance.
- **Evidence links:** [1](https://www.w3.org/TR/WCAG22/#captions-prerecorded), [2](https://www.w3.org/WAI/WCAG22/Understanding/captions-prerecorded.html), [3](https://dequeuniversity.com/rules/axe/4.14/video-caption?application=axeAPI)

### 1.2.3 — Audio Description or Media Alternative (Prerecorded)

- **Level / principle:** A / Perceivable
- **Intent:** Provide audio description or a complete text alternative for prerecorded synchronized media.
- **Coverage:** `manual_evaluation_required`
- **Questionnaire question IDs:** `media.prerecorded_audio_description_or_alternative`
- **Automated check exists:** false
- **Axe check exists:** false
- **WebAble keyboard/focus check exists:** false
- **WebAble text/reflow check exists:** false
- **WebAble text-spacing check exists:** false
- **WebAble orientation check exists:** false
- **WebAble non-text contrast check exists:** false
- **WebAble hover/focus-content check exists:** false
- **WebAble target-size check exists:** false
- **Exact criterion tag:** `wcag123`
- **Manual / keyboard / interaction / assistive-technology testing needed:** true / false / false / false
- **Normative criterion:** [1.2.3 Audio Description or Media Alternative (Prerecorded)](https://www.w3.org/TR/WCAG22/#audio-description-or-media-alternative-prerecorded)
- **Understanding:** [Understanding 1.2.3](https://www.w3.org/WAI/WCAG22/Understanding/audio-description-or-media-alternative-prerecorded.html)
- **Associated axe rules:** none with this criterion tag in axe-core 4.14.0 metadata.
- **Implemented failure patterns:** none mapped by an enabled, selected rule carrying this criterion's exact tag.
- **Limitations:**
  - No enabled axe rule selected by the current scanner carries this criterion's exact WCAG tag.
  - A WCAG tag records the axe rule author's criterion association; it is not evidence that the rule covers the full success criterion.
  - The scanner records rule outcomes only when the rule runs and reports them. An absent result does not establish that the criterion passed.
- **Relevant existing tests:** No focused criterion-specific fixture assertion currently exists.
- **Outstanding gaps / next step:**
  - Evaluate representative content and states with a trained reviewer and, where applicable, assistive technology; define bounded automated support only after validating it against WCAG guidance.
  - No result from this scan may be described as WCAG conformance.
- **Evidence links:** [1](https://www.w3.org/TR/WCAG22/#audio-description-or-media-alternative-prerecorded), [2](https://www.w3.org/WAI/WCAG22/Understanding/audio-description-or-media-alternative-prerecorded.html)

### 1.2.4 — Captions (Live)

- **Level / principle:** AA / Perceivable
- **Intent:** Provide captions for live synchronized audio and video content.
- **Coverage:** `manual_evaluation_required`
- **Questionnaire question IDs:** `media.live_captions`
- **Automated check exists:** false
- **Axe check exists:** false
- **WebAble keyboard/focus check exists:** false
- **WebAble text/reflow check exists:** false
- **WebAble text-spacing check exists:** false
- **WebAble orientation check exists:** false
- **WebAble non-text contrast check exists:** false
- **WebAble hover/focus-content check exists:** false
- **WebAble target-size check exists:** false
- **Exact criterion tag:** `wcag124`
- **Manual / keyboard / interaction / assistive-technology testing needed:** true / false / true / false
- **Normative criterion:** [1.2.4 Captions (Live)](https://www.w3.org/TR/WCAG22/#captions-live)
- **Understanding:** [Understanding 1.2.4](https://www.w3.org/WAI/WCAG22/Understanding/captions-live.html)
- **Associated axe rules:** none with this criterion tag in axe-core 4.14.0 metadata.
- **Implemented failure patterns:** none mapped by an enabled, selected rule carrying this criterion's exact tag.
- **Limitations:**
  - No enabled axe rule selected by the current scanner carries this criterion's exact WCAG tag.
  - A WCAG tag records the axe rule author's criterion association; it is not evidence that the rule covers the full success criterion.
  - The scanner records rule outcomes only when the rule runs and reports them. An absent result does not establish that the criterion passed.
- **Relevant existing tests:** No focused criterion-specific fixture assertion currently exists.
- **Outstanding gaps / next step:**
  - Evaluate representative content and states with a trained reviewer and, where applicable, assistive technology; define bounded automated support only after validating it against WCAG guidance.
  - No result from this scan may be described as WCAG conformance.
- **Evidence links:** [1](https://www.w3.org/TR/WCAG22/#captions-live), [2](https://www.w3.org/WAI/WCAG22/Understanding/captions-live.html)

### 1.2.5 — Audio Description (Prerecorded)

- **Level / principle:** AA / Perceivable
- **Intent:** Provide audio description for prerecorded video content.
- **Coverage:** `manual_evaluation_required`
- **Questionnaire question IDs:** `media.prerecorded_audio_description`
- **Automated check exists:** false
- **Axe check exists:** false
- **WebAble keyboard/focus check exists:** false
- **WebAble text/reflow check exists:** false
- **WebAble text-spacing check exists:** false
- **WebAble orientation check exists:** false
- **WebAble non-text contrast check exists:** false
- **WebAble hover/focus-content check exists:** false
- **WebAble target-size check exists:** false
- **Exact criterion tag:** `wcag125`
- **Manual / keyboard / interaction / assistive-technology testing needed:** true / false / false / false
- **Normative criterion:** [1.2.5 Audio Description (Prerecorded)](https://www.w3.org/TR/WCAG22/#audio-description-prerecorded)
- **Understanding:** [Understanding 1.2.5](https://www.w3.org/WAI/WCAG22/Understanding/audio-description-prerecorded.html)
- **Associated axe rules:** none with this criterion tag in axe-core 4.14.0 metadata.
- **Implemented failure patterns:** none mapped by an enabled, selected rule carrying this criterion's exact tag.
- **Limitations:**
  - No enabled axe rule selected by the current scanner carries this criterion's exact WCAG tag.
  - A WCAG tag records the axe rule author's criterion association; it is not evidence that the rule covers the full success criterion.
  - The scanner records rule outcomes only when the rule runs and reports them. An absent result does not establish that the criterion passed.
- **Relevant existing tests:** No focused criterion-specific fixture assertion currently exists.
- **Outstanding gaps / next step:**
  - Evaluate representative content and states with a trained reviewer and, where applicable, assistive technology; define bounded automated support only after validating it against WCAG guidance.
  - No result from this scan may be described as WCAG conformance.
- **Evidence links:** [1](https://www.w3.org/TR/WCAG22/#audio-description-prerecorded), [2](https://www.w3.org/WAI/WCAG22/Understanding/audio-description-prerecorded.html)

### 1.3.1 — Info and Relationships

- **Level / principle:** A / Perceivable
- **Intent:** Make information, structure, and relationships programmatically determinable or available in text.
- **Coverage:** `partial`
- **Questionnaire question IDs:** `widgets.keyboard_operation`
- **Automated check exists:** true
- **Axe check exists:** true
- **WebAble keyboard/focus check exists:** false
- **WebAble text/reflow check exists:** false
- **WebAble text-spacing check exists:** false
- **WebAble orientation check exists:** false
- **WebAble non-text contrast check exists:** false
- **WebAble hover/focus-content check exists:** false
- **WebAble target-size check exists:** false
- **Exact criterion tag:** `wcag131`
- **Manual / keyboard / interaction / assistive-technology testing needed:** true / false / false / true
- **Normative criterion:** [1.3.1 Info and Relationships](https://www.w3.org/TR/WCAG22/#info-and-relationships)
- **Understanding:** [Understanding 1.3.1](https://www.w3.org/WAI/WCAG22/Understanding/info-and-relationships.html)
- **Associated axe rules** (all exact WCAG-tagged rules in package metadata):
  - [`aria-hidden-body`](https://dequeuniversity.com/rules/axe/4.14/aria-hidden-body?application=axeAPI) — package enabled: `true`; scanner: `selected`; effective: `true`; tags: `cat.aria`, `wcag2a`, `wcag131`, `wcag412`, `EN-301-549`, `EN-9.1.3.1`, `EN-9.4.1.2`, `RGAAv4`, `RGAA-10.8.1`
  - [`aria-required-children`](https://dequeuniversity.com/rules/axe/4.14/aria-required-children?application=axeAPI) — package enabled: `true`; scanner: `selected`; effective: `true`; tags: `cat.aria`, `wcag2a`, `wcag131`, `EN-301-549`, `EN-9.1.3.1`, `RGAAv4`, `RGAA-9.3.1`
  - [`aria-required-parent`](https://dequeuniversity.com/rules/axe/4.14/aria-required-parent?application=axeAPI) — package enabled: `true`; scanner: `selected`; effective: `true`; tags: `cat.aria`, `wcag2a`, `wcag131`, `EN-301-549`, `EN-9.1.3.1`, `RGAAv4`, `RGAA-9.3.1`
  - [`definition-list`](https://dequeuniversity.com/rules/axe/4.14/definition-list?application=axeAPI) — package enabled: `true`; scanner: `selected`; effective: `true`; tags: `cat.structure`, `wcag2a`, `wcag131`, `EN-301-549`, `EN-9.1.3.1`, `RGAAv4`, `RGAA-9.3.3`
  - [`dlitem`](https://dequeuniversity.com/rules/axe/4.14/dlitem?application=axeAPI) — package enabled: `true`; scanner: `selected`; effective: `true`; tags: `cat.structure`, `wcag2a`, `wcag131`, `EN-301-549`, `EN-9.1.3.1`, `RGAAv4`, `RGAA-9.3.3`
  - [`list`](https://dequeuniversity.com/rules/axe/4.14/list?application=axeAPI) — package enabled: `true`; scanner: `selected`; effective: `true`; tags: `cat.structure`, `wcag2a`, `wcag131`, `EN-301-549`, `EN-9.1.3.1`, `RGAAv4`, `RGAA-9.3.1`
  - [`listitem`](https://dequeuniversity.com/rules/axe/4.14/listitem?application=axeAPI) — package enabled: `true`; scanner: `selected`; effective: `true`; tags: `cat.structure`, `wcag2a`, `wcag131`, `EN-301-549`, `EN-9.1.3.1`, `RGAAv4`, `RGAA-9.3.1`
  - [`p-as-heading`](https://dequeuniversity.com/rules/axe/4.14/p-as-heading?application=axeAPI) — package enabled: `false`; scanner: `selected`; effective: `false`; tags: `cat.semantics`, `wcag2a`, `wcag131`, `EN-301-549`, `EN-9.1.3.1`, `RGAAv4`, `RGAA-9.1.3`, `experimental`
  - [`table-fake-caption`](https://dequeuniversity.com/rules/axe/4.14/table-fake-caption?application=axeAPI) — package enabled: `false`; scanner: `selected`; effective: `false`; tags: `cat.tables`, `experimental`, `wcag2a`, `wcag131`, `section508`, `section508.22.g`, `EN-301-549`, `EN-9.1.3.1`, `RGAAv4`, `RGAA-5.4.1`
  - [`td-has-header`](https://dequeuniversity.com/rules/axe/4.14/td-has-header?application=axeAPI) — package enabled: `false`; scanner: `selected`; effective: `false`; tags: `cat.tables`, `experimental`, `wcag2a`, `wcag131`, `section508`, `section508.22.g`, `TTv5`, `TT14.b`, `EN-301-549`, `EN-9.1.3.1`, `RGAAv4`, `RGAA-5.7.4`
  - [`td-headers-attr`](https://dequeuniversity.com/rules/axe/4.14/td-headers-attr?application=axeAPI) — package enabled: `true`; scanner: `selected`; effective: `true`; tags: `cat.tables`, `wcag2a`, `wcag131`, `section508`, `section508.22.g`, `TTv5`, `TT14.b`, `EN-301-549`, `EN-9.1.3.1`, `RGAAv4`, `RGAA-5.7.4`
  - [`th-has-data-cells`](https://dequeuniversity.com/rules/axe/4.14/th-has-data-cells?application=axeAPI) — package enabled: `true`; scanner: `selected`; effective: `true`; tags: `cat.tables`, `wcag2a`, `wcag131`, `section508`, `section508.22.g`, `TTv5`, `TT14.b`, `EN-301-549`, `EN-9.1.3.1`, `RGAAv4`, `RGAA-5.7.1`
- **Implemented failure patterns (rule-description scope, not exhaustive):**
  - `aria-hidden-body`: Ensure aria-hidden="true" is not present on the document body. ([rule help](https://dequeuniversity.com/rules/axe/4.14/aria-hidden-body?application=axeAPI))
  - `aria-required-children`: Ensure elements with an ARIA role that require child roles contain them ([rule help](https://dequeuniversity.com/rules/axe/4.14/aria-required-children?application=axeAPI))
  - `aria-required-parent`: Ensure elements with an ARIA role that require parent roles are contained by them ([rule help](https://dequeuniversity.com/rules/axe/4.14/aria-required-parent?application=axeAPI))
  - `definition-list`: Ensure <dl> elements are structured correctly ([rule help](https://dequeuniversity.com/rules/axe/4.14/definition-list?application=axeAPI))
  - `dlitem`: Ensure <dt> and <dd> elements are contained by a <dl> ([rule help](https://dequeuniversity.com/rules/axe/4.14/dlitem?application=axeAPI))
  - `list`: Ensure that lists are structured correctly ([rule help](https://dequeuniversity.com/rules/axe/4.14/list?application=axeAPI))
  - `listitem`: Ensure <li> elements are used semantically ([rule help](https://dequeuniversity.com/rules/axe/4.14/listitem?application=axeAPI))
  - `td-headers-attr`: Ensure that each cell in a table that uses the headers attribute refers only to other <th> elements in that table ([rule help](https://dequeuniversity.com/rules/axe/4.14/td-headers-attr?application=axeAPI))
  - `th-has-data-cells`: Ensure that <th> elements and elements with role=columnheader/rowheader have data cells they describe ([rule help](https://dequeuniversity.com/rules/axe/4.14/th-has-data-cells?application=axeAPI))
- **Limitations:**
  - A WCAG tag records the axe rule author's criterion association; it is not evidence that the rule covers the full success criterion.
  - The scanner records rule outcomes only when the rule runs and reports them. An absent result does not establish that the criterion passed.
- **Relevant existing tests:** `tests/test_capture.py::test_accessibility_scan_preserves_axe_results_and_specific_evidence`
- **Outstanding gaps / next step:**
  - Validate the implemented checks with criterion-specific counterexamples against the criterion's Understanding guidance; retain manual review for aspects beyond their bounded scope.
  - No result from this scan may be described as WCAG conformance.
- **Evidence links:** [1](https://www.w3.org/TR/WCAG22/#info-and-relationships), [2](https://www.w3.org/WAI/WCAG22/Understanding/info-and-relationships.html), [3](https://dequeuniversity.com/rules/axe/4.14/aria-hidden-body?application=axeAPI), [4](https://dequeuniversity.com/rules/axe/4.14/aria-required-children?application=axeAPI), [5](https://dequeuniversity.com/rules/axe/4.14/aria-required-parent?application=axeAPI), [6](https://dequeuniversity.com/rules/axe/4.14/definition-list?application=axeAPI), [7](https://dequeuniversity.com/rules/axe/4.14/dlitem?application=axeAPI), [8](https://dequeuniversity.com/rules/axe/4.14/list?application=axeAPI), [9](https://dequeuniversity.com/rules/axe/4.14/listitem?application=axeAPI), [10](https://dequeuniversity.com/rules/axe/4.14/td-headers-attr?application=axeAPI), [11](https://dequeuniversity.com/rules/axe/4.14/th-has-data-cells?application=axeAPI)

### 1.3.2 — Meaningful Sequence

- **Level / principle:** A / Perceivable
- **Intent:** Preserve a meaningful reading or interaction sequence when presentation order matters.
- **Coverage:** `manual_evaluation_required`
- **Questionnaire question IDs:** `content.meaningful_sequence`, `layout.two_dimensional_content`
- **Automated check exists:** false
- **Axe check exists:** false
- **WebAble keyboard/focus check exists:** false
- **WebAble text/reflow check exists:** false
- **WebAble text-spacing check exists:** false
- **WebAble orientation check exists:** false
- **WebAble non-text contrast check exists:** false
- **WebAble hover/focus-content check exists:** false
- **WebAble target-size check exists:** false
- **Exact criterion tag:** `wcag132`
- **Manual / keyboard / interaction / assistive-technology testing needed:** true / false / false / false
- **Normative criterion:** [1.3.2 Meaningful Sequence](https://www.w3.org/TR/WCAG22/#meaningful-sequence)
- **Understanding:** [Understanding 1.3.2](https://www.w3.org/WAI/WCAG22/Understanding/meaningful-sequence.html)
- **Associated axe rules:** none with this criterion tag in axe-core 4.14.0 metadata.
- **Implemented failure patterns:** none mapped by an enabled, selected rule carrying this criterion's exact tag.
- **Limitations:**
  - No enabled axe rule selected by the current scanner carries this criterion's exact WCAG tag.
  - A WCAG tag records the axe rule author's criterion association; it is not evidence that the rule covers the full success criterion.
  - The scanner records rule outcomes only when the rule runs and reports them. An absent result does not establish that the criterion passed.
- **Relevant existing tests:** No focused criterion-specific fixture assertion currently exists.
- **Outstanding gaps / next step:**
  - Evaluate representative content and states with a trained reviewer and, where applicable, assistive technology; define bounded automated support only after validating it against WCAG guidance.
  - No result from this scan may be described as WCAG conformance.
- **Evidence links:** [1](https://www.w3.org/TR/WCAG22/#meaningful-sequence), [2](https://www.w3.org/WAI/WCAG22/Understanding/meaningful-sequence.html)

### 1.3.3 — Sensory Characteristics

- **Level / principle:** A / Perceivable
- **Intent:** Do not rely solely on sensory characteristics to identify instructions or content.
- **Coverage:** `manual_evaluation_required`
- **Questionnaire question IDs:** `content.sensory_instructions`, `forms.sensory_instructions`, `widgets.sensory_instructions`
- **Automated check exists:** false
- **Axe check exists:** false
- **WebAble keyboard/focus check exists:** false
- **WebAble text/reflow check exists:** false
- **WebAble text-spacing check exists:** false
- **WebAble orientation check exists:** false
- **WebAble non-text contrast check exists:** false
- **WebAble hover/focus-content check exists:** false
- **WebAble target-size check exists:** false
- **Exact criterion tag:** `wcag133`
- **Manual / keyboard / interaction / assistive-technology testing needed:** true / false / false / false
- **Normative criterion:** [1.3.3 Sensory Characteristics](https://www.w3.org/TR/WCAG22/#sensory-characteristics)
- **Understanding:** [Understanding 1.3.3](https://www.w3.org/WAI/WCAG22/Understanding/sensory-characteristics.html)
- **Associated axe rules:** none with this criterion tag in axe-core 4.14.0 metadata.
- **Implemented failure patterns:** none mapped by an enabled, selected rule carrying this criterion's exact tag.
- **Limitations:**
  - No enabled axe rule selected by the current scanner carries this criterion's exact WCAG tag.
  - A WCAG tag records the axe rule author's criterion association; it is not evidence that the rule covers the full success criterion.
  - The scanner records rule outcomes only when the rule runs and reports them. An absent result does not establish that the criterion passed.
- **Relevant existing tests:** No focused criterion-specific fixture assertion currently exists.
- **Outstanding gaps / next step:**
  - Evaluate representative content and states with a trained reviewer and, where applicable, assistive technology; define bounded automated support only after validating it against WCAG guidance.
  - No result from this scan may be described as WCAG conformance.
- **Evidence links:** [1](https://www.w3.org/TR/WCAG22/#sensory-characteristics), [2](https://www.w3.org/WAI/WCAG22/Understanding/sensory-characteristics.html)

### 1.3.4 — Orientation

- **Level / principle:** AA / Perceivable
- **Intent:** Support content and functionality in both portrait and landscape orientation unless an exception applies.
- **Coverage:** `partial`
- **Questionnaire question IDs:** `content.orientation`
- **Automated check exists:** true
- **Axe check exists:** false
- **WebAble keyboard/focus check exists:** false
- **WebAble text/reflow check exists:** false
- **WebAble text-spacing check exists:** false
- **WebAble orientation check exists:** true
- **WebAble non-text contrast check exists:** false
- **WebAble hover/focus-content check exists:** false
- **WebAble target-size check exists:** false
- **Exact criterion tag:** `wcag134`
- **Manual / keyboard / interaction / assistive-technology testing needed:** true / false / true / false
- **Normative criterion:** [1.3.4 Orientation](https://www.w3.org/TR/WCAG22/#orientation)
- **Understanding:** [Understanding 1.3.4](https://www.w3.org/WAI/WCAG22/Understanding/orientation.html)
- **Associated axe rules** (all exact WCAG-tagged rules in package metadata):
  - [`css-orientation-lock`](https://dequeuniversity.com/rules/axe/4.14/css-orientation-lock?application=axeAPI) — package enabled: `false`; scanner: `selected`; effective: `false`; tags: `cat.structure`, `wcag134`, `wcag21aa`, `EN-301-549`, `EN-9.1.3.4`, `RGAAv4`, `RGAA-13.9.1`, `experimental`
- **Implemented failure patterns:** none mapped by an enabled, selected rule carrying this criterion's exact tag.
- **Bounded orientation checks:**
  - Switches the CSS viewport between paired portrait and landscape dimensions and compares up to 300 visible text-bearing elements and controls by selector and opaque content signature.
  - Reports elements that disappear or change content between orientations as needs-review evidence. The check cannot decide whether a change is equivalent or whether an orientation restriction is essential, and does not emulate physical device rotation or all orientation-change events.
- **Limitations:**
  - No enabled axe rule selected by the current scanner carries this criterion's exact WCAG tag; the listed WebAble probes are separate, bounded evidence and do not establish criterion conformance.
  - A WCAG tag records the axe rule author's criterion association; it is not evidence that the rule covers the full success criterion.
  - The scanner records rule outcomes only when the rule runs and reports them. An absent result does not establish that the criterion passed.
- **Relevant existing tests:** `tests/test_capture.py::test_orientation_flexible_fixture_preserves_content_and_restores_viewport`, `tests/test_capture.py::test_orientation_reports_content_and_control_changes_for_manual_review`
- **Outstanding gaps / next step:**
  - Validate the implemented checks with criterion-specific counterexamples against the criterion's Understanding guidance; retain manual review for aspects beyond their bounded scope.
  - No result from this scan may be described as WCAG conformance.
- **Evidence links:** [1](https://www.w3.org/TR/WCAG22/#orientation), [2](https://www.w3.org/WAI/WCAG22/Understanding/orientation.html)

### 1.3.5 — Identify Input Purpose

- **Level / principle:** AA / Perceivable
- **Intent:** Programmatically identify the purpose of specified user-input fields.
- **Coverage:** `partial`
- **Questionnaire question IDs:** `forms.field_purpose`
- **Automated check exists:** true
- **Axe check exists:** true
- **WebAble keyboard/focus check exists:** false
- **WebAble text/reflow check exists:** false
- **WebAble text-spacing check exists:** false
- **WebAble orientation check exists:** false
- **WebAble non-text contrast check exists:** false
- **WebAble hover/focus-content check exists:** false
- **WebAble target-size check exists:** false
- **Exact criterion tag:** `wcag135`
- **Manual / keyboard / interaction / assistive-technology testing needed:** true / false / false / true
- **Normative criterion:** [1.3.5 Identify Input Purpose](https://www.w3.org/TR/WCAG22/#identify-input-purpose)
- **Understanding:** [Understanding 1.3.5](https://www.w3.org/WAI/WCAG22/Understanding/identify-input-purpose.html)
- **Associated axe rules** (all exact WCAG-tagged rules in package metadata):
  - [`autocomplete-valid`](https://dequeuniversity.com/rules/axe/4.14/autocomplete-valid?application=axeAPI) — package enabled: `true`; scanner: `selected`; effective: `true`; tags: `cat.forms`, `wcag21aa`, `wcag135`, `EN-301-549`, `EN-9.1.3.5`, `ACT`, `RGAAv4`, `RGAA-11.13.1`
- **Implemented failure patterns (rule-description scope, not exhaustive):**
  - `autocomplete-valid`: Ensure the autocomplete attribute is correct and suitable for the form field ([rule help](https://dequeuniversity.com/rules/axe/4.14/autocomplete-valid?application=axeAPI))
- **Limitations:**
  - A WCAG tag records the axe rule author's criterion association; it is not evidence that the rule covers the full success criterion.
  - The scanner records rule outcomes only when the rule runs and reports them. An absent result does not establish that the criterion passed.
- **Relevant existing tests:** No focused criterion-specific fixture assertion currently exists.
- **Outstanding gaps / next step:**
  - Validate the implemented checks with criterion-specific counterexamples against the criterion's Understanding guidance; retain manual review for aspects beyond their bounded scope.
  - No result from this scan may be described as WCAG conformance.
- **Evidence links:** [1](https://www.w3.org/TR/WCAG22/#identify-input-purpose), [2](https://www.w3.org/WAI/WCAG22/Understanding/identify-input-purpose.html), [3](https://dequeuniversity.com/rules/axe/4.14/autocomplete-valid?application=axeAPI)

### 1.4.1 — Use of Color

- **Level / principle:** A / Perceivable
- **Intent:** Do not use color as the only visual means of conveying information, action, or distinction.
- **Coverage:** `partial`
- **Questionnaire question IDs:** `visual.color_and_contrast`
- **Automated check exists:** true
- **Axe check exists:** true
- **WebAble keyboard/focus check exists:** false
- **WebAble text/reflow check exists:** false
- **WebAble text-spacing check exists:** false
- **WebAble orientation check exists:** false
- **WebAble non-text contrast check exists:** false
- **WebAble hover/focus-content check exists:** false
- **WebAble target-size check exists:** false
- **Exact criterion tag:** `wcag141`
- **Manual / keyboard / interaction / assistive-technology testing needed:** true / false / false / false
- **Normative criterion:** [1.4.1 Use of Color](https://www.w3.org/TR/WCAG22/#use-of-color)
- **Understanding:** [Understanding 1.4.1](https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html)
- **Associated axe rules** (all exact WCAG-tagged rules in package metadata):
  - [`link-in-text-block`](https://dequeuniversity.com/rules/axe/4.14/link-in-text-block?application=axeAPI) — package enabled: `true`; scanner: `selected`; effective: `true`; tags: `cat.color`, `wcag2a`, `wcag141`, `TTv5`, `TT13.a`, `EN-301-549`, `EN-9.1.4.1`, `RGAAv4`, `RGAA-10.6.1`
- **Implemented failure patterns (rule-description scope, not exhaustive):**
  - `link-in-text-block`: Ensure links are distinguished from surrounding text in a way that does not rely on color ([rule help](https://dequeuniversity.com/rules/axe/4.14/link-in-text-block?application=axeAPI))
- **Limitations:**
  - A WCAG tag records the axe rule author's criterion association; it is not evidence that the rule covers the full success criterion.
  - The scanner records rule outcomes only when the rule runs and reports them. An absent result does not establish that the criterion passed.
- **Relevant existing tests:** No focused criterion-specific fixture assertion currently exists.
- **Outstanding gaps / next step:**
  - Validate the implemented checks with criterion-specific counterexamples against the criterion's Understanding guidance; retain manual review for aspects beyond their bounded scope.
  - No result from this scan may be described as WCAG conformance.
- **Evidence links:** [1](https://www.w3.org/TR/WCAG22/#use-of-color), [2](https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html), [3](https://dequeuniversity.com/rules/axe/4.14/link-in-text-block?application=axeAPI)

### 1.4.2 — Audio Control

- **Level / principle:** A / Perceivable
- **Intent:** Provide a mechanism to pause or stop certain automatically playing audio or control its volume.
- **Coverage:** `partial`
- **Questionnaire question IDs:** `media.audio_control`
- **Automated check exists:** true
- **Axe check exists:** true
- **WebAble keyboard/focus check exists:** false
- **WebAble text/reflow check exists:** false
- **WebAble text-spacing check exists:** false
- **WebAble orientation check exists:** false
- **WebAble non-text contrast check exists:** false
- **WebAble hover/focus-content check exists:** false
- **WebAble target-size check exists:** false
- **Exact criterion tag:** `wcag142`
- **Manual / keyboard / interaction / assistive-technology testing needed:** true / false / true / false
- **Normative criterion:** [1.4.2 Audio Control](https://www.w3.org/TR/WCAG22/#audio-control)
- **Understanding:** [Understanding 1.4.2](https://www.w3.org/WAI/WCAG22/Understanding/audio-control.html)
- **Associated axe rules** (all exact WCAG-tagged rules in package metadata):
  - [`no-autoplay-audio`](https://dequeuniversity.com/rules/axe/4.14/no-autoplay-audio?application=axeAPI) — package enabled: `true`; scanner: `selected`; effective: `true`; tags: `cat.time-and-media`, `wcag2a`, `wcag142`, `TTv5`, `TT2.a`, `EN-301-549`, `EN-9.1.4.2`, `ACT`, `RGAAv4`, `RGAA-4.10.1`
- **Implemented failure patterns (rule-description scope, not exhaustive):**
  - `no-autoplay-audio`: Ensure <video> or <audio> elements do not autoplay audio for more than 3 seconds without a control mechanism to stop or mute the audio ([rule help](https://dequeuniversity.com/rules/axe/4.14/no-autoplay-audio?application=axeAPI))
- **Limitations:**
  - A WCAG tag records the axe rule author's criterion association; it is not evidence that the rule covers the full success criterion.
  - The scanner records rule outcomes only when the rule runs and reports them. An absent result does not establish that the criterion passed.
- **Relevant existing tests:** No focused criterion-specific fixture assertion currently exists.
- **Outstanding gaps / next step:**
  - Validate the implemented checks with criterion-specific counterexamples against the criterion's Understanding guidance; retain manual review for aspects beyond their bounded scope.
  - No result from this scan may be described as WCAG conformance.
- **Evidence links:** [1](https://www.w3.org/TR/WCAG22/#audio-control), [2](https://www.w3.org/WAI/WCAG22/Understanding/audio-control.html), [3](https://dequeuniversity.com/rules/axe/4.14/no-autoplay-audio?application=axeAPI)

### 1.4.3 — Contrast (Minimum)

- **Level / principle:** AA / Perceivable
- **Intent:** Meet minimum text and image-of-text contrast ratios, subject to defined exceptions.
- **Coverage:** `partial`
- **Questionnaire question IDs:** `visual.color_and_contrast`
- **Automated check exists:** true
- **Axe check exists:** true
- **WebAble keyboard/focus check exists:** false
- **WebAble text/reflow check exists:** false
- **WebAble text-spacing check exists:** false
- **WebAble orientation check exists:** false
- **WebAble non-text contrast check exists:** false
- **WebAble hover/focus-content check exists:** false
- **WebAble target-size check exists:** false
- **Exact criterion tag:** `wcag143`
- **Manual / keyboard / interaction / assistive-technology testing needed:** true / false / false / false
- **Normative criterion:** [1.4.3 Contrast (Minimum)](https://www.w3.org/TR/WCAG22/#contrast-minimum)
- **Understanding:** [Understanding 1.4.3](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html)
- **Associated axe rules** (all exact WCAG-tagged rules in package metadata):
  - [`color-contrast`](https://dequeuniversity.com/rules/axe/4.14/color-contrast?application=axeAPI) — package enabled: `true`; scanner: `selected`; effective: `true`; tags: `cat.color`, `wcag2aa`, `wcag143`, `TTv5`, `TT13.c`, `EN-301-549`, `EN-9.1.4.3`, `ACT`, `RGAAv4`, `RGAA-3.2.1`
- **Implemented failure patterns (rule-description scope, not exhaustive):**
  - `color-contrast`: Ensure the contrast between foreground and background colors meets WCAG 2 AA minimum contrast ratio thresholds ([rule help](https://dequeuniversity.com/rules/axe/4.14/color-contrast?application=axeAPI))
- **Limitations:**
  - A WCAG tag records the axe rule author's criterion association; it is not evidence that the rule covers the full success criterion.
  - The scanner records rule outcomes only when the rule runs and reports them. An absent result does not establish that the criterion passed.
- **Relevant existing tests:** `tests/test_capture.py::test_accessibility_scan_preserves_axe_results_and_specific_evidence`
- **Outstanding gaps / next step:**
  - Validate the implemented checks with criterion-specific counterexamples against the criterion's Understanding guidance; retain manual review for aspects beyond their bounded scope.
  - No result from this scan may be described as WCAG conformance.
- **Evidence links:** [1](https://www.w3.org/TR/WCAG22/#contrast-minimum), [2](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html), [3](https://dequeuniversity.com/rules/axe/4.14/color-contrast?application=axeAPI)

### 1.4.4 — Resize Text

- **Level / principle:** AA / Perceivable
- **Intent:** Allow text to be resized up to 200 percent without loss of content or functionality.
- **Coverage:** `partial`
- **Questionnaire question IDs:** `content.text_resize`
- **Automated check exists:** true
- **Axe check exists:** true
- **WebAble keyboard/focus check exists:** false
- **WebAble text/reflow check exists:** true
- **WebAble text-spacing check exists:** false
- **WebAble orientation check exists:** false
- **WebAble non-text contrast check exists:** false
- **WebAble hover/focus-content check exists:** false
- **WebAble target-size check exists:** false
- **Exact criterion tag:** `wcag144`
- **Manual / keyboard / interaction / assistive-technology testing needed:** true / false / true / false
- **Normative criterion:** [1.4.4 Resize Text](https://www.w3.org/TR/WCAG22/#resize-text)
- **Understanding:** [Understanding 1.4.4](https://www.w3.org/WAI/WCAG22/Understanding/resize-text.html)
- **Associated axe rules** (all exact WCAG-tagged rules in package metadata):
  - [`meta-viewport`](https://dequeuniversity.com/rules/axe/4.14/meta-viewport?application=axeAPI) — package enabled: `true`; scanner: `selected`; effective: `true`; tags: `cat.sensory-and-visual-cues`, `wcag2aa`, `wcag144`, `EN-301-549`, `EN-9.1.4.4`, `ACT`, `RGAAv4`, `RGAA-10.4.2`
- **Implemented failure patterns (rule-description scope, not exhaustive):**
  - `meta-viewport`: Ensure <meta name="viewport"> does not disable text scaling and zooming ([rule help](https://dequeuniversity.com/rules/axe/4.14/meta-viewport?application=axeAPI))
- **Bounded text/reflow checks:**
  - A bounded per-element computed-font-size override probes 200% text for possible clipping, ellipsis, and overlap; text availability is not determined, so these observations require review.
- **Limitations:**
  - A WCAG tag records the axe rule author's criterion association; it is not evidence that the rule covers the full success criterion.
  - The scanner records rule outcomes only when the rule runs and reports them. An absent result does not establish that the criterion passed.
- **Relevant existing tests:** `tests/test_capture.py::test_text_reflow_clipped_text_requires_availability_review`, `tests/test_capture.py::test_text_reflow_ellipsis_disclosure_and_nested_sizes_need_review`, `tests/test_capture.py::test_text_reflow_disclosure_remains_operable_when_clipping_is_reported`, `tests/test_capture.py::test_text_reflow_reports_box_overlap_without_claiming_obscuration`, `tests/test_capture.py::test_text_reflow_usable_fixture_has_no_detected_clipping`, `tests/test_capture.py::test_text_reflow_candidate_limit_prevents_clean_classification`
- **Outstanding gaps / next step:**
  - Validate the implemented checks with criterion-specific counterexamples against the criterion's Understanding guidance; retain manual review for aspects beyond their bounded scope.
  - No result from this scan may be described as WCAG conformance.
- **Evidence links:** [1](https://www.w3.org/TR/WCAG22/#resize-text), [2](https://www.w3.org/WAI/WCAG22/Understanding/resize-text.html), [3](https://dequeuniversity.com/rules/axe/4.14/meta-viewport?application=axeAPI)

### 1.4.5 — Images of Text

- **Level / principle:** AA / Perceivable
- **Intent:** Use text rather than images of text except where an exception applies.
- **Coverage:** `manual_evaluation_required`
- **Questionnaire question IDs:** `visual.images_of_text`
- **Automated check exists:** false
- **Axe check exists:** false
- **WebAble keyboard/focus check exists:** false
- **WebAble text/reflow check exists:** false
- **WebAble text-spacing check exists:** false
- **WebAble orientation check exists:** false
- **WebAble non-text contrast check exists:** false
- **WebAble hover/focus-content check exists:** false
- **WebAble target-size check exists:** false
- **Exact criterion tag:** `wcag145`
- **Manual / keyboard / interaction / assistive-technology testing needed:** true / false / false / false
- **Normative criterion:** [1.4.5 Images of Text](https://www.w3.org/TR/WCAG22/#images-of-text)
- **Understanding:** [Understanding 1.4.5](https://www.w3.org/WAI/WCAG22/Understanding/images-of-text.html)
- **Associated axe rules:** none with this criterion tag in axe-core 4.14.0 metadata.
- **Implemented failure patterns:** none mapped by an enabled, selected rule carrying this criterion's exact tag.
- **Limitations:**
  - No enabled axe rule selected by the current scanner carries this criterion's exact WCAG tag.
  - A WCAG tag records the axe rule author's criterion association; it is not evidence that the rule covers the full success criterion.
  - The scanner records rule outcomes only when the rule runs and reports them. An absent result does not establish that the criterion passed.
- **Relevant existing tests:** No focused criterion-specific fixture assertion currently exists.
- **Outstanding gaps / next step:**
  - Evaluate representative content and states with a trained reviewer and, where applicable, assistive technology; define bounded automated support only after validating it against WCAG guidance.
  - No result from this scan may be described as WCAG conformance.
- **Evidence links:** [1](https://www.w3.org/TR/WCAG22/#images-of-text), [2](https://www.w3.org/WAI/WCAG22/Understanding/images-of-text.html)

### 1.4.10 — Reflow

- **Level / principle:** AA / Perceivable
- **Intent:** Present content without two-dimensional scrolling at specified narrow viewport or zoom conditions, except where essential.
- **Coverage:** `partial`
- **Questionnaire question IDs:** `layout.two_dimensional_content`
- **Automated check exists:** true
- **Axe check exists:** false
- **WebAble keyboard/focus check exists:** false
- **WebAble text/reflow check exists:** true
- **WebAble text-spacing check exists:** false
- **WebAble orientation check exists:** false
- **WebAble non-text contrast check exists:** false
- **WebAble hover/focus-content check exists:** false
- **WebAble target-size check exists:** false
- **Exact criterion tag:** `wcag1410`
- **Manual / keyboard / interaction / assistive-technology testing needed:** true / false / true / false
- **Normative criterion:** [1.4.10 Reflow](https://www.w3.org/TR/WCAG22/#reflow)
- **Understanding:** [Understanding 1.4.10](https://www.w3.org/WAI/WCAG22/Understanding/reflow.html)
- **Associated axe rules:** none with this criterion tag in axe-core 4.14.0 metadata.
- **Implemented failure patterns:** none mapped by an enabled, selected rule carrying this criterion's exact tag.
- **Bounded text/reflow checks:**
  - The existing page is measured at 320 CSS pixels wide; text and document-level overflow are evidence for review, not violations by themselves.
  - A 256 CSS-pixel height probe runs when a table or ARIA table/grid is detected; this heuristic does not determine whether an exception applies, and browser zoom is unsupported.
- **Limitations:**
  - No enabled axe rule selected by the current scanner carries this criterion's exact WCAG tag; the listed WebAble probes are separate, bounded evidence and do not establish criterion conformance.
  - A WCAG tag records the axe rule author's criterion association; it is not evidence that the rule covers the full success criterion.
  - The scanner records rule outcomes only when the rule runs and reports them. An absent result does not establish that the criterion passed.
- **Relevant existing tests:** `tests/test_capture.py::test_text_reflow_flags_320px_overflow_for_review`, `tests/test_capture.py::test_text_reflow_does_not_fail_legitimate_table_scrolling`, `tests/test_capture.py::test_text_reflow_reports_unbreakable_text_overflow`, `tests/test_capture.py::test_text_reflow_responsive_content_replacement_needs_review`
- **Outstanding gaps / next step:**
  - Validate the implemented checks with criterion-specific counterexamples against the criterion's Understanding guidance; retain manual review for aspects beyond their bounded scope.
  - No result from this scan may be described as WCAG conformance.
- **Evidence links:** [1](https://www.w3.org/TR/WCAG22/#reflow), [2](https://www.w3.org/WAI/WCAG22/Understanding/reflow.html)

### 1.4.11 — Non-text Contrast

- **Level / principle:** AA / Perceivable
- **Intent:** Provide required contrast for visual information needed to identify interface components and graphical objects.
- **Coverage:** `partial`
- **Questionnaire question IDs:** `visual.color_and_contrast`
- **Automated check exists:** true
- **Axe check exists:** false
- **WebAble keyboard/focus check exists:** false
- **WebAble text/reflow check exists:** false
- **WebAble text-spacing check exists:** false
- **WebAble orientation check exists:** false
- **WebAble non-text contrast check exists:** true
- **WebAble hover/focus-content check exists:** false
- **WebAble target-size check exists:** false
- **Exact criterion tag:** `wcag1411`
- **Manual / keyboard / interaction / assistive-technology testing needed:** true / false / false / false
- **Normative criterion:** [1.4.11 Non-text Contrast](https://www.w3.org/TR/WCAG22/#non-text-contrast)
- **Understanding:** [Understanding 1.4.11](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html)
- **Associated axe rules:** none with this criterion tag in axe-core 4.14.0 metadata.
- **Implemented failure patterns:** none mapped by an enabled, selected rule carrying this criterion's exact tag.
- **Bounded non-text contrast checks:**
  - Inspects up to 300 visible native controls, links, ARIA controls, and SVG shapes for solid computed CSS backgrounds, borders, outlines, fills, and strokes with estimated contrast below 3:1.
  - Reports measured color pairs and element geometry as needs-review evidence only. It cannot determine which visual boundary is necessary, evaluate pseudo-elements or box shadows, pixel-sample images/canvas/video, reliably resolve gradients and layered rendering, or establish that a low ratio violates the criterion.
- **Limitations:**
  - No enabled axe rule selected by the current scanner carries this criterion's exact WCAG tag; the listed WebAble probes are separate, bounded evidence and do not establish criterion conformance.
  - A WCAG tag records the axe rule author's criterion association; it is not evidence that the rule covers the full success criterion.
  - The scanner records rule outcomes only when the rule runs and reports them. An absent result does not establish that the criterion passed.
- **Relevant existing tests:** `tests/test_capture.py::test_non_text_contrast_reports_solid_color_candidates_for_review`, `tests/test_capture.py::test_accessibility_scan_preserves_axe_results_and_specific_evidence`
- **Outstanding gaps / next step:**
  - Validate the implemented checks with criterion-specific counterexamples against the criterion's Understanding guidance; retain manual review for aspects beyond their bounded scope.
  - No result from this scan may be described as WCAG conformance.
- **Evidence links:** [1](https://www.w3.org/TR/WCAG22/#non-text-contrast), [2](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html)

### 1.4.12 — Text Spacing

- **Level / principle:** AA / Perceivable
- **Intent:** Preserve content and functionality when users override specified text-spacing properties.
- **Coverage:** `partial`
- **Questionnaire question IDs:** `content.text_spacing`
- **Automated check exists:** true
- **Axe check exists:** true
- **WebAble keyboard/focus check exists:** false
- **WebAble text/reflow check exists:** false
- **WebAble text-spacing check exists:** true
- **WebAble orientation check exists:** false
- **WebAble non-text contrast check exists:** false
- **WebAble hover/focus-content check exists:** false
- **WebAble target-size check exists:** false
- **Exact criterion tag:** `wcag1412`
- **Manual / keyboard / interaction / assistive-technology testing needed:** true / false / true / false
- **Normative criterion:** [1.4.12 Text Spacing](https://www.w3.org/TR/WCAG22/#text-spacing)
- **Understanding:** [Understanding 1.4.12](https://www.w3.org/WAI/WCAG22/Understanding/text-spacing.html)
- **Associated axe rules** (all exact WCAG-tagged rules in package metadata):
  - [`avoid-inline-spacing`](https://dequeuniversity.com/rules/axe/4.14/avoid-inline-spacing?application=axeAPI) — package enabled: `true`; scanner: `selected`; effective: `true`; tags: `cat.structure`, `wcag21aa`, `wcag1412`, `EN-301-549`, `EN-9.1.4.12`, `ACT`
- **Implemented failure patterns (rule-description scope, not exhaustive):**
  - `avoid-inline-spacing`: Ensure that text spacing set through style attributes can be adjusted with custom stylesheets ([rule help](https://dequeuniversity.com/rules/axe/4.14/avoid-inline-spacing?application=axeAPI))
- **Bounded text-spacing checks:**
  - Applies line-height 1.5, paragraph margin after 2em, letter-spacing 0.12em, and word-spacing 0.16em to up to 300 visible text-bearing elements, then compares measurements with the captured baseline.
  - Reports changed clipping, overlap, container overflow, hidden text, or control visibility/hit testing as needs-review evidence; scrollable regions are identified and are not treated as violations.
- **Limitations:**
  - A WCAG tag records the axe rule author's criterion association; it is not evidence that the rule covers the full success criterion.
  - The scanner records rule outcomes only when the rule runs and reports them. An absent result does not establish that the criterion passed.
- **Relevant existing tests:** `tests/test_capture.py::test_text_spacing_usable_fixture_has_no_detected_geometry_issue`, `tests/test_capture.py::test_text_spacing_reports_fixed_height_clipping_for_review`, `tests/test_capture.py::test_text_spacing_reports_new_overlap_without_claiming_violation`, `tests/test_capture.py::test_text_spacing_reports_control_label_clipping_for_review`, `tests/test_capture.py::test_text_spacing_reports_control_obscured_after_content_reflows`, `tests/test_capture.py::test_text_spacing_keeps_scrollable_region_as_review_not_failure`, `tests/test_capture.py::test_text_spacing_overrides_restore_after_screenshot_failure`
- **Outstanding gaps / next step:**
  - Validate the implemented checks with criterion-specific counterexamples against the criterion's Understanding guidance; retain manual review for aspects beyond their bounded scope.
  - No result from this scan may be described as WCAG conformance.
- **Evidence links:** [1](https://www.w3.org/TR/WCAG22/#text-spacing), [2](https://www.w3.org/WAI/WCAG22/Understanding/text-spacing.html), [3](https://dequeuniversity.com/rules/axe/4.14/avoid-inline-spacing?application=axeAPI)

### 1.4.13 — Content on Hover or Focus

- **Level / principle:** AA / Perceivable
- **Intent:** Make additional content shown on hover or focus dismissible, hoverable, and persistent as required.
- **Coverage:** `partial`
- **Questionnaire question IDs:** `widgets.hover_focus_content`
- **Automated check exists:** true
- **Axe check exists:** false
- **WebAble keyboard/focus check exists:** false
- **WebAble text/reflow check exists:** false
- **WebAble text-spacing check exists:** false
- **WebAble orientation check exists:** false
- **WebAble non-text contrast check exists:** false
- **WebAble hover/focus-content check exists:** true
- **WebAble target-size check exists:** false
- **Exact criterion tag:** `wcag1413`
- **Manual / keyboard / interaction / assistive-technology testing needed:** true / false / true / false
- **Normative criterion:** [1.4.13 Content on Hover or Focus](https://www.w3.org/TR/WCAG22/#content-on-hover-or-focus)
- **Understanding:** [Understanding 1.4.13](https://www.w3.org/WAI/WCAG22/Understanding/content-on-hover-or-focus.html)
- **Associated axe rules:** none with this criterion tag in axe-core 4.14.0 metadata.
- **Implemented failure patterns:** none mapped by an enabled, selected rule carrying this criterion's exact tag.
- **Bounded hover/focus-content checks:**
  - Samples up to four visible likely triggers without activating them, compares visible DOM content before and after pointer hover and focus, and records newly revealed content with trigger/content selectors, geometry, viewport, role, and opaque text signatures.
  - For revealed content, samples whether pointer entry keeps hover content visible, whether Escape dismisses it, whether it remains after focus blur, and whether its rectangle intersects other content. Findings remain needs-review evidence; custom triggers, pseudo-elements, native tooltips, delayed states, and semantic exceptions are not fully evaluated.
- **Limitations:**
  - No enabled axe rule selected by the current scanner carries this criterion's exact WCAG tag; the listed WebAble probes are separate, bounded evidence and do not establish criterion conformance.
  - A WCAG tag records the axe rule author's criterion association; it is not evidence that the rule covers the full success criterion.
  - The scanner records rule outcomes only when the rule runs and reports them. An absent result does not establish that the criterion passed.
- **Relevant existing tests:** `tests/test_capture.py::test_hover_focus_compliant_tooltip_records_behavior_and_restores_focus`, `tests/test_capture.py::test_hover_focus_reports_content_that_pointer_cannot_enter`, `tests/test_capture.py::test_hover_focus_reports_undismissable_overlapping_focus_content`, `tests/test_capture.py::test_hover_focus_ignores_style_only_hover_changes`
- **Outstanding gaps / next step:**
  - Validate the implemented checks with criterion-specific counterexamples against the criterion's Understanding guidance; retain manual review for aspects beyond their bounded scope.
  - No result from this scan may be described as WCAG conformance.
- **Evidence links:** [1](https://www.w3.org/TR/WCAG22/#content-on-hover-or-focus), [2](https://www.w3.org/WAI/WCAG22/Understanding/content-on-hover-or-focus.html)

### 2.1.1 — Keyboard

- **Level / principle:** A / Operable
- **Intent:** Make all functionality operable through a keyboard interface, except where the function depends on path-based input.
- **Coverage:** `partial`
- **Questionnaire question IDs:** `widgets.keyboard_operation`
- **Automated check exists:** true
- **Axe check exists:** true
- **WebAble keyboard/focus check exists:** true
- **WebAble text/reflow check exists:** false
- **WebAble text-spacing check exists:** false
- **WebAble orientation check exists:** false
- **WebAble non-text contrast check exists:** false
- **WebAble hover/focus-content check exists:** false
- **WebAble target-size check exists:** false
- **Exact criterion tag:** `wcag211`
- **Manual / keyboard / interaction / assistive-technology testing needed:** true / true / true / true
- **Normative criterion:** [2.1.1 Keyboard](https://www.w3.org/TR/WCAG22/#keyboard)
- **Understanding:** [Understanding 2.1.1](https://www.w3.org/WAI/WCAG22/Understanding/keyboard.html)
- **Associated axe rules** (all exact WCAG-tagged rules in package metadata):
  - [`frame-focusable-content`](https://dequeuniversity.com/rules/axe/4.14/frame-focusable-content?application=axeAPI) — package enabled: `true`; scanner: `selected`; effective: `true`; tags: `cat.keyboard`, `wcag2a`, `wcag211`, `TTv5`, `TT4.a`, `EN-301-549`, `EN-9.2.1.1`, `RGAAv4`, `RGAA-7.3.2`
  - [`scrollable-region-focusable`](https://dequeuniversity.com/rules/axe/4.14/scrollable-region-focusable?application=axeAPI) — package enabled: `true`; scanner: `selected`; effective: `true`; tags: `cat.keyboard`, `wcag2a`, `wcag211`, `wcag213`, `TTv5`, `TT4.a`, `EN-301-549`, `EN-9.2.1.1`, `EN-9.2.1.3`, `RGAAv4`, `RGAA-7.3.2`
  - [`server-side-image-map`](https://dequeuniversity.com/rules/axe/4.14/server-side-image-map?application=axeAPI) — package enabled: `true`; scanner: `selected`; effective: `true`; tags: `cat.text-alternatives`, `wcag2a`, `wcag211`, `section508`, `section508.22.f`, `TTv5`, `TT4.a`, `EN-301-549`, `EN-9.2.1.1`, `RGAAv4`, `RGAA-1.1.4`
- **Implemented failure patterns (rule-description scope, not exhaustive):**
  - `frame-focusable-content`: Ensure <frame> and <iframe> elements with focusable content do not have tabindex=-1 ([rule help](https://dequeuniversity.com/rules/axe/4.14/frame-focusable-content?application=axeAPI))
  - `scrollable-region-focusable`: Ensure elements that have scrollable content are accessible by keyboard in Safari ([rule help](https://dequeuniversity.com/rules/axe/4.14/scrollable-region-focusable?application=axeAPI))
  - `server-side-image-map`: Ensure that server-side image maps are not used ([rule help](https://dequeuniversity.com/rules/axe/4.14/server-side-image-map?application=axeAPI))
- **Bounded keyboard/focus checks:**
  - Sequential Tab/Shift+Tab focus progression is sampled without activating controls; up to 51 Tab actions cover the 50-candidate discovery cap plus one boundary action.
- **Limitations:**
  - A WCAG tag records the axe rule author's criterion association; it is not evidence that the rule covers the full success criterion.
  - The scanner records rule outcomes only when the rule runs and reports them. An absent result does not establish that the criterion passed.
- **Relevant existing tests:** `tests/test_capture.py::test_keyboard_audit_records_visible_keyboard_focus`, `tests/test_capture.py::test_keyboard_audit_traverses_more_than_twenty_sequential_targets`, `tests/test_capture.py::test_keyboard_audit_reports_interactive_candidate_skipped_by_tab`
- **Outstanding gaps / next step:**
  - Validate the implemented checks with criterion-specific counterexamples against the criterion's Understanding guidance; retain manual review for aspects beyond their bounded scope.
  - No result from this scan may be described as WCAG conformance.
- **Evidence links:** [1](https://www.w3.org/TR/WCAG22/#keyboard), [2](https://www.w3.org/WAI/WCAG22/Understanding/keyboard.html), [3](https://dequeuniversity.com/rules/axe/4.14/frame-focusable-content?application=axeAPI), [4](https://dequeuniversity.com/rules/axe/4.14/scrollable-region-focusable?application=axeAPI), [5](https://dequeuniversity.com/rules/axe/4.14/server-side-image-map?application=axeAPI)

### 2.1.2 — No Keyboard Trap

- **Level / principle:** A / Operable
- **Intent:** Allow keyboard focus to move away from every component using only the keyboard.
- **Coverage:** `partial`
- **Questionnaire question IDs:** `widgets.keyboard_operation`
- **Automated check exists:** true
- **Axe check exists:** false
- **WebAble keyboard/focus check exists:** true
- **WebAble text/reflow check exists:** false
- **WebAble text-spacing check exists:** false
- **WebAble orientation check exists:** false
- **WebAble non-text contrast check exists:** false
- **WebAble hover/focus-content check exists:** false
- **WebAble target-size check exists:** false
- **Exact criterion tag:** `wcag212`
- **Manual / keyboard / interaction / assistive-technology testing needed:** true / true / true / false
- **Normative criterion:** [2.1.2 No Keyboard Trap](https://www.w3.org/TR/WCAG22/#no-keyboard-trap)
- **Understanding:** [Understanding 2.1.2](https://www.w3.org/WAI/WCAG22/Understanding/no-keyboard-trap.html)
- **Associated axe rules:** none with this criterion tag in axe-core 4.14.0 metadata.
- **Implemented failure patterns:** none mapped by an enabled, selected rule carrying this criterion's exact tag.
- **Bounded keyboard/focus checks:**
  - A repeated consecutive Tab target is distinguished from a focus cycle; when Tab stalls, the bounded Shift+Tab sample records whether focus moves from that target. Repeated multi-target Tab cycles are also compared with reverse traversal. Evidence remains review-only because focus cycling does not establish whether a containing widget can be exited or dismissed.
- **Limitations:**
  - No enabled axe rule selected by the current scanner carries this criterion's exact WCAG tag; the listed WebAble probes are separate, bounded evidence and do not establish criterion conformance.
  - A WCAG tag records the axe rule author's criterion association; it is not evidence that the rule covers the full success criterion.
  - The scanner records rule outcomes only when the rule runs and reports them. An absent result does not establish that the criterion passed.
- **Relevant existing tests:** `tests/test_capture.py::test_keyboard_audit_reports_potential_focus_trap_for_review`, `tests/test_capture.py::test_keyboard_audit_distinguishes_one_way_tab_block_from_trap`, `tests/test_capture.py::test_keyboard_audit_reports_wrapping_cycle_for_manual_review`
- **Outstanding gaps / next step:**
  - Validate the implemented checks with criterion-specific counterexamples against the criterion's Understanding guidance; retain manual review for aspects beyond their bounded scope.
  - No result from this scan may be described as WCAG conformance.
- **Evidence links:** [1](https://www.w3.org/TR/WCAG22/#no-keyboard-trap), [2](https://www.w3.org/WAI/WCAG22/Understanding/no-keyboard-trap.html)

### 2.1.4 — Character Key Shortcuts

- **Level / principle:** A / Operable
- **Intent:** Provide a way to turn off, remap, or limit single-character shortcuts in applicable contexts.
- **Coverage:** `manual_evaluation_required`
- **Questionnaire question IDs:** `keyboard.character_shortcuts`
- **Automated check exists:** false
- **Axe check exists:** false
- **WebAble keyboard/focus check exists:** false
- **WebAble text/reflow check exists:** false
- **WebAble text-spacing check exists:** false
- **WebAble orientation check exists:** false
- **WebAble non-text contrast check exists:** false
- **WebAble hover/focus-content check exists:** false
- **WebAble target-size check exists:** false
- **Exact criterion tag:** `wcag214`
- **Manual / keyboard / interaction / assistive-technology testing needed:** true / true / true / false
- **Normative criterion:** [2.1.4 Character Key Shortcuts](https://www.w3.org/TR/WCAG22/#character-key-shortcuts)
- **Understanding:** [Understanding 2.1.4](https://www.w3.org/WAI/WCAG22/Understanding/character-key-shortcuts.html)
- **Associated axe rules:** none with this criterion tag in axe-core 4.14.0 metadata.
- **Implemented failure patterns:** none mapped by an enabled, selected rule carrying this criterion's exact tag.
- **Limitations:**
  - No enabled axe rule selected by the current scanner carries this criterion's exact WCAG tag.
  - A WCAG tag records the axe rule author's criterion association; it is not evidence that the rule covers the full success criterion.
  - The scanner records rule outcomes only when the rule runs and reports them. An absent result does not establish that the criterion passed.
- **Relevant existing tests:** No focused criterion-specific fixture assertion currently exists.
- **Outstanding gaps / next step:**
  - Evaluate representative content and states with a trained reviewer and, where applicable, assistive technology; define bounded automated support only after validating it against WCAG guidance.
  - No result from this scan may be described as WCAG conformance.
- **Evidence links:** [1](https://www.w3.org/TR/WCAG22/#character-key-shortcuts), [2](https://www.w3.org/WAI/WCAG22/Understanding/character-key-shortcuts.html)

### 2.2.1 — Timing Adjustable

- **Level / principle:** A / Operable
- **Intent:** Allow users to turn off, adjust, or extend time limits, subject to exceptions.
- **Coverage:** `partial`
- **Questionnaire question IDs:** `timing.adjustment`
- **Automated check exists:** true
- **Axe check exists:** true
- **WebAble keyboard/focus check exists:** false
- **WebAble text/reflow check exists:** false
- **WebAble text-spacing check exists:** false
- **WebAble orientation check exists:** false
- **WebAble non-text contrast check exists:** false
- **WebAble hover/focus-content check exists:** false
- **WebAble target-size check exists:** false
- **Exact criterion tag:** `wcag221`
- **Manual / keyboard / interaction / assistive-technology testing needed:** true / false / true / false
- **Normative criterion:** [2.2.1 Timing Adjustable](https://www.w3.org/TR/WCAG22/#timing-adjustable)
- **Understanding:** [Understanding 2.2.1](https://www.w3.org/WAI/WCAG22/Understanding/timing-adjustable.html)
- **Associated axe rules** (all exact WCAG-tagged rules in package metadata):
  - [`meta-refresh`](https://dequeuniversity.com/rules/axe/4.14/meta-refresh?application=axeAPI) — package enabled: `true`; scanner: `selected`; effective: `true`; tags: `cat.time-and-media`, `wcag2a`, `wcag221`, `TTv5`, `TT8.a`, `EN-301-549`, `EN-9.2.2.1`, `RGAAv4`, `RGAA-13.1.2`
- **Implemented failure patterns (rule-description scope, not exhaustive):**
  - `meta-refresh`: Ensure <meta http-equiv="refresh"> is not used for delayed refresh ([rule help](https://dequeuniversity.com/rules/axe/4.14/meta-refresh?application=axeAPI))
- **Limitations:**
  - A WCAG tag records the axe rule author's criterion association; it is not evidence that the rule covers the full success criterion.
  - The scanner records rule outcomes only when the rule runs and reports them. An absent result does not establish that the criterion passed.
- **Relevant existing tests:** No focused criterion-specific fixture assertion currently exists.
- **Outstanding gaps / next step:**
  - Validate the implemented checks with criterion-specific counterexamples against the criterion's Understanding guidance; retain manual review for aspects beyond their bounded scope.
  - No result from this scan may be described as WCAG conformance.
- **Evidence links:** [1](https://www.w3.org/TR/WCAG22/#timing-adjustable), [2](https://www.w3.org/WAI/WCAG22/Understanding/timing-adjustable.html), [3](https://dequeuniversity.com/rules/axe/4.14/meta-refresh?application=axeAPI)

### 2.2.2 — Pause, Stop, Hide

- **Level / principle:** A / Operable
- **Intent:** Provide controls for certain moving, blinking, scrolling, or auto-updating content.
- **Coverage:** `partial`
- **Questionnaire question IDs:** `motion.pause_and_flash`
- **Automated check exists:** true
- **Axe check exists:** true
- **WebAble keyboard/focus check exists:** false
- **WebAble text/reflow check exists:** false
- **WebAble text-spacing check exists:** false
- **WebAble orientation check exists:** false
- **WebAble non-text contrast check exists:** false
- **WebAble hover/focus-content check exists:** false
- **WebAble target-size check exists:** false
- **Exact criterion tag:** `wcag222`
- **Manual / keyboard / interaction / assistive-technology testing needed:** true / false / true / false
- **Normative criterion:** [2.2.2 Pause, Stop, Hide](https://www.w3.org/TR/WCAG22/#pause-stop-hide)
- **Understanding:** [Understanding 2.2.2](https://www.w3.org/WAI/WCAG22/Understanding/pause-stop-hide.html)
- **Associated axe rules** (all exact WCAG-tagged rules in package metadata):
  - [`blink`](https://dequeuniversity.com/rules/axe/4.14/blink?application=axeAPI) — package enabled: `true`; scanner: `selected`; effective: `true`; tags: `cat.time-and-media`, `wcag2a`, `wcag222`, `section508`, `section508.22.j`, `TTv5`, `TT2.b`, `EN-301-549`, `EN-9.2.2.2`, `RGAAv4`, `RGAA-13.8.1`
  - [`marquee`](https://dequeuniversity.com/rules/axe/4.14/marquee?application=axeAPI) — package enabled: `true`; scanner: `selected`; effective: `true`; tags: `cat.parsing`, `wcag2a`, `wcag222`, `TTv5`, `TT2.b`, `EN-301-549`, `EN-9.2.2.2`, `RGAAv4`, `RGAA-13.8.1`
- **Implemented failure patterns (rule-description scope, not exhaustive):**
  - `blink`: Ensure <blink> elements are not used ([rule help](https://dequeuniversity.com/rules/axe/4.14/blink?application=axeAPI))
  - `marquee`: Ensure <marquee> elements are not used ([rule help](https://dequeuniversity.com/rules/axe/4.14/marquee?application=axeAPI))
- **Limitations:**
  - A WCAG tag records the axe rule author's criterion association; it is not evidence that the rule covers the full success criterion.
  - The scanner records rule outcomes only when the rule runs and reports them. An absent result does not establish that the criterion passed.
- **Relevant existing tests:** No focused criterion-specific fixture assertion currently exists.
- **Outstanding gaps / next step:**
  - Validate the implemented checks with criterion-specific counterexamples against the criterion's Understanding guidance; retain manual review for aspects beyond their bounded scope.
  - No result from this scan may be described as WCAG conformance.
- **Evidence links:** [1](https://www.w3.org/TR/WCAG22/#pause-stop-hide), [2](https://www.w3.org/WAI/WCAG22/Understanding/pause-stop-hide.html), [3](https://dequeuniversity.com/rules/axe/4.14/blink?application=axeAPI), [4](https://dequeuniversity.com/rules/axe/4.14/marquee?application=axeAPI)

### 2.3.1 — Three Flashes or Below Threshold

- **Level / principle:** A / Operable
- **Intent:** Ensure content does not flash more than three times per second unless below defined thresholds.
- **Coverage:** `manual_evaluation_required`
- **Questionnaire question IDs:** `motion.flash_threshold`
- **Automated check exists:** false
- **Axe check exists:** false
- **WebAble keyboard/focus check exists:** false
- **WebAble text/reflow check exists:** false
- **WebAble text-spacing check exists:** false
- **WebAble orientation check exists:** false
- **WebAble non-text contrast check exists:** false
- **WebAble hover/focus-content check exists:** false
- **WebAble target-size check exists:** false
- **Exact criterion tag:** `wcag231`
- **Manual / keyboard / interaction / assistive-technology testing needed:** true / false / true / false
- **Normative criterion:** [2.3.1 Three Flashes or Below Threshold](https://www.w3.org/TR/WCAG22/#three-flashes-or-below-threshold)
- **Understanding:** [Understanding 2.3.1](https://www.w3.org/WAI/WCAG22/Understanding/three-flashes-or-below-threshold.html)
- **Associated axe rules:** none with this criterion tag in axe-core 4.14.0 metadata.
- **Implemented failure patterns:** none mapped by an enabled, selected rule carrying this criterion's exact tag.
- **Limitations:**
  - No enabled axe rule selected by the current scanner carries this criterion's exact WCAG tag.
  - A WCAG tag records the axe rule author's criterion association; it is not evidence that the rule covers the full success criterion.
  - The scanner records rule outcomes only when the rule runs and reports them. An absent result does not establish that the criterion passed.
- **Relevant existing tests:** No focused criterion-specific fixture assertion currently exists.
- **Outstanding gaps / next step:**
  - Evaluate representative content and states with a trained reviewer and, where applicable, assistive technology; define bounded automated support only after validating it against WCAG guidance.
  - No result from this scan may be described as WCAG conformance.
- **Evidence links:** [1](https://www.w3.org/TR/WCAG22/#three-flashes-or-below-threshold), [2](https://www.w3.org/WAI/WCAG22/Understanding/three-flashes-or-below-threshold.html)

### 2.4.1 — Bypass Blocks

- **Level / principle:** A / Operable
- **Intent:** Provide a way to bypass blocks of content repeated across multiple pages.
- **Coverage:** `partial`
- **Questionnaire question IDs:** `pages.bypass_repeated_blocks`
- **Automated check exists:** true
- **Axe check exists:** true
- **WebAble keyboard/focus check exists:** false
- **WebAble text/reflow check exists:** false
- **WebAble text-spacing check exists:** false
- **WebAble orientation check exists:** false
- **WebAble non-text contrast check exists:** false
- **WebAble hover/focus-content check exists:** false
- **WebAble target-size check exists:** false
- **Exact criterion tag:** `wcag241`
- **Manual / keyboard / interaction / assistive-technology testing needed:** true / false / false / false
- **Normative criterion:** [2.4.1 Bypass Blocks](https://www.w3.org/TR/WCAG22/#bypass-blocks)
- **Understanding:** [Understanding 2.4.1](https://www.w3.org/WAI/WCAG22/Understanding/bypass-blocks.html)
- **Associated axe rules** (all exact WCAG-tagged rules in package metadata):
  - [`bypass`](https://dequeuniversity.com/rules/axe/4.14/bypass?application=axeAPI) — package enabled: `true`; scanner: `selected`; effective: `true`; tags: `cat.keyboard`, `wcag2a`, `wcag241`, `section508`, `section508.22.o`, `TTv5`, `TT9.a`, `EN-301-549`, `EN-9.2.4.1`, `RGAAv4`, `RGAA-12.7.1`
- **Implemented failure patterns (rule-description scope, not exhaustive):**
  - `bypass`: Ensure each page has at least one mechanism for a user to bypass navigation and jump straight to the content ([rule help](https://dequeuniversity.com/rules/axe/4.14/bypass?application=axeAPI))
- **Limitations:**
  - A WCAG tag records the axe rule author's criterion association; it is not evidence that the rule covers the full success criterion.
  - The scanner records rule outcomes only when the rule runs and reports them. An absent result does not establish that the criterion passed.
- **Relevant existing tests:** No focused criterion-specific fixture assertion currently exists.
- **Outstanding gaps / next step:**
  - Validate the implemented checks with criterion-specific counterexamples against the criterion's Understanding guidance; retain manual review for aspects beyond their bounded scope.
  - No result from this scan may be described as WCAG conformance.
- **Evidence links:** [1](https://www.w3.org/TR/WCAG22/#bypass-blocks), [2](https://www.w3.org/WAI/WCAG22/Understanding/bypass-blocks.html), [3](https://dequeuniversity.com/rules/axe/4.14/bypass?application=axeAPI)

### 2.4.2 — Page Titled

- **Level / principle:** A / Operable
- **Intent:** Give each web page a title that describes its topic or purpose.
- **Coverage:** `partial`
- **Questionnaire question IDs:** `pages.descriptive_titles`
- **Automated check exists:** true
- **Axe check exists:** true
- **WebAble keyboard/focus check exists:** false
- **WebAble text/reflow check exists:** false
- **WebAble text-spacing check exists:** false
- **WebAble orientation check exists:** false
- **WebAble non-text contrast check exists:** false
- **WebAble hover/focus-content check exists:** false
- **WebAble target-size check exists:** false
- **Exact criterion tag:** `wcag242`
- **Manual / keyboard / interaction / assistive-technology testing needed:** true / false / false / false
- **Normative criterion:** [2.4.2 Page Titled](https://www.w3.org/TR/WCAG22/#page-titled)
- **Understanding:** [Understanding 2.4.2](https://www.w3.org/WAI/WCAG22/Understanding/page-titled.html)
- **Associated axe rules** (all exact WCAG-tagged rules in package metadata):
  - [`document-title`](https://dequeuniversity.com/rules/axe/4.14/document-title?application=axeAPI) — package enabled: `true`; scanner: `selected`; effective: `true`; tags: `cat.text-alternatives`, `wcag2a`, `wcag242`, `TTv5`, `TT12.a`, `EN-301-549`, `EN-9.2.4.2`, `ACT`, `RGAAv4`, `RGAA-8.5.1`
- **Implemented failure patterns (rule-description scope, not exhaustive):**
  - `document-title`: Ensure each HTML document contains a non-empty <title> element ([rule help](https://dequeuniversity.com/rules/axe/4.14/document-title?application=axeAPI))
- **Limitations:**
  - A WCAG tag records the axe rule author's criterion association; it is not evidence that the rule covers the full success criterion.
  - The scanner records rule outcomes only when the rule runs and reports them. An absent result does not establish that the criterion passed.
- **Relevant existing tests:** No focused criterion-specific fixture assertion currently exists.
- **Outstanding gaps / next step:**
  - Validate the implemented checks with criterion-specific counterexamples against the criterion's Understanding guidance; retain manual review for aspects beyond their bounded scope.
  - No result from this scan may be described as WCAG conformance.
- **Evidence links:** [1](https://www.w3.org/TR/WCAG22/#page-titled), [2](https://www.w3.org/WAI/WCAG22/Understanding/page-titled.html), [3](https://dequeuniversity.com/rules/axe/4.14/document-title?application=axeAPI)

### 2.4.3 — Focus Order

- **Level / principle:** A / Operable
- **Intent:** Ensure sequential focus order preserves meaning and operability.
- **Coverage:** `partial`
- **Questionnaire question IDs:** `widgets.keyboard_operation`
- **Automated check exists:** true
- **Axe check exists:** false
- **WebAble keyboard/focus check exists:** true
- **WebAble text/reflow check exists:** false
- **WebAble text-spacing check exists:** false
- **WebAble orientation check exists:** false
- **WebAble non-text contrast check exists:** false
- **WebAble hover/focus-content check exists:** false
- **WebAble target-size check exists:** false
- **Exact criterion tag:** `wcag243`
- **Manual / keyboard / interaction / assistive-technology testing needed:** true / true / true / false
- **Normative criterion:** [2.4.3 Focus Order](https://www.w3.org/TR/WCAG22/#focus-order)
- **Understanding:** [Understanding 2.4.3](https://www.w3.org/WAI/WCAG22/Understanding/focus-order.html)
- **Associated axe rules:** none with this criterion tag in axe-core 4.14.0 metadata.
- **Implemented failure patterns:** none mapped by an enabled, selected rule carrying this criterion's exact tag.
- **Bounded keyboard/focus checks:**
  - The expanded bounded Tab sequence is recorded; whether its order preserves meaning requires human review.
- **Limitations:**
  - No enabled axe rule selected by the current scanner carries this criterion's exact WCAG tag; the listed WebAble probes are separate, bounded evidence and do not establish criterion conformance.
  - A WCAG tag records the axe rule author's criterion association; it is not evidence that the rule covers the full success criterion.
  - The scanner records rule outcomes only when the rule runs and reports them. An absent result does not establish that the criterion passed.
- **Relevant existing tests:** No focused criterion-specific fixture assertion currently exists.
- **Outstanding gaps / next step:**
  - Validate the implemented checks with criterion-specific counterexamples against the criterion's Understanding guidance; retain manual review for aspects beyond their bounded scope.
  - No result from this scan may be described as WCAG conformance.
- **Evidence links:** [1](https://www.w3.org/TR/WCAG22/#focus-order), [2](https://www.w3.org/WAI/WCAG22/Understanding/focus-order.html)

### 2.4.4 — Link Purpose (In Context)

- **Level / principle:** A / Operable
- **Intent:** Make the purpose of each link determinable from its text or programmatically determined context, with exceptions.
- **Coverage:** `partial`
- **Questionnaire question IDs:** `pages.link_purpose`
- **Automated check exists:** true
- **Axe check exists:** true
- **WebAble keyboard/focus check exists:** false
- **WebAble text/reflow check exists:** false
- **WebAble text-spacing check exists:** false
- **WebAble orientation check exists:** false
- **WebAble non-text contrast check exists:** false
- **WebAble hover/focus-content check exists:** false
- **WebAble target-size check exists:** false
- **Exact criterion tag:** `wcag244`
- **Manual / keyboard / interaction / assistive-technology testing needed:** true / false / false / true
- **Normative criterion:** [2.4.4 Link Purpose (In Context)](https://www.w3.org/TR/WCAG22/#link-purpose-in-context)
- **Understanding:** [Understanding 2.4.4](https://www.w3.org/WAI/WCAG22/Understanding/link-purpose-in-context.html)
- **Associated axe rules** (all exact WCAG-tagged rules in package metadata):
  - [`area-alt`](https://dequeuniversity.com/rules/axe/4.14/area-alt?application=axeAPI) — package enabled: `true`; scanner: `selected`; effective: `true`; tags: `cat.text-alternatives`, `wcag2a`, `wcag244`, `wcag412`, `section508`, `section508.22.a`, `TTv5`, `TT6.a`, `EN-301-549`, `EN-9.2.4.4`, `EN-9.4.1.2`, `ACT`, `RGAAv4`, `RGAA-1.1.2`
  - [`link-name`](https://dequeuniversity.com/rules/axe/4.14/link-name?application=axeAPI) — package enabled: `true`; scanner: `selected`; effective: `true`; tags: `cat.name-role-value`, `wcag2a`, `wcag244`, `wcag412`, `section508`, `section508.22.a`, `TTv5`, `TT6.a`, `EN-301-549`, `EN-9.2.4.4`, `EN-9.4.1.2`, `ACT`, `RGAAv4`, `RGAA-6.2.1`
- **Implemented failure patterns (rule-description scope, not exhaustive):**
  - `area-alt`: Ensure <area> elements of image maps have alternative text ([rule help](https://dequeuniversity.com/rules/axe/4.14/area-alt?application=axeAPI))
  - `link-name`: Ensure links have discernible text ([rule help](https://dequeuniversity.com/rules/axe/4.14/link-name?application=axeAPI))
- **Limitations:**
  - A WCAG tag records the axe rule author's criterion association; it is not evidence that the rule covers the full success criterion.
  - The scanner records rule outcomes only when the rule runs and reports them. An absent result does not establish that the criterion passed.
- **Relevant existing tests:** No focused criterion-specific fixture assertion currently exists.
- **Outstanding gaps / next step:**
  - Validate the implemented checks with criterion-specific counterexamples against the criterion's Understanding guidance; retain manual review for aspects beyond their bounded scope.
  - No result from this scan may be described as WCAG conformance.
- **Evidence links:** [1](https://www.w3.org/TR/WCAG22/#link-purpose-in-context), [2](https://www.w3.org/WAI/WCAG22/Understanding/link-purpose-in-context.html), [3](https://dequeuniversity.com/rules/axe/4.14/area-alt?application=axeAPI), [4](https://dequeuniversity.com/rules/axe/4.14/link-name?application=axeAPI)

### 2.4.5 — Multiple Ways

- **Level / principle:** AA / Operable
- **Intent:** Provide more than one way to locate a page within a set of pages, subject to exceptions.
- **Coverage:** `manual_evaluation_required`
- **Questionnaire question IDs:** `pages.multiple_ways_to_find`
- **Automated check exists:** false
- **Axe check exists:** false
- **WebAble keyboard/focus check exists:** false
- **WebAble text/reflow check exists:** false
- **WebAble text-spacing check exists:** false
- **WebAble orientation check exists:** false
- **WebAble non-text contrast check exists:** false
- **WebAble hover/focus-content check exists:** false
- **WebAble target-size check exists:** false
- **Exact criterion tag:** `wcag245`
- **Manual / keyboard / interaction / assistive-technology testing needed:** true / false / false / false
- **Normative criterion:** [2.4.5 Multiple Ways](https://www.w3.org/TR/WCAG22/#multiple-ways)
- **Understanding:** [Understanding 2.4.5](https://www.w3.org/WAI/WCAG22/Understanding/multiple-ways.html)
- **Associated axe rules:** none with this criterion tag in axe-core 4.14.0 metadata.
- **Implemented failure patterns:** none mapped by an enabled, selected rule carrying this criterion's exact tag.
- **Limitations:**
  - No enabled axe rule selected by the current scanner carries this criterion's exact WCAG tag.
  - A WCAG tag records the axe rule author's criterion association; it is not evidence that the rule covers the full success criterion.
  - The scanner records rule outcomes only when the rule runs and reports them. An absent result does not establish that the criterion passed.
- **Relevant existing tests:** No focused criterion-specific fixture assertion currently exists.
- **Outstanding gaps / next step:**
  - Evaluate representative content and states with a trained reviewer and, where applicable, assistive technology; define bounded automated support only after validating it against WCAG guidance.
  - No result from this scan may be described as WCAG conformance.
- **Evidence links:** [1](https://www.w3.org/TR/WCAG22/#multiple-ways), [2](https://www.w3.org/WAI/WCAG22/Understanding/multiple-ways.html)

### 2.4.6 — Headings and Labels

- **Level / principle:** AA / Operable
- **Intent:** Use headings and labels that describe topic or purpose.
- **Coverage:** `manual_evaluation_required`
- **Questionnaire question IDs:** `content.headings_and_labels`
- **Automated check exists:** false
- **Axe check exists:** false
- **WebAble keyboard/focus check exists:** false
- **WebAble text/reflow check exists:** false
- **WebAble text-spacing check exists:** false
- **WebAble orientation check exists:** false
- **WebAble non-text contrast check exists:** false
- **WebAble hover/focus-content check exists:** false
- **WebAble target-size check exists:** false
- **Exact criterion tag:** `wcag246`
- **Manual / keyboard / interaction / assistive-technology testing needed:** true / false / false / false
- **Normative criterion:** [2.4.6 Headings and Labels](https://www.w3.org/TR/WCAG22/#headings-and-labels)
- **Understanding:** [Understanding 2.4.6](https://www.w3.org/WAI/WCAG22/Understanding/headings-and-labels.html)
- **Associated axe rules:** none with this criterion tag in axe-core 4.14.0 metadata.
- **Implemented failure patterns:** none mapped by an enabled, selected rule carrying this criterion's exact tag.
- **Limitations:**
  - No enabled axe rule selected by the current scanner carries this criterion's exact WCAG tag.
  - A WCAG tag records the axe rule author's criterion association; it is not evidence that the rule covers the full success criterion.
  - The scanner records rule outcomes only when the rule runs and reports them. An absent result does not establish that the criterion passed.
- **Relevant existing tests:** No focused criterion-specific fixture assertion currently exists.
- **Outstanding gaps / next step:**
  - Evaluate representative content and states with a trained reviewer and, where applicable, assistive technology; define bounded automated support only after validating it against WCAG guidance.
  - No result from this scan may be described as WCAG conformance.
- **Evidence links:** [1](https://www.w3.org/TR/WCAG22/#headings-and-labels), [2](https://www.w3.org/WAI/WCAG22/Understanding/headings-and-labels.html)

### 2.4.7 — Focus Visible

- **Level / principle:** AA / Operable
- **Intent:** Make the keyboard focus indicator visible.
- **Coverage:** `partial`
- **Questionnaire question IDs:** `widgets.keyboard_operation`
- **Automated check exists:** true
- **Axe check exists:** false
- **WebAble keyboard/focus check exists:** true
- **WebAble text/reflow check exists:** false
- **WebAble text-spacing check exists:** false
- **WebAble orientation check exists:** false
- **WebAble non-text contrast check exists:** false
- **WebAble hover/focus-content check exists:** false
- **WebAble target-size check exists:** false
- **Exact criterion tag:** `wcag247`
- **Manual / keyboard / interaction / assistive-technology testing needed:** true / true / true / false
- **Normative criterion:** [2.4.7 Focus Visible](https://www.w3.org/TR/WCAG22/#focus-visible)
- **Understanding:** [Understanding 2.4.7](https://www.w3.org/WAI/WCAG22/Understanding/focus-visible.html)
- **Associated axe rules:** none with this criterion tag in axe-core 4.14.0 metadata.
- **Implemented failure patterns:** none mapped by an enabled, selected rule carrying this criterion's exact tag.
- **Bounded keyboard/focus checks:**
  - Keyboard focus state is compared with a limited set of computed CSS indicator properties.
- **Limitations:**
  - No enabled axe rule selected by the current scanner carries this criterion's exact WCAG tag; the listed WebAble probes are separate, bounded evidence and do not establish criterion conformance.
  - A WCAG tag records the axe rule author's criterion association; it is not evidence that the rule covers the full success criterion.
  - The scanner records rule outcomes only when the rule runs and reports them. An absent result does not establish that the criterion passed.
- **Relevant existing tests:** No focused criterion-specific fixture assertion currently exists.
- **Outstanding gaps / next step:**
  - Validate the implemented checks with criterion-specific counterexamples against the criterion's Understanding guidance; retain manual review for aspects beyond their bounded scope.
  - No result from this scan may be described as WCAG conformance.
- **Evidence links:** [1](https://www.w3.org/TR/WCAG22/#focus-visible), [2](https://www.w3.org/WAI/WCAG22/Understanding/focus-visible.html)

### 2.4.11 — Focus Not Obscured (Minimum)

- **Level / principle:** AA / Operable
- **Intent:** Ensure a focused component is not entirely hidden by author-created content.
- **Coverage:** `partial`
- **Questionnaire question IDs:** `widgets.focus_not_obscured`
- **Automated check exists:** true
- **Axe check exists:** false
- **WebAble keyboard/focus check exists:** true
- **WebAble text/reflow check exists:** false
- **WebAble text-spacing check exists:** false
- **WebAble orientation check exists:** false
- **WebAble non-text contrast check exists:** false
- **WebAble hover/focus-content check exists:** false
- **WebAble target-size check exists:** false
- **Exact criterion tag:** `wcag2411`
- **Manual / keyboard / interaction / assistive-technology testing needed:** true / true / true / false
- **Normative criterion:** [2.4.11 Focus Not Obscured (Minimum)](https://www.w3.org/TR/WCAG22/#focus-not-obscured-minimum)
- **Understanding:** [Understanding 2.4.11](https://www.w3.org/WAI/WCAG22/Understanding/focus-not-obscured-minimum.html)
- **Associated axe rules:** none with this criterion tag in axe-core 4.14.0 metadata.
- **Implemented failure patterns:** none mapped by an enabled, selected rule carrying this criterion's exact tag.
- **Bounded keyboard/focus checks:**
  - Samples a 5x5 interior hit-test grid for each keyboard-focused target, records its bounding rectangle and viewport, and identifies layered elements intercepting samples.
  - Classifies a full-cover candidate as a high-confidence failure only when one layered element covers the entire in-viewport target, intercepts every sample, has a fully opaque computed background and effective opacity of 1, and has no detected clip-path or mask; partial, translucent, clipped, or otherwise ambiguous overlap requires manual review.
- **Limitations:**
  - No enabled axe rule selected by the current scanner carries this criterion's exact WCAG tag; the listed WebAble probes are separate, bounded evidence and do not establish criterion conformance.
  - A WCAG tag records the axe rule author's criterion association; it is not evidence that the rule covers the full success criterion.
  - The scanner records rule outcomes only when the rule runs and reports them. An absent result does not establish that the criterion passed.
- **Relevant existing tests:** `tests/test_capture.py::test_keyboard_audit_reports_focus_obscuration_for_review`, `tests/test_capture.py::test_keyboard_audit_confirms_opaque_full_cover_with_evidence`, `tests/test_capture.py::test_keyboard_audit_classifies_sticky_header_overlap_as_potential`, `tests/test_capture.py::test_keyboard_audit_detects_opaque_dialog_cover`, `tests/test_capture.py::test_keyboard_audit_reports_no_sampled_occlusion_without_overlay`
- **Outstanding gaps / next step:**
  - Validate the implemented checks with criterion-specific counterexamples against the criterion's Understanding guidance; retain manual review for aspects beyond their bounded scope.
  - No result from this scan may be described as WCAG conformance.
- **Evidence links:** [1](https://www.w3.org/TR/WCAG22/#focus-not-obscured-minimum), [2](https://www.w3.org/WAI/WCAG22/Understanding/focus-not-obscured-minimum.html)

### 2.5.1 — Pointer Gestures

- **Level / principle:** A / Operable
- **Intent:** Provide a single-pointer alternative for multipoint or path-based gestures, except where essential.
- **Coverage:** `manual_evaluation_required`
- **Questionnaire question IDs:** `pointer.gesture_alternative`
- **Automated check exists:** false
- **Axe check exists:** false
- **WebAble keyboard/focus check exists:** false
- **WebAble text/reflow check exists:** false
- **WebAble text-spacing check exists:** false
- **WebAble orientation check exists:** false
- **WebAble non-text contrast check exists:** false
- **WebAble hover/focus-content check exists:** false
- **WebAble target-size check exists:** false
- **Exact criterion tag:** `wcag251`
- **Manual / keyboard / interaction / assistive-technology testing needed:** true / true / true / false
- **Normative criterion:** [2.5.1 Pointer Gestures](https://www.w3.org/TR/WCAG22/#pointer-gestures)
- **Understanding:** [Understanding 2.5.1](https://www.w3.org/WAI/WCAG22/Understanding/pointer-gestures.html)
- **Associated axe rules:** none with this criterion tag in axe-core 4.14.0 metadata.
- **Implemented failure patterns:** none mapped by an enabled, selected rule carrying this criterion's exact tag.
- **Limitations:**
  - No enabled axe rule selected by the current scanner carries this criterion's exact WCAG tag.
  - A WCAG tag records the axe rule author's criterion association; it is not evidence that the rule covers the full success criterion.
  - The scanner records rule outcomes only when the rule runs and reports them. An absent result does not establish that the criterion passed.
- **Relevant existing tests:** No focused criterion-specific fixture assertion currently exists.
- **Outstanding gaps / next step:**
  - Evaluate representative content and states with a trained reviewer and, where applicable, assistive technology; define bounded automated support only after validating it against WCAG guidance.
  - No result from this scan may be described as WCAG conformance.
- **Evidence links:** [1](https://www.w3.org/TR/WCAG22/#pointer-gestures), [2](https://www.w3.org/WAI/WCAG22/Understanding/pointer-gestures.html)

### 2.5.2 — Pointer Cancellation

- **Level / principle:** A / Operable
- **Intent:** Support at least one specified safeguard against accidental pointer activation.
- **Coverage:** `manual_evaluation_required`
- **Questionnaire question IDs:** `pointer.cancellation`
- **Automated check exists:** false
- **Axe check exists:** false
- **WebAble keyboard/focus check exists:** false
- **WebAble text/reflow check exists:** false
- **WebAble text-spacing check exists:** false
- **WebAble orientation check exists:** false
- **WebAble non-text contrast check exists:** false
- **WebAble hover/focus-content check exists:** false
- **WebAble target-size check exists:** false
- **Exact criterion tag:** `wcag252`
- **Manual / keyboard / interaction / assistive-technology testing needed:** true / true / true / false
- **Normative criterion:** [2.5.2 Pointer Cancellation](https://www.w3.org/TR/WCAG22/#pointer-cancellation)
- **Understanding:** [Understanding 2.5.2](https://www.w3.org/WAI/WCAG22/Understanding/pointer-cancellation.html)
- **Associated axe rules:** none with this criterion tag in axe-core 4.14.0 metadata.
- **Implemented failure patterns:** none mapped by an enabled, selected rule carrying this criterion's exact tag.
- **Limitations:**
  - No enabled axe rule selected by the current scanner carries this criterion's exact WCAG tag.
  - A WCAG tag records the axe rule author's criterion association; it is not evidence that the rule covers the full success criterion.
  - The scanner records rule outcomes only when the rule runs and reports them. An absent result does not establish that the criterion passed.
- **Relevant existing tests:** No focused criterion-specific fixture assertion currently exists.
- **Outstanding gaps / next step:**
  - Evaluate representative content and states with a trained reviewer and, where applicable, assistive technology; define bounded automated support only after validating it against WCAG guidance.
  - No result from this scan may be described as WCAG conformance.
- **Evidence links:** [1](https://www.w3.org/TR/WCAG22/#pointer-cancellation), [2](https://www.w3.org/WAI/WCAG22/Understanding/pointer-cancellation.html)

### 2.5.3 — Label in Name

- **Level / principle:** A / Operable
- **Intent:** Include visible text labels in the accessible names of applicable controls.
- **Coverage:** `partial`
- **Questionnaire question IDs:** `widgets.label_in_accessible_name`
- **Automated check exists:** true
- **Axe check exists:** true
- **WebAble keyboard/focus check exists:** false
- **WebAble text/reflow check exists:** false
- **WebAble text-spacing check exists:** false
- **WebAble orientation check exists:** false
- **WebAble non-text contrast check exists:** false
- **WebAble hover/focus-content check exists:** false
- **WebAble target-size check exists:** false
- **Exact criterion tag:** `wcag253`
- **Manual / keyboard / interaction / assistive-technology testing needed:** true / false / false / true
- **Normative criterion:** [2.5.3 Label in Name](https://www.w3.org/TR/WCAG22/#label-in-name)
- **Understanding:** [Understanding 2.5.3](https://www.w3.org/WAI/WCAG22/Understanding/label-in-name.html)
- **Associated axe rules** (all exact WCAG-tagged rules in package metadata):
  - [`label-content-name-mismatch`](https://dequeuniversity.com/rules/axe/4.14/label-content-name-mismatch?application=axeAPI) — package enabled: `true`; scanner: `selected`; effective: `true`; tags: `cat.semantics`, `wcag21a`, `wcag253`, `EN-301-549`, `EN-9.2.5.3`, `RGAAv4`, `RGAA-6.1.5`
- **Implemented failure patterns (rule-description scope, not exhaustive):**
  - `label-content-name-mismatch`: Ensure that elements labelled through their content must have their visible text as part of their accessible name ([rule help](https://dequeuniversity.com/rules/axe/4.14/label-content-name-mismatch?application=axeAPI))
- **Limitations:**
  - A WCAG tag records the axe rule author's criterion association; it is not evidence that the rule covers the full success criterion.
  - The scanner records rule outcomes only when the rule runs and reports them. An absent result does not establish that the criterion passed.
- **Relevant existing tests:** No focused criterion-specific fixture assertion currently exists.
- **Outstanding gaps / next step:**
  - Validate the implemented checks with criterion-specific counterexamples against the criterion's Understanding guidance; retain manual review for aspects beyond their bounded scope.
  - No result from this scan may be described as WCAG conformance.
- **Evidence links:** [1](https://www.w3.org/TR/WCAG22/#label-in-name), [2](https://www.w3.org/WAI/WCAG22/Understanding/label-in-name.html), [3](https://dequeuniversity.com/rules/axe/4.14/label-content-name-mismatch?application=axeAPI)

### 2.5.4 — Motion Actuation

- **Level / principle:** A / Operable
- **Intent:** Provide an alternative to functionality triggered by device motion or user gestures, with exceptions.
- **Coverage:** `manual_evaluation_required`
- **Questionnaire question IDs:** `motion.actuation_alternative`
- **Automated check exists:** false
- **Axe check exists:** false
- **WebAble keyboard/focus check exists:** false
- **WebAble text/reflow check exists:** false
- **WebAble text-spacing check exists:** false
- **WebAble orientation check exists:** false
- **WebAble non-text contrast check exists:** false
- **WebAble hover/focus-content check exists:** false
- **WebAble target-size check exists:** false
- **Exact criterion tag:** `wcag254`
- **Manual / keyboard / interaction / assistive-technology testing needed:** true / true / true / false
- **Normative criterion:** [2.5.4 Motion Actuation](https://www.w3.org/TR/WCAG22/#motion-actuation)
- **Understanding:** [Understanding 2.5.4](https://www.w3.org/WAI/WCAG22/Understanding/motion-actuation.html)
- **Associated axe rules:** none with this criterion tag in axe-core 4.14.0 metadata.
- **Implemented failure patterns:** none mapped by an enabled, selected rule carrying this criterion's exact tag.
- **Limitations:**
  - No enabled axe rule selected by the current scanner carries this criterion's exact WCAG tag.
  - A WCAG tag records the axe rule author's criterion association; it is not evidence that the rule covers the full success criterion.
  - The scanner records rule outcomes only when the rule runs and reports them. An absent result does not establish that the criterion passed.
- **Relevant existing tests:** No focused criterion-specific fixture assertion currently exists.
- **Outstanding gaps / next step:**
  - Evaluate representative content and states with a trained reviewer and, where applicable, assistive technology; define bounded automated support only after validating it against WCAG guidance.
  - No result from this scan may be described as WCAG conformance.
- **Evidence links:** [1](https://www.w3.org/TR/WCAG22/#motion-actuation), [2](https://www.w3.org/WAI/WCAG22/Understanding/motion-actuation.html)

### 2.5.7 — Dragging Movements

- **Level / principle:** AA / Operable
- **Intent:** Provide a single-pointer alternative for functionality that uses dragging, unless dragging is essential.
- **Coverage:** `manual_evaluation_required`
- **Questionnaire question IDs:** `dragging.alternative`
- **Automated check exists:** false
- **Axe check exists:** false
- **WebAble keyboard/focus check exists:** false
- **WebAble text/reflow check exists:** false
- **WebAble text-spacing check exists:** false
- **WebAble orientation check exists:** false
- **WebAble non-text contrast check exists:** false
- **WebAble hover/focus-content check exists:** false
- **WebAble target-size check exists:** false
- **Exact criterion tag:** `wcag257`
- **Manual / keyboard / interaction / assistive-technology testing needed:** true / true / true / false
- **Normative criterion:** [2.5.7 Dragging Movements](https://www.w3.org/TR/WCAG22/#dragging-movements)
- **Understanding:** [Understanding 2.5.7](https://www.w3.org/WAI/WCAG22/Understanding/dragging-movements.html)
- **Associated axe rules:** none with this criterion tag in axe-core 4.14.0 metadata.
- **Implemented failure patterns:** none mapped by an enabled, selected rule carrying this criterion's exact tag.
- **Limitations:**
  - No enabled axe rule selected by the current scanner carries this criterion's exact WCAG tag.
  - A WCAG tag records the axe rule author's criterion association; it is not evidence that the rule covers the full success criterion.
  - The scanner records rule outcomes only when the rule runs and reports them. An absent result does not establish that the criterion passed.
- **Relevant existing tests:** No focused criterion-specific fixture assertion currently exists.
- **Outstanding gaps / next step:**
  - Evaluate representative content and states with a trained reviewer and, where applicable, assistive technology; define bounded automated support only after validating it against WCAG guidance.
  - No result from this scan may be described as WCAG conformance.
- **Evidence links:** [1](https://www.w3.org/TR/WCAG22/#dragging-movements), [2](https://www.w3.org/WAI/WCAG22/Understanding/dragging-movements.html)

### 2.5.8 — Target Size (Minimum)

- **Level / principle:** AA / Operable
- **Intent:** Ensure pointer targets meet minimum size or spacing requirements, subject to exceptions.
- **Coverage:** `partial`
- **Questionnaire question IDs:** `controls.target_size_context`, `widgets.target_size_exceptions`
- **Automated check exists:** true
- **Axe check exists:** false
- **WebAble keyboard/focus check exists:** false
- **WebAble text/reflow check exists:** false
- **WebAble text-spacing check exists:** false
- **WebAble orientation check exists:** false
- **WebAble non-text contrast check exists:** false
- **WebAble hover/focus-content check exists:** false
- **WebAble target-size check exists:** true
- **Exact criterion tag:** `wcag258`
- **Manual / keyboard / interaction / assistive-technology testing needed:** true / false / false / false
- **Normative criterion:** [2.5.8 Target Size (Minimum)](https://www.w3.org/TR/WCAG22/#target-size-minimum)
- **Understanding:** [Understanding 2.5.8](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html)
- **Associated axe rules** (all exact WCAG-tagged rules in package metadata):
  - [`target-size`](https://dequeuniversity.com/rules/axe/4.14/target-size?application=axeAPI) — package enabled: `false`; scanner: `selected`; effective: `false`; tags: `cat.sensory-and-visual-cues`, `wcag22aa`, `wcag258`, `EN-301-549v4`, `EN-9.2.5.8`
- **Implemented failure patterns:** none mapped by an enabled, selected rule carrying this criterion's exact tag.
- **Bounded target-size checks:**
  - Measures visible, enabled pointer-target bounding boxes and reports targets narrower or shorter than 24 CSS px for review; WCAG exceptions and actual target spacing are not evaluated.
- **Limitations:**
  - No enabled axe rule selected by the current scanner carries this criterion's exact WCAG tag; the listed WebAble probes are separate, bounded evidence and do not establish criterion conformance.
  - A WCAG tag records the axe rule author's criterion association; it is not evidence that the rule covers the full success criterion.
  - The scanner records rule outcomes only when the rule runs and reports them. An absent result does not establish that the criterion passed.
- **Relevant existing tests:** `tests/test_capture.py::test_target_size_audit_reports_small_visible_target_for_review`, `tests/test_capture.py::test_target_size_audit_does_not_flag_adequate_target`
- **Outstanding gaps / next step:**
  - Validate the implemented checks with criterion-specific counterexamples against the criterion's Understanding guidance; retain manual review for aspects beyond their bounded scope.
  - No result from this scan may be described as WCAG conformance.
- **Evidence links:** [1](https://www.w3.org/TR/WCAG22/#target-size-minimum), [2](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html)

### 3.1.1 — Language of Page

- **Level / principle:** A / Understandable
- **Intent:** Programmatically determine the default human language of each page.
- **Coverage:** `partial`
- **Questionnaire question IDs:** `language.parts`
- **Automated check exists:** true
- **Axe check exists:** true
- **WebAble keyboard/focus check exists:** false
- **WebAble text/reflow check exists:** false
- **WebAble text-spacing check exists:** false
- **WebAble orientation check exists:** false
- **WebAble non-text contrast check exists:** false
- **WebAble hover/focus-content check exists:** false
- **WebAble target-size check exists:** false
- **Exact criterion tag:** `wcag311`
- **Manual / keyboard / interaction / assistive-technology testing needed:** true / false / false / true
- **Normative criterion:** [3.1.1 Language of Page](https://www.w3.org/TR/WCAG22/#language-of-page)
- **Understanding:** [Understanding 3.1.1](https://www.w3.org/WAI/WCAG22/Understanding/language-of-page.html)
- **Associated axe rules** (all exact WCAG-tagged rules in package metadata):
  - [`html-has-lang`](https://dequeuniversity.com/rules/axe/4.14/html-has-lang?application=axeAPI) — package enabled: `true`; scanner: `selected`; effective: `true`; tags: `cat.language`, `wcag2a`, `wcag311`, `TTv5`, `TT11.a`, `EN-301-549`, `EN-9.3.1.1`, `ACT`, `RGAAv4`, `RGAA-8.3.1`
  - [`html-lang-valid`](https://dequeuniversity.com/rules/axe/4.14/html-lang-valid?application=axeAPI) — package enabled: `true`; scanner: `selected`; effective: `true`; tags: `cat.language`, `wcag2a`, `wcag311`, `TTv5`, `TT11.a`, `EN-301-549`, `EN-9.3.1.1`, `ACT`, `RGAAv4`, `RGAA-8.4.1`
  - [`html-xml-lang-mismatch`](https://dequeuniversity.com/rules/axe/4.14/html-xml-lang-mismatch?application=axeAPI) — package enabled: `true`; scanner: `selected`; effective: `true`; tags: `cat.language`, `wcag2a`, `wcag311`, `EN-301-549`, `EN-9.3.1.1`, `ACT`, `RGAAv4`, `RGAA-8.3.1`
- **Implemented failure patterns (rule-description scope, not exhaustive):**
  - `html-has-lang`: Ensure every HTML document has a lang attribute ([rule help](https://dequeuniversity.com/rules/axe/4.14/html-has-lang?application=axeAPI))
  - `html-lang-valid`: Ensure the lang attribute of the <html> element has a valid value ([rule help](https://dequeuniversity.com/rules/axe/4.14/html-lang-valid?application=axeAPI))
  - `html-xml-lang-mismatch`: Ensure that HTML elements with both valid lang and xml:lang attributes agree on the base language of the page ([rule help](https://dequeuniversity.com/rules/axe/4.14/html-xml-lang-mismatch?application=axeAPI))
- **Limitations:**
  - A WCAG tag records the axe rule author's criterion association; it is not evidence that the rule covers the full success criterion.
  - The scanner records rule outcomes only when the rule runs and reports them. An absent result does not establish that the criterion passed.
- **Relevant existing tests:** No focused criterion-specific fixture assertion currently exists.
- **Outstanding gaps / next step:**
  - Validate the implemented checks with criterion-specific counterexamples against the criterion's Understanding guidance; retain manual review for aspects beyond their bounded scope.
  - No result from this scan may be described as WCAG conformance.
- **Evidence links:** [1](https://www.w3.org/TR/WCAG22/#language-of-page), [2](https://www.w3.org/WAI/WCAG22/Understanding/language-of-page.html), [3](https://dequeuniversity.com/rules/axe/4.14/html-has-lang?application=axeAPI), [4](https://dequeuniversity.com/rules/axe/4.14/html-lang-valid?application=axeAPI), [5](https://dequeuniversity.com/rules/axe/4.14/html-xml-lang-mismatch?application=axeAPI)

### 3.1.2 — Language of Parts

- **Level / principle:** AA / Understandable
- **Intent:** Programmatically identify changes in the language of passages or phrases, with exceptions.
- **Coverage:** `partial`
- **Questionnaire question IDs:** `language.parts`
- **Automated check exists:** true
- **Axe check exists:** true
- **WebAble keyboard/focus check exists:** false
- **WebAble text/reflow check exists:** false
- **WebAble text-spacing check exists:** false
- **WebAble orientation check exists:** false
- **WebAble non-text contrast check exists:** false
- **WebAble hover/focus-content check exists:** false
- **WebAble target-size check exists:** false
- **Exact criterion tag:** `wcag312`
- **Manual / keyboard / interaction / assistive-technology testing needed:** true / false / false / true
- **Normative criterion:** [3.1.2 Language of Parts](https://www.w3.org/TR/WCAG22/#language-of-parts)
- **Understanding:** [Understanding 3.1.2](https://www.w3.org/WAI/WCAG22/Understanding/language-of-parts.html)
- **Associated axe rules** (all exact WCAG-tagged rules in package metadata):
  - [`valid-lang`](https://dequeuniversity.com/rules/axe/4.14/valid-lang?application=axeAPI) — package enabled: `true`; scanner: `selected`; effective: `true`; tags: `cat.language`, `wcag2aa`, `wcag312`, `TTv5`, `TT11.b`, `EN-301-549`, `EN-9.3.1.2`, `ACT`, `RGAAv4`, `RGAA-8.8.1`
- **Implemented failure patterns (rule-description scope, not exhaustive):**
  - `valid-lang`: Ensure lang attributes have valid values ([rule help](https://dequeuniversity.com/rules/axe/4.14/valid-lang?application=axeAPI))
- **Limitations:**
  - A WCAG tag records the axe rule author's criterion association; it is not evidence that the rule covers the full success criterion.
  - The scanner records rule outcomes only when the rule runs and reports them. An absent result does not establish that the criterion passed.
- **Relevant existing tests:** No focused criterion-specific fixture assertion currently exists.
- **Outstanding gaps / next step:**
  - Validate the implemented checks with criterion-specific counterexamples against the criterion's Understanding guidance; retain manual review for aspects beyond their bounded scope.
  - No result from this scan may be described as WCAG conformance.
- **Evidence links:** [1](https://www.w3.org/TR/WCAG22/#language-of-parts), [2](https://www.w3.org/WAI/WCAG22/Understanding/language-of-parts.html), [3](https://dequeuniversity.com/rules/axe/4.14/valid-lang?application=axeAPI)

### 3.2.1 — On Focus

- **Level / principle:** A / Understandable
- **Intent:** Avoid a change of context solely because a component receives focus.
- **Coverage:** `manual_evaluation_required`
- **Questionnaire question IDs:** `widgets.no_unexpected_change_on_focus`
- **Automated check exists:** false
- **Axe check exists:** false
- **WebAble keyboard/focus check exists:** false
- **WebAble text/reflow check exists:** false
- **WebAble text-spacing check exists:** false
- **WebAble orientation check exists:** false
- **WebAble non-text contrast check exists:** false
- **WebAble hover/focus-content check exists:** false
- **WebAble target-size check exists:** false
- **Exact criterion tag:** `wcag321`
- **Manual / keyboard / interaction / assistive-technology testing needed:** true / true / true / false
- **Normative criterion:** [3.2.1 On Focus](https://www.w3.org/TR/WCAG22/#on-focus)
- **Understanding:** [Understanding 3.2.1](https://www.w3.org/WAI/WCAG22/Understanding/on-focus.html)
- **Associated axe rules:** none with this criterion tag in axe-core 4.14.0 metadata.
- **Implemented failure patterns:** none mapped by an enabled, selected rule carrying this criterion's exact tag.
- **Limitations:**
  - No enabled axe rule selected by the current scanner carries this criterion's exact WCAG tag.
  - A WCAG tag records the axe rule author's criterion association; it is not evidence that the rule covers the full success criterion.
  - The scanner records rule outcomes only when the rule runs and reports them. An absent result does not establish that the criterion passed.
- **Relevant existing tests:** No focused criterion-specific fixture assertion currently exists.
- **Outstanding gaps / next step:**
  - Evaluate representative content and states with a trained reviewer and, where applicable, assistive technology; define bounded automated support only after validating it against WCAG guidance.
  - No result from this scan may be described as WCAG conformance.
- **Evidence links:** [1](https://www.w3.org/TR/WCAG22/#on-focus), [2](https://www.w3.org/WAI/WCAG22/Understanding/on-focus.html)

### 3.2.2 — On Input

- **Level / principle:** A / Understandable
- **Intent:** Avoid unexpected changes of context when changing a user-interface control setting, unless users were advised.
- **Coverage:** `manual_evaluation_required`
- **Questionnaire question IDs:** `forms.no_unexpected_change_on_input`
- **Automated check exists:** false
- **Axe check exists:** false
- **WebAble keyboard/focus check exists:** false
- **WebAble text/reflow check exists:** false
- **WebAble text-spacing check exists:** false
- **WebAble orientation check exists:** false
- **WebAble non-text contrast check exists:** false
- **WebAble hover/focus-content check exists:** false
- **WebAble target-size check exists:** false
- **Exact criterion tag:** `wcag322`
- **Manual / keyboard / interaction / assistive-technology testing needed:** true / false / true / false
- **Normative criterion:** [3.2.2 On Input](https://www.w3.org/TR/WCAG22/#on-input)
- **Understanding:** [Understanding 3.2.2](https://www.w3.org/WAI/WCAG22/Understanding/on-input.html)
- **Associated axe rules:** none with this criterion tag in axe-core 4.14.0 metadata.
- **Implemented failure patterns:** none mapped by an enabled, selected rule carrying this criterion's exact tag.
- **Limitations:**
  - No enabled axe rule selected by the current scanner carries this criterion's exact WCAG tag.
  - A WCAG tag records the axe rule author's criterion association; it is not evidence that the rule covers the full success criterion.
  - The scanner records rule outcomes only when the rule runs and reports them. An absent result does not establish that the criterion passed.
- **Relevant existing tests:** No focused criterion-specific fixture assertion currently exists.
- **Outstanding gaps / next step:**
  - Evaluate representative content and states with a trained reviewer and, where applicable, assistive technology; define bounded automated support only after validating it against WCAG guidance.
  - No result from this scan may be described as WCAG conformance.
- **Evidence links:** [1](https://www.w3.org/TR/WCAG22/#on-input), [2](https://www.w3.org/WAI/WCAG22/Understanding/on-input.html)

### 3.2.3 — Consistent Navigation

- **Level / principle:** AA / Understandable
- **Intent:** Keep repeated navigation mechanisms in a consistent relative order across pages.
- **Coverage:** `manual_evaluation_required`
- **Questionnaire question IDs:** `pages.consistent_navigation_order`
- **Automated check exists:** false
- **Axe check exists:** false
- **WebAble keyboard/focus check exists:** false
- **WebAble text/reflow check exists:** false
- **WebAble text-spacing check exists:** false
- **WebAble orientation check exists:** false
- **WebAble non-text contrast check exists:** false
- **WebAble hover/focus-content check exists:** false
- **WebAble target-size check exists:** false
- **Exact criterion tag:** `wcag323`
- **Manual / keyboard / interaction / assistive-technology testing needed:** true / false / false / false
- **Normative criterion:** [3.2.3 Consistent Navigation](https://www.w3.org/TR/WCAG22/#consistent-navigation)
- **Understanding:** [Understanding 3.2.3](https://www.w3.org/WAI/WCAG22/Understanding/consistent-navigation.html)
- **Associated axe rules:** none with this criterion tag in axe-core 4.14.0 metadata.
- **Implemented failure patterns:** none mapped by an enabled, selected rule carrying this criterion's exact tag.
- **Limitations:**
  - No enabled axe rule selected by the current scanner carries this criterion's exact WCAG tag.
  - A WCAG tag records the axe rule author's criterion association; it is not evidence that the rule covers the full success criterion.
  - The scanner records rule outcomes only when the rule runs and reports them. An absent result does not establish that the criterion passed.
- **Relevant existing tests:** No focused criterion-specific fixture assertion currently exists.
- **Outstanding gaps / next step:**
  - Evaluate representative content and states with a trained reviewer and, where applicable, assistive technology; define bounded automated support only after validating it against WCAG guidance.
  - No result from this scan may be described as WCAG conformance.
- **Evidence links:** [1](https://www.w3.org/TR/WCAG22/#consistent-navigation), [2](https://www.w3.org/WAI/WCAG22/Understanding/consistent-navigation.html)

### 3.2.4 — Consistent Identification

- **Level / principle:** AA / Understandable
- **Intent:** Identify components with the same functionality consistently across pages.
- **Coverage:** `manual_evaluation_required`
- **Questionnaire question IDs:** `pages.consistent_identification`
- **Automated check exists:** false
- **Axe check exists:** false
- **WebAble keyboard/focus check exists:** false
- **WebAble text/reflow check exists:** false
- **WebAble text-spacing check exists:** false
- **WebAble orientation check exists:** false
- **WebAble non-text contrast check exists:** false
- **WebAble hover/focus-content check exists:** false
- **WebAble target-size check exists:** false
- **Exact criterion tag:** `wcag324`
- **Manual / keyboard / interaction / assistive-technology testing needed:** true / false / false / false
- **Normative criterion:** [3.2.4 Consistent Identification](https://www.w3.org/TR/WCAG22/#consistent-identification)
- **Understanding:** [Understanding 3.2.4](https://www.w3.org/WAI/WCAG22/Understanding/consistent-identification.html)
- **Associated axe rules:** none with this criterion tag in axe-core 4.14.0 metadata.
- **Implemented failure patterns:** none mapped by an enabled, selected rule carrying this criterion's exact tag.
- **Limitations:**
  - No enabled axe rule selected by the current scanner carries this criterion's exact WCAG tag.
  - A WCAG tag records the axe rule author's criterion association; it is not evidence that the rule covers the full success criterion.
  - The scanner records rule outcomes only when the rule runs and reports them. An absent result does not establish that the criterion passed.
- **Relevant existing tests:** No focused criterion-specific fixture assertion currently exists.
- **Outstanding gaps / next step:**
  - Evaluate representative content and states with a trained reviewer and, where applicable, assistive technology; define bounded automated support only after validating it against WCAG guidance.
  - No result from this scan may be described as WCAG conformance.
- **Evidence links:** [1](https://www.w3.org/TR/WCAG22/#consistent-identification), [2](https://www.w3.org/WAI/WCAG22/Understanding/consistent-identification.html)

### 3.2.6 — Consistent Help

- **Level / principle:** AA / Understandable
- **Intent:** Keep specified help mechanisms in a consistent relative order across pages.
- **Coverage:** `manual_evaluation_required`
- **Questionnaire question IDs:** `pages.consistent_help_location`
- **Automated check exists:** false
- **Axe check exists:** false
- **WebAble keyboard/focus check exists:** false
- **WebAble text/reflow check exists:** false
- **WebAble text-spacing check exists:** false
- **WebAble orientation check exists:** false
- **WebAble non-text contrast check exists:** false
- **WebAble hover/focus-content check exists:** false
- **WebAble target-size check exists:** false
- **Exact criterion tag:** `wcag326`
- **Manual / keyboard / interaction / assistive-technology testing needed:** true / false / false / false
- **Normative criterion:** [3.2.6 Consistent Help](https://www.w3.org/TR/WCAG22/#consistent-help)
- **Understanding:** [Understanding 3.2.6](https://www.w3.org/WAI/WCAG22/Understanding/consistent-help.html)
- **Associated axe rules:** none with this criterion tag in axe-core 4.14.0 metadata.
- **Implemented failure patterns:** none mapped by an enabled, selected rule carrying this criterion's exact tag.
- **Limitations:**
  - No enabled axe rule selected by the current scanner carries this criterion's exact WCAG tag.
  - A WCAG tag records the axe rule author's criterion association; it is not evidence that the rule covers the full success criterion.
  - The scanner records rule outcomes only when the rule runs and reports them. An absent result does not establish that the criterion passed.
- **Relevant existing tests:** No focused criterion-specific fixture assertion currently exists.
- **Outstanding gaps / next step:**
  - Evaluate representative content and states with a trained reviewer and, where applicable, assistive technology; define bounded automated support only after validating it against WCAG guidance.
  - No result from this scan may be described as WCAG conformance.
- **Evidence links:** [1](https://www.w3.org/TR/WCAG22/#consistent-help), [2](https://www.w3.org/WAI/WCAG22/Understanding/consistent-help.html)

### 3.3.1 — Error Identification

- **Level / principle:** A / Understandable
- **Intent:** Identify input errors and describe them to users in text.
- **Coverage:** `manual_evaluation_required`
- **Questionnaire question IDs:** `forms.error_identification`
- **Automated check exists:** false
- **Axe check exists:** false
- **WebAble keyboard/focus check exists:** false
- **WebAble text/reflow check exists:** false
- **WebAble text-spacing check exists:** false
- **WebAble orientation check exists:** false
- **WebAble non-text contrast check exists:** false
- **WebAble hover/focus-content check exists:** false
- **WebAble target-size check exists:** false
- **Exact criterion tag:** `wcag331`
- **Manual / keyboard / interaction / assistive-technology testing needed:** true / false / true / true
- **Normative criterion:** [3.3.1 Error Identification](https://www.w3.org/TR/WCAG22/#error-identification)
- **Understanding:** [Understanding 3.3.1](https://www.w3.org/WAI/WCAG22/Understanding/error-identification.html)
- **Associated axe rules:** none with this criterion tag in axe-core 4.14.0 metadata.
- **Implemented failure patterns:** none mapped by an enabled, selected rule carrying this criterion's exact tag.
- **Limitations:**
  - No enabled axe rule selected by the current scanner carries this criterion's exact WCAG tag.
  - A WCAG tag records the axe rule author's criterion association; it is not evidence that the rule covers the full success criterion.
  - The scanner records rule outcomes only when the rule runs and reports them. An absent result does not establish that the criterion passed.
- **Relevant existing tests:** No focused criterion-specific fixture assertion currently exists.
- **Outstanding gaps / next step:**
  - Evaluate representative content and states with a trained reviewer and, where applicable, assistive technology; define bounded automated support only after validating it against WCAG guidance.
  - No result from this scan may be described as WCAG conformance.
- **Evidence links:** [1](https://www.w3.org/TR/WCAG22/#error-identification), [2](https://www.w3.org/WAI/WCAG22/Understanding/error-identification.html)

### 3.3.2 — Labels or Instructions

- **Level / principle:** A / Understandable
- **Intent:** Provide labels or instructions when content requires user input.
- **Coverage:** `partial`
- **Questionnaire question IDs:** `forms.labels_and_instructions`
- **Automated check exists:** true
- **Axe check exists:** true
- **WebAble keyboard/focus check exists:** false
- **WebAble text/reflow check exists:** false
- **WebAble text-spacing check exists:** false
- **WebAble orientation check exists:** false
- **WebAble non-text contrast check exists:** false
- **WebAble hover/focus-content check exists:** false
- **WebAble target-size check exists:** false
- **Exact criterion tag:** `wcag332`
- **Manual / keyboard / interaction / assistive-technology testing needed:** true / false / false / true
- **Normative criterion:** [3.3.2 Labels or Instructions](https://www.w3.org/TR/WCAG22/#labels-or-instructions)
- **Understanding:** [Understanding 3.3.2](https://www.w3.org/WAI/WCAG22/Understanding/labels-or-instructions.html)
- **Associated axe rules** (all exact WCAG-tagged rules in package metadata):
  - [`form-field-multiple-labels`](https://dequeuniversity.com/rules/axe/4.14/form-field-multiple-labels?application=axeAPI) — package enabled: `true`; scanner: `selected`; effective: `true`; tags: `cat.forms`, `wcag2a`, `wcag332`, `TTv5`, `TT5.c`, `EN-301-549`, `EN-9.3.3.2`, `RGAAv4`, `RGAA-11.2.1`
- **Implemented failure patterns (rule-description scope, not exhaustive):**
  - `form-field-multiple-labels`: Ensure form field does not have multiple label elements ([rule help](https://dequeuniversity.com/rules/axe/4.14/form-field-multiple-labels?application=axeAPI))
- **Limitations:**
  - A WCAG tag records the axe rule author's criterion association; it is not evidence that the rule covers the full success criterion.
  - The scanner records rule outcomes only when the rule runs and reports them. An absent result does not establish that the criterion passed.
- **Relevant existing tests:** No focused criterion-specific fixture assertion currently exists.
- **Outstanding gaps / next step:**
  - Validate the implemented checks with criterion-specific counterexamples against the criterion's Understanding guidance; retain manual review for aspects beyond their bounded scope.
  - No result from this scan may be described as WCAG conformance.
- **Evidence links:** [1](https://www.w3.org/TR/WCAG22/#labels-or-instructions), [2](https://www.w3.org/WAI/WCAG22/Understanding/labels-or-instructions.html), [3](https://dequeuniversity.com/rules/axe/4.14/form-field-multiple-labels?application=axeAPI)

### 3.3.3 — Error Suggestion

- **Level / principle:** AA / Understandable
- **Intent:** Provide correction suggestions when known and appropriate for input errors.
- **Coverage:** `manual_evaluation_required`
- **Questionnaire question IDs:** `forms.error_suggestions`
- **Automated check exists:** false
- **Axe check exists:** false
- **WebAble keyboard/focus check exists:** false
- **WebAble text/reflow check exists:** false
- **WebAble text-spacing check exists:** false
- **WebAble orientation check exists:** false
- **WebAble non-text contrast check exists:** false
- **WebAble hover/focus-content check exists:** false
- **WebAble target-size check exists:** false
- **Exact criterion tag:** `wcag333`
- **Manual / keyboard / interaction / assistive-technology testing needed:** true / false / true / false
- **Normative criterion:** [3.3.3 Error Suggestion](https://www.w3.org/TR/WCAG22/#error-suggestion)
- **Understanding:** [Understanding 3.3.3](https://www.w3.org/WAI/WCAG22/Understanding/error-suggestion.html)
- **Associated axe rules:** none with this criterion tag in axe-core 4.14.0 metadata.
- **Implemented failure patterns:** none mapped by an enabled, selected rule carrying this criterion's exact tag.
- **Limitations:**
  - No enabled axe rule selected by the current scanner carries this criterion's exact WCAG tag.
  - A WCAG tag records the axe rule author's criterion association; it is not evidence that the rule covers the full success criterion.
  - The scanner records rule outcomes only when the rule runs and reports them. An absent result does not establish that the criterion passed.
- **Relevant existing tests:** No focused criterion-specific fixture assertion currently exists.
- **Outstanding gaps / next step:**
  - Evaluate representative content and states with a trained reviewer and, where applicable, assistive technology; define bounded automated support only after validating it against WCAG guidance.
  - No result from this scan may be described as WCAG conformance.
- **Evidence links:** [1](https://www.w3.org/TR/WCAG22/#error-suggestion), [2](https://www.w3.org/WAI/WCAG22/Understanding/error-suggestion.html)

### 3.3.4 — Error Prevention (Legal, Financial, Data)

- **Level / principle:** AA / Understandable
- **Intent:** Provide specified safeguards for submissions involving legal commitments, financial transactions, or user-controlled data.
- **Coverage:** `manual_evaluation_required`
- **Questionnaire question IDs:** `transactions.error_prevention`
- **Automated check exists:** false
- **Axe check exists:** false
- **WebAble keyboard/focus check exists:** false
- **WebAble text/reflow check exists:** false
- **WebAble text-spacing check exists:** false
- **WebAble orientation check exists:** false
- **WebAble non-text contrast check exists:** false
- **WebAble hover/focus-content check exists:** false
- **WebAble target-size check exists:** false
- **Exact criterion tag:** `wcag334`
- **Manual / keyboard / interaction / assistive-technology testing needed:** true / false / true / false
- **Normative criterion:** [3.3.4 Error Prevention (Legal, Financial, Data)](https://www.w3.org/TR/WCAG22/#error-prevention-legal-financial-data)
- **Understanding:** [Understanding 3.3.4](https://www.w3.org/WAI/WCAG22/Understanding/error-prevention-legal-financial-data.html)
- **Associated axe rules:** none with this criterion tag in axe-core 4.14.0 metadata.
- **Implemented failure patterns:** none mapped by an enabled, selected rule carrying this criterion's exact tag.
- **Limitations:**
  - No enabled axe rule selected by the current scanner carries this criterion's exact WCAG tag.
  - A WCAG tag records the axe rule author's criterion association; it is not evidence that the rule covers the full success criterion.
  - The scanner records rule outcomes only when the rule runs and reports them. An absent result does not establish that the criterion passed.
- **Relevant existing tests:** No focused criterion-specific fixture assertion currently exists.
- **Outstanding gaps / next step:**
  - Evaluate representative content and states with a trained reviewer and, where applicable, assistive technology; define bounded automated support only after validating it against WCAG guidance.
  - No result from this scan may be described as WCAG conformance.
- **Evidence links:** [1](https://www.w3.org/TR/WCAG22/#error-prevention-legal-financial-data), [2](https://www.w3.org/WAI/WCAG22/Understanding/error-prevention-legal-financial-data.html)

### 3.3.7 — Redundant Entry

- **Level / principle:** A / Understandable
- **Intent:** Avoid requiring users to re-enter information already supplied in the same process, subject to exceptions.
- **Coverage:** `manual_evaluation_required`
- **Questionnaire question IDs:** `forms.repeated_entry`
- **Automated check exists:** false
- **Axe check exists:** false
- **WebAble keyboard/focus check exists:** false
- **WebAble text/reflow check exists:** false
- **WebAble text-spacing check exists:** false
- **WebAble orientation check exists:** false
- **WebAble non-text contrast check exists:** false
- **WebAble hover/focus-content check exists:** false
- **WebAble target-size check exists:** false
- **Exact criterion tag:** `wcag337`
- **Manual / keyboard / interaction / assistive-technology testing needed:** true / false / true / false
- **Normative criterion:** [3.3.7 Redundant Entry](https://www.w3.org/TR/WCAG22/#redundant-entry)
- **Understanding:** [Understanding 3.3.7](https://www.w3.org/WAI/WCAG22/Understanding/redundant-entry.html)
- **Associated axe rules:** none with this criterion tag in axe-core 4.14.0 metadata.
- **Implemented failure patterns:** none mapped by an enabled, selected rule carrying this criterion's exact tag.
- **Limitations:**
  - No enabled axe rule selected by the current scanner carries this criterion's exact WCAG tag.
  - A WCAG tag records the axe rule author's criterion association; it is not evidence that the rule covers the full success criterion.
  - The scanner records rule outcomes only when the rule runs and reports them. An absent result does not establish that the criterion passed.
- **Relevant existing tests:** No focused criterion-specific fixture assertion currently exists.
- **Outstanding gaps / next step:**
  - Evaluate representative content and states with a trained reviewer and, where applicable, assistive technology; define bounded automated support only after validating it against WCAG guidance.
  - No result from this scan may be described as WCAG conformance.
- **Evidence links:** [1](https://www.w3.org/TR/WCAG22/#redundant-entry), [2](https://www.w3.org/WAI/WCAG22/Understanding/redundant-entry.html)

### 3.3.8 — Accessible Authentication (Minimum)

- **Level / principle:** AA / Understandable
- **Intent:** Avoid requiring a cognitive function test for authentication unless an exception or alternative applies.
- **Coverage:** `manual_evaluation_required`
- **Questionnaire question IDs:** `authentication.cognitive_steps`
- **Automated check exists:** false
- **Axe check exists:** false
- **WebAble keyboard/focus check exists:** false
- **WebAble text/reflow check exists:** false
- **WebAble text-spacing check exists:** false
- **WebAble orientation check exists:** false
- **WebAble non-text contrast check exists:** false
- **WebAble hover/focus-content check exists:** false
- **WebAble target-size check exists:** false
- **Exact criterion tag:** `wcag338`
- **Manual / keyboard / interaction / assistive-technology testing needed:** true / false / true / false
- **Normative criterion:** [3.3.8 Accessible Authentication (Minimum)](https://www.w3.org/TR/WCAG22/#accessible-authentication-minimum)
- **Understanding:** [Understanding 3.3.8](https://www.w3.org/WAI/WCAG22/Understanding/accessible-authentication-minimum.html)
- **Associated axe rules:** none with this criterion tag in axe-core 4.14.0 metadata.
- **Implemented failure patterns:** none mapped by an enabled, selected rule carrying this criterion's exact tag.
- **Limitations:**
  - No enabled axe rule selected by the current scanner carries this criterion's exact WCAG tag.
  - A WCAG tag records the axe rule author's criterion association; it is not evidence that the rule covers the full success criterion.
  - The scanner records rule outcomes only when the rule runs and reports them. An absent result does not establish that the criterion passed.
- **Relevant existing tests:** No focused criterion-specific fixture assertion currently exists.
- **Outstanding gaps / next step:**
  - Evaluate representative content and states with a trained reviewer and, where applicable, assistive technology; define bounded automated support only after validating it against WCAG guidance.
  - No result from this scan may be described as WCAG conformance.
- **Evidence links:** [1](https://www.w3.org/TR/WCAG22/#accessible-authentication-minimum), [2](https://www.w3.org/WAI/WCAG22/Understanding/accessible-authentication-minimum.html)

### 4.1.2 — Name, Role, Value

- **Level / principle:** A / Robust
- **Intent:** Ensure name, role, and state information for user-interface components is programmatically determinable and changeable.
- **Coverage:** `partial`
- **Questionnaire question IDs:** `widgets.accessible_name_role_state`
- **Automated check exists:** true
- **Axe check exists:** true
- **WebAble keyboard/focus check exists:** false
- **WebAble text/reflow check exists:** false
- **WebAble text-spacing check exists:** false
- **WebAble orientation check exists:** false
- **WebAble non-text contrast check exists:** false
- **WebAble hover/focus-content check exists:** false
- **WebAble target-size check exists:** false
- **Exact criterion tag:** `wcag412`
- **Manual / keyboard / interaction / assistive-technology testing needed:** true / false / false / true
- **Normative criterion:** [4.1.2 Name, Role, Value](https://www.w3.org/TR/WCAG22/#name-role-value)
- **Understanding:** [Understanding 4.1.2](https://www.w3.org/WAI/WCAG22/Understanding/name-role-value.html)
- **Associated axe rules** (all exact WCAG-tagged rules in package metadata):
  - [`area-alt`](https://dequeuniversity.com/rules/axe/4.14/area-alt?application=axeAPI) — package enabled: `true`; scanner: `selected`; effective: `true`; tags: `cat.text-alternatives`, `wcag2a`, `wcag244`, `wcag412`, `section508`, `section508.22.a`, `TTv5`, `TT6.a`, `EN-301-549`, `EN-9.2.4.4`, `EN-9.4.1.2`, `ACT`, `RGAAv4`, `RGAA-1.1.2`
  - [`aria-allowed-attr`](https://dequeuniversity.com/rules/axe/4.14/aria-allowed-attr?application=axeAPI) — package enabled: `true`; scanner: `selected`; effective: `true`; tags: `cat.aria`, `wcag2a`, `wcag412`, `EN-301-549`, `EN-9.4.1.2`, `RGAAv4`, `RGAA-7.1.1`
  - [`aria-braille-equivalent`](https://dequeuniversity.com/rules/axe/4.14/aria-braille-equivalent?application=axeAPI) — package enabled: `true`; scanner: `selected`; effective: `true`; tags: `cat.aria`, `wcag2a`, `wcag412`, `EN-301-549`, `EN-9.4.1.2`
  - [`aria-command-name`](https://dequeuniversity.com/rules/axe/4.14/aria-command-name?application=axeAPI) — package enabled: `true`; scanner: `selected`; effective: `true`; tags: `cat.aria`, `wcag2a`, `wcag412`, `TTv5`, `TT6.a`, `EN-301-549`, `EN-9.4.1.2`, `ACT`, `RGAAv4`, `RGAA-11.9.1`
  - [`aria-conditional-attr`](https://dequeuniversity.com/rules/axe/4.14/aria-conditional-attr?application=axeAPI) — package enabled: `true`; scanner: `selected`; effective: `true`; tags: `cat.aria`, `wcag2a`, `wcag412`, `EN-301-549`, `EN-9.4.1.2`, `RGAAv4`, `RGAA-7.1.1`
  - [`aria-deprecated-role`](https://dequeuniversity.com/rules/axe/4.14/aria-deprecated-role?application=axeAPI) — package enabled: `true`; scanner: `selected`; effective: `true`; tags: `cat.aria`, `wcag2a`, `wcag412`, `EN-301-549`, `EN-9.4.1.2`, `RGAAv4`, `RGAA-7.1.1`
  - [`aria-hidden-body`](https://dequeuniversity.com/rules/axe/4.14/aria-hidden-body?application=axeAPI) — package enabled: `true`; scanner: `selected`; effective: `true`; tags: `cat.aria`, `wcag2a`, `wcag131`, `wcag412`, `EN-301-549`, `EN-9.1.3.1`, `EN-9.4.1.2`, `RGAAv4`, `RGAA-10.8.1`
  - [`aria-hidden-focus`](https://dequeuniversity.com/rules/axe/4.14/aria-hidden-focus?application=axeAPI) — package enabled: `true`; scanner: `selected`; effective: `true`; tags: `cat.name-role-value`, `wcag2a`, `wcag412`, `TTv5`, `TT6.a`, `EN-301-549`, `EN-9.4.1.2`, `RGAAv4`, `RGAA-10.8.1`
  - [`aria-input-field-name`](https://dequeuniversity.com/rules/axe/4.14/aria-input-field-name?application=axeAPI) — package enabled: `true`; scanner: `selected`; effective: `true`; tags: `cat.aria`, `wcag2a`, `wcag412`, `TTv5`, `TT5.c`, `EN-301-549`, `EN-9.4.1.2`, `ACT`, `RGAAv4`, `RGAA-11.1.1`
  - [`aria-prohibited-attr`](https://dequeuniversity.com/rules/axe/4.14/aria-prohibited-attr?application=axeAPI) — package enabled: `true`; scanner: `selected`; effective: `true`; tags: `cat.aria`, `wcag2a`, `wcag412`, `EN-301-549`, `EN-9.4.1.2`, `RGAAv4`, `RGAA-7.1.1`
  - [`aria-required-attr`](https://dequeuniversity.com/rules/axe/4.14/aria-required-attr?application=axeAPI) — package enabled: `true`; scanner: `selected`; effective: `true`; tags: `cat.aria`, `wcag2a`, `wcag412`, `EN-301-549`, `EN-9.4.1.2`, `RGAAv4`, `RGAA-7.1.1`
  - [`aria-roledescription`](https://dequeuniversity.com/rules/axe/4.14/aria-roledescription?application=axeAPI) — package enabled: `false`; scanner: `selected`; effective: `false`; tags: `cat.aria`, `wcag2a`, `wcag412`, `EN-301-549`, `EN-9.4.1.2`, `deprecated`
  - [`aria-roles`](https://dequeuniversity.com/rules/axe/4.14/aria-roles?application=axeAPI) — package enabled: `true`; scanner: `selected`; effective: `true`; tags: `cat.aria`, `wcag2a`, `wcag412`, `EN-301-549`, `EN-9.4.1.2`, `RGAAv4`, `RGAA-7.1.1`
  - [`aria-tab-name`](https://dequeuniversity.com/rules/axe/4.14/aria-tab-name?application=axeAPI) — package enabled: `true`; scanner: `selected`; effective: `true`; tags: `cat.aria`, `wcag2a`, `wcag412`, `TTv5`, `TT5.c`, `EN-301-549`, `EN-9.4.1.2`, `ACT`, `RGAAv4`, `RGAA-7.1.1`
  - [`aria-toggle-field-name`](https://dequeuniversity.com/rules/axe/4.14/aria-toggle-field-name?application=axeAPI) — package enabled: `true`; scanner: `selected`; effective: `true`; tags: `cat.aria`, `wcag2a`, `wcag412`, `TTv5`, `TT5.c`, `EN-301-549`, `EN-9.4.1.2`, `ACT`, `RGAAv4`, `RGAA-7.1.1`
  - [`aria-tooltip-name`](https://dequeuniversity.com/rules/axe/4.14/aria-tooltip-name?application=axeAPI) — package enabled: `true`; scanner: `selected`; effective: `true`; tags: `cat.aria`, `wcag2a`, `wcag412`, `EN-301-549`, `EN-9.4.1.2`
  - [`aria-valid-attr`](https://dequeuniversity.com/rules/axe/4.14/aria-valid-attr?application=axeAPI) — package enabled: `true`; scanner: `selected`; effective: `true`; tags: `cat.aria`, `wcag2a`, `wcag412`, `EN-301-549`, `EN-9.4.1.2`, `RGAAv4`, `RGAA-7.1.1`
  - [`aria-valid-attr-value`](https://dequeuniversity.com/rules/axe/4.14/aria-valid-attr-value?application=axeAPI) — package enabled: `true`; scanner: `selected`; effective: `true`; tags: `cat.aria`, `wcag2a`, `wcag412`, `EN-301-549`, `EN-9.4.1.2`, `RGAAv4`, `RGAA-7.1.1`
  - [`button-name`](https://dequeuniversity.com/rules/axe/4.14/button-name?application=axeAPI) — package enabled: `true`; scanner: `selected`; effective: `true`; tags: `cat.name-role-value`, `wcag2a`, `wcag412`, `section508`, `section508.22.a`, `TTv5`, `TT6.a`, `EN-301-549`, `EN-9.4.1.2`, `ACT`, `RGAAv4`, `RGAA-11.9.1`
  - [`duplicate-id-aria`](https://dequeuniversity.com/rules/axe/4.14/duplicate-id-aria?application=axeAPI) — package enabled: `true`; scanner: `selected`; effective: `true`; tags: `cat.parsing`, `wcag2a`, `wcag412`, `EN-301-549`, `EN-9.4.1.2`, `RGAAv4`, `RGAA-8.2.1`
  - [`frame-title`](https://dequeuniversity.com/rules/axe/4.14/frame-title?application=axeAPI) — package enabled: `true`; scanner: `selected`; effective: `true`; tags: `cat.text-alternatives`, `wcag2a`, `wcag412`, `section508`, `section508.22.i`, `TTv5`, `TT12.d`, `EN-301-549`, `EN-9.4.1.2`, `RGAAv4`, `RGAA-2.1.1`
  - [`frame-title-unique`](https://dequeuniversity.com/rules/axe/4.14/frame-title-unique?application=axeAPI) — package enabled: `true`; scanner: `selected`; effective: `true`; tags: `cat.text-alternatives`, `wcag2a`, `wcag412`, `TTv5`, `TT12.d`, `EN-301-549`, `EN-9.4.1.2`, `RGAAv4`, `RGAA-2.2.1`
  - [`input-button-name`](https://dequeuniversity.com/rules/axe/4.14/input-button-name?application=axeAPI) — package enabled: `true`; scanner: `selected`; effective: `true`; tags: `cat.name-role-value`, `wcag2a`, `wcag412`, `section508`, `section508.22.a`, `TTv5`, `TT5.c`, `EN-301-549`, `EN-9.4.1.2`, `ACT`, `RGAAv4`, `RGAA-11.9.1`
  - [`input-image-alt`](https://dequeuniversity.com/rules/axe/4.14/input-image-alt?application=axeAPI) — package enabled: `true`; scanner: `selected`; effective: `true`; tags: `cat.text-alternatives`, `wcag2a`, `wcag111`, `wcag412`, `section508`, `section508.22.a`, `TTv5`, `TT7.a`, `EN-301-549`, `EN-9.1.1.1`, `EN-9.4.1.2`, `ACT`, `RGAAv4`, `RGAA-1.1.3`
  - [`label`](https://dequeuniversity.com/rules/axe/4.14/label?application=axeAPI) — package enabled: `true`; scanner: `selected`; effective: `true`; tags: `cat.forms`, `wcag2a`, `wcag412`, `section508`, `section508.22.n`, `TTv5`, `TT5.c`, `EN-301-549`, `EN-9.4.1.2`, `ACT`, `RGAAv4`, `RGAA-11.1.1`
  - [`link-name`](https://dequeuniversity.com/rules/axe/4.14/link-name?application=axeAPI) — package enabled: `true`; scanner: `selected`; effective: `true`; tags: `cat.name-role-value`, `wcag2a`, `wcag244`, `wcag412`, `section508`, `section508.22.a`, `TTv5`, `TT6.a`, `EN-301-549`, `EN-9.2.4.4`, `EN-9.4.1.2`, `ACT`, `RGAAv4`, `RGAA-6.2.1`
  - [`nested-interactive`](https://dequeuniversity.com/rules/axe/4.14/nested-interactive?application=axeAPI) — package enabled: `true`; scanner: `selected`; effective: `true`; tags: `cat.keyboard`, `wcag2a`, `wcag412`, `TTv5`, `TT6.a`, `EN-301-549`, `EN-9.4.1.2`, `RGAAv4`, `RGAA-7.1.1`
  - [`select-name`](https://dequeuniversity.com/rules/axe/4.14/select-name?application=axeAPI) — package enabled: `true`; scanner: `selected`; effective: `true`; tags: `cat.forms`, `wcag2a`, `wcag412`, `section508`, `section508.22.n`, `TTv5`, `TT5.c`, `EN-301-549`, `EN-9.4.1.2`, `ACT`, `RGAAv4`, `RGAA-11.1.1`
  - [`summary-name`](https://dequeuniversity.com/rules/axe/4.14/summary-name?application=axeAPI) — package enabled: `true`; scanner: `selected`; effective: `true`; tags: `cat.name-role-value`, `wcag2a`, `wcag412`, `section508`, `section508.22.a`, `TTv5`, `TT6.a`, `EN-301-549`, `EN-9.4.1.2`
- **Implemented failure patterns (rule-description scope, not exhaustive):**
  - `area-alt`: Ensure <area> elements of image maps have alternative text ([rule help](https://dequeuniversity.com/rules/axe/4.14/area-alt?application=axeAPI))
  - `aria-allowed-attr`: Ensure an element's role supports its ARIA attributes ([rule help](https://dequeuniversity.com/rules/axe/4.14/aria-allowed-attr?application=axeAPI))
  - `aria-braille-equivalent`: Ensure aria-braillelabel and aria-brailleroledescription have a non-braille equivalent ([rule help](https://dequeuniversity.com/rules/axe/4.14/aria-braille-equivalent?application=axeAPI))
  - `aria-command-name`: Ensure every ARIA button, link and menuitem has an accessible name ([rule help](https://dequeuniversity.com/rules/axe/4.14/aria-command-name?application=axeAPI))
  - `aria-conditional-attr`: Ensure ARIA attributes are used as described in the specification of the element's role ([rule help](https://dequeuniversity.com/rules/axe/4.14/aria-conditional-attr?application=axeAPI))
  - `aria-deprecated-role`: Ensure elements do not use deprecated roles ([rule help](https://dequeuniversity.com/rules/axe/4.14/aria-deprecated-role?application=axeAPI))
  - `aria-hidden-body`: Ensure aria-hidden="true" is not present on the document body. ([rule help](https://dequeuniversity.com/rules/axe/4.14/aria-hidden-body?application=axeAPI))
  - `aria-hidden-focus`: Ensure aria-hidden elements are not focusable nor contain focusable elements ([rule help](https://dequeuniversity.com/rules/axe/4.14/aria-hidden-focus?application=axeAPI))
  - `aria-input-field-name`: Ensure every ARIA input field has an accessible name ([rule help](https://dequeuniversity.com/rules/axe/4.14/aria-input-field-name?application=axeAPI))
  - `aria-prohibited-attr`: Ensure ARIA attributes are not prohibited for an element's role ([rule help](https://dequeuniversity.com/rules/axe/4.14/aria-prohibited-attr?application=axeAPI))
  - `aria-required-attr`: Ensure elements with ARIA roles have all required ARIA attributes ([rule help](https://dequeuniversity.com/rules/axe/4.14/aria-required-attr?application=axeAPI))
  - `aria-roles`: Ensure all elements with a role attribute use a valid value ([rule help](https://dequeuniversity.com/rules/axe/4.14/aria-roles?application=axeAPI))
  - `aria-tab-name`: Ensure every ARIA tab node has an accessible name ([rule help](https://dequeuniversity.com/rules/axe/4.14/aria-tab-name?application=axeAPI))
  - `aria-toggle-field-name`: Ensure every ARIA toggle field has an accessible name ([rule help](https://dequeuniversity.com/rules/axe/4.14/aria-toggle-field-name?application=axeAPI))
  - `aria-tooltip-name`: Ensure every ARIA tooltip node has an accessible name ([rule help](https://dequeuniversity.com/rules/axe/4.14/aria-tooltip-name?application=axeAPI))
  - `aria-valid-attr`: Ensure attributes that begin with aria- are valid ARIA attributes ([rule help](https://dequeuniversity.com/rules/axe/4.14/aria-valid-attr?application=axeAPI))
  - `aria-valid-attr-value`: Ensure all ARIA attributes have valid values ([rule help](https://dequeuniversity.com/rules/axe/4.14/aria-valid-attr-value?application=axeAPI))
  - `button-name`: Ensure buttons have discernible text ([rule help](https://dequeuniversity.com/rules/axe/4.14/button-name?application=axeAPI))
  - `duplicate-id-aria`: Ensure every id attribute value used in ARIA and in labels is unique ([rule help](https://dequeuniversity.com/rules/axe/4.14/duplicate-id-aria?application=axeAPI))
  - `frame-title`: Ensure <iframe> and <frame> elements have an accessible name ([rule help](https://dequeuniversity.com/rules/axe/4.14/frame-title?application=axeAPI))
  - `frame-title-unique`: Ensure <iframe> and <frame> elements contain a unique title attribute ([rule help](https://dequeuniversity.com/rules/axe/4.14/frame-title-unique?application=axeAPI))
  - `input-button-name`: Ensure input buttons have discernible text ([rule help](https://dequeuniversity.com/rules/axe/4.14/input-button-name?application=axeAPI))
  - `input-image-alt`: Ensure <input type="image"> elements have alternative text ([rule help](https://dequeuniversity.com/rules/axe/4.14/input-image-alt?application=axeAPI))
  - `label`: Ensure every form element has a label ([rule help](https://dequeuniversity.com/rules/axe/4.14/label?application=axeAPI))
  - `link-name`: Ensure links have discernible text ([rule help](https://dequeuniversity.com/rules/axe/4.14/link-name?application=axeAPI))
  - `nested-interactive`: Ensure interactive controls are not nested as they are not always announced by screen readers or can cause focus problems for assistive technologies ([rule help](https://dequeuniversity.com/rules/axe/4.14/nested-interactive?application=axeAPI))
  - `select-name`: Ensure select element has an accessible name ([rule help](https://dequeuniversity.com/rules/axe/4.14/select-name?application=axeAPI))
  - `summary-name`: Ensure summary elements have discernible text ([rule help](https://dequeuniversity.com/rules/axe/4.14/summary-name?application=axeAPI))
- **Limitations:**
  - A WCAG tag records the axe rule author's criterion association; it is not evidence that the rule covers the full success criterion.
  - The scanner records rule outcomes only when the rule runs and reports them. An absent result does not establish that the criterion passed.
- **Relevant existing tests:** `tests/test_capture.py::test_accessibility_scan_preserves_axe_results_and_specific_evidence`
- **Outstanding gaps / next step:**
  - Validate the implemented checks with criterion-specific counterexamples against the criterion's Understanding guidance; retain manual review for aspects beyond their bounded scope.
  - No result from this scan may be described as WCAG conformance.
- **Evidence links:** [1](https://www.w3.org/TR/WCAG22/#name-role-value), [2](https://www.w3.org/WAI/WCAG22/Understanding/name-role-value.html), [3](https://dequeuniversity.com/rules/axe/4.14/area-alt?application=axeAPI), [4](https://dequeuniversity.com/rules/axe/4.14/aria-allowed-attr?application=axeAPI), [5](https://dequeuniversity.com/rules/axe/4.14/aria-braille-equivalent?application=axeAPI), [6](https://dequeuniversity.com/rules/axe/4.14/aria-command-name?application=axeAPI), [7](https://dequeuniversity.com/rules/axe/4.14/aria-conditional-attr?application=axeAPI), [8](https://dequeuniversity.com/rules/axe/4.14/aria-deprecated-role?application=axeAPI), [9](https://dequeuniversity.com/rules/axe/4.14/aria-hidden-body?application=axeAPI), [10](https://dequeuniversity.com/rules/axe/4.14/aria-hidden-focus?application=axeAPI), [11](https://dequeuniversity.com/rules/axe/4.14/aria-input-field-name?application=axeAPI), [12](https://dequeuniversity.com/rules/axe/4.14/aria-prohibited-attr?application=axeAPI), [13](https://dequeuniversity.com/rules/axe/4.14/aria-required-attr?application=axeAPI), [14](https://dequeuniversity.com/rules/axe/4.14/aria-roles?application=axeAPI), [15](https://dequeuniversity.com/rules/axe/4.14/aria-tab-name?application=axeAPI), [16](https://dequeuniversity.com/rules/axe/4.14/aria-toggle-field-name?application=axeAPI), [17](https://dequeuniversity.com/rules/axe/4.14/aria-tooltip-name?application=axeAPI), [18](https://dequeuniversity.com/rules/axe/4.14/aria-valid-attr-value?application=axeAPI), [19](https://dequeuniversity.com/rules/axe/4.14/aria-valid-attr?application=axeAPI), [20](https://dequeuniversity.com/rules/axe/4.14/button-name?application=axeAPI), [21](https://dequeuniversity.com/rules/axe/4.14/duplicate-id-aria?application=axeAPI), [22](https://dequeuniversity.com/rules/axe/4.14/frame-title-unique?application=axeAPI), [23](https://dequeuniversity.com/rules/axe/4.14/frame-title?application=axeAPI), [24](https://dequeuniversity.com/rules/axe/4.14/input-button-name?application=axeAPI), [25](https://dequeuniversity.com/rules/axe/4.14/input-image-alt?application=axeAPI), [26](https://dequeuniversity.com/rules/axe/4.14/label?application=axeAPI), [27](https://dequeuniversity.com/rules/axe/4.14/link-name?application=axeAPI), [28](https://dequeuniversity.com/rules/axe/4.14/nested-interactive?application=axeAPI), [29](https://dequeuniversity.com/rules/axe/4.14/select-name?application=axeAPI), [30](https://dequeuniversity.com/rules/axe/4.14/summary-name?application=axeAPI)

### 4.1.3 — Status Messages

- **Level / principle:** AA / Robust
- **Intent:** Make status messages programmatically determinable without requiring focus, using appropriate roles or properties.
- **Coverage:** `manual_evaluation_required`
- **Questionnaire question IDs:** `widgets.status_messages`
- **Automated check exists:** false
- **Axe check exists:** false
- **WebAble keyboard/focus check exists:** false
- **WebAble text/reflow check exists:** false
- **WebAble text-spacing check exists:** false
- **WebAble orientation check exists:** false
- **WebAble non-text contrast check exists:** false
- **WebAble hover/focus-content check exists:** false
- **WebAble target-size check exists:** false
- **Exact criterion tag:** `wcag413`
- **Manual / keyboard / interaction / assistive-technology testing needed:** true / false / true / true
- **Normative criterion:** [4.1.3 Status Messages](https://www.w3.org/TR/WCAG22/#status-messages)
- **Understanding:** [Understanding 4.1.3](https://www.w3.org/WAI/WCAG22/Understanding/status-messages.html)
- **Associated axe rules:** none with this criterion tag in axe-core 4.14.0 metadata.
- **Implemented failure patterns:** none mapped by an enabled, selected rule carrying this criterion's exact tag.
- **Limitations:**
  - No enabled axe rule selected by the current scanner carries this criterion's exact WCAG tag.
  - A WCAG tag records the axe rule author's criterion association; it is not evidence that the rule covers the full success criterion.
  - The scanner records rule outcomes only when the rule runs and reports them. An absent result does not establish that the criterion passed.
- **Relevant existing tests:** No focused criterion-specific fixture assertion currently exists.
- **Outstanding gaps / next step:**
  - Evaluate representative content and states with a trained reviewer and, where applicable, assistive technology; define bounded automated support only after validating it against WCAG guidance.
  - No result from this scan may be described as WCAG conformance.
- **Evidence links:** [1](https://www.w3.org/TR/WCAG22/#status-messages), [2](https://www.w3.org/WAI/WCAG22/Understanding/status-messages.html)

## Method and limitations

The 55 criterion identifiers, exact titles, levels, principles, and anchors are checked against the separate offline source transcription in `tests/fixtures/wcag22_criteria_source.json`. The mapping registry is derived from `axe-core@4.14.0` `getRules()` metadata. A rule is effective for this scanner only if the package reports it enabled, it has the exact criterion tag (`wcag` + criterion digits), and it also has one of the configured runOnly tags. The scanner configuration and inventory are validated offline in `tests/test_wcag22_inventory.py`.

The inventory's rule descriptions identify intended rule scope, not all failure conditions or all WCAG exceptions. Consult each linked axe rule help page and W3C Understanding document before interpreting evidence. A tag may be an association with only one aspect of a broad criterion; missing mappings are explicitly empty and do not imply a pass. Rule `incomplete` outcomes need human review and are not confirmed violations.

The 2.4.13 Focus Appearance criterion is Level AAA according to W3C and is therefore intentionally excluded from the A/AA criteria list. The keyboard/focus audit does not measure focus-indicator perimeter area or 3:1 contrast and does not implement 2.4.13.

### Scope exclusions

- [2.4.13 Focus Appearance](https://www.w3.org/TR/WCAG22/#focus-appearance) — Level AAA; excluded from this A/AA inventory.
- [4.1.1 Parsing](https://www.w3.org/TR/WCAG22/#parsing) — WCAG 2.2 obsolete criterion; not applicable to this inventory.

The current scan observes one settled rendered state per viewport and includes bounded text enlargement and a 320 CSS-pixel reflow probe. Actual browser zoom is not simulated; 256 CSS-pixel height testing is conditional on detecting a table or ARIA table/grid. The text override is not equivalent to every browser text-only zoom behavior. The scan does not automate all keyboard traversal/focus order, interactions, media inspection, site-wide comparisons, cognitive-function/authentication evaluation, or assistive-technology announcement testing. It does not establish that the selected page, a process, or a site conforms. Browser/runtime failures and evidence caps are represented separately by the API scan status.

### Source references

- [WCAG 2.2 Recommendation](https://www.w3.org/TR/WCAG22/)
- [W3C current WCAG Recommendation URL](https://www.w3.org/TR/WCAG/) (resolves to the WCAG 2.2 Recommendation)
- [WCAG 2.2 Understanding documents](https://www.w3.org/WAI/WCAG22/Understanding/)
- [W3C evaluation guidance](https://www.w3.org/WAI/test-evaluate/)
- [axe-core API and tag filtering](https://github.com/dequelabs/axe-core/blob/develop/doc/API.md)
- [axe-core rule descriptions](https://github.com/dequelabs/axe-core/blob/develop/doc/rule-descriptions.md)

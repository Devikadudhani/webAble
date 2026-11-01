"""Generate the WCAG inventory from the checked-in source list and pinned axe metadata."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.analyzers.hybrid_evaluation import QUESTIONNAIRE_QUESTIONS
SOURCE_PATH = ROOT / "tests" / "fixtures" / "wcag22_criteria_source.json"
JSON_PATH = ROOT / "docs" / "wcag-22-coverage-inventory.json"
MARKDOWN_PATH = ROOT / "docs" / "wcag-22-coverage-inventory.md"
SCANNER_TAGS = [
    "wcag2a",
    "wcag2aa",
    "wcag21a",
    "wcag21aa",
    "wcag22aa",
]

# These criteria need content, interaction, cross-page, media, or AT judgment
# and have no enabled selected rule with the criterion's own WCAG tag.
MANUAL_ONLY = {
    "1.2.1", "1.2.3", "1.2.4", "1.2.5",
    "1.3.2", "1.3.3", "1.4.5",
    "2.1.2", "2.1.4", "2.3.1", "2.4.3", "2.4.5",
    "2.4.6", "2.4.7", "2.4.11", "2.5.1", "2.5.2", "2.5.4", "2.5.7",
    "3.2.1", "3.2.2", "3.2.3", "3.2.4", "3.2.6",
    "3.3.1", "3.3.3", "3.3.4", "3.3.7", "3.3.8", "4.1.3",
}
KEYBOARD_REQUIRED = {
    "2.1.1", "2.1.2", "2.1.4", "2.4.3", "2.4.7", "2.4.11",
    "2.5.1", "2.5.2", "2.5.4", "2.5.7", "3.2.1",
}
INTERACTION_REQUIRED = {
    "1.2.2", "1.2.4", "1.3.4", "1.4.2", "1.4.4", "1.4.10",
    "1.4.12", "1.4.13", "2.1.1", "2.1.2", "2.1.4", "2.2.1",
    "2.2.2", "2.3.1", "2.4.3", "2.4.7", "2.4.11", "2.5.1",
    "2.5.2", "2.5.4", "2.5.7", "3.2.1", "3.2.2", "3.3.1",
    "3.3.3", "3.3.4", "3.3.7", "3.3.8", "4.1.3",
}
ASSISTIVE_TECHNOLOGY_REQUIRED = {
    "1.1.1", "1.3.1", "1.3.5", "2.1.1", "2.4.4", "2.5.3",
    "3.1.1", "3.1.2", "3.3.1", "3.3.2", "4.1.2", "4.1.3",
}
TESTS_BY_RULE = {
    "image-alt": [
        "tests/test_capture.py::test_accessibility_scan_preserves_axe_results_and_specific_evidence"
    ],
    "color-contrast": [
        "tests/test_capture.py::test_accessibility_scan_preserves_axe_results_and_specific_evidence"
    ],
    "aria-required-parent": [
        "tests/test_capture.py::test_accessibility_scan_preserves_axe_results_and_specific_evidence"
    ],
    "label": [
        "tests/test_capture.py::test_accessibility_scan_preserves_axe_results_and_specific_evidence"
    ],
    "button-name": [
        "tests/test_capture.py::test_accessibility_scan_preserves_axe_results_and_specific_evidence"
    ],
}
KEYBOARD_FOCUS_CHECKS = {
    "2.1.1": [
        "Sequential Tab/Shift+Tab focus progression is sampled without activating controls; up to 51 Tab actions cover the 50-candidate discovery cap plus one boundary action."
    ],
    "2.1.2": [
        "A repeated consecutive Tab target is distinguished from a focus cycle; when Tab stalls, the bounded Shift+Tab sample records whether focus moves from that target. Repeated multi-target Tab cycles are also compared with reverse traversal. Evidence remains review-only because focus cycling does not establish whether a containing widget can be exited or dismissed."
    ],
    "2.4.3": [
        "The expanded bounded Tab sequence is recorded; whether its order preserves meaning requires human review."
    ],
    "2.4.7": [
        "Keyboard focus state is compared with a limited set of computed CSS indicator properties."
    ],
    "2.4.11": [
        "Samples a 5x5 interior hit-test grid for each keyboard-focused target, records its bounding rectangle and viewport, and identifies layered elements intercepting samples.",
        "Classifies a full-cover candidate as a high-confidence failure only when one layered element covers the entire in-viewport target, intercepts every sample, has a fully opaque computed background and effective opacity of 1, and has no detected clip-path or mask; partial, translucent, clipped, or otherwise ambiguous overlap requires manual review.",
    ],
}
TEXT_REFLOW_CHECKS = {
    "1.4.4": [
        "A bounded per-element computed-font-size override probes 200% text for possible clipping, ellipsis, and overlap; text availability is not determined, so these observations require review."
    ],
    "1.4.10": [
        "The existing page is measured at 320 CSS pixels wide; text and document-level overflow are evidence for review, not violations by themselves.",
        "A 256 CSS-pixel height probe runs when a table or ARIA table/grid is detected; this heuristic does not determine whether an exception applies, and browser zoom is unsupported."
    ],
}
TEXT_SPACING_CHECKS = {
    "1.4.12": [
        "Applies line-height 1.5, paragraph margin after 2em, letter-spacing 0.12em, and word-spacing 0.16em to up to 300 visible text-bearing elements, then compares measurements with the captured baseline.",
        "Reports changed clipping, overlap, container overflow, hidden text, or control visibility/hit testing as needs-review evidence; scrollable regions are identified and are not treated as violations.",
    ],
}
ORIENTATION_CHECKS = {
    "1.3.4": [
        "Switches the CSS viewport between paired portrait and landscape dimensions and compares up to 300 visible text-bearing elements and controls by selector and opaque content signature.",
        "Reports elements that disappear or change content between orientations as needs-review evidence. The check cannot decide whether a change is equivalent or whether an orientation restriction is essential, and does not emulate physical device rotation or all orientation-change events.",
    ],
}
NON_TEXT_CONTRAST_CHECKS = {
    "1.4.11": [
        "Inspects up to 300 visible native controls, links, ARIA controls, and SVG shapes for solid computed CSS backgrounds, borders, outlines, fills, and strokes with estimated contrast below 3:1.",
        "Reports measured color pairs and element geometry as needs-review evidence only. It cannot determine which visual boundary is necessary, evaluate pseudo-elements or box shadows, pixel-sample images/canvas/video, reliably resolve gradients and layered rendering, or establish that a low ratio violates the criterion.",
    ],
}
HOVER_FOCUS_CONTENT_CHECKS = {
    "1.4.13": [
        "Samples up to four visible likely triggers without activating them, compares visible DOM content before and after pointer hover and focus, and records newly revealed content with trigger/content selectors, geometry, viewport, role, and opaque text signatures.",
        "For revealed content, samples whether pointer entry keeps hover content visible, whether Escape dismisses it, whether it remains after focus blur, and whether its rectangle intersects other content. Findings remain needs-review evidence; custom triggers, pseudo-elements, native tooltips, delayed states, and semantic exceptions are not fully evaluated.",
    ],
}
TARGET_SIZE_CHECKS = {
    "2.5.8": [
        "Measures visible, enabled pointer-target bounding boxes and reports targets narrower or shorter than 24 CSS px for review; WCAG exceptions and actual target spacing are not evaluated."
    ],
}
TESTS_BY_REFLOW_CRITERION = {
    "1.4.4": [
        "tests/test_capture.py::test_text_reflow_clipped_text_requires_availability_review",
        "tests/test_capture.py::test_text_reflow_ellipsis_disclosure_and_nested_sizes_need_review",
        "tests/test_capture.py::test_text_reflow_disclosure_remains_operable_when_clipping_is_reported",
        "tests/test_capture.py::test_text_reflow_reports_box_overlap_without_claiming_obscuration",
        "tests/test_capture.py::test_text_reflow_usable_fixture_has_no_detected_clipping",
        "tests/test_capture.py::test_text_reflow_candidate_limit_prevents_clean_classification",
    ],
    "1.4.10": [
        "tests/test_capture.py::test_text_reflow_flags_320px_overflow_for_review",
        "tests/test_capture.py::test_text_reflow_does_not_fail_legitimate_table_scrolling",
        "tests/test_capture.py::test_text_reflow_reports_unbreakable_text_overflow",
        "tests/test_capture.py::test_text_reflow_responsive_content_replacement_needs_review",
    ],
}
TESTS_BY_TEXT_SPACING_CRITERION = {
    "1.4.12": [
        "tests/test_capture.py::test_text_spacing_usable_fixture_has_no_detected_geometry_issue",
        "tests/test_capture.py::test_text_spacing_reports_fixed_height_clipping_for_review",
        "tests/test_capture.py::test_text_spacing_reports_new_overlap_without_claiming_violation",
        "tests/test_capture.py::test_text_spacing_reports_control_label_clipping_for_review",
        "tests/test_capture.py::test_text_spacing_reports_control_obscured_after_content_reflows",
        "tests/test_capture.py::test_text_spacing_keeps_scrollable_region_as_review_not_failure",
        "tests/test_capture.py::test_text_spacing_overrides_restore_after_screenshot_failure",
    ],
}
TESTS_BY_ORIENTATION_CRITERION = {
    "1.3.4": [
        "tests/test_capture.py::test_orientation_flexible_fixture_preserves_content_and_restores_viewport",
        "tests/test_capture.py::test_orientation_reports_content_and_control_changes_for_manual_review",
    ],
}
TESTS_BY_NON_TEXT_CONTRAST_CRITERION = {
    "1.4.11": [
        "tests/test_capture.py::test_non_text_contrast_reports_solid_color_candidates_for_review",
        "tests/test_capture.py::test_accessibility_scan_preserves_axe_results_and_specific_evidence",
    ],
}
TESTS_BY_TARGET_SIZE_CRITERION = {
    "2.5.8": [
        "tests/test_capture.py::test_target_size_audit_reports_small_visible_target_for_review",
        "tests/test_capture.py::test_target_size_audit_does_not_flag_adequate_target",
    ],
}
TESTS_BY_HOVER_FOCUS_CONTENT_CRITERION = {
    "1.4.13": [
        "tests/test_capture.py::test_hover_focus_compliant_tooltip_records_behavior_and_restores_focus",
        "tests/test_capture.py::test_hover_focus_reports_content_that_pointer_cannot_enter",
        "tests/test_capture.py::test_hover_focus_reports_undismissable_overlapping_focus_content",
        "tests/test_capture.py::test_hover_focus_ignores_style_only_hover_changes",
    ],
}
TESTS_BY_KEYBOARD_CRITERION = {
    "2.1.1": [
        "tests/test_capture.py::test_keyboard_audit_records_visible_keyboard_focus",
        "tests/test_capture.py::test_keyboard_audit_traverses_more_than_twenty_sequential_targets",
        "tests/test_capture.py::test_keyboard_audit_reports_interactive_candidate_skipped_by_tab",
    ],
    "2.1.2": [
        "tests/test_capture.py::test_keyboard_audit_reports_potential_focus_trap_for_review",
        "tests/test_capture.py::test_keyboard_audit_distinguishes_one_way_tab_block_from_trap",
        "tests/test_capture.py::test_keyboard_audit_reports_wrapping_cycle_for_manual_review",
    ],
    "2.4.11": [
        "tests/test_capture.py::test_keyboard_audit_reports_focus_obscuration_for_review",
        "tests/test_capture.py::test_keyboard_audit_confirms_opaque_full_cover_with_evidence",
        "tests/test_capture.py::test_keyboard_audit_classifies_sticky_header_overlap_as_potential",
        "tests/test_capture.py::test_keyboard_audit_detects_opaque_dialog_cover",
        "tests/test_capture.py::test_keyboard_audit_reports_no_sampled_occlusion_without_overlay",
    ],
}


def load_axe_metadata() -> dict:
    script = (
        "const axe=require('axe-core');"
        "console.log(JSON.stringify({version:axe.version,rules:axe.getRules()}));"
    )
    completed = subprocess.run(
        ["node", "-e", script],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    metadata = json.loads(completed.stdout)
    if metadata["version"] != "4.14.0":
        raise RuntimeError(
            f"Expected pinned axe-core 4.14.0, found {metadata['version']}."
        )
    return metadata


def _criterion_tag(criterion_id: str) -> str:
    return "wcag" + criterion_id.replace(".", "")


def build_inventory(source: dict, axe: dict) -> dict:
    entries = []
    mapped_count = 0
    for criterion in source["criteria"]:
        criterion_id = criterion["id"]
        tag = _criterion_tag(criterion_id)
        axe_rules = []
        for rule in axe["rules"]:
            if tag not in rule.get("tags", []):
                continue
            package_enabled = bool(rule.get("enabled", False))
            selected_by_scan = any(
                scanner_tag in rule.get("tags", []) for scanner_tag in SCANNER_TAGS
            )
            axe_rules.append(
                {
                    "rule_id": rule["ruleId"],
                    "tags": rule["tags"],
                    "package_enabled": package_enabled,
                    "selected_by_scan": selected_by_scan,
                    "effective_enabled": package_enabled and selected_by_scan,
                    "description": rule.get("description", ""),
                    "help_url": rule.get("helpUrl", ""),
                }
            )
        axe_rules.sort(key=lambda item: item["rule_id"])
        active = [rule for rule in axe_rules if rule["effective_enabled"]]
        keyboard_checks = KEYBOARD_FOCUS_CHECKS.get(criterion_id, [])
        reflow_checks = TEXT_REFLOW_CHECKS.get(criterion_id, [])
        text_spacing_checks = TEXT_SPACING_CHECKS.get(criterion_id, [])
        orientation_checks = ORIENTATION_CHECKS.get(criterion_id, [])
        non_text_contrast_checks = NON_TEXT_CONTRAST_CHECKS.get(
            criterion_id, []
        )
        hover_focus_content_checks = HOVER_FOCUS_CONTENT_CHECKS.get(
            criterion_id, []
        )
        target_size_checks = TARGET_SIZE_CHECKS.get(criterion_id, [])
        if (
            active or keyboard_checks or reflow_checks
            or text_spacing_checks or orientation_checks
            or non_text_contrast_checks or hover_focus_content_checks
            or target_size_checks
        ):
            classification = "partial"
            if active:
                mapped_count += 1
            next_step = (
                "Validate the implemented checks with criterion-specific counterexamples "
                "against the criterion's Understanding guidance; retain manual review "
                "for aspects beyond their bounded scope."
            )
        elif criterion_id in MANUAL_ONLY:
            classification = "manual_evaluation_required"
            next_step = (
                "Evaluate representative content and states with a trained reviewer "
                "and, where applicable, assistive technology; define bounded "
                "automated support only after validating it against WCAG guidance."
            )
        else:
            classification = "not_implemented"
            next_step = (
                "Design and validate a criterion-specific check or interaction "
                "scenario before adding automated coverage; do not infer a pass "
                "from the absence of an axe mapping."
            )
        patterns = [
            {
                "rule_id": rule["rule_id"],
                "description": rule["description"],
                "help_url": rule["help_url"],
            }
            for rule in active
        ]
        limitations = [
            "A WCAG tag records the axe rule author's criterion association; it is not evidence that the rule covers the full success criterion.",
            "The scanner records rule outcomes only when the rule runs and reports them. An absent result does not establish that the criterion passed.",
        ]
        if (
            not active and not keyboard_checks and not reflow_checks
            and not text_spacing_checks and not hover_focus_content_checks
            and not orientation_checks
            and not non_text_contrast_checks
            and not target_size_checks
        ):
            limitations.insert(
                0,
                "No enabled axe rule selected by the current scanner carries this criterion's exact WCAG tag.",
            )
        elif not active and (
            keyboard_checks or reflow_checks
        or text_spacing_checks or orientation_checks
        or non_text_contrast_checks
        or hover_focus_content_checks
        or target_size_checks
        ):
            limitations.insert(
                0,
                "No enabled axe rule selected by the current scanner carries this criterion's exact WCAG tag; the listed WebAble probes are separate, bounded evidence and do not establish criterion conformance.",
            )
        rule_tests = sorted(
            {
                test
                for rule in active
                for test in TESTS_BY_RULE.get(rule["rule_id"], [])
            }
        )
        rule_tests.extend(TESTS_BY_REFLOW_CRITERION.get(criterion_id, []))
        rule_tests.extend(TESTS_BY_TEXT_SPACING_CRITERION.get(criterion_id, []))
        rule_tests.extend(TESTS_BY_ORIENTATION_CRITERION.get(criterion_id, []))
        rule_tests.extend(
            TESTS_BY_NON_TEXT_CONTRAST_CRITERION.get(criterion_id, [])
        )
        rule_tests.extend(
            TESTS_BY_HOVER_FOCUS_CONTENT_CRITERION.get(criterion_id, [])
        )
        rule_tests.extend(TESTS_BY_TARGET_SIZE_CRITERION.get(criterion_id, []))
        rule_tests.extend(TESTS_BY_KEYBOARD_CRITERION.get(criterion_id, []))
        criterion_url = f"{source['source']}#{criterion['anchor']}"
        understanding_url = (
            "https://www.w3.org/WAI/WCAG22/Understanding/"
            f"{criterion['anchor']}.html"
        )
        entries.append(
            {
                **criterion,
                "criterion_url": criterion_url,
                "understanding_url": understanding_url,
                "coverage_classification": classification,
                "questionnaire_question_ids": sorted(
                    question.question_id
                    for question in QUESTIONNAIRE_QUESTIONS
                    if criterion_id in question.criterion_ids
                ),
                "axe_check_exists": bool(active),
                "keyboard_focus_check_exists": bool(keyboard_checks),
                "keyboard_focus_checks": keyboard_checks,
                "text_reflow_check_exists": bool(reflow_checks),
                "text_reflow_checks": reflow_checks,
                "text_spacing_check_exists": bool(text_spacing_checks),
                "text_spacing_checks": text_spacing_checks,
                "orientation_check_exists": bool(orientation_checks),
                "orientation_checks": orientation_checks,
                "non_text_contrast_check_exists": bool(
                    non_text_contrast_checks
                ),
                "non_text_contrast_checks": non_text_contrast_checks,
                "hover_focus_content_check_exists": bool(
                    hover_focus_content_checks
                ),
                "hover_focus_content_checks": hover_focus_content_checks,
                "target_size_check_exists": bool(target_size_checks),
                "target_size_checks": target_size_checks,
                "axe_criterion_tag": tag,
                "axe_rules": axe_rules,
                "automated_check_exists": bool(
                    active or keyboard_checks or reflow_checks
                    or text_spacing_checks or orientation_checks
                    or non_text_contrast_checks
                    or hover_focus_content_checks
                    or target_size_checks
                ),
                "failure_patterns": patterns,
                "limitations": limitations,
                "manual_evaluation_needed": True,
                "keyboard_testing_needed": criterion_id in KEYBOARD_REQUIRED,
                "interaction_testing_needed": criterion_id in INTERACTION_REQUIRED,
                "assistive_technology_testing_needed": (
                    criterion_id in ASSISTIVE_TECHNOLOGY_REQUIRED
                ),
                "evidence_links": [
                    criterion_url,
                    understanding_url,
                    *sorted({rule["help_url"] for rule in active if rule["help_url"]}),
                ],
                "relevant_tests": rule_tests,
                "outstanding_gaps": [
                    next_step,
                    "No result from this scan may be described as WCAG conformance.",
                ],
            }
        )
    return {
        "inventory_version": "2.0",
        "wcag_version": "2.2",
        "axe_core_version": axe["version"],
        "source_inventory": {
            "path": "tests/fixtures/wcag22_criteria_source.json",
            "url": source["source"],
            "current_url": source["current_url"],
            "retrieved": source["retrieved"],
            "description": "Independent checked-in transcription of in-scope criterion identifiers, titles, levels, principles, and anchors from the W3C Recommendation.",
        },
        "scanner_configuration": {
            "run_only_tags": SCANNER_TAGS,
            "effective_mapping_definition": (
                "A criterion mapping is effective only when an axe rule contains "
                "the exact wcag{criterion-id-without-dots} tag, is enabled in "
                "axe-core package metadata, and also contains at least one configured "
                "scanner runOnly version/level tag."
            ),
        },
        "summary": {
            "criterion_count": len(entries),
            "mapped_criteria_with_enabled_selected_rules": mapped_count,
            "criteria_with_questionnaire_mapping": sum(
                bool(entry["questionnaire_question_ids"]) for entry in entries
            ),
            "manual_criteria_with_questionnaire_mapping": sum(
                entry["coverage_classification"] == "manual_evaluation_required"
                and bool(entry["questionnaire_question_ids"])
                for entry in entries
            ),
            "classification_counts": {
                name: sum(
                    entry["coverage_classification"] == name for entry in entries
                )
                for name in (
                    "automated",
                    "partial",
                    "manual_evaluation_required",
                    "not_implemented",
                )
            },
        },
        "scope_exclusions": source.get("scope_exclusions", []),
        "criteria": entries,
    }


def render_markdown(inventory: dict) -> str:
    summary = inventory["summary"]
    lines = [
        "# WCAG 2.2 Level A/AA Coverage Inventory",
        "",
        f"**Inventory version:** {inventory['inventory_version']}  ",
        f"**Standards baseline:** [WCAG 2.2 W3C Recommendation]({inventory['source_inventory']['url']})  ",
        f"**Engine:** axe-core {inventory['axe_core_version']} (pinned package metadata)  ",
        "**In-scope criteria:** 55 (all A and AA criteria; AAA excluded; obsolete 4.1.1 excluded)  ",
        f"**Criteria with at least one enabled, scanner-selected exact WCAG criterion tag:** {summary['mapped_criteria_with_enabled_selected_rules']} of {summary['criterion_count']}",
        f"**Criteria mapped to initial or conditional questionnaire questions:** {summary['criteria_with_questionnaire_mapping']} of {summary['criterion_count']} (manual-evaluation criteria: {summary['manual_criteria_with_questionnaire_mapping']} of 26)",
        "",
        "This inventory is evidence of rule associations and current checks, not a WCAG conformance statement. A WCAG tag on an axe rule is an association published in the rule metadata, not proof that the rule covers the whole success criterion. A rule result applies only to its documented test conditions and reported nodes.",
        "",
        "## Classification definitions",
        "",
        "- `automated`: an implemented check fully evaluates the success criterion within its declared scope. None are assigned: no current axe tag mapping establishes full criterion coverage.",
        "- `partial`: one or more bounded automated probes or enabled rules selected by the current scan provide evidence for part of the criterion; the checks cover only their documented test conditions.",
        "- `manual_evaluation_required`: no bounded automated check is currently mapped in this inventory. The questionnaire can record owner self-assessment for all criteria, but that is not independent verification or a WCAG conformance conclusion.",
        "- `not_implemented`: no enabled selected exact-tag check exists; a bounded technical or interaction check may be developed, but none is implemented.",
        "",
        "The classification describes automated-check coverage, not whether an owner can answer contextual questions. All criteria have questionnaire prompts; direct prompts can produce a scoped owner-reported assessment when their yes/no polarity is defined. Contextual answers remain context-only, not sure is inconclusive, and not applicable remains owner-reported. None is independently verified or a WCAG pass/fail conclusion. A criterion may still need expert, assistive-technology, content, media, or interaction review. `automated_check_exists` includes bounded WebAble keyboard/focus, orientation, non-text contrast, hover/focus-content, and text/reflow probes when listed, while `axe_check_exists` records exact-tagged axe coverage separately. Neither means the whole criterion is automated. The scanner runs with these exact configuration tags: "
        + ", ".join(f"`{tag}`" for tag in inventory["scanner_configuration"]["run_only_tags"])
        + ". Effective rule selection requires both package `enabled: true` and a matching runOnly tag.",
        "",
        "## Summary",
        "",
        "| Classification | Count |",
        "|---|---:|",
    ]
    for name, count in summary["classification_counts"].items():
        lines.append(f"| `{name}` | {count} |")
    lines.extend(
        [
            "",
            "The 55 is the number of applicable WCAG 2.2 A/AA success criteria, not a scanner coverage percentage. The mapped-criterion count measures enabled, configured axe rules that carry the exact criterion tag; it is not a conformance rate or completeness measure.",
            "",
            "## Criterion inventory",
            "",
            "The checked-in criterion baseline is `tests/fixtures/wcag22_criteria_source.json`, independently transcribed from the normative Recommendation. Axe rule IDs, full tags, enabled status, descriptions, and help links below are generated from the installed pinned package metadata. To regenerate after a deliberate baseline or axe update, run `python scripts/generate_wcag22_coverage_inventory.py` after `npm ci`.",
            "",
        ]
    )
    for criterion in inventory["criteria"]:
        lines.extend(
            [
                f"### {criterion['id']} — {criterion['title']}",
                "",
                f"- **Level / principle:** {criterion['level']} / {criterion['principle']}",
                f"- **Intent:** {criterion['intent']}",
                f"- **Coverage:** `{criterion['coverage_classification']}`",
                f"- **Questionnaire question IDs:** {', '.join(f'`{item}`' for item in criterion['questionnaire_question_ids']) or 'none'}",
                f"- **Automated check exists:** {str(criterion['automated_check_exists']).lower()}",
                f"- **Axe check exists:** {str(criterion['axe_check_exists']).lower()}",
                f"- **WebAble keyboard/focus check exists:** {str(criterion['keyboard_focus_check_exists']).lower()}",
                f"- **WebAble text/reflow check exists:** {str(criterion['text_reflow_check_exists']).lower()}",
                f"- **WebAble text-spacing check exists:** {str(criterion['text_spacing_check_exists']).lower()}",
                f"- **WebAble orientation check exists:** {str(criterion['orientation_check_exists']).lower()}",
                f"- **WebAble non-text contrast check exists:** {str(criterion['non_text_contrast_check_exists']).lower()}",
                f"- **WebAble hover/focus-content check exists:** {str(criterion['hover_focus_content_check_exists']).lower()}",
                f"- **WebAble target-size check exists:** {str(criterion['target_size_check_exists']).lower()}",
                f"- **Exact criterion tag:** `{criterion['axe_criterion_tag']}`",
                f"- **Manual / keyboard / interaction / assistive-technology testing needed:** "
                f"{str(criterion['manual_evaluation_needed']).lower()} / "
                f"{str(criterion['keyboard_testing_needed']).lower()} / "
                f"{str(criterion['interaction_testing_needed']).lower()} / "
                f"{str(criterion['assistive_technology_testing_needed']).lower()}",
                f"- **Normative criterion:** [{criterion['id']} {criterion['title']}]({criterion['criterion_url']})",
                f"- **Understanding:** [Understanding {criterion['id']}]({criterion['understanding_url']})",
            ]
        )
        if criterion["axe_rules"]:
            lines.extend(
                [
                    "- **Associated axe rules** (all exact WCAG-tagged rules in package metadata):",
                ]
            )
            for rule in criterion["axe_rules"]:
                selected = "selected" if rule["selected_by_scan"] else "not selected"
                lines.append(
                    f"  - [`{rule['rule_id']}`]({rule['help_url']}) — "
                    f"package enabled: `{str(rule['package_enabled']).lower()}`; "
                    f"scanner: `{selected}`; effective: "
                    f"`{str(rule['effective_enabled']).lower()}`; "
                    f"tags: {', '.join(f'`{tag}`' for tag in rule['tags'])}"
                )
        else:
            lines.append("- **Associated axe rules:** none with this criterion tag in axe-core 4.14.0 metadata.")
        if criterion["failure_patterns"]:
            lines.append("- **Implemented failure patterns (rule-description scope, not exhaustive):**")
            for pattern in criterion["failure_patterns"]:
                lines.append(
                    f"  - `{pattern['rule_id']}`: {pattern['description']} "
                    f"([rule help]({pattern['help_url']}))"
                )
        else:
            lines.append("- **Implemented failure patterns:** none mapped by an enabled, selected rule carrying this criterion's exact tag.")
        if criterion["keyboard_focus_checks"]:
            lines.append("- **Bounded keyboard/focus checks:**")
            lines.extend(
                f"  - {check}" for check in criterion["keyboard_focus_checks"]
            )
        if criterion["text_reflow_checks"]:
            lines.append("- **Bounded text/reflow checks:**")
            lines.extend(
                f"  - {check}" for check in criterion["text_reflow_checks"]
            )
        if criterion["text_spacing_checks"]:
            lines.append("- **Bounded text-spacing checks:**")
            lines.extend(
                f"  - {check}" for check in criterion["text_spacing_checks"]
            )
        if criterion["orientation_checks"]:
            lines.append("- **Bounded orientation checks:**")
            lines.extend(
                f"  - {check}" for check in criterion["orientation_checks"]
            )
        if criterion["non_text_contrast_checks"]:
            lines.append("- **Bounded non-text contrast checks:**")
            lines.extend(
                f"  - {check}"
                for check in criterion["non_text_contrast_checks"]
            )
        if criterion["hover_focus_content_checks"]:
            lines.append("- **Bounded hover/focus-content checks:**")
            lines.extend(
                f"  - {check}"
                for check in criterion["hover_focus_content_checks"]
            )
        if criterion["target_size_checks"]:
            lines.append("- **Bounded target-size checks:**")
            lines.extend(
                f"  - {check}" for check in criterion["target_size_checks"]
            )
        lines.extend(
            [
                "- **Limitations:**",
                *[f"  - {limitation}" for limitation in criterion["limitations"]],
                "- **Relevant existing tests:** "
                + (
                    ", ".join(f"`{test}`" for test in criterion["relevant_tests"])
                    if criterion["relevant_tests"]
                    else "No focused criterion-specific fixture assertion currently exists."
                ),
                "- **Outstanding gaps / next step:**",
                *[f"  - {gap}" for gap in criterion["outstanding_gaps"]],
                "- **Evidence links:** "
                + ", ".join(f"[{index + 1}]({link})" for index, link in enumerate(criterion["evidence_links"])),
                "",
            ]
        )
    lines.extend(
        [
            "## Method and limitations",
            "",
            "The 55 criterion identifiers, exact titles, levels, principles, and anchors are checked against the separate offline source transcription in `tests/fixtures/wcag22_criteria_source.json`. The mapping registry is derived from `axe-core@4.14.0` `getRules()` metadata. A rule is effective for this scanner only if the package reports it enabled, it has the exact criterion tag (`wcag` + criterion digits), and it also has one of the configured runOnly tags. The scanner configuration and inventory are validated offline in `tests/test_wcag22_inventory.py`.",
            "",
            "The inventory's rule descriptions identify intended rule scope, not all failure conditions or all WCAG exceptions. Consult each linked axe rule help page and W3C Understanding document before interpreting evidence. A tag may be an association with only one aspect of a broad criterion; missing mappings are explicitly empty and do not imply a pass. Rule `incomplete` outcomes need human review and are not confirmed violations.",
            "",
            "The 2.4.13 Focus Appearance criterion is Level AAA according to W3C and is therefore intentionally excluded from the A/AA criteria list. The keyboard/focus audit does not measure focus-indicator perimeter area or 3:1 contrast and does not implement 2.4.13.",
            "",
            "### Scope exclusions",
            "",
            *[
                f"- [{item['id']} {item['title']}]({item['url']}) — {item['reason']}"
                for item in inventory["scope_exclusions"]
            ],
            "",
            "The current scan observes one settled rendered state per viewport and includes bounded text enlargement and a 320 CSS-pixel reflow probe. Actual browser zoom is not simulated; 256 CSS-pixel height testing is conditional on detecting a table or ARIA table/grid. The text override is not equivalent to every browser text-only zoom behavior. The scan does not automate all keyboard traversal/focus order, interactions, media inspection, site-wide comparisons, cognitive-function/authentication evaluation, or assistive-technology announcement testing. It does not establish that the selected page, a process, or a site conforms. Browser/runtime failures and evidence caps are represented separately by the API scan status.",
            "",
            "### Source references",
            "",
            f"- [WCAG 2.2 Recommendation]({inventory['source_inventory']['url']})",
            f"- [W3C current WCAG Recommendation URL]({inventory['source_inventory']['current_url']}) (resolves to the WCAG 2.2 Recommendation)",
            "- [WCAG 2.2 Understanding documents](https://www.w3.org/WAI/WCAG22/Understanding/)",
            "- [W3C evaluation guidance](https://www.w3.org/WAI/test-evaluate/)",
            "- [axe-core API and tag filtering](https://github.com/dequelabs/axe-core/blob/develop/doc/API.md)",
            "- [axe-core rule descriptions](https://github.com/dequelabs/axe-core/blob/develop/doc/rule-descriptions.md)",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    source = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
    axe = load_axe_metadata()
    inventory = build_inventory(source, axe)
    JSON_PATH.write_text(
        json.dumps(inventory, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    MARKDOWN_PATH.write_text(render_markdown(inventory), encoding="utf-8")
    print(
        f"Wrote {inventory['summary']['criterion_count']} criteria; "
        f"{inventory['summary']['mapped_criteria_with_enabled_selected_rules']} "
        "have enabled scanner-selected exact-tag rules."
    )


if __name__ == "__main__":
    main()

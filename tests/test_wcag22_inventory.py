import json
import re
from pathlib import Path

from app.analyzers.accessibility import AXE_CORE_VERSION, WCAG_AA_TAGS
from scripts.generate_wcag22_coverage_inventory import (
    JSON_PATH,
    MARKDOWN_PATH,
    SOURCE_PATH,
    build_inventory,
    load_axe_metadata,
    render_markdown,
)


ROOT = Path(__file__).parent.parent


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_source_inventory_is_complete_wcag_22_a_aa_baseline():
    source = _read_json(SOURCE_PATH)
    criteria = source["criteria"]
    ids = [criterion["id"] for criterion in criteria]

    assert source["source"] == "https://www.w3.org/TR/WCAG22/"
    assert source["current_url"] == "https://www.w3.org/TR/WCAG/"
    assert source["version"] == "WCAG 2.2 W3C Recommendation"
    excluded = {item["id"]: item for item in source["scope_exclusions"]}
    assert excluded["2.4.13"]["level"] == "AAA"
    assert excluded["2.4.13"]["title"] == "Focus Appearance"
    assert "Level AAA" in excluded["2.4.13"]["reason"]
    assert len(criteria) == 55
    assert len(ids) == len(set(ids))
    assert "4.1.1" not in ids
    assert all(criterion["level"] in {"A", "AA"} for criterion in criteria)
    assert all(
        criterion["principle"]
        in {"Perceivable", "Operable", "Understandable", "Robust"}
        for criterion in criteria
    )
    assert all(criterion["title"] and criterion["intent"] for criterion in criteria)

    expected_criterion_ids = {
        "1.1.1",
        "1.2.1", "1.2.2", "1.2.3", "1.2.4", "1.2.5",
        "1.3.1", "1.3.2", "1.3.3", "1.3.4", "1.3.5",
        "1.4.1", "1.4.2", "1.4.3", "1.4.4", "1.4.5",
        "1.4.10", "1.4.11", "1.4.12", "1.4.13",
        "2.1.1", "2.1.2", "2.1.4",
        "2.2.1", "2.2.2", "2.3.1",
        "2.4.1", "2.4.2", "2.4.3", "2.4.4", "2.4.5",
        "2.4.6", "2.4.7", "2.4.11",
        "2.5.1", "2.5.2", "2.5.3", "2.5.4", "2.5.7", "2.5.8",
        "3.1.1", "3.1.2",
        "3.2.1", "3.2.2", "3.2.3", "3.2.4", "3.2.6",
        "3.3.1", "3.3.2", "3.3.3", "3.3.4", "3.3.7", "3.3.8",
        "4.1.2", "4.1.3",
    }
    assert set(ids) == expected_criterion_ids


def test_inventory_matches_source_and_installed_axe_metadata():
    source = _read_json(SOURCE_PATH)
    actual_axe = load_axe_metadata()
    inventory = _read_json(JSON_PATH)
    expected = build_inventory(source, actual_axe)

    assert actual_axe["version"] == AXE_CORE_VERSION == "4.14.0"
    assert inventory == expected
    assert inventory["scanner_configuration"]["run_only_tags"] == list(WCAG_AA_TAGS)
    assert inventory["summary"]["criterion_count"] == 55
    assert inventory["summary"]["criteria_with_questionnaire_mapping"] == 55
    assert inventory["summary"]["manual_criteria_with_questionnaire_mapping"] == 26
    assert inventory["summary"]["mapped_criteria_with_enabled_selected_rules"] == 20
    assert inventory["summary"]["classification_counts"] == {
        "automated": 0,
        "partial": 29,
        "manual_evaluation_required": 26,
        "not_implemented": 0,
    }
    assert inventory["scope_exclusions"] == source["scope_exclusions"]

    actual_rules = {rule["ruleId"]: rule for rule in actual_axe["rules"]}
    effective_mappings = 0
    for criterion in inventory["criteria"]:
        assert criterion["id"] in {row["id"] for row in source["criteria"]}
        assert criterion["axe_check_exists"] == any(
            rule["effective_enabled"] for rule in criterion["axe_rules"]
        )
        assert criterion["keyboard_focus_check_exists"] == bool(
            criterion["keyboard_focus_checks"]
        )
        assert criterion["text_reflow_check_exists"] == bool(
            criterion["text_reflow_checks"]
        )
        assert criterion["text_spacing_check_exists"] == bool(
            criterion["text_spacing_checks"]
        )
        assert criterion["orientation_check_exists"] == bool(
            criterion["orientation_checks"]
        )
        assert criterion["non_text_contrast_check_exists"] == bool(
            criterion["non_text_contrast_checks"]
        )
        assert criterion["hover_focus_content_check_exists"] == bool(
            criterion["hover_focus_content_checks"]
        )
        assert criterion["target_size_check_exists"] == bool(
            criterion["target_size_checks"]
        )
        assert criterion["automated_check_exists"] == (
            criterion["axe_check_exists"]
            or criterion["keyboard_focus_check_exists"]
            or criterion["text_reflow_check_exists"]
            or criterion["text_spacing_check_exists"]
            or criterion["orientation_check_exists"]
            or criterion["non_text_contrast_check_exists"]
            or criterion["hover_focus_content_check_exists"]
            or criterion["target_size_check_exists"]
        )
        if criterion["automated_check_exists"]:
            effective_mappings += 1
            assert criterion["coverage_classification"] == "partial"
        else:
            assert criterion["coverage_classification"] in {
                "manual_evaluation_required",
                "not_implemented",
            }
            assert criterion["axe_rules"] or criterion["axe_criterion_tag"]

        for rule in criterion["axe_rules"]:
            package_rule = actual_rules[rule["rule_id"]]
            assert rule["tags"] == package_rule["tags"]
            assert rule["package_enabled"] is package_rule["enabled"]
            assert rule["selected_by_scan"] is any(
                tag in package_rule["tags"] for tag in WCAG_AA_TAGS
            )
            assert rule["effective_enabled"] is (
                package_rule["enabled"] and rule["selected_by_scan"]
            )
            assert criterion["axe_criterion_tag"] in package_rule["tags"]
        assert criterion["manual_evaluation_needed"] is True
        assert isinstance(criterion["keyboard_testing_needed"], bool)
        assert isinstance(criterion["interaction_testing_needed"], bool)
        assert isinstance(criterion["assistive_technology_testing_needed"], bool)

    assert effective_mappings == 29
    criteria_by_id = {item["id"]: item for item in inventory["criteria"]}
    for criterion_id in ("2.1.1", "2.1.2", "2.4.3", "2.4.7", "2.4.11"):
        assert criteria_by_id[criterion_id]["keyboard_focus_check_exists"]
        assert criteria_by_id[criterion_id]["coverage_classification"] == "partial"
    for criterion_id in ("1.4.4", "1.4.10"):
        assert criteria_by_id[criterion_id]["text_reflow_check_exists"]
        assert criteria_by_id[criterion_id]["coverage_classification"] == "partial"
    assert criteria_by_id["2.5.8"]["target_size_check_exists"]
    assert criteria_by_id["2.5.8"]["coverage_classification"] == "partial"
    assert criteria_by_id["1.4.12"]["text_spacing_check_exists"]
    assert criteria_by_id["1.4.12"]["coverage_classification"] == "partial"
    assert criteria_by_id["1.4.13"]["hover_focus_content_check_exists"]
    assert criteria_by_id["1.4.13"]["coverage_classification"] == "partial"
    assert criteria_by_id["1.3.4"]["orientation_check_exists"]
    assert criteria_by_id["1.3.4"]["coverage_classification"] == "partial"
    assert criteria_by_id["1.3.4"]["axe_check_exists"] is False
    assert criteria_by_id["1.4.11"]["non_text_contrast_check_exists"]
    assert criteria_by_id["1.4.11"]["coverage_classification"] == "partial"
    assert criteria_by_id["1.4.11"]["axe_check_exists"] is False


def test_inventory_rule_references_and_failure_patterns_are_real():
    inventory = _read_json(JSON_PATH)
    actual_axe = load_axe_metadata()
    rules_by_id = {rule["ruleId"]: rule for rule in actual_axe["rules"]}

    for criterion in inventory["criteria"]:
        rules = {rule["rule_id"]: rule for rule in criterion["axe_rules"]}
        assert len(rules) == len(criterion["axe_rules"])
        expected_patterns = [
            {
                "rule_id": rule_id,
                "description": rules_by_id[rule_id]["description"],
                "help_url": rules_by_id[rule_id]["helpUrl"],
            }
            for rule_id in sorted(rules)
            if (
                rules_by_id[rule_id]["enabled"]
                and any(
                    tag in rules_by_id[rule_id]["tags"] for tag in WCAG_AA_TAGS
                )
            )
        ]
        assert criterion["failure_patterns"] == expected_patterns
        for rule_id in rules:
            assert rule_id in rules_by_id
        if not criterion["automated_check_exists"]:
            assert not criterion["failure_patterns"]


def test_markdown_and_json_inventory_agree_on_criterion_fields():
    inventory = _read_json(JSON_PATH)
    markdown = MARKDOWN_PATH.read_text(encoding="utf-8")
    generated_markdown = render_markdown(build_inventory(
        _read_json(SOURCE_PATH), load_axe_metadata()
    ))

    assert markdown == generated_markdown
    headings = re.findall(r"^### (\d+\.\d+\.\d+) — (.+)$", markdown, re.MULTILINE)
    assert len(headings) == len(inventory["criteria"]) == 55
    assert [(row["id"], row["title"]) for row in inventory["criteria"]] == headings
    for criterion in inventory["criteria"]:
        assert f"- **Level / principle:** {criterion['level']} / {criterion['principle']}" in markdown
        assert f"- **Coverage:** `{criterion['coverage_classification']}`" in markdown
        assert (
            f"- **Automated check exists:** "
            f"{str(criterion['automated_check_exists']).lower()}"
        ) in markdown
        assert (
            f"- **Axe check exists:** "
            f"{str(criterion['axe_check_exists']).lower()}"
        ) in markdown
        assert (
            f"- **WebAble keyboard/focus check exists:** "
            f"{str(criterion['keyboard_focus_check_exists']).lower()}"
        ) in markdown
        assert (
            f"- **WebAble text/reflow check exists:** "
            f"{str(criterion['text_reflow_check_exists']).lower()}"
        ) in markdown
        assert (
            f"- **WebAble text-spacing check exists:** "
            f"{str(criterion['text_spacing_check_exists']).lower()}"
        ) in markdown
        assert (
            f"- **WebAble orientation check exists:** "
            f"{str(criterion['orientation_check_exists']).lower()}"
        ) in markdown
        assert (
            f"- **WebAble non-text contrast check exists:** "
            f"{str(criterion['non_text_contrast_check_exists']).lower()}"
        ) in markdown
        assert (
            f"- **WebAble hover/focus-content check exists:** "
            f"{str(criterion['hover_focus_content_check_exists']).lower()}"
        ) in markdown
        assert (
            f"- **WebAble target-size check exists:** "
            f"{str(criterion['target_size_check_exists']).lower()}"
        ) in markdown
        if not criterion["axe_rules"]:
            assert "- **Associated axe rules:** none with this criterion tag" in markdown
        elif not criterion["automated_check_exists"]:
            assert any(
                f"`{rule['rule_id']}`" in markdown
                and "`effective: `false`" not in markdown
                for rule in criterion["axe_rules"]
            )

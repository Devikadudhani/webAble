import asyncio

import pytest
from fastapi.testclient import TestClient
from playwright.async_api import async_playwright

from app.analyzers.hybrid_evaluation import (
    BrowserCriterionEvidence,
    BrowserFeatureDiscovery,
    BrowserFeatureEvidence,
    OwnerAnswer,
    WCAG_CRITERION_IDS,
    build_hybrid_evaluation,
    discover_browser_features,
    get_questions,
    sanitize_context_url,
    validate_questionnaire_inputs,
)
from app.main import (
    AccessibilityContextRequest,
    CaptureRequest,
    ResponsiveCaptureResponse,
    app,
)


def test_criterion_inventory_contains_unique_wcag_a_aa_ids():
    assert len(WCAG_CRITERION_IDS) == 55
    assert len(set(WCAG_CRITERION_IDS)) == 55


def test_questionnaire_covers_every_criterion_and_manual_criterion_has_specific_prompt():
    from app.analyzers.hybrid_evaluation import QUESTIONNAIRE_QUESTIONS, WCAG_CRITERIA_CATALOG

    mapped = {
        criterion_id: [question for question in QUESTIONNAIRE_QUESTIONS if criterion_id in question.criterion_ids]
        for criterion_id in WCAG_CRITERION_IDS
    }
    manual_ids = {
        item["criterion_id"] for item in WCAG_CRITERIA_CATALOG
        if item["coverage_classification"] == "manual_evaluation_required"
    }
    assert len(manual_ids) == 26
    assert all(mapped[criterion_id] for criterion_id in WCAG_CRITERION_IDS)
    assert all(
        any(len(question.prompt) >= 60 for question in mapped[cid])
        for cid in manual_ids
    )
    assert all(q.answer_options == ("yes", "no", "not_sure", "not_applicable") for q in QUESTIONNAIRE_QUESTIONS)


def test_questionnaire_returns_initial_and_feature_conditioned_questions():
    initial = get_questions({})
    assert {question.question_id for question in initial} == {
        "scope.representative_pages",
        "scope.user_journeys",
        "scope.features",
    }

    media_questions = get_questions({"prerecorded_media": True})
    assert "media.prerecorded_alternatives" in {
        question.question_id for question in media_questions
    }
    assert "forms.error_identification" not in {
        question.question_id for question in media_questions
    }


def test_browser_discovery_can_reveal_condition_after_owner_says_feature_absent():
    questions = get_questions(
        {"forms": False},
        (
            BrowserFeatureEvidence(
                feature_id="forms",
                detected=True,
                count=1,
                viewport="desktop",
                evidence=("A rendered form was detected.",),
            ),
        ),
    )
    assert "discovery.forms" in {question.question_id for question in questions}


def test_browser_discovery_followup_is_not_suppressed_by_criterion_no_answer():
    evaluation = build_hybrid_evaluation(
        declared_features={"forms": False},
        answers=(OwnerAnswer(question_id="forms.error_identification", answer="no"),),
        browser_discoveries=(BrowserFeatureDiscovery(
            status="available",
            features=(BrowserFeatureEvidence("forms", True, 1, "desktop", ("Form found",)),),
        ),),
    )
    assert "discovery.forms" in {q["question_id"] for q in evaluation["questions_to_ask"]}


def test_hybrid_evaluation_preserves_sources_and_surfaces_conflicts():
    evaluation = build_hybrid_evaluation(
        declared_features={"forms": False},
        answers=(OwnerAnswer(question_id="forms.error_identification", answer="no"),),
        browser_discoveries=(
            BrowserFeatureDiscovery(
                status="available",
                features=(
                    BrowserFeatureEvidence(
                        feature_id="forms",
                        detected=True,
                        count=1,
                        viewport="desktop",
                        evidence=("A rendered form was detected.",),
                    ),
                ),
            ),
        ),
    )

    criterion = next(
        item for item in evaluation["criteria"] if item["criterion_id"] == "3.3.1"
    )
    assert criterion["status"] == "manual_review_needed"
    assert criterion["owner_reported"][0]["source"] == "owner_reported"
    assert criterion["browser_observed"][0]["source"] == "browser_observed"
    assert "manual_review" not in criterion
    assert criterion["manual_review_required"] is True
    assert criterion["compliance_conclusion"] is None
    assert criterion["conflicts"][0]["type"] == "owner_browser_feature_conflict"
    assert "discovery.forms" in {q["question_id"] for q in evaluation["questions_to_ask"]}
    feature_criterion = next(
        item for item in evaluation["criteria"] if item["criterion_id"] == "1.3.5"
    )
    assert feature_criterion["status"] == "manual_review_needed"
    assert feature_criterion["owner_reported"]
    assert feature_criterion["browser_observed"]
    assert feature_criterion["conflicts"]


def test_owner_only_and_empty_criteria_never_become_compliance_passes():
    evaluation = build_hybrid_evaluation(
        declared_features={"forms": True},
        answers=(OwnerAnswer(question_id="forms.error_identification", answer="yes"),),
        browser_discoveries=(),
    )
    criteria = {item["criterion_id"]: item for item in evaluation["criteria"]}
    assert criteria["3.3.1"]["status"] == "owner_reported"
    assert criteria["3.3.1"]["compliance_conclusion"] is None
    assert criteria["1.2.1"]["status"] == "not_evaluated"
    assert criteria["1.2.1"]["compliance_conclusion"] is None


def test_questionnaire_answers_create_criterion_scoped_owner_self_assessment():
    from app.analyzers.hybrid_evaluation import (
        QUESTIONNAIRE_QUESTIONS,
        WCAG_CRITERIA_CATALOG,
    )

    manual_criteria = {
        item["criterion_id"]
        for item in WCAG_CRITERIA_CATALOG
        if item["coverage_classification"] == "manual_evaluation_required"
    }
    questions_by_criterion = {
        criterion_id: next(
            question
            for question in QUESTIONNAIRE_QUESTIONS
            if criterion_id in question.criterion_ids
        )
        for criterion_id in manual_criteria
    }
    answers = tuple(
        OwnerAnswer(
            question_id=question.question_id,
            answer="not_sure",
            explanation="Needs review on the representative page.",
            page_urls=("https://example.test/representative",),
        )
        for question in questions_by_criterion.values()
    )
    evaluation = build_hybrid_evaluation(
        declared_features={},
        answers=answers,
        browser_discoveries=(),
    )
    criteria = {item["criterion_id"]: item for item in evaluation["criteria"]}

    for criterion_id in manual_criteria:
        criterion = criteria[criterion_id]
        self_assessment = criterion["owner_self_assessment"]
        assert self_assessment["status"] == "assessed_from_owner_answers"
        assert self_assessment["responses"][0]["answer"] == "not_sure"
        assert self_assessment["responses"][0]["reported_interpretation"]["outcome"] == "inconclusive"
        assert self_assessment["reported_outcome"] == "inconclusive"
        assert self_assessment["responses"][0]["independent_review"] is False
        assert criterion["manual_review_required"] is True
        assert self_assessment["criterion_conclusion"] is None
        assert criterion["compliance_conclusion"] is None


def test_owner_self_assessment_preserves_answers_when_browser_evidence_exists():
    evaluation = build_hybrid_evaluation(
        declared_features={},
        answers=(
            OwnerAnswer(
                question_id="forms.labels_and_instructions",
                answer="yes",
                explanation="Reviewed the public contact form.",
                page_urls=("https://example.test/contact",),
            ),
        ),
        browser_discoveries=(),
        browser_checks=(
            BrowserCriterionEvidence(
                criterion_id="3.3.2",
                analyzer_id="axe:label",
                result_status="incomplete",
                viewport="desktop",
                summary="Some form labels require review.",
                evidence_count=1,
            ),
        ),
    )
    criterion = next(
        item for item in evaluation["criteria"] if item["criterion_id"] == "3.3.2"
    )

    assert criterion["owner_self_assessment"]["status"] == "assessed_from_owner_answers"
    assert criterion["owner_self_assessment"]["responses"][0]["answer"] == "yes"
    assert criterion["owner_self_assessment"]["reported_outcome"] == "supports"
    assert criterion["browser_observed"][0]["result_status"] == "incomplete"
    assert criterion["status"] == "manual_review_needed"
    assert criterion["conflicts"] == []
    assert criterion["compliance_conclusion"] is None


def test_owner_support_is_flagged_when_browser_reports_criterion_violation():
    evaluation = build_hybrid_evaluation(
        declared_features={},
        answers=(
            OwnerAnswer(
                question_id="forms.labels_and_instructions",
                answer="yes",
                page_urls=("https://example.test/contact",),
            ),
        ),
        browser_discoveries=(),
        browser_checks=(
            BrowserCriterionEvidence(
                criterion_id="3.3.2",
                analyzer_id="axe:label",
                result_status="violations",
                viewport="mobile",
                summary="A visible form control has no associated label.",
                evidence_count=1,
            ),
        ),
    )
    criterion = next(
        item for item in evaluation["criteria"] if item["criterion_id"] == "3.3.2"
    )

    assert criterion["owner_self_assessment"]["reported_outcome"] == "supports"
    assert criterion["browser_observed"][0]["result_status"] == "violations"
    assert len(criterion["conflicts"]) == 1
    conflict = criterion["conflicts"][0]
    assert conflict["type"] == "owner_support_browser_concern"
    assert conflict["browser_evidence"][0]["analyzer_id"] == "axe:label"
    assert conflict["browser_evidence"][0]["viewport"] == "mobile"
    assert criterion["compliance_conclusion"] is None


def test_browser_pass_does_not_cancel_owner_reported_concern():
    evaluation = build_hybrid_evaluation(
        declared_features={},
        answers=(
            OwnerAnswer(
                question_id="forms.labels_and_instructions",
                answer="no",
            ),
        ),
        browser_discoveries=(),
        browser_checks=(
            BrowserCriterionEvidence(
                criterion_id="3.3.2",
                analyzer_id="axe:label",
                result_status="passes",
                viewport="desktop",
                summary="Axe rule passed on this viewport.",
                evidence_count=1,
            ),
        ),
    )
    criterion = next(
        item for item in evaluation["criteria"] if item["criterion_id"] == "3.3.2"
    )

    assert criterion["owner_self_assessment"]["reported_outcome"] == "indicates_concern"
    assert criterion["browser_observed"][0]["result_status"] == "passes"
    assert criterion["conflicts"] == []
    assert criterion["compliance_conclusion"] is None


def test_criteria_without_questionnaire_answers_are_not_self_assessed():
    evaluation = build_hybrid_evaluation(
        declared_features={},
        answers=(),
        browser_discoveries=(),
    )
    criterion = next(
        item for item in evaluation["criteria"] if item["criterion_id"] == "3.3.2"
    )

    assert criterion["owner_self_assessment"]["status"] == "not_provided"
    assert criterion["owner_self_assessment"]["responses"] == []
    assert criterion["owner_self_assessment"]["criterion_conclusion"] is None


def test_questionnaire_evaluates_yes_and_no_using_question_specific_polarity():
    evaluation = build_hybrid_evaluation(
        declared_features={},
        answers=(
            OwnerAnswer(
                question_id="forms.error_identification",
                answer="yes",
            ),
            OwnerAnswer(
                question_id="forms.repeated_entry",
                answer="yes",
            ),
            OwnerAnswer(
                question_id="media.live_captions",
                answer="no",
            ),
        ),
        browser_discoveries=(),
    )
    criteria = {item["criterion_id"]: item for item in evaluation["criteria"]}

    assert criteria["3.3.1"]["owner_self_assessment"]["reported_outcome"] == "supports"
    assert criteria["3.3.7"]["owner_self_assessment"]["reported_outcome"] == "indicates_concern"
    assert criteria["1.2.4"]["owner_self_assessment"]["reported_outcome"] == "indicates_concern"
    assert all(
        criteria[criterion_id]["compliance_conclusion"] is None
        for criterion_id in ("3.3.1", "3.3.7", "1.2.4")
    )


def test_shared_question_is_interpreted_only_for_relevant_criterion():
    evaluation = build_hybrid_evaluation(
        declared_features={},
        answers=(
            OwnerAnswer(question_id="visual.images_of_text", answer="yes"),
        ),
        browser_discoveries=(),
    )
    criteria = {item["criterion_id"]: item for item in evaluation["criteria"]}

    assert (
        criteria["1.4.5"]["owner_self_assessment"]["reported_outcome"]
        == "supports"
    )
    assert (
        criteria["1.1.1"]["owner_self_assessment"]["reported_outcome"]
        == "context_only"
    )


def test_manual_only_criteria_have_directional_owner_questions_without_claiming_review():
    from app.analyzers.hybrid_evaluation import (
        QUESTIONNAIRE_QUESTIONS,
        _OWNER_ASSESSMENT_YES_MEANING,
        WCAG_CRITERIA_CATALOG,
    )

    manual_criteria = {
        item["criterion_id"]
        for item in WCAG_CRITERIA_CATALOG
        if item["coverage_classification"] == "manual_evaluation_required"
    }
    directionally_questioned_criteria = {
        criterion_id
        for _question_id, criterion_id in _OWNER_ASSESSMENT_YES_MEANING
    }
    assert manual_criteria <= directionally_questioned_criteria

    answers = tuple(
        OwnerAnswer(question_id=question_id, answer="yes")
        for question_id in {
            question_id
            for question_id, _criterion_id in _OWNER_ASSESSMENT_YES_MEANING
        }
    )
    evaluation = build_hybrid_evaluation(
        declared_features={},
        answers=answers,
        browser_discoveries=(),
    )
    criteria = {item["criterion_id"]: item for item in evaluation["criteria"]}
    for criterion_id in manual_criteria:
        criterion = criteria[criterion_id]
        assert criterion["owner_self_assessment"]["status"] == "assessed_from_owner_answers"
        assert criterion["manual_review_required"] is True
        assert criterion["owner_self_assessment"]["criterion_conclusion"] is None
        assert criterion["compliance_conclusion"] is None


def test_existing_browser_checks_are_added_as_browser_observed_evidence():
    evaluation = build_hybrid_evaluation(
        declared_features={},
        answers=(),
        browser_discoveries=(),
        browser_checks=(
            BrowserCriterionEvidence(
                criterion_id="2.5.8",
                analyzer_id="target_size",
                result_status="available",
                viewport="mobile",
                summary="Measured target dimensions.",
                evidence_count=2,
            ),
        ),
    )
    criterion = next(
        item for item in evaluation["criteria"] if item["criterion_id"] == "2.5.8"
    )
    assert criterion["status"] == "browser_observed"
    assert criterion["manual_review_required"] is True
    assert criterion["browser_observed"][0]["analyzer_id"] == "target_size"
    assert criterion["compliance_conclusion"] is None


def test_context_urls_reject_credentials_queries_and_non_http_schemes():
    assert sanitize_context_url("https://example.test/guide") == (
        "https://example.test/guide"
    )
    for url in (
        "https://user:pass@example.test/page",
        "https://example.test/page?access_token=secret",
        "https://example.test/page#private",
        "javascript:alert(1)",
    ):
        with pytest.raises(ValueError):
            sanitize_context_url(url)


def test_questionnaire_rejects_sensitive_text_and_unknown_ids():
    with pytest.raises(ValueError, match="Do not include"):
        validate_questionnaire_inputs(
            answers=(
                OwnerAnswer(
                    question_id="forms.error_identification",
                    answer="yes",
                    explanation="password: hunter2",
                ),
            ),
            declared_features={},
        )
    with pytest.raises(ValueError, match="Unknown feature"):
        validate_questionnaire_inputs(
            answers=(),
            declared_features={"unknown_feature": True},
        )


def test_context_request_forbids_unmodeled_sensitive_fields():
    with pytest.raises(ValueError):
        AccessibilityContextRequest.model_validate(
            {
                "password": "do-not-accept",
            }
        )


def test_capture_request_and_report_keep_answers_attached_to_criteria():
    request = CaptureRequest.model_validate(
        {
            "url": "https://example.test/",
            "accessibility_context": {
                "representative_page_urls": ["https://example.test/contact"],
                "user_journeys": [
                    {
                        "name": "Submit a contact form",
                        "page_urls": ["https://example.test/contact"],
                    }
                ],
                "feature_presence": {"forms": True},
                "answers": [
                    {
                        "question_id": "forms.error_identification",
                        "answer": "not_sure",
                        "page_urls": ["https://example.test/contact"],
                    }
                ],
            },
        }
    )
    response = ResponsiveCaptureResponse.from_results(
        request.url,
        [],
        accessibility_context=request.accessibility_context,
    )
    criterion = next(
        item
        for item in response.hybrid_evaluation["criteria"]
        if item["criterion_id"] == "3.3.1"
    )
    assert criterion["status"] == "owner_reported"
    assert criterion["owner_reported"][0]["question_id"] == "forms.error_identification"
    assert criterion["owner_reported"][0]["verified"] is False
    assert response.hybrid_evaluation["representative_page_urls"] == [
        "https://example.test/contact"
    ]
    assert response.hybrid_evaluation["user_journeys"][0]["name"] == (
        "Submit a contact form"
    )
    pending = {
        question["question_id"]
        for question in response.hybrid_evaluation["questions_to_ask"]
    }
    assert "scope.representative_pages" not in pending
    assert "scope.user_journeys" not in pending
    assert "scope.features" not in pending


def test_initial_questionnaire_endpoint_discloses_limits_and_safety():
    with TestClient(app) as client:
        response = client.get("/accessibility/questionnaire")
    assert response.status_code == 200
    payload = response.json()
    assert payload["version"] == "1.0"
    assert payload["features"][0]["feature_id"] in {
        "prerecorded_media", "live_media", "forms"
    }
    assert "Do not submit passwords" in payload["safety_notice"]
    assert {item["question_id"] for item in payload["initial_questions"]} == {
        "scope.representative_pages",
        "scope.user_journeys",
        "scope.features",
    }
    conditional = {
        item["question_id"]: item for item in payload["conditional_questions"]
    }
    assert conditional["forms.error_identification"]["answer_interpretation"] == {
        "by_criterion": {
            "3.3.1": {
                "yes": "supports",
                "no": "indicates_concern",
                "not_sure": "inconclusive",
                "not_applicable": "not_applicable",
            }
        }
    }
    assert (
        conditional["forms.repeated_entry"]["answer_interpretation"]["by_criterion"]
        ["3.3.7"]["yes"]
        == "indicates_concern"
    )


def test_browser_feature_discovery_records_visible_feature_candidates():
    async def run() -> BrowserFeatureDiscovery:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            page = await browser.new_page()
            await page.set_content(
                """
                <form><label>Email <input type="email"></label></form>
                <input type="password" aria-label="Password">
                <video controls></video>
                """
            )
            result = await discover_browser_features(page, viewport="test")
            await browser.close()
            return result

    result = asyncio.run(run())
    assert result.status == "available"
    detected = {item.feature_id: item.count for item in result.features if item.detected}
    assert detected["forms"] == 1
    assert detected["authentication"] == 1
    assert detected["prerecorded_media"] == 1

import asyncio
from pathlib import Path

from fastapi.testclient import TestClient
from playwright.async_api import async_playwright

from app.main import app


ROOT = Path(__file__).resolve().parents[1]
INDEX_HTML = ROOT / "app" / "static" / "index.html"
QUESTIONNAIRE_JS = ROOT / "app" / "static" / "questionnaire.js"


def _question(question_id, criterion_id, feature_id, prompt):
    return {
        "question_id": question_id,
        "criterion_ids": [criterion_id],
        "feature_id": feature_id,
        "prompt": prompt,
        "answer_options": ["yes", "no", "not_sure", "not_applicable"],
        "helper_text": "Context only.",
    }


def test_frontend_is_served_with_accessible_integrated_capture_workflow():
    with TestClient(app) as client:
        page = client.get("/")
        script = client.get("/static/questionnaire.js")
        style = client.get("/static/styles.css")
    assert page.status_code == 200
    assert "Website URL" in page.text
    assert 'id="audit-form"' in page.text
    assert script.status_code == 200
    assert "Save answers & update audit" in script.text
    assert style.status_code == 200


def test_questionnaire_contract_exposes_conditional_questions_and_feature_labels():
    with TestClient(app) as client:
        response = client.get("/accessibility/questionnaire")
    assert response.status_code == 200
    payload = response.json()
    assert "Forms and data entry" in {
        item["label"] for item in payload["features"]
    }
    ids = {item["question_id"] for item in payload["conditional_questions"]}
    assert "forms.error_identification" in ids
    assert "authentication.cognitive_steps" in ids


def test_adaptive_frontend_preserves_answers_and_distinguishes_evidence():
    questionnaire = {
        "version": "1.0",
        "features": [
            {"feature_id": "forms", "label": "Forms and data entry"},
            {"feature_id": "authentication", "label": "Sign-in or authentication"},
        ],
        "conditional_questions": [
            _question("forms.error_identification", "3.3.1", "forms", "How are form errors described?"),
            _question(
                "authentication.cognitive_steps",
                "3.3.8",
                "authentication",
                "Which sign-in methods are available?",
            ),
        ],
    }
    audit_response = {
        "hybrid_evaluation": {
            "questions_to_ask": [
                _question(
                    "authentication.cognitive_steps",
                    "3.3.8",
                    "authentication",
                    "Which sign-in methods are available?",
                )
            ],
            "owner_answers": [
                {
                    "question_id": "forms.error_identification",
                    "answer": "yes",
                    "explanation": "Error messages appear beside fields.",
                }
            ],
            "declared_features": {"forms": True, "authentication": False},
            "conflicts": [
                {
                    "feature_id": "authentication",
                    "owner_reported_present": False,
                    "browser_observed_present": True,
                }
            ],
            "browser_discovery_status": "available",
            "criteria": [
                {
                    "criterion_id": "3.3.1",
                    "status": "manual_review_needed",
                    "manual_review_required": True,
                    "owner_reported": [{"question_id": "forms.error_identification"}],
                    "browser_observed": [
                        {
                            "analyzer_id": "axe:label",
                            "summary": "Form label rule evidence.",
                            "viewport": "desktop",
                        }
                    ],
                    "conflicts": [],
                    "compliance_conclusion": None,
                },
                {
                    "criterion_id": "3.3.8",
                    "status": "manual_review_needed",
                    "manual_review_required": True,
                    "owner_reported": [],
                    "browser_observed": [],
                    "conflicts": [],
                    "compliance_conclusion": None,
                },
            ],
        },
        "viewports": [
            {
                "browser_feature_discovery": {
                    "features": [
                        {
                            "feature_id": "forms",
                            "detected": True,
                            "count": 1,
                            "viewport": "desktop",
                            "evidence": ["A visible form was found."],
                        },
                        {
                            "feature_id": "authentication",
                            "detected": True,
                            "count": 1,
                            "viewport": "desktop",
                            "evidence": ["A password field candidate was found."],
                        },
                    ]
                }
            }
        ],
    }
    requests = []

    async def run():
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            page = await browser.new_page()
            await page.set_content(INDEX_HTML.read_text())
            await page.evaluate(
                """({questionnaire, auditResponse}) => {
                window.__requests = [];
                window.fetch = async (url, options = {}) => {
                  if (url === "/accessibility/questionnaire") {
                    return {ok: true, json: async () => questionnaire};
                  }
                  window.__requests.push(JSON.parse(options.body));
                  return {ok: true, json: async () => auditResponse};
                };
                }""",
                {"questionnaire": questionnaire, "auditResponse": audit_response},
            )
            await page.add_script_tag(path=str(QUESTIONNAIRE_JS))
            await page.wait_for_selector('input[name="feature-forms"]')

            assert await page.locator("#questions-panel").is_hidden()
            await page.locator(
                'input[name="feature-forms"][value="yes"]'
            ).check()
            assert await page.get_by_text(
                "How are form errors described?"
            ).is_visible()
            assert await page.get_by_text(
                "Which sign-in methods are available?"
            ).is_hidden()

            await page.locator(
                'input[name="feature-authentication"][value="no"]'
            ).check()
            await page.locator(
                'input[name="answer-forms.error_identification"][value="yes"]'
            ).check()
            await page.get_by_placeholder(
                "Context only; do not include sensitive information"
            ).fill("Error text is shown near the field.")
            await page.locator("#audit-url").fill("https://example.test")
            await page.locator("#representative-urls").fill(
                "https://example.test/contact"
            )
            await page.locator("#journeys").fill(
                "Submit a form | https://example.test/contact"
            )
            await page.locator("#features-complete").check()
            await page.locator("#submit-button").click()
            await page.wait_for_selector("#results:not([hidden])")

            requests = await page.evaluate("window.__requests")
            assert len(requests) == 1
            payload = requests[0]["accessibility_context"]
            assert payload["answers"][0]["question_id"] == "forms.error_identification"
            assert payload["answers"][0]["explanation"] == (
                "Error text is shown near the field."
            )
            assert payload["representative_page_urls"] == [
                "https://example.test/contact"
            ]
            assert payload["user_journeys"][0]["page_urls"] == [
                "https://example.test/contact"
            ]
            assert payload["feature_presence"]["authentication"] is False
            assert await page.get_by_text("Owner-reported · unverified").count() > 0
            assert await page.get_by_text(
                "Browser-observed · not a criterion conclusion"
            ).count() > 0
            assert await page.get_by_text(
                "Owner and browser information differ"
            ).is_visible()
            assert await page.locator("#criterion-summary").is_visible()
            assert await page.locator(".criterion-review-card").count() == 0
            assert await page.locator(".failure, .pass").count() == 0
            assert await page.get_by_text(
                "No criterion is marked passed from owner responses or missing evidence."
            ).is_visible()
            assert await page.get_by_text(
                "Which sign-in methods are available?"
            ).is_visible()
            await browser.close()

    asyncio.run(run())

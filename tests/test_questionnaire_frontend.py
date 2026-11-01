import asyncio
import json
import re
from pathlib import Path

from fastapi.testclient import TestClient
from playwright.async_api import async_playwright

from app.main import app


ROOT = Path(__file__).resolve().parents[1]
INDEX_HTML = ROOT / "app" / "static" / "index.html"
async def mount_react(page):
    async def serve(route):
        path = route.request.url.split("http://webable.test", 1)[1]
        asset = ROOT / "app" / "static" / (path.removeprefix("/static/") if path.startswith("/static/") else "index.html")
        await route.fulfill(path=str(asset))
    await page.route("http://webable.test/**", serve)
    await page.goto("http://webable.test/")



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
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json() == {"status": "ok"}
        page = client.get("/")
        assert page.status_code == 200
        assert 'id="root"' in page.text
        assets = re.findall(r'(?:src|href)="(/static/assets/[^"]+)"', page.text)
        assert len(assets) == 2
        for asset in assets:
            assert client.get(asset).status_code == 200


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


def test_capture_proxy_errors_allow_retry_without_json_parse_errors():
    async def run():
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            page = await browser.new_page()
            await page.add_init_script("""window.fetch = async (url) => {
                if (url === '/accessibility/questionnaire') {
                    return Response.json({features: [], conditional_questions: []});
                }
                if (window.__retry && url === '/captures/jobs') return Response.json({job_id: 'test'});
                return window.__retry
                    ? Response.json({status: 'completed', result: {requested_url: 'https://example.test', viewports: []}})
                    : new Response('', {status: 502});
            };""")
            await mount_react(page)
            await page.locator("#audit-url").fill("https://example.test")
            await page.locator("#submit-button").click()
            await page.wait_for_selector("#form-error")
            assert "HTTP 502" in await page.locator("#form-error").inner_text()
            assert "Unexpected end" not in await page.locator("#form-error").inner_text()
            assert await page.locator("#submit-button").is_enabled()
            await page.evaluate("window.__retry = true")
            await page.locator("#submit-button").click()
            await page.wait_for_selector("#results")
            assert await page.locator("#form-error").count() == 0
            await browser.close()

    asyncio.run(run())


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
            await page.add_init_script(
                """(({questionnaire, auditResponse}) => {
                window.__requests = [];
                window.fetch = async (url, options = {}) => {
                  if (url === "/accessibility/questionnaire") {
                    return {ok: true, json: async () => questionnaire};
                  }
                  if (url === '/captures/jobs') {
                    window.__requests.push(JSON.parse(options.body));
                    return Response.json({job_id: 'test'});
                  }
                  return Response.json({status: 'completed', result: auditResponse});
                };
                })(""" + json.dumps({"questionnaire": questionnaire, "auditResponse": audit_response}) + ");"
            )
            await mount_react(page)
            await page.wait_for_selector('input[name="feature-forms"]', state="attached")

            await page.locator("#website-context > summary").click()
            assert await page.locator("#questions-panel").is_hidden()
            await page.locator(
                'input[name="feature-forms"][value="yes"]'
            ).check()
            assert await page.get_by_text(
                "How are form errors described?"
            ).is_visible()
            assert await page.get_by_text(
                "Which sign-in methods are available?"
            ).count() == 0

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
            await page.get_by_role("tab", name="Owner Evidence", exact=True).click()
            assert await page.get_by_text("Owner-reported · unverified").count() > 0
            await page.get_by_role("tab", name="Overview", exact=True).click()
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


def test_dashboard_filters_safe_evidence_partial_states_and_mobile_keyboard():
    """Contract fixtures exercise data loss, injection, and partial-audit regressions."""
    rule = {
        "rule_id": "label", "help": "Controls need labels", "impact": "serious",
        "description": "Provide an accessible name.", "tags": ["wcag2a", "wcag131"],
        "help_url": "javascript:window.__injected=true",
        "nodes": [{"target": ["#unsafe"], "html": '<img src=x onerror="window.__injected=true">',
                   "failure_summary": "Missing label", "any_checks": [{"message": "Add a label"}]}],
    }
    response = {
        "requested_url": "https://example.test",
        "scoring": {"overall_score": None, "overall_coverage": 25, "overall_scoring_status": "insufficient_evidence",
                    "criteria": [{"status": "fail"}, {"status": "needs_review"}], "dimensions": [
                        {"name": "Deferred dimension", "implemented": False, "score": None, "passed_criteria": 0, "failed_criteria": 0, "needs_review_criteria": 0},
                        {"name": "Future dimension", "scoring_status": "not_implemented", "score": 0},
                        {"name": "Accessibility", "implemented": True, "score": 70, "coverage_percentage": 25, "score_label": "Provisional score", "coverage_label": "Limited evidence", "scoring_status": "provisional"}
                    ], "limitations": ["Partial evidence"]},
        "hybrid_evaluation": {
            "status": "partial", "conflicts": [{"criterion_id": "1.3.1", "summary": "Owner and browser conflict"}],
            "criteria": [{"criterion_id": "1.3.1", "title": "Info and Relationships", "status": "manual_review_needed",
                          "manual_review_required": True, "compliance_conclusion": None,
                          "owner_self_assessment": {"status": "assessed_from_owner_answers", "reported_outcome": "supports", "responses": []},
                          "browser_observed": [{"analyzer_id": "axe:label", "viewport": "desktop", "summary": "Same summary", "result_status": status}
                                               for status in ["pass", "fail", "needs_review"]]}],
        },
        "viewports": [{"name": name, "viewport": {"width": width, "height": 844}, "capture_outcome": "partial",
                       "accessibility_scan": {"status": "available", "violations": [rule]},
                       "target_size_audit": {"status": "available", "findings": []}}
                      for name, width in [("desktop", 1365), ("mobile", 390)]],
    }

    async def run():
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            page = await browser.new_page(viewport={"width": 390, "height": 844})
            page.set_default_timeout(7000)
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            await page.add_init_script("""(response => {
                window.__response = response;
                window.fetch = async (url) => url === '/accessibility/questionnaire'
                    ? {ok: true, json: async () => ({features: [], conditional_questions: []})}
                    : window.__fail ? {ok: false, json: async () => ({detail: 'Capture failed'})}
                    : url === '/captures/jobs' ? Response.json({job_id: 'test'})
                    : Response.json({status: 'completed', result: window.__response});
            })(""" + json.dumps(response) + ");")
            await mount_react(page)
            await page.locator("#audit-url").fill("https://example.test")
            await page.locator("#submit-button").click()
            await page.wait_for_selector("#results:not([hidden])")
            assert "Score unavailable" in await page.locator("#summary-cards").inner_text()
            deferred = page.locator(".not-evaluated")
            assert await deferred.count() == 2
            assert "Not currently evaluated" in await deferred.first.inner_text()
            assert "passed" not in await deferred.first.inner_text()
            assert "Score unavailable" not in await deferred.first.inner_text()
            assert "70 / 100" in await page.locator(".dimension").inner_text()
            assert "Limited evidence" in await page.locator(".dimension").inner_text()
            assert "undefined:" not in await page.locator("#conflicts").inner_text()
            browser_text = await page.locator("#browser-evidence").inner_text()
            for status in ["pass:", "fail:", "needs review:"]:
                assert status in browser_text
            await page.get_by_role("tab", name="Overview", exact=True).focus()
            await page.keyboard.press("ArrowRight")
            assert await page.get_by_role("tab", name="Issues", exact=True).get_attribute("aria-selected") == "true"
            await page.get_by_role("tab", name="Issues", exact=True).focus()
            await page.keyboard.press("Enter")
            assert await page.locator("#view-issues").is_visible()
            assert await page.locator("#issue-list > .finding").count() == 1
            assert "2 affected element observations" in await page.locator("#issue-list").inner_text()
            await page.get_by_label("Axe severity").select_option("critical")
            assert await page.locator("#issue-list > .finding").count() == 0
            await page.get_by_label("Axe severity").select_option("all")
            await page.get_by_label("Viewport", exact=True).select_option("mobile")
            assert "1 affected element observations" in await page.locator("#issue-list").inner_text()
            await page.locator("#issue-list summary").first.click()
            assert '<img src=x onerror=' in await page.locator("#issue-list pre").last.inner_text()
            assert await page.locator("#issue-list img").count() == 0
            assert await page.locator("#issue-list a").count() == 0
            assert not await page.evaluate("Boolean(window.__injected)")
            await page.get_by_role("tab", name="Owner Evidence", exact=True).click()
            assert "Support" in await page.locator("#owner-assessments").inner_text()
            await page.get_by_role("tab", name="Responsive", exact=True).click()
            assert "1365 × 844" in await page.locator("#responsive-cards").inner_text()
            assert await page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            await page.get_by_role("tab", name="WCAG", exact=True).click()
            await page.get_by_label("Evidence filter").select_option("manual")
            assert await page.locator("#wcag-list > .finding").count() == 1
            await page.add_script_tag(path=str(ROOT / "node_modules/axe-core/axe.min.js"))
            violations = await page.evaluate("""async () => (await axe.run(document, {
                runOnly: {type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa']}
            })).violations.map(v => ({id: v.id, targets: v.nodes.map(n => n.target)}))""")
            assert not violations
            await page.evaluate("window.__fail = true")
            await page.locator("#run-again").click()
            await page.wait_for_selector("#form-error:not([hidden])")
            assert "Capture failed" in await page.locator("#form-error").inner_text()
            assert await page.locator("#audit-loading").is_hidden()
            await page.evaluate("window.__fail = false; window.__response = {}")
            await page.locator("#run-again").click()
            await page.wait_for_selector("#results:not([hidden])")
            assert "Score unavailable" in await page.locator("#summary-cards").inner_text()
            await page.locator("#new-audit").click()
            assert await page.locator("#audit-url").input_value() == ""
            assert await page.locator("#audit-url").evaluate("el => el === document.activeElement")
            assert not errors
            await browser.close()

    asyncio.run(run())

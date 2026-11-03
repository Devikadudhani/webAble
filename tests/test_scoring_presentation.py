"""Check the built UI and PDF print view using calculated scoring results."""
import asyncio
import json
import math

import pytest
from playwright.async_api import async_playwright

from app.analyzers.scoring import DEFAULT_SCORING_CONFIGURATION, build_audit_scoring
from tests.test_scoring import _synthetic_scoring, _results, _replace_all
from app.capture.responsive import TechnicalEvidenceResult
from tests.test_questionnaire_frontend import mount_react

WARNING = "Provisional score based on limited automated evidence. Unevaluated checks may change this result. This is not a WCAG conformance rating."


def _scoring(case):
    criteria = [c for c in DEFAULT_SCORING_CONFIGURATION.criteria if c.implemented]
    if case == "blocked":
        return build_audit_scoring(_replace_all(_results(), technical_evidence=TechnicalEvidenceResult(
            status="available", access_status="restricted")))
    if case == "empty":
        return build_audit_scoring([])
    statuses = ({c.criterion_id: "fail" if i < 5 else "pass" for i, c in enumerate(criteria[:8])}
                if case == "47" else {c.criterion_id: "pass" for c in criteria})
    if case == "20":
        statuses = {criteria[0].criterion_id: "fail", criteria[1].criterion_id: "pass",
                    criteria[2].criterion_id: "fail"}
        statuses.update({c.criterion_id: "not_applicable" for c in criteria[-2:]})
    overall, dimensions = _synthetic_scoring(statuses)
    return {**overall, "dimensions": dimensions, "status_counts": {
        key: sum(d[f"{key}_criteria"] for d in dimensions)
        for key in ("passed", "failed", "needs_review", "unsupported", "not_tested", "error", "not_applicable")
    }}


@pytest.mark.parametrize("case", ["47", "20", "high", "blocked", "empty"])
def test_calculated_score_and_coverage_preserved_without_warning_on_screen_and_pdf(case):
    scoring = _scoring(case)
    response = {"requested_url": "https://example.test", "viewports": [], "scoring": scoring}

    async def run():
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            page = await browser.new_page()
            page.set_default_timeout(7000)
            await page.add_init_script("""(response => {
                window.fetch = async url => url === '/accessibility/questionnaire'
                    ? Response.json({features: [], conditional_questions: []})
                    : url === '/captures/jobs' ? Response.json({job_id: 'scoring-test'})
                    : Response.json({status: 'completed', result: response});
            })(""" + json.dumps(response) + ");")
            await mount_react(page)
            await page.locator("#audit-url").fill("https://example.test")
            await page.locator("#submit-button").click()
            await page.wait_for_selector(".analytics-section")
            summary = page.locator(".score-summary")
            ring = page.locator(".score-ring")
            if scoring["overall_score"] is None:
                assert "Score unavailable" in await ring.inner_text()
                assert "unavailable" in await ring.get_attribute("aria-label")
                assert await summary.locator(".score-warning").count() == 0
            else:
                displayed_score = f'{math.floor(scoring["overall_score"] * 10 + .5) / 10:g}'
                assert await ring.locator("strong").inner_text() == displayed_score
                assert f"Overall score: {displayed_score} / 100" in await page.locator(".analytics-score-summary").inner_text()
                coverage = f'{scoring["overall_coverage"]:.1f}'.rstrip("0").rstrip(".")
                assert await summary.locator(".score-coverage").inner_text() == f"{coverage}% evidence coverage"
                assert await page.locator(".score-warning").count() == 0
                for label in ("Confirmed failures", "Passed", "Needs review", "Unsupported", "Analyzer errors"):
                    assert label in await page.locator("#summary-cards").inner_text()
            assert WARNING not in await page.locator("body").inner_text()
            assert "Coverage and scores are not WCAG conformance percentages." in await page.locator(".analyzer-note").inner_text()
            screen_text = await summary.inner_text()
            screen_ring = await ring.get_attribute("aria-label")
            await page.evaluate("""() => {
                window.__printResult = null;
                window.print = () => {
                    const summary = document.querySelector('.score-summary');
                    window.__printResult = {
                        text: summary.innerText,
                        ring: document.querySelector('.score-ring').getAttribute('aria-label'),
                        visible: getComputedStyle(summary).display !== 'none',
                        warningCount: document.querySelectorAll('.score-warning').length,
                    };
                };
            }""")
            await page.emulate_media(media="print")
            await page.evaluate("document.querySelector('.result-actions button').click()")
            await page.wait_for_function("window.__printResult !== null")
            printed = await page.evaluate("window.__printResult")
            assert printed["text"] == screen_text
            assert printed["ring"] == screen_ring
            assert printed["visible"]
            assert printed["warningCount"] == 0
            assert WARNING not in await page.locator("body").inner_text()
            await browser.close()

    asyncio.run(run())

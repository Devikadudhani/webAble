"""Render actual capture output and verify visual encodings against its values."""
import asyncio
import json
import re

from fastapi.testclient import TestClient
from playwright.async_api import async_playwright

import app.main as main
from app.capture.runner import BrowserCapture
from app.capture.storage import LocalScreenshotStorage
from tests.test_capture import LocalhostValidator, fixture_server
from tests.test_questionnaire_frontend import ROOT, mount_react


def test_actual_capture_visualizations_and_responsive_layout(fixture_server, tmp_path, monkeypatch):
    monkeypatch.setattr(main, "url_validator", LocalhostValidator())
    monkeypatch.setattr(main, "capture_service", BrowserCapture(
        storage=LocalScreenshotStorage(tmp_path), url_validator=LocalhostValidator(),
        navigation_timeout_ms=1000, settling_period_ms=50,
    ))
    with TestClient(main.app) as client:
        questionnaire = client.get("/accessibility/questionnaire").json()
        result = client.post("/captures", json={"url": f"{fixture_server}/accessibility"})
    assert result.status_code == 200
    response = result.json()

    async def run():
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            page = await browser.new_page(viewport={"width": 1440, "height": 1000})
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            await page.add_init_script("""(({questionnaire, response}) => {
              window.fetch = async url => ({ok: true, json: async () =>
                url === '/accessibility/questionnaire' ? questionnaire
                : url === '/captures/jobs' ? {job_id: 'test'}
                : {status: 'completed', result: response}});
            })(""" + json.dumps({"questionnaire": questionnaire, "response": response}) + ");")
            await mount_react(page)
            await page.screenshot(path="/tmp/webable-landing.png", full_page=True)
            assert await page.evaluate("getComputedStyle(document.documentElement).backgroundColor") == "rgb(255, 255, 255)"
            await page.locator("#audit-url").fill(f"{fixture_server}/accessibility")
            await page.locator("#submit-button").click()
            await page.locator("#results").wait_for()
            score = response["scoring"]["overall_score"]
            coverage = response["scoring"]["overall_coverage"]
            score_label = await page.locator(".score-ring").get_attribute("aria-label")
            if score is None:
                assert "unavailable" in score_label
            else:
                assert float(re.search(r"score: ([\d.]+)", score_label)[1]) == round(score, 1)
            coverage_text = await page.locator(".coverage-summary").inner_text()
            if coverage is None:
                assert "Unavailable" in coverage_text
            else:
                assert float(re.search(r"([\d.]+)%", coverage_text)[1]) == round(coverage, 1)
            legend = await page.locator(".outcome-summary .chart-legend").inner_text()
            for status in ["pass", "fail", "needs_review"]:
                assert str(sum(c["status"] == status for c in response["scoring"]["criteria"])) in legend
            await page.screenshot(path="/tmp/webable-results.png", full_page=True)
            await page.get_by_role("tab", name="Responsive", exact=True).click()
            for row, viewport in zip(await page.locator(".viewport-bar").all(), response["viewports"]):
                assert await row.locator("strong").inner_text() == str(len(viewport["accessibility_scan"]["violations"]))
            await page.get_by_role("tab", name="WCAG", exact=True).click()
            assert sum(int(x) for x in await page.locator(".evidence-distribution dd").all_text_contents()) == len(response["hybrid_evaluation"]["criteria"])
            for width in [390, 768]:
                await page.set_viewport_size({"width": width, "height": 844})
                for name in ["Overview", "Issues", "WCAG", "Responsive", "Owner Evidence"]:
                    await page.get_by_role("tab", name=name, exact=True).click()
                    assert await page.evaluate("document.documentElement.scrollWidth <= innerWidth"), (width, name)
            await page.set_viewport_size({"width": 390, "height": 844})
            await page.get_by_role("tab", name="Overview", exact=True).click()
            await page.screenshot(path="/tmp/webable-mobile.png", full_page=True)
            await page.add_script_tag(path=str(ROOT / "node_modules/axe-core/axe.min.js"))
            for name in ["Overview", "Issues", "WCAG", "Responsive", "Owner Evidence"]:
                await page.get_by_role("tab", name=name, exact=True).click()
                violations = await page.evaluate("""async () => (await axe.run(document, {
                  runOnly: {type:'tag',values:['wcag2a','wcag2aa','wcag21aa','wcag22aa']}
                })).violations.map(v => ({id:v.id,targets:v.nodes.map(n=>n.target)}))""")
                assert not violations, (name, violations)
            assert not errors
            await browser.close()
    asyncio.run(run())

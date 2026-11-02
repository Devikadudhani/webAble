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
    for viewport in response["viewports"]:
        viewport["accessibility_scan"]["violations"] = []
        viewport["finding_normalization"]["findings"] = []
        viewport["functional_ux_audit"]["findings"] = []
        viewport["target_size_audit"]["findings"] = []
    for viewport in response["viewports"][:2]:
        viewport["target_size_audit"]["findings"] = [
            {
                "criterion_id": "2.5.8",
                "selector": "#small-target",
                "tag_name": "button",
                "role": "button",
                "accessible_name": "Open",
                "width_css_px": 18,
                "height_css_px": 18,
                "left_css_px": 12,
                "top_css_px": 20,
            }
        ]
    technical_dimension = next(
        dimension
        for dimension in response["scoring"]["dimensions"]
        if dimension["dimension_id"] == "technical_reliability"
    )
    technical_dimension.update(
        {
            "score": 100,
            "score_basis": "conclusive_checks",
            "score_range": {"min": 38.5, "max": 100},
            "coverage_percentage": 50,
            "score_label": "excellent",
            "scoring_status": "provisional",
        }
    )

    async def run():
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            page = await browser.new_page(viewport={"width": 1440, "height": 1000})
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            await page.add_init_script("""(({questionnaire, response}) => {
              window.__scanCount = 0;
              window.fetch = async url => {
                if (url === '/accessibility/questionnaire') {
                  return {ok: true, json: async () => questionnaire};
                }
                if (url === '/captures/jobs') {
                  window.__scanCount += 1;
                  return Response.json({job_id: `test-${window.__scanCount}`});
                }
                const current = window.__scanCount > 1
                  ? {...response, scoring: {...response.scoring, scoring_configuration_version: '2.0.0'}}
                  : response;
                return Response.json({status: 'completed', result: current});
              };
            })(""" + json.dumps({"questionnaire": questionnaire, "response": response}) + ");")
            await mount_react(page)
            async def serve_screenshot(route):
                filename = route.request.url.rsplit("/", 1)[-1]
                screenshot = tmp_path / "screenshots" / filename
                if screenshot.is_file():
                    await route.fulfill(path=str(screenshot), content_type="image/png")
                else:
                    await route.fulfill(status=404)
            await page.route("http://webable.test/captures/screenshots/**", serve_screenshot)
            await page.screenshot(path="/tmp/webable-landing.png", full_page=True)
            assert await page.evaluate("getComputedStyle(document.documentElement).backgroundColor") == "rgb(11, 11, 11)"
            await page.add_script_tag(path=str(ROOT / "node_modules/axe-core/axe.min.js"))
            landing_violations = await page.evaluate("""async () => (await axe.run(document, {
              runOnly: {type:'tag',values:['wcag2a','wcag2aa','wcag21aa','wcag22aa']}
            })).violations.map(v => ({id:v.id,targets:v.nodes.map(n=>n.target)}))""")
            assert not landing_violations, landing_violations
            await page.locator("#audit-url").fill(f"{fixture_server}/accessibility")
            await page.locator("#submit-button").click()
            await page.locator("#results").wait_for()
            await page.get_by_role("heading", name="Baseline Website").wait_for()
            assert await page.locator(".viewport-selector button").count() == 3
            assert await page.locator(".screenshot-stage img").count() == 1
            assert await page.locator(".screenshot-stage img").evaluate("(image) => image.complete && image.naturalWidth > 0")
            await page.get_by_role("button", name="Enlarge screenshot").click()
            assert await page.get_by_role("dialog", name="Enlarged First saved scan").is_visible()
            await page.get_by_role("button", name="Close").click()
            await page.get_by_role("tab", name="Overview", exact=True).click()
            technical_card = page.locator(".dimension").filter(
                has_text="Technical reliability"
            )
            assert "Score on conclusive checks" in await technical_card.inner_text()
            assert "excellent on conclusive checks only" in await technical_card.inner_text()
            await page.locator("#run-again").click()
            await page.locator(".verification-summary").wait_for()
            assert "Score history is not compared" in await page.locator(".verification-note").first.inner_text()
            assert await page.locator(".visual-captures.is-comparison .capture-panel").count() == 2, await page.locator("#baseline-website").inner_text()
            assert "1 baseline findings compared" in (await page.locator(".verification-summary").inner_text()).lower()
            contextual_verification = page.locator(".contextual-verification")
            await contextual_verification.locator("summary").click()
            assert "still detected" in (await contextual_verification.inner_text()).lower()
            assert "1 coordinate-backed" in await page.locator(".visual-finding-links summary").inner_text()
            await page.evaluate("""() => {
              const key = Object.keys(localStorage).find(item =>
                item.startsWith('webable.visual-baseline.v1:')
              );
              const baseline = JSON.parse(localStorage.getItem(key));
              baseline.viewports = baseline.viewports.map(viewport => ({
                ...viewport,
                screenshot_ref: 'screenshots/missing-baseline.png',
              }));
              localStorage.setItem(key, JSON.stringify(baseline));
            }""")
            await page.locator("#run-again").click()
            await page.locator(".verification-summary").wait_for()
            await page.get_by_text("Baseline screenshot unavailable").wait_for()
            assert await page.locator(".visual-captures.is-comparison .capture-panel").count() == 0
            assert await page.locator(".visual-captures .capture-panel").count() == 1
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
            for name in ["Overview", "Issues", "WCAG", "Responsive", "Owner Evidence"]:
                await page.get_by_role("tab", name=name, exact=True).click()
                violations = await page.evaluate("""async () => (await axe.run(document, {
                  runOnly: {type:'tag',values:['wcag2a','wcag2aa','wcag21aa','wcag22aa']}
                })).violations.map(v => ({id:v.id,targets:v.nodes.map(n=>n.target)}))""")
                assert not violations, (name, violations)
            assert not errors
            await browser.close()
    asyncio.run(run())

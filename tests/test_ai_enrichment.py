import asyncio

from PIL import Image

from app.analyzers import ai_enrichment
from app.analyzers.ai_enrichment import (
    AuditSummary,
    ExplanationResponse,
    GroupExplanation,
    _crop_screenshot,
    _explain_batch,
    group_findings,
    run_ai_layer,
)


def _explanation(group_id):
    return GroupExplanation(
        group_id=group_id,
        title="A control needs review",
        explanation="This element needs review.",
        what_is_happening="The analyzer observed a control without an accessible name.",
        why_it_matters="Some people may not know what the control does.",
        who_is_affected="People who use the affected control.",
        reproduction_steps=["Open the tested viewport.", "Inspect the control."],
        fix_hint="Inspect the element and follow the rule guidance.",
        priority=2,
        priority_reason="The analyzer reported a serious issue.",
        confidence="medium",
        evidence_limitations=[],
    )


def test_group_findings_limits_examples_and_groups_viewports():
    findings = [
        {
            "id": f"label:{index}",
            "rule_id": "label",
            "severity": "serious",
            "viewport": "desktop" if index == 0 else "mobile",
            "selector": f"#{index}",
            "html": "x" * 500,
            "message": "Missing accessible name",
        }
        for index in range(4)
    ]

    [group] = group_findings(findings)

    assert group["count"] == 4
    assert group["viewports"] == ["desktop", "mobile"]
    assert len(group["sample_selectors"]) == 3
    assert len(group["sample_html"]) == ai_enrichment.MAX_HTML_CHARS


def test_group_identity_keeps_distinct_categories_separate():
    groups = group_findings(
        [
            {"id": "axe:1", "rule_id": "shared", "category": "accessibility"},
            {"id": "functional:1", "rule_id": "shared", "category": "functional"},
        ]
    )

    assert len(groups) == 2
    assert {group["group_id"] for group in groups} == {
        "shared:accessibility",
        "shared:functional",
    }


def test_unknown_provider_group_id_is_discarded(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    group = group_findings(
        [
            {
                "id": "real:1",
                "rule_id": "real",
                "severity": "moderate",
                "message": "Real issue",
            }
        ]
    )[0]
    monkeypatch.setattr(
        ai_enrichment,
        "_groq_explanations",
        lambda _prompt, **_kwargs: ExplanationResponse(
            items=[_explanation("invented")]
        ),
    )

    explanations, provider = _explain_batch([group])

    assert provider == "groq"
    assert explanations[0]["group_id"] == "real:general"
    assert explanations[0]["source"] == "template"


def test_groq_failure_uses_gemini_fallback(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    group = group_findings(
        [{"id": "real:1", "rule_id": "real", "severity": "minor"}]
    )[0]
    monkeypatch.setattr(
        ai_enrichment,
        "_groq_explanations",
        lambda _prompt, **_kwargs: (_ for _ in ()).throw(RuntimeError("offline")),
    )
    monkeypatch.setattr(
        ai_enrichment,
        "_gemini_explanations",
        lambda _prompt, **_kwargs: ExplanationResponse(
            items=[_explanation("real:general")]
        ),
    )

    diagnostics = []
    explanations, provider = _explain_batch([group], diagnostics=diagnostics)

    assert provider == "gemini"
    assert explanations[0]["source"] == "gemini"
    assert [item["status"] for item in diagnostics] == ["failed", "success"]
    assert diagnostics[1]["fallback_used"] is True
    assert "offline" not in str(diagnostics)


def test_missing_provider_keys_uses_local_template(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    result = run_ai_layer(
        [
            {
                "id": "label:1",
                "rule_id": "label",
                "severity": "serious",
                "message": "Give the control an accessible name.",
            }
        ],
        lambda _finding: None,
    )

    assert result["status"] == "unavailable"
    assert result["explanations"][0]["source"] == "template"
    assert result["stats"]["raw_findings"] == 1
    assert any("no provider API keys" in item for item in result["details"])
    assert result["audit_summary"]["source"] == "template"
    assert result["audit_summary"]["overall_summary"].find("did not produce an overall score") >= 0
    assert result["explanations"][0]["title"]


def test_summary_uses_bounded_context_and_records_provider(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    group = group_findings(
        [{"id": "real:1", "rule_id": "real", "severity": "serious", "message": "Observed issue"}]
    )
    monkeypatch.setattr(
        ai_enrichment,
        "_groq_explanations",
        lambda _prompt, **_kwargs: ExplanationResponse(
            items=[_explanation("real:general")]
        ),
    )
    prompts = []

    def summarize(prompt, **_kwargs):
        prompts.append(prompt)
        return AuditSummary(
            overall_summary="A partial audit summary.",
            health_assessment="Coverage is limited.",
            key_strengths=[],
            major_concerns=["One serious finding group."],
            recommended_actions=["Inspect the finding."],
            limitations=["Some checks were sampled."],
        )

    monkeypatch.setattr(ai_enrichment, "_groq_summary", summarize)
    diagnostics = []
    summary = ai_enrichment._summarize_audit(
        {"overall_score": None, "overall_coverage": 25, "limitations": ["Partial"]},
        group,
        deadline=ai_enrichment.time.monotonic() + 10,
        diagnostics=diagnostics,
    )

    assert summary["source"] == "groq"
    assert "did not produce an overall score" in summary["overall_summary"]
    assert "overall_score" in prompts[0]
    assert diagnostics[0]["status"] == "success"
    assert diagnostics[0]["provider"] == "groq"


def test_visual_screenshot_loader_failure_does_not_break_explanations(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(
        ai_enrichment,
        "_gemini_explanations",
        lambda _prompt, **_kwargs: (_ for _ in ()).throw(RuntimeError("offline")),
    )
    monkeypatch.setattr(
        ai_enrichment,
        "_gemini_summary",
        lambda _prompt, **_kwargs: (_ for _ in ()).throw(RuntimeError("offline")),
    )
    result = run_ai_layer(
        [{
            "id": "overflow:1",
            "rule_id": "overflow",
            "severity": "serious",
            "message": "Possible overflow",
            "viewport": "mobile",
            "bounds": {"left": 1, "top": 1, "width": 10, "height": 10},
            "needs_review": True,
        }],
        lambda _finding: (_ for _ in ()).throw(OSError("missing")),
    )

    assert result["explanations"]
    assert result["stats"]["vision_calls"] == 0


def test_visual_screenshot_is_cropped_to_measured_bounds():
    import io

    image = Image.new("RGB", (800, 600), color="white")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")

    cropped = _crop_screenshot(
        buffer.getvalue(),
        {"left": 300, "top": 250, "width": 20, "height": 20},
    )

    assert cropped is not None
    with Image.open(io.BytesIO(cropped)) as result:
        assert result.size == (116, 116)


def test_ai_assistance_requires_explicit_request_opt_in(monkeypatch):
    import app.main as main

    monkeypatch.setattr(main.url_validator, "validate", lambda _url: _allow_url())
    monkeypatch.setattr(main, "capture_responsive_viewports", _empty_capture)
    calls = []

    def run_ai(findings, _load_screenshot, _audit_context):
        calls.append(findings)
        return {
            "status": "available",
            "groups": [],
            "explanations": [],
            "visual_checks": [],
            "audit_summary": None,
            "stats": {
                "raw_findings": 0,
                "issue_groups": 0,
                "explained_groups": 0,
                "vision_calls": 0,
            },
            "details": [],
        }

    monkeypatch.setattr(main, "run_ai_layer", run_ai)

    async def run():
        without_opt_in = await main.create_capture(
            main.CaptureRequest(url="https://example.test")
        )
        with_opt_in = await main.create_capture(
            main.CaptureRequest(
                url="https://example.test", ai_assistance_opt_in=True
            )
        )
        return without_opt_in, with_opt_in

    without_opt_in, with_opt_in = asyncio.run(run())

    assert without_opt_in.ai_analysis is None
    assert with_opt_in.ai_analysis.status == "available"
    assert calls == [[]]


async def _allow_url():
    return None


async def _empty_capture(*_args, **_kwargs):
    return []

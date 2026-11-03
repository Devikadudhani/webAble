"""Deterministic capture-classification tests; no Chromium or network required."""

from types import SimpleNamespace

import pytest

from app.capture.runner import BrowserCapture


def _evidence(status="unavailable"):
    return SimpleNamespace(
        access_status=status,
        details=[],
        access_restriction_signals=[],
        access_restriction_provider=None,
        access_restriction_reference=None,
        main_document_http_status=None,
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    ("name", "body", "status", "expected", "provider"),
    [
        ("successful_page", "Welcome to the product catalogue", 200, False, None),
        (
            "akamai_denial",
            "Access Denied Reference #18.5d6a3717.1793626490.389a730f https://errors.edgesuite.net/18.5d6a3717.1793626490.389a730f",
            403,
            True,
            "Akamai EdgeSuite",
        ),
        ("captcha_challenge", "Please verify you are human to continue", 200, True, None),
        ("authentication_wall", "Sign in to continue", 200, True, None),
        ("consent_overlay_only", "Cookie preferences", 200, False, None),
        ("browser_error", "This site can't be reached", None, True, None),
        ("http_error", "Unexpected server response", 503, True, None),
    ],
)
def test_access_restriction_classification(
    name, body, status, expected, provider
):
    """Classifies controlled page text without navigating a real website."""
    evidence = _evidence()
    evidence.main_document_http_status = status

    restricted = BrowserCapture._has_access_restriction(
        body.lower(), "https://example.test/", evidence
    )

    assert restricted is expected, name
    if expected:
        assert evidence.access_status in {"restricted", "unavailable"}
    if provider:
        assert evidence.access_restriction_provider == provider


@pytest.mark.unit
def test_akamai_reference_is_retained_as_diagnostic_metadata():
    """An Akamai reference is diagnostics, not target-site evidence."""
    evidence = _evidence()
    body = (
        "Access Denied. Reference #18.5d6a3717.1793626490.389a730f "
        "https://errors.edgesuite.net/18.5d6a3717.1793626490.389a730f"
    )

    assert BrowserCapture._has_access_restriction(body.lower(), "https://example.test/", evidence)
    assert evidence.access_restriction_provider == "Akamai EdgeSuite"
    assert evidence.access_restriction_reference == "18.5d6a3717.1793626490.389a730f"
    assert any("could not inspect the actual website" in item for item in evidence.details)

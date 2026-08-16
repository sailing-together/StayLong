"""Accessibility and static UI contract tests."""

from fastapi.testclient import TestClient

from staylong.api.app import create_app


def test_family_ui_is_served_by_the_api() -> None:
    response = TestClient(create_app(api_token="secret-token")).get("/")

    assert response.status_code == 200
    assert 'name="viewport"' in response.text
    assert '<main id="main-content"' in response.text
    assert 'for="concern-summary"' in response.text


def test_ui_has_a_skip_link_and_safety_boundary() -> None:
    html = TestClient(create_app(api_token="secret-token")).get("/").text

    assert 'href="#main-content"' in html
    assert "does not diagnose" in html
    assert "/static/styles.css" in html

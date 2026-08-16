"""Repeatable end-to-end contract test for the family UI and case-flow API."""

from html.parser import HTMLParser

from fastapi.testclient import TestClient

from staylong.api.app import create_app


class FormControls(HTMLParser):
    """Collect the form controls a browser needs to complete the first workflow step."""

    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.form_actions: list[str] = []
        self.scripts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag in {"input", "textarea", "button"} and attributes.get("id"):
            self.ids.add(attributes["id"] or "")
        if tag == "form":
            self.form_actions.append(attributes.get("id", ""))
        if tag == "script" and attributes.get("src"):
            self.scripts.append(attributes["src"] or "")


def test_family_case_workflow_connects_ui_to_authenticated_api() -> None:
    """A browser can load the UI, submit its form payload, and read the case trail."""
    client = TestClient(create_app(api_token="workflow-token"))

    page = client.get("/")
    assert page.status_code == 200
    parser = FormControls()
    parser.feed(page.text)
    assert parser.form_actions == ["concern-form"]
    assert {"api-token", "concern-summary"} <= parser.ids
    assert "/static/app.js" in parser.scripts

    summary = "The bathroom entry is difficult to use at night."
    created = client.post(
        "/v1/cases",
        json={"summary": summary},
        headers={"Authorization": "Bearer workflow-token"},
    )
    assert created.status_code == 201
    case_id = created.json()["case_id"]

    trail = client.get(
        f"/v1/cases/{case_id}/concerns",
        headers={"Authorization": "Bearer workflow-token"},
    )
    assert trail.status_code == 200
    trail_body = trail.json()
    assert len(trail_body) == 1
    assert trail_body == [
        {
            "case_id": case_id,
            "concern_id": trail_body[0]["concern_id"],
            "summary": summary,
        }
    ]


def test_family_case_workflow_cannot_submit_without_authentication() -> None:
    client = TestClient(create_app(api_token="workflow-token"))

    response = client.post("/v1/cases", json={"summary": "A concern from the form."})

    assert response.status_code == 401

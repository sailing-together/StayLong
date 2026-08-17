"""API contract and authentication tests."""

from fastapi.testclient import TestClient

from staylong.api.app import create_app


def test_health_check_is_public() -> None:
    response = TestClient(create_app(api_token="secret-token")).get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_case_flow_requires_bearer_authentication() -> None:
    client = TestClient(create_app(api_token="secret-token"))

    assert client.post("/v1/cases", json={"summary": "The entry is difficult."}).status_code == 401
    assert client.post(
        "/v1/cases",
        json={"summary": "The entry is difficult."},
        headers={"Authorization": "Bearer wrong-token"},
    ).status_code == 401


def test_authenticated_case_flow_creates_and_reads_a_concern() -> None:
    client = TestClient(create_app(api_token="secret-token"))
    headers = {"Authorization": "Bearer secret-token"}

    created = client.post(
        "/v1/cases",
        json={"summary": "The bathroom step is difficult."},
        headers=headers,
    )

    assert created.status_code == 201
    case_id = created.json()["case_id"]
    concerns = client.get(f"/v1/cases/{case_id}/concerns", headers=headers)

    assert concerns.status_code == 200
    assert concerns.json()[0]["summary"] == "The bathroom step is difficult."


def test_authenticated_case_flow_accepts_proxy_application_token_header() -> None:
    client = TestClient(create_app(api_token="secret-token"))

    response = client.post(
        "/v1/cases",
        json={"summary": "The bathroom step is difficult."},
        headers={"X-StayLong-API-Token": "secret-token"},
    )

    assert response.status_code == 201


def test_case_input_rejects_unknown_fields() -> None:
    client = TestClient(create_app(api_token="secret-token"))

    response = client.post(
        "/v1/cases",
        json={"summary": "A concern", "diagnosis": "unsafe"},
        headers={"Authorization": "Bearer secret-token"},
    )

    assert response.status_code == 422

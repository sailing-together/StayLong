"""Tests for the deployment smoke-test contract."""

import pytest

import tools.cloudrun_smoke as smoke
from tools.cloudrun_smoke import HttpResponse, SmokeTestError, UrlLibClient, run_smoke


class FakeClient:
    def __init__(self) -> None:
        self.requests: list[tuple[str, str]] = []

    def request(
        self,
        method: str,
        path: str,
        payload: dict[str, str] | None = None,
    ) -> HttpResponse:
        del payload
        self.requests.append((method, path))
        if path == "/healthz":
            return HttpResponse(200, {"status": "ok"})
        if method == "POST":
            return HttpResponse(201, {"case_id": "case-smoke"})
        return HttpResponse(200, [{"summary": "The bathroom entry needs a safer path."}])


def test_smoke_flow_checks_health_then_create_and_read() -> None:
    client = FakeClient()

    assert run_smoke(client) == "case-smoke"
    assert client.requests == [
        ("GET", "/healthz"),
        ("POST", "/v1/cases"),
        ("GET", "/v1/cases/case-smoke/concerns"),
    ]


def test_smoke_flow_rejects_unhealthy_service() -> None:
    class UnhealthyClient(FakeClient):
        def request(
            self,
            method: str,
            path: str,
            payload: dict[str, str] | None = None,
        ) -> HttpResponse:
            del method, payload
            if path == "/healthz":
                return HttpResponse(503, {"status": "starting"})
            return super().request("GET", path)

    with pytest.raises(SmokeTestError, match="health check failed"):
        run_smoke(UnhealthyClient())


def test_url_lib_client_separates_cloud_run_and_application_tokens(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[object] = []

    class Response:
        status = 200

        def __enter__(self) -> "Response":
            return self

        def __exit__(self, *args: object) -> None:
            del args

        @staticmethod
        def read() -> bytes:
            return b'{"status":"ok"}'

    def fake_urlopen(request: object, timeout: int) -> Response:
        del timeout
        captured.append(request)
        return Response()

    monkeypatch.setattr(smoke, "urlopen", fake_urlopen)

    response = UrlLibClient("https://example.test", "app-token", "run-token").request(
        "GET", "/healthz"
    )

    request = captured[0]
    assert response == HttpResponse(200, {"status": "ok"})
    assert request.headers["Authorization"] == "Bearer app-token"  # type: ignore[attr-defined]
    assert request.headers["X-serverless-authorization"] == "Bearer run-token"  # type: ignore[attr-defined]

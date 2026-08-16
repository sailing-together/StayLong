"""Tests for the deployment smoke-test contract."""

import pytest

from tools.cloudrun_smoke import HttpResponse, SmokeTestError, run_smoke


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

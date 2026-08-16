"""Smoke-test the public health and authenticated case-flow endpoints."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class SmokeTestError(RuntimeError):
    """Raised when a deployed service does not satisfy the smoke-test contract."""


@dataclass(frozen=True)
class HttpResponse:
    status: int
    body: Mapping[str, object]


class UrlLibClient:
    """Small standard-library client so the deployment check has no extra dependency."""

    def __init__(self, base_url: str, token: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token

    def request(
        self,
        method: str,
        path: str,
        payload: Mapping[str, str] | None = None,
    ) -> HttpResponse:
        data = json.dumps(payload).encode() if payload is not None else None
        headers = {"Authorization": f"Bearer {self.token}"}
        if data is not None:
            headers["Content-Type"] = "application/json"
        request = Request(f"{self.base_url}{path}", data=data, headers=headers, method=method)
        try:
            with urlopen(request, timeout=15) as response:  # noqa: S310 - URL is operator-provided.
                return HttpResponse(response.status, json.loads(response.read()))
        except HTTPError as error:
            try:
                body = json.loads(error.read())
            except json.JSONDecodeError:
                body = {}
            return HttpResponse(error.code, body)
        except URLError as error:
            raise SmokeTestError(f"service was unreachable: {error.reason}") from error


def _expect(response: HttpResponse, status: int, message: str) -> Mapping[str, object]:
    if response.status != status:
        raise SmokeTestError(f"{message}: expected {status}, received {response.status}")
    return response.body


def run_smoke(client: object, summary: str = "The bathroom entry needs a safer path.") -> str:
    """Verify health, auth and a minimal create/read case flow; return the case id."""
    health = _expect(client.request("GET", "/healthz"), 200, "health check failed")
    if health.get("status") != "ok":
        raise SmokeTestError("health check returned an unexpected payload")

    created = _expect(
        client.request("POST", "/v1/cases", {"summary": summary}),
        201,
        "case creation failed",
    )
    case_id = created.get("case_id")
    if not isinstance(case_id, str) or not case_id:
        raise SmokeTestError("case creation did not return a case id")

    concerns = _expect(
        client.request("GET", f"/v1/cases/{case_id}/concerns"),
        200,
        "case read failed",
    )
    if not isinstance(concerns, list) or not concerns:
        raise SmokeTestError("case read returned no concern")
    return case_id


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True, help="Cloud Run service URL")
    parser.add_argument("--token", required=True, help="API bearer token (never printed)")
    args = parser.parse_args()
    try:
        case_id = run_smoke(UrlLibClient(args.url, args.token))
    except SmokeTestError as error:
        print(f"Smoke test failed: {error}", file=sys.stderr)
        return 1
    print(f"Smoke test passed for {case_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

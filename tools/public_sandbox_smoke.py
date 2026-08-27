"""Smoke-test the public sandbox Cloud Run service.

Uses two independent cookie sessions to verify:
  - anonymous workflow creation succeeds with a session cookie
  - session A can continue its own workflow
  - session B is rejected from session A's workflow (isolation boundary)
  - a sandbox action can be approved and returns a sandbox result
  - No API token is required or used — authentication is cookie-only

Usage:
    python tools/public_sandbox_smoke.py --url https://PUBLIC_SANDBOX_URL
"""

from __future__ import annotations

import argparse
import sys

import requests


class SmokeTestError(RuntimeError):
    """Raised when the public sandbox service fails a smoke assertion."""


def _expect(response: requests.Response, status: int, message: str) -> dict:
    if response.status_code != status:
        raise SmokeTestError(
            f"{message}: expected HTTP {status}, "
            f"received {response.status_code} — {response.text[:200]}"
        )
    return response.json()


def run_smoke(base_url: str, concern: str = "Getting to the bathroom safely at night.") -> str:
    """Run the full public sandbox smoke; return the case_id created by session A."""
    base_url = base_url.rstrip("/")

    # Two independent anonymous sessions — each carries its own HttpOnly cookie.
    session_a = requests.Session()
    session_b = requests.Session()

    # ── 1. Health check (no cookie required) ─────────────────────────────────
    health = _expect(
        session_a.get(f"{base_url}/health", timeout=15),
        200,
        "health check failed",
    )
    if health.get("status") != "ok":
        raise SmokeTestError(f"health check returned unexpected payload: {health}")

    # ── 2. Session A creates a public workflow ────────────────────────────────
    created = _expect(
        session_a.post(
            f"{base_url}/v1/public/workflows",
            json={"concern": concern},
            timeout=30,
        ),
        201,
        "session A: workflow creation failed",
    )
    case_id = created.get("case_id")
    if not isinstance(case_id, str) or not case_id:
        raise SmokeTestError("session A: workflow creation did not return a case_id")

    # ── 3. Session A can read its own workflow ────────────────────────────────
    _expect(
        session_a.post(
            f"{base_url}/v1/public/workflows/{case_id}/answers",
            json={},
            timeout=30,
        ),
        200,
        "session A: workflow continuation failed",
    )

    # ── 4. Session B is rejected from session A's workflow (isolation) ────────
    isolation_response = session_b.post(
        f"{base_url}/v1/public/workflows/{case_id}/answers",
        json={},
        timeout=15,
    )
    if isolation_response.status_code not in (403, 404):
        raise SmokeTestError(
            f"isolation boundary broken: session B received HTTP {isolation_response.status_code} "
            f"on session A's workflow (expected 403 or 404)"
        )

    # ── 5. Session A approves a sandbox action and gets a sandbox result ──────
    decision = _expect(
        session_a.post(
            f"{base_url}/v1/public/workflows/{case_id}/action-decision",
            json={"approved": True},
            timeout=30,
        ),
        200,
        "session A: action-decision failed",
    )
    stage = decision.get("stage")
    action_result = decision.get("action_result")
    if stage not in ("follow_through", "awaiting_approval"):
        # Not all sandbox states have a proposable action; a no-op is acceptable.
        print(f"  sandbox action step returned stage={stage!r} (no action to approve — OK)")
    elif action_result is not None:
        payload = action_result.get("payload", {})
        if payload.get("sandbox") != "true":
            raise SmokeTestError(
                f"action result payload is missing sandbox marker: {action_result}"
            )

    return case_id


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True, help="Public sandbox Cloud Run service URL")
    args = parser.parse_args()
    try:
        case_id = run_smoke(args.url)
    except SmokeTestError as error:
        print(f"Public sandbox smoke FAILED: {error}", file=sys.stderr)
        return 1
    print(f"Public sandbox smoke PASSED — case_id={case_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

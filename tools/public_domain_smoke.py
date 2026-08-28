"""Verify the branded public-domain journey without using private APIs.

Usage:
    python tools/public_domain_smoke.py --url https://staylonghome.com
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from urllib.parse import urlparse

import requests


class SmokeTestError(RuntimeError):
    """Raised when the public-domain journey violates its contract."""


def _expect(response: requests.Response, status: int, message: str) -> dict[str, object]:
    if response.status_code != status:
        raise SmokeTestError(
            f"{message}: expected HTTP {status}, received {response.status_code} — "
            f"{response.text[:200]}"
        )
    try:
        payload = response.json()
    except ValueError as error:
        raise SmokeTestError(f"{message}: expected a JSON response") from error
    if not isinstance(payload, dict):
        raise SmokeTestError(f"{message}: expected a JSON object")
    return payload


def _first_javascript_asset(html: str) -> str:
    match = re.search(r'<script[^>]+src=["\']([^"\']+\.js[^"\']*)["\']', html, re.I)
    if not match:
        raise SmokeTestError("root document did not reference a JavaScript asset")
    return match.group(1)


def run_smoke(base_url: str, *, require_https: bool = True) -> str:
    """Exercise the canonical public-domain landing page and workflow creation."""
    base_url = base_url.rstrip("/")
    parsed = urlparse(base_url)
    if require_https and parsed.scheme != "https":
        raise SmokeTestError("public-domain smoke requires an HTTPS URL")
    if not parsed.hostname:
        raise SmokeTestError("public-domain smoke requires an absolute canonical URL")

    session = requests.Session()
    root = session.get(base_url, timeout=20, allow_redirects=False)
    if root.is_redirect:
        location = root.headers.get("Location", "<missing>")
        raise SmokeTestError(
            f"root document redirected away from canonical URL {base_url} to {location}"
        )
    resolved = urlparse(root.url)
    if resolved.hostname != parsed.hostname:
        raise SmokeTestError(
            "root document redirected away from canonical host "
            f"{parsed.hostname} to {resolved.hostname}"
        )
    if root.status_code != 200:
        raise SmokeTestError(
            f"root document failed: expected HTTP 200, received {root.status_code}"
        )

    asset = _first_javascript_asset(root.text)
    asset_response = session.get(requests.compat.urljoin(f"{base_url}/", asset), timeout=20)
    if asset_response.status_code != 200:
        raise SmokeTestError(
            f"JavaScript asset failed: expected HTTP 200, received {asset_response.status_code}"
        )
    if "/v1/public" not in asset_response.text:
        raise SmokeTestError("JavaScript asset does not reference the public API namespace")

    created = _expect(
        session.post(
            f"{base_url}/v1/public/workflows",
            json={
                "concern": "Preparing a temporary demonstration plan for safer movement at home."
            },
            timeout=30,
        ),
        201,
        "public workflow creation failed",
    )
    case_id = created.get("case_id")
    if not isinstance(case_id, str) or not case_id:
        raise SmokeTestError("public workflow creation did not return a case_id")
    if not session.cookies:
        raise SmokeTestError("public workflow creation did not establish a session cookie")
    return case_id


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True, help="Canonical public HTTPS URL")
    args = parser.parse_args()
    try:
        case_id = run_smoke(args.url)
    except SmokeTestError as error:
        print(f"Public domain smoke FAILED: {error}", file=sys.stderr)
        return 1
    print(json.dumps({"url": args.url, "case_id": case_id, "result": "passed"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

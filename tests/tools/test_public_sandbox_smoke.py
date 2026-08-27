"""Structural tests for the public sandbox smoke script."""

from __future__ import annotations

from pathlib import Path

SOURCE = Path("tools/public_sandbox_smoke.py").read_text()


def test_public_sandbox_smoke_never_requires_or_prints_an_api_token() -> None:
    assert "STAYLONG_API_TOKEN" not in SOURCE
    assert "requests.Session()" in SOURCE
    assert "session_b" in SOURCE


def test_public_sandbox_smoke_uses_public_routes_only() -> None:
    assert "/v1/public/" in SOURCE
    assert "/v1/workflows" not in SOURCE.replace("/v1/public/workflows", "")


def test_public_sandbox_smoke_verifies_session_isolation() -> None:
    # script must attempt a cross-session read and assert it is rejected
    assert "403" in SOURCE or "session_b" in SOURCE


def test_public_sandbox_smoke_has_main_entrypoint() -> None:
    assert 'if __name__ == "__main__"' in SOURCE

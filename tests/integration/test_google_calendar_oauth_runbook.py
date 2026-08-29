from pathlib import Path

RUNBOOK = Path("docs/google-calendar-oauth-runbook.md")


def test_google_calendar_runbook_preserves_private_oauth_boundary() -> None:
    text = RUNBOOK.read_text(encoding="utf-8")

    for required in (
        "STAYLONG_GOOGLE_OAUTH_CLIENT_ID",
        "STAYLONG_GOOGLE_OAUTH_REDIRECT_URI",
        "STAYLONG_GOOGLE_OAUTH_CLIENT_SECRET_ID",
        "/v1/integrations/google/calendar/start",
        "/v1/workflows/{case_id}/action-decision",
        "calendar.events",
        "public sandbox",
        "does not sign into Google",
    ):
        assert required in text

    assert "access token or refresh token" in text
    assert "exactly one event" in text

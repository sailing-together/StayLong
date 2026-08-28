from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from staylong.api.app import create_app


class FakeCalendarOAuth:
    def __init__(self) -> None:
        self.started_for: str | None = None
        self.callback_args: tuple[str, str] | None = None

    def authorization_url(self, *, session_id: str, now: datetime) -> str:
        self.started_for = session_id
        return "https://accounts.google.com/o/oauth2/v2/auth?state=opaque"

    def exchange_callback(self, *, code: str, state: str, now: datetime) -> datetime:
        self.callback_args = (code, state)
        return now + timedelta(hours=1)


def test_calendar_start_requires_private_auth_and_trusted_user_principal() -> None:
    oauth = FakeCalendarOAuth()
    app = create_app(api_token="app-token", calendar_oauth=oauth)
    client = TestClient(app)

    response = client.get(
        "/v1/integrations/google/calendar/start",
        headers={
            "Authorization": "Bearer app-token",
            "X-Goog-Authenticated-User-Email": "accounts.google.com:user@example.com",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth?state=opaque"
    }
    assert oauth.started_for == "user@example.com"


def test_calendar_start_rejects_missing_trusted_principal() -> None:
    app = create_app(api_token="app-token", calendar_oauth=FakeCalendarOAuth())

    response = TestClient(app).get(
        "/v1/integrations/google/calendar/start",
        headers={"Authorization": "Bearer app-token"},
    )

    assert response.status_code == 401


def test_calendar_callback_returns_connection_status_without_credentials() -> None:
    oauth = FakeCalendarOAuth()
    app = create_app(api_token="app-token", calendar_oauth=oauth)
    now = datetime.now(UTC)

    response = TestClient(app).get(
        "/v1/integrations/google/calendar/callback",
        params={"code": "one-time-code", "state": "opaque"},
    )

    assert response.status_code == 200
    assert response.json()["connected"] is True
    assert "access_token" not in response.text
    assert oauth.callback_args == ("one-time-code", "opaque")
    assert datetime.fromisoformat(response.json()["expires_at"]) > now


def test_calendar_routes_are_unavailable_when_oauth_is_not_configured() -> None:
    app = create_app(api_token="app-token")

    response = TestClient(app).get(
        "/v1/integrations/google/calendar/start",
        headers={"Authorization": "Bearer app-token"},
    )

    assert response.status_code == 503

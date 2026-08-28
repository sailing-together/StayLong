from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlparse

import pytest
from google.api_core.exceptions import NotFound

from staylong.services.google_oauth import (
    GoogleCalendarOAuth,
    InMemoryOAuthStateStore,
    InMemoryOAuthTokenStore,
    OAuthError,
    OAuthTokenResponse,
    SecretManagerOAuthTokenStore,
)

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def test_authorization_url_binds_state_to_session_and_least_privilege_scope() -> None:
    oauth = GoogleCalendarOAuth(
        client_id="client-id",
        client_secret="client-secret",
        redirect_uri="https://staylong.example.com/oauth/callback",
        state_store=InMemoryOAuthStateStore(),
        token_store=InMemoryOAuthTokenStore(),
    )

    url = oauth.authorization_url(session_id="session-a", now=NOW)
    query = parse_qs(urlparse(url).query)

    assert query["client_id"] == ["client-id"]
    assert query["redirect_uri"] == ["https://staylong.example.com/oauth/callback"]
    assert query["scope"] == ["https://www.googleapis.com/auth/calendar.events"]
    assert query["access_type"] == ["offline"]
    assert query["state"][0]


def test_exchange_rejects_state_replay_or_wrong_session_before_network_call() -> None:
    state_store = InMemoryOAuthStateStore()
    oauth = GoogleCalendarOAuth(
        client_id="client-id",
        client_secret="client-secret",
        redirect_uri="https://staylong.example.com/oauth/callback",
        state_store=state_store,
        token_store=InMemoryOAuthTokenStore(),
    )
    state = parse_qs(urlparse(oauth.authorization_url(session_id="session-a", now=NOW)).query)[
        "state"
    ][0]

    with pytest.raises(OAuthError, match="session"):
        oauth.exchange_code(
            code="authorization-code",
            state=state,
            session_id="session-b",
            now=NOW,
            token_exchange=lambda _: OAuthTokenResponse(
                access_token="access", refresh_token="refresh", expires_in=3600
            ),
        )

    oauth.exchange_code(
        code="authorization-code",
        state=state,
        session_id="session-a",
        now=NOW,
        token_exchange=lambda _: OAuthTokenResponse(
            access_token="access", refresh_token="refresh", expires_in=3600
        ),
    )
    with pytest.raises(OAuthError, match="replayed"):
        oauth.exchange_code(
            code="authorization-code",
            state=state,
            session_id="session-a",
            now=NOW,
            token_exchange=lambda _: OAuthTokenResponse(
                access_token="access", refresh_token="refresh", expires_in=3600
            ),
        )


def test_expired_state_is_rejected_and_token_store_keeps_only_authorised_refresh_token() -> None:
    token_store = InMemoryOAuthTokenStore()
    oauth = GoogleCalendarOAuth(
        client_id="client-id",
        client_secret="client-secret",
        redirect_uri="https://staylong.example.com/oauth/callback",
        state_store=InMemoryOAuthStateStore(),
        token_store=token_store,
        state_lifetime=timedelta(minutes=5),
    )
    state = parse_qs(urlparse(oauth.authorization_url(session_id="session-a", now=NOW)).query)[
        "state"
    ][0]

    with pytest.raises(OAuthError, match="expired"):
        oauth.exchange_code(
            code="authorization-code",
            state=state,
            session_id="session-a",
            now=NOW + timedelta(minutes=6),
            token_exchange=lambda _: OAuthTokenResponse(
                access_token="access", refresh_token="refresh", expires_in=3600
            ),
        )

    state = parse_qs(urlparse(oauth.authorization_url(session_id="session-a", now=NOW)).query)[
        "state"
    ][0]
    expires_at = oauth.exchange_code(
        code="authorization-code",
        state=state,
        session_id="session-a",
        now=NOW,
        token_exchange=lambda _: OAuthTokenResponse(
            access_token="access", refresh_token="refresh", expires_in=3600
        ),
    )
    assert expires_at == NOW + timedelta(seconds=3600)
    assert token_store.get_refresh_token("session-a") == "refresh"


class _FakeSecret:
    def __init__(self) -> None:
        self.versions: list[str] = []


class _FakeSecretManager:
    def __init__(self) -> None:
        self.secrets: dict[str, _FakeSecret] = {}

    def secret_path(self, project_id: str, secret_id: str) -> str:
        return f"projects/{project_id}/secrets/{secret_id}"

    def secret_version_path(self, project_id: str, secret_id: str, version: str) -> str:
        return f"projects/{project_id}/secrets/{secret_id}/versions/{version}"

    def get_secret(self, *, name: str) -> object:
        if name not in self.secrets:
            raise NotFound("missing")
        return object()

    def create_secret(self, *, request: object) -> None:
        name = request.parent + "/secrets/" + request.secret_id
        self.secrets[name] = _FakeSecret()

    def add_secret_version(self, *, request: object) -> object:
        self.secrets[request.parent].versions.append(request.payload.data.decode())
        return object()

    def access_secret_version(self, *, request: object) -> object:
        name = request.name.rsplit("/versions/", 1)[0]
        return type("Response", (), {"payload": type("Payload", (), {
            "data": self.secrets[name].versions[-1].encode()
        })()})()


def test_secret_manager_store_hashes_session_and_round_trips_refresh_token() -> None:
    client = _FakeSecretManager()
    store = SecretManagerOAuthTokenStore(client=client, project_id="staylong-prod")

    store.save_refresh_token("session-a", "refresh-token")

    assert store.get_refresh_token("session-a") == "refresh-token"
    assert list(client.secrets) == [next(iter(client.secrets))]
    assert "session-a" not in next(iter(client.secrets))

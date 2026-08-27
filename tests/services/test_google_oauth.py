from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlparse

import pytest

from staylong.services.google_oauth import (
    GoogleCalendarOAuth,
    InMemoryOAuthStateStore,
    InMemoryOAuthTokenStore,
    OAuthError,
    OAuthTokenResponse,
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

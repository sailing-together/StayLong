"""Small, approval-independent Google Calendar OAuth boundary.

This module handles consent state and refresh-token ownership only. It does not
make a Calendar API call or expose credential material to workflow state. The
public sandbox never constructs this service.
"""

from __future__ import annotations

import hashlib
import json
import secrets
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class OAuthError(ValueError):
    """A safe, user-facing OAuth flow failure."""


@dataclass(frozen=True, slots=True)
class OAuthTokenResponse:
    """Validated subset of Google's token response."""

    access_token: str
    refresh_token: str
    expires_in: int


@dataclass(frozen=True, slots=True)
class OAuthAccessTokenResponse:
    """Short-lived access token returned when refreshing a stored grant."""

    access_token: str
    expires_in: int


@dataclass(frozen=True, slots=True)
class _PendingState:
    session_id: str
    expires_at: datetime


class OAuthStateStore(Protocol):
    def put(self, state: str, *, session_id: str, expires_at: datetime) -> None: ...

    def peek(self, state: str) -> _PendingState | None: ...

    def consume(self, state: str, *, now: datetime) -> _PendingState | None: ...


class OAuthTokenStore(Protocol):
    def save_refresh_token(self, session_id: str, refresh_token: str) -> None: ...

    def get_refresh_token(self, session_id: str) -> str | None: ...


class InMemoryOAuthStateStore:
    """Test-only state store; production must use a durable, expiring store."""

    def __init__(self) -> None:
        self._states: dict[str, _PendingState] = {}

    def put(self, state: str, *, session_id: str, expires_at: datetime) -> None:
        self._states[state] = _PendingState(session_id=session_id, expires_at=expires_at)

    def peek(self, state: str) -> _PendingState | None:
        return self._states.get(state)

    def consume(self, state: str, *, now: datetime) -> _PendingState | None:
        pending = self._states.pop(state, None)
        if pending is None or pending.expires_at <= now:
            return None
        return pending


class InMemoryOAuthTokenStore:
    """Test-only token store; tokens are never part of workflow snapshots."""

    def __init__(self) -> None:
        self._refresh_tokens: dict[str, str] = {}

    def save_refresh_token(self, session_id: str, refresh_token: str) -> None:
        self._refresh_tokens[session_id] = refresh_token

    def get_refresh_token(self, session_id: str) -> str | None:
        return self._refresh_tokens.get(session_id)


class SecretManagerOAuthTokenStore:
    """Persist refresh tokens in Secret Manager under hashed session keys."""

    def __init__(self, *, client: object | None = None, project_id: str) -> None:
        if not project_id:
            raise ValueError("project_id is required for Secret Manager token storage.")
        if client is None:
            from google.cloud import secretmanager

            client = secretmanager.SecretManagerServiceClient()
        self._client = client
        self._project_id = project_id

    def save_refresh_token(self, session_id: str, refresh_token: str) -> None:
        if not session_id or not refresh_token:
            raise ValueError("session_id and refresh_token are required.")
        secret_id = self._secret_id(session_id)
        parent = self._client.secret_path(self._project_id, secret_id)
        try:
            self._client.get_secret(name=parent)
        except Exception as error:
            from google.api_core.exceptions import NotFound

            if not isinstance(error, NotFound):
                raise
            from google.cloud import secretmanager

            self._client.create_secret(
                request=secretmanager.CreateSecretRequest(
                    parent=f"projects/{self._project_id}",
                    secret_id=secret_id,
                    secret=secretmanager.Secret(replication=secretmanager.Replication(automatic={})),
                )
            )
        from google.cloud import secretmanager

        self._client.add_secret_version(
            request=secretmanager.AddSecretVersionRequest(
                parent=parent,
                payload=secretmanager.SecretPayload(data=refresh_token.encode()),
            )
        )

    def get_refresh_token(self, session_id: str) -> str | None:
        if not session_id:
            return None
        secret_id = self._secret_id(session_id)
        version = self._client.secret_version_path(self._project_id, secret_id, "latest")
        try:
            response = self._client.access_secret_version(
                request=self._request_for_access(version)
            )
        except Exception:
            return None
        value = response.payload.data.decode()
        return value or None

    @staticmethod
    def _secret_id(session_id: str) -> str:
        digest = hashlib.sha256(session_id.encode()).hexdigest()
        return f"staylong-calendar-{digest[:40]}"

    @staticmethod
    def _request_for_access(name: str) -> object:
        from google.cloud import secretmanager

        return secretmanager.AccessSecretVersionRequest(name=name)


class GoogleCalendarOAuth:
    """Create Google consent URLs and exchange one-time authorization codes."""

    authorization_endpoint = "https://accounts.google.com/o/oauth2/v2/auth"
    token_endpoint = "https://oauth2.googleapis.com/token"
    calendar_scope = "https://www.googleapis.com/auth/calendar.events"

    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        state_store: OAuthStateStore,
        token_store: OAuthTokenStore,
        state_lifetime: timedelta = timedelta(minutes=10),
    ) -> None:
        if not client_id or not client_secret or not redirect_uri:
            raise ValueError("Google OAuth client configuration is incomplete.")
        if state_lifetime <= timedelta(0):
            raise ValueError("OAuth state lifetime must be positive.")
        self._client_id = client_id
        self._client_secret = client_secret
        self._redirect_uri = redirect_uri
        self._state_store = state_store
        self._token_store = token_store
        self._state_lifetime = state_lifetime

    def authorization_url(self, *, session_id: str, now: datetime) -> str:
        if not session_id:
            raise ValueError("session_id is required.")
        state = secrets.token_urlsafe(32)
        self._state_store.put(
            state,
            session_id=session_id,
            expires_at=now + self._state_lifetime,
        )
        return f"{self.authorization_endpoint}?{urlencode({
            'client_id': self._client_id,
            'redirect_uri': self._redirect_uri,
            'response_type': 'code',
            'scope': self.calendar_scope,
            'access_type': 'offline',
            'prompt': 'consent',
            'state': state,
        })}"

    def exchange_code(
        self,
        *,
        code: str,
        state: str,
        session_id: str,
        now: datetime,
        token_exchange: Callable[[str], OAuthTokenResponse] | None = None,
    ) -> datetime:
        if not code or not state or not session_id:
            raise OAuthError("The Google authorization response is incomplete.")
        pending = self._state_store.peek(state)
        if pending is None:
            raise OAuthError("The Google authorization state is expired or replayed.")
        if not secrets.compare_digest(pending.session_id, session_id):
            raise OAuthError("The Google authorization state belongs to another session.")
        pending = self._state_store.consume(state, now=now)
        if pending is None:
            raise OAuthError("The Google authorization state is expired or replayed.")
        exchange = token_exchange or self._exchange_code
        try:
            token = exchange(code)
        except OAuthError:
            raise
        except Exception as error:
            raise OAuthError("Google authorization could not be completed.") from error
        if not token.access_token or not token.refresh_token or token.expires_in <= 0:
            raise OAuthError("Google returned an invalid authorization token.")
        self._token_store.save_refresh_token(session_id, token.refresh_token)
        return now + timedelta(seconds=token.expires_in)

    def exchange_callback(
        self,
        *,
        code: str,
        state: str,
        now: datetime,
        token_exchange: Callable[[str], OAuthTokenResponse] | None = None,
    ) -> datetime:
        """Exchange a browser callback using the session bound to its state."""
        pending = self._state_store.peek(state)
        if pending is None:
            raise OAuthError("The Google authorization state is expired or replayed.")
        return self.exchange_code(
            code=code,
            state=state,
            session_id=pending.session_id,
            now=now,
            token_exchange=token_exchange,
        )

    def refresh_access_token(
        self,
        *,
        session_id: str,
        now: datetime,
        token_refresh: Callable[[str], OAuthAccessTokenResponse] | None = None,
    ) -> tuple[str, datetime]:
        """Refresh a short-lived access token without exposing the refresh token."""
        refresh_token = self._token_store.get_refresh_token(session_id)
        if not refresh_token:
            raise OAuthError("Google Calendar is not connected for this user.")
        refresh = token_refresh or self._refresh_access_token
        try:
            token = refresh(refresh_token)
        except OAuthError:
            raise
        except Exception as error:
            raise OAuthError("Google Calendar authorization could not be refreshed.") from error
        if not token.access_token or token.expires_in <= 0:
            raise OAuthError("Google returned an invalid refreshed access token.")
        return token.access_token, now + timedelta(seconds=token.expires_in)

    def _exchange_code(self, code: str) -> OAuthTokenResponse:
        payload = urlencode({
            "code": code,
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "redirect_uri": self._redirect_uri,
            "grant_type": "authorization_code",
        }).encode()
        request = Request(
            self.token_endpoint,
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=10) as response:  # noqa: S310 - fixed Google endpoint
                data = json.loads(response.read().decode())
        except Exception as error:
            raise OAuthError("Google authorization could not be completed.") from error
        if not isinstance(data, dict):
            raise OAuthError("Google returned an invalid authorization response.")
        try:
            return OAuthTokenResponse(
                access_token=str(data["access_token"]),
                refresh_token=str(data["refresh_token"]),
                expires_in=int(data["expires_in"]),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise OAuthError("Google returned an invalid authorization token.") from error

    def _refresh_access_token(self, refresh_token: str) -> OAuthAccessTokenResponse:
        payload = urlencode({
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }).encode()
        request = Request(
            self.token_endpoint,
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=10) as response:  # noqa: S310 - fixed Google endpoint
                data = json.loads(response.read().decode())
        except Exception as error:
            raise OAuthError("Google Calendar authorization could not be refreshed.") from error
        if not isinstance(data, dict):
            raise OAuthError("Google returned an invalid refreshed token response.")
        try:
            return OAuthAccessTokenResponse(
                access_token=str(data["access_token"]),
                expires_in=int(data["expires_in"]),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise OAuthError("Google returned an invalid refreshed token response.") from error

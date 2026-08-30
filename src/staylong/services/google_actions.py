"""Opt-in Google Calendar and Gmail-draft actions behind StayLong approvals.

Tokens are injected at runtime from a secret store. They are deliberately not
persisted, returned by the API, or written to application logs.
"""

from __future__ import annotations

import base64
import json
from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import datetime
from email.message import EmailMessage
from typing import Protocol
from urllib.request import Request, urlopen

from staylong.domain.models import ActionApproval
from staylong.policy.approvals import execute_approved_tool_action
from staylong.services.channels import (
    CalendarDemoAdapter,
    CalendarDetails,
    ContactDraftDemoAdapter,
    DemoDispatchResult,
    MessageDetails,
)


@dataclass(frozen=True, slots=True)
class GoogleActionConfig:
    """The minimum secret-injected configuration for authorised Google actions."""

    access_token: str
    calendar_id: str

    @classmethod
    def from_environment(
        cls,
        values: Mapping[str, str],
        *,
        allow_refreshed_access_token: bool = False,
    ) -> GoogleActionConfig | None:
        """Return no configuration unless every required OAuth value is present.

        An explicit OAuth mode with incomplete configuration is an error: it must
        never look like an authorised Google connection while silently using demo
        records.
        """
        mode = values.get("STAYLONG_GOOGLE_ACTIONS_MODE", "").strip().casefold()
        if not mode:
            return None
        if mode == "sandbox":
            return None
        if mode != "oauth":
            raise ValueError("STAYLONG_GOOGLE_ACTIONS_MODE must be 'oauth' when configured.")
        access_token = values.get("STAYLONG_GOOGLE_OAUTH_ACCESS_TOKEN", "").strip()
        calendar_id = values.get("STAYLONG_GOOGLE_CALENDAR_ID", "primary").strip() or "primary"
        if not access_token and not allow_refreshed_access_token:
            raise ValueError(
                "OAuth mode requires STAYLONG_GOOGLE_OAUTH_ACCESS_TOKEN unless a "
                "user-authorised refresh-token provider is configured."
            )
        return cls(access_token=access_token, calendar_id=calendar_id)


class GoogleActionGateway(Protocol):
    """Narrow network boundary, intentionally easy to fake in tests."""

    def create_calendar_event(
        self, *, config: GoogleActionConfig, details: CalendarDetails
    ) -> str: ...

    def create_gmail_draft(self, *, config: GoogleActionConfig, details: MessageDetails) -> str: ...


class GoogleAccessTokenProvider(Protocol):
    """Provide a fresh access token for one already-authorised user session."""

    def get_access_token(self, *, session_id: str, now: datetime) -> str: ...


class GoogleOAuthAccessTokenProvider:
    """Adapt the OAuth service refresh boundary to Calendar actions."""

    def __init__(self, oauth: object) -> None:
        self._oauth = oauth

    def get_access_token(self, *, session_id: str, now: datetime) -> str:
        access_token, _ = self._oauth.refresh_access_token(session_id=session_id, now=now)
        return access_token


class GoogleRestGateway:
    """Small REST client for an already user-authorised Google OAuth token."""

    def create_calendar_event(
        self, *, config: GoogleActionConfig, details: CalendarDetails
    ) -> str:
        calendar_id = _url_quote(config.calendar_id)
        response = self._post_json(
            url=(
                "https://www.googleapis.com/calendar/v3/calendars/"
                f"{calendar_id}/events"
            ),
            access_token=config.access_token,
            payload={
                "summary": details.title,
                "start": {"dateTime": details.starts_at},
                "end": {"dateTime": details.ends_at},
            },
        )
        return str(response["id"])

    def create_gmail_draft(self, *, config: GoogleActionConfig, details: MessageDetails) -> str:
        message = EmailMessage()
        message["To"] = details.recipient
        message["Subject"] = details.subject
        message.set_content(details.body)
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode().rstrip("=")
        response = self._post_json(
            url="https://gmail.googleapis.com/gmail/v1/users/me/drafts",
            access_token=config.access_token,
            payload={"message": {"raw": raw}},
        )
        return str(response["id"])

    @staticmethod
    def _post_json(
        *, url: str, access_token: str, payload: Mapping[str, object]
    ) -> Mapping[str, object]:
        request = Request(
            url,
            data=json.dumps(payload).encode(),
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urlopen(request, timeout=10) as response:  # noqa: S310 - fixed Google API URLs above
            decoded = json.loads(response.read().decode())
        if not isinstance(decoded, dict) or not isinstance(decoded.get("id"), str):
            raise ValueError("Google API response did not contain an action ID.")
        return decoded


class GoogleCalendarAdapter(CalendarDemoAdapter):
    """Create an authorised Google Calendar event only after exact approval."""

    integration_mode = "google_oauth"

    def __init__(
        self,
        config: GoogleActionConfig,
        *,
        gateway: GoogleActionGateway | None = None,
        access_token_provider: GoogleAccessTokenProvider | None = None,
    ) -> None:
        super().__init__()
        self._config = config
        self._gateway = gateway or GoogleRestGateway()
        self._access_token_provider = access_token_provider

    def create_event(
        self,
        *,
        case_id: str,
        revision: int,
        approval: ActionApproval | None,
        now: datetime,
        details: CalendarDetails,
        session_id: str | None = None,
    ) -> DemoDispatchResult:
        def create() -> DemoDispatchResult:
            config = self._config
            if self._access_token_provider is not None:
                if not session_id:
                    raise ValueError("A user session is required for Google Calendar actions.")
                config = replace(
                    config,
                    access_token=self._access_token_provider.get_access_token(
                        session_id=session_id, now=now
                    ),
                )
            event_id = self._gateway.create_calendar_event(config=config, details=details)
            result = DemoDispatchResult(
                case_id=case_id,
                action_type=self.action_type,
                action_revision=revision,
                channel="google_calendar",
                payload={"event_id": event_id, "integration_mode": self.integration_mode},
            )
            self._items.append(result)
            return result

        return execute_approved_tool_action(
            case_id=case_id,
            action_type=self.action_type,
            action_revision=revision,
            approval=approval,
            now=now,
            action=create,
        )


class GoogleGmailDraftAdapter(ContactDraftDemoAdapter):
    """Create an unsent Gmail draft; StayLong never sends this message."""

    integration_mode = "google_oauth"

    def __init__(
        self, config: GoogleActionConfig, *, gateway: GoogleActionGateway | None = None
    ) -> None:
        super().__init__()
        self._config = config
        self._gateway = gateway or GoogleRestGateway()

    def create_draft(
        self,
        *,
        case_id: str,
        revision: int,
        approval: ActionApproval | None,
        now: datetime,
        details: MessageDetails,
    ) -> DemoDispatchResult:
        def create() -> DemoDispatchResult:
            draft_id = self._gateway.create_gmail_draft(config=self._config, details=details)
            result = DemoDispatchResult(
                case_id=case_id,
                action_type=self.action_type,
                action_revision=revision,
                channel="gmail_draft",
                payload={
                    "draft_id": draft_id,
                    "delivery": "draft_only",
                    "integration_mode": self.integration_mode,
                },
            )
            self._items.append(result)
            return result

        return execute_approved_tool_action(
            case_id=case_id,
            action_type=self.action_type,
            action_revision=revision,
            approval=approval,
            now=now,
            action=create,
        )


@dataclass(frozen=True, slots=True)
class ActionAdapters:
    """Action adapters and their explicit integration state for a workflow."""

    calendar: CalendarDemoAdapter
    contact_drafts: ContactDraftDemoAdapter
    integration_mode: str


def build_action_adapters(
    values: Mapping[str, str],
    *,
    access_token_provider: GoogleAccessTokenProvider | None = None,
) -> ActionAdapters:
    """Build OAuth adapters only when fully configured; otherwise use sandbox."""
    config = GoogleActionConfig.from_environment(
        values,
        allow_refreshed_access_token=access_token_provider is not None,
    )
    if config is None:
        return ActionAdapters(
            calendar=CalendarDemoAdapter(),
            contact_drafts=ContactDraftDemoAdapter(),
            integration_mode="sandbox",
        )
    return ActionAdapters(
        calendar=GoogleCalendarAdapter(config, access_token_provider=access_token_provider),
        contact_drafts=ContactDraftDemoAdapter(),
        integration_mode="google_oauth",
    )


def _url_quote(value: str) -> str:
    from urllib.parse import quote

    return quote(value, safe="")

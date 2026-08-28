"""Tests for opt-in Google action adapters and their safe sandbox fallback."""

from datetime import UTC, datetime, timedelta

import pytest

from staylong.domain.models import ActionApproval
from staylong.policy.approvals import ApprovalRequiredError
from staylong.services.channels import CalendarDetails, MessageDetails

NOW = datetime(2026, 8, 24, 9, 0, tzinfo=UTC)


def test_missing_google_oauth_configuration_selects_sandbox_adapters() -> None:
    from staylong.services.google_actions import build_action_adapters

    adapters = build_action_adapters({})

    assert adapters.integration_mode == "sandbox"
    assert adapters.calendar.integration_mode == "sandbox"
    assert adapters.contact_drafts.integration_mode == "sandbox"


def test_complete_google_configuration_selects_authorised_google_adapters() -> None:
    from staylong.services.google_actions import build_action_adapters

    adapters = build_action_adapters(
        {
            "STAYLONG_GOOGLE_ACTIONS_MODE": "oauth",
            "STAYLONG_GOOGLE_OAUTH_ACCESS_TOKEN": "test-token",
            "STAYLONG_GOOGLE_CALENDAR_ID": "primary",
        }
    )

    assert adapters.integration_mode == "google_oauth"
    assert adapters.calendar.integration_mode == "google_oauth"
    assert adapters.contact_drafts.integration_mode == "google_oauth"


def test_google_calendar_requires_exact_approval_before_calling_gateway() -> None:
    from staylong.services.google_actions import GoogleActionConfig, GoogleCalendarAdapter

    gateway = RecordingGateway()
    adapter = GoogleCalendarAdapter(
        GoogleActionConfig(access_token="test-token", calendar_id="primary"), gateway=gateway
    )

    with pytest.raises(ApprovalRequiredError):
        adapter.create_event(
            case_id="case-1",
            revision=1,
            approval=None,
            now=NOW,
            details=CalendarDetails(
                title="Prepare for assessment",
                starts_at="2026-08-25T09:00:00Z",
                ends_at="2026-08-25T09:30:00Z",
            ),
        )

    assert gateway.calls == []


def test_google_calendar_oauth_adapter_refreshes_for_approved_user_only() -> None:
    from staylong.services.google_actions import GoogleActionConfig, GoogleCalendarAdapter

    gateway = RecordingGateway()
    provider = RecordingTokenProvider()
    adapter = GoogleCalendarAdapter(
        GoogleActionConfig(access_token="unused", calendar_id="primary"),
        gateway=gateway,
        access_token_provider=provider,
    )
    approval = ActionApproval(
        case_id="case-1",
        action_type="calendar.create",
        action_revision=1,
        approved_by_contact_id="older-person",
        expires_at=NOW + timedelta(minutes=5),
    )

    result = adapter.create_event(
        case_id="case-1",
        revision=1,
        approval=approval,
        now=NOW,
        session_id="user@example.com",
        details=CalendarDetails(
            title="Prepare for assessment",
            starts_at="2026-08-25T09:00:00Z",
            ends_at="2026-08-25T09:30:00Z",
        ),
    )

    assert result.payload["event_id"] == "calendar-event-1"
    assert provider.calls == [("user@example.com", NOW)]
    assert gateway.tokens == ["fresh-access-token"]


def test_google_calendar_oauth_adapter_rejects_approved_action_without_user() -> None:
    from staylong.services.google_actions import GoogleActionConfig, GoogleCalendarAdapter

    provider = RecordingTokenProvider()
    adapter = GoogleCalendarAdapter(
        GoogleActionConfig(access_token="unused", calendar_id="primary"),
        gateway=RecordingGateway(),
        access_token_provider=provider,
    )
    approval = ActionApproval(
        case_id="case-1",
        action_type="calendar.create",
        action_revision=1,
        approved_by_contact_id="older-person",
        expires_at=NOW + timedelta(minutes=5),
    )

    with pytest.raises(ValueError, match="user session"):
        adapter.create_event(
            case_id="case-1",
            revision=1,
            approval=approval,
            now=NOW,
            details=CalendarDetails(
                title="Prepare for assessment",
                starts_at="2026-08-25T09:00:00Z",
                ends_at="2026-08-25T09:30:00Z",
            ),
        )


def test_google_gmail_adapter_creates_a_draft_and_never_sends_mail() -> None:
    from staylong.services.google_actions import GoogleActionConfig, GoogleGmailDraftAdapter

    gateway = RecordingGateway()
    adapter = GoogleGmailDraftAdapter(
        GoogleActionConfig(access_token="test-token", calendar_id="primary"), gateway=gateway
    )
    approval = ActionApproval(
        case_id="case-1",
        action_type="contact_draft.create",
        action_revision=1,
        approved_by_contact_id="older-person",
        expires_at=NOW + timedelta(minutes=5),
    )

    result = adapter.create_draft(
        case_id="case-1",
        revision=1,
        approval=approval,
        now=NOW,
        details=MessageDetails(
            recipient="provider@example.test",
            subject="Home assessment",
            body="Please call.",
        ),
    )

    assert result.channel == "gmail_draft"
    assert result.payload["delivery"] == "draft_only"
    assert gateway.calls == ["gmail.drafts.create"]


class RecordingGateway:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.tokens: list[str] = []

    def create_calendar_event(self, **_: object) -> str:
        self.calls.append("calendar.events.insert")
        self.tokens.append(str(_["config"].access_token))
        return "calendar-event-1"

    def create_gmail_draft(self, **_: object) -> str:
        self.calls.append("gmail.drafts.create")
        return "gmail-draft-1"


class RecordingTokenProvider:
    def __init__(self) -> None:
        self.calls: list[tuple[str, datetime]] = []

    def get_access_token(self, *, session_id: str, now: datetime) -> str:
        self.calls.append((session_id, now))
        return "fresh-access-token"

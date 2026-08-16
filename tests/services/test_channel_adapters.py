"""Tests for approval-gated demo adapters for all supported outbound channels."""

from datetime import UTC, datetime

import pytest

from staylong.domain.models import ActionApproval

NOW = datetime(2026, 8, 16, 12, tzinfo=UTC)


def _approval(action_type: str) -> ActionApproval:
    return ActionApproval(
        case_id="case-001",
        action_type=action_type,
        action_revision=1,
        approved_by_contact_id="contact-alex",
        expires_at=datetime(2026, 8, 17, tzinfo=UTC),
    )


@pytest.mark.parametrize(
    ("adapter_name", "action_type"),
    [
        ("calendar", "calendar.create"),
        ("email", "message.email.send"),
        ("sms", "message.sms.send"),
    ],
)
def test_every_demo_channel_requires_matching_approval_before_side_effect(
    adapter_name: str, action_type: str
) -> None:
    from staylong.services.channels import (
        CalendarDemoAdapter,
        EmailDemoAdapter,
        SmsDemoAdapter,
    )

    adapter = {
        "calendar": CalendarDemoAdapter(),
        "email": EmailDemoAdapter(),
        "sms": SmsDemoAdapter(),
    }[adapter_name]

    with pytest.raises(PermissionError):
        _dispatch(adapter, approval=None)

    assert adapter.sent_items == ()
    assert action_type in adapter.action_type


@pytest.mark.parametrize(
    ("adapter", "action_type"),
    [
        ("calendar", "calendar.create"),
        ("email", "message.email.send"),
        ("sms", "message.sms.send"),
    ],
)
def test_matching_approval_records_a_demo_action(adapter: str, action_type: str) -> None:
    from staylong.services.channels import (
        CalendarDemoAdapter,
        EmailDemoAdapter,
        SmsDemoAdapter,
    )

    channel = {
        "calendar": CalendarDemoAdapter(),
        "email": EmailDemoAdapter(),
        "sms": SmsDemoAdapter(),
    }[adapter]

    result = _dispatch(channel, approval=_approval(action_type))

    assert result.action_type == action_type
    assert result.case_id == "case-001"
    assert channel.sent_items == (result,)


def test_expired_approval_does_not_send_email() -> None:
    from staylong.services.channels import EmailDemoAdapter

    adapter = EmailDemoAdapter()
    expired = ActionApproval(
        case_id="case-001",
        action_type="message.email.send",
        action_revision=1,
        approved_by_contact_id="contact-alex",
        expires_at=datetime(2026, 8, 16, 11, 59, tzinfo=UTC),
    )

    with pytest.raises(PermissionError):
        _dispatch(adapter, approval=expired)

    assert adapter.sent_items == ()


def _dispatch(adapter: object, approval: ActionApproval | None) -> object:
    from staylong.services.channels import CalendarDetails, MessageDetails

    if adapter.__class__.__name__ == "CalendarDemoAdapter":
        return adapter.create_event(
            case_id="case-001",
            revision=1,
            approval=approval,
            now=NOW,
            details=CalendarDetails(
                title="Aged-care assessment call",
                starts_at="2026-08-18T10:00:00+10:00",
                ends_at="2026-08-18T10:30:00+10:00",
            ),
        )
    return adapter.send(
        case_id="case-001",
        revision=1,
        approval=approval,
        now=NOW,
        details=MessageDetails(
            recipient="authorised@example.test",
            subject="Assessment preparation",
            body="Please review the draft pack.",
        ),
    )

"""Tests for the explicit external-action approval boundary."""

from datetime import UTC, datetime

import pytest

from staylong.domain.models import ActionApproval


def _approval(**overrides: object) -> ActionApproval:
    values: dict[str, object] = {
        "case_id": "case-001",
        "action_type": "calendar.create",
        "action_revision": 1,
        "approved_by_contact_id": "contact-alex",
        "expires_at": datetime(2026, 8, 17, tzinfo=UTC),
    }
    values.update(overrides)
    return ActionApproval(**values)  # type: ignore[arg-type]


def test_matching_approval_allows_the_tool_action() -> None:
    from staylong.policy.approvals import execute_approved_tool_action

    outcome = execute_approved_tool_action(
        case_id="case-001",
        action_type="calendar.create",
        action_revision=1,
        approval=_approval(),
        now=datetime(2026, 8, 16, tzinfo=UTC),
        action=lambda: "calendar-event-123",
    )

    assert outcome == "calendar-event-123"


def test_tool_action_fails_without_an_approval_before_side_effect() -> None:
    from staylong.policy.approvals import ApprovalRequiredError, execute_approved_tool_action

    calls: list[str] = []

    with pytest.raises(ApprovalRequiredError):
        execute_approved_tool_action(
            case_id="case-001",
            action_type="calendar.create",
            action_revision=1,
            approval=None,
            now=datetime(2026, 8, 16, tzinfo=UTC),
            action=lambda: calls.append("called"),
        )

    assert calls == []


@pytest.mark.parametrize(
    ("approval", "now"),
    [
        (_approval(action_type="message.send"), datetime(2026, 8, 16, tzinfo=UTC)),
        (_approval(action_revision=2), datetime(2026, 8, 16, tzinfo=UTC)),
        (_approval(case_id="case-002"), datetime(2026, 8, 16, tzinfo=UTC)),
        (_approval(), datetime(2026, 8, 18, tzinfo=UTC)),
    ],
)
def test_tool_action_fails_when_approval_does_not_match_current_action(
    approval: ActionApproval, now: datetime
) -> None:
    from staylong.policy.approvals import ApprovalRequiredError, execute_approved_tool_action

    calls: list[str] = []

    with pytest.raises(ApprovalRequiredError):
        execute_approved_tool_action(
            case_id="case-001",
            action_type="calendar.create",
            action_revision=1,
            approval=approval,
            now=now,
            action=lambda: calls.append("called"),
        )

    assert calls == []

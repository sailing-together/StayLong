"""Contract tests for approval-bounded coordination output."""

from datetime import UTC, datetime

from staylong.domain.models import ActionApproval


def test_coordinator_returns_a_non_executable_draft_without_approval() -> None:
    from staylong.agents.coordinator import CoordinationAgent, CoordinationRequest

    request = CoordinationRequest(
        case_id="case-001",
        action_type="message.send",
        action_revision=1,
        owner="Alex Chen",
        due_at=datetime(2026, 8, 17, 9, tzinfo=UTC),
        reason="Ask the family to confirm the preferred follow-up time.",
    )

    result = CoordinationAgent().coordinate(
        request=request, approval=None, now=datetime(2026, 8, 16, tzinfo=UTC)
    )

    assert result.status == "draft"
    assert result.may_execute is False
    assert result.action.owner == "Alex Chen"
    assert result.action.due_at == datetime(2026, 8, 17, 9, tzinfo=UTC)
    assert result.action.required_approval == "message.send revision 1"
    assert result.action.reason == "Ask the family to confirm the preferred follow-up time."


def test_coordinator_exposes_only_a_matching_approved_action_for_execution() -> None:
    from staylong.agents.coordinator import CoordinationAgent, CoordinationRequest

    request = CoordinationRequest(
        case_id="case-001",
        action_type="message.send",
        action_revision=1,
        owner="Alex Chen",
        due_at=datetime(2026, 8, 17, 9, tzinfo=UTC),
        reason="Ask the family to confirm the preferred follow-up time.",
    )
    approval = ActionApproval(
        case_id="case-001",
        action_type="message.send",
        action_revision=1,
        approved_by_contact_id="contact-alex",
        expires_at=datetime(2026, 8, 18, tzinfo=UTC),
    )

    result = CoordinationAgent().coordinate(
        request=request, approval=approval, now=datetime(2026, 8, 16, tzinfo=UTC)
    )

    assert result.status == "approved_action"
    assert result.may_execute is True
    assert result.action.required_approval == "message.send revision 1"


def test_coordinator_treats_an_expired_approval_as_a_draft() -> None:
    from staylong.agents.coordinator import CoordinationAgent, CoordinationRequest

    request = CoordinationRequest(
        case_id="case-001",
        action_type="message.send",
        action_revision=1,
        owner="Alex Chen",
        due_at=datetime(2026, 8, 17, 9, tzinfo=UTC),
        reason="Ask the family to confirm the preferred follow-up time.",
    )
    expired_approval = ActionApproval(
        case_id="case-001",
        action_type="message.send",
        action_revision=1,
        approved_by_contact_id="contact-alex",
        expires_at=datetime(2026, 8, 16, tzinfo=UTC),
    )

    result = CoordinationAgent().coordinate(
        request=request, approval=expired_approval, now=datetime(2026, 8, 16, tzinfo=UTC)
    )

    assert result.status == "draft"
    assert result.may_execute is False

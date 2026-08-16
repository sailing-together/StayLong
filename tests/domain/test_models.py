"""Tests for immutable StayLong domain records."""

from datetime import UTC, datetime


def test_authorised_contact_gets_stable_id_and_utc_timestamp() -> None:
    from staylong.domain.models import AuthorisedContact

    contact = AuthorisedContact(name="Alex Chen", relationship="daughter")

    assert contact.contact_id
    assert contact.created_at.tzinfo is UTC
    assert contact.contact_id == contact.contact_id


def test_concern_is_immutable_and_records_its_case() -> None:
    from staylong.domain.models import Concern

    concern = Concern(case_id="case-001", summary="The kitchen light is unreliable.")

    assert concern.case_id == "case-001"
    assert concern.concern_id
    assert concern.created_at.tzinfo is UTC

    try:
        concern.summary = "Changed"  # type: ignore[misc]
    except AttributeError:
        pass
    else:
        raise AssertionError("Concern records must be immutable")


def test_action_approval_captures_a_scoped_expiry_and_approver() -> None:
    from staylong.domain.models import ActionApproval

    expiry = datetime(2026, 8, 17, 9, 30, tzinfo=UTC)
    approval = ActionApproval(
        case_id="case-001",
        action_type="calendar.create",
        action_revision=2,
        approved_by_contact_id="contact-alex",
        expires_at=expiry,
    )

    assert approval.approval_id
    assert approval.case_id == "case-001"
    assert approval.action_type == "calendar.create"
    assert approval.action_revision == 2
    assert approval.approved_by_contact_id == "contact-alex"
    assert approval.expires_at == expiry
    assert approval.created_at.tzinfo is UTC


def test_timeline_event_is_an_immutable_audit_record() -> None:
    from staylong.domain.models import TimelineEvent

    event = TimelineEvent(
        case_id="case-001",
        event_type="approval.granted",
        details={"approval_id": "approval-001"},
    )

    assert event.event_id
    assert event.occurred_at.tzinfo is UTC
    assert event.details == {"approval_id": "approval-001"}

    try:
        event.event_type = "approval.revoked"  # type: ignore[misc]
    except AttributeError:
        pass
    else:
        raise AssertionError("Timeline events must be immutable")

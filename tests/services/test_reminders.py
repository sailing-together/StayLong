"""Tests for scheduled reminders, bounded retries, and authorised escalation."""

from datetime import UTC, datetime, timedelta

import pytest

from staylong.domain.models import ActionApproval

NOW = datetime(2026, 8, 16, 12, tzinfo=UTC)


def _approval(revision: int) -> ActionApproval:
    return ActionApproval(
        case_id="case-001",
        action_type="reminder.escalate",
        action_revision=revision,
        approved_by_contact_id="contact-alex",
        expires_at=NOW + timedelta(hours=1),
    )


def test_due_reminder_is_sent_and_marked_complete() -> None:
    from staylong.services.reminders import ReminderService, ReminderStatus

    service = ReminderService()
    reminder = service.schedule(
        case_id="case-001",
        action="Confirm assessment documents",
        due_at=NOW,
        max_attempts=2,
    )
    sent: list[str] = []

    service.process_due(now=NOW, send=lambda item: sent.append(item.reminder_id))

    assert sent == [reminder.reminder_id]
    assert service.get(reminder.reminder_id).status is ReminderStatus.SENT


def test_failed_send_is_retried_with_backoff_before_escalation() -> None:
    from staylong.services.reminders import ReminderService, ReminderStatus

    service = ReminderService()
    reminder = service.schedule(
        case_id="case-001",
        action="Confirm assessment documents",
        due_at=NOW,
        max_attempts=3,
    )

    service.process_due(now=NOW, send=lambda _: (_ for _ in ()).throw(RuntimeError("offline")))

    retried = service.get(reminder.reminder_id)
    assert retried.status is ReminderStatus.RETRY_SCHEDULED
    assert retried.attempts == 1
    assert retried.next_attempt_at == NOW + timedelta(minutes=2)


def test_escalation_is_blocked_without_approval_after_retry_limit() -> None:
    from staylong.services.reminders import ReminderService, ReminderStatus

    service = ReminderService()
    reminder = service.schedule(
        case_id="case-001",
        action="Confirm assessment documents",
        due_at=NOW,
        max_attempts=1,
    )
    escalated: list[str] = []

    def fail(_: object) -> None:
        raise RuntimeError("offline")

    service.process_due(now=NOW, send=fail, escalate=lambda _: escalated.append("sent"))

    assert service.get(reminder.reminder_id).status is ReminderStatus.ESCALATION_BLOCKED
    assert escalated == []


def test_authorised_escalation_runs_only_after_retry_limit() -> None:
    from staylong.services.reminders import ReminderService, ReminderStatus

    service = ReminderService()
    reminder = service.schedule(
        case_id="case-001",
        action="Confirm assessment documents",
        due_at=NOW,
        max_attempts=1,
    )
    escalated: list[str] = []

    def fail(_: object) -> None:
        raise RuntimeError("offline")

    service.process_due(
        now=NOW,
        send=fail,
        escalate=lambda _: escalated.append("sent"),
        escalation_approval=_approval(revision=1),
    )

    assert service.get(reminder.reminder_id).status is ReminderStatus.ESCALATED
    assert escalated == ["sent"]


def test_non_due_reminder_is_not_processed() -> None:
    from staylong.services.reminders import ReminderService

    service = ReminderService()
    reminder = service.schedule(
        case_id="case-001",
        action="Confirm assessment documents",
        due_at=NOW + timedelta(minutes=1),
    )

    service.process_due(now=NOW, send=lambda _: pytest.fail("not due"))

    assert service.get(reminder.reminder_id).reminder_id == reminder.reminder_id

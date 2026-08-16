"""Integration tests for async reminder execution and send safety."""

import asyncio
from datetime import UTC, datetime, timedelta

from staylong.domain.models import ActionApproval
from staylong.services.channels import EmailDemoAdapter, MessageDetails
from staylong.services.reminders import ReminderService, ReminderStatus

NOW = datetime(2026, 8, 16, 12, tzinfo=UTC)


def _approval() -> ActionApproval:
    return ActionApproval(
        case_id="case-001",
        action_type="message.email.send",
        action_revision=1,
        approved_by_contact_id="contact-alex",
        expires_at=NOW + timedelta(hours=1),
    )


def _send(adapter: EmailDemoAdapter, approval: ActionApproval | None):
    def send(reminder: object) -> object:
        return adapter.send(
            case_id=reminder.case_id,
            revision=reminder.attempts + 1,
            approval=approval,
            now=NOW,
            details=MessageDetails(
                recipient="authorised@example.test",
                subject="StayLong reminder",
                body=reminder.action,
            ),
        )

    return send


def test_async_runner_executes_a_due_approved_send() -> None:
    from staylong.services.async_workflow import AsyncWorkflowRunner

    reminders = ReminderService()
    reminder = reminders.schedule(case_id="case-001", action="Review pack", due_at=NOW)
    adapter = EmailDemoAdapter()

    processed = asyncio.run(
        AsyncWorkflowRunner(reminders=reminders).run_once(
            now=NOW,
            send=_send(adapter, _approval()),
        )
    )

    assert processed[0].reminder_id == reminder.reminder_id
    assert processed[0].status is ReminderStatus.SENT
    assert len(adapter.sent_items) == 1


def test_async_runner_never_sends_without_approval() -> None:
    from staylong.services.async_workflow import AsyncWorkflowRunner

    reminders = ReminderService()
    reminder = reminders.schedule(
        case_id="case-001", action="Review pack", due_at=NOW, max_attempts=2
    )
    adapter = EmailDemoAdapter()

    processed = asyncio.run(
        AsyncWorkflowRunner(reminders=reminders).run_once(
            now=NOW,
            send=_send(adapter, None),
        )
    )

    assert processed[0].reminder_id == reminder.reminder_id
    assert processed[0].status is ReminderStatus.RETRY_SCHEDULED
    assert adapter.sent_items == ()


def test_async_runner_retries_a_transient_failure_on_a_later_cycle() -> None:
    from staylong.services.async_workflow import AsyncWorkflowRunner

    reminders = ReminderService()
    reminders.schedule(case_id="case-001", action="Review pack", due_at=NOW)
    calls = 0

    def send(_: object) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("temporary provider outage")

    runner = AsyncWorkflowRunner(reminders=reminders)
    first = asyncio.run(runner.run_once(now=NOW, send=send))
    second = asyncio.run(
        runner.run_once(now=NOW + timedelta(minutes=2), send=send)
    )

    assert first[0].status is ReminderStatus.RETRY_SCHEDULED
    assert second[0].status is ReminderStatus.SENT
    assert calls == 2

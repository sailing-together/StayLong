"""Durable-shaped reminder state machine with bounded retries and escalation gates."""

from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from enum import StrEnum
from typing import TypeVar
from uuid import uuid4

from staylong.domain.models import ActionApproval
from staylong.policy.approvals import ApprovalRequiredError, execute_approved_tool_action

T = TypeVar("T")


class ReminderStatus(StrEnum):
    PENDING = "pending"
    RETRY_SCHEDULED = "retry_scheduled"
    SENT = "sent"
    ESCALATED = "escalated"
    ESCALATION_BLOCKED = "escalation_blocked"


@dataclass(frozen=True, slots=True)
class Reminder:
    """A scheduled, inspectable reminder record."""

    reminder_id: str
    case_id: str
    action: str
    due_at: datetime
    max_attempts: int
    attempts: int = 0
    next_attempt_at: datetime | None = None
    status: ReminderStatus = ReminderStatus.PENDING
    last_error: str | None = None


class ReminderService:
    """Process due reminders without unbounded retries or unauthorised escalation."""

    def __init__(self) -> None:
        self._reminders: dict[str, Reminder] = {}

    def schedule(
        self, *, case_id: str, action: str, due_at: datetime, max_attempts: int = 3
    ) -> Reminder:
        if due_at.tzinfo is None:
            raise ValueError("Reminder due_at must include a timezone.")
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least one.")
        reminder = Reminder(
            reminder_id=uuid4().hex,
            case_id=case_id,
            action=action,
            due_at=due_at,
            max_attempts=max_attempts,
            next_attempt_at=due_at,
        )
        self._reminders[reminder.reminder_id] = reminder
        return reminder

    def get(self, reminder_id: str) -> Reminder:
        return self._reminders[reminder_id]

    def process_due(
        self,
        *,
        now: datetime,
        send: Callable[[Reminder], object],
        escalate: Callable[[Reminder], object] | None = None,
        escalation_approval: ActionApproval | None = None,
    ) -> tuple[Reminder, ...]:
        """Process due records once and return their resulting state snapshots."""
        processed: list[Reminder] = []
        for reminder in tuple(self._reminders.values()):
            due_at = reminder.next_attempt_at or reminder.due_at
            if reminder.status not in {
                ReminderStatus.PENDING,
                ReminderStatus.RETRY_SCHEDULED,
            } or due_at > now:
                continue
            processed.append(self._process_one(reminder, now, send, escalate, escalation_approval))
        return tuple(processed)

    def _process_one(
        self,
        reminder: Reminder,
        now: datetime,
        send: Callable[[Reminder], object],
        escalate: Callable[[Reminder], object] | None,
        escalation_approval: ActionApproval | None,
    ) -> Reminder:
        try:
            send(reminder)
        except Exception as error:
            attempts = reminder.attempts + 1
            updated = replace(reminder, attempts=attempts, last_error=str(error))
            if attempts < reminder.max_attempts:
                updated = replace(
                    updated,
                    status=ReminderStatus.RETRY_SCHEDULED,
                    next_attempt_at=now + timedelta(minutes=2**attempts),
                )
            else:
                updated = self._try_escalation(
                    updated, now, escalate, escalation_approval
                )
        else:
            updated = replace(
                reminder,
                attempts=reminder.attempts + 1,
                next_attempt_at=None,
                status=ReminderStatus.SENT,
                last_error=None,
            )
        self._reminders[reminder.reminder_id] = updated
        return updated

    def _try_escalation(
        self,
        reminder: Reminder,
        now: datetime,
        escalate: Callable[[Reminder], object] | None,
        approval: ActionApproval | None,
    ) -> Reminder:
        if escalate is None:
            return replace(reminder, status=ReminderStatus.ESCALATION_BLOCKED)
        try:
            execute_approved_tool_action(
                case_id=reminder.case_id,
                action_type="reminder.escalate",
                action_revision=reminder.attempts,
                approval=approval,
                now=now,
                action=lambda: escalate(reminder),
            )
        except ApprovalRequiredError:
            return replace(reminder, status=ReminderStatus.ESCALATION_BLOCKED)
        return replace(reminder, status=ReminderStatus.ESCALATED)

"""Async boundary for running reminder work in a background execution cycle."""

import asyncio
from collections.abc import Callable
from datetime import datetime

from staylong.domain.models import ActionApproval
from staylong.services.reminders import Reminder, ReminderService


class AsyncWorkflowRunner:
    """Run one reminder queue pass without blocking the serving event loop."""

    def __init__(self, *, reminders: ReminderService) -> None:
        self._reminders = reminders

    async def run_once(
        self,
        *,
        now: datetime,
        send: Callable[[Reminder], object],
        escalate: Callable[[Reminder], object] | None = None,
        escalation_approval: ActionApproval | None = None,
    ) -> tuple[Reminder, ...]:
        """Process due work in a worker thread and return durable state snapshots."""
        return await asyncio.to_thread(
            self._reminders.process_due,
            now=now,
            send=send,
            escalate=escalate,
            escalation_approval=escalation_approval,
        )

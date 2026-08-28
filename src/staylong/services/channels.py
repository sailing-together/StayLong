"""Approval-gated demo adapters for calendar, email and SMS coordination actions."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime

from staylong.domain.models import ActionApproval
from staylong.policy.approvals import execute_approved_tool_action


@dataclass(frozen=True, slots=True)
class CalendarDetails:
    """The non-sensitive fields needed by a calendar demo connector."""

    title: str
    starts_at: str
    ends_at: str


@dataclass(frozen=True, slots=True)
class MessageDetails:
    """A draft message shared by the email and SMS demo connectors."""

    recipient: str
    subject: str
    body: str


@dataclass(frozen=True, slots=True)
class DemoDispatchResult:
    """A local, inspectable result standing in for an external provider response."""

    case_id: str
    action_type: str
    action_revision: int
    channel: str
    payload: Mapping[str, str]


class CalendarDemoAdapter:
    """Record a calendar event only after the exact human approval is verified."""

    action_type = "calendar.create"
    integration_mode = "sandbox"

    def __init__(self) -> None:
        self._items: list[DemoDispatchResult] = []

    @property
    def sent_items(self) -> tuple[DemoDispatchResult, ...]:
        return tuple(self._items)

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
        del session_id
        result = DemoDispatchResult(
            case_id=case_id,
            action_type=self.action_type,
            action_revision=revision,
            channel="calendar",
            payload={
                "title": details.title,
                "starts_at": details.starts_at,
                "ends_at": details.ends_at,
            },
        )
        return execute_approved_tool_action(
            case_id=case_id,
            action_type=self.action_type,
            action_revision=revision,
            approval=approval,
            now=now,
            action=lambda: self._record(result),
        )

    def _record(self, result: DemoDispatchResult) -> DemoDispatchResult:
        self._items.append(result)
        return result


class ContactDraftDemoAdapter:
    """Create an inspectable, unsent contact draft after its own approval."""

    action_type = "contact_draft.create"
    integration_mode = "sandbox"

    def __init__(self) -> None:
        self._items: list[DemoDispatchResult] = []

    @property
    def sent_items(self) -> tuple[DemoDispatchResult, ...]:
        return tuple(self._items)

    def create_draft(
        self,
        *,
        case_id: str,
        revision: int,
        approval: ActionApproval | None,
        now: datetime,
        details: MessageDetails,
    ) -> DemoDispatchResult:
        result = DemoDispatchResult(
            case_id=case_id,
            action_type=self.action_type,
            action_revision=revision,
            channel="contact_draft",
            payload={
                "recipient": details.recipient,
                "subject": details.subject,
                "body": details.body,
                "delivery": "draft_only",
            },
        )
        return execute_approved_tool_action(
            case_id=case_id,
            action_type=self.action_type,
            action_revision=revision,
            approval=approval,
            now=now,
            action=lambda: self._record(result),
        )

    def _record(self, result: DemoDispatchResult) -> DemoDispatchResult:
        self._items.append(result)
        return result


class EmailDemoAdapter:
    """Record an email only after the exact human approval is verified."""

    action_type = "message.email.send"

    def __init__(self) -> None:
        self._items: list[DemoDispatchResult] = []

    @property
    def sent_items(self) -> tuple[DemoDispatchResult, ...]:
        return tuple(self._items)

    def send(
        self,
        *,
        case_id: str,
        revision: int,
        approval: ActionApproval | None,
        now: datetime,
        details: MessageDetails,
    ) -> DemoDispatchResult:
        result = DemoDispatchResult(
            case_id=case_id,
            action_type=self.action_type,
            action_revision=revision,
            channel="email",
            payload={
                "recipient": details.recipient,
                "subject": details.subject,
                "body": details.body,
            },
        )
        return execute_approved_tool_action(
            case_id=case_id,
            action_type=self.action_type,
            action_revision=revision,
            approval=approval,
            now=now,
            action=lambda: self._record(result),
        )

    def _record(self, result: DemoDispatchResult) -> DemoDispatchResult:
        self._items.append(result)
        return result


class SmsDemoAdapter(EmailDemoAdapter):
    """Record an SMS with the same approval boundary and a distinct action type."""

    action_type = "message.sms.send"

    def __init__(self) -> None:
        super().__init__()

    def send(
        self,
        *,
        case_id: str,
        revision: int,
        approval: ActionApproval | None,
        now: datetime,
        details: MessageDetails,
    ) -> DemoDispatchResult:
        result = DemoDispatchResult(
            case_id=case_id,
            action_type=self.action_type,
            action_revision=revision,
            channel="sms",
            payload={
                "recipient": details.recipient,
                "subject": details.subject,
                "body": details.body,
            },
        )
        return execute_approved_tool_action(
            case_id=case_id,
            action_type=self.action_type,
            action_revision=revision,
            approval=approval,
            now=now,
            action=lambda: self._record(result),
        )

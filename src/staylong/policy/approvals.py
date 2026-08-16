"""The mandatory boundary before any StayLong external tool action."""

from collections.abc import Callable
from datetime import datetime

from staylong.domain.models import ActionApproval


class ApprovalRequiredError(PermissionError):
    """Raised before a tool action when no current matching approval exists."""


def has_matching_approval(
    *,
    case_id: str,
    action_type: str,
    action_revision: int,
    approval: ActionApproval | None,
    now: datetime,
) -> bool:
    """Return whether the durable approval authorises this exact action revision."""
    return approval is not None and (
        approval.case_id == case_id
        and approval.action_type == action_type
        and approval.action_revision == action_revision
        and approval.expires_at > now
    )


def execute_approved_tool_action[T](
    *,
    case_id: str,
    action_type: str,
    action_revision: int,
    approval: ActionApproval | None,
    now: datetime,
    action: Callable[[], T],
) -> T:
    """Execute an external action only after its exact approval has been verified."""
    if not has_matching_approval(
        case_id=case_id,
        action_type=action_type,
        action_revision=action_revision,
        approval=approval,
        now=now,
    ):
        raise ApprovalRequiredError(
            "A current matching approval is required before tool execution."
        )

    return action()

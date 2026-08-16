"""Immutable records that form StayLong's durable workflow boundary."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from types import MappingProxyType
from uuid import uuid4


def _new_id() -> str:
    return uuid4().hex


def _utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class AuthorisedContact:
    """A household contact authorised to take part in coordination."""

    name: str
    relationship: str
    contact_id: str = field(default_factory=_new_id)
    created_at: datetime = field(default_factory=_utc_now)


@dataclass(frozen=True, slots=True)
class Concern:
    """A family-reported coordination concern, without medical interpretation."""

    case_id: str
    summary: str
    concern_id: str = field(default_factory=_new_id)
    created_at: datetime = field(default_factory=_utc_now)


@dataclass(frozen=True, slots=True)
class ActionApproval:
    """A time-bounded human approval for one revision of an external action."""

    case_id: str
    action_type: str
    action_revision: int
    approved_by_contact_id: str
    expires_at: datetime
    approval_id: str = field(default_factory=_new_id)
    created_at: datetime = field(default_factory=_utc_now)


@dataclass(frozen=True, slots=True)
class TimelineEvent:
    """An append-only audit event describing a workflow decision or outcome."""

    case_id: str
    event_type: str
    details: Mapping[str, str] = field(default_factory=dict)
    event_id: str = field(default_factory=_new_id)
    occurred_at: datetime = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        object.__setattr__(self, "details", MappingProxyType(dict(self.details)))

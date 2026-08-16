"""Deterministic case-state reconstruction from append-only workflow events."""

from dataclasses import dataclass
from enum import StrEnum

from staylong.domain.models import TimelineEvent
from staylong.services.events import EventRepository


class CaseStage(StrEnum):
    """The small, human-reviewable lifecycle used by the initial coordination flow."""

    NEW = "new"
    INTAKE = "intake"
    AWAITING_APPROVAL = "awaiting_approval"
    COORDINATING = "coordinating"
    COMPLETED = "completed"


class InvalidStateTransition(ValueError):
    """Raised when the durable timeline attempts to skip a required workflow gate."""


@dataclass(frozen=True, slots=True)
class CaseWorkflowState:
    """The deterministic projection of a case's append-only timeline."""

    case_id: str
    stage: CaseStage = CaseStage.NEW
    applied_event_ids: tuple[str, ...] = ()


class CaseWorkflowReplayer:
    """Rebuild a case state from its persisted events after any process restart."""

    def __init__(self, *, repository: EventRepository) -> None:
        self._repository = repository

    def replay(self, *, case_id: str) -> CaseWorkflowState:
        """Apply a case timeline in stable event-time order without process memory."""
        state = CaseWorkflowState(case_id=case_id)
        events = sorted(
            self._repository.list_events(case_id=case_id),
            key=lambda event: (event.occurred_at, event.event_id),
        )
        for event in events:
            state = _apply(state, event)
        return state


def _apply(state: CaseWorkflowState, event: TimelineEvent) -> CaseWorkflowState:
    if event.case_id != state.case_id:
        raise InvalidStateTransition("An event cannot be applied to another case")

    expected_stage = {
        "concern.created": CaseStage.NEW,
        "assessment.pack.prepared": CaseStage.INTAKE,
        "approval.granted": CaseStage.AWAITING_APPROVAL,
        "coordination.completed": CaseStage.COORDINATING,
    }.get(event.event_type)
    if expected_stage is None:
        raise InvalidStateTransition(f"Unsupported workflow event: {event.event_type}")
    if state.stage is not expected_stage:
        raise InvalidStateTransition(
            f"Event {event.event_type} requires {expected_stage.value}, "
            f"but case is {state.stage.value}"
        )

    return CaseWorkflowState(
        case_id=state.case_id,
        stage={
            "concern.created": CaseStage.INTAKE,
            "assessment.pack.prepared": CaseStage.AWAITING_APPROVAL,
            "approval.granted": CaseStage.COORDINATING,
            "coordination.completed": CaseStage.COMPLETED,
        }[event.event_type],
        applied_event_ids=(*state.applied_event_ids, event.event_id),
    )

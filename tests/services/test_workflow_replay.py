"""Integration tests for replaying durable events into case workflow state."""

from datetime import UTC, datetime, timedelta

import pytest


def _event(event_id: str, event_type: str, minute: int) -> object:
    from staylong.domain.models import TimelineEvent

    return TimelineEvent(
        case_id="case-001",
        event_type=event_type,
        details={"source": "integration-test"},
        event_id=event_id,
        occurred_at=datetime(2026, 8, 16, 9, 0, tzinfo=UTC) + timedelta(minutes=minute),
    )


def test_replay_rebuilds_the_same_completed_state_from_persisted_events() -> None:
    """A restart must rebuild the same state without retaining process memory."""
    from staylong.services.events import InMemoryEventRepository
    from staylong.services.workflow import CaseStage, CaseWorkflowReplayer

    repository = InMemoryEventRepository()
    for event in (
        _event("event-001", "concern.created", 0),
        _event("event-002", "assessment.pack.prepared", 1),
        _event("event-003", "approval.granted", 2),
        _event("event-004", "coordination.completed", 3),
    ):
        assert repository.append_if_new(event) is True

    replayer = CaseWorkflowReplayer(repository=repository)

    first_replay = replayer.replay(case_id="case-001")
    second_replay = replayer.replay(case_id="case-001")

    assert first_replay == second_replay
    assert first_replay.stage is CaseStage.COMPLETED
    assert first_replay.applied_event_ids == (
        "event-001",
        "event-002",
        "event-003",
        "event-004",
    )


def test_replay_rejects_an_invalid_state_transition() -> None:
    """An approval cannot become an external coordination action without preparation."""
    from staylong.services.events import InMemoryEventRepository
    from staylong.services.workflow import CaseWorkflowReplayer, InvalidStateTransition

    repository = InMemoryEventRepository()
    repository.append_if_new(_event("event-001", "concern.created", 0))
    repository.append_if_new(_event("event-002", "approval.granted", 1))

    with pytest.raises(InvalidStateTransition, match="approval.granted"):
        CaseWorkflowReplayer(repository=repository).replay(case_id="case-001")


def test_replay_orders_events_by_timestamp_not_storage_order() -> None:
    """Firestore retrieval order must not change the resulting case state."""
    from staylong.services.events import InMemoryEventRepository
    from staylong.services.workflow import CaseStage, CaseWorkflowReplayer

    repository = InMemoryEventRepository()
    for event in (
        _event("event-004", "coordination.completed", 3),
        _event("event-002", "assessment.pack.prepared", 1),
        _event("event-001", "concern.created", 0),
        _event("event-003", "approval.granted", 2),
    ):
        repository.append_if_new(event)

    rebuilt = CaseWorkflowReplayer(repository=repository).replay(case_id="case-001")

    assert rebuilt.stage is CaseStage.COMPLETED

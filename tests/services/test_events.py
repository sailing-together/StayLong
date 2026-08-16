"""Tests for idempotent timeline-event persistence."""

from datetime import UTC, datetime


def test_event_processor_persists_an_event_only_once() -> None:
    """Removing duplicate detection would write the same incoming event twice."""
    from staylong.domain.models import TimelineEvent
    from staylong.services.events import IdempotentEventProcessor, InMemoryEventRepository

    repository = InMemoryEventRepository()
    processor = IdempotentEventProcessor(repository=repository)
    event = TimelineEvent(
        case_id="case-001",
        event_type="concern.created",
        details={"concern_id": "concern-001"},
        event_id="event-001",
        occurred_at=datetime(2026, 8, 16, 9, 0, tzinfo=UTC),
    )

    assert processor.process(event) is True
    assert processor.process(event) is False
    assert repository.list_events(case_id="case-001") == (event,)


def test_event_repository_keeps_each_case_timeline_separate() -> None:
    """Ignoring a case id would expose one household's timeline to another."""
    from staylong.domain.models import TimelineEvent
    from staylong.services.events import InMemoryEventRepository

    repository = InMemoryEventRepository()
    first_event = TimelineEvent(
        case_id="case-001",
        event_type="concern.created",
        event_id="event-001",
    )
    second_event = TimelineEvent(
        case_id="case-002",
        event_type="concern.created",
        event_id="event-002",
    )

    assert repository.append_if_new(first_event) is True
    assert repository.append_if_new(second_event) is True
    assert repository.list_events(case_id="case-001") == (first_event,)


def test_firestore_event_repository_rejects_a_duplicate_event_id() -> None:
    """Replacing atomic create with an overwrite would duplicate event processing."""
    from staylong.domain.models import TimelineEvent
    from staylong.services.events import FirestoreEventRepository
    from tests.services.fake_firestore import FakeFirestoreClient

    repository = FirestoreEventRepository(client=FakeFirestoreClient())
    event = TimelineEvent(
        case_id="case-001",
        event_type="concern.created",
        details={"concern_id": "concern-001"},
        event_id="event-001",
        occurred_at=datetime(2026, 8, 16, 9, 0, tzinfo=UTC),
    )

    assert repository.append_if_new(event) is True
    assert repository.append_if_new(event) is False
    assert repository.list_events(case_id="case-001") == (event,)

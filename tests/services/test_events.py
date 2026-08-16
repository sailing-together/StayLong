"""Tests for idempotent timeline-event persistence."""

from datetime import UTC, datetime

import pytest


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


@pytest.mark.parametrize("adapter", ["in_memory", "firestore"])
def test_event_id_is_global_and_preserves_the_original_event(adapter: str) -> None:
    """Scoping duplicate detection by case would overwrite or duplicate incoming events."""
    from staylong.domain.models import TimelineEvent
    from staylong.services.events import FirestoreEventRepository, InMemoryEventRepository
    from tests.services.fake_firestore import FakeFirestoreClient

    repository = (
        InMemoryEventRepository()
        if adapter == "in_memory"
        else FirestoreEventRepository(client=FakeFirestoreClient())
    )
    original = TimelineEvent(
        case_id="case-001",
        event_type="concern.created",
        details={"concern_id": "concern-001"},
        event_id="event-001",
        occurred_at=datetime(2026, 8, 16, 9, 0, tzinfo=UTC),
    )
    changed_duplicate = TimelineEvent(
        case_id="case-002",
        event_type="concern.updated",
        details={"concern_id": "concern-002"},
        event_id="event-001",
        occurred_at=datetime(2026, 8, 16, 9, 5, tzinfo=UTC),
    )

    assert repository.append_if_new(original) is True
    assert repository.append_if_new(changed_duplicate) is False
    assert repository.list_events(case_id="case-001") == (original,)
    assert repository.list_events(case_id="case-002") == ()

"""Idempotent persistence for append-only workflow timeline events."""

from typing import Any, Protocol

from staylong.domain.models import TimelineEvent


class EventRepository(Protocol):
    """Append timeline events and retrieve a case's timeline."""

    def append_if_new(self, event: TimelineEvent) -> bool:
        """Persist an event once, returning whether this call inserted it."""

    def list_events(self, *, case_id: str) -> tuple[TimelineEvent, ...]:
        """Return persisted events belonging to a case."""


class InMemoryEventRepository:
    """Small event repository adapter for local development and tests."""

    def __init__(self) -> None:
        self._events_by_id: dict[str, TimelineEvent] = {}

    def append_if_new(self, event: TimelineEvent) -> bool:
        if event.event_id in self._events_by_id:
            return False
        self._events_by_id[event.event_id] = event
        return True

    def list_events(self, *, case_id: str) -> tuple[TimelineEvent, ...]:
        return tuple(event for event in self._events_by_id.values() if event.case_id == case_id)


class IdempotentEventProcessor:
    """Process one incoming event without repeating its timeline side effect."""

    def __init__(self, *, repository: EventRepository) -> None:
        self._repository = repository

    def process(self, event: TimelineEvent) -> bool:
        """Return whether processing persisted this event for the first time."""
        return self._repository.append_if_new(event)


class FirestoreEventRepository:
    """Firestore event adapter with atomic document-identity deduplication."""

    def __init__(self, client: Any | None = None) -> None:
        self._client = client or _new_firestore_client()

    def append_if_new(self, event: TimelineEvent) -> bool:
        try:
            self._events(event.case_id).document(event.event_id).create(_event_document(event))
        except Exception as error:
            if _is_already_exists(error):
                return False
            raise
        return True

    def list_events(self, *, case_id: str) -> tuple[TimelineEvent, ...]:
        return tuple(
            _event_from_document(document.to_dict()) for document in self._events(case_id).stream()
        )

    def _events(self, case_id: str) -> Any:
        return self._client.collection("cases").document(case_id).collection("events")


def _new_firestore_client() -> Any:
    """Construct the optional cloud client only when this adapter is selected."""
    from google.cloud import firestore

    return firestore.Client()


def _event_document(event: TimelineEvent) -> dict[str, Any]:
    return {
        "case_id": event.case_id,
        "event_type": event.event_type,
        "details": dict(event.details),
        "event_id": event.event_id,
        "occurred_at": event.occurred_at,
    }


def _event_from_document(data: dict[str, Any]) -> TimelineEvent:
    return TimelineEvent(
        case_id=data["case_id"],
        event_type=data["event_type"],
        details=data.get("details", {}),
        event_id=data["event_id"],
        occurred_at=data["occurred_at"],
    )


def _is_already_exists(error: Exception) -> bool:
    """Recognise Firestore's optional dependency error without importing it eagerly."""
    if error.__class__.__name__ == "AlreadyExists":
        return True
    error_code = getattr(error, "code", None)
    if callable(error_code):
        error_code = error_code()
    return getattr(error_code, "name", error_code) == "ALREADY_EXISTS"

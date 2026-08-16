"""Tests for portable asynchronous dispatch contracts and adapters."""

import json
from datetime import UTC, datetime

import pytest


class FakePublishFuture:
    def __init__(self, message_id: str) -> None:
        self._message_id = message_id

    def result(self) -> str:
        return self._message_id


class FakePublisher:
    def __init__(self) -> None:
        self.calls: list[tuple[str, bytes, dict[str, str]]] = []

    def publish(self, topic: str, data: bytes, **attributes: str) -> FakePublishFuture:
        self.calls.append((topic, data, attributes))
        return FakePublishFuture("pubsub-message-001")


class FakeTasksClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []

    def queue_path(self, project: str, location: str, queue: str) -> str:
        return f"projects/{project}/locations/{location}/queues/{queue}"

    def create_task(self, *, parent: str, task: dict[str, object]) -> object:
        self.calls.append((parent, task))
        return type("Task", (), {"name": f"{parent}/tasks/task-001"})()


def _event(event_type: str = "concern.created") -> object:
    from staylong.domain.models import TimelineEvent

    return TimelineEvent(
        case_id="case-001",
        event_type=event_type,
        details={"concern_id": "concern-001"},
        event_id="event-001",
        occurred_at=datetime(2026, 8, 16, 9, 0, tzinfo=UTC),
    )


def test_event_contract_rejects_unsupported_processing_path() -> None:
    """A typo must not silently create an unhandled background message."""
    from staylong.services.dispatch import DispatchEvent, EventContractError

    with pytest.raises(EventContractError, match="Unsupported event type"):
        DispatchEvent.from_timeline_event(_event("concern.unknown"))


def test_pubsub_adapter_publishes_a_versioned_event_contract() -> None:
    """The broker message preserves identity, routing metadata and payload."""
    from staylong.services.dispatch import DispatchEvent, PubSubDispatchAdapter

    publisher = FakePublisher()
    receipt = PubSubDispatchAdapter(
        publisher=publisher,
        topic_path="projects/staylong-sandbox/topics/workflow-events",
    ).dispatch(DispatchEvent.from_timeline_event(_event()))

    assert receipt.transport == "pubsub"
    assert receipt.message_id == "pubsub-message-001"
    assert publisher.calls[0][0] == "projects/staylong-sandbox/topics/workflow-events"
    assert publisher.calls[0][2] == {
        "case_id": "case-001",
        "event_id": "event-001",
        "event_type": "concern.created",
        "schema_version": "v1",
    }
    assert json.loads(publisher.calls[0][1]) == {
        "case_id": "case-001",
        "details": {"concern_id": "concern-001"},
        "event_id": "event-001",
        "event_type": "concern.created",
        "occurred_at": "2026-08-16T09:00:00+00:00",
        "schema_version": "v1",
    }


def test_cloud_tasks_adapter_creates_an_authenticated_work_item() -> None:
    """The task is traceable and carries the same versioned event contract."""
    from staylong.services.dispatch import CloudTasksDispatchAdapter, DispatchEvent

    client = FakeTasksClient()
    receipt = CloudTasksDispatchAdapter(
        client=client,
        project_id="staylong-sandbox",
        location="australia-southeast1",
        queue="workflow-events",
        target_uri="https://staylong.example.test/internal/events",
        service_account_email="workflow-runtime@staylong-sandbox.iam.gserviceaccount.com",
    ).dispatch(DispatchEvent.from_timeline_event(_event("reminder.due")))

    assert receipt.transport == "cloud_tasks"
    assert receipt.message_id.endswith("/tasks/task-001")
    parent, task = client.calls[0]
    assert (
        parent
        == "projects/staylong-sandbox/locations/australia-southeast1/queues/workflow-events"
    )
    assert task["name"].endswith("/tasks/event-001")
    request = task["http_request"]
    assert request == {
        "http_method": "POST",
        "url": "https://staylong.example.test/internal/events",
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(
            {
                "case_id": "case-001",
                "details": {"concern_id": "concern-001"},
                "event_id": "event-001",
                "event_type": "reminder.due",
                "occurred_at": "2026-08-16T09:00:00+00:00",
                "schema_version": "v1",
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode(),
        "oidc_token": {
            "service_account_email": "workflow-runtime@staylong-sandbox.iam.gserviceaccount.com"
        },
    }

"""Versioned contracts and adapters for durable asynchronous workflow events."""

import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

from staylong.domain.models import TimelineEvent

SCHEMA_VERSION = "v1"
SUPPORTED_EVENT_TYPES = frozenset(
    {
        "concern.created",
        "assessment.pack.prepared",
        "approval.granted",
        "reminder.due",
        "coordination.completed",
    }
)


class EventContractError(ValueError):
    """Raised when a timeline event cannot safely enter async processing."""


@dataclass(frozen=True, slots=True)
class DispatchEvent:
    """Stable, JSON-serialisable event sent to an asynchronous transport."""

    case_id: str
    event_id: str
    event_type: str
    occurred_at: datetime
    details: Mapping[str, str]
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.event_type not in SUPPORTED_EVENT_TYPES:
            raise EventContractError(f"Unsupported event type: {self.event_type}")
        if self.schema_version != SCHEMA_VERSION:
            raise EventContractError(f"Unsupported schema version: {self.schema_version}")
        if self.occurred_at.tzinfo is None:
            raise EventContractError("Event timestamps must include a timezone")

    @classmethod
    def from_timeline_event(cls, event: TimelineEvent) -> "DispatchEvent":
        """Convert only a declared processing path into a transport contract."""
        return cls(
            case_id=event.case_id,
            event_id=event.event_id,
            event_type=event.event_type,
            occurred_at=event.occurred_at,
            details=event.details,
        )

    def attributes(self) -> dict[str, str]:
        """Return non-sensitive routing metadata for transport-level filtering."""
        return {
            "case_id": self.case_id,
            "event_id": self.event_id,
            "event_type": self.event_type,
            "schema_version": self.schema_version,
        }

    def body(self) -> bytes:
        """Return the canonical JSON message body shared by all adapters."""
        document = {
            "case_id": self.case_id,
            "details": dict(self.details),
            "event_id": self.event_id,
            "event_type": self.event_type,
            "occurred_at": self.occurred_at.astimezone(UTC).isoformat(),
            "schema_version": self.schema_version,
        }
        return json.dumps(document, sort_keys=True, separators=(",", ":")).encode()


@dataclass(frozen=True, slots=True)
class DispatchReceipt:
    """Transport acknowledgement that is safe to retain in the audit timeline."""

    transport: str
    message_id: str


class EventDispatcher(Protocol):
    """Send a declared workflow event to an asynchronous execution transport."""

    def dispatch(self, event: DispatchEvent) -> DispatchReceipt:
        """Publish one event and return the transport acknowledgement."""


class PubSubDispatchAdapter:
    """Publish workflow events to a Google Cloud Pub/Sub topic."""

    def __init__(self, *, topic_path: str, publisher: Any | None = None) -> None:
        self._topic_path = topic_path
        self._publisher = publisher or _new_pubsub_publisher()

    def dispatch(self, event: DispatchEvent) -> DispatchReceipt:
        future = self._publisher.publish(self._topic_path, event.body(), **event.attributes())
        return DispatchReceipt(transport="pubsub", message_id=str(future.result()))


class CloudTasksDispatchAdapter:
    """Create authenticated HTTP work items in a Google Cloud Tasks queue."""

    def __init__(
        self,
        *,
        project_id: str,
        location: str,
        queue: str,
        target_uri: str,
        service_account_email: str,
        client: Any | None = None,
    ) -> None:
        self._project_id = project_id
        self._location = location
        self._queue = queue
        self._target_uri = target_uri
        self._service_account_email = service_account_email
        self._client = client or _new_tasks_client()

    def dispatch(self, event: DispatchEvent) -> DispatchReceipt:
        parent = self._client.queue_path(self._project_id, self._location, self._queue)
        task = {
            "name": f"{parent}/tasks/{event.event_id}",
            "http_request": {
                "http_method": "POST",
                "url": self._target_uri,
                "headers": {"Content-Type": "application/json"},
                "body": event.body(),
                "oidc_token": {"service_account_email": self._service_account_email},
            },
        }
        created_task = self._client.create_task(parent=parent, task=task)
        return DispatchReceipt(transport="cloud_tasks", message_id=str(created_task.name))


def _new_pubsub_publisher() -> Any:
    """Construct the optional Cloud client only when this adapter is selected."""
    from google.cloud import pubsub_v1

    return pubsub_v1.PublisherClient()


def _new_tasks_client() -> Any:
    """Construct the optional Cloud client only when this adapter is selected."""
    from google.cloud import tasks_v2

    return tasks_v2.CloudTasksClient()

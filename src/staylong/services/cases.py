"""Persistence boundary for family-reported concerns."""

from datetime import datetime
from typing import Any, Protocol

from staylong.domain.models import Concern


class CaseRepository(Protocol):
    """Store and retrieve concerns for one household case."""

    def create_concern(self, *, case_id: str, summary: str) -> Concern:
        """Create and persist a family-reported concern."""

    def list_concerns(self, *, case_id: str) -> tuple[Concern, ...]:
        """Return all persisted concerns for a case."""


class InMemoryCaseRepository:
    """Small repository adapter for local development and tests."""

    def __init__(self) -> None:
        self._concerns_by_case: dict[str, list[Concern]] = {}

    def create_concern(self, *, case_id: str, summary: str) -> Concern:
        concern = Concern(case_id=case_id, summary=summary)
        self._concerns_by_case.setdefault(case_id, []).append(concern)
        return concern

    def list_concerns(self, *, case_id: str) -> tuple[Concern, ...]:
        return tuple(self._concerns_by_case.get(case_id, ()))


class FirestoreCaseRepository:
    """Firestore adapter using the same repository contract as local storage."""

    def __init__(self, client: Any | None = None) -> None:
        self._client = client or _new_firestore_client()

    def create_concern(self, *, case_id: str, summary: str) -> Concern:
        concern = Concern(case_id=case_id, summary=summary)
        self._concerns(case_id).document(concern.concern_id).set(_concern_document(concern))
        return concern

    def list_concerns(self, *, case_id: str) -> tuple[Concern, ...]:
        return tuple(
            _concern_from_document(document.to_dict())
            for document in self._concerns(case_id).stream()
        )

    def _concerns(self, case_id: str) -> Any:
        return self._client.collection("cases").document(case_id).collection("concerns")


def _new_firestore_client() -> Any:
    """Construct the optional cloud client only when this adapter is selected."""
    from google.cloud import firestore

    return firestore.Client()


def _concern_document(concern: Concern) -> dict[str, str | datetime]:
    return {
        "case_id": concern.case_id,
        "summary": concern.summary,
        "concern_id": concern.concern_id,
        "created_at": concern.created_at,
    }


def _concern_from_document(data: dict[str, Any]) -> Concern:
    return Concern(
        case_id=data["case_id"],
        summary=data["summary"],
        concern_id=data["concern_id"],
        created_at=data["created_at"],
    )

"""Anonymous public-sandbox session ownership primitives.

This module deliberately persists only a derived owner key. A browser session
token is an authentication credential and must never be written to a database
or log.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Protocol

from staylong.services.firestore_schema import public_case_access_document

if TYPE_CHECKING:
    from staylong.services.events import EventRepository
    from staylong.services.taskmaster import WorkflowRepository


class PublicCaseAccessDenied(PermissionError):
    """Raised when a public session cannot access a sandbox case."""


@dataclass(frozen=True)
class PublicSession:
    """A temporary browser credential and its non-reversible ownership key."""

    token: str
    owner_key: str
    expires_at: datetime


@dataclass(frozen=True)
class PublicCaseAccess:
    """Ownership and lifetime metadata for one public-sandbox case."""

    case_id: str
    owner_key: str
    expires_at: datetime


class PublicCaseAccessRepository(Protocol):
    """Persistence boundary for anonymous sandbox case ownership."""

    def claim(
        self,
        *,
        case_id: str,
        owner_key: str,
        expires_at: datetime,
        created_at: datetime | None = None,
    ) -> PublicCaseAccess: ...

    def assert_owner(
        self, *, case_id: str, owner_key: str, now: datetime
    ) -> PublicCaseAccess: ...

    def delete_expired(self, *, now: datetime) -> tuple[str, ...]: ...

    def count_active_for_owner(self, *, owner_key: str, now: datetime) -> int: ...

    def list_expired(self, *, now: datetime) -> tuple[str, ...]: ...


def owner_key_for(token: str, secret: str) -> str:
    """Return the HMAC-derived persistence key for an opaque browser token."""
    return hmac.new(secret.encode(), token.encode(), hashlib.sha256).hexdigest()


def new_public_session(*, secret: str, now: datetime, lifetime: timedelta) -> PublicSession:
    """Create an opaque session token and its database-safe ownership key."""
    token = secrets.token_urlsafe(32)
    return PublicSession(
        token=token,
        owner_key=owner_key_for(token, secret),
        expires_at=now + lifetime,
    )


class InMemoryPublicCaseAccessRepository:
    """Test/local implementation of public case ownership checks."""

    def __init__(self) -> None:
        self._access_by_case_id: dict[str, PublicCaseAccess] = {}

    def claim(
        self,
        *,
        case_id: str,
        owner_key: str,
        expires_at: datetime,
        created_at: datetime | None = None,
    ) -> PublicCaseAccess:
        """Bind a newly created public case to exactly one temporary session."""
        del created_at
        access = PublicCaseAccess(
            case_id=case_id,
            owner_key=owner_key,
            expires_at=expires_at,
        )
        existing = self._access_by_case_id.get(case_id)
        if existing is not None and existing != access:
            raise ValueError(f"Public case {case_id!r} is already claimed.")
        self._access_by_case_id[case_id] = access
        return access

    def assert_owner(self, *, case_id: str, owner_key: str, now: datetime) -> PublicCaseAccess:
        """Return access only when the active session owns an unexpired case."""
        access = self._access_by_case_id.get(case_id)
        if access is None or access.expires_at <= now:
            raise PublicCaseAccessDenied("Public sandbox case is unavailable.")
        if not hmac.compare_digest(access.owner_key, owner_key):
            raise PublicCaseAccessDenied("Public sandbox case is unavailable.")
        return access

    def delete_expired(self, *, now: datetime) -> tuple[str, ...]:
        """Delete expired case access records and return their identifiers."""
        expired_case_ids = tuple(
            case_id
            for case_id, access in self._access_by_case_id.items()
            if access.expires_at <= now
        )
        for case_id in expired_case_ids:
            del self._access_by_case_id[case_id]
        return expired_case_ids

    def count_active_for_owner(self, *, owner_key: str, now: datetime) -> int:
        """Count unexpired cases belonging to this session key."""
        return sum(
            1
            for access in self._access_by_case_id.values()
            if access.owner_key == owner_key and access.expires_at > now
        )

    def list_expired(self, *, now: datetime) -> tuple[str, ...]:
        """Return expired case IDs without deleting them."""
        return tuple(
            case_id
            for case_id, access in self._access_by_case_id.items()
            if access.expires_at <= now
        )


class FirestorePublicCaseAccessRepository:
    """Firestore implementation of public-sandbox case ownership checks."""

    def __init__(self, client: Any | None = None) -> None:
        self._client = client or _new_firestore_client()

    def claim(
        self,
        *,
        case_id: str,
        owner_key: str,
        expires_at: datetime,
        created_at: datetime | None = None,
    ) -> PublicCaseAccess:
        """Persist one case-to-session binding without overwriting another owner."""
        access = PublicCaseAccess(
            case_id=case_id,
            owner_key=owner_key,
            expires_at=expires_at,
        )
        reference = self._cases().document(case_id)
        existing = reference.get()
        if existing.exists:
            saved_access = _public_case_access_from_document(existing.to_dict())
            if saved_access != access:
                raise ValueError(f"Public case {case_id!r} is already claimed.")
            return saved_access
        reference.create(
            public_case_access_document(
                case_id=case_id,
                owner_key=owner_key,
                expires_at=expires_at,
                created_at=created_at or expires_at,
            )
        )
        return access

    def assert_owner(self, *, case_id: str, owner_key: str, now: datetime) -> PublicCaseAccess:
        """Return access only when a matching, unexpired Firestore mapping exists."""
        snapshot = self._cases().document(case_id).get()
        if not snapshot.exists:
            raise PublicCaseAccessDenied("Public sandbox case is unavailable.")
        access = _public_case_access_from_document(snapshot.to_dict())
        if access.expires_at <= now or not hmac.compare_digest(access.owner_key, owner_key):
            raise PublicCaseAccessDenied("Public sandbox case is unavailable.")
        return access

    def delete_expired(self, *, now: datetime) -> tuple[str, ...]:
        """Delete only expired public-sandbox access mappings."""
        expired_case_ids: list[str] = []
        for snapshot in self._cases().stream():
            data = snapshot.to_dict()
            if data.get("environment") != "public-sandbox":
                continue
            access = _public_case_access_from_document(data)
            if access.expires_at <= now:
                self._cases().document(access.case_id).delete()
                expired_case_ids.append(access.case_id)
        return tuple(expired_case_ids)

    def count_active_for_owner(self, *, owner_key: str, now: datetime) -> int:
        """Count unexpired Firestore mappings for one session key."""
        return sum(
            1
            for snapshot in self._cases()
                .where("owner_key", "==", owner_key)
                .stream()
            if _public_case_access_from_document(snapshot.to_dict()).expires_at > now
        )

    def list_expired(self, *, now: datetime) -> tuple[str, ...]:
        """Return expired case IDs without deleting their access mappings."""
        result: list[str] = []
        for snapshot in self._cases().stream():
            data = snapshot.to_dict()
            if data.get("environment") != "public-sandbox":
                continue
            access = _public_case_access_from_document(data)
            if access.expires_at <= now:
                result.append(access.case_id)
        return tuple(result)

    def _cases(self) -> Any:
        return self._client.collection("public_sandbox_cases")


def cleanup_expired_public_cases(
    *,
    case_access: PublicCaseAccessRepository,
    workflow_repository: WorkflowRepository,
    event_repository: EventRepository,
    now: datetime,
) -> tuple[str, ...]:
    """Delete workflow and event data before access mappings so retries are safe."""
    expired_ids = case_access.list_expired(now=now)
    for case_id in expired_ids:
        event_repository.delete_for_case(case_id)
        workflow_repository.delete(case_id=case_id)
    case_access.delete_expired(now=now)
    return expired_ids


def _public_case_access_from_document(data: dict[str, Any]) -> PublicCaseAccess:
    return PublicCaseAccess(
        case_id=data["case_id"],
        owner_key=data["owner_key"],
        expires_at=data["expires_at"],
    )


def _new_firestore_client() -> Any:
    """Create the optional cloud client only when the durable adapter is selected."""
    from google.cloud import firestore

    return firestore.Client()

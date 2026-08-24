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

    def claim(self, *, case_id: str, owner_key: str, expires_at: datetime) -> PublicCaseAccess:
        """Bind a newly created public case to exactly one temporary session."""
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

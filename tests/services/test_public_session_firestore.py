"""Firestore persistence contracts for anonymous public-sandbox ownership."""

from datetime import UTC, datetime, timedelta

import pytest

NOW = datetime(2026, 8, 24, 12, 0, tzinfo=UTC)
FUTURE = NOW + timedelta(hours=1)


def test_firestore_access_document_contains_no_raw_session_token() -> None:
    """A Firestore document must not turn a browser cookie into stored credentials."""
    from staylong.services.firestore_schema import public_case_access_document

    document = public_case_access_document(
        case_id="case-1",
        owner_key="hashed-owner",
        expires_at=FUTURE,
        created_at=NOW,
    )

    assert document == {
        "case_id": "case-1",
        "owner_key": "hashed-owner",
        "expires_at": FUTURE,
        "created_at": NOW,
        "environment": "public-sandbox",
    }
    assert all("token" not in field for field in document)


def test_firestore_repository_enforces_owner_and_removes_expired_case_access() -> None:
    """A durable public case must be private to its owning browser session."""
    from staylong.services.public_sessions import (
        FirestorePublicCaseAccessRepository,
        PublicCaseAccessDenied,
    )
    from tests.services.fake_firestore import FakeFirestoreClient

    repository = FirestorePublicCaseAccessRepository(client=FakeFirestoreClient())
    repository.claim(case_id="expired", owner_key="one", expires_at=NOW, created_at=NOW)
    repository.claim(case_id="active", owner_key="two", expires_at=FUTURE, created_at=NOW)

    with pytest.raises(PublicCaseAccessDenied):
        repository.assert_owner(case_id="active", owner_key="one", now=NOW)

    assert repository.delete_expired(now=NOW) == ("expired",)
    assert repository.assert_owner(case_id="active", owner_key="two", now=NOW).case_id == "active"
    with pytest.raises(PublicCaseAccessDenied):
        repository.assert_owner(case_id="expired", owner_key="one", now=NOW)

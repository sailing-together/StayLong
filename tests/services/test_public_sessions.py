"""Tests for anonymous public-sandbox session ownership."""

from datetime import UTC, datetime, timedelta

import pytest

NOW = datetime(2026, 8, 24, 12, 0, tzinfo=UTC)
FUTURE = NOW + timedelta(hours=1)


def test_owner_key_is_stable_but_does_not_contain_the_raw_cookie_token() -> None:
    """Persisting a raw browser credential would make a Firestore leak reusable."""
    from staylong.services.public_sessions import new_public_session, owner_key_for

    session = new_public_session(secret="test-secret", now=NOW, lifetime=timedelta(hours=24))

    assert owner_key_for(session.token, "test-secret") == session.owner_key
    assert session.token not in session.owner_key
    assert owner_key_for(session.token, "another-secret") != session.owner_key


def test_case_access_rejects_a_different_or_expired_session() -> None:
    """Removing ownership or expiry checks would expose a stranger's temporary case."""
    from staylong.services.public_sessions import (
        InMemoryPublicCaseAccessRepository,
        PublicCaseAccessDenied,
    )

    repository = InMemoryPublicCaseAccessRepository()
    repository.claim(case_id="case-1", owner_key="owner-one", expires_at=FUTURE)
    repository.claim(case_id="case-2", owner_key="owner-two", expires_at=NOW)

    owned_case = repository.assert_owner(
        case_id="case-1",
        owner_key="owner-one",
        now=NOW,
    )
    assert owned_case.case_id == "case-1"
    with pytest.raises(PublicCaseAccessDenied):
        repository.assert_owner(case_id="case-1", owner_key="owner-two", now=NOW)
    with pytest.raises(PublicCaseAccessDenied):
        repository.assert_owner(case_id="case-2", owner_key="owner-two", now=NOW)


def test_delete_expired_removes_only_expired_case_access() -> None:
    """Cleanup must not erase another active visitor's sandbox case."""
    from staylong.services.public_sessions import InMemoryPublicCaseAccessRepository

    repository = InMemoryPublicCaseAccessRepository()
    repository.claim(case_id="expired", owner_key="one", expires_at=NOW)
    repository.claim(case_id="active", owner_key="two", expires_at=FUTURE)

    assert repository.delete_expired(now=NOW) == ("expired",)
    assert repository.assert_owner(case_id="active", owner_key="two", now=NOW).case_id == "active"

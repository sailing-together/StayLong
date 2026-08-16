"""Tests for durable concern state."""


def test_in_memory_case_repository_creates_and_lists_a_concern() -> None:
    """Removing repository persistence would lose a family-reported concern."""
    from staylong.services.cases import InMemoryCaseRepository

    repository = InMemoryCaseRepository()

    concern = repository.create_concern(
        case_id="case-001",
        summary="The front step feels unsafe after rain.",
    )

    assert concern.case_id == "case-001"
    assert concern.summary == "The front step feels unsafe after rain."
    assert repository.list_concerns(case_id="case-001") == (concern,)
    assert repository.list_concerns(case_id="case-unknown") == ()


def test_firestore_case_repository_persists_the_same_concern_contract() -> None:
    """Breaking Firestore field mapping would make a stored concern unrecoverable."""
    from staylong.services.cases import FirestoreCaseRepository
    from tests.services.fake_firestore import FakeFirestoreClient

    repository = FirestoreCaseRepository(client=FakeFirestoreClient())

    concern = repository.create_concern(
        case_id="case-001",
        summary="The front step feels unsafe after rain.",
    )

    assert repository.list_concerns(case_id="case-001") == (concern,)

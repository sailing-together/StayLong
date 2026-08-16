"""Tests for explicit Firestore document layouts used by StayLong."""

from datetime import UTC, datetime


def test_case_schema_keeps_household_consent_and_approval_records_case_scoped() -> None:
    from staylong.services.firestore_schema import case_schema

    schema = case_schema(
        case_id="case-001",
        household_id="household-001",
        consent_contact_ids=("contact-alex",),
        approval_ids=("approval-001",),
        created_at=datetime(2026, 8, 16, tzinfo=UTC),
    )

    assert schema.collection_path == "cases/case-001"
    assert schema.document["household_id"] == "household-001"
    assert schema.document["consent_contact_ids"] == ["contact-alex"]
    assert schema.document["approval_ids"] == ["approval-001"]
    assert schema.document["created_at"] == datetime(2026, 8, 16, tzinfo=UTC)


def test_schema_paths_separate_household_consent_and_approvals_from_global_audit_events() -> None:
    from staylong.services.firestore_schema import collection_paths

    paths = collection_paths(case_id="case-001", household_id="household-001")

    assert paths == {
        "household": "households/household-001",
        "consents": "cases/case-001/consents",
        "approvals": "cases/case-001/approvals",
        "audit_events": "events",
    }

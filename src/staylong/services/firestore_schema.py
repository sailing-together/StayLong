"""Explicit Firestore document layouts for durable StayLong case state."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class CaseSchema:
    """A case document and its stable Firestore location."""

    collection_path: str
    document: dict[str, object]


def collection_paths(*, case_id: str, household_id: str) -> dict[str, str]:
    """Return the ownership-aware Firestore paths used by the workflow."""
    return {
        "household": f"households/{household_id}",
        "consents": f"cases/{case_id}/consents",
        "approvals": f"cases/{case_id}/approvals",
        "audit_events": "events",
    }


def case_schema(
    *,
    case_id: str,
    household_id: str,
    consent_contact_ids: Sequence[str],
    approval_ids: Sequence[str],
    created_at: datetime,
) -> CaseSchema:
    """Create the persistent case record without interpreting care needs."""
    return CaseSchema(
        collection_path=f"cases/{case_id}",
        document={
            "case_id": case_id,
            "household_id": household_id,
            "consent_contact_ids": list(consent_contact_ids),
            "approval_ids": list(approval_ids),
            "created_at": created_at,
        },
    )

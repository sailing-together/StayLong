"""Keep the seeded household fixture synthetic and contract-valid."""

import json
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).parents[2]


def test_seeded_household_matches_schema_and_contains_only_demo_identifiers() -> None:
    schema = json.loads((ROOT / "fixtures/demo/seeded-household.schema.json").read_text())
    fixture = json.loads((ROOT / "fixtures/demo/seeded-household.json").read_text())

    errors = sorted(Draft202012Validator(schema).iter_errors(fixture), key=lambda error: error.path)
    assert errors == []
    assert fixture["household"]["display_name"] == "Demo household"
    assert all(
        contact["display_name"].startswith("Demo ")
        for contact in fixture["household"]["contacts"]
    )
    assert fixture["household"]["consent"]["external_actions"] == "approval-required"
    assert "diagnosis" not in json.dumps(fixture).casefold()
    assert "password" not in json.dumps(fixture).casefold()

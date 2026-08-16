"""Run deterministic safety fixtures against the bounded intake agent."""

import json
from dataclasses import dataclass
from pathlib import Path

from staylong.agents.intake import (
    EmergencyRouteRequired,
    IntakeAgent,
    IntakeSchemaError,
    MedicalTriageRefusalRequired,
)

_EXPECTED_ERRORS = {
    "emergency_route": EmergencyRouteRequired,
    "medical_triage_refusal": MedicalTriageRefusalRequired,
    "schema_rejection": IntakeSchemaError,
}


@dataclass(frozen=True, slots=True)
class FixtureResult:
    """One stable evaluation result suitable for CI logs."""

    fixture_id: str
    passed: bool
    observed: str


class _FixtureProvider:
    def __init__(self, response: object) -> None:
        self.response = response
        self.call_count = 0

    def generate_json(self, *, system_instruction: str, prompt: str) -> object:
        self.call_count += 1
        return self.response


def run_fixtures(path: Path) -> tuple[FixtureResult, ...]:
    """Evaluate every committed fixture with a fresh provider and intake agent."""
    fixtures = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(fixtures, list):
        raise ValueError("Policy fixture file must contain a JSON list.")

    results: list[FixtureResult] = []
    for fixture in fixtures:
        if not isinstance(fixture, dict):
            raise ValueError("Each policy fixture must be a JSON object.")
        fixture_id = fixture["id"]
        expected_name = fixture["expected_error"]
        expected_error = _EXPECTED_ERRORS[expected_name]
        provider = _FixtureProvider(fixture.get("response", {}))
        try:
            IntakeAgent(provider=provider).intake(fixture["concern"])
        except expected_error as error:
            results.append(FixtureResult(fixture_id, True, type(error).__name__))
        except Exception as error:  # pragma: no cover - reported as a failed fixture
            results.append(FixtureResult(fixture_id, False, type(error).__name__))
        else:
            results.append(FixtureResult(fixture_id, False, "no_error"))

        if expected_name in {"emergency_route", "medical_triage_refusal"}:
            if provider.call_count != 0:
                results[-1] = FixtureResult(fixture_id, False, "model_called")
    return tuple(results)


def format_results(results: tuple[FixtureResult, ...]) -> str:
    """Render stable machine-readable output for local runs and GitHub Actions."""
    return json.dumps(
        [
            {"fixture_id": item.fixture_id, "passed": item.passed, "observed": item.observed}
            for item in results
        ],
        indent=2,
        sort_keys=True,
    )

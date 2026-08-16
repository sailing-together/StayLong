"""Regression tests for committed policy attack and failure fixtures."""

from pathlib import Path

from staylong.evaluations.policy import run_fixtures


def test_all_policy_fixtures_pass_repeatably() -> None:
    fixture_path = Path(__file__).parents[2] / "fixtures" / "policy" / "intake-policy.json"

    first = run_fixtures(fixture_path)
    second = run_fixtures(fixture_path)

    assert first == second
    assert all(result.passed for result in first)

"""CLI entry point for repeatable policy fixture evaluation."""

import sys
from pathlib import Path

from staylong.evaluations.policy import format_results, run_fixtures


def main() -> int:
    fixture_path = Path(__file__).parents[1] / "fixtures" / "policy" / "intake-policy.json"
    results = run_fixtures(fixture_path)
    print(format_results(results))
    return 0 if all(result.passed for result in results) else 1


if __name__ == "__main__":
    sys.exit(main())

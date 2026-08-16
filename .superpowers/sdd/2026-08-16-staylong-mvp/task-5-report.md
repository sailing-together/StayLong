# Task 5 report: ADK intake and coordination agents

## Scope and choices

- Added prompt constants that implement the shared, intake, and coordination
  contracts in `docs/agent-prompts.md`.
- Added a typed `StructuredModelProvider` boundary and an `IntakeOutput` schema.
  Unit tests inject a local provider and need no Google credentials, network, or
  model execution.
- `IntakeAgent` runs the existing deterministic emergency router before it asks
  a provider anything. A red-flag concern raises `EmergencyRouteRequired` with
  the Triple Zero (000) route and cannot reach the model adapter.
- Added lazy Google ADK factories with the `gemini-3.5-pro` Vertex model
  configuration. `google-adk` is an optional production dependency; its import
  is deliberately deferred so local contract tests remain offline.
- Added deterministic `CoordinationAgent` output. It has no tool interface;
  absent, expired, or mismatched approval produces a non-executable draft.
  Even a matching approval is only surfaced as `approved_action`; a downstream
  integration must still use `execute_approved_tool_action` at the side-effect
  boundary.

No external action, clinical assessment, recommendation, eligibility decision,
government submission, credential, or emergency-router change was introduced.

## TDD evidence

1. Added the intake and coordinator contract tests before the `staylong.agents`
   package existed. RED:

   ```text
   .venv/bin/pytest tests/agents/test_intake.py tests/agents/test_coordinator.py -q
   6 failed: ModuleNotFoundError: No module named 'staylong.agents'
   ```

2. Implemented the smallest schema, provider injection, deterministic emergency
   boundary, prompt constants, ADK factories, and approval-bounded coordinator.
   GREEN:

   ```text
   .venv/bin/pytest tests/agents/test_intake.py tests/agents/test_coordinator.py -q
   6 passed in 0.01s
   ```

3. Refactored prompt formatting to satisfy the repository lint policy and
   reran the focused and full checks.

## Final verification

```text
.venv/bin/python -m pytest tests/agents/test_intake.py tests/agents/test_coordinator.py -q
6 passed in 0.01s

.venv/bin/python -m pytest -q
32 passed in 0.02s

.venv/bin/python -m ruff check src tests
All checks passed!

git diff --check
exit 0 (no whitespace errors)
```

`python -m pytest` is intentional: invoking the `pytest` script directly does
not put the checkout root first on `sys.path` in this environment, so the
existing service tests cannot import their `tests.services` helper.

## Files

- `src/staylong/agents/__init__.py`
- `src/staylong/agents/prompts.py`
- `src/staylong/agents/intake.py`
- `src/staylong/agents/coordinator.py`
- `tests/agents/test_intake.py`
- `tests/agents/test_coordinator.py`
- `pyproject.toml`

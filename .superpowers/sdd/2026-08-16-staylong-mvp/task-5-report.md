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

## Re-review remediation

### Changes

- Restricted the `gemini-3.6-flash` inference endpoint to
  `GOOGLE_CLOUD_LOCATION=global`. Cloud Run remains in
  `australia-southeast1`, but that service region cannot be used as the Gemini
  model location.
- Made `VertexRuntimeConfig` enforce the global endpoint whether it is created
  from the environment or constructed directly.
- Bound the validated project, location, and Vertex-mode values to the actual
  environment consumed by Google ADK immediately before constructing its
  `Gemini` model. The ADK factory no longer discards configuration and supplies
  `tools=[]` explicitly.
- Made the ADK response provider and raw ADK agent private implementation
  details. `IntakeAgent` has a private provider, so its public path is
  `intake()`, which always runs deterministic emergency routing and schema
  validation first.
- Added a controlled ADK module-loading seam for production-factory tests. The
  tests use fake `Agent`/`Gemini` classes to prove effective Vertex runtime
  values and empty tools without installing or calling Google ADK.

### TDD evidence

1. Added tests for global-only inference, private provider visibility, and
   effective ADK configuration. RED:

   ```text
   .venv/bin/python -m pytest tests/agents/test_vertex_factories.py -q
   3 failed: non-global location accepted, public provider exposed, and missing
   ADK module seam
   ```

2. Implemented runtime binding, the private provider, the controlled ADK
   loader, and no-tools configuration. GREEN:

   ```text
   10 passed in 0.01s
   ```

3. Added a direct `VertexRuntimeConfig(location="australia-southeast1")`
   regression test before closing the constructor bypass. RED:

   ```text
   1 failed: DID NOT RAISE VertexConfigurationError
   ```

4. Added constructor validation and reran focused checks.

### Final re-review verification

```text
.venv/bin/python -m pytest tests/agents/test_vertex_factories.py tests/agents/test_intake.py tests/agents/test_coordinator.py -q
10 passed in 0.01s

.venv/bin/python -m pytest -q
36 passed in 0.02s

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

## Review-finding remediation

### Changes

- Replaced the unavailable `gemini-3.5-pro` identifier with the current
  competition-compatible Flash default, `gemini-3.6-flash`.
- Added `VertexRuntimeConfig`, which requires and validates
  `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`, and
  `GOOGLE_GENAI_USE_VERTEXAI=true` before ADK construction. The runtime
  requirements are documented in `docs/technology-and-compliance.md`.
- Replaced the prompt-only ADK factory returns with bounded application
  wrappers. The intake factory requires an injected ADK Runner JSON executor,
  then routes every request through deterministic emergency routing and
  `IntakeOutput` schema validation. The coordinator factory returns only the
  policy-bounded coordinator, so absent/stale approval remains a draft and no
  raw ADK object is exposed as an action bypass.
- Updated the optional dependency to `google-adk[gcp]>=2.0.0,<3.0.0`, matching
  the Google ADK Vertex runtime extra.

### TDD evidence

1. Added factory-contract tests before the Vertex configuration module and
   wrapper factory interfaces existed. RED:

   ```text
   .venv/bin/python -m pytest tests/agents/test_vertex_factories.py -q
   3 failed: missing staylong.agents.vertex and unexpected factory arguments
   ```

2. Added validated runtime configuration, injectable ADK constructor/executor
   boundaries, and wrapper factories. GREEN:

   ```text
   9 passed in 0.01s (factory, intake, and coordinator contracts)
   ```

3. Changed the factory expectation to the current valid Flash model identifier
   before changing production configuration. RED:

   ```text
   2 failed: gemini-3-flash-preview != gemini-3.6-flash
   ```

4. Set `VERTEX_GEMINI_MODEL` to `gemini-3.6-flash`, then reran the focused,
   full, lint, and whitespace checks.

### Final remediation verification

```text
.venv/bin/python -m pytest tests/agents/test_vertex_factories.py tests/agents/test_intake.py tests/agents/test_coordinator.py -q
9 passed in 0.01s

.venv/bin/python -m pytest -q
35 passed in 0.02s

.venv/bin/python -m ruff check src tests
All checks passed!

git diff --check
exit 0 (no whitespace errors)
```

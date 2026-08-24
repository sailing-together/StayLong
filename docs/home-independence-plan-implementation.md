# Home Independence Plan Implementation Plan

> **For agentic workers:** Use task-by-task development with tests written before production code. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the reminder-only outcome with a durable, approval-governed Home Independence Plan containing useful tasks, a Calendar action and an unsent contact draft.

**Architecture:** Keep the existing deterministic Taskmaster state machine as the authority for state and consent. Add typed plan and action collections to the workflow snapshot, adapter protocols for Calendar and contact drafts, and a UI that renders the durable plan rather than a single reminder. Production Google adapters remain opt-in through OAuth configuration; sandbox adapters make the same contracts demonstrable locally.

**Tech Stack:** Python 3.12, FastAPI, Pydantic, Google ADK/Vertex AI, Firestore, React 19, TypeScript, Vitest, pytest.

**Spec:** `docs/home-independence-plan-design.md`

## Global constraints

- The emergency route stays deterministic and produces no plan or actions.
- No source file contains OAuth secrets, tokens, recipient details, or real household data.
- Calendar creation and contact-draft creation require separate, matching approvals.
- A contact draft is never sent by the product.
- Each approved action is idempotent by case, action type and revision.
- The UI must expose sandbox or unavailable integration state honestly.

---

### Task 1: Model and persist the Home Independence Plan

**Files:**

- Create: `src/staylong/services/home_plan.py`
- Modify: `src/staylong/services/taskmaster.py`
- Modify: `tests/services/test_taskmaster.py`

**Interfaces:**

- Produces `PlanTask`, `HomeIndependencePlan`, and `build_home_independence_plan(pack, now)`.
- Extends `WorkflowSnapshot` with `plan: HomeIndependencePlan | None`.

- [ ] **Step 1: Write failing service tests**

```python
def test_answered_intake_builds_three_actionable_plan_tasks() -> None:
    _, prepared = _prepared_workflow()
    assert prepared.plan is not None
    assert [task.title for task in prepared.plan.tasks] == [
        "Arrange a My Aged Care assessment",
        "Prepare your assessment notes",
        "Confirm home access or permission",
    ]
    assert {task.status for task in prepared.plan.tasks} == {"ready"}

def test_emergency_route_does_not_create_a_home_plan() -> None:
    snapshot = _workflow().start(concern="I am unconscious", now=NOW)
    assert snapshot.plan is None
```

- [ ] **Step 2: Run the new tests and verify the first fails because `plan` is absent**

Run: `uv run pytest tests/services/test_taskmaster.py -q`

- [ ] **Step 3: Implement the smallest typed plan factory**

```python
@dataclass(frozen=True, slots=True)
class PlanTask:
    task_id: str
    title: str
    description: str
    owner: str
    due_at: datetime
    status: Literal["ready", "blocked", "completed"]
    blocker: str | None = None

def build_home_independence_plan(
    pack: AssessmentPreparationPack, now: datetime
) -> HomeIndependencePlan:
    return HomeIndependencePlan(...)
```

- [ ] **Step 4: Set the plan when fact collection finishes and preserve it in every snapshot transition**

- [ ] **Step 5: Re-run the service test file and commit**

Run: `uv run pytest tests/services/test_taskmaster.py -q`

Commit: `feat(plan): create durable home independence plan`

### Task 2: Support separate Calendar and contact-draft approvals

**Files:**

- Modify: `src/staylong/services/channels.py`
- Modify: `src/staylong/services/taskmaster.py`
- Modify: `tests/services/test_channel_adapters.py`
- Modify: `tests/services/test_taskmaster.py`

**Interfaces:**

- Produces `CalendarAdapter`, `ContactDraftAdapter`, `CalendarSandboxAdapter`, and `ContactDraftSandboxAdapter`.
- Replaces singular `proposed_action` and `action_result` with typed action collections while temporarily retaining compatibility accessors.
- Adds `decide_action(case_id, action_type, action_revision, approve, now)`.

- [ ] **Step 1: Write failing approval-isolation tests**

```python
def test_approving_calendar_does_not_create_contact_draft() -> None:
    workflow, prepared = _prepared_workflow()
    result = workflow.decide_action(
        case_id=prepared.case_id,
        action_type="calendar.create",
        action_revision=1,
        approve=True,
        now=NOW,
    )
    assert result.action_result_for("calendar.create") is not None
    assert result.action_result_for("contact_draft.create") is None

def test_duplicate_calendar_approval_returns_the_original_result() -> None:
    # approve the same revision twice
    assert len(workflow.calendar.sent_items) == 1
```

- [ ] **Step 2: Run tests and verify they fail because the named-action interface is absent**

Run: `uv run pytest tests/services/test_taskmaster.py tests/services/test_channel_adapters.py -q`

- [ ] **Step 3: Implement adapters that create only local, visibly sandboxed records**

```python
class ContactDraftSandboxAdapter:
    action_type = "contact_draft.create"

    def create_draft(self, *, case_id: str, revision: int,
                     approval: ActionApproval | None, now: datetime,
                     details: MessageDetails) -> DemoDispatchResult:
        ...
```

- [ ] **Step 4: Generate two versioned proposals and execute one exact approved action at a time**

- [ ] **Step 5: Record `calendar.created`, `contact_draft.created` and `action.blocked` events, then re-run tests and commit**

Run: `uv run pytest tests/services/test_taskmaster.py tests/services/test_channel_adapters.py -q`

Commit: `feat(actions): separate approved plan actions`

### Task 3: Round-trip plans and action collections through Firestore and FastAPI

**Files:**

- Modify: `src/staylong/services/taskmaster.py`
- Modify: `src/staylong/api/app.py`
- Modify: `tests/services/test_taskmaster.py`
- Modify: `tests/api/test_taskmaster_api.py`

**Interfaces:**

- `GET /v1/workflows/{case_id}` returns `plan`, `proposed_actions`, `action_results`, and timeline.
- `POST /v1/workflows/{case_id}/action-decision` accepts `action_type`, `action_revision`, and `decision`.

- [ ] **Step 1: Write failing API and Firestore round-trip tests**

```python
def test_api_returns_plan_and_two_independent_proposals() -> None:
    prepared = _prepared_response()
    assert len(prepared.json()["plan"]["tasks"]) == 3
    assert {item["action_type"] for item in prepared.json()["proposed_actions"]} == {
        "calendar.create", "contact_draft.create",
    }

def test_firestore_round_trip_preserves_plan_actions_and_results() -> None:
    assert reloaded.plan == completed.plan
    assert reloaded.proposed_actions == completed.proposed_actions
```

- [ ] **Step 2: Run tests and verify contract failures**

Run: `uv run pytest tests/api/test_taskmaster_api.py tests/services/test_taskmaster.py -q`

- [ ] **Step 3: Add Pydantic response models and named-action validation**

- [ ] **Step 4: Extend Firestore serializers without dropping legacy snapshot data**

- [ ] **Step 5: Run backend tests and commit**

Run: `uv run pytest tests/api/test_taskmaster_api.py tests/services/test_taskmaster.py -q`

Commit: `feat(api): expose durable home plan actions`

### Task 4: Add optional Google integration configuration and safe fallback

**Files:**

- Create: `src/staylong/services/google_actions.py`
- Modify: `src/staylong/api/runtime.py`
- Modify: `pyproject.toml`
- Modify: `docs/technology-and-compliance.md`
- Test: `tests/services/test_google_actions.py`
- Test: `tests/api/test_runtime_wiring.py`

**Interfaces:**

- Produces `GoogleActionConfig.from_environment(values)` and `build_action_adapters(values)`.
- Configured production Calendar adapter creates a user-authorised event; configured Gmail adapter creates a draft only.
- Unconfigured runtime returns sandbox adapters labelled `sandbox`, never a fake Google success.

- [x] **Step 1: Write failing configuration tests**

```python
def test_missing_google_oauth_configuration_selects_sandbox_adapters() -> None:
    adapters = build_action_adapters({})
    assert adapters.calendar.integration_mode == "sandbox"

def test_google_adapter_requires_an_approved_action_before_api_call() -> None:
    with pytest.raises(ApprovalRequired):
        adapter.create_event(..., approval=None, ...)
```

- [x] **Step 2: Run tests and verify missing configuration factory**

Run: `uv run pytest tests/services/test_google_actions.py tests/api/test_runtime_wiring.py -q`

- [x] **Step 3: Implement configuration parsing and adapter factory; keep OAuth tokens outside Firestore and logs**

- [x] **Step 4: Add a narrow Google Calendar/Gmail draft dependency only if the adapter test needs it**

- [x] **Step 5: Update deployment documentation with required manual OAuth consent and re-run tests**

Run: `uv run pytest tests/services/test_google_actions.py tests/api/test_runtime_wiring.py -q`

Commit: `feat(integrations): add approval-gated Google action boundary`

### Task 5: Build the Home Independence Plan task-board experience

**Files:**

- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/App.css`
- Modify: `frontend/src/App.test.tsx`

**Interfaces:**

- Consumes the API workflow response from Task 3.
- Renders `Home Independence Plan`, three tasks, action cards, explicit integration mode, and action history.

- [ ] **Step 1: Write failing UI tests for the meaningful outcome**

```tsx
it('shows three concrete plan tasks after intake', async () => {
  render(<App />)
  await completeIntake()
  expect(await screen.findByRole('heading', { name: 'Your Home Independence Plan' })).toBeVisible()
  expect(screen.getByText('Arrange a My Aged Care assessment')).toBeVisible()
  expect(screen.getByText('Prepare your assessment notes')).toBeVisible()
})

it('approves only the calendar action and keeps the contact draft pending', async () => {
  await user.click(screen.getByRole('button', { name: 'Add assessment reminder to calendar' }))
  expect(screen.getByText('Calendar event created in sandbox')).toBeVisible()
  expect(screen.getByText('Contact draft waiting for approval')).toBeVisible()
})
```

- [ ] **Step 2: Run the targeted tests and verify the plan board does not yet exist**

Run: `npm test -- --run src/App.test.tsx`

- [ ] **Step 3: Implement typed client models, named-action requests, task cards and status announcements**

- [ ] **Step 4: Keep boundaries concise and make the result of each agent action primary content**

- [ ] **Step 5: Run UI tests, production build and commit**

Run: `npm test -- --run src/App.test.tsx && npm run build`

Commit: `feat(ui): show home independence plan actions`

### Task 6: Verify the workflow, deployment configuration and demo evidence

**Files:**

- Modify: `docs/demo-scenario.md`
- Modify: `docs/product-brief.md`
- Modify: `docs/release-evidence.md`
- Test: `tests/api/test_taskmaster_api.py`
- Test: `tests/services/test_taskmaster.py`

**Interfaces:**

- Demo accepts the existing night-time bathroom concern and shows one completed Calendar action plus one still-pending contact draft.

- [ ] **Step 1: Add a failing end-to-end API test that asserts the full durable state after a restart**

```python
def test_reloaded_plan_keeps_calendar_complete_and_contact_draft_pending() -> None:
    snapshot = _reload_after_calendar_approval()
    assert snapshot.action_result_for("calendar.create") is not None
    assert snapshot.action_result_for("contact_draft.create") is None
```

- [ ] **Step 2: Run the test and verify it fails before full workflow support**

Run: `uv run pytest tests/api/test_taskmaster_api.py -q`

- [ ] **Step 3: Update the demo script and product brief to describe the implemented, not aspirational, behavior**

- [ ] **Step 4: Run the complete quality suite**

Run: `uv run pytest -q && (cd frontend && npm test && npm run build)`

- [ ] **Step 5: Perform an authenticated local workflow replay and record its evidence without real household data**

- [ ] **Step 6: Commit docs and evidence**

Commit: `docs: demonstrate home independence workflow`

## Plan review

- [ ] All requirements in `docs/home-independence-plan-design.md` map to Tasks 1–6.
- [ ] Tests are written before each production change.
- [ ] Calendar and contact actions remain independently approval-gated and idempotent.
- [ ] OAuth setup is documented as a manual user-controlled step.

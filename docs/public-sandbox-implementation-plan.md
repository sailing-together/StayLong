# StayLong Public Sandbox Implementation Plan

> **For implementation workers:** Execute one checked task at a time. Each task starts with a failing test, makes the smallest safe implementation, runs focused verification, then commits independently.

**Goal:** Release a publicly accessible StayLong sandbox URL with anonymous temporary sessions, isolated Firestore case access and sandbox-only actions.

**Architecture:** A dedicated Cloud Run service runs the normal Vertex AI/ADK and Firestore workflow behind a separate public-sandbox API boundary. An opaque HttpOnly session cookie becomes a one-way ownership key; each workflow case belongs to exactly one active session and expires after a bounded retention period. Terraform owns the isolated service, runtime identity, public invoker policy and cleanup trigger; the private service remains private.

**Tech Stack:** Python 3.12, FastAPI, Pydantic, Google ADK, Vertex AI, Firestore, Cloud Run, Cloud Scheduler, Terraform, GitHub Actions WIF, React, TypeScript, Vitest and pytest.

**Spec:** [public-sandbox-design.md](public-sandbox-design.md)

## Global constraints

- Public sandbox data is non-clinical, temporary and synthetic/demo-only.
- Public actions use sandbox adapters only; OAuth, Calendar, Gmail, provider contact and payments are prohibited.
- The raw session token and private API token are never logged, returned in JSON, stored in Firestore or exposed to the frontend.
- The private Cloud Run service, bearer-token API contract and IAM policy remain unchanged.
- Terraform owns all cloud resources and lifecycle actions; GitHub Actions uses WIF only.

---

### Task 1: Define public-session ownership primitives

**Files:**

- Create: src/staylong/services/public_sessions.py
- Create: tests/services/test_public_sessions.py

**Interfaces:**

- PublicSession(token: str, owner_key: str, expires_at: datetime)
- new_public_session(secret: str, now: datetime, lifetime: timedelta) -> PublicSession
- owner_key_for(token: str, secret: str) -> str
- PublicCaseAccessRepository.claim, assert_owner and delete_expired

- [ ] **Step 1: Write failing unit tests**

~~~python
def test_owner_key_is_stable_but_does_not_contain_the_raw_cookie_token() -> None:
    session = new_public_session(secret="test-secret", now=NOW, lifetime=timedelta(hours=24))
    assert owner_key_for(session.token, "test-secret") == session.owner_key
    assert session.token not in session.owner_key

def test_case_access_rejects_a_different_or_expired_session() -> None:
    repository = InMemoryPublicCaseAccessRepository()
    repository.claim(case_id="case-1", owner_key="one", expires_at=FUTURE)
    with pytest.raises(PublicCaseAccessDenied):
        repository.assert_owner(case_id="case-1", owner_key="two", now=NOW)
~~~

- [ ] **Step 2: Run RED**

Run: uv run pytest tests/services/test_public_sessions.py -q

Expected: FAIL because the public-session module does not exist.

- [ ] **Step 3: Implement minimal primitives**

~~~python
def owner_key_for(token: str, secret: str) -> str:
    return hmac.new(secret.encode(), token.encode(), hashlib.sha256).hexdigest()

def new_public_session(*, secret: str, now: datetime, lifetime: timedelta) -> PublicSession:
    token = secrets.token_urlsafe(32)
    return PublicSession(token=token, owner_key=owner_key_for(token, secret), expires_at=now + lifetime)
~~~

Implement PublicCaseAccessDenied and reject unknown and expired ownership
records with the same error type.

- [ ] **Step 4: Run GREEN**

Run: uv run pytest tests/services/test_public_sessions.py -q

Expected: PASS.

- [ ] **Step 5: Commit**

~~~bash
git add src/staylong/services/public_sessions.py tests/services/test_public_sessions.py
git commit -m "feat: add public sandbox session ownership"
~~~

### Task 2: Persist ownership and expiry in Firestore

**Files:**

- Modify: src/staylong/services/public_sessions.py
- Modify: src/staylong/services/firestore_schema.py
- Create: tests/services/test_public_session_firestore.py

**Interfaces:**

- FirestorePublicCaseAccessRepository implements Task 1's protocol.
- Access mappings use public_sandbox_cases/{case_id}.
- Mapping fields are owner_key, expires_at, created_at and environment=public-sandbox.
- delete_expired(now) returns deleted case IDs for workflow/event cleanup.

- [ ] **Step 1: Write failing Firestore-contract tests**

~~~python
def test_firestore_access_document_contains_no_raw_session_token() -> None:
    document = public_case_access_document(
        case_id="case-1", owner_key="hashed-owner", expires_at=FUTURE, created_at=NOW,
    )
    assert document["owner_key"] == "hashed-owner"
    assert "token" not in document
    assert document["environment"] == "public-sandbox"
~~~

- [ ] **Step 2: Run RED**

Run: uv run pytest tests/services/test_public_session_firestore.py -q

Expected: FAIL because no Firestore serialization contract exists.

- [ ] **Step 3: Implement Firestore persistence**

Keep public access mapping out of household and consent documents. Query only
expired public-sandbox mappings, check both owner equality and expiry before
returning access, and store no raw cookie value.

- [ ] **Step 4: Run GREEN**

Run: uv run pytest tests/services/test_public_session_firestore.py -q

Expected: PASS.

- [ ] **Step 5: Commit**

~~~bash
git add src/staylong/services/public_sessions.py src/staylong/services/firestore_schema.py tests/services/test_public_session_firestore.py
git commit -m "feat: persist public sandbox case ownership"
~~~

### Task 3: Add the public FastAPI session boundary

**Files:**

- Modify: src/staylong/api/app.py
- Modify: src/staylong/api/main.py
- Create: tests/api/test_public_sandbox_api.py

**Interfaces:**

- create_app receives an explicit PublicSandboxConfig object.
- Public routes use the staylong_public_session cookie; private routes retain require_auth.
- A public workflow is claimed by its session immediately after TaskmasterWorkflow.start.
- Answers and action decisions assert ownership before workflow execution.

- [ ] **Step 1: Write failing API tests**

~~~python
def test_public_workflow_sets_an_httponly_session_cookie_and_needs_no_bearer_token(client) -> None:
    response = client.post("/v1/public/workflows", json={"concern": "Bathroom access is difficult at night."})
    assert response.status_code == 201
    assert "staylong_public_session" in response.headers["set-cookie"]
    assert "HttpOnly" in response.headers["set-cookie"]

def test_second_public_session_cannot_mutate_the_first_sessions_case(client) -> None:
    first = client.post("/v1/public/workflows", json={"concern": "Night bathroom access."})
    other_browser = TestClient(client.app)
    response = other_browser.post(f"/v1/public/workflows/{first.json()['case_id']}/answers", json={"answers": {}})
    assert response.status_code == 404

def test_private_workflow_route_still_requires_bearer_authentication(client) -> None:
    assert client.post("/v1/workflows", json={"concern": "Night bathroom access."}).status_code == 401
~~~

- [ ] **Step 2: Run RED**

Run: uv run pytest tests/api/test_public_sandbox_api.py -q

Expected: FAIL because public endpoints and cookie handling do not exist.

- [ ] **Step 3: Implement isolated public routes**

Add public create, answer and action-decision routes under /v1/public. Set the
cookie as Secure, HttpOnly and SameSite=Lax with matching expiry. Return a
generic 404 for unknown, foreign and expired cases. Do not weaken private
bearer authentication.

- [ ] **Step 4: Run GREEN**

Run: uv run pytest tests/api/test_public_sandbox_api.py tests/api/test_app.py tests/api/test_taskmaster_api.py -q

Expected: PASS, including private-authentication coverage.

- [ ] **Step 5: Commit**

~~~bash
git add src/staylong/api/app.py src/staylong/api/main.py tests/api/test_public_sandbox_api.py
git commit -m "feat: add anonymous public sandbox API"
~~~

### Task 4: Limit anonymous use and clean up expired cases

**Files:**

- Modify: src/staylong/services/public_sessions.py
- Modify: src/staylong/services/taskmaster.py
- Modify: src/staylong/api/app.py
- Create: tests/api/test_public_sandbox_cleanup.py

**Interfaces:**

- PublicSandboxConfig includes a 24-hour session lifetime and a
  `max_cases_per_session` default of 2.
- cleanup_expired_public_cases(now) deletes access mapping, workflow snapshot and event timeline.
- POST /internal/public-sandbox/cleanup accepts only a Cloud Scheduler OIDC request.
- Lifecycle telemetry emits event names and counts only; concern text and
  credentials are prohibited from telemetry payloads.

- [ ] **Step 1: Write failing limit and cleanup tests**

~~~python
def test_public_session_cannot_create_more_than_the_configured_case_limit(client) -> None:
    for _ in range(2):
        assert client.post("/v1/public/workflows", json={"concern": "Night bathroom access."}).status_code == 201
    response = client.post("/v1/public/workflows", json={"concern": "Night bathroom access."})
    assert response.status_code == 429

def test_cleanup_deletes_expired_access_and_workflow_records() -> None:
    assert cleanup_expired_public_cases(now=NOW) == ("expired-case",)
    assert workflow_repository.load("expired-case") is None
~~~

- [ ] **Step 2: Run RED**

Run: uv run pytest tests/api/test_public_sandbox_cleanup.py -q

Expected: FAIL because limits and cleanup do not exist.

- [ ] **Step 3: Implement limits and protected cleanup**

Enforce the two-case limit server-side before calling Vertex. Delete mapping,
snapshot and event records idempotently after the 24-hour retention period.
The cleanup endpoint rejects anonymous calls and is invoked only by the
dedicated scheduler identity. Record only aggregate lifecycle event names and
counts, never concern text or session credentials.

- [ ] **Step 4: Run GREEN**

Run: uv run pytest tests/api/test_public_sandbox_cleanup.py -q

Expected: PASS.

- [ ] **Step 5: Commit**

~~~bash
git add src/staylong/services/public_sessions.py src/staylong/services/taskmaster.py src/staylong/api/app.py tests/api/test_public_sandbox_cleanup.py
git commit -m "feat: expire public sandbox cases"
~~~

### Task 5: Expose the public sandbox in React

**Files:**

- Modify: frontend/src/App.tsx
- Modify: frontend/src/App.test.tsx
- Modify: frontend/src/App.css

**Interfaces:**

- VITE_STAYLONG_API_MODE=public-sandbox selects /v1/public and credentials: include.
- The page displays: Public sandbox — temporary data, no real bookings or messages.
- The integration label uses workflow.integration_mode rather than hard-coded text.

- [ ] **Step 1: Write failing frontend tests**

~~~tsx
it("uses the public endpoint with credentials and names the public sandbox boundary", async () => {
  render(<App />)
  await user.click(screen.getByRole("button", { name: "Start my plan" }))
  expect(fetchMock).toHaveBeenCalledWith("/v1/public/workflows", expect.objectContaining({ credentials: "include" }))
  expect(screen.getByText("Public sandbox — temporary data, no real bookings or messages.")).toBeVisible()
})

it("labels a connected integration only when the workflow reports google_oauth", () => {
  renderPreparedWorkflow({ integration_mode: "google_oauth" })
  expect(screen.getByText("Connected Google actions")).toBeVisible()
})
~~~

- [ ] **Step 2: Run RED**

Run: npm --prefix frontend test -- App.test.tsx

Expected: FAIL because public mode and live integration labels are missing.

- [ ] **Step 3: Implement minimal public mode**

Keep private API mode intact. Public requests include cookie credentials and
never read a token. Add clear temporary-data and no-real-actions copy using
the existing accessible visual system.

- [ ] **Step 4: Run GREEN**

Run: npm --prefix frontend test -- App.test.tsx && npm --prefix frontend run lint && npm --prefix frontend run build

Expected: PASS.

- [ ] **Step 5: Commit**

~~~bash
git add frontend/src/App.tsx frontend/src/App.test.tsx frontend/src/App.css
git commit -m "feat: expose public sandbox experience"
~~~

### Task 6: Provision public-sandbox with Terraform

**Files:**

- Create: infra/terraform/components/public-sandbox/main.tf
- Create: infra/terraform/components/public-sandbox/outputs.tf
- Create: infra/terraform/components/public-sandbox/variables.tf
- Create: infra/terraform/components/public-sandbox/versions.tf
- Create: infra/terraform/projects/config/staylong-public-sandbox.json
- Modify: infra/terraform/projects/config/schemas/project.schema.json
- Create: tests/infra/test_public_sandbox_component.py

**Interfaces:**

- Inputs are project_config=staylong-public-sandbox.json and environment_config=sandbox.json.
- Outputs are public_url, service_name and cleanup_scheduler_job.
- Runtime environment includes STAYLONG_PUBLIC_SANDBOX=true and STAYLONG_GOOGLE_ACTIONS_MODE=sandbox, but no private API token.

- [ ] **Step 1: Write failing infrastructure tests**

~~~python
def test_public_sandbox_is_dedicated_and_has_no_private_api_token() -> None:
    source = COMPONENT.read_text()
    assert 'name = "staylong-public-sandbox"' in source
    assert 'member   = "allUsers"' in source
    assert 'STAYLONG_GOOGLE_ACTIONS_MODE' in source
    assert 'value = "sandbox"' in source
    assert 'STAYLONG_API_TOKEN' not in source

def test_public_sandbox_schedules_authenticated_cleanup() -> None:
    source = COMPONENT.read_text()
    assert "google_cloud_scheduler_job" in source
    assert "/internal/public-sandbox/cleanup" in source
~~~

- [ ] **Step 2: Run RED**

Run: uv run pytest tests/infra/test_public_sandbox_component.py -q

Expected: FAIL because the component does not exist.

- [ ] **Step 3: Implement Terraform component**

Use existing modules where possible. Give its dedicated runtime identity only
Vertex, Firestore, Logging and scheduler-invoker access required by this
design. Create a separate session-HMAC Secret Manager secret; never reuse the
private API token. Use Cloud Scheduler OIDC to invoke cleanup. Configure
scale-to-zero and a conservative maximum instance count.

- [ ] **Step 4: Run GREEN**

Run: uv run pytest tests/infra/test_public_sandbox_component.py -q && terraform -chdir=infra/terraform fmt -check -recursive && terraform -chdir=infra/terraform/components/public-sandbox init -backend=false && terraform -chdir=infra/terraform/components/public-sandbox validate

Expected: PASS.

- [ ] **Step 5: Commit**

~~~bash
git add infra/terraform tests/infra/test_public_sandbox_component.py
git commit -m "feat: provision public StayLong sandbox"
~~~

### Task 7: Add deploy, teardown and public end-to-end evidence

**Files:**

- Modify: .github/workflows/terraform.yml
- Modify: .github/workflows/deploy.yml or create .github/workflows/public-sandbox.yml
- Modify: .github/workflows/tests.yml
- Modify: README.md
- Modify: docs/release-evidence.md
- Create: tools/public_sandbox_smoke.py
- Create: tests/tools/test_public_sandbox_smoke.py

**Interfaces:**

- Manual workflows support component=public-sandbox and explicit apply/destroy confirmation.
- Smoke script uses two cookie sessions to test isolation, reload continuity and a sandbox-only approved action.
- Documentation names the URL, retention policy, permitted demo data and teardown command.

- [ ] **Step 1: Write failing smoke-script test**

~~~python
def test_public_sandbox_smoke_never_requires_or_prints_an_api_token() -> None:
    source = Path("tools/public_sandbox_smoke.py").read_text()
    assert "STAYLONG_API_TOKEN" not in source
    assert "requests.Session()" in source
    assert "session_b" in source
~~~

- [ ] **Step 2: Run RED**

Run: uv run pytest tests/tools/test_public_sandbox_smoke.py -q

Expected: FAIL because the smoke script does not exist.

- [ ] **Step 3: Implement release controls and smoke script**

The smoke uses no auth header, verifies the cookie, creates a case in session A,
rejects case access from session B, approves a sandbox action and asserts a
sandbox result. The deployment outputs the generated URL. Teardown is manual,
explicit and scoped only to the public-sandbox component.

- [ ] **Step 4: Run complete local verification**

Run: uv run pytest -q && npm --prefix frontend test && npm --prefix frontend run lint && npm --prefix frontend run build && terraform -chdir=infra/terraform fmt -check -recursive

Expected: all suites PASS.

- [ ] **Step 5: Commit**

~~~bash
git add .github/workflows README.md docs/release-evidence.md tools tests/tools
git commit -m "feat: automate public sandbox release evidence"
~~~

## Plan self-review

- Spec coverage: Tasks 1–4 implement ownership, limits and expiry; Task 5 adds honest user-facing public mode; Tasks 6–7 provision, deploy, verify and tear down the isolated service.
- Private-boundary coverage: Tasks 3 and 6 preserve private auth and prohibit private-token reuse.
- Placeholder scan: the plan contains no unresolved work markers or deferred implementation steps.
- Type consistency: Task 1 repository protocol is implemented in Task 2, consumed in Task 3 and cleaned in Task 4; Terraform configuration from Task 6 is verified by Task 7.

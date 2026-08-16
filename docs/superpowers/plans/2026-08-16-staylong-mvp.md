# StayLong MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and deploy a safe, event-driven Taskmaster that coordinates one ageing-in-place concern from intake through human-approved follow-up.

**Architecture:** A Cloud Run Python service hosts the web/API surface and Google ADK coordinator. Firestore keeps household, approval and task state; Pub/Sub and Cloud Tasks dispatch event and scheduled work. Terraform provisions the platform, while GitHub Actions uses WIF for CI/CD without a long-lived cloud key.

**Tech Stack:** Python 3.12, Google ADK, Vertex AI Gemini 3.5+, Cloud Run, Firestore, Cloud Tasks, Pub/Sub, Terraform, GitHub Actions, pytest and Ruff.

## Global Constraints

- Use Gemini 3.5+ through Vertex AI and Google ADK.
- Keep all external side effects behind explicit approval records.
- Never implement medical diagnosis, OT prescriptions, AT-HM eligibility or government-form submission.
- Use synthetic data in development and the demo.
- Use GitHub OIDC Workload Identity Federation; do not store a GCP service-account key in GitHub.
- Keep all code and docs new for the submission period; disclose any incorporated pre-existing work.

---

## File structure

| Path | Responsibility |
|---|---|
| `src/staylong/domain/` | Typed case, task, approval and event models. |
| `src/staylong/policy/` | Deterministic red-flag and action-approval rules. |
| `src/staylong/agents/` | ADK intake, coordinator and escalation agents. |
| `src/staylong/tools/` | Typed, approval-aware integration adapters. |
| `src/staylong/services/` | Case orchestration and event dispatch. |
| `src/staylong/api/` | Cloud Run HTTP API. |
| `tests/` | Unit, contract and end-to-end tests. |
| `infra/terraform/` | GCP and WIF infrastructure. |

### Task 1: Establish the secure delivery foundation

**Files:** `.github/workflows/ci.yml`, `.github/workflows/terraform.yml`, `.github/workflows/deploy.yml`, `infra/terraform/*`, `pyproject.toml`, `tests/test_package.py`

- [ ] Run the package test and confirm it passes.
- [ ] Add CI for Ruff and pytest on pull requests and `main`.
- [ ] Provision Artifact Registry, Cloud Run prerequisites, runtime service account and GitHub WIF using Terraform.
- [ ] Run `terraform fmt -check` and `terraform validate` with configured variables.
- [ ] Create a WIF-authenticated manual Cloud Run deployment workflow.
- [ ] Commit the foundation as `chore: initialize staylong delivery foundation`.

### Task 2: Model cases, consent and approvals

**Files:** `src/staylong/domain/models.py`, `src/staylong/policy/approvals.py`, `tests/domain/test_models.py`, `tests/policy/test_approvals.py`

- [ ] Write tests for an authorised contact, concern, action approval and immutable timeline event.
- [ ] Implement typed models with stable IDs and timestamps.
- [ ] Write tests proving a tool action fails without a matching approval.
- [ ] Implement the approval policy and run the focused tests.
- [ ] Commit the domain and approval boundary.

### Task 3: Add deterministic emergency routing

**Files:** `src/staylong/policy/emergency.py`, `tests/policy/test_emergency.py`

- [ ] Write parameterized tests for configured emergency terms and non-emergency cases.
- [ ] Implement a deterministic classifier returning `emergency_route` or `normal_route`.
- [ ] Ensure the emergency route produces no LLM call and no delayed task.
- [ ] Run all policy tests and commit.

### Task 4: Implement Firestore-backed case state and events

**Files:** `src/staylong/services/cases.py`, `src/staylong/services/events.py`, `tests/services/test_cases.py`, `tests/services/test_events.py`

- [ ] Write tests for concern creation, idempotent event processing and timeline persistence.
- [ ] Implement repository interfaces plus an in-memory test adapter.
- [ ] Implement Firestore persistence behind the same interface.
- [ ] Run service tests and commit.

### Task 5: Implement ADK intake and coordination agents

**Files:** `src/staylong/agents/intake.py`, `src/staylong/agents/coordinator.py`, `src/staylong/agents/prompts.py`, `tests/agents/test_intake.py`, `tests/agents/test_coordinator.py`

- [ ] Write contract tests for structured intake output and approved-action-only coordination output.
- [ ] Implement the prompt contracts from `docs/agent-prompts.md` with schema validation.
- [ ] Implement a coordinator that produces drafts when approval is absent.
- [ ] Run agent contract tests and commit.

### Task 6: Add async reminders, escalation and demo tools

**Files:** `src/staylong/services/escalation.py`, `src/staylong/tools/calendar.py`, `src/staylong/tools/messaging.py`, `src/staylong/tools/resources.py`, `tests/services/test_escalation.py`, `tests/tools/test_adapters.py`

- [ ] Write tests for overdue reminder, backup-contact escalation and no-contact-without-approval.
- [ ] Implement Cloud Tasks/Pub/Sub adapters and local fakes.
- [ ] Implement approved draft calendar, messaging and official-resource adapters.
- [ ] Run tests and commit.

### Task 7: Deliver the Cloud Run UI/API and end-to-end demo path

**Files:** `src/staylong/api/app.py`, `src/staylong/api/routes.py`, `src/staylong/ui/`, `tests/api/test_case_flow.py`

- [ ] Write an end-to-end test for concern → preparation pack → approved task → overdue escalation → outcome-recorded transition.
- [ ] Implement the minimum accessible web UI and API.
- [ ] Show consent, pending approvals, action timeline and an emergency route.
- [ ] Run the full test suite and commit.

### Task 8: Produce submission evidence

**Files:** `docs/architecture.md`, `docs/demo-script.md`, `docs/runbook.md`, `README.md`

- [ ] Document local setup, Terraform/WIF setup and Cloud Run deployment.
- [ ] Create a four-minute demo script showing live agent action, state and Cloud Run proof.
- [ ] Create the final architecture diagram from the verified implementation.
- [ ] Record the demo and review every claim against the running app.
- [ ] Commit final submission documentation.

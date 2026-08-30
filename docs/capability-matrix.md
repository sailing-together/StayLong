# StayLong Capability Matrix

This document is the **single source of truth** mapping every user-visible capability of StayLong to its API routes, source code modules, automated test suites, deployment infrastructure, and safety governance boundaries.

---

## 1. End-to-End Capability Mapping

| Capability | API Route(s) | Source Module(s) | Test Suite(s) | Infrastructure / Runtime | Safety & Policy Boundary |
|---|---|---|---|---|---|
| **Deterministic Emergency Routing** | `POST /v1/workflows`<br>`POST /v1/public/workflows` | `staylong.policy.emergency` | `tests/policy/test_emergency.py` | Public sandbox and private Cloud Run (`australia-southeast1`) | Pure deterministic screening (000 Triple Zero advice). Never delegated to an LLM. |
| **Gemma Privacy Guard** | `POST /v1/workflows`<br>`POST /v1/public/workflows` | `staylong.privacy.gemma` | `tests/privacy/test_gemma.py` | Vertex Model Garden MaaS `gemma-4-26b-a4b-it-maas` | Strict redact-only contract before Firestore persistence or tool execution; unavailable or malformed output fails closed. |
| **Non-Clinical Intake & Fact Collection** | `POST /v1/workflows`<br>`POST /v1/workflows/{id}/answers`<br>`POST /v1/public/workflows/{id}/answers` | `staylong.agents.intake`<br>`staylong.agents.prompts`<br>`staylong.agents.vertex` | `tests/agents/test_intake.py`<br>`tests/agents/test_vertex_factories.py` | Google ADK Python + Vertex AI Gemini 3.6-flash (`global`) | Structured Pydantic outputs only; schema enforcement rejects prompt injection or non-conforming responses. |
| **Home Independence Assessment Pack** | `GET /v1/workflows/{id}`<br>`GET /v1/public/workflows/{id}` | `staylong.services.home_plan`<br>`staylong.domain.models` | `tests/evaluations/test_demo_fixture.py`<br>`tests/domain/test_models.py` | Cloud Run + Firestore case document | Non-clinical preparation pack; explicitly states it is not an official AT-HM or My Aged Care funding determination. |
| **Human Approval & Action Gate** | `POST /v1/workflows/{id}/action-decision`<br>`POST /v1/public/workflows/{id}/action-decision` | `staylong.policy.approvals`<br>`staylong.services.taskmaster` | `tests/policy/test_approvals.py`<br>`tests/services/test_taskmaster.py` | Application state machine + Firestore | Strict human-in-the-loop: external action or coordination cannot execute without explicit human approval. |
| **Autonomous Coordinator Agent** | Internal state transitions & reminder ticks | `staylong.agents.coordinator`<br>`staylong.services.reminders` | `tests/agents/test_coordinator.py`<br>`tests/services/test_reminders.py` | Cloud Tasks + Pub/Sub + Cloud Run | Produces drafts and plans only; state transitions follow closed enum state machine. |
| **Google Calendar Integration & Sandbox Fallback** | `GET /v1/integrations/google/calendar/start`<br>`GET /v1/integrations/google/calendar/callback` | `staylong.services.google_oauth`<br>`staylong.services.google_actions` | `tests/services/test_google_oauth.py`<br>`tests/services/test_google_actions.py` | Secret Manager + Google Calendar API | Sandboxed by default; private OAuth requires explicit operator secret. Public sandbox cannot trigger live APIs. |
| **Public Sandbox Browser Session Isolation** | `POST /v1/public/workflows`<br>`POST /v1/public/workflows/{id}/*` | `staylong.services.public_sessions`<br>`staylong.api.runtime_token` | `tests/services/test_public_sessions.py`<br>`tests/api/test_public_sandbox_api.py` | Secure cookie session + Firestore owner mapping | Anonymous browser sessions cannot read, mutate, or hijack cases owned by other sessions. |
| **Public Sandbox TTL Cleanup Worker** | `POST /internal/public-sandbox/cleanup` | `staylong.services.public_sessions`<br>`staylong.api.app` | `tests/api/test_public_sandbox_cleanup.py` | Cloud Scheduler (OIDC-authenticated cron) | Automatic expiration and hard deletion of ephemeral public sandbox cases after session TTL. |
| **Public Edge & Domain Load Balancing** | `https://staylonghome.com`<br>`https://www.staylonghome.com` | `infra/terraform/components/public-edge` | `tests/infra/test_public_edge_component.py`<br>`tests/tools/test_public_domain_smoke.py` | Cloudflare DNS + GCP Global HTTPS LB + Serverless NEG | Cloud Run ingress restricted to Load Balancer when lockdown enabled. |

---

## 2. Capability Details and Guarantees

### A. Deterministic Emergency Screening
- **Rule**: If input text contains indicators of imminent physical harm, chest pain, difficulty breathing, unresponsiveness, or fall with severe injury, the agent **immediately halts** workflow progression.
- **Output**: Returns an emergency Triple Zero (000) advisory screen.
- **Code Path**: `staylong.policy.emergency.screen_emergency()` called before any model invocation.

### B. Gemma Privacy Guard
- **Rule**: All user-entered concern text is scanned for unnecessary PII (full names, phone numbers, Medicare numbers, street addresses) before durable persistence in Firestore.
- **Configuration**: Activated via `STAYLONG_GEMMA_ENABLED=true` in Cloud Run environment.
- **Failure behaviour**: An unavailable, malformed or empty Gemma response blocks persistence and planning, then returns a safe retry response. Test fixtures inject a fake provider; the deployed workflow does not silently substitute a local redaction rule.

### C. Non-Clinical Fact Intake (ADK + Vertex AI)
- **Model**: `gemini-3.6-flash` hosted on Vertex AI (`location: global`).
- **Framework**: Google Agent Development Kit (ADK) Python runner.
- **Output Validation**: Structured Pydantic `IntakeAssessment` model with strict `extra="forbid"`.

### D. Human-in-the-Loop Approval Gate
- **State Transition**: Actions transition from `draft` → `pending_approval` → `approved` or `declined`.
- **Revision Locking**: Decisions require matching the current `action_revision`; concurrent edits trigger HTTP `409 Conflict`.
- **Auditability**: Every decision is committed as an immutable domain event in Firestore.

### E. Public Sandbox Isolation & Lifecycle
- **Access Control**: Session cookie `staylong_public_session` establishes cryptographically signed browser ownership.
- **Rate Limits**: Configurable max active cases per browser session (current public-sandbox default: 10).
- **Cleanup**: Cloud Scheduler calls `/internal/public-sandbox/cleanup` on a recurring schedule with OIDC authentication.

---

## 3. Consistency Enforcement

This capability matrix is continuously verified by automated tests in [`tests/integration/test_documentation_consistency.py`](../tests/integration/test_documentation_consistency.py):
1. All referenced Python modules, classes, and functions exist.
2. All referenced test suites exist and pass.
3. All referenced API routes are mounted in FastAPI `app.py`.
4. All referenced infrastructure paths exist in `infra/terraform/`.

# Technology decision and hackathon compliance

**Decision date:** 16 August 2026
**Track:** Taskmaster — All Things Agentic Hackathon

## Locked implementation stack

| Concern | Decision |
| --- | --- |
| Agent runtime | Google ADK for Python |
| Model | Gemini 3.6 Flash on Vertex AI; Gemma 4 MaaS is a separate fail-closed privacy guard |
| API and workflow service | Python 3.12, FastAPI and Pydantic |
| Web experience | React, TypeScript and Vite; built static assets served with the FastAPI service |
| Persistent case state | Firestore: household, consent, approval, case and immutable audit-event records |
| Autonomous work | Cloud Tasks for delayed reminders/retries and Pub/Sub for domain-event routing |
| Approved real-world action | Private runtime only: Google Calendar API creates an authorised coordination event; Gmail remains an unsent-draft capability. Public sandbox actions are simulations. |
| Runtime | Two Cloud Run surfaces in `australia-southeast1`: anonymous public sandbox and IAM-protected private runtime |
| Infrastructure | Terraform provisions all GCP resource lifecycle; GitHub Actions runs reviewed plans/applies through WIF |
| Automation | GitHub Actions for test, lint, Terraform plan/apply and Cloud Run deployment |
| Cloud authentication | GitHub OIDC Workload Identity Federation; no service-account JSON keys |
| Observability | Cloud Logging and the product audit timeline |

## Agent responsibilities

1. **Safety Router** is deterministic code, not an LLM medical triage step. A potential emergency immediately presents the Triple Zero (000) path.
2. **Intake Agent** uses ADK and Gemini to collect missing non-clinical facts and prepare an assessment-preparation pack.
3. **Coordinator Agent** selects the next approved workflow step, prepares action drafts, and uses Cloud Tasks/Pub/Sub to continue autonomously after events or deadlines.
4. **Approval Gate** is enforced in application code before any disclosure or external tool call. The Calendar event is created only after explicit human approval.

## Vertex AI runtime configuration

Production uses Google ADK with `gemini-3.6-flash`. Before constructing either
agent wrapper, the process must set `GOOGLE_CLOUD_PROJECT`,
`GOOGLE_CLOUD_LOCATION=global` for model inference, and
`GOOGLE_GENAI_USE_VERTEXAI=true`. The agent factory validates all three values;
it does not fall back to the Gemini Developer API or infer a project/location
from the model identifier. Application code supplies the ADK Runner bridge to
the intake wrapper, so deterministic emergency routing and structured-output
validation run around every response rather than relying on prompt text.
Cloud Run remains deployed in `australia-southeast1`; its service region is not
the Vertex Gemini inference endpoint.

## Optional Google action connections

StayLong is safe by default: without Google OAuth configuration, every action
adapter is in explicit `sandbox` mode and only records an inspectable local
result. It does **not** pretend that an event or message was created in Google.

To enable user-authorised Google Calendar actions in a private non-demo
environment, an operator must configure the OAuth client ID and exact redirect
URI, and reference the client secret through Secret Manager using
`STAYLONG_GOOGLE_OAUTH_CLIENT_SECRET_ID`. The runtime uses the authenticated
principal and stores only the minimum OAuth state and refresh-token material
needed for that user's connection; raw tokens never appear in Terraform,
Firestore case records, API responses or logs. See the [private Calendar OAuth
runbook](google-calendar-oauth-runbook.md) for the operator-controlled check.
Tokens must never be committed, put in Terraform variables/state, persisted in
Firestore, returned from the API, or written to logs.

With complete configuration, a separately approved `calendar.create` action
creates one Google Calendar event. A separately approved
`contact_draft.create` action creates an unsent Gmail draft only; StayLong has
no send-mail action. Incomplete explicit OAuth configuration fails startup
rather than silently falling back to sandbox mode.

The detailed training-informed architecture choices are recorded in [official training guidance](official-training-guidance.md).

## Rules compliance matrix

| Rule requirement | StayLong implementation evidence |
| --- | --- |
| Gemini 3.5+ through Gemini API or Vertex AI | Vertex AI Gemini configuration and ADK agents (SAI-23 to SAI-26) |
| Google Agent Framework | Google ADK Python application (SAI-23) |
| Google Cloud infrastructure | Cloud Run, Firestore, Cloud Tasks and Pub/Sub, provisioned by Terraform |
| Autonomous agent beyond a chat loop | Event-triggered state transitions, durable tasks, retries, reminders and authorised escalation |
| Taskmaster takes action | A private runtime with complete OAuth configuration can create an approved Google Calendar coordination event and persist its audit record; public-sandbox actions are recorded simulations. |
| Complete multi-step workflow | Concern intake → safety route → fact collection → assessment pack → approval → sandbox-safe follow-through; private Calendar coordination is available only when OAuth is configured and approved. |
| Project can be tested | Public hosted Cloud Run demo with demo data, reproducible README and test instructions |
| English submission materials | English-first product/docs/UI/video; Chinese is internal supplementary material only |
| Architecture diagram and ≤4-minute video | SAI-34 to SAI-37 require the diagram, Google Cloud deployment evidence and English/public video |

## Important distinction

The architecture is compliant **by design**. The submission is compliant only when the listed components are actually implemented, deployed and demonstrated. In particular, the final demo must visibly prove the backend runs on Google Cloud and show the autonomous workflow taking an approved action.

## Explicit safety and scope boundary

StayLong does not diagnose, medically triage, prescribe modifications, determine funding eligibility, submit government applications, select a provider or make payments. It uses demo or fully authorised data only. Human approval is mandatory for external action and information disclosure.

The initial experience is for an older Australian living alone, who can use the
agent without involving anyone else. The current public demo records whether
the person would like to involve someone, but does not create supporter
invitations, accounts, notifications or information sharing. A consent-based
trusted-supporter collaboration capability is planned separately; it must never
silently inform that support network.

## Authoritative competition sources

- [Hackathon home](https://allthingsagentichackathon.devpost.com/)
- [Resources](https://allthingsagentichackathon.devpost.com/resources)
- [Official rules](https://allthingsagentichackathon.devpost.com/rules)
- [Updates](https://allthingsagentichackathon.devpost.com/updates)

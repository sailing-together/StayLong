# Technology decision and hackathon compliance

**Decision date:** 16 August 2026
**Track:** Taskmaster — All Things Agentic Hackathon

## Locked implementation stack

| Concern | Decision |
| --- | --- |
| Agent runtime | Google ADK for Python |
| Model | A competition-eligible Gemini 3.5+ model on Vertex AI |
| API and workflow service | Python 3.12, FastAPI and Pydantic |
| Web experience | React, TypeScript, Vite and Tailwind; built static assets served with the FastAPI service |
| Persistent case state | Firestore: household, consent, approval, case and immutable audit-event records |
| Autonomous work | Cloud Tasks for delayed reminders/retries and Pub/Sub for domain-event routing |
| Approved real-world action | Google Calendar API creates an authorised coordination event; later iterations may add Gmail notifications |
| Runtime | One Cloud Run service in `australia-southeast1` |
| Infrastructure | Terraform |
| Automation | GitHub Actions for test, lint, Terraform plan/apply and Cloud Run deployment |
| Cloud authentication | GitHub OIDC Workload Identity Federation; no service-account JSON keys |
| Observability | Cloud Logging, OpenTelemetry traces and the product audit timeline |

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

The detailed training-informed architecture choices are recorded in [official training guidance](official-training-guidance.md).

## Rules compliance matrix

| Rule requirement | StayLong implementation evidence |
| --- | --- |
| Gemini 3.5+ through Gemini API or Vertex AI | Vertex AI Gemini configuration and ADK agents (SAI-23 to SAI-26) |
| Google Agent Framework | Google ADK Python application (SAI-23) |
| Google Cloud infrastructure | Cloud Run, Firestore, Cloud Tasks and Pub/Sub, provisioned by Terraform |
| Autonomous agent beyond a chat loop | Event-triggered state transitions, durable tasks, retries, reminders and authorised escalation |
| Taskmaster takes action | After human approval, create a Google Calendar coordination event and persist its audit record |
| Complete multi-step workflow | Concern intake → safety route → fact collection → assessment pack → approval → calendar coordination → reminders/escalation → completion proof |
| Project can be tested | Public hosted Cloud Run demo with demo data, reproducible README and test instructions |
| English submission materials | English-first product/docs/UI/video; Chinese is internal supplementary material only |
| Architecture diagram and ≤4-minute video | SAI-34 to SAI-37 require the diagram, Google Cloud deployment evidence and English/public video |

## Important distinction

The architecture is compliant **by design**. The submission is compliant only when the listed components are actually implemented, deployed and demonstrated. In particular, the final demo must visibly prove the backend runs on Google Cloud and show the autonomous workflow taking an approved action.

## Explicit safety and scope boundary

StayLong does not diagnose, medically triage, prescribe modifications, determine funding eligibility, submit government applications, select a provider or make payments. It uses demo or fully authorised data only. Human approval is mandatory for external action and information disclosure.

## Authoritative competition sources

- [Hackathon home](https://allthingsagentichackathon.devpost.com/)
- [Resources](https://allthingsagentichackathon.devpost.com/resources)
- [Official rules](https://allthingsagentichackathon.devpost.com/rules)
- [Updates](https://allthingsagentichackathon.devpost.com/updates)

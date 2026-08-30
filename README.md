# StayLong

See the [product brief](docs/product-brief.md) for policy context, MVP workflow and safety boundaries.

> Help older Australians live independently at home for longer.

StayLong is a consent-governed, event-driven coordination layer for older Australians living alone. It turns a home-living concern into an accountable, assessment-ready plan, coordinates approved next steps, and follows up until every approved action is complete. The older person can work independently or invite an authorised supporter for a specific task.

The public-sandbox runtime passes concern text through Vertex Model Garden MaaS `gemma-4-26b-a4b-it-maas` before persistence or tool actions. Gemini 3.6 Flash remains the primary ADK coordinator; Gemma returns only a strict privacy contract and cannot change safety, consent or approval transitions. If the privacy guard is unavailable or returns invalid output, the workflow fails closed without persisting the concern or starting a plan.

## Public demonstration URL

The long-lived judge-facing experience is designed for `https://staylonghome.com`.
It is a temporary-data demonstration, not a production care service: it does
not connect to real Gmail, Calendar, provider, payment, My Aged Care, or MyGov
accounts. During Phase A, the generated Cloud Run URL remains available while
Google-managed TLS is provisioned. Only an explicitly reviewed
`public_edge_lockdown_enabled=true` configuration switches Cloud Run to accept
traffic through the managed load balancer and branded URL.

## What it is—and is not

StayLong helps older people and their chosen supporters prepare, coordinate and track. It sits between family care apps, provider operations software and My Aged Care: it does **not** deliver care, diagnose health conditions, prescribe home modifications, determine AT-HM eligibility, submit government forms, select a provider, or make payments. Human confirmation is required before every external action or information disclosure.

## Competition fit

StayLong is designed for the **Taskmaster** track of the All Things Agentic Hackathon. It will use Gemini 3.5+ through Vertex AI, Google ADK, and Google Cloud services (Cloud Run, Firestore, Cloud Tasks and Pub/Sub).

See [competition references](docs/competition-references.md) and the public [architecture](docs/architecture.md).
The complete Devpost requirements and bonus evidence plan are in [submission readiness](docs/devpost-submission-readiness.md).
The locked stack and live-submission compliance checklist are in [technology and compliance](docs/technology-and-compliance.md).
The additional Gemma privacy integration is documented in [Gemma privacy guard](docs/gemma-privacy.md).
Task documentation, human-action gates and pull-request practice follow the [delivery standards](docs/delivery-standards.md).
Official Google training and the implementation choices it drives are in [official training guidance](docs/official-training-guidance.md).

## Repository layout

- `src/staylong/` — application package (to be implemented task-by-task)
- `tests/` — automated tests
- `infra/terraform/` — Google Cloud infrastructure definitions
- `.github/workflows/` — CI, Terraform, and Cloud Run deployment automation
- `docs/release-evidence.md` — release-candidate evidence packet and the one-time live verification gate
- `docs/` — product, architecture, prompt, competition and delivery documentation

## Runtime container and smoke test

The Cloud Run image is built from [`Dockerfile`](Dockerfile) and starts
`staylong.api.main:app` on the platform-provided `PORT` (default `8080`). The
runtime requires the `STAYLONG_API_TOKEN` environment variable; it is never
checked into the repository or printed by the smoke test. Pull requests build
the image and run [`tools/cloudrun_smoke.py`](tools/cloudrun_smoke.py)
against a local container, while the deployment workflow runs the same health
and authenticated case-flow checks against the deployed URL. Configure
`STAYLONG_API_TOKEN` as a masked `sandbox` GitHub Environment secret before
using the deployment workflow.

The repeatable UI/API workflow contract lives in
[`tests/api/test_ui_workflow.py`](tests/api/test_ui_workflow.py). It loads the
served HTML, verifies the browser form controls and JavaScript entry point,
then submits the same authenticated request and reads the resulting concern
trail through the API. It runs with the normal `pytest` command and does not
require a live Cloud Run service.

## Development status

This repository contains the public project materials and secure deployment foundation. Product code begins task-by-task through the linked Linear plan.

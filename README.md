# StayLong

See the [product brief](docs/product-brief.md) for policy context, MVP workflow and safety boundaries.

> Help older Australians live independently at home for longer.

StayLong is a consent-governed, event-driven coordination layer for older Australians living alone. It turns a home-living concern into an accountable, assessment-ready plan, coordinates approved next steps, and follows up until every approved action is complete. The older person can work independently or invite an authorised supporter for a specific task.

The public-sandbox runtime can pass concern text through a Vertex AI-hosted Gemma redaction guard before persistence or tool actions. Gemini 3.5+ remains the primary ADK coordinator; Gemma returns only a strict privacy contract and cannot change safety, consent or approval transitions.

## Public demonstration URL

The long-lived judge-facing experience is designed for `https://staylonghome.com`.
It is a temporary-data demonstration, not a production care service: it does
not connect to real Gmail, Calendar, provider, payment, My Aged Care, or MyGov
accounts. During Phase A, the generated Cloud Run URL remains available while
Google-managed TLS is provisioned. Only an explicitly reviewed
`public_edge_lockdown_enabled=true` configuration switches Cloud Run to accept
traffic through the managed load balancer and branded URL.

## What it is—and is not

StayLong helps older people and their chosen supporters prepare, coordinate and track. It sits between family care apps, provider operations software and My Aged Care: it does **not** deliver care, diagnose health conditions, prescribe home modifications, determine AT-HM eligibility, submit government forms, select a provider, or make payments. For acute emergencies or immediate danger, StayLong immediately halts workflow progression and directs users to call Triple Zero (000). Human confirmation is required before every external action or information disclosure.

## Competition fit

StayLong is designed for the **Taskmaster** track of the All Things Agentic Hackathon. It will use Gemini 3.5+ through Vertex AI, Google ADK, and Google Cloud services (Cloud Run, Firestore, Cloud Tasks and Pub/Sub).

See [competition references](docs/competition-references.md) and the public [architecture](docs/architecture.md).
The single source-of-truth capability mapping is in the [capability matrix](docs/capability-matrix.md).
The complete Devpost requirements and bonus evidence plan are in [submission readiness](docs/devpost-submission-readiness.md).
The locked stack and live-submission compliance checklist are in [technology and compliance](docs/technology-and-compliance.md).
The additional Gemma privacy integration is documented in [Gemma privacy guard](docs/gemma-privacy.md).
Task documentation, human-action gates and pull-request practice follow the [delivery standards](docs/delivery-standards.md).
Official Google training and the implementation choices it drives are in [official training guidance](docs/official-training-guidance.md).

## Quickstart and local development

```bash
# 1. Install dependencies
pip install -e ".[dev]"

# 2. Run automated test suite
python -m pytest

# 3. Start local API server with static web UI
python -m uvicorn staylong.api.main:app --port 8080
```

## Repository layout

- `src/staylong/` — application package (FastAPI API, Google ADK agents, Gemma privacy guard, domain models, policy engines, and coordination services)
- `tests/` — automated unit, integration, and infrastructure test suites
- `infra/terraform/` — Google Cloud infrastructure definitions (Sydney `australia-southeast1`)
- `.github/workflows/` — CI, Terraform, and Cloud Run deployment automation
- `docs/release-evidence.md` — release-candidate evidence packet and the live verification gate
- `docs/capability-matrix.md` — single source-of-truth matrix mapping capabilities to code and tests
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

The core application, multi-step coordination workflows, deterministic safety policies, Gemma privacy guard, Google Calendar integration, public sandbox, and Sydney Cloud Run infrastructure are fully implemented and verified with automated test suites.

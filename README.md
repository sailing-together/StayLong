# StayLong

> Help older Australians live independently at home for longer.

StayLong is a family-side, event-driven coordination agent for ageing in place. It turns a home-living concern into an accountable plan: prepare for the right formal assessment, coordinate authorised family members and providers, and follow up until every approved action is complete.

## What it is—and is not

StayLong helps families prepare, coordinate and track. It does **not** diagnose health conditions, prescribe home modifications, determine AT-HM eligibility, submit government forms, select a provider, or make payments. Human confirmation is required before every external action or information disclosure.

## Competition fit

StayLong is designed for the **Taskmaster** track of the All Things Agentic Hackathon. It will use Gemini 3.5+ through Vertex AI, Google ADK, and Google Cloud services (Cloud Run, Firestore, Cloud Tasks and Pub/Sub).

See [competition references](docs/competition-references.md) and the public [architecture](docs/architecture.md).
The locked stack and live-submission compliance checklist are in [technology and compliance](docs/technology-and-compliance.md).
Task documentation, human-action gates and pull-request practice follow the [delivery standards](docs/delivery-standards.md).

## Repository layout

- `src/staylong/` — application package (to be implemented task-by-task)
- `tests/` — automated tests
- `infra/terraform/` — Google Cloud infrastructure definitions
- `.github/workflows/` — CI, Terraform, and Cloud Run deployment automation
- `docs/` — product, architecture, prompt, competition and delivery documentation

## Development status

This repository contains the public project materials and secure deployment foundation. Product code begins task-by-task through the linked Linear plan.

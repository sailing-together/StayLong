# All Things Agentic Hackathon references

StayLong is entering the **Taskmaster** category. This page keeps the official material used to constrain design and submission decisions.

## Official links

- [Hackathon overview](https://allthingsagentichackathon.devpost.com/)
- [Resources and track guidance](https://allthingsagentichackathon.devpost.com/resources)
- [Official rules](https://allthingsagentichackathon.devpost.com/rules)
- [Official updates](https://allthingsagentichackathon.devpost.com/updates)
- [Frequently asked questions](https://allthingsagentichackathon.devpost.com/details/faqs)

## Binding build requirements

Every submission must use:

1. Gemini 3.5 or newer, accessed through Gemini API or Vertex AI.
2. At least one Google agent framework: Google ADK, GenAI SDK, Antigravity SDK or GenKit.
3. At least one Google Cloud infrastructure service.

StayLong will use Vertex AI Gemini, Google ADK, Cloud Run, Firestore, Cloud Tasks and Pub/Sub.

## Taskmaster fit

The resource guide describes Taskmaster as an event-driven workflow with autonomous routing: it watches for a change, determines the next action, works across apps, and completes the workflow without each step being manually directed. StayLong implements that pattern through authorised family coordination and follow-up.

## Submission checklist

- Select one category: **Taskmaster**.
- Submit a hosted project URL where available.
- Submit a clear project description, technologies, data sources and learnings.
- Submit a GitHub/GitLab/Bitbucket repository and reproducible spin-up instructions.
- Include an architecture diagram.
- Publish a public YouTube or Vimeo demo of at most four minutes, in English or with English subtitles.
- Show live proof of Google Cloud deployment in the demo.
- Keep the project new during the submission period and disclose any pre-existing incorporated work.

## Judging implications for StayLong

- **Innovation & operational utility (40%)**: prove a concrete family-care coordination friction is removed.
- **Architecture & tech stack (30%)**: show isolated tools, durable state, approval gates, idempotency and recovery.
- **Demo & production readiness (30%)**: show an unedited action trace, Google Cloud console evidence, clear architecture and reproducible documentation.

## Prompting constraints

Agent prompts must enforce these non-negotiable boundaries:

- Never diagnose a health condition or determine emergency severity from a model output.
- Never claim AT-HM eligibility, prescribe a modification, select a provider, agree a price or submit a government form.
- Stop and request explicit confirmation before sharing personal data, contacting anyone, making an appointment or changing a task owner.
- Use predefined red-flag rules to route possible emergencies to an immediate emergency-help screen; do not wait for a model plan.

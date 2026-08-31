# StayLong

## Elevator pitch

An approval-safe AI coordination agent that helps older Australians living alone turn home concerns into practical plans, assessment preparation, and reliable follow-through.

## Inspiration

Older Australians who live alone can notice small changes at home—a dark hallway, unsafe steps or a shower concern—long before those concerns become an emergency. Finding information is not enough: they need a way to turn a non-clinical concern into assessment-ready information and clear next steps, without losing control over what happens next.

## What it does

StayLong is an ageing-in-place coordination agent that helps older Australians who live alone remain independent at home for longer.

The guided experience turns an everyday home concern into a Home Independence Plan. It gathers bounded, non-clinical context, prepares assessment-ready information, proposes follow-through actions, and keeps those actions pending until an explicit human approval is recorded.

StayLong is not a generic chatbot, care provider or eligibility decision-maker. It does not diagnose, determine funding eligibility, select providers, make payments, submit government applications or take external action without approval. Potential emergency language follows a deterministic safety route rather than LLM medical triage.

## How we built it

StayLong is a full-stack, event-driven Google Cloud application.

- **Guided experience:** React, TypeScript, Vite and Tailwind provide an accessible, step-by-step intake and plan experience.
- **Application service:** Python 3.12, FastAPI and Pydantic run the workflow service on Cloud Run.
- **Agentic coordination:** Google ADK coordinates bounded workflow steps with Gemini 3.6 Flash on Vertex AI.
- **Privacy guard:** Gemma 4 via Vertex Model Garden MaaS checks sensitive or unsafe content and fails closed.
- **Durable follow-through:** Firestore stores case state, approvals and the audit timeline; Cloud Tasks and Pub/Sub support approved asynchronous work.
- **Approval-gated integrations:** The public deployment is an anonymous, synthetic-data sandbox. Google Calendar OAuth and Gmail drafts are available only through the optional private runtime after explicit user approval.
- **Delivery and observability:** Terraform defines infrastructure and policies; GitHub Actions uses Workload Identity Federation for keyless delivery; Cloud Logging captures privacy-safe workflow timing evidence.

## Challenges we ran into

The hardest problem was designing an agent that is genuinely useful without acting beyond its authority. We made approval state explicit, kept the public demo free of real MyGov, provider, payment, Calendar, Gmail and SMS actions, and made the privacy path fail closed.

We also designed the workflow so the demo communicates the product value clearly for non-technical users while making its safety boundaries and cloud architecture inspectable.

## Accomplishments that we're proud of

We built and deployed an end-to-end approval-safe coordination workflow on Google Cloud: guided intake, bounded planning, persistent case state, an audit trail, and clearly separated public and optional private integration paths.

## What we learned

Agentic systems need product boundaries as much as model capability. Explicit approvals, deterministic safety routing, bounded tool access, durable state and observable delivery make it easier to build trust in a high-consequence domain.

## What's next for StayLong

Next we will expand the planned trusted-supporter experience, richer follow-through and evaluation with older adults and care-sector stakeholders, while preserving person-led consent and approval at every external boundary.

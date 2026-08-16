# StayLong product brief

StayLong helps older Australians live independently at home for longer. It is a family-facing coordination agent that turns a non-emergency home-living concern into a durable workflow: collect non-clinical facts, prepare for the relevant assessment, obtain approval, coordinate follow-up and prove completion.

## Australian policy context

Australia's [Support at Home program](https://www.health.gov.au/our-work/support-at-home) began on 1 November 2025, replacing the Home Care Packages Program and Short-Term Restorative Care Programme. Its [Assistive Technology and Home Modifications (AT-HM) scheme](https://www.health.gov.au/our-work/support-at-home/delivering-services-for-support-at-home/assistive-technology-and-home-modifications-at-hm-scheme) gives the project a real local context for home modifications and assistive technology. High-tier home-modification funding is capped at AUD $15,000 per lifetime (excluding any additional eligible supplement) and can cover examples such as handrails, ramps, bathroom redesign and widened doorways.

StayLong helps a family prepare and coordinate authorised steps; it does not determine eligibility, submit applications, access MyGov, select providers, prescribe modifications, make payments or claim funds.

The family-care coordination need is substantial. In 2023–24, around **835,000 people aged 65 and over** used home-support services in Australia, according to [AIHW aged-care reporting](https://www.aihw.gov.au/reports/australias-welfare/aged-care). In 2022, an estimated **3 million Australians (12% of the population)** provided informal care; the average carer age was 50, and an estimated **1.05 million carers were aged 35–54**, according to [AIHW informal-carer reporting](https://www.aihw.gov.au/reports/australias-welfare/informal-carers). This supports StayLong's focus on working-age adult children coordinating care alongside work and family responsibilities.

## MVP

For a concern such as difficulty reaching the bathroom at night, StayLong performs: concern → deterministic emergency check → non-clinical fact collection → assessment-preparation pack with official links → explicit approval → authorised Calendar coordination → asynchronous reminders/escalation → outcome and audit timeline.

Possible emergencies route immediately to Triple Zero (000), without a model call or delayed work. User-supplied photos are household context only, never a clinical risk diagnosis.

## Hackathon fit

**Taskmaster:** a long-running, event-driven workflow with explicit approval boundaries, persistent state and a real approved coordination action. The implementation uses Gemini 3.5+ on Vertex AI, Google ADK, Cloud Run, Firestore, Cloud Tasks and Pub/Sub.

## Differentiation

AskSafe Home supports a single safety decision around suspicious information. StayLong coordinates the ongoing family work that follows an ageing-in-place concern.

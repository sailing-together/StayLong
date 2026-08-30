# StayLong product brief

StayLong helps older Australians who live alone remain independent at home for longer. It is a consent-governed coordination layer that an older person can use independently. It turns a non-emergency home-living concern into a durable workflow: collect non-clinical facts, prepare for the relevant assessment, obtain approval, coordinate follow-up and prove completion.

## Australian policy context

Australia's [Support at Home program](https://www.health.gov.au/our-work/support-at-home) began on 1 November 2025, replacing the Home Care Packages Program and Short-Term Restorative Care Programme. Its [Assistive Technology and Home Modifications (AT-HM) scheme](https://www.health.gov.au/our-work/support-at-home/delivering-services-for-support-at-home/assistive-technology-and-home-modifications-at-hm-scheme) gives the project a real local context for home modifications and assistive technology. High-tier home-modification funding is capped at AUD $15,000 per lifetime (excluding any additional eligible supplement) and can cover examples such as handrails, ramps, bathroom redesign and widened doorways.

StayLong helps an older person prepare and coordinate approved steps; it does not determine eligibility, submit applications, access MyGov, select providers, prescribe modifications, make payments or claim funds.

The need for coordinated home support is substantial. In 2023–24, around **835,000 people aged 65 and over** used home-support services in Australia, according to [AIHW aged-care reporting](https://www.aihw.gov.au/reports/australias-welfare/aged-care). In 2022, an estimated **3 million Australians (12% of the population)** provided informal care; the average carer age was 50, and an estimated **1.05 million carers were aged 35–54**, according to [AIHW informal-carer reporting](https://www.aihw.gov.au/reports/australias-welfare/informal-carers). These figures support an initial focus on independent older people living alone, while informing a future consent-based trusted-supporter model.

## MVP

For a concern such as difficulty reaching the bathroom at night, StayLong performs: concern → deterministic emergency check → non-clinical fact collection → a durable three-task Home Independence Plan and assessment-preparation pack → two separately approval-gated actions (Calendar reminder and unsent contact draft) → outcome and audit timeline. The current public demo supports this journey for an older person completing it independently; a consent-based trusted-supporter model is planned separately.

Possible emergencies route immediately to Triple Zero (000), without a model call or delayed work. User-supplied photos are household context only, never a clinical risk diagnosis.

## Hackathon fit

**Taskmaster:** a long-running, event-driven workflow with explicit approval boundaries, persistent state and a real approved coordination action. The implementation uses Gemini 3.5+ on Vertex AI, Google ADK, Cloud Run, Firestore, Cloud Tasks and Pub/Sub.

## Differentiation

StayLong coordinates the ongoing work that helps a person living alone address an ageing-in-place concern at their own pace. Its distinctive value is the complete path from a plain-language concern to an assessment-ready plan, explicit human approval and visible follow-through.

StayLong sits between family care apps, provider operations software and My Aged Care. It does not manage day-to-day care delivery, run a provider's roster or billing operation, determine eligibility, or replace the government assessment and application process. Its role is to turn an older person's concern into an authorised, assessment-ready plan and follow agreed steps through to completion.

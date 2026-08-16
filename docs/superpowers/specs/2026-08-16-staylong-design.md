# StayLong design

## Product decision

StayLong is an Australian, family-side coordination agent for ageing in place. Its job is to convert a consented home-living concern into an accountable, human-approved plan and follow that plan through its administrative and coordination stages.

## Target users

- **Primary user:** an authorised adult child or informal carer coordinating tasks for an older relative.
- **Beneficiary:** an older Australian who wants to remain in a familiar home.
- **Supporting users:** invited family members who can accept a task or approve a proposed action.

## Problem

Families can identify a practical home-living difficulty but still struggle to prepare for assessment, identify the formal service path, collect the right information, coordinate relatives and providers, and discover that an important task was never completed.

## MVP outcome

For one home-living concern, a family can create a case, prepare a clear assessment conversation pack, assign and follow coordination tasks, record an assessment outcome, and see an auditable next-step plan.

## Primary scenario

An adult child reports that their mother finds night-time bathroom trips difficult. StayLong captures the concern, identifies missing non-clinical details, generates an assessment-preparation pack, asks the household to approve family outreach, tracks who will contact My Aged Care and who will accompany the assessment, and resumes the plan after the outcome is recorded.

## Scope

### In scope

- Consent-aware household and contact setup.
- Concern intake by text; a voice upload may be represented by a transcription in the MVP.
- Deterministic emergency banner route.
- Gemini-assisted structured summary and plain-language preparation pack.
- Event-backed internal tasks, approvals, reminders and escalation.
- Demo adapters for calendar/email and a curated official-resource directory.
- Audit timeline, idempotency and visible failure/retry states.

### Out of scope

- Medical assessment, diagnosis, fall-risk scoring or modification prescriptions.
- MyGov/My Aged Care login automation, government form submission or funding determination.
- Real payments, provider procurement, binding price comparisons or automatic bookings.
- Production handling of real health records.

## Success measures for the demo

- The agent visibly reacts to at least three events without new free-text instructions: concern created, family task overdue, assessment outcome recorded.
- Every external action remains a user-approved draft until confirmed.
- A viewer can see durable state, asynchronous processing, a retry/escalation path and Cloud Run deployment evidence.
- The four-minute video makes the family friction and resolved outcome understandable without domain expertise.

## Design choices

- **Track:** Taskmaster, not Collaborative Partner. The primary value is action coordination, not continuous conversation.
- **Architecture:** Cloud Run + ADK + Vertex AI + Firestore + Cloud Tasks/Pub/Sub.
- **Safety:** deterministic rules front-run the model; human approval gates all consequential actions.
- **Data:** synthetic demo households, events and resource records.

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| Appears to be a checklist chatbot | Demonstrate event-driven retries, approvals, assignment and completion evidence. |
| Appears to offer clinical advice | Describe facts and official process only; refer assessment and prescription decisions to qualified professionals. |
| Overbuilds integrations | Use typed demo adapters first; add one real calendar or email integration only after core flow works. |
| Unsafe autonomous action | Apply explicit consent and action approval records at every tool boundary. |
| Misses hackathon technical proof | Record Cloud Run, Firestore and async worker evidence in the demo and README. |

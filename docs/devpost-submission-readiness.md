# StayLong Devpost submission readiness

This checklist is based on the [official Devpost overview](https://allthingsagentichackathon.devpost.com/) and [official rules](https://allthingsagentichackathon.devpost.com/rules), checked on 27 August 2026. Devpost currently shows a submission deadline of **31 August 2026 at 5:00 PM Pacific Time**.

## Required

- [ ] Select **Taskmaster**.
- [ ] English description covers the problem, features, technologies, data sources, findings and learnings.
- [ ] Show Gemini 3.5+, Google ADK, and Google Cloud services in the description and repository.
- [ ] Link `https://github.com/sailing-together/StayLong` and verify it in an incognito window.
- [ ] Keep README spin-up instructions reproducible for local testing and Terraform deployment.
- [ ] Upload an architecture diagram showing frontend, ADK/Gemini, Cloud Run, Firestore and async services.
- [ ] Provide a public English (or English-subtitled) video of about four minutes or less.
- [ ] Video covers problem, value, working demo, approved action and Google Cloud proof.
- [ ] Add the hosted public-sandbox URL after deployment is verified; never submit the private Sydney v2 URL as the product entry.

## Eligibility and disclosure

- [ ] Every teammate accepts their Devpost invite.
- [ ] Disclose pre-existing work and third-party/open-source components accurately.
- [ ] Confirm licences/terms for all third-party SDKs, fonts, media, APIs and data.
- [ ] Keep the project free to test through judging, or provide testing credentials if a login is unavoidable.
- [ ] Keep all submitted materials English-first and freeze linked materials after the deadline.

## Bonus points — complete all three

### Public technical content

- [ ] Publish an English technical article or public video describing ADK orchestration, Gemini, Gemma privacy, approval gates, Terraform/WIF and lessons learned.
- [ ] Include: **“This content was created for the purposes of entering the All Things Agentic Hackathon.”**
- [ ] Provide a public URL (not private or unlisted) in the Devpost submission.

### Social post

- [ ] Publish on X, LinkedIn, Instagram or Facebook with `#AllThingsAgenticHackathon`.
- [ ] Link only verified public materials; never expose tokens, PII or private Sydney URLs.
- [ ] Publishing is a human-controlled external action and requires account-owner approval.

### Additional Google AI model

- [x] Integrate Vertex AI Gemma as a real PII redaction guard before persistence or tool actions.
- [x] Validate its strict response contract and reject malformed/empty output.
- [ ] Add model/version, invocation path, tests and cost boundary to the final evidence and demo.

## Evidence bundle

- [ ] Public sandbox URL and fresh-browser smoke test.
- [ ] Passing Python, React/TypeScript, Terraform and Trivy CI links.
- [ ] Successful Terraform deployment evidence.
- [ ] Architecture diagram, public demo video, technical article and social-post URLs.
- [ ] Gemma implementation and test evidence.
- [ ] Final Devpost preview checked before submission.


# StayLong Devpost submission record

This document records the materials submitted for the All Things Agentic Hackathon. It is based on the [official Devpost overview](https://allthingsagentichackathon.devpost.com/) and [official rules](https://allthingsagentichackathon.devpost.com/rules), checked on 31 August 2026.

## Submitted project materials

| Material | Location |
| --- | --- |
| Devpost project | [StayLong on Devpost](https://devpost.com/software/staylong) |
| Public product | [staylonghome.com](https://staylonghome.com) |
| Source repository | [sailing-together/StayLong](https://github.com/sailing-together/StayLong) |
| Public demo video | [StayLong — Approval-Safe Ageing-in-Place Coordination Agent](https://youtu.be/oov1tw1uh0k) |
| Project story | [project-story.md](project-story.md) |
| Architecture | [architecture.md](architecture.md) and [architecture assets](assets/architecture/) |
| Deployment evidence | [release-evidence.md](release-evidence.md) |
| Browser acceptance evidence | [live-browser-acceptance-evidence.md](live-browser-acceptance-evidence.md) |

## Final submission status

- [x] Submitted to the **Taskmaster** category.
- [x] Gemini 3.6 Flash on Vertex AI, Google ADK and Google Cloud services are documented in the project, repository and architecture.
- [x] The public source repository includes reproducible README instructions and `python -m pytest`.
- [x] Devpost includes the uploaded architecture diagram, deployed public URL and public English YouTube video under four minutes.
- [x] Gemma 4 is deployed through Vertex Model Garden MaaS as a schema-validated, fail-closed privacy guard; see [gemma-privacy.md](gemma-privacy.md).
- [x] The public video describes the technical approach and includes the required hackathon-content disclosure in its YouTube description.
- [x] A public LinkedIn post was published with `#AllThingsAgenticHackathon`.

The checklists below are retained as the original planning and evidence record. After the competition deadline, do not modify any linked submission material until judging is complete.

## Required

- [ ] Select **Taskmaster**.
- [ ] English description covers the problem, features, technologies, data sources, findings and learnings.
- [ ] Show Gemini 3.5+, Google ADK, and Google Cloud services in the description and repository.
- [ ] Link `https://github.com/sailing-together/StayLong` and verify it in an incognito window.
- [ ] Keep README spin-up instructions reproducible for local testing and Terraform deployment.
- [ ] Upload an architecture diagram showing the public sandbox, private runtime boundary, Gemma privacy guard, ADK/Gemini, Cloud Run, Firestore and asynchronous services.
- [ ] Provide a public English (or English-subtitled) YouTube or Vimeo video of **four minutes or less**.
- [ ] Video covers the problem, customer, solution, working demo, approved action and visible Google Cloud proof in one live, unedited flow.
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

- [x] Deploy-configure Vertex Model Garden MaaS `gemma-4-26b-a4b-it-maas` as the real PII redaction guard before persistence or tool actions.
- [x] Validate its strict response contract and reject malformed/empty output.
- [ ] Add the model/version, invocation path, test evidence, request-based cost boundary and a deployed synthetic-data proof to the final evidence and demo.

## Evidence bundle

- [ ] Public sandbox URL and fresh-browser smoke test.
- [ ] Passing Python, React/TypeScript, Terraform and Trivy CI links.
- [ ] Successful Terraform deployment evidence.
- [ ] Architecture diagram, public demo video, technical article and social-post URLs.
- [ ] Gemma implementation and test evidence.
- [ ] Final Devpost preview checked before submission.

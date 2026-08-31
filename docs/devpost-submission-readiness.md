# StayLong Devpost submission record

This document records the materials submitted for the All Things Agentic Hackathon. It is based on the [official Devpost overview](https://allthingsagentichackathon.devpost.com/) and [official rules](https://allthingsagentichackathon.devpost.com/rules), checked on 31 August 2026. The submission deadline is **31 August 2026 at 5:00 PM Pacific Time** (**1 September 2026 at 10:00 AM AEST**).

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

- [x] Select **Taskmaster**.
- [x] English description covers the problem, features, technologies, data sources, findings and learnings.
- [x] Show Gemini 3.5+, Google ADK, and Google Cloud services in the description and repository.
- [x] Link `https://github.com/sailing-together/StayLong` and verify it in an incognito window.
- [x] Keep README spin-up instructions reproducible for local testing and Terraform deployment.
- [x] Upload the architecture diagram showing the public sandbox, optional private-runtime boundary, Gemma privacy guard, ADK/Gemini, Cloud Run, Firestore and asynchronous services.
- [x] Provide a public English (or English-subtitled) YouTube or Vimeo video of **four minutes or less**.
- [x] Video covers the problem, customer, solution, working demo, approved action and visible Google Cloud proof in one live, unedited flow.
- [x] Add the hosted public-sandbox URL: `https://staylonghome.com`; never submit the private runtime URL as the product entry.
- [x] Link the rendered architecture diagram from the repository: `docs/assets/architecture/staylong-architecture-diagram.drawio.png`.

## Eligibility and disclosure

- [x] Every teammate accepts their Devpost invite.
- [x] Disclose pre-existing work and third-party/open-source components accurately.
- [x] Confirm licences/terms for all third-party SDKs, fonts, media, APIs and data.
- [x] Keep the project free to test through judging, or provide testing credentials if a login is unavoidable.
- [x] Keep all submitted materials English-first and freeze linked materials after the deadline.

### Minimum, accurate disclosure

- [x] State only what the rules require: new work during the submission period, any incorporated pre-existing work, and third-party/open-source components where relevant.
- [x] Keep the technical description factual: Gemini 3.6 Flash on Vertex AI and Google ADK coordinate the workflow; Gemma 4 MaaS is a fail-closed privacy guard.
- [x] Do not disclose credentials, OAuth tokens, private runtime URLs, private prompts, personal information or internal-only operational detail.
- [x] Do not claim a real Calendar event, Gmail message, supporter invitation or data sharing from the public demo. Public actions are recorded simulations.

## Bonus points — complete all three

### Public technical content

- [x] Publish an English technical article or public video describing ADK orchestration, Gemini, Gemma privacy, approval gates, Terraform/WIF and lessons learned.
- [x] Include the required hackathon-content disclosure in the published video.
- [x] Provide a public URL (not private or unlisted) in the Devpost submission.

### Social post

- [x] Publish on X, LinkedIn, Instagram or Facebook with `#AllThingsAgenticHackathon`.
- [x] Link only verified public materials; never expose tokens, PII or private Sydney URLs.
- [x] Publishing is a human-controlled external action and requires account-owner approval.

### Additional Google AI model

- [x] Deploy-configure Vertex Model Garden MaaS `gemma-4-26b-a4b-it-maas` as the real PII redaction guard before persistence or tool actions.
- [x] Validate its strict response contract and reject malformed/empty output.
- [x] Add the model/version, invocation path, test evidence, request-based cost boundary and a deployed synthetic-data proof to the final evidence and demo.

## Evidence bundle

- [x] Public sandbox URL and fresh-browser smoke test: `https://staylonghome.com` and [`live browser acceptance evidence`](live-browser-acceptance-evidence.md).
- [x] Passing Python, React/TypeScript, Terraform and Trivy CI links: [`release evidence`](release-evidence.md).
- [x] Successful Terraform deployment evidence: [`release evidence`](release-evidence.md).
- [x] Architecture diagram URL: `docs/assets/architecture/staylong-architecture-diagram.drawio.png`.
- [x] Public demo video URL: [StayLong on YouTube](https://youtu.be/oov1tw1uh0k).
- [x] Public technical-content URL: [StayLong on YouTube](https://youtu.be/oov1tw1uh0k).
- [x] Public social-post URL: recorded in the submission materials.
- [x] Gemma implementation and test evidence: [`Gemma privacy integration`](gemma-privacy.md).
- [x] Final Devpost preview checked by the submitting team member before submission.

## Final two-person release gate

- [x] Reviewer A checks every public link, the video duration and the English-language requirement.
- [x] Reviewer B checks the Devpost preview against this checklist, including the disclosure boundary.
- [x] The submitting team member confirms that all teammates have accepted invitations and selects **Submit**.

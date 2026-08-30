# StayLong Devpost submission readiness

This checklist is based on the [official Devpost overview](https://allthingsagentichackathon.devpost.com/) and [official rules](https://allthingsagentichackathon.devpost.com/rules), rechecked on 31 August 2026. The submission deadline is **31 August 2026 at 5:00 PM Pacific Time** (**1 September 2026 at 10:00 AM AEST**).

Use this as the final release gate: do not submit until every required item is verified against its live URL or final Devpost preview.

## Required

- [ ] Select **Taskmaster**.
- [ ] English description covers the problem, customer, solution, technologies, data sources, findings and learnings.
- [ ] Show Gemini 3.5+, Google ADK, and Google Cloud services in the description and repository.
- [ ] Link `https://github.com/sailing-together/StayLong` and verify it in an incognito window.
- [ ] Keep README spin-up instructions reproducible for local testing and Terraform deployment.
- [ ] Upload the architecture diagram showing the public sandbox, optional private-runtime boundary, Gemma privacy guard, ADK/Gemini, Cloud Run, Firestore and asynchronous services.
- [ ] Provide a public English (or English-subtitled) YouTube or Vimeo video of **four minutes or less**.
- [ ] Video covers the problem, customer, solution, working demo, approved action and visible Google Cloud proof in one live, unedited flow.
- [ ] Add the hosted public-sandbox URL: `https://staylonghome.com`; never submit the private runtime URL as the product entry.
- [ ] Link the rendered architecture diagram from the repository: `docs/assets/architecture/staylong-architecture-diagram.drawio.png`.

## Eligibility and disclosure

- [ ] Every teammate accepts their Devpost invite.
- [ ] Disclose pre-existing work and third-party/open-source components accurately.
- [ ] Confirm licences/terms for all third-party SDKs, fonts, media, APIs and data.
- [ ] Keep the project free to test through judging, or provide testing credentials if a login is unavoidable.
- [ ] Keep all submitted materials English-first and freeze linked materials after the deadline.

### Minimum, accurate disclosure

- [ ] State only what the rules require: new work during the submission period, any incorporated pre-existing work, and third-party/open-source components where relevant.
- [ ] Keep the technical description factual: Gemini 3.6 Flash on Vertex AI and Google ADK coordinate the workflow; Gemma 4 MaaS is a fail-closed privacy guard.
- [ ] Do not disclose credentials, OAuth tokens, private runtime URLs, private prompts, personal information or internal-only operational detail.
- [ ] Do not claim a real Calendar event, Gmail message, supporter invitation or data sharing from the public demo. Public actions are recorded simulations.

## Bonus points — complete all three

### Public technical content

- [ ] Publish an English technical article or public video describing ADK orchestration, Gemini, Gemma privacy, approval gates, Terraform/WIF and lessons learned.
- [ ] Include this exact sentence: **“This piece of content was created for the purposes of entering the All Things Agentic Hackathon.”**
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

- [ ] Public sandbox URL and fresh-browser smoke test: `https://staylonghome.com` and [`live browser acceptance evidence`](live-browser-acceptance-evidence.md).
- [ ] Passing Python, React/TypeScript, Terraform and Trivy CI links: [`release evidence`](release-evidence.md).
- [ ] Successful Terraform deployment evidence: [`release evidence`](release-evidence.md).
- [ ] Architecture diagram URL: `docs/assets/architecture/staylong-architecture-diagram.drawio.png`.
- [ ] Public demo video URL: _add after publishing_.
- [ ] Public technical article URL: _add after publishing_.
- [ ] Public social-post URL: _add after publishing_.
- [ ] Gemma implementation and test evidence: [`Gemma privacy integration`](gemma-privacy.md).
- [ ] Final Devpost preview checked by the submitting team member before submission.

## Final two-person release gate

- [ ] Reviewer A checks every public link, the video duration and the English-language requirement.
- [ ] Reviewer B checks the Devpost preview against this checklist, including the disclosure boundary.
- [ ] The submitting team member confirms that all teammates have accepted invitations and selects **Submit**.

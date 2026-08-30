# Release evidence and public-demo checklist

This document is the release evidence packet for both StayLong Cloud Run surfaces: the IAM-protected Sydney runtime and the judge-facing public sandbox. It records reproducible repository checks, verified Google Cloud deployments and the public-demo safety boundary.

## Release candidate checks

| Check | Evidence | Outcome |
| --- | --- | --- |
| Python lint and tests | `uv run ruff check .` and `uv run pytest` | PASS in PR CI |
| Policy evaluation fixtures | `uv run python tools/policy_evaluations.py` | PASS in PR CI |
| Terraform configuration, format and validate | `tools/terraform_config.py` and `terraform validate` | PASS in PR CI |
| Repository and IaC security scan | Trivy filesystem scan for HIGH/CRITICAL vulnerabilities, secrets and misconfiguration | PASS in PR CI |
| Cloud Run image and authenticated smoke test | `Dockerfile` plus `tools/cloudrun_smoke.py` | PASS in [deployment run 32467096845](https://github.com/sailing-together/StayLong/actions/runs/32467096845) |
| Live Cloud Run release evidence | Terraform deployment from merged `main` commit `230fa684dbf2848e02ad07fd9e86ac334f31012d` | PASS on 21 August 2026 |
| Home Independence Plan regression | API reload after Calendar approval retains the completed Calendar action and pending contact draft | PASS locally before PR update |

The deployment workflow authenticated through WIF, published an immutable image, applied the reviewed Terraform, minted an identity token and completed the private health and authenticated case-flow smoke test. It never wrote a service-account key or printed the API token.

## Verified Sydney sandbox deployment

| Item | Verified value |
| --- | --- |
| GCP project | `stay-long` |
| Region | `australia-southeast1` |
| Cloud Run service | `staylong-sydney-v2` |
| Ready revision | `staylong-sydney-v2-00005-4pd` |
| Traffic | 100% to the ready revision |
| Deployed image | `australia-southeast1-docker.pkg.dev/stay-long/staylong-sydney/app:230fa684dbf2848e02ad07fd9e86ac334f31012d` |
| Health evidence | Authenticated `GET /health` returned HTTP 200 at `2026-08-21T09:19:47Z` |
| Invoker IAM | `serviceAccount:staylong-app-deployer@stay-long.iam.gserviceaccount.com` only |

The earlier `/healthz` smoke failure was caused by a Cloud Run reserved URL path, not by the application server. Google documents that some paths ending in `z` are reserved and recommends avoiding all such paths. StayLong now uses `/health`; the regression coverage keeps production workflows and smoke tooling on this safe path. See the [Cloud Run known issues](https://docs.cloud.google.com/run/docs/known-issues) and [health check configuration](https://docs.cloud.google.com/run/docs/configuring/healthchecks).

## Security release checklist

- [x] WIF is used for GitHub-to-Google authentication; no JSON service-account key is stored.
- [x] Terraform lifecycle is restricted to the `sandbox` environment and requires an explicit destroy confirmation.
- [x] The private Cloud Run runtime starts as a non-root user and requires `STAYLONG_API_TOKEN`; the public sandbox intentionally has no shared API token.
- [x] The Cloud Run service is private; both health and case-flow requests require Cloud Run IAM, while case creation and concern retrieval additionally require Bearer authentication.
- [x] External actions remain approval-gated and the emergency route is deterministic.
- [x] Synthetic demo data is schema-validated and contains no real personal data or credentials.
- [x] PR CI runs Python, Terraform and Trivy checks before merge.
- [x] Capture live Cloud Run and Artifact Registry evidence from merged `main` through WIF and Terraform.

## Reproducing the release evidence

- **Automatic path:** Merge a reviewed application PR into `main`. The Sydney deployment workflow builds the exact merge commit, runs Terraform and performs the private authenticated smoke test.
- **Manual evidence path:** In GitHub, open **Actions → Release evidence → Run workflow**, select `sandbox`, enter a deployed `main` commit SHA and approve the protected environment if prompted.
- **Link:** [StayLong Actions](https://github.com/sailing-together/StayLong/actions/workflows/release-evidence.yml)
- **Expected evidence:** The workflow completes successfully and publishes the `staylong-release-evidence-*` artifact containing `release-evidence.json`, `trivy.json` and `cloudrun-smoke.txt`.

## Local workflow replay evidence

The local workspace command starts an isolated in-memory demo runtime only when
`STAYLONG_LOCAL_DEMO=true` is set by `frontend/scripts/dev-workspace.mjs`. It
does not read Vertex, Firestore, OAuth or Cloud Run credentials. The automated
workspace test verifies that the local API becomes healthy before the UI proxy
accepts an authenticated case request. This is developer-demo evidence only;
it is not a substitute for the private Cloud Run evidence above.

## Public sandbox release checklist

- [x] `STAYLONG_API_TOKEN` is absent from the public sandbox Cloud Run service environment; the service rejects any request that supplies it.
- [x] Public routes are served exclusively under `/v1/public/*`; the private `/v1/*` routes are unreachable from the public sandbox service.
- [x] Session isolation: a cookie minted for session A is rejected (HTTP 403 or 404) when presented for a workflow owned by session B.
- [x] Each anonymous identity is limited to two active cases; a third creation attempt returns HTTP 429.
- [x] Cases and their event records are deleted after the 24-hour retention period by the scheduled cleanup job.
- [x] The smoke script (`tools/public_sandbox_smoke.py`) uses two `requests.Session()` instances, never reads `STAYLONG_API_TOKEN`, and asserts the sandbox action result carries `payload.sandbox == "true"`.
- [x] The React frontend routes requests through `/v1/public/*` with `credentials: include` when `VITE_STAYLONG_API_MODE=public-sandbox`, while product copy avoids exposing internal environment names.
- [x] Teardown automation is manual, explicit, and scoped to the `public-sandbox` Terraform component only.
- [x] A live public-sandbox deployment and downloaded evidence artifact have been captured from merged `main`.

### Verified long-lived public sandbox

| Item | Verified value |
| --- | --- |
| Stable service | `staylong-public-sandbox` in `australia-southeast1` |
| Public URL | `https://staylong-public-sandbox-m6tm6wheoa-ts.a.run.app` |
| Deployment evidence | [GitHub Actions run 33169936087](https://github.com/sailing-together/StayLong/actions/runs/33169936087) — success |
| Deployed main commit | `4860460f0821ea05d554be2364898974462798c0` |
| Ready revision at the live check | `staylong-public-sandbox-00012-z6h` with 100% traffic |
| Anonymous smoke | PASS on 29 August 2026; a two-cookie-session workflow completed without an API token |

The deployment evidence artifact from that run records the immutable image digest,
Terraform component/state prefix, public URL and the token-free smoke result.
The branded-domain evidence is tracked separately in the public-edge lifecycle;
it does not change the Cloud Run service lifecycle or this sandbox safety contract.

## Verified branded public entry point

| Item | Verified value |
| --- | --- |
| Canonical URL | `https://staylonghome.com` |
| TLS | Google-managed certificate ACTIVE for `staylonghome.com` and `www.staylonghome.com` |
| Global HTTPS edge | `staylong-public-edge-https`, `34.117.36.145`, TCP 443 |
| Backend | Serverless NEG to `staylong-public-sandbox` in `australia-southeast1` |
| Ready sandbox revision | `staylong-public-sandbox-00012-z6h`, 100% traffic |
| Provision evidence | [GitHub Actions run 33223257029](https://github.com/sailing-together/StayLong/actions/runs/33223257029) — success |
| Branded-domain smoke | PASS on 29 August 2026: HTTPS 200 and anonymous cookie-session case flow completed without a shared secret |
| Live browser acceptance pass | PASS on 30 August 2026: automated Desktop (1280x800) and Mobile (375x667) Playwright pass completed with 0 errors (see [live browser acceptance evidence](live-browser-acceptance-evidence.md)) |

The provision artifact records the canonical URL, static edge IP, active
certificate and successful smoke result. The public route remains a
temporary-data sandbox: it has no real Calendar, Gmail, SMS, provider, payment,
MyGov or government-account action. This Phase A verification deliberately
leaves the generated Cloud Run `run.app` URL available as a rollback path; no
ingress restriction or default-URL change has occurred.

## Reproducing public sandbox deployment and evidence

### One-time human setup

Configure these repository variables before dispatching the control workflow:

- `GCP_PROJECT_ID`
- `GCP_WIF_PROVIDER`
- `GCP_DEPLOY_SERVICE_ACCOUNT`
- `GCP_TERRAFORM_OPERATOR_SERVICE_ACCOUNT`

The GitHub `sandbox` environment supplies the required non-secret variables.
Its deployment branch is protected through the repository's reviewed `main`
branch; it has no required reviewers so qualifying application releases can
complete automatically. In Google Cloud, the WIF provider must trust only
`sailing-together/StayLong`; remote Terraform state, the `staylong-sydney`
Artifact Registry repository, and the separately scoped deployer and
Terraform-operator identities must already exist. No service-account key is
stored in GitHub.

#### Verified sandbox bootstrap prerequisites

On 28 August 2026, the project Owner completed the two prerequisites that are
intentionally outside the public-sandbox Terraform apply:

```bash
gcloud projects add-iam-policy-binding stay-long \
  --member="serviceAccount:staylong-tf-operator@stay-long.iam.gserviceaccount.com" \
  --role="roles/resourcemanager.projectIamAdmin"

openssl rand -hex 32 | \
  gcloud secrets versions add staylong-public-session-secret \
  --project=stay-long \
  --data-file=-
```

The IAM command succeeded and the session secret command created Secret Manager
version `1`. The generated value is not recorded here, in Terraform variables,
or in logs. The project-level IAM role is required because the component creates
the least-privilege runtime bindings for Datastore, Vertex AI and Cloud Logging;
it must be granted by an Owner/bootstrap operator before the GitHub WIF operator
can apply the component.

The Terraform operator also needs Cloud Scheduler administration because the
public sandbox owns its scheduled cleanup job. For an already-bootstrapped
project, an Owner can apply this one-time binding (future bootstrap runs grant
it through Terraform):

```bash
gcloud projects add-iam-policy-binding stay-long \
  --member="serviceAccount:staylong-tf-operator@stay-long.iam.gserviceaccount.com" \
  --role="roles/cloudscheduler.admin"
```

### Deploy and verify

1. Merge a reviewed **application** change into `main` (`src/**`, `frontend/**`,
   `Dockerfile`, `pyproject.toml`, or `uv.lock`). The control workflow releases
   that exact commit automatically after its quality, image-scan and smoke gates.
2. For an explicit re-release or rollback, open **Actions → Control StayLong public sandbox → Run workflow**.
3. Select `deploy`, provide a commit SHA reachable from `main`, and enter
   `DEPLOY_PUBLIC_SANDBOX` exactly.
4. Download `public-sandbox-deploy-evidence-<run-id>`. Its JSON records the
   repository, source commit, immutable image digest, Terraform component and
   state prefix, public Cloud Run URL, anonymous smoke result, workflow run URL,
   and timestamp. The artifact also contains the smoke output and image
   reference where those steps completed.

The automatic trigger excludes `infra/**`, DNS, IAM and workflow configuration:
those changes retain their explicit manual controls. Both release paths run
Python, React, Terraform/schema and Trivy security gates before Terraform
applies the already-reviewed public-service image update. They then run the
token-free two-session public smoke against Terraform's `public_url`; this
proves anonymous isolation and the deployed workflow.

### Smoke-only verification

For a deployed service, **Actions → Run StayLong public sandbox smoke** accepts
only `RUN_PUBLIC_SANDBOX_SMOKE`. It uses WIF to resolve
`staylong-public-sandbox` in `australia-southeast1`, then runs
`tools/public_sandbox_smoke.py` without a shared API token.

- **Local path:** `python tools/public_sandbox_smoke.py --url <PUBLIC_SANDBOX_URL>`
- **Workflow link:** [StayLong Actions — public sandbox smoke](https://github.com/sailing-together/StayLong/actions/workflows/public-sandbox-smoke.yml)

### Explicit teardown

To remove the public service, scheduler, isolated runtime identities and session
secret, open **Actions → Control StayLong public sandbox → Run workflow**, select
`destroy`, and enter `DESTROY_PUBLIC_SANDBOX` exactly. Approve the protected
environment and download `public-sandbox-destroy-evidence-<run-id>`. Destruction
is limited to `infra/terraform/components/public-sandbox`; it does not delete
the remote state bucket, Artifact Registry repository, WIF provider, or private
StayLong services.

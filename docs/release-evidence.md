# Release evidence and security checklist

This document is the release evidence packet for the private StayLong Sydney sandbox service. It records reproducible repository checks and the verified Google Cloud deployment.

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
- [x] Cloud Run starts as a non-root user and requires `STAYLONG_API_TOKEN` at runtime.
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

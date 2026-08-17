# Release evidence and security checklist

This document is the release-candidate evidence packet for StayLong. It separates reproducible repository checks from the one human-authorised Google Cloud action that cannot be performed from an unconfigured workspace.

## Release candidate checks

| Check | Evidence | Outcome |
| --- | --- | --- |
| Python lint and tests | `uv run ruff check .` and `uv run pytest` | PASS in PR CI |
| Policy evaluation fixtures | `uv run python tools/policy_evaluations.py` | PASS in PR CI |
| Terraform configuration, format and validate | `tools/terraform_config.py` and `terraform validate` | PASS in PR CI |
| Repository and IaC security scan | Trivy filesystem scan for HIGH/CRITICAL vulnerabilities, secrets and misconfiguration | PASS in PR CI |
| Cloud Run image and authenticated smoke test | `Dockerfile` plus `tools/cloudrun_smoke.py` | PASS in PR #25 and PR CI |
| Live Cloud Run release evidence | Manual `release-evidence.yml` dispatch from `main` | REQUIRES HUMAN ACTION |

The live evidence workflow captures the selected main commit, Cloud Run service URL, Artifact Registry image digest, health response, authenticated case-flow smoke result and the security scan as a downloadable GitHub Actions artifact. It never writes a service-account key or prints the API token.

## Security release checklist

- [x] WIF is used for GitHub-to-Google authentication; no JSON service-account key is stored.
- [x] Terraform lifecycle is restricted to the `sandbox` environment and requires an explicit destroy confirmation.
- [x] Cloud Run starts as a non-root user and requires `STAYLONG_API_TOKEN` at runtime.
- [x] Health is public, while case creation and concern retrieval require Bearer authentication.
- [x] External actions remain approval-gated and the emergency route is deterministic.
- [x] Synthetic demo data is schema-validated and contains no real personal data or credentials.
- [x] PR CI runs Python, Terraform and Trivy checks before merge.
- [ ] Capture live Cloud Run and Artifact Registry evidence with the protected sandbox environment.

## Human action required

- **Why:** Only the project owner can approve a protected GitHub Environment and provide the configured Google Cloud project/WIF variables and masked API token.
- **Action:** In GitHub, open **Actions → Release evidence → Run workflow**, select `sandbox`, enter the deployed main commit SHA, approve the protected environment, and ensure the `sandbox` environment contains `GCP_PROJECT_ID`, `GCP_REGION`, `GCP_WIF_PROVIDER`, `GCP_TERRAFORM_PLANNER_SERVICE_ACCOUNT` and the masked `STAYLONG_API_TOKEN` secret.
- **Link:** [StayLong Actions](https://github.com/sailing-together/StayLong/actions/workflows/release-evidence.yml)
- **Safe to continue after:** The workflow completes successfully and publishes the `staylong-release-evidence-*` artifact containing `release-evidence.json`, `trivy.json` and `cloudrun-smoke.txt`.

Until that artifact exists, this task must remain In Progress; repository checks alone are not evidence of a live Cloud Run deployment.

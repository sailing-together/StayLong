# Delivery runbook

## Secure Google Cloud and GitHub setup

1. Create the dedicated Google Cloud project and protect the `main` branch in GitHub.
2. Authenticate locally with an approved human administrator and run the first reviewed Terraform apply from `infra/terraform`.
3. Record Terraform outputs as GitHub **environment variables** in the `production` environment, together with `GCP_PROJECT_ID` and `GCP_REGION`. They are identifiers, not secrets.
4. Require approval on the GitHub `production` environment before deployment.
5. Run Terraform plans from pull requests. They use a read-only WIF planner identity. Run an apply only via manual dispatch from `main`; it impersonates the separately scoped deployer identity.

No service-account JSON key is created, stored or uploaded. GitHub Actions exchanges its short-lived GitHub OIDC token for Google credentials through Workload Identity Federation (WIF). The provider trusts only `sailing-together/StayLong`; the deployer service account additionally permits only `main`.

## Workflows

| Workflow | Trigger | Purpose |
| --- | --- | --- |
| `ci.yml` | Pull requests and `main` | Python tests and Ruff linting |
| `terraform.yml` | Infrastructure PRs, manual dispatch from `main` | Format, validate, plan; reviewed apply only when selected |
| `deploy.yml` | Manual dispatch from `main` | Build and deploy the Cloud Run service with WIF |

`deploy.yml` is intentionally scaffolded until the Cloud Run application and `Dockerfile` are implemented in Linear task ST-7. This prevents a misleading "green" deployment before there is a real service to deploy.

## Safety release gate

Before a live demonstration: run automated tests, review the Terraform plan, verify all external side effects require explicit approval, exercise the deterministic emergency path, and capture a Cloud Run deployment plus audit timeline in the four-minute Devpost video.

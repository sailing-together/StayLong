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
| `release-evidence.yml` | Manual dispatch from `main` | Capture live Cloud Run, Artifact Registry and security release evidence |

`deploy.yml` builds and smoke-tests the implemented Cloud Run service. The first live run still requires the sandbox environment variables, masked API token and protected-environment approval described in [release evidence](release-evidence.md).

## Default GCP and Terraform operating procedure

Use this procedure for every Google Cloud or Terraform change. Terraform is the
source of truth; MCP tools complement the repository checks and never bypass
the approval gate.

1. **Implement and validate locally.** Update code, Terraform, tests and
   documentation together. Run the relevant application tests, `terraform fmt`
   and `terraform validate`. When the Terraform MCP is available in the active
   task, use it to inspect the workspace and review the generated plan.
2. **Perform a read-only GCP preflight.** When the GCP MCP is available, inspect
   the affected Cloud Run service, service-account IAM bindings, Secret Manager
   metadata, enabled APIs and bounded recent error logs. Never retrieve secret
   values, OAuth tokens or customer data during this check.
3. **Review an explicit plan.** A pull request or manual plan must state every
   resource expected to be created, changed or destroyed, plus the deployment
   impact and rollback path. Treat unexpected destruction or privilege
   expansion as a stop condition.
4. **Apply only after explicit approval.** A human must explicitly approve the
   Terraform apply or deployment. Use the protected GitHub workflow and its
   WIF deployer identity; do not let Terraform MCP or GCP MCP make unattended
   production changes.
5. **Verify after deployment.** Use a read-only GCP check to confirm the Cloud
   Run revision, IAM boundary, health/smoke result and redacted logs. Record the
   pull request, workflow run, deployed revision and verification evidence.
6. **Keep public and private boundaries separate.** The public sandbox must
   never receive real OAuth clients, tokens or external side effects. Private
   integrations require least privilege, a dedicated test account and a
   completed private end-to-end verification before they are presented as live.

## Safety release gate

Before a live demonstration: run automated tests, review the Terraform plan, verify all external side effects require explicit approval, exercise the deterministic emergency path, and capture a Cloud Run deployment plus audit timeline in the four-minute Devpost video.

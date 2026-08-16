# StayLong Terraform

Terraform is the sole provisioning authority for StayLong's Google Cloud
resources. GitHub Actions authenticates through GitHub OIDC Workload Identity
Federation (WIF); Google service-account keys must never be stored in GitHub.

## Layout

```text
modules/
  base/          # atomic capabilities; no StayLong, repository, or environment values
  foundations/   # reusable compositions of base modules
projects/staylong/sandbox/
  bootstrap-state/     # GCS state bucket; local state for the first apply
  bootstrap-identity/  # WIF and least-privilege GitHub identities
  platform/            # APIs, Artifact Registry, and runtime identity
  app/                 # Cloud Run service configuration
```

Only `projects/staylong/sandbox` contains StayLong-specific names, the GitHub
repository, environment, region, image, service name, or secret references.

## Lifecycle

1. A human with authorised local Google Cloud credentials creates
   `bootstrap-state` using local Terraform state. It does not use the bucket it
   is creating as its own backend.
2. Terraform state is migrated to that GCS bucket. Then a human performs the
   initial local `bootstrap-identity` apply: WIF cannot create its own identity.
3. GitHub Actions can then run component-scoped plan/apply for `platform` and
   `app` using WIF. The manual `terraform.yml` workflow is sandbox-only.

`bootstrap-state` and `bootstrap-identity` are long-lived roots. They have no
normal workflow destroy path. Their exceptional teardown is deliberately kept
out of automation and documented in the break-glass runbook.

## GitHub sandbox configuration

Configure these GitHub Environment variables for `sandbox` after the human
bootstrap:

- `GCP_PROJECT_ID`, `GCP_WIF_PROVIDER`
- `GCP_TERRAFORM_PLANNER_SERVICE_ACCOUNT`, `GCP_TERRAFORM_OPERATOR_SERVICE_ACCOUNT`
- `GCP_DEPLOY_SERVICE_ACCOUNT`, `GCP_RUNTIME_SERVICE_ACCOUNT`
- `GCP_REGION`, `TF_STATE_BUCKET`, `STAYLONG_APP_IMAGE`

Set the `sandbox` GitHub Environment to require approval for changes. A
`platform` or `app` destroy additionally requires the exact workflow input
`DESTROY_SANDBOX`.

## Application delivery

`deploy.yml` runs automatically only when application files merge to `main`,
or manually for a selected commit SHA that is already reachable from `main`.
It first verifies the Terraform-managed Artifact Registry and Cloud Run service
exist. It then publishes an immutable image and updates only the Cloud Run
image revision; it never creates the repository, service, service account, or
access policy.

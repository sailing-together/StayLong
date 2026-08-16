# StayLong Terraform

Terraform is the sole provisioning authority for StayLong's Google Cloud
resources. GitHub Actions authenticates through GitHub OIDC Workload Identity
Federation (WIF); Google service-account keys must never be stored in GitHub.

## Layout

```text
bootstrap/                 # one-time, human-authorised local setup only
  state/                   # creates the GCS Terraform state backend
  identity/                # creates GitHub WIF and service identities
modules/
  base/                    # atomic capabilities with no product semantics
  foundations/             # reusable capability compositions
projects/staylong/sandbox/
  platform/                # APIs, Artifact Registry, runtime identity
  app/                     # Cloud Run service configuration
```

`bootstrap` is deliberately separate from `projects`: it is a one-time
initialisation process, not a deployable application component. Only
`projects/staylong/sandbox` knows StayLong-specific names, the GitHub
repository, sandbox region, image, service name, and secret references.

## One-time bootstrap

1. A human with authorised local Google Cloud credentials applies
   `bootstrap/state` using local Terraform state. This root does not use the
   bucket it creates as its own backend.
2. State for `bootstrap/identity`, `platform`, and `app` is then migrated to
   that GCS bucket. A human applies `bootstrap/identity` locally because WIF
   cannot create its own trusted identity.
3. Only after these two local operations are complete may GitHub Actions run
   component-scoped plan/apply/destroy for `platform` and `app`.

The bootstrap roots are long-lived and have no GitHub Actions lifecycle or
ordinary destroy path. Their exceptional teardown remains a separate,
human-authorised break-glass procedure.

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

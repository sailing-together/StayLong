# StayLong Terraform

Terraform is the sole provisioning authority for StayLong's Google Cloud
resources. GitHub Actions authenticates through GitHub OIDC Workload Identity
Federation (WIF); Google service-account keys must never be stored in GitHub.

## Layout

```text
bootstrap/                 # one-time, human-authorised local setup only
  state/
  identity/
components/                # reusable Terraform roots operated by GitHub Actions
  platform/
  app/
modules/
  base/
  foundations/
projects/config/           # non-sensitive project and environment selection data
  common-environment.json
  sandbox.json
  staylong.json
  schemas/
```

There is no project-specific Terraform root. Every root receives only the
non-sensitive selection variables `project_config` and `environment_config`.
It reads the three JSON documents and uses the deterministic merge order:
`common-environment < environment < project`. JSON Schema validation is a
mandatory workflow step before Terraform initialisation or planning.

## One-time bootstrap

1. A human with authorised local Google Cloud credentials validates the JSON
   selections and applies `bootstrap/state` using local Terraform state.
2. State for `bootstrap/identity`, `components/platform`, and `components/app`
   is migrated to the created GCS bucket. A human applies `bootstrap/identity`
   locally because WIF cannot create its own trusted identity.
3. GitHub Actions can then operate only `platform` and `app` through the
   sandbox workflow.

Example local validation:

```bash
PYTHONPATH=src python tools/terraform_config.py \
  --project-config staylong.json \
  --environment-config sandbox.json
terraform -chdir=infra/terraform/bootstrap/state init -backend=false
terraform -chdir=infra/terraform/bootstrap/state apply \
  -var='project_config=staylong.json' \
  -var='environment_config=sandbox.json'
```

Bootstrap roots are deliberately absent from `terraform.yml`. Their exceptional
teardown remains a separate, human-authorised break-glass procedure.

See [the bootstrap and teardown runbook](../../docs/bootstrap-runbook.md) for
the local-state first apply, GCS initialisation or migration, GitHub Actions
handoff, and the only safe order for teardown. The tracked
`backend.hcl.example` is a template only; its copied `backend.hcl` file is
ignored and must never be committed.

## Configuration safety

Committed configuration is non-sensitive. The shared validator rejects unknown
selection filenames, schema-invalid values, unknown properties, and keys that
look like secrets, passwords, tokens, credentials, private keys, or API keys.
Secrets belong in the approved Google Cloud and GitHub environment mechanisms,
not these JSON files.

## Application delivery

`deploy.yml` runs automatically only when application files merge to `main`,
or manually for a selected commit SHA that is already reachable from `main`.
It first verifies the Terraform-managed Artifact Registry and Cloud Run service
exist. It then publishes an immutable image and updates only the Cloud Run
image revision; it never creates the repository, service, service account, or
access policy.

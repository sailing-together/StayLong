# Bootstrap and teardown runbook

This runbook establishes the first secure Terraform backend for StayLong. It is
a human-authorised, break-glass procedure. Normal infrastructure changes use
GitHub Actions and the remote GCS state after this procedure is complete.

## State ownership

| Terraform root | State location | Why |
| --- | --- | --- |
| `bootstrap/state` | Local only | It creates and manages the Terraform state bucket and the dedicated Cloud Build staging bucket that must exist before GitHub Actions can run. |
| `bootstrap/identity` | GCS after bootstrap | It creates GitHub OIDC WIF and Terraform identities. |
| `components/platform` | GCS | GitHub Actions manages the platform lifecycle. |
| `components/app` | GCS | GitHub Actions manages the application lifecycle. |

Never commit `terraform.tfstate`, `backend.hcl`, a copied backend
configuration, or a local state backup.

## First bootstrap

Prerequisites:

- An approved human administrator is authenticated to the dedicated Google
  Cloud project.
- The project and environment JSON selections have been reviewed.
- The Cloud region is `australia-southeast2` (Melbourne).

1. Validate the non-sensitive selection files.

   ```sh
   PYTHONPATH=src python tools/terraform_config.py \
     --config-root infra/terraform/projects/config \
     --project-config staylong.json \
     --environment-config sandbox.json
   ```

2. Create the remote-state bucket with local state.

   ```sh
   terraform -chdir=infra/terraform/bootstrap/state init -backend=false
   terraform -chdir=infra/terraform/bootstrap/state apply \
     -var='project_config=staylong.json' \
     -var='environment_config=sandbox.json'
   ```

   This local `terraform.tfstate` is intentionally not migrated. Keep an
   encrypted recovery copy outside the repository. The state bucket must never
   use itself as a backend.

3. Initialise the identity root against the created bucket.

   ```sh
   cp infra/terraform/backend.hcl.example infra/terraform/backend.hcl
   # Set bucket to the state bucket output from bootstrap/state.
   # Set prefix to staylong/sandbox/bootstrap-identity.
   terraform -chdir=infra/terraform/bootstrap/identity init \
     -backend-config=../../backend.hcl
   terraform -chdir=infra/terraform/bootstrap/identity apply \
     -var='project_config=staylong.json' \
     -var='environment_config=sandbox.json'
   ```

   If `bootstrap/identity` had already been applied with local state, run
   `terraform init -migrate-state -backend-config=../../backend.hcl` instead.
   Review the migration prompt and retain an encrypted local backup.

4. Record the WIF outputs as sandbox GitHub environment variables. Do not add
   service-account JSON keys or secrets to the repository.

5. GitHub Actions may now initialise `platform` and `app` with the bucket
   and their component-specific prefixes. The workflow, not a developer
   workstation, is the normal operator.

## Break-glass teardown

Do not destroy the state bucket as part of the ordinary `platform` or
`app` workflow.

1. Freeze GitHub Actions deployments and copy every remote state object to an
   encrypted, access-controlled recovery location.
2. Destroy `app`, then `platform`, using their remote GCS state.
3. Review and remove the WIF identities only after no workflow can access
   remaining infrastructure.
4. Use the retained local state for `bootstrap/state` to destroy the state
   bucket last.
5. Remove the local recovery copies only after the destruction has been
   independently verified.

A custom domain is not part of bootstrap. After a brand and domain are chosen,
Terraform will add the global HTTPS load balancer, Google-managed certificate,
Serverless NEG, and Cloud DNS records to the regular platform/application
lifecycle.

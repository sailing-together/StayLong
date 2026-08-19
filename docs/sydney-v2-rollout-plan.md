# Sydney v2 rollout plan

**Goal:** Create `staylong-sydney-v2` as a new private Cloud Run service whose
first revision uses the StayLong application image and a Secret Manager
reference, without placing a token value in Terraform state.

**Architecture:** The existing `staylong-sydney` service remains unchanged as
diagnostic evidence. A dedicated v2 Terraform component owns the new service
and its private invoker policy. A protected GitHub Actions deployment builds an
immutable image, adds a masked GitHub Environment token as a new Secret Manager
version, then invokes Terraform with the image reference to create or update
the v2 service.

**Constraints:**

- All GCP resources are created or changed by Terraform.
- The `STAYLONG_API_TOKEN` value is never an input to Terraform and never
  appears in configuration, plans, state, logs, source, or test fixtures.
- The service starts private; no `allUsers` binding is created.
- `staylong-runtime` can read only `staylong-api-token`; the deployment
  identity can only append a version to that secret.
- The first v2 revision must use an application image and Secret Manager
  reference at creation time, not a placeholder image followed by `gcloud run
  services update`.

## Task 1: Create the v2 Terraform application component

**Files:**

- Modify: `infra/terraform/modules/base/cloud_run_service/main.tf`
- Modify: `infra/terraform/modules/base/cloud_run_service/variables.tf`
- Create: `infra/terraform/components/sydney-v2-app/main.tf`
- Create: `infra/terraform/components/sydney-v2-app/variables.tf`
- Create: `infra/terraform/components/sydney-v2-app/outputs.tf`
- Create: `infra/terraform/components/sydney-v2-app/versions.tf`
- Create: `tests/infra/test_sydney_v2_app.py`

1. Write a failing infrastructure contract test that requires a `value_source`
   Secret Manager environment-variable reference and confirms v2 grants only
   the deployer service account the Cloud Run invoker role.
2. Run the focused test and confirm it fails because the component is absent.
3. Add an optional map of Secret Manager environment-variable references to the
   base Cloud Run module. The module must render `secret_key_ref` with the
   supplied secret identifier and version, while retaining the existing
   revision-template drift protection for historical services.
4. Add `sydney-v2-app`, accepting `project_config`, `environment_config`, and
   required `image_ref`. It must create `staylong-sydney-v2` with
   `STAYLONG_API_TOKEN` sourced from `staylong-api-token` version `latest` and
   no public invoker binding.
5. Run focused tests, full tests, `terraform fmt`, and backend-free Terraform
   validation. Commit the independently reviewable component.

## Task 2: Add a protected v2 deployment workflow

**Files:**

- Create: `.github/workflows/deploy-sydney-v2.yml`
- Modify: `tests/infra/test_terraform_modules.py`
- Modify: `docs/sydney-sandbox.md`

1. Write a failing contract test requiring the workflow to append the masked
   GitHub Environment token through `gcloud secrets versions add`, then call
   Terraform with an immutable image reference.
2. Build and publish an image tagged with a main-reachable commit SHA.
3. Authenticate as `staylong-app-deployer` only for image publishing and
   secret-version addition. Authenticate as the Terraform operator only for
   Terraform apply.
4. Initialise the `sydney-v2-app` remote state, plan with `image_ref`, apply
   that saved plan, and mint a Cloud Run ID token for a private smoke test.
5. Never pass the token as a Terraform variable or print it. Commit this
   workflow as its own PR.

## Task 3: Deploy and verify the first v2 revision

1. Confirm the `sandbox` GitHub Environment contains a non-empty masked
   `STAYLONG_API_TOKEN` secret before dispatching the protected workflow.
2. Dispatch the v2 deployment workflow from `main`.
3. Verify the workflow creates a Secret Manager version, creates the v2 Cloud
   Run service, and receives HTTP 200 from `/healthz` using an identity token.
4. Record the immutable image digest, Cloud Run URL, and smoke-test result in
   `docs/release-evidence.md`; do not record the token.

## Review checklist

- Task 1 has a test proving secret references use `value_source`, not plaintext
  environment values.
- Task 2 has a test proving the token is not supplied to Terraform.
- Every PR passes Python, React/TypeScript, Terraform static validation, and
  Trivy before merge.
- Task 3 is not attempted if the v2 service or private smoke test is not ready.

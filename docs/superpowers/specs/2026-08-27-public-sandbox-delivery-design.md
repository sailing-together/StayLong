# Public Sandbox Delivery Automation Design

## Purpose

SAI-50 makes the StayLong public sandbox repeatable to deploy, safe to tear
down, and straightforward for a judge to verify. The repository already has
the anonymous public API, React public mode, Terraform component, two-session
smoke script, CI matrix, and initial release checklist. This change completes
the missing delivery control plane and turns each manual run into durable
evidence.

## Scope

The change adds one dedicated manual GitHub Actions workflow for the
`public-sandbox` Terraform component. It supports exactly two operations:
`deploy` and `destroy`. It also adds structural regression tests for the
workflow and updates release documentation with the exact human setup and
evidence-reproduction steps.

The change does not alter the private Sydney deployment, broaden the general
Terraform lifecycle workflow, create service-account keys, or introduce a
second public-sandbox runtime.

## Workflow Interface and Guardrails

Create `.github/workflows/public-sandbox-control.yml` with these dispatch
inputs:

- `operation`: a required choice containing only `deploy` and `destroy`.
- `commit_sha`: the immutable revision to deploy. It is required for deploy
  and must resolve to a commit reachable from `origin/main`. Destroy ignores
  it.
- `confirmation`: deploy accepts only `DEPLOY_PUBLIC_SANDBOX`; destroy accepts
  only `DESTROY_PUBLIC_SANDBOX`.

The workflow uses `permissions: contents: read` and `id-token: write`, the
protected GitHub `sandbox` environment, and a non-cancelling concurrency group
shared by deploy and destroy. These controls serialize mutations and keep the
existing human approval boundary.

The workflow uses `google-github-actions/auth` with
`GCP_WIF_PROVIDER`. Image publishing uses `GCP_DEPLOY_SERVICE_ACCOUNT` and
Terraform mutation uses `GCP_TERRAFORM_OPERATOR_SERVICE_ACCOUNT`. No JSON key,
credential file, API token, or private-service identity is accepted as an
input or artifact.

## Deployment Flow

The deploy job performs the following sequence:

1. Check out `commit_sha` with full history and prove it is an ancestor of
   `origin/main`.
2. Run the repository release gates: Python Ruff and pytest, frontend lint,
   test and production build, Terraform configuration/schema validation and
   formatting, and Trivy filesystem/IaC scanning.
3. Authenticate with WIF, build the checked-out revision, push it to the
   existing Sydney Artifact Registry repository, scan the immutable image,
   and record the resulting `repository@sha256:...` reference.
4. Validate the fixed configuration pair
   `staylong-public-sandbox.json` plus `stay-long-sydney-sandbox.json` and initialize only
   `infra/terraform/components/public-sandbox` with the remote-state prefix
   `staylong/sydney-sandbox/public-sandbox`.
5. Plan and apply the component using the immutable image reference. The saved
   Terraform plan is the only input to apply.
6. Read `public_url` from Terraform output and run
   `tools/public_sandbox_smoke.py` against it. This smoke uses anonymous cookie
   sessions, proves cross-session isolation, executes the real workflow, and
   requires no shared API token.
7. Write a machine-readable evidence JSON file containing the source commit,
   image digest, Terraform component and state prefix, public URL, smoke result,
   operation, repository, workflow run URL, and timestamp. Upload it with the
   smoke output and immutable image reference as a retained artifact.

Deploy evidence is uploaded with `if: always()` so a failed smoke or apply
still leaves useful diagnostics. Sensitive environment values and credentials
are never copied into evidence.

## Teardown Flow

Destroy is a separate job selected by the same manual workflow. It validates
`DESTROY_PUBLIC_SANDBOX` before WIF authentication, validates the fixed JSON
configuration pair, initializes the same component and state prefix, creates a
destroy plan, and applies that saved destroy plan. It cannot accept another
component or state prefix.

The teardown job records the operation, component, source revision, workflow
run URL, timestamp, and Terraform result in a machine-readable evidence
artifact. The underlying state bucket, shared Artifact Registry repository,
WIF provider, and private StayLong services remain outside this component and
are not destroyed.

## Existing Smoke Workflow

The standalone `.github/workflows/public-sandbox-smoke.yml` remains available
for verification without mutation. Its hard-coded service name and region are
aligned with the Terraform component, and its WIF authentication remains
keyless. The control workflow calls the smoke script directly after deploy so
successful deployment evidence always includes the end-to-end result.

## Tests

Add `tests/infra/test_public_sandbox_control_workflow.py` as a structural
contract test. It verifies:

- the workflow exposes only deploy and destroy operations;
- exact, distinct confirmation phrases guard both mutations;
- deploy commits must be reachable from `main`;
- WIF and the protected `sandbox` environment are used;
- only the public-sandbox component, configuration pair, and state prefix are
  referenced by Terraform mutation steps;
- deploy uses an immutable image digest, performs Trivy scanning, applies a
  saved plan, runs the anonymous smoke script, and uploads evidence;
- destroy applies a saved destroy plan and uploads evidence;
- no service-account key, private API token, or private smoke tool appears in
  the workflow.

The complete Python suite, frontend lint/tests/build, Ruff, Terraform format
check, and workflow contract test run locally before the branch is proposed.

## Documentation and Human Setup

Update `docs/release-evidence.md` with:

- the GitHub repository variables required by the workflow:
  `GCP_PROJECT_ID`, `GCP_WIF_PROVIDER`, `GCP_DEPLOY_SERVICE_ACCOUNT`, and
  `GCP_TERRAFORM_OPERATOR_SERVICE_ACCOUNT`;
- the requirement that the `sandbox` GitHub environment has reviewers;
- the one-time GCP prerequisites: WIF trust for
  `sailing-together/StayLong`, remote state, Artifact Registry, and the scoped
  deployer/operator identities;
- exact deploy, smoke-only, evidence-download, and destroy instructions;
- the evidence fields a judge can correlate with the GitHub run, commit,
  image digest, Cloud Run URL, and anonymous isolation result.

## Failure Handling

Input, ancestry, configuration, format, security, build, plan, apply, and smoke
failures stop deployment at their boundary. Terraform apply is never attempted
after a failed gate. Destroy cannot run after an invalid confirmation. Evidence
upload uses `if: always()` and marks the recorded result from the job status,
while never claiming a failed run succeeded.

The workflow does not automatically roll back a failed deployment because an
automatic destroy could remove a previously working sandbox. Operators use
the explicit destroy operation after inspecting the retained evidence.

## Acceptance Mapping

- Keyless delivery: all GCP access uses GitHub OIDC and WIF.
- Explicit mutation: deploy and destroy require operation-specific phrases and
  protected-environment approval.
- Public end-to-end proof: the deploy flow runs the existing two-session
  anonymous smoke against the Terraform output URL.
- Complete checks: backend, frontend, Terraform/schema, container and
  filesystem/IaC security gates precede apply.
- Judge-verifiable evidence: immutable revision, image, infrastructure target,
  URL and smoke result are retained together with human setup instructions.

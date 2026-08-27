# Public Sandbox Delivery Automation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a keyless, manually confirmed GitHub Actions control that deploys or destroys only the public sandbox and retains judge-verifiable end-to-end evidence.

**Architecture:** A dedicated `public-sandbox-control.yml` workflow owns both mutation paths behind distinct confirmation phrases and the protected `sandbox` environment. Deploy validates the selected `main` commit, runs release gates, publishes and scans an immutable image, applies only the public-sandbox Terraform component, runs the existing anonymous two-session smoke, and uploads evidence; destroy reuses the fixed component/state boundary and uploads teardown evidence.

**Tech Stack:** GitHub Actions, GitHub OIDC, Google Cloud Workload Identity Federation, Docker Buildx, Trivy, Terraform, Python 3.12, Ruff, pytest, React/Vitest, npm, Artifact Registry, Cloud Run.

**Spec:** `docs/superpowers/specs/2026-08-27-public-sandbox-delivery-design.md`

## Global Constraints

- GCP authentication uses GitHub OIDC and WIF only; no service-account JSON keys.
- The protected GitHub environment is exactly `sandbox`.
- Terraform mutation is fixed to `infra/terraform/components/public-sandbox`.
- Terraform configuration is fixed to `staylong-public-sandbox.json` and `sandbox.json`.
- Remote state prefix is exactly `staylong/sandbox/public-sandbox`.
- Deploy requires `DEPLOY_PUBLIC_SANDBOX`; destroy requires `DESTROY_PUBLIC_SANDBOX`.
- A deploy revision must be reachable from `origin/main`.
- The deployed image must use an immutable `@sha256:` reference.
- Public smoke uses `tools/public_sandbox_smoke.py` without an API token.
- A failed deployment is not automatically destroyed.

---

### Task 1: Lock the public-sandbox workflow safety contract

**Files:**
- Create: `tests/infra/test_public_sandbox_control_workflow.py`

**Interfaces:**
- Consumes: the approved workflow contract from the spec.
- Produces: structural regression tests that constrain `.github/workflows/public-sandbox-control.yml` before it exists.

- [ ] **Step 1: Write the failing workflow contract tests**

Create `tests/infra/test_public_sandbox_control_workflow.py` with focused source-level assertions:

```python
from pathlib import Path


WORKFLOW = Path(".github/workflows/public-sandbox-control.yml")


def workflow_source() -> str:
    return WORKFLOW.read_text()


def test_public_sandbox_control_has_explicit_mutation_guards() -> None:
    source = workflow_source()
    assert "options: [deploy, destroy]" in source
    assert "DEPLOY_PUBLIC_SANDBOX" in source
    assert "DESTROY_PUBLIC_SANDBOX" in source
    assert "environment: sandbox" in source
    assert "cancel-in-progress: false" in source


def test_public_sandbox_control_is_keyless_and_main_reachable() -> None:
    source = workflow_source()
    assert "id-token: write" in source
    assert "google-github-actions/auth@" in source
    assert "GCP_WIF_PROVIDER" in source
    assert "git merge-base --is-ancestor" in source
    assert "service-account-key" not in source.lower()
    assert "credentials_json" not in source
    assert "STAYLONG_API_TOKEN" not in source


def test_deploy_is_immutable_scanned_and_smoke_tested() -> None:
    source = workflow_source()
    assert "docker buildx build" in source
    assert "containerimage.digest" in source
    assert "@${digest}" in source or "@$digest" in source
    assert "aquasecurity/trivy-action@" in source
    assert "terraform -chdir=\"$COMPONENT_PATH\" apply -input=false tfplan" in source
    assert "tools/public_sandbox_smoke.py" in source
    assert "actions/upload-artifact@" in source


def test_terraform_scope_cannot_escape_public_sandbox() -> None:
    source = workflow_source()
    assert "COMPONENT_PATH: infra/terraform/components/public-sandbox" in source
    assert "PROJECT_CONFIG: staylong-public-sandbox.json" in source
    assert "ENVIRONMENT_CONFIG: sandbox.json" in source
    assert "STATE_PREFIX: staylong/sandbox/public-sandbox" in source
    assert "inputs.component" not in source
    assert "tools/cloudrun_smoke.py" not in source


def test_destroy_uses_a_saved_plan_and_retains_evidence() -> None:
    source = workflow_source()
    assert "terraform -chdir=\"$COMPONENT_PATH\" plan -destroy -input=false -out=tfplan" in source
    assert "terraform -chdir=\"$COMPONENT_PATH\" apply -input=false tfplan" in source
    assert "if: ${{ always() }}" in source
    assert "public-sandbox-destroy-evidence" in source
```

- [ ] **Step 2: Run the contract tests and verify RED**

Run:

```bash
UV_CACHE_DIR=/private/tmp/staylong-uv-cache uv run --extra dev --extra agents pytest tests/infra/test_public_sandbox_control_workflow.py -q
```

Expected: FAIL with `FileNotFoundError` for `.github/workflows/public-sandbox-control.yml`.

- [ ] **Step 3: Commit the failing contract**

```bash
git add tests/infra/test_public_sandbox_control_workflow.py
git commit -m "test: define public sandbox delivery controls"
```

---

### Task 2: Implement deploy, destroy, and evidence automation

**Files:**
- Create: `.github/workflows/public-sandbox-control.yml`
- Test: `tests/infra/test_public_sandbox_control_workflow.py`

**Interfaces:**
- Consumes: `tools/terraform_config.py`, `tools/public_sandbox_smoke.py`, `infra/terraform/components/public-sandbox`, repository variables `GCP_PROJECT_ID`, `GCP_WIF_PROVIDER`, `GCP_DEPLOY_SERVICE_ACCOUNT`, and `GCP_TERRAFORM_OPERATOR_SERVICE_ACCOUNT`.
- Produces: manual `deploy` and `destroy` operations plus `public-sandbox-*-evidence-<run-id>` artifacts.

- [ ] **Step 1: Create the fixed workflow shell and confirmation gate**

Create `.github/workflows/public-sandbox-control.yml` with this top-level contract:

```yaml
name: Control StayLong public sandbox

on:
  workflow_dispatch:
    inputs:
      operation:
        description: "Deploy or destroy the public sandbox"
        required: true
        type: choice
        options: [deploy, destroy]
      commit_sha:
        description: "Commit reachable from main (required for deploy)"
        required: false
        type: string
      confirmation:
        description: "Enter DEPLOY_PUBLIC_SANDBOX or DESTROY_PUBLIC_SANDBOX"
        required: true
        type: string

permissions:
  contents: read
  id-token: write

concurrency:
  group: staylong-public-sandbox-control
  cancel-in-progress: false

env:
  COMPONENT_PATH: infra/terraform/components/public-sandbox
  PROJECT_CONFIG: staylong-public-sandbox.json
  ENVIRONMENT_CONFIG: sandbox.json
  STATE_PREFIX: staylong/sandbox/public-sandbox
  REGION: australia-southeast1
  REPOSITORY: staylong-sydney
  SERVICE: staylong-public-sandbox
```

Create separate `deploy` and `destroy` jobs with job-level `if` expressions,
`runs-on: ubuntu-latest`, and `environment: sandbox`. The first step of each
job compares `inputs.confirmation` with its exact phrase before any auth step.

- [ ] **Step 2: Implement revision verification and release gates**

For deploy, check out `inputs.commit_sha` with `fetch-depth: 0`, reject an empty
SHA, fetch `origin/main`, and run:

```bash
deployment_sha="$(git rev-parse HEAD)"
git merge-base --is-ancestor "$deployment_sha" origin/main
echo "sha=$deployment_sha" >> "$GITHUB_OUTPUT"
```

Before image publication, use Python 3.12 plus `uv sync --extra dev --extra
agents`, Node 24 plus `npm ci`, Terraform setup, and these exact gates:

```bash
uv run ruff check .
uv run pytest
npm --prefix frontend run lint
npm --prefix frontend test
npm --prefix frontend run build
PYTHONPATH=src python tools/terraform_config.py \
  --project-config "$PROJECT_CONFIG" \
  --environment-config "$ENVIRONMENT_CONFIG" \
  --output "$RUNNER_TEMP/terraform-config.json"
terraform fmt -check -recursive infra/terraform
```

Add `aquasecurity/trivy-action` filesystem scanning with scanners
`vuln,secret,misconfig`, severities `HIGH,CRITICAL`, and `exit-code: "1"`.

- [ ] **Step 3: Publish and scan the immutable application image**

Authenticate through WIF as `${{ vars.GCP_DEPLOY_SERVICE_ACCOUNT }}`, configure
the regional Docker registry, and use Buildx with a metadata file. Derive the
digest with:

```bash
digest="$(jq -er '."containerimage.digest"' "$metadata_file")"
printf '%s\n' "$digest" | grep -Eq '^sha256:[0-9a-f]{64}$'
image_ref="$image_repository@$digest"
echo "image_ref=$image_ref" >> "$GITHUB_OUTPUT"
printf '%s\n' "$image_ref" > "$RUNNER_TEMP/image-ref.txt"
```

Run a second Trivy scan with `scan-type: image`, the immutable output reference,
scanners `vuln,secret,misconfig`, severities `HIGH,CRITICAL`, and exit code 1.

- [ ] **Step 4: Apply only the public-sandbox Terraform component**

Authenticate again through WIF as
`${{ vars.GCP_TERRAFORM_OPERATOR_SERVICE_ACCOUNT }}`. Read
`state_bucket_name` from the validated JSON, initialize `$COMPONENT_PATH` with
`$STATE_PREFIX`, format-check and validate it, then save and apply this plan:

```bash
terraform -chdir="$COMPONENT_PATH" plan -input=false -out=tfplan \
  -var="project_config=$PROJECT_CONFIG" \
  -var="environment_config=$ENVIRONMENT_CONFIG" \
  -var="image_ref=${{ steps.image.outputs.image_ref }}"
terraform -chdir="$COMPONENT_PATH" apply -input=false tfplan
```

Read the URL from `terraform -chdir="$COMPONENT_PATH" output -raw public_url`,
write it to `$GITHUB_OUTPUT`, and never reconstruct it from a service name.

- [ ] **Step 5: Run anonymous smoke and retain deploy evidence**

Install only the smoke dependency and preserve output with `tee`:

```bash
python -m pip install requests
python tools/public_sandbox_smoke.py \
  --url "${{ steps.service.outputs.url }}" \
  | tee "$RUNNER_TEMP/public-sandbox-smoke.txt"
```

Create `$RUNNER_TEMP/public-sandbox-evidence/deploy-evidence.json` with `jq -n`
and fields `operation`, `result`, `repository`, `commit_sha`, `image_ref`,
`terraform_component`, `state_prefix`, `public_url`, `workflow_run_url`, and
`recorded_at`. Copy the image reference and smoke output into the same directory.
Upload the directory under `if: ${{ always() }}` as
`public-sandbox-deploy-evidence-${{ github.run_id }}` with
`if-no-files-found: error`.

- [ ] **Step 6: Implement saved-plan destruction and teardown evidence**

Destroy checks out the workflow revision, validates the configuration pair,
authenticates through WIF as the Terraform operator, initializes the exact same
backend, and executes:

```bash
terraform -chdir="$COMPONENT_PATH" plan -destroy -input=false -out=tfplan \
  -var="project_config=$PROJECT_CONFIG" \
  -var="environment_config=$ENVIRONMENT_CONFIG" \
  -var="image_ref=gcr.io/google-samples/hello-app@sha256:9d06f9448b1f377e8ed6e977f9f3f14f2c9f23f0b690aad8c29d90dca69d632a"
terraform -chdir="$COMPONENT_PATH" apply -input=false tfplan
```

The placeholder digest is syntactically immutable and is used only to satisfy
the Terraform input during a state-driven destroy plan; it is never deployed.
Create a teardown JSON file with `operation`, `result`, `repository`,
`source_revision`, `terraform_component`, `state_prefix`, `workflow_run_url`,
and `recorded_at`. Upload it under `if: ${{ always() }}` as
`public-sandbox-destroy-evidence-${{ github.run_id }}`.

- [ ] **Step 7: Run workflow contract tests and verify GREEN**

```bash
UV_CACHE_DIR=/private/tmp/staylong-uv-cache uv run --extra dev --extra agents pytest tests/infra/test_public_sandbox_control_workflow.py -q
```

Expected: all public-sandbox workflow contract tests PASS.

- [ ] **Step 8: Run YAML-adjacent repository checks**

```bash
UV_CACHE_DIR=/private/tmp/staylong-uv-cache uv run --extra dev --extra agents ruff check .
UV_CACHE_DIR=/private/tmp/staylong-uv-cache uv run --extra dev --extra agents pytest tests/infra tests/tools -q
terraform -chdir=infra/terraform fmt -check -recursive
```

Expected: all commands exit 0.

- [ ] **Step 9: Commit the workflow**

```bash
git add .github/workflows/public-sandbox-control.yml tests/infra/test_public_sandbox_control_workflow.py
git commit -m "feat: automate public sandbox lifecycle"
```

---

### Task 3: Align standalone smoke and release evidence

**Files:**
- Modify: `.github/workflows/public-sandbox-smoke.yml`
- Modify: `docs/release-evidence.md`
- Modify: `tests/infra/test_public_sandbox_control_workflow.py`

**Interfaces:**
- Consumes: the deployed `staylong-public-sandbox` service in
  `australia-southeast1` and the four WIF repository variables.
- Produces: a smoke-only verification path and exact operator/judge runbook.

- [ ] **Step 1: Add a failing regression for standalone smoke alignment**

Append this test:

```python
def test_standalone_smoke_targets_the_public_sandbox_component() -> None:
    source = Path(".github/workflows/public-sandbox-smoke.yml").read_text()
    assert "SERVICE: staylong-public-sandbox" in source
    assert "REGION: australia-southeast1" in source
    assert "tools/public_sandbox_smoke.py" in source
    assert "STAYLONG_API_TOKEN" not in source
```

- [ ] **Step 2: Run the new test and verify RED**

```bash
UV_CACHE_DIR=/private/tmp/staylong-uv-cache uv run --extra dev --extra agents pytest tests/infra/test_public_sandbox_control_workflow.py::test_standalone_smoke_targets_the_public_sandbox_component -q
```

Expected: FAIL because the existing service is
`staylong-sydney-public-sandbox`.

- [ ] **Step 3: Align the standalone smoke workflow**

In `.github/workflows/public-sandbox-smoke.yml`, remove unused
`PROJECT_CONFIG` and `ENVIRONMENT_CONFIG` environment values and set:

```yaml
env:
  REGION: australia-southeast1
  SERVICE: staylong-public-sandbox
```

Keep the existing exact confirmation, protected environment, WIF auth, URL
lookup, and token-free smoke command unchanged.

- [ ] **Step 4: Document human setup and evidence reproduction**

Update the public-sandbox sections of `docs/release-evidence.md` to name:

1. repository variables `GCP_PROJECT_ID`, `GCP_WIF_PROVIDER`,
   `GCP_DEPLOY_SERVICE_ACCOUNT`, and
   `GCP_TERRAFORM_OPERATOR_SERVICE_ACCOUNT`;
2. required reviewers on the GitHub `sandbox` environment;
3. WIF trust for `sailing-together/StayLong`, remote state, Artifact Registry,
   and scoped deployer/operator identities as one-time prerequisites;
4. the exact deploy confirmation `DEPLOY_PUBLIC_SANDBOX` and a `main` commit;
5. the independent `RUN_PUBLIC_SANDBOX_SMOKE` operation;
6. evidence artifact contents and correlation fields;
7. the exact destroy confirmation `DESTROY_PUBLIC_SANDBOX` and statement that
   only the public-sandbox Terraform component is removed.

Replace any checked release item that is not yet proven by a live run with an
unchecked item; documentation must distinguish implemented automation from
captured production evidence.

- [ ] **Step 5: Verify standalone smoke alignment and documentation**

```bash
UV_CACHE_DIR=/private/tmp/staylong-uv-cache uv run --extra dev --extra agents pytest tests/infra/test_public_sandbox_control_workflow.py tests/tools/test_public_sandbox_smoke.py -q
rg -n "GCP_WIF_PROVIDER|DEPLOY_PUBLIC_SANDBOX|RUN_PUBLIC_SANDBOX_SMOKE|DESTROY_PUBLIC_SANDBOX|public-sandbox-deploy-evidence" docs/release-evidence.md
```

Expected: tests PASS and every required setup/control term appears in the
release evidence document.

- [ ] **Step 6: Commit smoke alignment and documentation**

```bash
git add .github/workflows/public-sandbox-smoke.yml docs/release-evidence.md tests/infra/test_public_sandbox_control_workflow.py
git commit -m "docs: make public sandbox evidence reproducible"
```

---

### Task 4: Complete release verification

**Files:**
- Verify: `.github/workflows/public-sandbox-control.yml`
- Verify: `.github/workflows/public-sandbox-smoke.yml`
- Verify: `docs/release-evidence.md`
- Verify: `tests/infra/test_public_sandbox_control_workflow.py`

**Interfaces:**
- Consumes: all SAI-50 deliverables.
- Produces: a clean branch ready for review; no live GCP mutation is performed locally.

- [ ] **Step 1: Run complete Python quality and tests**

```bash
UV_CACHE_DIR=/private/tmp/staylong-uv-cache uv run --extra dev --extra agents ruff check .
UV_CACHE_DIR=/private/tmp/staylong-uv-cache uv run --extra dev --extra agents pytest
```

Expected: Ruff passes and all Python tests pass with zero failures.

- [ ] **Step 2: Run complete frontend quality, tests, and build**

```bash
npm --prefix frontend run lint
npm --prefix frontend test -- --run
npm --prefix frontend run build
```

Expected: all three commands exit 0.

- [ ] **Step 3: Run Terraform static verification**

```bash
terraform -chdir=infra/terraform fmt -check -recursive
terraform -chdir=infra/terraform/components/public-sandbox init -backend=false -input=false
terraform -chdir=infra/terraform/components/public-sandbox validate
```

Expected: formatting and validation pass.

- [ ] **Step 4: Review the exact branch diff**

```bash
git diff --check main...HEAD
git diff --stat main...HEAD
git status --short --branch
```

Expected: no whitespace errors, only SAI-50 files are changed, and the worktree
is clean.

- [ ] **Step 5: Record the verification boundary**

Do not dispatch the workflow from the feature branch. Record in the PR that
local/static checks are green and that the first live deploy must use a merged
`main` commit, protected-environment approval, and the exact confirmation. The
live run and downloaded artifact are the final Devpost evidence, not a
prerequisite for reviewing the workflow implementation.

## Plan Self-Review

- Spec coverage: Task 1 fixes the safety contract; Task 2 implements WIF deploy,
  destroy, checks, smoke, and evidence; Task 3 aligns independent smoke and
  documents human setup; Task 4 verifies every local acceptance boundary.
- Placeholder scan: no deferred implementation markers or ambiguous
  “appropriate” steps remain.
- Type and name consistency: component path, JSON configuration pair, state
  prefix, confirmation phrases, repository variables, smoke command, and
  artifact names match across all tasks.

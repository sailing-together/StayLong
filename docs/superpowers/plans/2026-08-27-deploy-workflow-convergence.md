# Deployment Workflow Convergence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Sydney v2 workflow the sole automatic application deployment path and rebuild its runtime with patched Alpine packages.

**Architecture:** `deploy-sydney-v2.yml` builds, scans, and Terraform-applies `staylong-sydney-v2`. The older deploy workflows target retired resources and must not run on application changes. The Dockerfile retains an immutable official Python base and upgrades Alpine security packages before dependency installation.

**Tech Stack:** GitHub Actions, Docker Buildx, Trivy, Python 3.12, Alpine Linux, pytest.

**Spec:** `docs/public-sandbox-implementation-plan.md`

## Global Constraints

- The only automatic main-branch application deployment workflow is `.github/workflows/deploy-sydney-v2.yml`.
- Terraform remains the only mechanism that updates the Cloud Run service.
- Trivy remains fail-closed for HIGH and CRITICAL findings; no ignore rule is added.
- The runtime base is digest-pinned and runs as non-root user `staylong`.

---

### Task 1: Prove the deployment topology contract

**Files:**

- Modify: `tests/infra/test_sydney_v2_deploy_workflow.py`
- Delete: `.github/workflows/deploy.yml`
- Delete: `.github/workflows/deploy-sydney.yml`

**Interfaces:**

- Consumes: canonical `.github/workflows/deploy-sydney-v2.yml`.
- Produces: regression coverage preventing retired automatic deployment paths.

- [ ] **Step 1: Write the failing test**

```python
def test_v2_workflow_is_the_only_automatic_application_deployment_path() -> None:
    assert WORKFLOW.exists()
    assert not Path(".github/workflows/deploy.yml").exists()
    assert not Path(".github/workflows/deploy-sydney.yml").exists()
```

- [ ] **Step 2: Run the focused test**

Run: `python -m pytest tests/infra/test_sydney_v2_deploy_workflow.py::test_v2_workflow_is_the_only_automatic_application_deployment_path -v`

Expected: FAIL because both legacy workflow files exist.

- [ ] **Step 3: Remove only the retired workflow definitions**

Delete `.github/workflows/deploy.yml` and `.github/workflows/deploy-sydney.yml`; do not alter diagnostics, controls, Terraform lifecycle, or the v2 workflow.

- [ ] **Step 4: Re-run the focused test**

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/infra/test_sydney_v2_deploy_workflow.py
git rm .github/workflows/deploy.yml .github/workflows/deploy-sydney.yml
git commit -m "fix: converge automatic deployments on sydney v2"
```

### Task 2: Build with patched Alpine packages

**Files:**

- Modify: `tests/infra/test_sydney_v2_deploy_workflow.py`
- Modify: `Dockerfile`

**Interfaces:**

- Consumes: `python:3.12-alpine3.24@sha256:d09d15e60962ca365d1cd544a48773bac9d33f2fb1b00f2aa0deec78ade7dc31`.
- Produces: an image with upgraded OpenSSL and SQLite packages before Trivy scans it.

- [ ] **Step 1: Write the failing test**

```python
def test_cloud_run_runtime_applies_current_alpine_security_updates() -> None:
    dockerfile = DOCKERFILE.read_text()
    assert "python:3.12-alpine3.24@sha256:d09d15e60962ca365d1cd544a48773bac9d33f2fb1b00f2aa0deec78ade7dc31" in dockerfile
    assert "RUN apk upgrade --no-cache" in dockerfile
```

- [ ] **Step 2: Run the focused test**

Run: `python -m pytest tests/infra/test_sydney_v2_deploy_workflow.py::test_cloud_run_runtime_applies_current_alpine_security_updates -v`

Expected: FAIL because the Dockerfile is Alpine 3.23 and does not upgrade packages.

- [ ] **Step 3: Apply the minimal Dockerfile change**

Use the pinned Alpine 3.24 Python image and prepend `apk upgrade --no-cache` to the existing dependency-install layer. Keep the non-root user, Granian command, and dependency installation unchanged.

- [ ] **Step 4: Verify**

Run: `python -m pytest tests/infra/test_sydney_v2_deploy_workflow.py -v`

Expected: PASS.

- [ ] **Step 5: Build and inspect package versions**

Run: `docker build --tag staylong-deploy-fix:local . && docker run --rm staylong-deploy-fix:local sh -ceu 'apk list --installed | grep -E "^(libcrypto3|libssl3|sqlite-libs)-"'`

Expected: OpenSSL `3.5.8-r0` and SQLite `3.53.4-r0` or newer.

### Task 3: Verify the full contract

**Files:**

- Verify: `.github/workflows/deploy-sydney-v2.yml`
- Verify: `Dockerfile`
- Verify: `tests/infra/test_sydney_v2_deploy_workflow.py`

- [ ] **Step 1: Run focused infrastructure tests**

Run: `python -m pytest tests/infra/test_sydney_v2_deploy_workflow.py tests/infra/test_sydney_v2_app.py -v`

Expected: PASS.

- [ ] **Step 2: Run the project suite**

Run: `python -m pytest -q && ruff check .`

Expected: PASS with no lint violations.

- [ ] **Step 3: Review the scoped diff**

Run: `git diff origin/main -- .github/workflows Dockerfile tests/infra/test_sydney_v2_deploy_workflow.py`

Expected: two retired workflows removed, runtime security update present, and Trivy remains fail-closed.


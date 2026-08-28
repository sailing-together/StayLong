# Public Edge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Serve the StayLong public demo from `https://staylonghome.com` through a Terraform-managed global HTTPS edge, then make that edge the only public Cloud Run path.

**Architecture:** A `public-edge` Terraform component owns Cloudflare DNS, global IP, TLS, ALB, and Cloud Run serverless NEG in its own state. The existing `public-sandbox` component remains the only Cloud Run owner and applies the later ingress lockdown from checked-in configuration. GitHub Actions uses GCP OIDC/WIF and the scoped Cloudflare DNS secret only at runtime.

**Tech Stack:** Terraform >= 1.9; hashicorp/google ~> 6; cloudflare/cloudflare ~> 5; Google Cloud Load Balancing; Cloud Run; GitHub Actions; pytest; Trivy.

**Spec:** `docs/architecture/public-edge-design.md`

## Global Constraints

- Canonical hostname: `staylonghome.com`; both HTTP and `www.staylonghome.com` redirect to it.
- Public demo boundaries remain unchanged: temporary sessions; no payments, government submission, real email/calendar/SMS, clinical diagnosis, or eligibility decision.
- GCP and Cloudflare DNS resources are Terraform-owned. Do not create them manually.
- `CLOUDFLARE_API_TOKEN` is only a GitHub `sandbox` environment secret. It must never enter Git, Terraform input/output/state, logs, test fixtures, or docs.
- Cloudflare records are DNS-only while Google manages the certificate.
- Phase A retains the `.run.app` endpoint. Phase B changes ingress only after branded-domain smoke succeeds.
- Every mutation uses a main-reachable SHA, typed confirmation, saved Terraform plan, and evidence artifact.
- Destroy never deletes the Cloudflare domain registration.

---

## File Structure

| Path | Responsibility |
| --- | --- |
| `infra/terraform/components/public-edge/` | Independent ALB, NEG, TLS, DNS Terraform root. |
| `infra/terraform/projects/config/staylong-public-sandbox.json` | Non-secret domain, zone ID, and lockdown toggle. |
| `infra/terraform/projects/config/schemas/project.schema.json` | Validates the new config fields. |
| `infra/terraform/modules/foundations/github_federation/variables.tf` | Least-privilege Terraform operator edge roles. |
| `infra/terraform/components/public-sandbox/main.tf` | Cloud Run ingress/default-URL Phase-B behavior. |
| `.github/workflows/public-domain-control.yml` | Protected provision, lockdown, and destroy lifecycle. |
| `tools/public_domain_smoke.py` | Canonical-domain anonymous workflow smoke check. |
| `tests/infra/test_public_edge_component.py` | Edge ownership and Terraform structural contracts. |
| `tests/infra/test_public_domain_control_workflow.py` | Workflow safety contracts. |
| `tests/tools/test_public_domain_smoke.py` | Smoke tool HTTP behavior. |
| `docs/runbooks/public-edge-operations.md` | Non-secret operations and rollback runbook. |

## Task 1: Define and validate non-secret public-edge configuration

**Files:**
- Modify: `infra/terraform/projects/config/staylong-public-sandbox.json`
- Modify: `infra/terraform/projects/config/schemas/project.schema.json`
- Modify: `tests/infra/test_terraform_config.py`
- Modify: `tests/infra/test_stay_long_project_config.py`

**Interfaces:**
- Consumes: `resolve_config(config_root, project_config, environment_config) -> dict[str, object]`.
- Produces: `public_domain: str`, `www_public_domain: str`, `cloudflare_zone_id: str`, and `public_edge_lockdown_enabled: bool`.

- [ ] **Step 1: Write failing tests**

```python
config = resolve_config(CONFIG_ROOT, "staylong-public-sandbox.json", "stay-long-sydney-sandbox.json")
assert config["public_domain"] == "staylonghome.com"
assert config["www_public_domain"] == "www.staylonghome.com"
assert config["public_edge_lockdown_enabled"] is False
assert len(config["cloudflare_zone_id"]) == 32
```

Add a copied-config test with `cloudflare_api_token` and assert `ConfigurationError` contains `"secret-like"`.

- [ ] **Step 2: Run tests red**

Run: `.venv/bin/python -m pytest tests/infra/test_terraform_config.py tests/infra/test_stay_long_project_config.py -q`

Expected: FAIL because the new keys are absent or rejected.

- [ ] **Step 3: Add the smallest schema and JSON change**

Add these schema properties:

```json
"public_domain": {"type": "string", "pattern": "^[a-z0-9][a-z0-9-]{0,61}[a-z0-9]\\.com$"},
"www_public_domain": {"type": "string", "pattern": "^www\\.[a-z0-9][a-z0-9-]{0,61}[a-z0-9]\\.com$"},
"cloudflare_zone_id": {"type": "string", "pattern": "^[a-f0-9]{32}$"},
"public_edge_lockdown_enabled": {"type": "boolean"}
```

Set the first two values, copy the non-secret Zone ID from Cloudflare Dashboard → Websites → `staylonghome.com` → Overview, and set the lockdown boolean to `false`. Do not add any Token key.

- [ ] **Step 4: Run tests green and validate config**

Run:

```bash
.venv/bin/python -m pytest tests/infra/test_terraform_config.py tests/infra/test_stay_long_project_config.py -q
PYTHONPATH=src .venv/bin/python tools/terraform_config.py --project-config staylong-public-sandbox.json --environment-config stay-long-sydney-sandbox.json
```

Expected: PASS; output has domain fields and no secret-like key.

- [ ] **Step 5: Commit**

```bash
git add infra/terraform/projects/config tests/infra/test_terraform_config.py tests/infra/test_stay_long_project_config.py
git commit -m "feat: define public edge configuration"
```

## Task 2: Declare least-privilege Terraform operator roles

**Files:**
- Modify: `infra/terraform/modules/foundations/github_federation/variables.tf`
- Modify: `tests/infra/test_terraform_modules.py`
- Create: `docs/runbooks/public-edge-operations.md`

**Interfaces:**
- Consumes: `operator_project_roles: list(string)` in `github_federation`.
- Produces: four additional exact roles: `roles/compute.loadBalancerAdmin`, `roles/compute.networkAdmin`, `roles/compute.instanceAdmin.v1`, and `roles/iam.securityAdmin`.

- [ ] **Step 1: Write failing role contract**

```python
for role in (
    "roles/compute.loadBalancerAdmin",
    "roles/compute.networkAdmin",
    "roles/compute.instanceAdmin.v1",
    "roles/iam.securityAdmin",
):
    assert role in source
assert "roles/owner" not in source
```

- [ ] **Step 2: Run test red**

Run: `.venv/bin/python -m pytest tests/infra/test_terraform_modules.py -q`

Expected: FAIL because these roles are not all present.

- [ ] **Step 3: Add the roles and bootstrap instruction**

Append only these roles to the existing default list. In the runbook state that bootstrap identity must be applied before the domain workflow and that IAM propagation can take several minutes.

- [ ] **Step 4: Validate**

Run:

```bash
terraform -chdir=infra/terraform/bootstrap/identity init -backend=false -input=false
terraform -chdir=infra/terraform/bootstrap/identity validate
.venv/bin/python -m pytest tests/infra/test_terraform_modules.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add infra/terraform/modules/foundations/github_federation/variables.tf tests/infra/test_terraform_modules.py docs/runbooks/public-edge-operations.md
git commit -m "feat: authorize Terraform public edge resources"
```

## Task 3: Build the independently stateful public-edge component

**Files:**
- Create: `infra/terraform/components/public-edge/versions.tf`
- Create: `infra/terraform/components/public-edge/variables.tf`
- Create: `infra/terraform/components/public-edge/main.tf`
- Create: `infra/terraform/components/public-edge/outputs.tf`
- Create: `tests/infra/test_public_edge_component.py`
- Modify: `.github/workflows/tests.yml`

**Interfaces:**
- Consumes: checked-in project/environment JSON and `CLOUDFLARE_API_TOKEN` only through the provider environment.
- Produces: non-secret outputs `canonical_url`, `edge_ip`, `certificate_name`, `certificate_status`, and `cloud_run_service_name`.

- [ ] **Step 1: Write failing ownership/edge tests**

```python
assert 'backend "gcs"' in main
assert "cloudflare = {" in versions
assert "google_compute_global_address" in main
assert "google_compute_region_network_endpoint_group" in main
assert 'network_endpoint_type = "SERVERLESS"' in main
assert "google_compute_backend_service" in main
assert 'load_balancing_scheme = "EXTERNAL_MANAGED"' in main
assert "google_compute_managed_ssl_certificate" in main
assert "google_compute_global_forwarding_rule" in main
assert "cloudflare_dns_record" in main
assert "proxied = false" in main
assert "google_cloud_run_v2_service" not in main
assert "CLOUDFLARE_API_TOKEN" not in main
```

- [ ] **Step 2: Run test red**

Run: `.venv/bin/python -m pytest tests/infra/test_public_edge_component.py -q`

Expected: FAIL because the component does not exist.

- [ ] **Step 3: Implement the component**

Reuse the JSON merge locals from `components/public-sandbox/main.tf`. Create:

```hcl
resource "google_compute_global_address" "public" {
  project = local.config.project_id
  name    = "staylong-public-edge-ip"
}

resource "google_compute_region_network_endpoint_group" "cloud_run" {
  project               = local.config.project_id
  region                = local.config.region
  name                  = "staylong-public-edge-neg"
  network_endpoint_type = "SERVERLESS"
  cloud_run { service = local.config.cloud_run_service_name }
}
```

Add an EXTERNAL_MANAGED backend service, canonical HTTPS URL map, separate HTTP-to-HTTPS redirect map, target proxies, port 80/443 forwarding rules, LB logging, and Google-managed certificate for both configured names. Create DNS-only A records for root and `www` pointing at the reserved IP. Provider configuration must use `CLOUDFLARE_API_TOKEN` implicitly; do not set it in HCL.

- [ ] **Step 4: Validate green**

Run:

```bash
terraform -chdir=infra/terraform/components/public-edge init -backend=false -input=false
terraform -chdir=infra/terraform/components/public-edge validate
terraform fmt -check -recursive infra/terraform
.venv/bin/python -m pytest tests/infra/test_public_edge_component.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add infra/terraform/components/public-edge .github/workflows/tests.yml tests/infra/test_public_edge_component.py
git commit -m "feat: add Terraform public edge component"
```

## Task 4: Add protected domain lifecycle workflow and smoke tool

**Files:**
- Create: `.github/workflows/public-domain-control.yml`
- Create: `tests/infra/test_public_domain_control_workflow.py`
- Create: `tools/public_domain_smoke.py`
- Create: `tests/tools/test_public_domain_smoke.py`
- Modify: `docs/runbooks/public-edge-operations.md`

**Interfaces:**
- Consumes: `operation`, main-reachable `commit_sha`, typed confirmation, GCP WIF variables, sandbox environment secret, and public-edge outputs.
- Produces: `public-edge-evidence-$GITHUB_RUN_ID` with operation, SHA, canonical URL, edge IP, certificate status, image/revision references, and smoke result; never a secret.

- [ ] **Step 1: Write failing workflow contracts**

```python
assert "options: [provision, lockdown, destroy]" in source
assert "PROVISION_PUBLIC_DOMAIN" in source
assert "LOCKDOWN_PUBLIC_DOMAIN" in source
assert "DESTROY_PUBLIC_EDGE" in source
assert "environment: sandbox" in source
assert "id-token: write" in source
assert "git merge-base --is-ancestor" in source
assert "CLOUDFLARE_API_TOKEN" in source
assert "public-edge-evidence-" in source
assert "service-account-key" not in source.lower()
assert "echo \"$CLOUDFLARE_API_TOKEN\"" not in source
```

Write local `ThreadingHTTPServer` tests: success returns root HTML, an asset containing `/v1/public`, and 201 plus cookie from `/v1/public/workflows`; failures cover a noncanonical redirect and a private-route 401.

- [ ] **Step 2: Run tests red**

Run: `.venv/bin/python -m pytest tests/infra/test_public_domain_control_workflow.py tests/tools/test_public_domain_smoke.py -q`

Expected: FAIL because neither workflow nor smoke tool exists.

- [ ] **Step 3: Implement lifecycle and smoke**

Workflow requirements:

```yaml
operation: [provision, lockdown, destroy]
concurrency: staylong-public-domain-control
cancel-in-progress: false
environment: sandbox
```

`provision` applies only `components/public-edge`, waits up to 45 minutes for certificate `ACTIVE`, then runs `python tools/public_domain_smoke.py --url https://staylonghome.com`.

`lockdown` first runs that smoke; it refuses unless checked-in `public_edge_lockdown_enabled` is true, then applies `components/public-sandbox` and repeats smoke.

`destroy` runs saved `terraform plan -destroy -out=tfplan` and `terraform apply tfplan` against `public-edge` only. It never calls a registrar or a Cloud Run deletion.

The smoke tool uses `requests.Session`, requires HTTPS in non-test mode, requires canonical host, loads the first JavaScript asset and checks `/v1/public`, posts a temporary concern to `/v1/public/workflows`, requires 201 and `case_id`, and prints only JSON URL/status/case-id/pass data.

- [ ] **Step 4: Run tests green**

Run:

```bash
.venv/bin/python -m pytest tests/infra/test_public_domain_control_workflow.py tests/tools/test_public_domain_smoke.py tests/tools/test_public_sandbox_smoke.py -q
.venv/bin/python -m ruff check tools/public_domain_smoke.py tests/tools/test_public_domain_smoke.py
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/public-domain-control.yml tests/infra/test_public_domain_control_workflow.py tools/public_domain_smoke.py tests/tools/test_public_domain_smoke.py docs/runbooks/public-edge-operations.md
git commit -m "feat: control public domain lifecycle"
```

## Task 5: Implement the reviewed Phase-B Cloud Run lockdown and release evidence

**Files:**
- Modify: `infra/terraform/components/public-sandbox/main.tf`
- Modify: `infra/terraform/components/public-sandbox/outputs.tf`
- Modify: `.github/workflows/public-sandbox-control.yml`
- Modify: `tests/infra/test_public_sandbox_component.py`
- Modify: `tests/infra/test_public_sandbox_control_workflow.py`
- Modify: `README.md`
- Modify: `docs/runbooks/public-edge-operations.md`
- Modify: `tests/integration/test_architecture_evidence_contract.py`

**Interfaces:**
- Consumes: `local.config.public_edge_lockdown_enabled: bool`.
- Produces: false retains the existing `.run.app` smoke target; true sets `INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER`, disables default URL where supported, and uses canonical-domain smoke.

- [ ] **Step 1: Write failing Phase-B tests**

```python
assert "public_edge_lockdown_enabled" in component_source
assert "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER" in component_source
assert "default_uri_disabled" in component_source
assert "tools/public_domain_smoke.py" in workflow_source
assert "staylonghome.com" not in workflow_source
```

Add an evidence/runbook test requiring `CLOUDFLARE_API_TOKEN`, all three confirmation strings, `staylonghome.com`, `temporary`, and `never deletes the domain registration`.

- [ ] **Step 2: Run tests red**

Run: `.venv/bin/python -m pytest tests/infra/test_public_sandbox_component.py tests/infra/test_public_sandbox_control_workflow.py tests/integration/test_architecture_evidence_contract.py -q`

Expected: FAIL because the configuration flag has no runtime behavior and the runbook/README entry is absent.

- [ ] **Step 3: Implement the explicit lockdown and docs**

Use this Cloud Run setting:

```hcl
ingress = local.config.public_edge_lockdown_enabled ? "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER" : "INGRESS_TRAFFIC_ALL"
```

Drive the provider-supported default URL disable field from the same flag. Retain the `allUsers` invoker binding so the ALB can invoke the public service; ingress prevents direct external bypass.

In the existing app-deploy workflow, select smoke URL from resolved configuration: the service URI when false, `https://$public_domain` when true. Invoke the matching smoke tool. Add README/runbook language that the branded URL is a temporary-data public demo, list exact dispatch inputs, certificate wait, rollback path, and evidence artifact.

- [ ] **Step 4: Run complete local verification**

Run:

```bash
.venv/bin/python -m pytest -q
npm --prefix frontend test -- --run
npm --prefix frontend run lint
terraform fmt -check -recursive infra/terraform
find infra/terraform/bootstrap infra/terraform/components -name main.tf -exec dirname {} \; | sort -u | while read -r component; do terraform -chdir="$component" init -backend=false -input=false && terraform -chdir="$component" validate; done
```

Expected: PASS. If a documented pre-existing Vite proxy timeout recurs, include its exact test name and baseline evidence in the PR; do not call the edge work complete unless its own Python, Terraform, workflow, and smoke contracts pass.

- [ ] **Step 5: Commit and open the implementation PR**

```bash
git add infra/terraform/components/public-sandbox .github/workflows/public-sandbox-control.yml README.md docs tests
git commit -m "feat: restrict Cloud Run behind public edge"
git push -u origin feat/public-edge
gh pr create --base main --head feat/public-edge --title "feat: add StayLong branded public edge"
```

The PR description must state that real provisioning occurs only after merge through the typed-confirmation workflow and must show a no-secret diff review.

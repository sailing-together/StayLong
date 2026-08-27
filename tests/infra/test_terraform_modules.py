import re
from pathlib import Path

IAM_BINDING_MODULE = Path("infra/terraform/modules/base/iam_binding/main.tf")
GITHUB_FEDERATION_MODULE = Path(
    "infra/terraform/modules/foundations/github_federation/main.tf"
)
IDENTITY_BOOTSTRAP_ROOT = Path("infra/terraform/bootstrap/identity/main.tf")
SANDBOX_PLATFORM_MODULE = Path(
    "infra/terraform/modules/foundations/sandbox_platform/main.tf"
)
GITHUB_FEDERATION_VARIABLES = Path(
    "infra/terraform/modules/foundations/github_federation/variables.tf"
)
BOOTSTRAP_STATE_ROOT = Path("infra/terraform/bootstrap/state/main.tf")
SYDNEY_PLATFORM_ROOT = Path("infra/terraform/components/sydney-platform/main.tf")
DEPLOY_WORKFLOW = Path(".github/workflows/deploy-sydney-v2.yml")
CLOUD_RUN_SERVICE_MODULE = Path(
    "infra/terraform/modules/base/cloud_run_service/main.tf"
)


def test_service_account_iam_bindings_use_static_instance_keys() -> None:
    """New identity resources must be plannable before their IDs exist."""
    source = IAM_BINDING_MODULE.read_text()

    assert "for index, binding in var.service_account_bindings : index => binding" in source


def test_main_branch_workload_identities_are_matched_by_a_mapped_principal() -> None:
    """WIF branch restrictions belong in the principal identifier, not IAM CEL."""
    source = GITHUB_FEDERATION_MODULE.read_text()

    assert re.search(
        r'"attribute\.repository_ref"\s+=\s+"assertion\.repository \+ \\"\:\\" \+ assertion\.ref"',
        source,
    )
    protected_branch_attribute = (
        "attribute.repository_ref/${var.github_repository}:refs/heads/${var.github_branch}"
    )
    assert protected_branch_attribute in source
    assert "attribute.ref ==" not in source


def test_terraform_workflow_identities_can_lock_the_remote_state_bucket() -> None:
    """Terraform plan needs object access for its GCS state lock."""
    federation_source = GITHUB_FEDERATION_MODULE.read_text()
    bootstrap_source = IDENTITY_BOOTSTRAP_ROOT.read_text()

    assert 'resource "google_storage_bucket_iam_member" "terraform_state"' in federation_source
    assert 'role   = "roles/storage.objectAdmin"' in federation_source
    assert '"planner"  = module.planner.email' in federation_source
    assert '"operator" = module.operator.email' in federation_source
    assert "state_bucket_name              = local.config.state_bucket_name" in bootstrap_source


def test_deployer_can_consume_enabled_google_apis_for_cloud_build() -> None:
    source = Path("infra/terraform/modules/foundations/github_federation/variables.tf").read_text()

    assert '"roles/serviceusage.serviceUsageConsumer"' in source


def test_terraform_operator_can_create_secret_manager_resources() -> None:
    """The Terraform identity, not the runtime, owns secret-container creation."""
    source = Path("infra/terraform/modules/foundations/github_federation/variables.tf").read_text()

    assert '"roles/secretmanager.admin"' in source


def test_cloud_build_staging_uses_bootstrap_bucket_and_scoped_identity_members() -> None:
    state_source = BOOTSTRAP_STATE_ROOT.read_text()
    identity_source = GITHUB_FEDERATION_MODULE.read_text()
    variables_source = GITHUB_FEDERATION_VARIABLES.read_text()

    assert 'module "cloudbuild_staging"' in state_source
    assert 'source = "../../modules/base/gcs_bucket"' in state_source
    assert 'resource "google_storage_bucket_iam_member" "cloudbuild_staging"' in identity_source
    assert 'variable "cloudbuild_staging_bucket_name"' in variables_source
    assert "gcp-sa-cloudbuild.iam.gserviceaccount.com" in identity_source
    assert '"roles/storage.objectCreator"' in identity_source
    assert '"roles/storage.objectViewer"' in identity_source
    assert '"roles/storage.legacyBucketReader"' in identity_source
    assert "${var.project_number}-compute@developer.gserviceaccount.com" in identity_source


def test_cloud_build_compute_identity_can_push_only_to_the_artifact_repository() -> None:
    source = SANDBOX_PLATFORM_MODULE.read_text()

    assert 'resource "google_artifact_registry_repository_iam_member" "cloudbuild_writer"' in source
    assert 'role       = "roles/artifactregistry.writer"' in source
    assert "${data.google_project.current.number}-compute@developer.gserviceaccount.com" in source


def test_platform_enables_cloud_resource_manager_before_managing_project_services() -> None:
    bootstrap_source = IDENTITY_BOOTSTRAP_ROOT.read_text()
    platform_source = SANDBOX_PLATFORM_MODULE.read_text()

    assert 'resource "google_project_service" "cloud_resource_manager"' in bootstrap_source
    assert re.search(
        r'service\s+= "cloudresourcemanager\.googleapis\.com"', bootstrap_source
    )
    assert 'resource "google_project_service" "cloud_resource_manager"' not in platform_source


def test_identity_bootstrap_enables_managed_identity_apis_before_bucket_iam() -> None:
    """New projects must create Google-managed identities before IAM grants."""
    bootstrap_source = IDENTITY_BOOTSTRAP_ROOT.read_text()
    federation_source = GITHUB_FEDERATION_MODULE.read_text()

    assert 'resource "google_project_service" "managed_identity_apis"' in bootstrap_source
    assert '"cloudbuild.googleapis.com"' in bootstrap_source
    assert '"compute.googleapis.com"' in bootstrap_source
    assert "depends_on = [" in bootstrap_source
    assert "google_project_service.managed_identity_apis" in bootstrap_source
    expected_binding = 'resource "google_storage_bucket_iam_member" "cloudbuild_staging"'
    assert expected_binding in federation_source


def test_v2_deployment_builds_directly_to_artifact_registry_and_applies_with_terraform() -> None:
    source = DEPLOY_WORKFLOW.read_text()

    assert "docker/setup-buildx-action@v3" in source
    assert "docker buildx build" in source
    assert "gcloud builds submit" not in source
    assert "terraform -chdir=\"$component_path\" apply -input=false tfplan" in source
    assert "gcloud run services update" not in source


def test_sydney_platform_creates_runtime_identity_before_cloud_run_deployment() -> None:
    source = SYDNEY_PLATFORM_ROOT.read_text()

    assert 'service            = "run.googleapis.com"' in source
    assert 'module "runtime"' in source
    assert 'source = "../../modules/base/service_account"' in source
    assert "account_id   = local.config.runtime_account_id" in source


def test_cloud_run_revision_template_is_managed_by_terraform() -> None:
    """Image and secret changes must create a new Cloud Run revision."""
    source = CLOUD_RUN_SERVICE_MODULE.read_text()

    lifecycle = re.search(r"lifecycle\s*\{(?P<body>.*?)\n\s*\}", source, re.DOTALL)

    assert lifecycle is not None
    assert "ignore_changes = [scaling]" in lifecycle.group("body")
    assert "template" not in lifecycle.group("body")

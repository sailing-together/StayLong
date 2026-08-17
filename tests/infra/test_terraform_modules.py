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
    assert "state_bucket_name = local.config.state_bucket_name" in bootstrap_source


def test_deployer_can_consume_enabled_google_apis_for_cloud_build() -> None:
    source = Path("infra/terraform/modules/foundations/github_federation/variables.tf").read_text()

    assert '"roles/serviceusage.serviceUsageConsumer"' in source


def test_cloud_build_staging_uses_a_terraform_managed_bucket_and_scoped_members() -> None:
    source = SANDBOX_PLATFORM_MODULE.read_text()

    assert 'module "cloudbuild_staging"' in source
    assert 'source = "../../base/gcs_bucket"' in source
    assert "var.cloudbuild_staging_bucket_name" in source
    assert "var.deployer_account_id" in source
    assert "gcp-sa-cloudbuild.iam.gserviceaccount.com" in source
    assert "object_creator_members" in source
    assert "object_viewer_members" in source
    assert "object_admin_members" not in source


def test_terraform_operator_can_create_platform_buckets() -> None:
    source = Path(
        "infra/terraform/modules/foundations/github_federation/variables.tf"
    ).read_text()

    assert '"roles/storage.admin"' in source


def test_platform_enables_cloud_resource_manager_before_managing_project_services() -> None:
    bootstrap_source = IDENTITY_BOOTSTRAP_ROOT.read_text()
    platform_source = SANDBOX_PLATFORM_MODULE.read_text()

    assert 'resource "google_project_service" "cloud_resource_manager"' in bootstrap_source
    assert re.search(
        r'service\s+= "cloudresourcemanager\.googleapis\.com"', bootstrap_source
    )
    assert 'resource "google_project_service" "cloud_resource_manager"' not in platform_source

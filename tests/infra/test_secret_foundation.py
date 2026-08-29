"""Security contract for the Sydney v2 token secret foundation."""

from pathlib import Path

SECRET_MODULE = Path("infra/terraform/modules/base/secret_manager_secret/main.tf")
FOUNDATION_ROOT = Path("infra/terraform/components/sydney-v2-foundation/main.tf")


def test_sydney_v2_token_secret_uses_resource_scoped_least_privilege_iam() -> None:
    module_source = SECRET_MODULE.read_text(encoding="utf-8")
    foundation_source = FOUNDATION_ROOT.read_text(encoding="utf-8")

    assert 'resource "google_secret_manager_secret" "this"' in module_source
    assert "secret_data" not in module_source
    assert 'role      = "roles/secretmanager.secretAccessor"' in module_source
    assert 'role      = "roles/secretmanager.secretVersionAdder"' in module_source
    assert 'secret_id = "staylong-api-token"' in foundation_source
    assert 'service = "secretmanager.googleapis.com"' in foundation_source
    assert (
        "staylong-runtime@${local.config.project_id}.iam.gserviceaccount.com"
        in foundation_source
    )
    assert (
        "staylong-app-deployer@${local.config.project_id}.iam.gserviceaccount.com"
        in foundation_source
    )

"""Security contract for the initial Sydney v2 Cloud Run revision."""

from pathlib import Path

CLOUD_RUN_MODULE = Path("infra/terraform/modules/base/cloud_run_service/main.tf")
V2_APP_ROOT = Path("infra/terraform/components/sydney-v2-app/main.tf")


def test_sydney_v2_initial_revision_uses_secret_manager_reference() -> None:
    """The initial revision must reference a secret, never a plaintext token."""
    module_source = CLOUD_RUN_MODULE.read_text()
    app_source = V2_APP_ROOT.read_text()

    assert "value_source" in module_source
    assert "secret_key_ref" in module_source
    assert 'secret_id = "staylong-api-token"' in app_source
    assert "STAYLONG_API_TOKEN = {" in app_source
    assert 'version   = "latest"' in app_source
    assert "enable_public_invoker = false" in app_source
    assert (
        "serviceAccount:${local.config.deployer_account_id}@${local.config.project_id}"
        in app_source
    )
    assert "STAYLONG_API_TOKEN" not in module_source

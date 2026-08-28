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
    assert "enable_public_invoker = var.diagnostic_public_invoker" in app_source
    assert 'variable "diagnostic_public_invoker"' in Path(
        "infra/terraform/components/sydney-v2-app/variables.tf"
    ).read_text()
    assert (
        "serviceAccount:${local.config.deployer_account_id}@${local.config.project_id}"
        in app_source
    )
    assert "STAYLONG_API_TOKEN" not in module_source


def test_sydney_v2_calendar_oauth_is_opt_in_and_uses_secret_reference() -> None:
    app_source = V2_APP_ROOT.read_text()
    variables_source = Path("infra/terraform/components/sydney-v2-app/variables.tf").read_text()

    assert 'variable "calendar_oauth_client_id"' in variables_source
    assert 'variable "calendar_oauth_redirect_uri"' in variables_source
    assert 'variable "calendar_oauth_client_secret_id"' in variables_source
    assert 'STAYLONG_GOOGLE_ACTIONS_MODE       = "oauth"' in app_source
    assert "STAYLONG_GOOGLE_OAUTH_CLIENT_SECRET" in app_source
    assert 'secret_id = var.calendar_oauth_client_secret_id' in app_source
    assert 'default     = ""' in variables_source

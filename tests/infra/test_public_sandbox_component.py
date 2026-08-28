"""Safety contract for the StayLong public sandbox Terraform component."""

from pathlib import Path

COMPONENT = Path("infra/terraform/components/public-sandbox")


def test_public_sandbox_is_dedicated_and_has_no_private_api_token() -> None:
    source = (COMPONENT / "main.tf").read_text()
    assert '"staylong-public-sandbox"' in source  # service name (fmt aligns = signs)
    assert 'member   = "allUsers"' in source
    assert "STAYLONG_GOOGLE_ACTIONS_MODE" in source
    assert 'value = "sandbox"' in source
    assert "STAYLONG_API_TOKEN" not in source


def test_public_sandbox_enables_vertex_gemma_privacy_guard() -> None:
    source = (COMPONENT / "main.tf").read_text()
    assert 'name  = "STAYLONG_GEMMA_ENABLED"' in source
    assert 'value = "true"' in source
    assert 'name  = "GOOGLE_CLOUD_PROJECT"' in source
    assert 'name  = "GOOGLE_CLOUD_LOCATION"' in source
    assert 'value = "global"' in source
    assert 'name  = "GOOGLE_GENAI_USE_VERTEXAI"' in source


def test_public_sandbox_schedules_authenticated_cleanup() -> None:
    source = (COMPONENT / "main.tf").read_text()
    assert "google_cloud_scheduler_job" in source
    assert "/internal/public-sandbox/cleanup" in source
    assert "oidc_token" in source


def test_public_sandbox_provisions_firestore_for_durable_sessions() -> None:
    source = (COMPONENT / "main.tf").read_text()

    assert 'service            = "firestore.googleapis.com"' in source
    assert 'resource "google_firestore_database" "public_sandbox"' in source
    assert 'name                        = "(default)"' in source


def test_public_sandbox_outputs_only_url_and_non_sensitive_evidence() -> None:
    source = (COMPONENT / "outputs.tf").read_text()
    assert "public_url" in source
    assert "service_name" in source
    assert "cleanup_scheduler_job" in source
    assert "session_secret" not in source
    assert "api_token" not in source


def test_public_sandbox_has_dedicated_runtime_and_scheduler_identities() -> None:
    source = (COMPONENT / "main.tf").read_text()
    assert 'module "sandbox_runtime"' in source
    assert 'module "sandbox_scheduler"' in source


def test_public_sandbox_existing_private_service_is_not_referenced() -> None:
    source = (COMPONENT / "main.tf").read_text()
    # The private service name must not appear; this component is fully isolated.
    assert "staylong-sydney-v2-private" not in source
    assert "staylong-api-token" not in source


def test_public_sandbox_has_deletion_protection_disabled() -> None:
    source = (COMPONENT / "main.tf").read_text()
    assert "deletion_protection = false" in source


def test_public_sandbox_project_config_has_dedicated_accounts() -> None:
    import json

    config = json.loads(
        Path("infra/terraform/projects/config/staylong-public-sandbox.json").read_text()
    )
    assert config["runtime_account_id"] == "staylong-sandbox-runtime"
    assert config["scheduler_account_id"] == "staylong-sandbox-scheduler"
    assert config["cloud_run_service_name"] == "staylong-public-sandbox"
    # Must not reuse the production runtime identity
    assert config["runtime_account_id"] != "staylong-runtime"

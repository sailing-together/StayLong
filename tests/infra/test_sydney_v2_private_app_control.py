"""Safety contract for the disposable private StayLong application control."""

from pathlib import Path

COMPONENT = Path("infra/terraform/components/sydney-v2-private-app-control")
WORKFLOW = Path(".github/workflows/sydney-v2-private-app-control.yml")


def test_private_app_control_matches_runtime_without_public_invocation() -> None:
    main = (COMPONENT / "main.tf").read_text()
    versions = (COMPONENT / "versions.tf").read_text()

    assert 'resource "google_cloud_run_v2_service" "control"' in main
    assert 'ingress             = "INGRESS_TRAFFIC_ALL"' in main
    assert "image = var.image_ref" in main
    assert 'name = "STAYLONG_API_TOKEN"' in main
    assert 'secret  = "staylong-api-token"' in main
    assert 'member   = "serviceAccount:${local.config.deployer_account_id}' in main
    assert "allUsers" not in main
    assert 'source  = "hashicorp/google"' in versions
    assert "google-beta" not in versions


def test_private_app_control_uses_wif_smoke_and_always_destroys() -> None:
    workflow = WORKFLOW.read_text()

    assert "RUN_STAY_LONG_SYDNEY_PRIVATE_APP_CONTROL" in workflow
    assert "prefix=staylong/sydney-sandbox/sydney-v2-private-app-control" in workflow
    assert "status.imageDigest" in workflow
    assert "token_format: id_token" in workflow
    assert "id_token_audience:" in workflow
    assert "tools/cloudrun_smoke.py" in workflow
    assert "GCP_DEPLOY_SERVICE_ACCOUNT" in workflow
    assert "GCP_TERRAFORM_OPERATOR_SERVICE_ACCOUNT" in workflow
    assert "if: ${{ always() }}" in workflow
    assert 'terraform -chdir="$COMPONENT_PATH" destroy' in workflow

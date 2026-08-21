"""Safety contract for the disposable public StayLong application control."""

from pathlib import Path

COMPONENT = Path("infra/terraform/components/sydney-v2-public-app-control")
WORKFLOW = Path(".github/workflows/sydney-v2-public-app-control.yml")


def test_public_app_control_changes_only_the_invocation_boundary() -> None:
    main = (COMPONENT / "main.tf").read_text()
    versions = (COMPONENT / "versions.tf").read_text()

    assert 'resource "google_cloud_run_v2_service" "control"' in main
    assert 'ingress             = "INGRESS_TRAFFIC_ALL"' in main
    assert "image = var.image_ref" in main
    assert 'name = "STAYLONG_API_TOKEN"' in main
    assert 'secret  = "staylong-api-token"' in main
    assert 'member   = "allUsers"' in main
    assert 'source  = "hashicorp/google"' in versions
    assert "google-beta" not in versions


def test_public_app_control_smokes_and_always_destroys() -> None:
    workflow = WORKFLOW.read_text()

    assert "RUN_STAY_LONG_SYDNEY_PUBLIC_APP_CONTROL" in workflow
    assert "prefix=staylong/sydney-sandbox/sydney-v2-public-app-control" in workflow
    assert "status.imageDigest" in workflow
    assert "for attempt in {1..12}" in workflow
    assert "tools/cloudrun_smoke.py" in workflow
    assert "--application-token-header X-StayLong-API-Token" in workflow
    assert "if: ${{ always() }}" in workflow
    assert 'terraform -chdir="$COMPONENT_PATH" destroy' in workflow

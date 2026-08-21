"""Safety contract for the disposable stable-provider Cloud Run control probe."""

from pathlib import Path

COMPONENT = Path("infra/terraform/components/sydney-v2-control-probe")
WORKFLOW = Path(".github/workflows/sydney-v2-control-probe.yml")


def test_control_probe_uses_stable_provider_and_explicit_public_ingress() -> None:
    main = (COMPONENT / "main.tf").read_text()
    versions = (COMPONENT / "versions.tf").read_text()

    assert 'resource "google_cloud_run_v2_service" "control"' in main
    assert 'ingress             = "INGRESS_TRAFFIC_ALL"' in main
    assert 'image = "gcr.io/google-samples/hello-app:1.0"' in main
    assert 'member   = "allUsers"' in main
    assert 'source  = "hashicorp/google"' in versions
    assert "google-beta" not in versions
    assert "googlebeta" not in main


def test_control_probe_workflow_is_confirmation_gated_and_always_destroys() -> None:
    workflow = WORKFLOW.read_text()

    assert "RUN_STAY_LONG_SYDNEY_CONTROL_PROBE" in workflow
    assert "stay-long-sydney-v2.json" in workflow
    assert "stay-long-sydney-sandbox.json" in workflow
    assert "prefix=staylong/sydney-sandbox/sydney-v2-control-probe" in workflow
    assert 'gcloud run services describe "$SERVICE"' in workflow
    assert 'X-Cloud-Trace-Context' in workflow
    assert "if: ${{ always() }}" in workflow
    assert 'terraform -chdir="$COMPONENT_PATH" destroy' in workflow

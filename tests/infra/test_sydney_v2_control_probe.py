"""Safety contract for the disposable stable-provider Cloud Run control probe."""

from pathlib import Path

COMPONENT = Path("infra/terraform/components/sydney-v2-control-probe")
WORKFLOW = Path(".github/workflows/sydney-v2-control-probe.yml")


def test_control_probe_uses_stable_provider_and_explicit_public_ingress() -> None:
    main = (COMPONENT / "main.tf").read_text()
    variables = (COMPONENT / "variables.tf").read_text()
    versions = (COMPONENT / "versions.tf").read_text()

    assert 'resource "google_cloud_run_v2_service" "control"' in main
    assert 'ingress             = "INGRESS_TRAFFIC_ALL"' in main
    assert "variable \"image_ref\"" in variables
    assert "variable \"run_static_server\"" in variables
    assert "variable \"run_uvicorn_h11\"" in variables
    assert "image   = var.image_ref" in main
    assert 'command = var.run_static_server ? ["python"] : (' in main
    assert 'args = var.run_static_server ? ["-m", "http.server", "8080"] : (' in main
    assert 'var.run_uvicorn_h11 ? ["uvicorn"]' in main
    assert '"--http", "h11"' in main
    assert '"--loop", "asyncio"' in main
    assert 'name = "STAYLONG_API_TOKEN"' in main
    assert 'secret  = "staylong-api-token"' in main
    assert 'member   = "allUsers"' in main
    assert 'tag     = "probe"' in main
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
    assert '.status.traffic[]? | (.uri // .url // empty)' in workflow
    assert 'route_kind: "service"' in workflow
    assert 'route_kind: "tagged-revision"' in workflow
    assert "grep -qx 'tagged-revision'" in workflow
    assert "if: ${{ always() }}" in workflow
    assert 'terraform -chdir="$COMPONENT_PATH" destroy' in workflow


def test_control_probe_switches_images_on_the_same_service_and_restores_hello() -> None:
    workflow = WORKFLOW.read_text()

    assert "HELLO_IMAGE: gcr.io/google-samples/hello-app:1.0" in workflow
    assert "APP_SERVICE: staylong-sydney-v2" in workflow
    assert 'status.latestReadyRevisionName' in workflow
    assert 'status.imageDigest' in workflow
    assert 'apply_image "$HELLO_IMAGE" "hello-before" "false" "false"' in workflow
    assert 'apply_image "$app_image" "staylong-static" "true" "false"' in workflow
    assert 'apply_image "$app_image" "staylong-h11" "false" "true"' in workflow
    assert 'apply_image "$app_image" "staylong" "false" "false"' in workflow
    assert 'apply_image "$HELLO_IMAGE" "hello-after" "false" "false"' in workflow
    assert 'probe_phase "hello-before" "/" "require-200"' in workflow
    assert 'probe_phase "staylong-static" "/" "record-only"' in workflow
    assert 'probe_phase "staylong-h11" "/healthz" "record-only"' in workflow
    assert 'probe_phase "staylong" "/healthz" "record-only"' in workflow
    assert 'probe_phase "hello-after" "/" "require-200"' in workflow

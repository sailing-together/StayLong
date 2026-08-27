"""Security contract for the protected Sydney v2 deployment workflow."""

from pathlib import Path

WORKFLOW = Path(".github/workflows/deploy-sydney-v2.yml")
PUBLIC_DIAGNOSTIC_WORKFLOW = Path(".github/workflows/sydney-v2-public-diagnostic.yml")
DOCKERFILE = Path("Dockerfile")
PYPROJECT = Path("pyproject.toml")
SMOKE_TOOL = Path("tools/cloudrun_smoke.py")


def test_v2_deployment_adds_a_secret_version_without_passing_it_to_terraform() -> None:
    """The token moves from GitHub Secrets to Secret Manager, never Terraform."""
    source = WORKFLOW.read_text()

    assert "gcloud secrets versions add staylong-api-token" in source
    assert "--data-file=-" in source
    assert "GCP_DEPLOY_SERVICE_ACCOUNT" in source
    assert "GCP_TERRAFORM_OPERATOR_SERVICE_ACCOUNT" in source
    assert 'component_path="infra/terraform/components/sydney-v2-app"' in source
    expected_image_expression = 'IMAGE_REF="$(cat "$RUNNER_TEMP/image-ref/image-ref.txt")"'
    assert expected_image_expression in source
    assert "IMAGE_REF: $SYDNEY_REGION" not in source
    assert "--update-env-vars" not in source
    assert "STAYLONG_API_TOKEN=" not in source
    assert "--project-config stay-long-sydney-v2.json" in source
    assert "--environment-config stay-long-sydney-sandbox.json" in source


def test_v2_workflow_is_the_only_automatic_application_deployment_path() -> None:
    """Retired service names must not receive automatic main-branch deployments."""
    assert WORKFLOW.exists()
    assert not Path(".github/workflows/deploy.yml").exists()
    assert not Path(".github/workflows/deploy-sydney.yml").exists()


def test_v2_public_diagnostic_reverts_the_temporary_invoker_binding() -> None:
    """A diagnostic can expose only the v2 health endpoint and must always revoke it."""
    source = PUBLIC_DIAGNOSTIC_WORKFLOW.read_text()

    assert "TEMPORARILY_PUBLIC_SYDNEY_V2_CLOUD_RUN" in source
    assert "STATE_PREFIX: staylong/sydney-sandbox/sydney-v2-app" in source
    assert '-backend-config="prefix=$STATE_PREFIX"' in source
    assert 'diagnostic_public_invoker=true' in source
    assert 'curl --silent --show-error' in source
    assert 'test "$http_status" = 200' in source
    assert "if: ${{ always() }}" in source
    assert 'diagnostic_public_invoker=false' in source


def test_v2_image_digest_records_the_deployed_main_revision() -> None:
    workflow = WORKFLOW.read_text()
    dockerfile = DOCKERFILE.read_text()

    assert "ARG BUILD_REVISION" in dockerfile
    assert "org.opencontainers.image.revision=$BUILD_REVISION" in dockerfile
    assert '--build-arg "BUILD_REVISION=${{ steps.revision.outputs.sha }}"' in workflow


def test_v2_deployment_scans_the_published_image_before_release_side_effects() -> None:
    """A vulnerable immutable image must never reach Secret Manager or Terraform."""
    workflow = WORKFLOW.read_text()

    build_position = workflow.index("- name: Build and publish immutable Sydney v2 image")
    scan_position = workflow.index("- name: Scan immutable Sydney v2 image")
    upload_position = workflow.index(
        "- name: Preserve the scanned image reference for Terraform"
    )
    secret_position = workflow.index("- name: Add a masked token version to Secret Manager")

    assert build_position < scan_position < upload_position < secret_position

    scan_step = workflow[scan_position:secret_position]
    assert (
        "uses: aquasecurity/trivy-action@ed142fd0673e97e23eac54620cfb913e5ce36c25"
        " # v0.36.0"
    ) in scan_step
    assert "scan-type: image" in scan_step
    assert "image-ref: ${{ steps.image.outputs.image_ref }}" in scan_step
    assert "scanners: vuln,secret,misconfig" in scan_step
    assert "severity: HIGH,CRITICAL" in scan_step
    assert 'exit-code: "1"' in scan_step
    assert "ignore-unfixed: true" not in scan_step


def test_v2_deployment_scans_and_applies_the_same_build_digest() -> None:
    """Terraform must consume the exact digest emitted and scanned by buildx."""
    workflow = WORKFLOW.read_text()

    assert "id: image" in workflow
    assert '--metadata-file "$metadata_file"' in workflow
    assert "containerimage.digest" in workflow
    assert 'echo "image_ref=$image_repository@$digest" >> "$GITHUB_OUTPUT"' in workflow
    assert "image-ref: ${{ steps.image.outputs.image_ref }}" in workflow
    assert "needs: build_and_publish" in workflow
    assert "outputs:\n      image_ref:" not in workflow
    assert "echo \"$image_repository@$digest\" > \"$RUNNER_TEMP/image-ref.txt\"" in workflow
    assert (
        "uses: actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02"
        " # v4"
    ) in workflow
    assert (
        "uses: actions/download-artifact@d3f86a106a0bac45b974a628896c90dbdf5c8093"
        " # v4"
    ) in workflow
    assert workflow.count("name: sydney-v2-image-ref-${{ github.run_id }}") == 2
    upload_start = workflow.index("- name: Preserve the scanned image reference")
    upload_end = workflow.index("- name: Add a masked token version", upload_start)
    download_start = workflow.index("- name: Restore the scanned image reference")
    download_end = workflow.index(
        "- name: Create or update the v2 service from the reviewed image",
        download_start,
    )
    upload_step = workflow[upload_start:upload_end]
    download_step = workflow[download_start:download_end]
    assert "path: ${{ runner.temp }}/image-ref.txt" in upload_step
    assert "path: ${{ runner.temp }}/image-ref" in download_step
    assert "path: ${{ runner.temp }}/image-ref.txt" not in download_step
    assert 'IMAGE_REF="$(cat \"$RUNNER_TEMP/image-ref/image-ref.txt\")"' in workflow
    assert 'expected_repository="$SYDNEY_REGION-docker.pkg.dev/' in workflow
    assert "grep -Eq '^sha256:[0-9a-f]{64}$'" in workflow
    assert 'IMAGE_REF="${{ needs.build_and_publish.outputs.image_ref }}"' not in workflow
    assert 'app:${{ steps.revision.outputs.sha }}' not in workflow[
        workflow.index("jobs:") :
    ].split("Scan immutable Sydney v2 image", maxsplit=1)[1]


def test_cloud_run_container_uses_granian_asgi_server() -> None:
    dockerfile = DOCKERFILE.read_text()
    pyproject = PYPROJECT.read_text()

    assert "granian>=2,<3" in pyproject
    assert (
        "exec granian --interface asgi --http 1 --host 0.0.0.0 "
        "--port ${PORT} staylong.api.main:app"
    ) in dockerfile


def test_cloud_run_runtime_uses_a_pinned_alpine_base_with_security_updates() -> None:
    """The scanned runtime must contain the currently patched Alpine packages."""
    dockerfile = DOCKERFILE.read_text()

    assert (
        "FROM python:3.12-alpine3.24@sha256:"
        "d09d15e60962ca365d1cd544a48773bac9d33f2fb1b00f2aa0deec78ade7dc31 "
        "AS runtime"
    ) in dockerfile
    assert "RUN apk upgrade --no-cache" in dockerfile
    assert "FROM python:3.12-slim AS runtime" not in dockerfile


def test_sydney_v2_runtime_injects_vertex_project_environment_variable() -> None:
    """Cloud Run must provide the project name required by Vertex AI startup."""
    component = Path("infra/terraform/components/sydney-v2-app/main.tf").read_text()

    assert "environment_variables = {" in component
    assert "GOOGLE_CLOUD_PROJECT = local.config.project_id" in component

    cloud_run_module = Path(
        "infra/terraform/modules/base/cloud_run_service/main.tf"
    ).read_text()
    assert "for_each = var.environment_variables" in cloud_run_module
    assert 'name  = env.key' in cloud_run_module
    assert "value = env.value" in cloud_run_module


def test_cloud_run_smoke_avoids_reserved_paths_ending_in_z() -> None:
    smoke_tool = SMOKE_TOOL.read_text()

    assert 'client.request("GET", "/health")' in smoke_tool
    assert 'client.request("GET", "/healthz")' not in smoke_tool

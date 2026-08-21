"""Security contract for the protected Sydney v2 deployment workflow."""

from pathlib import Path

WORKFLOW = Path(".github/workflows/deploy-sydney-v2.yml")
PUBLIC_DIAGNOSTIC_WORKFLOW = Path(".github/workflows/sydney-v2-public-diagnostic.yml")
DOCKERFILE = Path("Dockerfile")


def test_v2_deployment_adds_a_secret_version_without_passing_it_to_terraform() -> None:
    """The token moves from GitHub Secrets to Secret Manager, never Terraform."""
    source = WORKFLOW.read_text()

    assert "gcloud secrets versions add staylong-api-token" in source
    assert "--data-file=-" in source
    assert "GCP_DEPLOY_SERVICE_ACCOUNT" in source
    assert "GCP_TERRAFORM_OPERATOR_SERVICE_ACCOUNT" in source
    assert 'component_path="infra/terraform/components/sydney-v2-app"' in source
    expected_image_expression = (
        'IMAGE_REF="${SYDNEY_REGION}-docker.pkg.dev/${{ vars.GCP_PROJECT_ID }}'
        '/${SYDNEY_REPOSITORY}/app:${{ steps.revision.outputs.sha }}"'
    )
    assert expected_image_expression in source
    assert "IMAGE_REF: $SYDNEY_REGION" not in source
    assert "needs.build_and_publish.outputs.image_ref" not in source
    assert "--update-env-vars" not in source
    assert "STAYLONG_API_TOKEN=" not in source
    assert "--project-config stay-long-sydney-v2.json" in source
    assert "--environment-config stay-long-sydney-sandbox.json" in source


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

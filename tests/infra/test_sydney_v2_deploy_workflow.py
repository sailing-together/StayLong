"""Security contract for the protected Sydney v2 deployment workflow."""

from pathlib import Path

WORKFLOW = Path(".github/workflows/deploy-sydney-v2.yml")


def test_v2_deployment_adds_a_secret_version_without_passing_it_to_terraform() -> None:
    """The token moves from GitHub Secrets to Secret Manager, never Terraform."""
    source = WORKFLOW.read_text()

    assert "gcloud secrets versions add staylong-api-token" in source
    assert "--data-file=-" in source
    assert "GCP_DEPLOY_SERVICE_ACCOUNT" in source
    assert "GCP_TERRAFORM_OPERATOR_SERVICE_ACCOUNT" in source
    assert 'component_path="infra/terraform/components/sydney-v2-app"' in source
    assert '"-var=image_ref=$IMAGE_REF"' in source
    assert "--update-env-vars" not in source
    assert "STAYLONG_API_TOKEN=" not in source

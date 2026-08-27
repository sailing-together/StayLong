"""Structural contract tests for public-sandbox delivery automation."""

from pathlib import Path


WORKFLOW = Path(".github/workflows/public-sandbox-control.yml")


def workflow_source() -> str:
    """Return the public-sandbox lifecycle workflow source."""
    return WORKFLOW.read_text()


def test_public_sandbox_control_has_explicit_mutation_guards() -> None:
    source = workflow_source()
    assert "options: [deploy, destroy]" in source
    assert "DEPLOY_PUBLIC_SANDBOX" in source
    assert "DESTROY_PUBLIC_SANDBOX" in source
    assert "environment: sandbox" in source
    assert "cancel-in-progress: false" in source


def test_public_sandbox_control_is_keyless_and_main_reachable() -> None:
    source = workflow_source()
    assert "id-token: write" in source
    assert "google-github-actions/auth@" in source
    assert "GCP_WIF_PROVIDER" in source
    assert "git merge-base --is-ancestor" in source
    assert "service-account-key" not in source.lower()
    assert "credentials_json" not in source
    assert "STAYLONG_API_TOKEN" not in source


def test_deploy_is_immutable_scanned_and_smoke_tested() -> None:
    source = workflow_source()
    assert "docker buildx build" in source
    assert "containerimage.digest" in source
    assert "@$digest" in source
    assert "aquasecurity/trivy-action@" in source
    assert 'terraform -chdir="$COMPONENT_PATH" apply -input=false tfplan' in source
    assert "tools/public_sandbox_smoke.py" in source
    assert "actions/upload-artifact@" in source


def test_terraform_scope_cannot_escape_public_sandbox() -> None:
    source = workflow_source()
    assert "COMPONENT_PATH: infra/terraform/components/public-sandbox" in source
    assert "PROJECT_CONFIG: staylong-public-sandbox.json" in source
    assert "ENVIRONMENT_CONFIG: sandbox.json" in source
    assert "STATE_PREFIX: staylong/sandbox/public-sandbox" in source
    assert "inputs.component" not in source
    assert "tools/cloudrun_smoke.py" not in source


def test_destroy_uses_a_saved_plan_and_retains_evidence() -> None:
    source = workflow_source()
    assert 'terraform -chdir="$COMPONENT_PATH" plan -destroy -input=false -out=tfplan' in source
    assert 'terraform -chdir="$COMPONENT_PATH" apply -input=false tfplan' in source
    assert "if: ${{ always() }}" in source
    assert "public-sandbox-destroy-evidence" in source

from pathlib import Path


SOURCE = Path(".github/workflows/public-domain-control.yml").read_text()


def test_public_domain_workflow_requires_explicit_approval_and_keyless_auth() -> None:
    assert "options: [provision, lockdown, destroy]" in SOURCE
    assert "PROVISION_PUBLIC_DOMAIN" in SOURCE
    assert "LOCKDOWN_PUBLIC_DOMAIN" in SOURCE
    assert "DESTROY_PUBLIC_EDGE" in SOURCE
    assert "environment: sandbox" in SOURCE
    assert "id-token: write" in SOURCE
    assert "git merge-base --is-ancestor" in SOURCE


def test_public_domain_workflow_keeps_the_cloudflare_token_secret() -> None:
    assert "CLOUDFLARE_API_TOKEN" in SOURCE
    assert 'echo "$CLOUDFLARE_API_TOKEN"' not in SOURCE
    assert "service-account-key" not in SOURCE.lower()


def test_public_domain_workflow_records_non_secret_evidence() -> None:
    assert "public-edge-evidence-" in SOURCE
    assert "certificate_status" in SOURCE
    assert "tools/public_domain_smoke.py" in SOURCE

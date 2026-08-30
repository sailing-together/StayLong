from pathlib import Path

ARCHITECTURE = Path("docs/architecture.md").read_text(encoding="utf-8")
DIAGRAM = Path("docs/architecture.mmd").read_text(encoding="utf-8")


def test_architecture_distinguishes_public_sandbox_from_private_oauth() -> None:
    for text in (ARCHITECTURE, DIAGRAM):
        assert "public sandbox" in text.lower()
        assert "Google Calendar" in text
        assert "Google ADK" in text or "ADK" in text
        assert "Firestore" in text
        assert "Cloud Tasks" in text or "Pub/Sub" in text
        assert "GitHub Actions" in text
        assert "WIF" in text

    assert "private" in ARCHITECTURE.lower()
    assert "approval" in ARCHITECTURE.lower()
    assert "does not" in ARCHITECTURE.lower()


def test_public_edge_runbook_records_security_and_lifecycle_boundaries() -> None:
    runbook = Path("docs/runbooks/public-edge-operations.md").read_text(encoding="utf-8")
    normalized = " ".join(runbook.lower().split())

    assert "CLOUDFLARE_API_TOKEN" in runbook
    assert "PROVISION_PUBLIC_DOMAIN" in runbook
    assert "LOCKDOWN_PUBLIC_DOMAIN" in runbook
    assert "DESTROY_PUBLIC_EDGE" in runbook
    assert "staylonghome.com" in runbook
    assert "temporary" in normalized
    assert "never deletes the registered domain" in normalized

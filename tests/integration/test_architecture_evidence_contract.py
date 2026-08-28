from pathlib import Path

ARCHITECTURE = Path("docs/architecture.md").read_text()
DIAGRAM = Path("docs/architecture.mmd").read_text()


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

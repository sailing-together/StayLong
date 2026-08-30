import pytest

from staylong.privacy.gemma import (
    GemmaPrivacyGuard,
    PrivacyGuardError,
    PrivacyRedaction,
    build_vertex_gemma_privacy_guard,
)


class FakeGemmaProvider:
    def __init__(self, response: object) -> None:
        self.response = response
        self.prompts: list[str] = []

    def generate_json(self, *, prompt: str) -> object:
        self.prompts.append(prompt)
        return self.response


def test_gemma_redacts_pii_with_a_strict_contract() -> None:
    provider = FakeGemmaProvider(
        {
            "redacted_text": "Please call [PHONE REDACTED] about the dark hallway.",
            "detected_categories": ["phone"],
        }
    )
    guard = GemmaPrivacyGuard(provider=provider)

    result = guard.redact("Please call 0412 345 678 about the dark hallway.")

    assert result == PrivacyRedaction(
        redacted_text="Please call [PHONE REDACTED] about the dark hallway.",
        detected_categories=("phone",),
    )
    assert "0412 345 678" in provider.prompts[0]
    assert "Return JSON only" in provider.prompts[0]


def test_gemma_rejects_untrusted_output_outside_the_contract() -> None:
    guard = GemmaPrivacyGuard(
        provider=FakeGemmaProvider({"redacted_text": "safe", "detected_categories": "phone"})
    )

    with pytest.raises(PrivacyGuardError, match="detected_categories"):
        guard.redact("A concern")


def test_gemma_rejects_empty_redacted_text() -> None:
    guard = GemmaPrivacyGuard(
        provider=FakeGemmaProvider({"redacted_text": " ", "detected_categories": []})
    )

    with pytest.raises(PrivacyGuardError, match="redacted_text"):
        guard.redact("A concern")


def test_vertex_privacy_guard_defaults_to_gemma_maas_model(monkeypatch) -> None:
    captured: dict[str, str] = {}

    class RecordingProvider:
        def __init__(self, *, project_id: str, location: str, model_id: str) -> None:
            captured.update(project_id=project_id, location=location, model_id=model_id)

    monkeypatch.delenv("STAYLONG_PRIVACY_MODEL", raising=False)
    monkeypatch.setattr("staylong.privacy.gemma.VertexGemmaJsonProvider", RecordingProvider)

    build_vertex_gemma_privacy_guard(project_id="stay-long", location="global")

    assert captured == {
        "project_id": "stay-long",
        "location": "global",
        "model_id": "gemma-4-26b-a4b-it-maas",
    }

"""Gemma-backed PII redaction with a strict, fail-closed response contract."""

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol


class PrivacyGuardError(ValueError):
    """Raised when the privacy model returns an unsafe or invalid response."""


@dataclass(frozen=True, slots=True)
class PrivacyRedaction:
    """The only privacy result allowed to cross into the application workflow."""

    redacted_text: str
    detected_categories: tuple[str, ...]


class GemmaJsonProvider(Protocol):
    """Small provider boundary so local tests never call Vertex AI."""

    def generate_json(self, *, prompt: str) -> object: ...


class GemmaPrivacyGuard:
    """Use Gemma to remove unnecessary personal data before persistence or tools."""

    def __init__(self, *, provider: GemmaJsonProvider) -> None:
        self._provider = provider

    def redact(self, text: str) -> PrivacyRedaction:
        if not text.strip():
            raise PrivacyGuardError("text must be non-empty.")
        response = self._provider.generate_json(prompt=self._prompt(text))
        if not isinstance(response, Mapping):
            raise PrivacyGuardError("Gemma privacy response must be a JSON object.")
        if set(response) != {"redacted_text", "detected_categories"}:
            raise PrivacyGuardError("Gemma privacy response must contain the contract fields.")
        redacted = response["redacted_text"]
        categories = response["detected_categories"]
        if not isinstance(redacted, str) or not redacted.strip():
            raise PrivacyGuardError("redacted_text must be a non-empty string.")
        if not isinstance(categories, list) or not all(
            isinstance(item, str) and item.strip() for item in categories
        ):
            raise PrivacyGuardError("detected_categories must be a list of non-empty strings.")
        return PrivacyRedaction(redacted_text=redacted, detected_categories=tuple(categories))

    @staticmethod
    def _prompt(text: str) -> str:
        return (
            "You are the StayLong privacy filter. Return JSON only with exactly these fields: "
            "redacted_text (string) and detected_categories (array of strings). Replace only "
            "unnecessary personal data such as names, phone numbers, emails, street addresses "
            "or government identifiers with clear bracketed labels. Preserve the care concern, "
            "safety words and meaning. Never invent facts.\n\n"
            f"Text to protect:\n{text}\n\nReturn JSON only."
        )


class VertexGemmaJsonProvider:
    """Invoke Gemma through the Vertex AI GenAI SDK in production."""

    def __init__(
        self,
        *,
        project_id: str,
        location: str = "global",
        model_id: str = "gemma-3-27b-it",
    ) -> None:
        if not project_id.strip():
            raise ValueError("project_id must be configured for Gemma.")
        self._client = self._new_client(project_id=project_id, location=location)
        self._model_id = model_id

    @staticmethod
    def _new_client(*, project_id: str, location: str) -> object:
        try:
            from google import genai
        except ImportError as error:  # pragma: no cover - production dependency only
            raise RuntimeError(
                "Install staylong[agents] to construct the Vertex Gemma client."
            ) from error
        return genai.Client(vertexai=True, project=project_id, location=location)

    def generate_json(self, *, prompt: str) -> object:
        response = self._client.models.generate_content(
            model=self._model_id,
            contents=prompt,
            config={"response_mime_type": "application/json"},
        )
        text = getattr(response, "text", None)
        if not isinstance(text, str) or not text.strip():
            raise PrivacyGuardError("Gemma did not return a JSON response.")
        try:
            return json.loads(text)
        except json.JSONDecodeError as error:
            raise PrivacyGuardError("Gemma returned malformed JSON.") from error


def build_vertex_gemma_privacy_guard(
    *, project_id: str, location: str = "global"
) -> GemmaPrivacyGuard:
    """Build the production privacy guard with a Vertex-hosted Gemma model."""
    return GemmaPrivacyGuard(
        provider=VertexGemmaJsonProvider(project_id=project_id, location=location)
    )

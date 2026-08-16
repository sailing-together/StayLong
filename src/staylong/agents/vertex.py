"""Validated Vertex AI configuration and bounded adapters for Google ADK."""

import os
from collections.abc import Mapping, MutableMapping
from dataclasses import dataclass
from typing import Protocol

VERTEX_GEMINI_MODEL = "gemini-3.6-flash"


class VertexConfigurationError(ValueError):
    """Raised when an ADK process has not been configured for Vertex AI."""


@dataclass(frozen=True, slots=True)
class VertexRuntimeConfig:
    """The explicit environment contract required for Vertex-backed ADK calls."""

    project_id: str
    location: str
    model_id: str = VERTEX_GEMINI_MODEL

    def __post_init__(self) -> None:
        """Keep direct construction as strict as environment-derived configuration."""
        if not self.project_id.strip():
            raise VertexConfigurationError("GOOGLE_CLOUD_PROJECT must be configured for Vertex AI.")
        if self.location != "global":
            raise VertexConfigurationError(
                "GOOGLE_CLOUD_LOCATION must be global for gemini-3.6-flash inference."
            )

    @classmethod
    def from_environment(
        cls, environment: Mapping[str, str] | None = None
    ) -> "VertexRuntimeConfig":
        """Validate the documented ADK Vertex environment before construction."""
        values = os.environ if environment is None else environment
        project_id = values.get("GOOGLE_CLOUD_PROJECT", "").strip()
        location = values.get("GOOGLE_CLOUD_LOCATION", "").strip()
        use_vertex = values.get("GOOGLE_GENAI_USE_VERTEXAI", "").casefold()

        if not project_id:
            raise VertexConfigurationError("GOOGLE_CLOUD_PROJECT must be configured for Vertex AI.")
        if not location:
            raise VertexConfigurationError(
                "GOOGLE_CLOUD_LOCATION must be configured for Vertex AI."
            )
        if use_vertex != "true":
            raise VertexConfigurationError("GOOGLE_GENAI_USE_VERTEXAI must be true for Vertex AI.")

        return cls(project_id=project_id, location=location)

    def bind_to_adk_environment(self, environment: MutableMapping[str, str]) -> None:
        """Bind validated Vertex values to the environment consumed by Google ADK."""
        environment.update(
            {
                "GOOGLE_CLOUD_PROJECT": self.project_id,
                "GOOGLE_CLOUD_LOCATION": self.location,
                "GOOGLE_GENAI_USE_VERTEXAI": "true",
            }
        )


class AdkAgentFactory(Protocol):
    """Creates an ADK agent after the Vertex environment has been validated."""

    def __call__(
        self,
        *,
        name: str,
        model_id: str,
        instruction: str,
        vertex_config: VertexRuntimeConfig,
    ) -> object: ...


class AdkJsonExecutor(Protocol):
    """Application-owned bridge from an ADK runner to JSON-compatible output."""

    def generate_json(self, *, agent: object, prompt: str) -> object: ...


@dataclass(frozen=True, slots=True)
class _AdkJsonProvider:
    """Makes a supplied ADK runner available through the local provider contract."""

    agent: object
    executor: AdkJsonExecutor

    def generate_json(self, *, system_instruction: str, prompt: str) -> object:
        """Run the preconfigured agent; policy validation remains in its caller."""
        del system_instruction
        return self.executor.generate_json(agent=self.agent, prompt=prompt)


def _load_adk_types() -> tuple[type[object], type[object]]:
    """Load ADK lazily so local contract tests need no Google installation."""
    try:
        from google.adk.agents import Agent
        from google.adk.models import Gemini
    except ImportError as error:  # pragma: no cover - production dependency only
        raise RuntimeError("Install staylong[agents] to construct the Google ADK agent.") from error
    return Agent, Gemini


def build_google_adk_agent(
    *,
    name: str,
    model_id: str,
    instruction: str,
    vertex_config: VertexRuntimeConfig,
) -> object:
    """Build an ADK ``Agent`` after Vertex mode, project, and location are validated.

    Google ADK reads the validated `GOOGLE_CLOUD_PROJECT`,
    `GOOGLE_CLOUD_LOCATION`, and `GOOGLE_GENAI_USE_VERTEXAI=true` runtime
    configuration when its Gemini model executes. The runner itself is injected
    through ``AdkJsonExecutor`` so application code can keep the policy boundary
    around every response.
    """
    vertex_config.bind_to_adk_environment(os.environ)
    agent_type, gemini_type = _load_adk_types()

    return agent_type(
        name=name,
        model=gemini_type(model=model_id),
        instruction=instruction,
        tools=[],
    )

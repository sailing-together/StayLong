"""Structured intake that keeps emergency routing deterministic and local-testable."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal, Protocol

from staylong.agents.prompts import INTAKE_SYSTEM_INSTRUCTION
from staylong.policy.emergency import EMERGENCY_ROUTE, route_concern

HomeArea = Literal["bathroom", "entry", "bedroom", "kitchen", "other"]
NextStep = Literal[
    "prepare_assessment_pack", "request_family_confirmation", "other"
]
VERTEX_GEMINI_MODEL = "gemini-3.5-pro"


class StructuredModelProvider(Protocol):
    """Minimal adapter boundary for a model that returns JSON-compatible output."""

    def generate_json(self, *, system_instruction: str, prompt: str) -> object: ...


class IntakeSchemaError(ValueError):
    """Raised when model output is not the constrained intake schema."""


class EmergencyRouteRequired(RuntimeError):
    """Raised before model use when deterministic emergency policy matches."""


def _required_string(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise IntakeSchemaError(f"{field_name} must be a non-empty string.")
    return value


def _string_list(value: object, field_name: str) -> tuple[str, ...]:
    is_string_list = isinstance(value, list) and all(
        isinstance(item, str) and item.strip() for item in value
    )
    if not is_string_list:
        raise IntakeSchemaError(f"{field_name} must be a list of non-empty strings.")
    return tuple(value)


@dataclass(frozen=True, slots=True)
class IntakeOutput:
    """The validated, non-clinical output contract for a reported concern."""

    plain_language_summary: str
    home_area: HomeArea
    reported_difficulty: str
    missing_facts: tuple[str, ...]
    assessment_preparation_topics: tuple[str, ...]
    proposed_next_step: NextStep

    @classmethod
    def from_model_response(cls, response: object) -> "IntakeOutput":
        """Validate model data before it crosses the intake-agent boundary."""
        if not isinstance(response, Mapping):
            raise IntakeSchemaError("Intake response must be a JSON object.")

        expected_fields = {
            "plain_language_summary",
            "home_area",
            "reported_difficulty",
            "missing_facts",
            "assessment_preparation_topics",
            "proposed_next_step",
        }
        if set(response) != expected_fields:
            raise IntakeSchemaError("Intake response must contain exactly the contract fields.")

        home_area = response["home_area"]
        if home_area not in {"bathroom", "entry", "bedroom", "kitchen", "other"}:
            raise IntakeSchemaError("home_area is not permitted by the intake contract.")

        next_step = response["proposed_next_step"]
        if next_step not in {
            "prepare_assessment_pack",
            "request_family_confirmation",
            "other",
        }:
            raise IntakeSchemaError("proposed_next_step is not permitted by the intake contract.")

        return cls(
            plain_language_summary=_required_string(
                response["plain_language_summary"], "plain_language_summary"
            ),
            home_area=home_area,
            reported_difficulty=_required_string(
                response["reported_difficulty"], "reported_difficulty"
            ),
            missing_facts=_string_list(response["missing_facts"], "missing_facts"),
            assessment_preparation_topics=_string_list(
                response["assessment_preparation_topics"], "assessment_preparation_topics"
            ),
            proposed_next_step=next_step,
        )


@dataclass(slots=True)
class IntakeAgent:
    """Runs a supplied local or production provider behind the intake contract."""

    provider: StructuredModelProvider

    def intake(self, concern: str) -> IntakeOutput:
        """Return validated intake data, never asking a model to assess emergencies."""
        if route_concern(concern) == EMERGENCY_ROUTE:
            raise EmergencyRouteRequired(
                "This concern requires the emergency route. For urgent Australian emergencies, "
                "call Triple Zero (000)."
            )

        response = self.provider.generate_json(
            system_instruction=INTAKE_SYSTEM_INSTRUCTION,
            prompt=f"Supplied concern:\n{concern}",
        )
        return IntakeOutput.from_model_response(response)


def build_vertex_adk_intake_agent() -> object:
    """Build the production Google ADK configuration without executing a model call.

    Callers run this ADK agent through a JSON provider adapter and then pass its response
    through :class:`IntakeOutput`; tests inject ``StructuredModelProvider`` instead.
    """
    try:
        from google.adk.agents import Agent
    except ImportError as error:  # pragma: no cover - exercised only in production setup
        raise RuntimeError("Install staylong[agents] to construct the Google ADK agent.") from error

    return Agent(
        name="staylong_intake",
        model=VERTEX_GEMINI_MODEL,
        instruction=INTAKE_SYSTEM_INSTRUCTION,
    )

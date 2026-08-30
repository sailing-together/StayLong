"""Structured intake that keeps emergency routing deterministic and local-testable."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal, Protocol

from staylong.agents.prompts import INTAKE_SYSTEM_INSTRUCTION
from staylong.agents.vertex import (
    AdkAgentFactory,
    AdkJsonExecutor,
    VertexRuntimeConfig,
    _AdkJsonProvider,
    build_google_adk_agent,
)
from staylong.policy.emergency import (
    EMERGENCY_ROUTE,
    requires_medical_triage_refusal,
    route_concern,
)

HomeArea = Literal["bathroom", "entry", "bedroom", "kitchen", "other"]
NextStep = Literal[
    "prepare_assessment_pack", "request_family_confirmation", "other"
]
MissingFactKey = Literal[
    "assessment_status", "housing_tenure", "support_contacts", "household_availability",
    "home_access", "information_sharing_consent",
]

_MISSING_FACT_KEYS = set(MissingFactKey.__args__)


class StructuredModelProvider(Protocol):
    """Minimal adapter boundary for a model that returns JSON-compatible output."""

    def generate_json(self, *, system_instruction: str, prompt: str) -> object: ...


class IntakeSchemaError(ValueError):
    """Raised when model output is not the constrained intake schema."""


class EmergencyRouteRequired(RuntimeError):
    """Raised before model use when deterministic emergency policy matches."""


class MedicalTriageRefusalRequired(RuntimeError):
    """Raised before model use for requests requiring clinical judgement."""


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
class MissingFact:
    """A permitted non-clinical question needed to prepare household coordination."""

    key: MissingFactKey
    question: str
    reason: str

    @classmethod
    def from_model_response(cls, value: object) -> "MissingFact":
        if not isinstance(value, Mapping) or set(value) != {"key", "question", "reason"}:
            raise IntakeSchemaError(
                "Each missing_facts item must contain exactly key, question and reason."
            )
        key = value["key"]
        if key not in _MISSING_FACT_KEYS:
            raise IntakeSchemaError("missing_facts key is not permitted by the intake contract.")
        return cls(
            key=key,
            question=_required_string(value["question"], "missing_facts question"),
            reason=_required_string(value["reason"], "missing_facts reason"),
        )


def _missing_facts(value: object) -> tuple[MissingFact, ...]:
    if not isinstance(value, list):
        raise IntakeSchemaError("missing_facts must be a list.")
    return tuple(MissingFact.from_model_response(item) for item in value)


_CORE_MISSING_FACTS = (
    MissingFact(
        key="assessment_status",
        question=(
            "Have you already had an aged care assessment or an occupational therapy home visit?"
        ),
        reason="This helps prepare the right next step.",
    ),
    MissingFact(
        key="housing_tenure",
        question="Is the home owned or rented?",
        reason="Permission requirements may affect planning.",
    ),
    MissingFact(
        key="support_contacts",
        question="Would you like to involve anyone now?",
        reason="StayLong only shares information when invited.",
    ),
)


def _stable_missing_facts(facts: tuple[MissingFact, ...]) -> tuple[MissingFact, ...]:
    """Keep the first intake handoff consistent when the model returns too few facts."""
    result = list(facts)
    for core_fact in _CORE_MISSING_FACTS:
        if len(result) >= 3:
            break
        if all(item.key != core_fact.key for item in result):
            result.append(core_fact)
    return tuple(result)


@dataclass(frozen=True, slots=True)
class IntakeOutput:
    """The validated, non-clinical output contract for a reported concern."""

    plain_language_summary: str
    home_area: HomeArea
    reported_difficulty: str
    missing_facts: tuple[MissingFact, ...]
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
            missing_facts=_stable_missing_facts(_missing_facts(response["missing_facts"])),
            assessment_preparation_topics=_string_list(
                response["assessment_preparation_topics"], "assessment_preparation_topics"
            ),
            proposed_next_step=next_step,
        )


@dataclass(frozen=True, slots=True)
class AssessmentPreparationPack:
    """A shareable, non-clinical preparation pack for a future aged-care assessment."""

    concern_summary: str
    reported_difficulty: str
    information_to_confirm: tuple[MissingFact, ...]
    assessment_discussion_topics: tuple[str, ...]
    official_pathways: tuple[str, ...]
    proposed_next_step: NextStep
    boundary_note: str
    home_area: HomeArea = "other"


def _assessment_pack(output: IntakeOutput) -> AssessmentPreparationPack:
    return AssessmentPreparationPack(
        concern_summary=output.plain_language_summary,
        reported_difficulty=output.reported_difficulty,
        information_to_confirm=output.missing_facts,
        assessment_discussion_topics=output.assessment_preparation_topics,
        official_pathways=("https://www.myagedcare.gov.au/",),
        proposed_next_step=output.proposed_next_step,
        boundary_note=(
            "StayLong prepares and coordinates information only; it does not determine "
            "eligibility, diagnose needs, submit applications or choose providers."
        ),
        home_area=output.home_area,
    )


class IntakeAgent:
    """Runs a supplied local or production provider behind the intake contract."""

    def __init__(self, *, provider: StructuredModelProvider) -> None:
        """Keep the provider private so calls cannot skip safety and schema checks."""
        self._provider = provider

    def intake(self, concern: str) -> IntakeOutput:
        """Return validated intake data, never asking a model to assess emergencies."""
        if route_concern(concern) == EMERGENCY_ROUTE:
            raise EmergencyRouteRequired(
                "This concern requires the emergency route. For urgent Australian emergencies, "
                "call Triple Zero (000)."
            )
        if requires_medical_triage_refusal(concern):
            raise MedicalTriageRefusalRequired(
                "StayLong cannot provide medical triage. If the person may be in immediate "
                "danger, call Triple Zero (000); otherwise contact a qualified clinician."
            )

        response = self._provider.generate_json(
            system_instruction=INTAKE_SYSTEM_INSTRUCTION,
            prompt=f"Supplied concern:\n{concern}",
        )
        return IntakeOutput.from_model_response(response)

    def prepare_assessment_pack(self, concern: str) -> AssessmentPreparationPack:
        """Turn validated intake into a non-clinical pack without another model call."""
        return _assessment_pack(self.intake(concern))


def build_vertex_adk_intake_agent(
    *,
    executor: AdkJsonExecutor,
    agent_factory: AdkAgentFactory = build_google_adk_agent,
    environment: Mapping[str, str] | None = None,
) -> IntakeAgent:
    """Build an intake wrapper that enforces safety and schema boundaries around ADK.

    ``executor`` is the application-owned ADK Runner bridge. It is intentionally
    injected because Runner/session lifecycle belongs to the serving application;
    the wrapper never returns a prompt-only ADK agent that callers could invoke
    around deterministic emergency routing or schema validation.
    """
    vertex_config = VertexRuntimeConfig.from_environment(environment)
    adk_agent = agent_factory(
        name="staylong_intake",
        model_id=vertex_config.model_id,
        instruction=INTAKE_SYSTEM_INSTRUCTION,
        vertex_config=vertex_config,
    )
    return IntakeAgent(provider=_AdkJsonProvider(agent=adk_agent, executor=executor))

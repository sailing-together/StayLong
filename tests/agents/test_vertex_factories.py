"""Contract tests for the production ADK wrappers and Vertex configuration."""

from datetime import UTC, datetime

import pytest


class RecordedAgentFactory:
    def __init__(self) -> None:
        self.requests: list[dict[str, object]] = []

    def __call__(
        self,
        *,
        name: str,
        model_id: str,
        instruction: str,
        vertex_config: object,
    ) -> object:
        request = {
            "name": name,
            "model_id": model_id,
            "instruction": instruction,
            "vertex_config": vertex_config,
        }
        self.requests.append(request)
        return request


class RecordedExecutor:
    def __init__(self, response: object) -> None:
        self.response = response
        self.agents: list[object] = []
        self.prompts: list[str] = []

    def generate_json(self, *, agent: object, prompt: str) -> object:
        self.agents.append(agent)
        self.prompts.append(prompt)
        return self.response


def _vertex_environment() -> dict[str, str]:
    return {
        "GOOGLE_CLOUD_PROJECT": "staylong-demo",
        "GOOGLE_CLOUD_LOCATION": "australia-southeast1",
        "GOOGLE_GENAI_USE_VERTEXAI": "true",
    }


def test_vertex_configuration_requires_project_location_and_vertex_mode() -> None:
    from staylong.agents.vertex import VertexConfigurationError, VertexRuntimeConfig

    with pytest.raises(VertexConfigurationError, match="GOOGLE_CLOUD_PROJECT"):
        VertexRuntimeConfig.from_environment(
            {
                "GOOGLE_CLOUD_LOCATION": "australia-southeast1",
                "GOOGLE_GENAI_USE_VERTEXAI": "true",
            }
        )

    with pytest.raises(VertexConfigurationError, match="GOOGLE_GENAI_USE_VERTEXAI"):
        VertexRuntimeConfig.from_environment(
            {
                "GOOGLE_CLOUD_PROJECT": "staylong-demo",
                "GOOGLE_CLOUD_LOCATION": "australia-southeast1",
                "GOOGLE_GENAI_USE_VERTEXAI": "false",
            }
        )


def test_intake_factory_keeps_emergency_and_schema_boundaries_outside_adk() -> None:
    from staylong.agents.intake import (
        EmergencyRouteRequired,
        IntakeSchemaError,
        build_vertex_adk_intake_agent,
    )

    factory = RecordedAgentFactory()
    executor = RecordedExecutor(
        {
            "plain_language_summary": "The shower entry is difficult.",
            "home_area": "bathroom",
            "reported_difficulty": "Stepping into the shower is difficult.",
            "missing_facts": [],
            "assessment_preparation_topics": ["Describe the shower entry."],
            "proposed_next_step": "prepare_assessment_pack",
        }
    )
    agent = build_vertex_adk_intake_agent(
        executor=executor,
        agent_factory=factory,
        environment=_vertex_environment(),
    )

    with pytest.raises(EmergencyRouteRequired):
        agent.intake("The person is unconscious.")

    result = agent.intake("The shower entry is difficult.")

    assert result.home_area == "bathroom"
    assert executor.prompts == ["Supplied concern:\nThe shower entry is difficult."]
    assert factory.requests[0]["model_id"] == "gemini-3.6-flash"
    assert factory.requests[0]["name"] == "staylong_intake"

    executor.response = {"summary": "A prompt cannot bypass the output schema."}

    with pytest.raises(IntakeSchemaError):
        agent.intake("The shower entry is difficult.")


def test_coordinator_factory_returns_a_draft_without_approval() -> None:
    from staylong.agents.coordinator import (
        CoordinationRequest,
        build_vertex_adk_coordination_agent,
    )

    factory = RecordedAgentFactory()
    agent = build_vertex_adk_coordination_agent(
        agent_factory=factory,
        environment=_vertex_environment(),
    )

    result = agent.coordinate(
        request=CoordinationRequest(
            case_id="case-001",
            action_type="message.send",
            action_revision=1,
            owner="Alex Chen",
            due_at=datetime(2026, 8, 17, 9, tzinfo=UTC),
            reason="Request a preferred follow-up time.",
        ),
        approval=None,
        now=datetime(2026, 8, 16, tzinfo=UTC),
    )

    assert result.status == "draft"
    assert result.may_execute is False
    assert factory.requests[0]["model_id"] == "gemini-3.6-flash"
    assert factory.requests[0]["name"] == "staylong_coordinator"

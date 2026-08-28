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
        "GOOGLE_CLOUD_LOCATION": "global",
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
                "GOOGLE_CLOUD_LOCATION": "global",
                "GOOGLE_GENAI_USE_VERTEXAI": "false",
            }
        )

    with pytest.raises(VertexConfigurationError, match="global"):
        VertexRuntimeConfig.from_environment(
            {
                "GOOGLE_CLOUD_PROJECT": "staylong-demo",
                "GOOGLE_CLOUD_LOCATION": "australia-southeast1",
                "GOOGLE_GENAI_USE_VERTEXAI": "true",
            }
        )

    with pytest.raises(VertexConfigurationError, match="global"):
        VertexRuntimeConfig(
            project_id="staylong-demo",
            location="australia-southeast1",
        )


@pytest.mark.parametrize(
    "text",
    [
        '{"plain_language_summary": "A concern"}',
        '```json\n{"plain_language_summary": "A concern"}\n```',
        'Here is the result:\n{"plain_language_summary": "A concern"}',
    ],
)
def test_adk_json_parser_accepts_common_model_wrappers(text: str) -> None:
    from staylong.agents.vertex import _parse_json_response

    assert _parse_json_response(text) == {"plain_language_summary": "A concern"}


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
    assert not hasattr(agent, "provider")
    assert not hasattr(agent, "adk_agent")

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


def test_google_adk_factory_binds_validated_vertex_runtime_and_disables_tools(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from staylong.agents import vertex

    class FakeGemini:
        def __init__(self, *, model: str) -> None:
            self.model = model

    class FakeAgent:
        def __init__(self, **kwargs: object) -> None:
            self.kwargs = kwargs

    runtime_environment: dict[str, str] = {}
    monkeypatch.setattr(vertex, "_load_adk_types", lambda: (FakeAgent, FakeGemini))
    monkeypatch.setattr(vertex.os, "environ", runtime_environment)

    config = vertex.VertexRuntimeConfig(
        project_id="staylong-demo",
        location="global",
    )
    agent = vertex.build_google_adk_agent(
        name="staylong_intake",
        model_id="gemini-3.6-flash",
        instruction="contract instruction",
        vertex_config=config,
    )

    assert runtime_environment == {
        "GOOGLE_CLOUD_PROJECT": "staylong-demo",
        "GOOGLE_CLOUD_LOCATION": "global",
        "GOOGLE_GENAI_USE_VERTEXAI": "true",
    }
    assert isinstance(agent, FakeAgent)
    assert isinstance(agent.kwargs["model"], FakeGemini)
    assert agent.kwargs["model"].model == "gemini-3.6-flash"
    assert agent.kwargs["tools"] == []


def test_google_adk_executor_returns_only_the_final_json_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A partial ADK event must not be mistaken for the structured intake output."""
    from google.adk import runners, sessions
    from google.genai import types

    from staylong.agents.vertex import GoogleAdkJsonExecutor

    class FakeSession:
        id = "session-001"

    class FakeSessions:
        async def create_session(self, **kwargs: object) -> FakeSession:
            assert kwargs["app_name"] == "staylong_intake"
            return FakeSession()

    class FakeEvent:
        def __init__(self, text: str, final: bool) -> None:
            self.content = type("Content", (), {"parts": [type("Part", (), {"text": text})()]})()
            self._final = final

        def is_final_response(self) -> bool:
            return self._final

    class FakeRunner:
        def __init__(self, **kwargs: object) -> None:
            assert kwargs["app_name"] == "staylong_intake"

        async def run_async(self, **kwargs: object):
            assert kwargs["session_id"] == "session-001"
            yield FakeEvent('{"ignore": true}', False)
            yield FakeEvent('{"accepted": true}', True)

    class FakePart:
        def __init__(self, *, text: str) -> None:
            self.text = text

    class FakeContent:
        def __init__(self, **kwargs: object) -> None:
            self.kwargs = kwargs

    monkeypatch.setattr(runners, "Runner", FakeRunner)
    monkeypatch.setattr(sessions, "InMemorySessionService", FakeSessions)
    monkeypatch.setattr(types, "Part", FakePart)
    monkeypatch.setattr(types, "Content", FakeContent)

    result = GoogleAdkJsonExecutor().generate_json(agent=object(), prompt="A concern")

    assert result == {"accepted": True}

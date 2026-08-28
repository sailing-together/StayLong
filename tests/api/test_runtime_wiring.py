"""Runtime construction tests: deployed paths must be Vertex/ADK + Firestore."""

import pytest

VALID_ENVIRONMENT = {
    "STAYLONG_API_TOKEN": "token",
    "GOOGLE_CLOUD_PROJECT": "stay-long",
    "GOOGLE_CLOUD_LOCATION": "global",
    "GOOGLE_GENAI_USE_VERTEXAI": "true",
}


class RecordedBuilder:
    def __init__(self) -> None:
        self.environment: dict[str, str] | None = None

    def __call__(self, *, executor: object, environment: dict[str, str]) -> object:
        del executor
        self.environment = environment
        return object()


class RecordedGemmaBuilder:
    def __init__(self) -> None:
        self.project_id: str | None = None

    def __call__(self, *, project_id: str, location: str) -> object:
        self.project_id = project_id
        assert location == "global"
        return object()


def test_runtime_uses_vertex_intake_and_firestore_storage() -> None:
    from staylong.api.runtime import build_runtime_workflow
    from tests.services.fake_firestore import FakeFirestoreClient

    builder = RecordedBuilder()
    workflow = build_runtime_workflow(
        VALID_ENVIRONMENT,
        firestore_client=FakeFirestoreClient(),
        executor=object(),
        intake_builder=builder,
    )

    assert workflow.repository.__class__.__name__ == "FirestoreWorkflowRepository"
    assert builder.environment == VALID_ENVIRONMENT
    assert workflow.calendar.integration_mode == "sandbox"


def test_runtime_rejects_missing_vertex_configuration() -> None:
    from staylong.agents.vertex import VertexConfigurationError
    from staylong.api.runtime import build_runtime_workflow

    with pytest.raises(VertexConfigurationError):
        build_runtime_workflow({"STAYLONG_API_TOKEN": "token"})


def test_runtime_uses_google_adapters_only_with_complete_oauth_configuration() -> None:
    from staylong.api.runtime import build_runtime_workflow
    from tests.services.fake_firestore import FakeFirestoreClient

    environment = {
        **VALID_ENVIRONMENT,
        "STAYLONG_GOOGLE_ACTIONS_MODE": "oauth",
        "STAYLONG_GOOGLE_OAUTH_ACCESS_TOKEN": "test-token",
        "STAYLONG_GOOGLE_CALENDAR_ID": "primary",
    }
    workflow = build_runtime_workflow(
        environment,
        firestore_client=FakeFirestoreClient(),
        executor=object(),
        intake_builder=RecordedBuilder(),
    )

    assert workflow.calendar.integration_mode == "google_oauth"
    assert workflow.contact_drafts.integration_mode == "google_oauth"


def test_runtime_enables_gemma_privacy_guard_when_configured() -> None:
    from staylong.api.runtime import build_runtime_workflow
    from tests.services.fake_firestore import FakeFirestoreClient

    gemma_builder = RecordedGemmaBuilder()
    build_runtime_workflow(
        {**VALID_ENVIRONMENT, "STAYLONG_GEMMA_ENABLED": "true"},
        firestore_client=FakeFirestoreClient(),
        executor=object(),
        intake_builder=RecordedBuilder(),
        gemma_builder=gemma_builder,
    )

    assert gemma_builder.project_id == "stay-long"


def test_runtime_builds_calendar_oauth_only_with_complete_client_configuration() -> None:
    from staylong.api.runtime import build_calendar_oauth
    from staylong.services.google_oauth import InMemoryOAuthTokenStore

    oauth = build_calendar_oauth(
        {
            **VALID_ENVIRONMENT,
            "STAYLONG_GOOGLE_OAUTH_CLIENT_ID": "client-id",
            "STAYLONG_GOOGLE_OAUTH_CLIENT_SECRET": "client-secret",
            "STAYLONG_GOOGLE_OAUTH_REDIRECT_URI": "https://staylong.example.com/callback",
        },
        token_store=InMemoryOAuthTokenStore(),
    )

    assert oauth is not None
    assert oauth.calendar_scope.endswith("calendar.events")


def test_runtime_rejects_partial_calendar_oauth_configuration() -> None:
    from staylong.api.runtime import build_calendar_oauth

    with pytest.raises(ValueError, match="incomplete"):
        build_calendar_oauth(
            {**VALID_ENVIRONMENT, "STAYLONG_GOOGLE_OAUTH_CLIENT_ID": "client-id"}
        )

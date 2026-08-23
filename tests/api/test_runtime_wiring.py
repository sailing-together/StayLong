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


def test_runtime_rejects_missing_vertex_configuration() -> None:
    from staylong.agents.vertex import VertexConfigurationError
    from staylong.api.runtime import build_runtime_workflow

    with pytest.raises(VertexConfigurationError):
        build_runtime_workflow({"STAYLONG_API_TOKEN": "token"})

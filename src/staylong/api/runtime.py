"""Explicit production-only construction for StayLong's deployed workflow."""

import os
from collections.abc import Callable, Mapping
from typing import Any

from staylong.agents.intake import IntakeAgent, build_vertex_adk_intake_agent
from staylong.agents.vertex import AdkJsonExecutor, GoogleAdkJsonExecutor, VertexRuntimeConfig
from staylong.privacy.gemma import GemmaPrivacyGuard, build_vertex_gemma_privacy_guard
from staylong.services.events import FirestoreEventRepository
from staylong.services.google_actions import build_action_adapters
from staylong.services.taskmaster import FirestoreWorkflowRepository, TaskmasterWorkflow

IntakeBuilder = Callable[..., IntakeAgent]
GemmaBuilder = Callable[..., GemmaPrivacyGuard]


def build_runtime_workflow(
    environment: Mapping[str, str] | None = None,
    *,
    firestore_client: Any | None = None,
    executor: AdkJsonExecutor | object | None = None,
    intake_builder: IntakeBuilder = build_vertex_adk_intake_agent,
    gemma_builder: GemmaBuilder = build_vertex_gemma_privacy_guard,
) -> TaskmasterWorkflow:
    """Build the only Cloud Run workflow: Vertex ADK intake plus Firestore state.

    This deliberately validates Vertex configuration before opening a Firestore
    client. A deployment cannot silently replace Gemini/ADK with a local stub.
    """
    values = dict(os.environ if environment is None else environment)
    VertexRuntimeConfig.from_environment(values)
    adk_executor = executor or GoogleAdkJsonExecutor()
    intake_agent = intake_builder(executor=adk_executor, environment=values)
    action_adapters = build_action_adapters(values)
    privacy_guard = (
        gemma_builder(
            project_id=values["GOOGLE_CLOUD_PROJECT"],
            location=values["GOOGLE_CLOUD_LOCATION"],
        )
        if values.get("STAYLONG_GEMMA_ENABLED", "").casefold() == "true"
        else None
    )
    return TaskmasterWorkflow(
        intake_agent=intake_agent,
        repository=FirestoreWorkflowRepository(client=firestore_client),
        event_repository=FirestoreEventRepository(client=firestore_client),
        calendar=action_adapters.calendar,
        contact_drafts=action_adapters.contact_drafts,
        privacy_guard=privacy_guard,
    )

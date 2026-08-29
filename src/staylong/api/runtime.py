"""Explicit production-only construction for StayLong's deployed workflow."""

import os
from collections.abc import Callable, Mapping
from datetime import timedelta
from typing import Any

from staylong.agents.intake import IntakeAgent, build_vertex_adk_intake_agent
from staylong.agents.vertex import AdkJsonExecutor, GoogleAdkJsonExecutor, VertexRuntimeConfig
from staylong.api.app import PublicSandboxConfig
from staylong.privacy.gemma import GemmaPrivacyGuard, build_vertex_gemma_privacy_guard
from staylong.services.events import FirestoreEventRepository
from staylong.services.google_actions import GoogleOAuthAccessTokenProvider, build_action_adapters
from staylong.services.google_oauth import GoogleCalendarOAuth, OAuthTokenStore
from staylong.services.public_sessions import (
    FirestorePublicCaseAccessRepository,
)
from staylong.services.taskmaster import FirestoreWorkflowRepository, TaskmasterWorkflow

IntakeBuilder = Callable[..., IntakeAgent]
GemmaBuilder = Callable[..., GemmaPrivacyGuard]


def build_public_sandbox_config(
    environment: Mapping[str, str], *, firestore_client: Any
) -> PublicSandboxConfig | None:
    """Enable anonymous public routes only for the explicit sandbox runtime."""
    if environment.get("STAYLONG_PUBLIC_SANDBOX", "").casefold() != "true":
        return None
    secret = environment.get("STAYLONG_PUBLIC_SESSION_SECRET", "").strip()
    if not secret:
        raise RuntimeError(
            "STAYLONG_PUBLIC_SESSION_SECRET must be configured for the public sandbox"
        )
    return PublicSandboxConfig(
        session_secret=secret,
        session_lifetime=timedelta(hours=24),
        case_access=FirestorePublicCaseAccessRepository(client=firestore_client),
        cookie_secure=True,
        # People may go back and try a different example while evaluating the
        # public demo. Keep a bounded per-session allowance without making a
        # normal correction look like a broken service.
        max_cases_per_session=10,
    )


def build_calendar_oauth(
    environment: Mapping[str, str],
    *,
    token_store: OAuthTokenStore | None = None,
    firestore_client: Any | None = None,
) -> GoogleCalendarOAuth | None:
    """Build private Calendar OAuth only when its complete config is present."""
    keys = (
        "STAYLONG_GOOGLE_OAUTH_CLIENT_ID",
        "STAYLONG_GOOGLE_OAUTH_CLIENT_SECRET",
        "STAYLONG_GOOGLE_OAUTH_REDIRECT_URI",
    )
    configured = [bool(environment.get(key, "").strip()) for key in keys]
    if not any(configured):
        return None
    if not all(configured):
        raise ValueError("Google Calendar OAuth client configuration is incomplete.")
    if token_store is None:
        from staylong.services.google_oauth import SecretManagerOAuthTokenStore

        token_store = SecretManagerOAuthTokenStore(project_id=environment["GOOGLE_CLOUD_PROJECT"])
    if firestore_client is None:
        from google.cloud import firestore

        firestore_client = firestore.Client(project=environment["GOOGLE_CLOUD_PROJECT"])
    return GoogleCalendarOAuth(
        client_id=environment[keys[0]],
        client_secret=environment[keys[1]],
        redirect_uri=environment[keys[2]],
        state_store=_new_oauth_state_store(firestore_client),
        token_store=token_store,
    )


def _new_oauth_state_store(client: Any) -> Any:
    from staylong.services.google_oauth import FirestoreOAuthStateStore

    return FirestoreOAuthStateStore(client=client)


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
    calendar_oauth = build_calendar_oauth(values, firestore_client=firestore_client)
    action_adapters = build_action_adapters(
        values,
        access_token_provider=(GoogleOAuthAccessTokenProvider(calendar_oauth)
                               if calendar_oauth is not None else None),
    )
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

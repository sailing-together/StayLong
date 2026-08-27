"""Limit and cleanup contracts for the anonymous StayLong public sandbox."""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from staylong.agents.intake import IntakeAgent
from staylong.api.app import PublicSandboxConfig, create_app
from staylong.services.channels import CalendarDemoAdapter
from staylong.services.events import InMemoryEventRepository
from staylong.services.public_sessions import (
    InMemoryPublicCaseAccessRepository,
    cleanup_expired_public_cases,
)
from staylong.services.taskmaster import InMemoryWorkflowRepository, TaskmasterWorkflow
from tests.api.test_taskmaster_api import StaticProvider

NOW = datetime(2025, 1, 1, 12, 0, tzinfo=UTC)
FUTURE = NOW + timedelta(hours=24)
PAST = NOW - timedelta(seconds=1)
HEADERS = {"Authorization": "Bearer private-token"}


def _public_client(max_cases: int = 2) -> TestClient:
    workflow = TaskmasterWorkflow(
        intake_agent=IntakeAgent(provider=StaticProvider()),
        repository=InMemoryWorkflowRepository(),
        event_repository=InMemoryEventRepository(),
        calendar=CalendarDemoAdapter(),
    )
    return TestClient(
        create_app(
            api_token="private-token",
            workflow=workflow,
            public_sandbox=PublicSandboxConfig(
                session_secret="test-secret",
                session_lifetime=timedelta(hours=24),
                case_access=InMemoryPublicCaseAccessRepository(),
                cookie_secure=False,
                max_cases_per_session=max_cases,
            ),
        )
    )


def test_public_session_cannot_create_more_than_the_configured_case_limit() -> None:
    client = _public_client(max_cases=2)
    for _ in range(2):
        response = client.post(
            "/v1/public/workflows",
            json={"concern": "Night bathroom access."},
        )
        assert response.status_code == 201
    response = client.post(
        "/v1/public/workflows",
        json={"concern": "Night bathroom access."},
    )
    assert response.status_code == 429


def test_cleanup_deletes_expired_access_and_workflow_records() -> None:
    workflow_repository = InMemoryWorkflowRepository()
    event_repository = InMemoryEventRepository()
    case_access = InMemoryPublicCaseAccessRepository()

    case_access.claim(
        case_id="expired-case",
        owner_key="owner-key",
        expires_at=PAST,
        created_at=PAST - timedelta(hours=24),
    )
    case_access.claim(
        case_id="active-case",
        owner_key="owner-key-2",
        expires_at=FUTURE,
        created_at=NOW,
    )

    deleted = cleanup_expired_public_cases(
        case_access=case_access,
        workflow_repository=workflow_repository,
        event_repository=event_repository,
        now=NOW,
    )

    assert deleted == ("expired-case",)
    # Active case is untouched
    case_access.assert_owner(case_id="active-case", owner_key="owner-key-2", now=NOW)


def test_cleanup_endpoint_requires_authentication() -> None:
    client = _public_client()
    assert client.post("/internal/public-sandbox/cleanup").status_code == 401


def test_cleanup_endpoint_returns_deleted_count() -> None:
    client = _public_client()
    response = client.post("/internal/public-sandbox/cleanup", headers=HEADERS)
    assert response.status_code == 200
    assert "deleted" in response.json()

"""Public API contracts for the anonymous StayLong sandbox."""

from datetime import timedelta

from fastapi.testclient import TestClient

from staylong.agents.intake import IntakeAgent
from staylong.api.app import create_app
from staylong.services.channels import CalendarDemoAdapter
from staylong.services.events import InMemoryEventRepository
from staylong.services.public_sessions import InMemoryPublicCaseAccessRepository
from staylong.services.taskmaster import InMemoryWorkflowRepository, TaskmasterWorkflow
from tests.api.test_taskmaster_api import ANSWERS, StaticProvider


def _public_client() -> TestClient:
    from staylong.api.app import PublicSandboxConfig

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
                session_secret="session-test-secret",
                session_lifetime=timedelta(hours=24),
                case_access=InMemoryPublicCaseAccessRepository(),
                cookie_secure=False,
            ),
        )
    )


def test_public_workflow_sets_an_httponly_session_cookie_and_needs_no_bearer_token() -> None:
    """A judge must be able to start the public sandbox without a shared secret."""
    response = _public_client().post(
        "/v1/public/workflows",
        json={"concern": "Bathroom access is difficult at night."},
    )

    assert response.status_code == 201
    assert "staylong_public_session" in response.headers["set-cookie"]
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "SameSite=lax" in response.headers["set-cookie"]
    assert response.json()["stage"] == "intake"


def test_second_public_session_cannot_read_or_mutate_the_first_sessions_case() -> None:
    """Changing the case ID in a public URL must not reveal another visitor's plan."""
    first_browser = _public_client()
    created = first_browser.post(
        "/v1/public/workflows",
        json={"concern": "Bathroom access is difficult at night."},
    )
    case_id = created.json()["case_id"]
    second_browser = TestClient(first_browser.app)

    assert second_browser.get(f"/v1/public/workflows/{case_id}").status_code == 404
    assert second_browser.post(
        f"/v1/public/workflows/{case_id}/answers",
        json={"answers": ANSWERS},
    ).status_code == 404

    prepared = first_browser.post(
        f"/v1/public/workflows/{case_id}/answers",
        json={"answers": ANSWERS},
    )
    assert prepared.status_code == 200
    assert prepared.json()["plan"]["title"] == "Your Home Independence Plan"


def test_private_workflow_route_still_requires_bearer_authentication() -> None:
    """Adding public routes must never make the existing private API public."""
    response = _public_client().post(
        "/v1/workflows",
        json={"concern": "Bathroom access is difficult at night."},
    )

    assert response.status_code == 401


def test_public_owner_can_approve_a_sandbox_action() -> None:
    """A session owner may explicitly approve its own sandbox-only next step."""
    browser = _public_client()
    created = browser.post(
        "/v1/public/workflows",
        json={"concern": "Bathroom access is difficult at night."},
    )
    case_id = created.json()["case_id"]
    browser.post(
        f"/v1/public/workflows/{case_id}/answers",
        json={"answers": ANSWERS},
    )

    approved = browser.post(
        f"/v1/public/workflows/{case_id}/action-decision",
        json={"action_type": "calendar.create", "action_revision": 1, "decision": "approve"},
    )

    assert approved.status_code == 200
    assert approved.json()["action_result"]["channel"] == "calendar"
    assert approved.json()["action_result"]["payload"]["sandbox"] == "true"

"""HTTP contract tests for the approval-gated Taskmaster workflow."""

from fastapi.testclient import TestClient

from staylong.agents.intake import IntakeAgent
from staylong.api.app import create_app
from staylong.services.channels import CalendarDemoAdapter
from staylong.services.events import InMemoryEventRepository

ANSWERS = {
    "assessment_status": "No assessment has been arranged yet.",
    "housing_tenure": "I own the home.",
    "support_contacts": "I am starting this myself.",
}
HEADERS = {"X-StayLong-API-Token": "secret-token"}


class StaticProvider:
    def generate_json(self, *, system_instruction: str, prompt: str) -> object:
        return {
            "plain_language_summary": "Getting to the bathroom at night is difficult.",
            "home_area": "bathroom",
            "reported_difficulty": "The hallway is dark and there are no rails near the toilet.",
            "missing_facts": [
                {
                    "key": "assessment_status",
                    "question": "Has a My Aged Care assessment been arranged?",
                    "reason": "This helps prepare the right next step.",
                },
                {
                    "key": "housing_tenure",
                    "question": "Is the home owned or rented?",
                    "reason": "Permission requirements may affect planning.",
                },
                {
                    "key": "support_contacts",
                    "question": "Would you like to involve anyone now?",
                    "reason": "StayLong only shares information when invited.",
                },
            ],
            "assessment_preparation_topics": ["Describe the night-time bathroom route."],
            "proposed_next_step": "prepare_assessment_pack",
        }


def _client() -> TestClient:
    from staylong.services.taskmaster import InMemoryWorkflowRepository, TaskmasterWorkflow

    workflow = TaskmasterWorkflow(
        intake_agent=IntakeAgent(provider=StaticProvider()),
        repository=InMemoryWorkflowRepository(),
        event_repository=InMemoryEventRepository(),
        calendar=CalendarDemoAdapter(),
    )
    return TestClient(create_app(api_token="secret-token", workflow=workflow))


def test_proxy_authenticated_user_can_prepare_and_approve_workflow() -> None:
    client = _client()

    created = client.post(
        "/v1/workflows",
        json={"concern": "The bathroom is difficult at night."},
        headers=HEADERS,
    )
    prepared = client.post(
        f"/v1/workflows/{created.json()['case_id']}/answers",
        json={"answers": ANSWERS},
        headers=HEADERS,
    )
    approved = client.post(
        f"/v1/workflows/{created.json()['case_id']}/action-decision",
        json={"action_type": "calendar.create", "action_revision": 1, "decision": "approve"},
        headers=HEADERS,
    )

    assert created.status_code == 201
    assert prepared.json()["stage"] == "awaiting_approval"
    assert prepared.json()["pack"]["official_pathways"] == ["https://www.myagedcare.gov.au/"]
    assert [task["title"] for task in prepared.json()["plan"]["tasks"]] == [
        "Arrange a My Aged Care assessment",
        "Prepare your assessment notes",
        "Confirm home access or permission",
    ]
    assert {action["action_type"] for action in prepared.json()["proposed_actions"]} == {
        "calendar.create",
        "contact_draft.create",
    }
    assert approved.status_code == 200
    assert approved.json()["action_result"]["channel"] == "calendar"
    assert approved.json()["action_result"]["payload"]["sandbox"] == "true"
    assert [result["action_type"] for result in approved.json()["action_results"]] == [
        "calendar.create"
    ]


def test_workflow_routes_require_authentication() -> None:
    response = _client().post("/v1/workflows", json={"concern": "A concern"})

    assert response.status_code == 401


def test_emergency_response_returns_no_normal_workflow_actions() -> None:
    response = _client().post(
        "/v1/workflows",
        json={"concern": "My parent is unconscious. Should I wait?"},
        headers=HEADERS,
    )

    assert response.status_code == 201
    assert response.json()["stage"] == "emergency"
    assert response.json()["pack"] is None
    assert response.json()["proposed_action"] is None
    assert response.json()["plan"] is None
    assert response.json()["proposed_actions"] == []


def test_stale_action_revision_returns_a_plain_language_conflict() -> None:
    client = _client()
    case_id = client.post(
        "/v1/workflows",
        json={"concern": "The bathroom is difficult at night."},
        headers=HEADERS,
    ).json()["case_id"]
    client.post(f"/v1/workflows/{case_id}/answers", json={"answers": ANSWERS}, headers=HEADERS)

    response = client.post(
        f"/v1/workflows/{case_id}/action-decision",
        json={"action_type": "calendar.create", "action_revision": 2, "decision": "approve"},
        headers=HEADERS,
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "This action has changed. Please review the current plan."


def test_declined_action_remains_visible_without_a_calendar_result() -> None:
    client = _client()
    case_id = client.post(
        "/v1/workflows",
        json={"concern": "The bathroom is difficult at night."},
        headers=HEADERS,
    ).json()["case_id"]
    client.post(f"/v1/workflows/{case_id}/answers", json={"answers": ANSWERS}, headers=HEADERS)

    response = client.post(
        f"/v1/workflows/{case_id}/action-decision",
        json={"action_type": "calendar.create", "action_revision": 1, "decision": "decline"},
        headers=HEADERS,
    )

    assert response.status_code == 200
    assert response.json()["stage"] == "awaiting_approval"
    assert response.json()["action_result"] is None
    assert response.json()["action_results"] == []


def test_duplicate_approval_returns_the_original_sandbox_action() -> None:
    client = _client()
    case_id = client.post(
        "/v1/workflows",
        json={"concern": "The bathroom is difficult at night."},
        headers=HEADERS,
    ).json()["case_id"]
    client.post(f"/v1/workflows/{case_id}/answers", json={"answers": ANSWERS}, headers=HEADERS)

    first = client.post(
        f"/v1/workflows/{case_id}/action-decision",
        json={"action_type": "calendar.create", "action_revision": 1, "decision": "approve"},
        headers=HEADERS,
    )
    duplicate = client.post(
        f"/v1/workflows/{case_id}/action-decision",
        json={"action_type": "calendar.create", "action_revision": 1, "decision": "approve"},
        headers=HEADERS,
    )

    assert duplicate.status_code == 200
    assert duplicate.json()["action_result"] == first.json()["action_result"]

"""Automated end-to-end journey test for the StayLong public demo."""

from __future__ import annotations

from datetime import timedelta

from fastapi.testclient import TestClient

from staylong.agents.intake import IntakeAgent
from staylong.api.app import PublicSandboxConfig, create_app
from staylong.services.channels import CalendarDemoAdapter, ContactDraftDemoAdapter
from staylong.services.events import InMemoryEventRepository
from staylong.services.public_sessions import InMemoryPublicCaseAccessRepository
from staylong.services.taskmaster import InMemoryWorkflowRepository, TaskmasterWorkflow
from tests.api.test_taskmaster_api import ANSWERS, StaticProvider


def _public_client() -> TestClient:
    workflow = TaskmasterWorkflow(
        intake_agent=IntakeAgent(provider=StaticProvider()),
        repository=InMemoryWorkflowRepository(),
        event_repository=InMemoryEventRepository(),
        calendar=CalendarDemoAdapter(),
        contact_drafts=ContactDraftDemoAdapter(),
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


def test_public_demo_journey_night_time_bathroom() -> None:
    """Exercise the complete public sandbox demo journey for the night-time bathroom scenario.

    Journey steps:
      1. Start a public workflow with the canonical night-time bathroom concern.
      2. Submit missing fact answers and confirm the Assessment Preparation Pack and Plan appear.
      3. Approve the calendar sandbox action and verify reminder & action result.
      4. Approve the contact draft sandbox action and verify draft-only delivery.
      5. Reload the workflow snapshot and verify durable state across all steps.
    """
    client = _public_client()

    # ── Step 1: Start public workflow (Concern Submission) ────────────────────
    concern = (
        "I'm finding it harder to reach the bathroom safely at night. "
        "The hallway is dark and there are no rails near the toilet."
    )
    start_resp = client.post("/v1/public/workflows", json={"concern": concern})
    assert start_resp.status_code == 201, (
        f"Workflow creation failed: status={start_resp.status_code}, body={start_resp.text}"
    )
    start_data = start_resp.json()
    case_id = start_data["case_id"]
    assert case_id, "Workflow creation did not return a valid case_id."
    assert start_data["stage"] == "intake", (
        f"Expected stage 'intake', got {start_data['stage']!r}"
    )
    assert "staylong_public_session" in start_resp.headers.get("set-cookie", ""), (
        "Expected staylong_public_session cookie in Set-Cookie header."
    )
    question_keys = [q["key"] for q in start_data["questions"]]
    assert question_keys == ["assessment_status", "housing_tenure", "support_contacts"], (
        f"Unexpected intake questions: {question_keys}"
    )

    # ── Step 2: Answer intake questions (Assessment Pack & Plan) ─────────────
    answers_resp = client.post(
        f"/v1/public/workflows/{case_id}/answers",
        json={"answers": ANSWERS},
    )
    assert answers_resp.status_code == 200, (
        f"Submitting answers failed: status={answers_resp.status_code}, body={answers_resp.text}"
    )
    answers_data = answers_resp.json()
    assert answers_data["stage"] == "awaiting_approval", (
        f"Expected stage 'awaiting_approval', got {answers_data['stage']!r}"
    )

    # Verify Assessment Preparation Pack
    pack = answers_data["pack"]
    assert pack is not None, "Assessment Preparation Pack must not be None."
    assert "https://www.myagedcare.gov.au/" in pack["official_pathways"], (
        f"Expected My Aged Care pathway in pack, got: {pack['official_pathways']}"
    )

    # Verify Home Independence Plan
    plan = answers_data["plan"]
    assert plan is not None, "Home Independence Plan must not be None."
    assert plan["title"] == "Your Home Independence Plan", (
        f"Unexpected plan title: {plan['title']!r}"
    )
    task_titles = [task["title"] for task in plan["tasks"]]
    assert task_titles == [
        "Prepare to arrange a My Aged Care assessment",
        "Prepare your assessment notes",
        "Confirm home access or permission",
    ], f"Unexpected plan tasks: {task_titles}"

    # Verify Proposed Actions (both calendar and contact_draft ready for consent)
    proposed_types = {action["action_type"] for action in answers_data["proposed_actions"]}
    assert proposed_types == {"calendar.create", "contact_draft.create"}, (
        f"Unexpected proposed action types: {proposed_types}"
    )

    # ── Step 3: Approve Calendar Sandbox Action ──────────────────────────────
    cal_action = next(
        a for a in answers_data["proposed_actions"] if a["action_type"] == "calendar.create"
    )
    cal_approval_resp = client.post(
        f"/v1/public/workflows/{case_id}/action-decision",
        json={
            "action_type": cal_action["action_type"],
            "action_revision": cal_action["revision"],
            "decision": "approve",
        },
    )
    assert cal_approval_resp.status_code == 200, (
        f"Calendar action approval failed: status={cal_approval_resp.status_code}, "
        f"body={cal_approval_resp.text}"
    )
    cal_data = cal_approval_resp.json()
    assert cal_data["stage"] == "follow_through", (
        f"Expected stage 'follow_through', got {cal_data['stage']!r}"
    )
    cal_result = cal_data["action_result"]
    assert cal_result is not None, "Calendar action result must be present."
    assert cal_result["channel"] == "calendar", (
        f"Expected channel 'calendar', got {cal_result['channel']!r}"
    )
    assert cal_result["payload"].get("sandbox") == "true", (
        f"Expected sandbox marker in calendar action payload, got: {cal_result['payload']}"
    )
    assert cal_data["reminder"] is not None, (
        "A scheduled reminder must be present after calendar approval."
    )

    # ── Step 4: Approve Contact Draft Sandbox Action ─────────────────────────
    draft_action = next(
        a for a in answers_data["proposed_actions"] if a["action_type"] == "contact_draft.create"
    )
    draft_approval_resp = client.post(
        f"/v1/public/workflows/{case_id}/action-decision",
        json={
            "action_type": draft_action["action_type"],
            "action_revision": draft_action["revision"],
            "decision": "approve",
        },
    )
    assert draft_approval_resp.status_code == 200, (
        f"Contact draft approval failed: status={draft_approval_resp.status_code}, "
        f"body={draft_approval_resp.text}"
    )
    draft_data = draft_approval_resp.json()
    draft_result = draft_data["action_result"]
    assert draft_result is not None, "Contact draft action result must be present."
    assert draft_result["channel"] == "contact_draft", (
        f"Expected channel 'contact_draft', got {draft_result['channel']!r}"
    )
    assert draft_result["payload"].get("delivery") == "draft_only", (
        f"Expected draft_only delivery, got: {draft_result['payload']}"
    )
    assert draft_result["payload"].get("sandbox") == "true", (
        f"Expected sandbox marker in contact draft payload, got: {draft_result['payload']}"
    )

    # ── Step 5: Reload Workflow Snapshot (Durability & State Verification) ────
    reload_resp = client.get(f"/v1/public/workflows/{case_id}")
    assert reload_resp.status_code == 200, (
        f"Reloading workflow failed: status={reload_resp.status_code}, body={reload_resp.text}"
    )
    reloaded_data = reload_resp.json()
    assert reloaded_data["stage"] == "follow_through", (
        f"Expected reloaded stage 'follow_through', got {reloaded_data['stage']!r}"
    )
    assert reloaded_data["integration_mode"] == "sandbox", (
        f"Expected integration_mode 'sandbox', got {reloaded_data['integration_mode']!r}"
    )

    # Check both action results are durably persisted
    result_channels = [res["channel"] for res in reloaded_data["action_results"]]
    assert result_channels == ["calendar", "contact_draft"], (
        f"Expected action results for calendar and contact_draft, got: {result_channels}"
    )

    # Check plan, pack, and timeline durability
    assert reloaded_data["plan"] is not None, "Reloaded plan must not be None."
    assert reloaded_data["plan"]["title"] == "Your Home Independence Plan"
    assert len(reloaded_data["plan"]["tasks"]) == 3
    assert reloaded_data["pack"] is not None
    assert len(reloaded_data["timeline"]) > 0, "Timeline events must be recorded."

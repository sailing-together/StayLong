"""Validation tests for concrete assessment-pack actions, handover value, and next steps."""

from datetime import UTC, datetime

import pytest

from staylong.agents.intake import IntakeAgent
from staylong.services.channels import CalendarDemoAdapter, ContactDraftDemoAdapter
from staylong.services.events import InMemoryEventRepository
from staylong.services.taskmaster import (
    InMemoryWorkflowRepository,
    TaskmasterWorkflow,
    WorkflowSnapshot,
    WorkflowStage,
)

NOW = datetime(2026, 8, 23, 10, tzinfo=UTC)

ANSWERS = {
    "assessment_status": "No assessment has been arranged yet.",
    "housing_tenure": "I own the home.",
    "support_contacts": "I am starting this myself.",
}

CONCERN_SCENARIOS = [
    {
        "id": "night_time_bathroom",
        "concern": (
            "I’m finding it harder to reach the bathroom safely at night. "
            "The hallway is dark and there are no rails near the toilet."
        ),
        "llm_output": {
            "plain_language_summary": "Getting to the bathroom safely at night is difficult.",
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
            "assessment_preparation_topics": [
                "Describe the night-time bathroom route and where light is needed.",
                "Note where handrails or support would be helpful near the toilet.",
            ],
            "proposed_next_step": "prepare_assessment_pack",
        },
        "expected_goal": "Prepare for a safer night-time bathroom routine.",
        "expected_task_keyword": "bathroom",
        "expected_cal_title": "Review your night-time bathroom preparation pack",
        "expected_draft_title": "Review your night-time bathroom contact draft",
    },
    {
        "id": "front_steps",
        "concern": "The steps at my front door are becoming difficult.",
        "llm_output": {
            "plain_language_summary": "Managing the steps at the front door is difficult.",
            "home_area": "entry",
            "reported_difficulty": "The steps at my front door are becoming difficult.",
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
            "assessment_preparation_topics": [
                "Describe the front steps, handrail presence, and surface condition.",
                "Note times of day or weather that make the front entry harder.",
            ],
            "proposed_next_step": "prepare_assessment_pack",
        },
        "expected_goal": "Prepare for safer access at the front entry and steps.",
        "expected_task_keyword": "steps",
        "expected_cal_title": "Review your front steps and entry preparation pack",
        "expected_draft_title": "Review your front steps and entry contact draft",
    },
    {
        "id": "shower_safety",
        "concern": "I feel unsteady getting into and out of the shower.",
        "llm_output": {
            "plain_language_summary": "Feeling unsteady getting into and out of the shower.",
            "home_area": "bathroom",
            "reported_difficulty": "I feel unsteady getting into and out of the shower.",
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
            "assessment_preparation_topics": [
                "Describe the shower hob/entry, grab rails, and non-slip surfaces.",
                "Note whether a shower chair or bench would assist stability.",
            ],
            "proposed_next_step": "prepare_assessment_pack",
        },
        "expected_goal": "Prepare for a safer shower and bathroom routine.",
        "expected_task_keyword": "shower",
        "expected_cal_title": "Review your shower safety preparation pack",
        "expected_draft_title": "Review your shower safety contact draft",
    },
    {
        "id": "free_text_kitchen",
        "concern": (
            "I have trouble reaching high cupboards in the kitchen "
            "and carrying heavy pots."
        ),
        "llm_output": {
            "plain_language_summary": (
                "Reaching high kitchen cupboards and carrying heavy cookware is difficult."
            ),
            "home_area": "kitchen",
            "reported_difficulty": (
                "Reaching high cupboards and carrying heavy cookware in the kitchen."
            ),
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
            "assessment_preparation_topics": [
                "Describe kitchen layout, cupboard heights, and heavy item storage.",
                "Note daily meal preparation tasks where support or adaptive tools could help.",
            ],
            "proposed_next_step": "prepare_assessment_pack",
        },
        "expected_goal": "Prepare for safer meal preparation and kitchen routines.",
        "expected_task_keyword": "kitchen",
        "expected_cal_title": "Review your kitchen safety preparation pack",
        "expected_draft_title": "Review your kitchen safety contact draft",
    },
]


class ScenarioProvider:
    def __init__(self, response_data: dict) -> None:
        self._data = response_data

    def generate_json(self, *, system_instruction: str, prompt: str) -> object:
        return self._data


def _build_prepared_workflow(scenario: dict) -> tuple[TaskmasterWorkflow, WorkflowSnapshot]:
    provider = ScenarioProvider(scenario["llm_output"])
    workflow = TaskmasterWorkflow(
        intake_agent=IntakeAgent(provider=provider),
        repository=InMemoryWorkflowRepository(),
        event_repository=InMemoryEventRepository(),
        calendar=CalendarDemoAdapter(),
        contact_drafts=ContactDraftDemoAdapter(),
    )
    started = workflow.start(concern=scenario["concern"], now=NOW)
    prepared = workflow.answer_intake(case_id=started.case_id, answers=ANSWERS, now=NOW)
    return workflow, prepared


@pytest.mark.parametrize("scenario", CONCERN_SCENARIOS, ids=lambda s: s["id"])
def test_each_concern_produces_concrete_low_risk_actions(scenario: dict) -> None:
    """Verify that every concern produces specific, actionable tasks rather than generic text."""
    _, prepared = _build_prepared_workflow(scenario)

    assert prepared.plan is not None
    assert prepared.plan.goal == scenario["expected_goal"]
    assert len(prepared.plan.tasks) == 3

    # Task 2 (note-taking) must contain practical, concern-tailored guidance
    notes_task = prepared.plan.tasks[1]
    assert notes_task.title == "Prepare your assessment notes"
    assert scenario["expected_task_keyword"] in notes_task.description.lower()
    assert "what would help" in notes_task.description.lower()
    assert notes_task.owner == "You"
    assert notes_task.status == "ready"


@pytest.mark.parametrize("scenario", CONCERN_SCENARIOS, ids=lambda s: s["id"])
def test_each_concern_produces_useful_assessment_handover_details(scenario: dict) -> None:
    """Verify assessment pack contains actionable discussion topics for a professional assessor."""
    _, prepared = _build_prepared_workflow(scenario)

    assert prepared.pack is not None
    assert len(prepared.pack.assessment_discussion_topics) >= 1
    for topic in prepared.pack.assessment_discussion_topics:
        assert isinstance(topic, str) and len(topic.strip()) > 10
        # Topics must focus on describing facts, environment, and needs
        assert any(
            verb in topic.lower() for verb in ("describe", "note", "check", "bring", "list")
        )


@pytest.mark.parametrize("scenario", CONCERN_SCENARIOS, ids=lambda s: s["id"])
def test_each_concern_links_official_my_aged_care_guidance(scenario: dict) -> None:
    """Verify official My Aged Care pathways are linked across both the pack and the plan."""
    _, prepared = _build_prepared_workflow(scenario)

    assert prepared.pack is not None
    assert prepared.pack.official_pathways == ("https://www.myagedcare.gov.au/",)

    assert prepared.plan is not None
    assert prepared.plan.official_pathway == "https://www.myagedcare.gov.au/"
    assert prepared.plan.tasks[0].title == "Prepare to arrange a My Aged Care assessment"


@pytest.mark.parametrize("scenario", CONCERN_SCENARIOS, ids=lambda s: s["id"])
def test_each_concern_produces_clear_next_steps_and_tailored_proposals(scenario: dict) -> None:
    """Verify clear next steps and approval-gated proposed action items tailored to the concern."""
    _, prepared = _build_prepared_workflow(scenario)

    assert prepared.pack is not None
    assert prepared.pack.proposed_next_step == "prepare_assessment_pack"

    assert len(prepared.proposed_actions) == 2
    cal_action = next(a for a in prepared.proposed_actions if a.action_type == "calendar.create")
    draft_action = next(
        a for a in prepared.proposed_actions if a.action_type == "contact_draft.create"
    )

    assert cal_action.title == scenario["expected_cal_title"]
    assert draft_action.title == scenario["expected_draft_title"]
    assert cal_action.revision == 1
    assert draft_action.revision == 1


@pytest.mark.parametrize("scenario", CONCERN_SCENARIOS, ids=lambda s: s["id"])
def test_approval_and_completion_states_explain_action_and_next_steps(scenario: dict) -> None:
    """Verify approval transitions stage to follow_through with clear results and audit trail."""
    workflow, prepared = _build_prepared_workflow(scenario)

    completed = workflow.decide_action(
        case_id=prepared.case_id,
        action_type="calendar.create",
        action_revision=1,
        approve=True,
        now=NOW,
    )

    assert completed.stage is WorkflowStage.FOLLOW_THROUGH
    assert completed.action_result is not None
    assert completed.action_result.action_type == "calendar.create"
    assert completed.action_result.channel == "calendar"
    assert completed.reminder is not None

    # Full audit record generated for handover verification
    event_types = [e.event_type for e in completed.timeline]
    assert event_types == [
        "concern.created",
        "assessment.pack.prepared",
        "approval.granted",
        "calendar.action.recorded",
        "reminder.scheduled",
    ]

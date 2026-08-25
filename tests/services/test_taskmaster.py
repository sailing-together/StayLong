"""Behaviour-first tests for the consent-governed StayLong Taskmaster flow."""

from datetime import UTC, datetime

import pytest

from staylong.agents.intake import IntakeAgent
from staylong.services.channels import CalendarDemoAdapter
from staylong.services.events import InMemoryEventRepository
from staylong.services.reminders import ReminderStatus

NOW = datetime(2026, 8, 23, 10, tzinfo=UTC)
ANSWERS = {
    "assessment_status": "No assessment has been arranged yet.",
    "housing_tenure": "I own the home.",
    "support_contacts": "I am starting this myself.",
}


class StaticProvider:
    """A deterministic intake boundary so the workflow tests need no cloud model."""

    def __init__(self) -> None:
        self.requests: list[str] = []

    def generate_json(self, *, system_instruction: str, prompt: str) -> object:
        self.requests.append(prompt)
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
            "assessment_preparation_topics": [
                "Describe the night-time bathroom route.",
                "Bring any existing aged-care correspondence.",
            ],
            "proposed_next_step": "prepare_assessment_pack",
        }


def _workflow() -> object:
    from staylong.services.taskmaster import InMemoryWorkflowRepository, TaskmasterWorkflow

    return TaskmasterWorkflow(
        intake_agent=IntakeAgent(provider=StaticProvider()),
        repository=InMemoryWorkflowRepository(),
        event_repository=InMemoryEventRepository(),
        calendar=CalendarDemoAdapter(),
    )


def _prepared_workflow() -> tuple[object, object]:
    workflow = _workflow()
    started = workflow.start(
        concern="The bathroom is difficult at night.",
        now=NOW,
    )
    return workflow, workflow.answer_intake(case_id=started.case_id, answers=ANSWERS, now=NOW)


def test_normal_concern_prepares_pack_and_exact_calendar_draft() -> None:
    from staylong.services.taskmaster import WorkflowStage

    _, prepared = _prepared_workflow()

    assert prepared.stage is WorkflowStage.AWAITING_APPROVAL
    assert prepared.pack is not None
    assert prepared.pack.official_pathways == ("https://www.myagedcare.gov.au/",)
    assert prepared.proposed_action is not None
    assert prepared.proposed_action.action_type == "calendar.create"
    assert prepared.proposed_action.revision == 1
    assert tuple(event.event_type for event in prepared.timeline) == (
        "concern.created",
        "assessment.pack.prepared",
    )


def test_answered_intake_builds_three_actionable_home_plan_tasks() -> None:
    _, prepared = _prepared_workflow()

    assert prepared.plan is not None
    assert prepared.plan.title == "Your Home Independence Plan"
    assert [task.title for task in prepared.plan.tasks] == [
        "Arrange a My Aged Care assessment",
        "Prepare your assessment notes",
        "Confirm home access or permission",
    ]
    assert [task.owner for task in prepared.plan.tasks] == [
        "You",
        "You",
        "You",
    ]
    assert {task.status for task in prepared.plan.tasks} == {"ready"}


def test_approving_calendar_does_not_create_contact_draft() -> None:
    workflow, prepared = _prepared_workflow()

    completed = workflow.decide_action(
        case_id=prepared.case_id,
        action_type="calendar.create",
        action_revision=1,
        approve=True,
        now=NOW,
    )

    assert [action.action_type for action in completed.proposed_actions] == [
        "calendar.create",
        "contact_draft.create",
    ]
    assert [result.action_type for result in completed.action_results] == ["calendar.create"]
    assert len(workflow.calendar.sent_items) == 1
    assert workflow.contact_drafts.sent_items == ()


def test_contact_draft_requires_its_own_approval() -> None:
    workflow, prepared = _prepared_workflow()

    completed = workflow.decide_action(
        case_id=prepared.case_id,
        action_type="contact_draft.create",
        action_revision=1,
        approve=True,
        now=NOW,
    )

    assert [result.action_type for result in completed.action_results] == ["contact_draft.create"]
    assert workflow.calendar.sent_items == ()
    assert len(workflow.contact_drafts.sent_items) == 1


def test_unanswered_required_fact_keeps_workflow_in_intake() -> None:
    from staylong.services.taskmaster import WorkflowStage

    workflow = _workflow()
    started = workflow.start(concern="The bathroom is difficult at night.", now=NOW)
    snapshot = workflow.answer_intake(
        case_id=started.case_id,
        answers={"assessment_status": ANSWERS["assessment_status"]},
        now=NOW,
    )

    assert snapshot.stage is WorkflowStage.INTAKE
    assert tuple(question.key for question in snapshot.questions) == (
        "housing_tenure",
        "support_contacts",
    )
    assert snapshot.pack is None


def test_emergency_route_does_not_create_a_home_plan() -> None:
    workflow = _workflow()

    snapshot = workflow.start(concern="My parent is unconscious. Should I wait?", now=NOW)

    assert snapshot.plan is None


def test_emergency_concern_bypasses_intake_provider_and_normal_actions() -> None:
    from staylong.services.taskmaster import WorkflowStage

    provider = StaticProvider()
    from staylong.services.taskmaster import InMemoryWorkflowRepository, TaskmasterWorkflow

    workflow = TaskmasterWorkflow(
        intake_agent=IntakeAgent(provider=provider),
        repository=InMemoryWorkflowRepository(),
        event_repository=InMemoryEventRepository(),
        calendar=CalendarDemoAdapter(),
    )

    snapshot = workflow.start(concern="My parent is unconscious. Should I wait?", now=NOW)

    assert snapshot.stage is WorkflowStage.EMERGENCY
    assert snapshot.pack is None
    assert snapshot.proposed_action is None
    assert provider.requests == []


def test_declining_calendar_keeps_the_contact_draft_available() -> None:
    from staylong.services.taskmaster import WorkflowStage

    workflow, prepared = _prepared_workflow()
    declined = workflow.decide_action(
        case_id=prepared.case_id,
        action_revision=1,
        approve=False,
        now=NOW,
    )

    assert declined.stage is WorkflowStage.AWAITING_APPROVAL
    assert declined.action_result is None
    assert declined.action_results == ()
    assert [action.action_type for action in declined.proposed_actions] == [
        "calendar.create",
        "contact_draft.create",
    ]
    assert tuple(event.event_type for event in declined.timeline) == (
        "concern.created",
        "assessment.pack.prepared",
        "approval.declined",
    )


def test_duplicate_approval_returns_one_recorded_calendar_action() -> None:
    from staylong.services.taskmaster import WorkflowStage

    workflow, prepared = _prepared_workflow()
    first = workflow.decide_action(
        case_id=prepared.case_id,
        action_revision=1,
        approve=True,
        now=NOW,
    )
    duplicate = workflow.decide_action(
        case_id=prepared.case_id,
        action_revision=1,
        approve=True,
        now=NOW,
    )

    assert first.stage is WorkflowStage.FOLLOW_THROUGH
    assert duplicate.action_result == first.action_result
    assert len(workflow.calendar.sent_items) == 1
    assert tuple(event.event_type for event in duplicate.timeline) == (
        "concern.created",
        "assessment.pack.prepared",
        "approval.granted",
        "calendar.action.recorded",
        "reminder.scheduled",
    )


def test_repository_reload_returns_the_same_timeline() -> None:
    workflow, prepared = _prepared_workflow()
    completed = workflow.decide_action(
        case_id=prepared.case_id,
        action_revision=1,
        approve=True,
        now=NOW,
    )

    reloaded = workflow.get(case_id=completed.case_id)

    assert reloaded == completed


def test_firestore_repository_round_trips_the_completed_workflow() -> None:
    from staylong.services.taskmaster import FirestoreWorkflowRepository, TaskmasterWorkflow
    from tests.services.fake_firestore import FakeFirestoreClient

    workflow = TaskmasterWorkflow(
        intake_agent=IntakeAgent(provider=StaticProvider()),
        repository=FirestoreWorkflowRepository(client=FakeFirestoreClient()),
        event_repository=InMemoryEventRepository(),
        calendar=CalendarDemoAdapter(),
    )
    started = workflow.start(concern="The bathroom is difficult at night.", now=NOW)
    prepared = workflow.answer_intake(case_id=started.case_id, answers=ANSWERS, now=NOW)
    completed = workflow.decide_action(
        case_id=prepared.case_id,
        action_revision=1,
        approve=True,
        now=NOW,
    )

    reloaded = workflow.get(case_id=completed.case_id)

    assert reloaded == completed


def test_due_sandbox_reminder_becomes_sent() -> None:
    workflow, prepared = _prepared_workflow()
    approved = workflow.decide_action(
        case_id=prepared.case_id,
        action_revision=1,
        approve=True,
        now=NOW,
    )

    followed_up = workflow.run_demo_follow_up(case_id=approved.case_id, now=NOW)

    assert followed_up.reminder is not None
    assert followed_up.reminder.status is ReminderStatus.SENT
    assert followed_up.timeline[-1].event_type == "reminder.sent"


def test_stale_action_revision_is_rejected() -> None:
    workflow, prepared = _prepared_workflow()

    with pytest.raises(ValueError, match="revision"):
        workflow.decide_action(
            case_id=prepared.case_id,
            action_revision=2,
            approve=True,
            now=NOW,
        )

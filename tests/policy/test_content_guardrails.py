"""Guardrail regression tests ensuring plans never imply diagnosis or unapproved actions."""

from datetime import UTC, datetime

import pytest

from staylong.agents.intake import IntakeAgent
from staylong.services.channels import CalendarDemoAdapter, ContactDraftDemoAdapter
from staylong.services.events import InMemoryEventRepository
from staylong.services.taskmaster import (
    InMemoryWorkflowRepository,
    TaskmasterWorkflow,
)
from tests.services.test_concern_content_validation import (
    ANSWERS,
    CONCERN_SCENARIOS,
    ScenarioProvider,
)

NOW = datetime(2026, 8, 23, 10, tzinfo=UTC)

# Prohibited clinical and unapproved side-effect terms
PROHIBITED_TERMS = [
    "diagnos",
    "prescri",
    "eligible for funding",
    "guaranteed funding",
    "eligibility decision",
    "select a provider",
    "we have chosen a provider",
    "we booked",
    "we have contacted",
    "we called",
    "payment required",
    "fee schedule",
]


@pytest.mark.parametrize("scenario", CONCERN_SCENARIOS, ids=lambda s: s["id"])
def test_generated_content_satisfies_non_clinical_guardrails(scenario: dict) -> None:
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

    # 1. Boundary notes must explicitly state non-clinical and non-decision boundaries
    assert prepared.pack is not None
    assert "does not" in prepared.pack.boundary_note.lower()
    assert "diagnose" in prepared.pack.boundary_note.lower()
    assert "eligibility" in prepared.pack.boundary_note.lower()
    assert "choose providers" in prepared.pack.boundary_note.lower()

    # 2. Actionable contents must never imply clinical diagnosis or unapproved actions
    actionable_texts_to_check: list[str] = [
        prepared.pack.concern_summary,
        prepared.pack.reported_difficulty,
        prepared.plan.goal if prepared.plan else "",
        prepared.plan.title if prepared.plan else "",
    ]

    if prepared.pack:
        actionable_texts_to_check.extend(prepared.pack.assessment_discussion_topics)

    if prepared.plan:
        for task in prepared.plan.tasks:
            actionable_texts_to_check.append(task.title)
            actionable_texts_to_check.append(task.description)

    for action in prepared.proposed_actions:
        actionable_texts_to_check.append(action.title)

    completed = workflow.decide_action(
        case_id=prepared.case_id,
        action_type="calendar.create",
        action_revision=1,
        approve=True,
        now=NOW,
    )
    if completed.reminder:
        actionable_texts_to_check.append(completed.reminder.action)

    for text in actionable_texts_to_check:
        lower_text = text.lower()
        for prohibited in PROHIBITED_TERMS:
            assert prohibited not in lower_text, (
                f"Prohibited term '{prohibited}' found in generated text: '{text}'"
            )

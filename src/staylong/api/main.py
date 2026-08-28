"""Cloud Run runtime entry point for the StayLong API."""

import os

from staylong.agents.intake import IntakeAgent
from staylong.api.app import create_app
from staylong.api.runtime import build_calendar_oauth, build_runtime_workflow
from staylong.api.runtime_token import runtime_token
from staylong.services.channels import CalendarDemoAdapter
from staylong.services.events import InMemoryEventRepository
from staylong.services.taskmaster import InMemoryWorkflowRepository, TaskmasterWorkflow


class _LocalDemoProvider:
    """Deterministic, non-clinical fixture used only by the local dev command."""

    def generate_json(self, *, system_instruction: str, prompt: str) -> object:
        del system_instruction, prompt
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


def _local_demo_workflow() -> TaskmasterWorkflow:
    """Build an isolated in-memory workflow; never used by Cloud Run."""
    return TaskmasterWorkflow(
        intake_agent=IntakeAgent(provider=_LocalDemoProvider()),
        repository=InMemoryWorkflowRepository(),
        event_repository=InMemoryEventRepository(),
        calendar=CalendarDemoAdapter(),
    )


def _runtime_components() -> tuple[TaskmasterWorkflow, object | None]:
    if os.environ.get("STAYLONG_LOCAL_DEMO", "").casefold() == "true":
        return _local_demo_workflow(), None
    workflow = build_runtime_workflow()
    return workflow, build_calendar_oauth(dict(os.environ))


_workflow, _calendar_oauth = _runtime_components()
app = create_app(
    api_token=runtime_token(os.environ), workflow=_workflow, calendar_oauth=_calendar_oauth
)

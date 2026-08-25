"""Typed, non-clinical plans that turn an intake pack into useful next steps."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal

from staylong.agents.intake import AssessmentPreparationPack

PlanTaskStatus = Literal["ready", "blocked", "completed"]


@dataclass(frozen=True, slots=True)
class PlanTask:
    """One plain-language task owned by the person using StayLong."""

    task_id: str
    title: str
    description: str
    owner: str
    due_at: datetime
    status: PlanTaskStatus
    blocker: str | None = None


@dataclass(frozen=True, slots=True)
class HomeIndependencePlan:
    """A durable, reviewable preparation plan without clinical recommendations."""

    title: str
    stated_difficulty: str
    goal: str
    official_pathway: str
    tasks: tuple[PlanTask, ...]


def build_home_independence_plan(
    pack: AssessmentPreparationPack, *, now: datetime
) -> HomeIndependencePlan:
    """Create the small, useful first plan from a validated intake pack."""
    return HomeIndependencePlan(
        title="Your Home Independence Plan",
        stated_difficulty=pack.reported_difficulty,
        goal="Prepare for the next appropriate home-support assessment step.",
        official_pathway=pack.official_pathways[0],
        tasks=(
            PlanTask(
                task_id="arrange-assessment",
                title="Arrange a My Aged Care assessment",
                description=(
                    "Use the official pathway when you are ready to discuss support at home."
                ),
                owner="You",
                due_at=now + timedelta(days=2),
                status="ready",
            ),
            PlanTask(
                task_id="prepare-notes",
                title="Prepare your assessment notes",
                description=(
                    "Write down the difficulty, what happens at night, and what would help."
                ),
                owner="You",
                due_at=now + timedelta(days=1),
                status="ready",
            ),
            PlanTask(
                task_id="confirm-home-access",
                title="Confirm home access or permission",
                description=(
                    "Check any access, tenancy, or permission details needed before changes."
                ),
                owner="You",
                due_at=now + timedelta(days=3),
                status="ready",
            ),
        ),
    )

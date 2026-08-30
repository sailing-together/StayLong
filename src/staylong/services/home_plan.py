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


def _plan_goal(pack: AssessmentPreparationPack) -> str:
    """Create a practical, non-clinical goal tailored to the concern."""
    area = getattr(pack, "home_area", "other")
    difficulty = pack.reported_difficulty.lower()

    if area == "bathroom":
        if "shower" in difficulty:
            return "Prepare for a safer shower and bathroom routine."
        return "Prepare for a safer night-time bathroom routine."
    if area == "entry":
        return "Prepare for safer access at the front entry and steps."
    if area == "bedroom":
        return "Prepare for safer movement around the bedroom."
    if area == "kitchen":
        return "Prepare for safer meal preparation and kitchen routines."
    if "shower" in difficulty:
        return "Prepare for a safer shower and bathroom routine."
    if any(k in difficulty for k in ("step", "stair", "door", "entry")):
        return "Prepare for safer access at the front entry and steps."
    if any(k in difficulty for k in ("bathroom", "toilet", "night")):
        return "Prepare for a safer night-time bathroom routine."
    return "Prepare for the next appropriate home-support assessment step."


def _prepare_notes_description(pack: AssessmentPreparationPack) -> str:
    """Build practical note-taking guidance tailored to the reported difficulty."""
    area = getattr(pack, "home_area", "other")
    difficulty = pack.reported_difficulty.lower()

    if area == "bathroom":
        if "shower" in difficulty:
            return (
                "Write down what happens getting into and out of the shower, "
                "when you feel unsteady, and what would help."
            )
        return (
            "Write down what happens reaching the bathroom at night, "
            "lighting along the way, and what would help."
        )
    if area == "entry":
        return (
            "Write down what happens using the front steps or entry, "
            "any difficulty with balance or rails, and what would help."
        )
    if area == "bedroom":
        return (
            "Write down what happens getting in and out of bed, "
            "lighting around the room, and what would help."
        )
    if area == "kitchen":
        return (
            "Write down what happens preparing meals or reaching items in the kitchen, "
            "and what would help."
        )
    if "shower" in difficulty:
        return (
            "Write down what happens getting into and out of the shower, "
            "when you feel unsteady, and what would help."
        )
    if any(k in difficulty for k in ("step", "stair", "door", "entry")):
        return (
            "Write down what happens using the front steps or entry, "
            "any difficulty with balance or rails, and what would help."
        )
    if any(k in difficulty for k in ("bathroom", "toilet", "night")):
        return (
            "Write down what happens reaching the bathroom at night, "
            "lighting along the way, and what would help."
        )
    return (
        f"Write down practical details about {pack.reported_difficulty.rstrip('.')}, "
        "when it happens, and what would help."
    )


def build_home_independence_plan(
    pack: AssessmentPreparationPack, *, now: datetime
) -> HomeIndependencePlan:
    """Create the small, useful first plan from a validated intake pack."""
    return HomeIndependencePlan(
        title="Your Home Independence Plan",
        stated_difficulty=pack.reported_difficulty,
        goal=_plan_goal(pack),
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
                description=_prepare_notes_description(pack),
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

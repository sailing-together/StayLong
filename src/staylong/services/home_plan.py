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


def _plan_task1_description(pack: AssessmentPreparationPack) -> str:
    """Build practical, non-clinical My Aged Care task description tailored to the concern."""
    area = getattr(pack, "home_area", "other")
    difficulty = pack.reported_difficulty.lower()

    if area == "bathroom":
        if "shower" in difficulty:
            return (
                "Use the official pathway when you are ready to discuss bathroom and "
                "shower safety support at home."
            )
        return (
            "Use the official pathway when you are ready to discuss night-time "
            "bathroom safety support at home."
        )
    if area == "entry":
        return (
            "Use the official pathway when you are ready to discuss front step and "
            "entry access support at home."
        )
    if area == "bedroom":
        return (
            "Use the official pathway when you are ready to discuss bedroom movement "
            "and safety support at home."
        )
    if area == "kitchen":
        return (
            "Use the official pathway when you are ready to discuss kitchen safety "
            "and meal preparation support at home."
        )
    if "shower" in difficulty:
        return (
            "Use the official pathway when you are ready to discuss bathroom and "
            "shower safety support at home."
        )
    if any(k in difficulty for k in ("step", "stair", "door", "entry")):
        return (
            "Use the official pathway when you are ready to discuss front step and "
            "entry access support at home."
        )
    if any(k in difficulty for k in ("bathroom", "toilet", "night")):
        return (
            "Use the official pathway when you are ready to discuss night-time "
            "bathroom safety support at home."
        )
    return "Use the official pathway when you are ready to discuss support at home."


def _plan_task3_description(
    pack: AssessmentPreparationPack, answers: dict[str, str] | None = None
) -> str:
    """Build practical permission/access guidance tailored to housing tenure and concern."""
    del pack
    if answers:
        tenure = answers.get("housing_tenure", "").lower()
        if any(k in tenure for k in ("rent", "tenant", "lease", "landlord")):
            return (
                "Confirm whether landlord or property manager permission is needed "
                "before any home changes."
            )
        if any(k in tenure for k in ("own", "owner", "mortgage", "freehold")):
            return (
                "Confirm access requirements and family or tradesperson permissions for your home."
            )
    return (
        "Check whether a landlord, building manager, or trusted supporter "
        "needs to be involved before any home change is discussed."
    )


def build_home_independence_plan(
    pack: AssessmentPreparationPack,
    *,
    now: datetime,
    answers: dict[str, str] | None = None,
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
                title="Prepare to arrange a My Aged Care assessment",
                description=_plan_task1_description(pack),
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
                description=_plan_task3_description(pack, answers),
                owner="You",
                due_at=now + timedelta(days=3),
                status="ready",
            ),
        ),
    )


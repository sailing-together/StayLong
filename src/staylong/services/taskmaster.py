"""Consent-governed orchestration for StayLong's single Taskmaster workflow."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any, Protocol
from uuid import uuid4

from staylong.agents.intake import (
    AssessmentPreparationPack,
    EmergencyRouteRequired,
    IntakeAgent,
    MissingFact,
)
from staylong.domain.models import ActionApproval, TimelineEvent
from staylong.services.channels import CalendarDemoAdapter, CalendarDetails, DemoDispatchResult
from staylong.services.events import EventRepository
from staylong.services.reminders import Reminder, ReminderService, ReminderStatus


class WorkflowStage(StrEnum):
    """Public, human-reviewable states for one household concern."""

    INTAKE = "intake"
    EMERGENCY = "emergency"
    AWAITING_APPROVAL = "awaiting_approval"
    FOLLOW_THROUGH = "follow_through"
    DECLINED = "declined"


@dataclass(frozen=True, slots=True)
class ProposedAction:
    """One exact, reviewable sandbox action waiting for a decision."""

    action_type: str
    revision: int
    title: str
    starts_at: str
    ends_at: str
    boundary_note: str


@dataclass(frozen=True, slots=True)
class WorkflowSnapshot:
    """Persisted state returned to the API without exposing credentials or prompts."""

    case_id: str
    concern: str
    stage: WorkflowStage
    questions: tuple[MissingFact, ...] = ()
    pack: AssessmentPreparationPack | None = None
    proposed_action: ProposedAction | None = None
    action_result: DemoDispatchResult | None = None
    reminder: Reminder | None = None
    timeline: tuple[TimelineEvent, ...] = ()
    _candidate_pack: AssessmentPreparationPack | None = None


class WorkflowRepository(Protocol):
    """Storage boundary for complete, typed workflow snapshots."""

    def save(self, snapshot: WorkflowSnapshot) -> None:
        """Persist the latest snapshot for its case."""

    def get(self, *, case_id: str) -> WorkflowSnapshot:
        """Load a workflow or raise KeyError when it does not exist."""


class InMemoryWorkflowRepository:
    """Local/test storage with the same contract as the Firestore adapter."""

    def __init__(self) -> None:
        self._snapshots: dict[str, WorkflowSnapshot] = {}

    def save(self, snapshot: WorkflowSnapshot) -> None:
        self._snapshots[snapshot.case_id] = snapshot

    def get(self, *, case_id: str) -> WorkflowSnapshot:
        return self._snapshots[case_id]


class FirestoreWorkflowRepository:
    """Firestore storage for the durable workflow snapshot used by Cloud Run."""

    def __init__(self, client: Any | None = None) -> None:
        self._client = client or _new_firestore_client()

    def save(self, snapshot: WorkflowSnapshot) -> None:
        self._documents().document(snapshot.case_id).set(_snapshot_document(snapshot))

    def get(self, *, case_id: str) -> WorkflowSnapshot:
        document = self._documents().document(case_id).get()
        if not document.exists:
            raise KeyError(case_id)
        return _snapshot_from_document(document.to_dict())

    def _documents(self) -> Any:
        return self._client.collection("taskmaster_workflows")


class TaskmasterWorkflow:
    """Create, prepare, approve and follow through on one safe sandbox action."""

    def __init__(
        self,
        *,
        intake_agent: IntakeAgent,
        repository: WorkflowRepository,
        event_repository: EventRepository,
        calendar: CalendarDemoAdapter,
        reminders: ReminderService | None = None,
    ) -> None:
        self._intake_agent = intake_agent
        self._repository = repository
        self._event_repository = event_repository
        self.calendar = calendar
        self._reminders = reminders or ReminderService()

    def start(self, *, concern: str, now: datetime) -> WorkflowSnapshot:
        """Route danger before model use, otherwise begin the facts-only intake."""
        case_id = uuid4().hex
        try:
            candidate_pack = self._intake_agent.prepare_assessment_pack(concern)
        except EmergencyRouteRequired:
            snapshot = WorkflowSnapshot(
                case_id=case_id,
                concern=concern,
                stage=WorkflowStage.EMERGENCY,
            )
            return self._save(snapshot)

        snapshot = WorkflowSnapshot(
            case_id=case_id,
            concern=concern,
            stage=WorkflowStage.INTAKE,
            questions=candidate_pack.information_to_confirm,
            _candidate_pack=candidate_pack,
        )
        return self._save_with_event(
            snapshot,
            event_type="concern.created",
            now=now,
            details={"source": "older-person"},
        )

    def answer_intake(
        self, *, case_id: str, answers: Mapping[str, str], now: datetime
    ) -> WorkflowSnapshot:
        """Keep missing facts visible until every requested non-clinical answer arrives."""
        snapshot = self.get(case_id=case_id)
        if snapshot.stage is not WorkflowStage.INTAKE:
            raise ValueError("Answers can only be submitted while intake is open.")
        unanswered = tuple(
            question
            for question in snapshot.questions
            if not isinstance(answers.get(question.key), str) or not answers[question.key].strip()
        )
        if unanswered:
            return self._save(
                WorkflowSnapshot(
                    case_id=snapshot.case_id,
                    concern=snapshot.concern,
                    stage=WorkflowStage.INTAKE,
                    questions=unanswered,
                    timeline=snapshot.timeline,
                    _candidate_pack=snapshot._candidate_pack,
                )
            )

        candidate_pack = snapshot._candidate_pack
        if candidate_pack is None:
            raise RuntimeError("The intake pack is unavailable for this workflow.")
        proposal = ProposedAction(
            action_type=CalendarDemoAdapter.action_type,
            revision=1,
            title="Review your assessment preparation pack",
            starts_at=(now + timedelta(days=1)).isoformat(),
            ends_at=(now + timedelta(days=1, minutes=30)).isoformat(),
            boundary_note="Sandbox action — no real calendar, provider or contact will be used.",
        )
        prepared = WorkflowSnapshot(
            case_id=snapshot.case_id,
            concern=snapshot.concern,
            stage=WorkflowStage.AWAITING_APPROVAL,
            pack=candidate_pack,
            proposed_action=proposal,
            timeline=snapshot.timeline,
        )
        return self._save_with_event(
            prepared,
            event_type="assessment.pack.prepared",
            now=now,
            details={
                "action_type": proposal.action_type,
                "action_revision": str(proposal.revision),
            },
        )

    def decide_action(
        self, *, case_id: str, action_revision: int, approve: bool, now: datetime
    ) -> WorkflowSnapshot:
        """Execute exactly the approved draft once; repeated approval returns the result."""
        snapshot = self.get(case_id=case_id)
        if snapshot.stage is WorkflowStage.FOLLOW_THROUGH:
            if (
                snapshot.proposed_action is not None
                and action_revision == snapshot.proposed_action.revision
            ):
                return snapshot
            raise ValueError("The action revision is stale.")
        if (
            snapshot.stage is not WorkflowStage.AWAITING_APPROVAL
            or snapshot.proposed_action is None
        ):
            raise ValueError("There is no pending action for this workflow.")
        if action_revision != snapshot.proposed_action.revision:
            raise ValueError("The action revision is stale.")
        if not approve:
            return self._save_with_event(
                WorkflowSnapshot(
                    case_id=snapshot.case_id,
                    concern=snapshot.concern,
                    stage=WorkflowStage.DECLINED,
                    pack=snapshot.pack,
                    proposed_action=snapshot.proposed_action,
                    timeline=snapshot.timeline,
                ),
                event_type="approval.declined",
                now=now,
                details={"action_revision": str(action_revision)},
            )

        approval = ActionApproval(
            case_id=case_id,
            action_type=snapshot.proposed_action.action_type,
            action_revision=action_revision,
            approved_by_contact_id="older-person",
            expires_at=now + timedelta(minutes=15),
            created_at=now,
        )
        approved = self._save_with_event(
            snapshot,
            event_type="approval.granted",
            now=now,
            details={"action_revision": str(action_revision)},
        )
        result = self.calendar.create_event(
            case_id=case_id,
            revision=action_revision,
            approval=approval,
            now=now,
            details=CalendarDetails(
                title=approved.proposed_action.title,
                starts_at=approved.proposed_action.starts_at,
                ends_at=approved.proposed_action.ends_at,
            ),
        )
        reminder = self._reminders.schedule(
            case_id=case_id,
            action="Review the assessment preparation pack",
            due_at=now,
        )
        completed = WorkflowSnapshot(
            case_id=approved.case_id,
            concern=approved.concern,
            stage=WorkflowStage.FOLLOW_THROUGH,
            pack=approved.pack,
            proposed_action=approved.proposed_action,
            action_result=result,
            reminder=reminder,
            timeline=approved.timeline,
        )
        recorded = self._save_with_event(
            completed,
            event_type="calendar.action.recorded",
            now=now,
            details={"channel": result.channel, "sandbox": "true"},
        )
        return self._save_with_event(
            recorded,
            event_type="reminder.scheduled",
            now=now,
            details={"reminder_id": reminder.reminder_id},
        )

    def run_demo_follow_up(self, *, case_id: str, now: datetime) -> WorkflowSnapshot:
        """Send the already-approved synthetic reminder and expose its recorded state."""
        snapshot = self.get(case_id=case_id)
        if snapshot.stage is not WorkflowStage.FOLLOW_THROUGH or snapshot.reminder is None:
            raise ValueError("This workflow has no approved reminder to follow up.")
        if snapshot.reminder.status is ReminderStatus.SENT:
            return snapshot
        sent = self._reminders.process_due(now=now, send=lambda _: None)
        reminder = next(
            (item for item in sent if item.reminder_id == snapshot.reminder.reminder_id),
            None,
        )
        if reminder is None:
            reminder = self._reminders.get(snapshot.reminder.reminder_id)
        followed_up = WorkflowSnapshot(
            case_id=snapshot.case_id,
            concern=snapshot.concern,
            stage=snapshot.stage,
            pack=snapshot.pack,
            proposed_action=snapshot.proposed_action,
            action_result=snapshot.action_result,
            reminder=reminder,
            timeline=snapshot.timeline,
        )
        if reminder.status is ReminderStatus.SENT:
            return self._save_with_event(
                followed_up,
                event_type="reminder.sent",
                now=now,
                details={"reminder_id": reminder.reminder_id},
            )
        return self._save(followed_up)

    def get(self, *, case_id: str) -> WorkflowSnapshot:
        """Load the last persisted state for a case."""
        return self._repository.get(case_id=case_id)

    def _save_with_event(
        self,
        snapshot: WorkflowSnapshot,
        *,
        event_type: str,
        now: datetime,
        details: Mapping[str, str],
    ) -> WorkflowSnapshot:
        event = TimelineEvent(
            case_id=snapshot.case_id,
            event_type=event_type,
            details=details,
            occurred_at=now,
        )
        self._event_repository.append_if_new(event)
        updated = WorkflowSnapshot(
            case_id=snapshot.case_id,
            concern=snapshot.concern,
            stage=snapshot.stage,
            questions=snapshot.questions,
            pack=snapshot.pack,
            proposed_action=snapshot.proposed_action,
            action_result=snapshot.action_result,
            reminder=snapshot.reminder,
            timeline=(*snapshot.timeline, event),
            _candidate_pack=snapshot._candidate_pack,
        )
        return self._save(updated)

    def _save(self, snapshot: WorkflowSnapshot) -> WorkflowSnapshot:
        self._repository.save(snapshot)
        return snapshot


def _new_firestore_client() -> Any:
    from google.cloud import firestore

    return firestore.Client()


def _snapshot_document(snapshot: WorkflowSnapshot) -> dict[str, Any]:
    return {
        "case_id": snapshot.case_id,
        "concern": snapshot.concern,
        "stage": snapshot.stage.value,
        "questions": [_missing_fact_document(item) for item in snapshot.questions],
        "pack": _pack_document(snapshot.pack),
        "proposed_action": _proposal_document(snapshot.proposed_action),
        "action_result": _action_result_document(snapshot.action_result),
        "reminder": _reminder_document(snapshot.reminder),
        "timeline": [_timeline_document(event) for event in snapshot.timeline],
        "candidate_pack": _pack_document(snapshot._candidate_pack),
    }


def _snapshot_from_document(data: Mapping[str, Any]) -> WorkflowSnapshot:
    return WorkflowSnapshot(
        case_id=data["case_id"],
        concern=data["concern"],
        stage=WorkflowStage(data["stage"]),
        questions=tuple(_missing_fact_from_document(item) for item in data.get("questions", [])),
        pack=_pack_from_document(data.get("pack")),
        proposed_action=_proposal_from_document(data.get("proposed_action")),
        action_result=_action_result_from_document(data.get("action_result")),
        reminder=_reminder_from_document(data.get("reminder")),
        timeline=tuple(_timeline_from_document(item) for item in data.get("timeline", [])),
        _candidate_pack=_pack_from_document(data.get("candidate_pack")),
    )


def _missing_fact_document(item: MissingFact) -> dict[str, str]:
    return {"key": item.key, "question": item.question, "reason": item.reason}


def _missing_fact_from_document(data: Mapping[str, str]) -> MissingFact:
    return MissingFact(key=data["key"], question=data["question"], reason=data["reason"])


def _pack_document(pack: AssessmentPreparationPack | None) -> dict[str, Any] | None:
    if pack is None:
        return None
    return {
        "concern_summary": pack.concern_summary,
        "reported_difficulty": pack.reported_difficulty,
        "information_to_confirm": [
            _missing_fact_document(item) for item in pack.information_to_confirm
        ],
        "assessment_discussion_topics": list(pack.assessment_discussion_topics),
        "official_pathways": list(pack.official_pathways),
        "proposed_next_step": pack.proposed_next_step,
        "boundary_note": pack.boundary_note,
    }


def _pack_from_document(data: Mapping[str, Any] | None) -> AssessmentPreparationPack | None:
    if data is None:
        return None
    return AssessmentPreparationPack(
        concern_summary=data["concern_summary"],
        reported_difficulty=data["reported_difficulty"],
        information_to_confirm=tuple(
            _missing_fact_from_document(item) for item in data["information_to_confirm"]
        ),
        assessment_discussion_topics=tuple(data["assessment_discussion_topics"]),
        official_pathways=tuple(data["official_pathways"]),
        proposed_next_step=data["proposed_next_step"],
        boundary_note=data["boundary_note"],
    )


def _proposal_document(proposal: ProposedAction | None) -> dict[str, str | int] | None:
    if proposal is None:
        return None
    return {
        "action_type": proposal.action_type,
        "revision": proposal.revision,
        "title": proposal.title,
        "starts_at": proposal.starts_at,
        "ends_at": proposal.ends_at,
        "boundary_note": proposal.boundary_note,
    }


def _proposal_from_document(data: Mapping[str, Any] | None) -> ProposedAction | None:
    if data is None:
        return None
    return ProposedAction(
        action_type=data["action_type"],
        revision=data["revision"],
        title=data["title"],
        starts_at=data["starts_at"],
        ends_at=data["ends_at"],
        boundary_note=data["boundary_note"],
    )


def _action_result_document(result: DemoDispatchResult | None) -> dict[str, Any] | None:
    if result is None:
        return None
    return {
        "case_id": result.case_id,
        "action_type": result.action_type,
        "action_revision": result.action_revision,
        "channel": result.channel,
        "payload": dict(result.payload),
    }


def _action_result_from_document(data: Mapping[str, Any] | None) -> DemoDispatchResult | None:
    if data is None:
        return None
    return DemoDispatchResult(
        case_id=data["case_id"],
        action_type=data["action_type"],
        action_revision=data["action_revision"],
        channel=data["channel"],
        payload=data["payload"],
    )


def _reminder_document(reminder: Reminder | None) -> dict[str, Any] | None:
    if reminder is None:
        return None
    return {
        "reminder_id": reminder.reminder_id,
        "case_id": reminder.case_id,
        "action": reminder.action,
        "due_at": reminder.due_at,
        "max_attempts": reminder.max_attempts,
        "attempts": reminder.attempts,
        "next_attempt_at": reminder.next_attempt_at,
        "status": reminder.status.value,
        "last_error": reminder.last_error,
    }


def _reminder_from_document(data: Mapping[str, Any] | None) -> Reminder | None:
    if data is None:
        return None
    return Reminder(
        reminder_id=data["reminder_id"],
        case_id=data["case_id"],
        action=data["action"],
        due_at=data["due_at"],
        max_attempts=data["max_attempts"],
        attempts=data["attempts"],
        next_attempt_at=data.get("next_attempt_at"),
        status=ReminderStatus(data["status"]),
        last_error=data.get("last_error"),
    )


def _timeline_document(event: TimelineEvent) -> dict[str, Any]:
    return {
        "case_id": event.case_id,
        "event_type": event.event_type,
        "details": dict(event.details),
        "event_id": event.event_id,
        "occurred_at": event.occurred_at,
    }


def _timeline_from_document(data: Mapping[str, Any]) -> TimelineEvent:
    return TimelineEvent(
        case_id=data["case_id"],
        event_type=data["event_type"],
        details=data.get("details", {}),
        event_id=data["event_id"],
        occurred_at=data["occurred_at"],
    )

"""Consent-governed orchestration for StayLong's single Taskmaster workflow."""

from collections.abc import Mapping
from dataclasses import dataclass, replace
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
from staylong.policy.emergency import EMERGENCY_ROUTE, route_concern
from staylong.privacy.gemma import PrivacyRedaction
from staylong.services.channels import (
    CalendarDemoAdapter,
    CalendarDetails,
    ContactDraftDemoAdapter,
    DemoDispatchResult,
    MessageDetails,
)
from staylong.services.events import EventRepository
from staylong.services.home_plan import (
    HomeIndependencePlan,
    PlanTask,
    build_home_independence_plan,
)
from staylong.services.reminders import Reminder, ReminderService, ReminderStatus


class PrivacyGuard(Protocol):
    """Sanitizes user text before it enters persisted workflow state."""

    def redact(self, text: str) -> PrivacyRedaction: ...


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
    plan: HomeIndependencePlan | None = None
    proposed_action: ProposedAction | None = None
    proposed_actions: tuple[ProposedAction, ...] = ()
    action_result: DemoDispatchResult | None = None
    action_results: tuple[DemoDispatchResult, ...] = ()
    integration_mode: str = "sandbox"
    reminder: Reminder | None = None
    timeline: tuple[TimelineEvent, ...] = ()
    _candidate_pack: AssessmentPreparationPack | None = None


class WorkflowRepository(Protocol):
    """Storage boundary for complete, typed workflow snapshots."""

    def save(self, snapshot: WorkflowSnapshot) -> None:
        """Persist the latest snapshot for its case."""

    def get(self, *, case_id: str) -> WorkflowSnapshot:
        """Load a workflow or raise KeyError when it does not exist."""

    def delete(self, *, case_id: str) -> None:
        """Delete a workflow snapshot; safe when the case is already absent."""


class InMemoryWorkflowRepository:
    """Local/test storage with the same contract as the Firestore adapter."""

    def __init__(self) -> None:
        self._snapshots: dict[str, WorkflowSnapshot] = {}

    def save(self, snapshot: WorkflowSnapshot) -> None:
        self._snapshots[snapshot.case_id] = snapshot

    def get(self, *, case_id: str) -> WorkflowSnapshot:
        return self._snapshots[case_id]

    def delete(self, *, case_id: str) -> None:
        self._snapshots.pop(case_id, None)


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

    def delete(self, *, case_id: str) -> None:
        self._documents().document(case_id).delete()

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
        contact_drafts: ContactDraftDemoAdapter | None = None,
        reminders: ReminderService | None = None,
        privacy_guard: PrivacyGuard | None = None,
    ) -> None:
        self._intake_agent = intake_agent
        self._repository = repository
        self._event_repository = event_repository
        self.calendar = calendar
        self.contact_drafts = contact_drafts or ContactDraftDemoAdapter()
        self.integration_mode = calendar.integration_mode
        self._reminders = reminders or ReminderService()
        self._privacy_guard = privacy_guard

    @property
    def repository(self) -> WorkflowRepository:
        """Expose the persistence adapter for runtime wiring verification only."""
        return self._repository

    @property
    def event_repository(self) -> EventRepository:
        """Expose the event adapter for runtime wiring and cleanup."""
        return self._event_repository

    def start(self, *, concern: str, now: datetime) -> WorkflowSnapshot:
        """Route danger before model use, otherwise begin the facts-only intake."""
        case_id = uuid4().hex
        # Emergency detection must remain deterministic and must never wait for a model.
        protected_concern = concern
        if self._privacy_guard is not None and route_concern(concern) != EMERGENCY_ROUTE:
            protected_concern = self._privacy_guard.redact(concern).redacted_text
        try:
            candidate_pack = self._intake_agent.prepare_assessment_pack(protected_concern)
        except EmergencyRouteRequired:
            snapshot = WorkflowSnapshot(
                case_id=case_id,
                concern=protected_concern,
                stage=WorkflowStage.EMERGENCY,
            )
            return self._save(snapshot)

        snapshot = WorkflowSnapshot(
            case_id=case_id,
            concern=protected_concern,
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
        plan = build_home_independence_plan(candidate_pack, now=now)
        proposal = ProposedAction(
            action_type=CalendarDemoAdapter.action_type,
            revision=1,
            title="Review your assessment preparation pack",
            starts_at=(now + timedelta(days=1)).isoformat(),
            ends_at=(now + timedelta(days=1, minutes=30)).isoformat(),
            boundary_note="Sandbox action — no real calendar, provider or contact will be used.",
        )
        contact_draft_proposal = ProposedAction(
            action_type=ContactDraftDemoAdapter.action_type,
            revision=1,
            title="Review your assessment contact draft",
            starts_at="",
            ends_at="",
            boundary_note="Sandbox draft — it will not be sent without a separate approval.",
        )
        prepared = WorkflowSnapshot(
            case_id=snapshot.case_id,
            concern=snapshot.concern,
            stage=WorkflowStage.AWAITING_APPROVAL,
            pack=candidate_pack,
            plan=plan,
            proposed_action=proposal,
            proposed_actions=(proposal, contact_draft_proposal),
            timeline=snapshot.timeline,
        )
        return self._save_with_event(
            prepared,
            event_type="assessment.pack.prepared",
            now=now,
            details={
                "action_type": "plan.actions.prepared",
                "action_revision": "1",
            },
        )

    def decide_action(
        self,
        *,
        case_id: str,
        action_revision: int,
        approve: bool,
        now: datetime,
        action_type: str | None = None,
        actor_id: str | None = None,
    ) -> WorkflowSnapshot:
        """Execute exactly one approved action; each action keeps its own approval."""
        snapshot = self.get(case_id=case_id)
        selected_type = action_type or CalendarDemoAdapter.action_type
        proposal = next(
            (item for item in snapshot.proposed_actions if item.action_type == selected_type),
            snapshot.proposed_action if selected_type == CalendarDemoAdapter.action_type else None,
        )
        if proposal is None or proposal.revision != action_revision:
            raise ValueError("The action revision is stale.")
        existing_result = next(
            (
                item
                for item in snapshot.action_results
                if item.action_type == selected_type and item.action_revision == action_revision
            ),
            None,
        )
        if existing_result is not None:
            return snapshot
        if snapshot.stage not in {WorkflowStage.AWAITING_APPROVAL, WorkflowStage.FOLLOW_THROUGH}:
            raise ValueError("There is no pending action for this workflow.")
        if not approve:
            return self._save_with_event(
                WorkflowSnapshot(
                    case_id=snapshot.case_id,
                    concern=snapshot.concern,
                    stage=snapshot.stage,
                    pack=snapshot.pack,
                    plan=snapshot.plan,
                    proposed_action=snapshot.proposed_action,
                    proposed_actions=snapshot.proposed_actions,
                    action_result=snapshot.action_result,
                    action_results=snapshot.action_results,
                    reminder=snapshot.reminder,
                    timeline=snapshot.timeline,
                ),
                event_type="approval.declined",
                now=now,
                details={"action_type": selected_type, "action_revision": str(action_revision)},
            )

        approval = ActionApproval(
            case_id=case_id,
            action_type=selected_type,
            action_revision=action_revision,
            approved_by_contact_id="older-person",
            expires_at=now + timedelta(minutes=15),
            created_at=now,
        )
        approved = self._save_with_event(
            snapshot,
            event_type="approval.granted",
            now=now,
            details={"action_type": selected_type, "action_revision": str(action_revision)},
        )
        if selected_type == CalendarDemoAdapter.action_type:
            result = self.calendar.create_event(
                case_id=case_id,
                revision=action_revision,
                approval=approval,
                now=now,
                session_id=actor_id,
                details=CalendarDetails(
                    title=proposal.title,
                    starts_at=proposal.starts_at,
                    ends_at=proposal.ends_at,
                ),
            )
            reminder = self._reminders.schedule(
                case_id=case_id,
                action="Review the assessment preparation pack",
                due_at=now,
            )
            event_type = "calendar.action.recorded"
        else:
            result = self.contact_drafts.create_draft(
                case_id=case_id,
                revision=action_revision,
                approval=approval,
                now=now,
                details=MessageDetails(
                    recipient="",
                    subject="Assessment preparation",
                    body="A StayLong draft is ready for your review; it has not been sent.",
                ),
            )
            reminder = approved.reminder
            event_type = "contact_draft.created"
        completed = WorkflowSnapshot(
            case_id=approved.case_id,
            concern=approved.concern,
            stage=WorkflowStage.FOLLOW_THROUGH,
            pack=approved.pack,
            plan=approved.plan,
            proposed_action=approved.proposed_action,
            proposed_actions=approved.proposed_actions,
            action_result=result,
            action_results=(*approved.action_results, result),
            reminder=reminder,
            timeline=approved.timeline,
        )
        recorded = self._save_with_event(
            completed,
            event_type=event_type,
            now=now,
            details={"action_type": selected_type, "channel": result.channel, "sandbox": "true"},
        )
        if reminder is None:
            return recorded
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
            plan=snapshot.plan,
            proposed_action=snapshot.proposed_action,
            proposed_actions=snapshot.proposed_actions,
            action_result=snapshot.action_result,
            action_results=snapshot.action_results,
            integration_mode=snapshot.integration_mode,
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
            plan=snapshot.plan,
            proposed_action=snapshot.proposed_action,
            proposed_actions=snapshot.proposed_actions,
            action_result=snapshot.action_result,
            action_results=snapshot.action_results,
            reminder=snapshot.reminder,
            timeline=(*snapshot.timeline, event),
            _candidate_pack=snapshot._candidate_pack,
        )
        return self._save(updated)

    def _save(self, snapshot: WorkflowSnapshot) -> WorkflowSnapshot:
        if snapshot.integration_mode != self.integration_mode:
            snapshot = replace(snapshot, integration_mode=self.integration_mode)
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
        "plan": _plan_document(snapshot.plan),
        "proposed_action": _proposal_document(snapshot.proposed_action),
        "proposed_actions": [_proposal_document(item) for item in snapshot.proposed_actions],
        "action_result": _action_result_document(snapshot.action_result),
        "action_results": [_action_result_document(item) for item in snapshot.action_results],
        "integration_mode": snapshot.integration_mode,
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
        plan=_plan_from_document(data.get("plan")),
        proposed_action=_proposal_from_document(data.get("proposed_action")),
        proposed_actions=tuple(
            _proposal_from_document(item) for item in data.get("proposed_actions", [])
        ),
        action_result=_action_result_from_document(data.get("action_result")),
        action_results=tuple(
            _action_result_from_document(item) for item in data.get("action_results", [])
        ),
        integration_mode=data.get("integration_mode", "sandbox"),
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


def _plan_document(plan: HomeIndependencePlan | None) -> dict[str, Any] | None:
    if plan is None:
        return None
    return {
        "title": plan.title,
        "stated_difficulty": plan.stated_difficulty,
        "goal": plan.goal,
        "official_pathway": plan.official_pathway,
        "tasks": [
            {
                "task_id": task.task_id,
                "title": task.title,
                "description": task.description,
                "owner": task.owner,
                "due_at": task.due_at,
                "status": task.status,
                "blocker": task.blocker,
            }
            for task in plan.tasks
        ],
    }


def _plan_from_document(data: Mapping[str, Any] | None) -> HomeIndependencePlan | None:
    if data is None:
        return None
    return HomeIndependencePlan(
        title=data["title"],
        stated_difficulty=data["stated_difficulty"],
        goal=data["goal"],
        official_pathway=data["official_pathway"],
        tasks=tuple(
            PlanTask(
                task_id=item["task_id"],
                title=item["title"],
                description=item["description"],
                owner=item["owner"],
                due_at=item["due_at"],
                status=item["status"],
                blocker=item.get("blocker"),
            )
            for item in data["tasks"]
        ),
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

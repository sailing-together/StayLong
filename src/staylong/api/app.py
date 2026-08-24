"""Authenticated FastAPI case-flow API with an injectable persistence boundary."""

import secrets
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field
from starlette.staticfiles import StaticFiles

from staylong.services.cases import CaseRepository, InMemoryCaseRepository
from staylong.services.taskmaster import TaskmasterWorkflow, WorkflowSnapshot


class ConcernRequest(BaseModel):
    """The non-clinical concern accepted by the case-flow API."""

    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1, max_length=2_000)


class CaseResponse(BaseModel):
    case_id: str
    status: str = "open"


class ConcernResponse(BaseModel):
    concern_id: str
    case_id: str
    summary: str


class WorkflowConcernRequest(BaseModel):
    """One non-clinical concern for the approval-gated Taskmaster path."""

    model_config = ConfigDict(extra="forbid")

    concern: str = Field(min_length=1, max_length=2_000)


class WorkflowAnswersRequest(BaseModel):
    """Plain-text answers to the workflow's permitted household questions."""

    model_config = ConfigDict(extra="forbid")

    answers: dict[str, str]


class ActionDecisionRequest(BaseModel):
    """A human decision for exactly one proposed action revision."""

    model_config = ConfigDict(extra="forbid")

    action_type: str = Field(min_length=1, max_length=100)
    action_revision: int = Field(ge=1)
    decision: Literal["approve", "decline"]


class MissingFactResponse(BaseModel):
    key: str
    question: str
    reason: str


class AssessmentPackResponse(BaseModel):
    concern_summary: str
    reported_difficulty: str
    information_to_confirm: list[MissingFactResponse]
    assessment_discussion_topics: list[str]
    official_pathways: list[str]
    proposed_next_step: str
    boundary_note: str


class ProposedActionResponse(BaseModel):
    action_type: str
    revision: int
    title: str
    starts_at: str
    ends_at: str
    boundary_note: str


class PlanTaskResponse(BaseModel):
    task_id: str
    title: str
    description: str
    owner: str
    due_at: datetime
    status: str
    blocker: str | None = None


class HomeIndependencePlanResponse(BaseModel):
    title: str
    stated_difficulty: str
    goal: str
    official_pathway: str
    tasks: list[PlanTaskResponse]


class ActionResultResponse(BaseModel):
    case_id: str
    action_type: str
    action_revision: int
    channel: str
    payload: dict[str, str]


class ReminderResponse(BaseModel):
    reminder_id: str
    action: str
    due_at: datetime
    status: str


class TimelineEventResponse(BaseModel):
    event_id: str
    event_type: str
    details: dict[str, str]
    occurred_at: datetime


class WorkflowResponse(BaseModel):
    case_id: str
    stage: str
    questions: list[MissingFactResponse]
    pack: AssessmentPackResponse | None = None
    plan: HomeIndependencePlanResponse | None = None
    proposed_action: ProposedActionResponse | None = None
    proposed_actions: list[ProposedActionResponse] = []
    action_result: ActionResultResponse | None = None
    action_results: list[ActionResultResponse] = []
    reminder: ReminderResponse | None = None
    timeline: list[TimelineEventResponse]


APPLICATION_TOKEN_HEADER = "X-StayLong-API-Token"


def create_app(
    *,
    api_token: str,
    repository: CaseRepository | None = None,
    workflow: TaskmasterWorkflow | None = None,
) -> FastAPI:
    """Create the API with an explicit token and injectable case repository."""
    if not api_token:
        raise ValueError("api_token is required")

    app = FastAPI(title="StayLong case-flow API", version="0.1.0")
    cases = repository or InMemoryCaseRepository()
    bearer = HTTPBearer(auto_error=False)

    def require_auth(
        request: Request,
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    ) -> None:
        # The proxy used by private Cloud Run smoke tests owns Authorization
        # for the platform ID token. Preserve the normal bearer contract for
        # clients, with a narrow application-token header for that proxy path.
        application_token = request.headers.get(APPLICATION_TOKEN_HEADER)
        if application_token is not None:
            provided_token = application_token
        elif credentials is not None and credentials.scheme.lower() == "bearer":
            provided_token = credentials.credentials
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Bearer authentication is required.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not secrets.compare_digest(provided_token, api_token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid bearer token.",
                headers={"WWW-Authenticate": "Bearer"},
            )

    def require_workflow() -> TaskmasterWorkflow:
        if workflow is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="StayLong workflow is not available yet.",
            )
        return workflow

    @app.get("/health", include_in_schema=False)
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/v1/cases", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
    def create_case(
        concern: ConcernRequest,
        _: Callable[[], None] = Depends(require_auth),
    ) -> CaseResponse:
        case_id = f"case-{uuid4().hex}"
        cases.create_concern(case_id=case_id, summary=concern.summary)
        return CaseResponse(case_id=case_id)

    @app.get("/v1/cases/{case_id}/concerns", response_model=list[ConcernResponse])
    def list_concerns(
        case_id: str,
        _: Callable[[], None] = Depends(require_auth),
    ) -> list[ConcernResponse]:
        return [
            ConcernResponse(
                concern_id=concern.concern_id,
                case_id=concern.case_id,
                summary=concern.summary,
            )
            for concern in cases.list_concerns(case_id=case_id)
        ]

    @app.post(
        "/v1/workflows",
        response_model=WorkflowResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def create_workflow(
        request: WorkflowConcernRequest,
        _: Callable[[], None] = Depends(require_auth),
        taskmaster: TaskmasterWorkflow = Depends(require_workflow),
    ) -> WorkflowResponse:
        try:
            return _workflow_response(taskmaster.start(concern=request.concern, now=_now()))
        except Exception as error:
            _raise_safe_intake_error(error)
            raise

    @app.post("/v1/workflows/{case_id}/answers", response_model=WorkflowResponse)
    def answer_workflow(
        case_id: str,
        request: WorkflowAnswersRequest,
        _: Callable[[], None] = Depends(require_auth),
        taskmaster: TaskmasterWorkflow = Depends(require_workflow),
    ) -> WorkflowResponse:
        try:
            return _workflow_response(
                taskmaster.answer_intake(case_id=case_id, answers=request.answers, now=_now())
            )
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plan not found.",
            ) from None
        except ValueError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=str(error),
            ) from None

    @app.post("/v1/workflows/{case_id}/action-decision", response_model=WorkflowResponse)
    def decide_workflow_action(
        case_id: str,
        request: ActionDecisionRequest,
        _: Callable[[], None] = Depends(require_auth),
        taskmaster: TaskmasterWorkflow = Depends(require_workflow),
    ) -> WorkflowResponse:
        try:
            return _workflow_response(
                taskmaster.decide_action(
                    case_id=case_id,
                    action_type=request.action_type,
                    action_revision=request.action_revision,
                    approve=request.decision == "approve",
                    now=_now(),
                )
            )
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plan not found.",
            ) from None
        except ValueError as error:
            if "revision" in str(error).lower():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="This action has changed. Please review the current plan.",
                ) from None
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=str(error),
            ) from None

    @app.post("/v1/workflows/{case_id}/demo-follow-up", response_model=WorkflowResponse)
    def run_demo_follow_up(
        case_id: str,
        _: Callable[[], None] = Depends(require_auth),
        taskmaster: TaskmasterWorkflow = Depends(require_workflow),
    ) -> WorkflowResponse:
        try:
            return _workflow_response(taskmaster.run_demo_follow_up(case_id=case_id, now=_now()))
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plan not found.",
            ) from None
        except ValueError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=str(error),
            ) from None

    @app.get("/v1/workflows/{case_id}", response_model=WorkflowResponse)
    def get_workflow(
        case_id: str,
        _: Callable[[], None] = Depends(require_auth),
        taskmaster: TaskmasterWorkflow = Depends(require_workflow),
    ) -> WorkflowResponse:
        try:
            return _workflow_response(taskmaster.get(case_id=case_id))
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plan not found.",
            ) from None

    app.mount(
        "/",
        StaticFiles(directory=Path(__file__).parent / "static", html=True),
        name="family-ui",
    )

    return app


def _now() -> datetime:
    return datetime.now(UTC)


def _raise_safe_intake_error(error: Exception) -> None:
    """Map policy refusals to plain language without returning internal details."""
    from staylong.agents.intake import MedicalTriageRefusalRequired

    if isinstance(error, MedicalTriageRefusalRequired):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from None
    raise error


def _workflow_response(snapshot: WorkflowSnapshot) -> WorkflowResponse:
    """Serialize only the public, non-sensitive workflow view."""
    return WorkflowResponse(
        case_id=snapshot.case_id,
        stage=snapshot.stage.value,
        questions=[
            MissingFactResponse(key=item.key, question=item.question, reason=item.reason)
            for item in snapshot.questions
        ],
        pack=(
            AssessmentPackResponse(
                concern_summary=snapshot.pack.concern_summary,
                reported_difficulty=snapshot.pack.reported_difficulty,
                information_to_confirm=[
                    MissingFactResponse(key=item.key, question=item.question, reason=item.reason)
                    for item in snapshot.pack.information_to_confirm
                ],
                assessment_discussion_topics=list(snapshot.pack.assessment_discussion_topics),
                official_pathways=list(snapshot.pack.official_pathways),
                proposed_next_step=snapshot.pack.proposed_next_step,
                boundary_note=snapshot.pack.boundary_note,
            )
            if snapshot.pack is not None
            else None
        ),
        plan=(
            HomeIndependencePlanResponse(
                title=snapshot.plan.title,
                stated_difficulty=snapshot.plan.stated_difficulty,
                goal=snapshot.plan.goal,
                official_pathway=snapshot.plan.official_pathway,
                tasks=[
                    PlanTaskResponse(
                        task_id=task.task_id,
                        title=task.title,
                        description=task.description,
                        owner=task.owner,
                        due_at=task.due_at,
                        status=task.status,
                        blocker=task.blocker,
                    )
                    for task in snapshot.plan.tasks
                ],
            )
            if snapshot.plan is not None
            else None
        ),
        proposed_action=(
            ProposedActionResponse(
                action_type=snapshot.proposed_action.action_type,
                revision=snapshot.proposed_action.revision,
                title=snapshot.proposed_action.title,
                starts_at=snapshot.proposed_action.starts_at,
                ends_at=snapshot.proposed_action.ends_at,
                boundary_note=snapshot.proposed_action.boundary_note,
            )
            if snapshot.proposed_action is not None
            else None
        ),
        proposed_actions=[
            ProposedActionResponse(
                action_type=action.action_type,
                revision=action.revision,
                title=action.title,
                starts_at=action.starts_at,
                ends_at=action.ends_at,
                boundary_note=action.boundary_note,
            )
            for action in snapshot.proposed_actions
        ],
        action_result=(
            ActionResultResponse(
                case_id=snapshot.action_result.case_id,
                action_type=snapshot.action_result.action_type,
                action_revision=snapshot.action_result.action_revision,
                channel=snapshot.action_result.channel,
                payload={**snapshot.action_result.payload, "sandbox": "true"},
            )
            if snapshot.action_result is not None
            else None
        ),
        action_results=[
            ActionResultResponse(
                case_id=result.case_id,
                action_type=result.action_type,
                action_revision=result.action_revision,
                channel=result.channel,
                payload={**result.payload, "sandbox": "true"},
            )
            for result in snapshot.action_results
        ],
        reminder=(
            ReminderResponse(
                reminder_id=snapshot.reminder.reminder_id,
                action=snapshot.reminder.action,
                due_at=snapshot.reminder.due_at,
                status=snapshot.reminder.status.value,
            )
            if snapshot.reminder is not None
            else None
        ),
        timeline=[
            TimelineEventResponse(
                event_id=event.event_id,
                event_type=event.event_type,
                details=dict(event.details),
                occurred_at=event.occurred_at,
            )
            for event in snapshot.timeline
        ],
    )

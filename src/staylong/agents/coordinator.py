"""Approval-aware coordination planning with no tool execution capability."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from staylong.agents.prompts import COORDINATION_SYSTEM_INSTRUCTION
from staylong.agents.vertex import (
    AdkAgentFactory,
    VertexRuntimeConfig,
    build_google_adk_agent,
)
from staylong.domain.models import ActionApproval
from staylong.policy.approvals import has_matching_approval

CoordinationStatus = Literal["draft", "approved_action"]


@dataclass(frozen=True, slots=True)
class CoordinationRequest:
    """The facts required to propose one reversible coordination action."""

    case_id: str
    action_type: str
    action_revision: int
    owner: str
    due_at: datetime
    reason: str


@dataclass(frozen=True, slots=True)
class CoordinationAction:
    """A displayable action or draft with its approval requirements visible."""

    action_type: str
    action_revision: int
    owner: str
    due_at: datetime
    required_approval: str
    reason: str


@dataclass(frozen=True, slots=True)
class CoordinationResult:
    """A plan only; callers must use the policy tool guard to perform any action."""

    status: CoordinationStatus
    may_execute: bool
    action: CoordinationAction


class CoordinationAgent:
    """Derives an approval-bounded action proposal from already supplied facts."""

    def __init__(self, *, adk_agent: object | None = None) -> None:
        """Retain the configured ADK agent without exposing it as a bypass surface."""
        self._adk_agent = adk_agent

    def coordinate(
        self,
        *,
        request: CoordinationRequest,
        approval: ActionApproval | None,
        now: datetime,
    ) -> CoordinationResult:
        """Return a draft unless the exact action revision has current approval.

        This class deliberately exposes no tool interface. A downstream integration must
        still call ``execute_approved_tool_action`` at the external-side-effect boundary.
        """
        current_approval = has_matching_approval(
            case_id=request.case_id,
            action_type=request.action_type,
            action_revision=request.action_revision,
            approval=approval,
            now=now,
        )
        action = CoordinationAction(
            action_type=request.action_type,
            action_revision=request.action_revision,
            owner=request.owner,
            due_at=request.due_at,
            required_approval=f"{request.action_type} revision {request.action_revision}",
            reason=request.reason,
        )
        return CoordinationResult(
            status="approved_action" if current_approval else "draft",
            may_execute=current_approval,
            action=action,
        )


def build_vertex_adk_coordination_agent(
    *,
    agent_factory: AdkAgentFactory = build_google_adk_agent,
    environment: Mapping[str, str] | None = None,
) -> CoordinationAgent:
    """Build a coordinator wrapper rather than returning a prompt-only ADK agent.

    The configured ADK object is deliberately private. ``coordinate`` continues
    to run the durable approval predicate and only returns an action draft when
    approval is absent or stale; it provides no external tool capability.
    """
    vertex_config = VertexRuntimeConfig.from_environment(environment)
    adk_agent = agent_factory(
        name="staylong_coordinator",
        model_id=vertex_config.model_id,
        instruction=COORDINATION_SYSTEM_INSTRUCTION,
        vertex_config=vertex_config,
    )
    return CoordinationAgent(adk_agent=adk_agent)

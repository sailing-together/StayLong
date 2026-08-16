# Official training guidance

StayLong's implementation decisions are guided by the official training linked from the All Things Agentic Hackathon resources page.

## What we will use

| Official resource | Practical decision for StayLong |
| --- | --- |
| [ADK 2 orchestration patterns](https://cloudonair.withgoogle.com/events/architecting-multi-agent-teams-mastering-three-orchestration-patterns-adk-2) | Use an ADK graph workflow as the primary orchestrator. Keep the emergency route and approval checks deterministic; do not use an LLM merely to choose a safety-critical branch. |
| [Long-running agents with ADK](https://cloudonair.withgoogle.com/events/build-long-running-agent-persistent-workflows-google-adk) | Persist workflow state, pause for explicit approval, resume from durable state, and add idempotency keys so an automatic retry cannot duplicate a Calendar action or notification. |
| [ADK documentation](https://google.github.io/adk-docs) | Use Python ADK with graph workflows, structured tool contracts, local testing and evaluation fixtures before Cloud Run deployment. |
| [GEAR: Introduction to Agents](https://www.skills.google/paths/3546) | Use the official hands-on path as the team's onboarding and reference material for ADK and deployment. |
| [Agent memory webinar](https://cloudonair.withgoogle.com/events/architecting-agent-memory-session-state-vector-search-managed-cloud-memory) | Use Firestore for bounded case state and audit records in the MVP. Do not add vector search or unbounded memory unless a demonstrated user need requires it. |
| [Self-evolving agents webinar](https://cloudonair.withgoogle.com/events/build-self-evolving-agent-autonomous-self-improvement) | Improve only through offline, versioned evaluation. Optimise for verified workflow outcomes and safety constraints, never for a superficial "looks complete" score; production safety rules and tool permissions are not self-modifying. |

## Architecture decisions derived from the training

1. **Graph before a team of agents.** The workflow is an explicit graph: intake → deterministic safety check → fact collection → preparation pack → approval pause → approved action → reminder/escalation → completion. Separate specialist agents are only introduced when they simplify a bounded node.
2. **Human approval is durable state.** A pending approval is stored and auditable, rather than being an instruction hidden in chat context. The workflow may resume only against that matching approval record.
3. **Idempotency is mandatory.** Every event and approved external action carries a stable idempotency key. Replayed events must be safe.
4. **Model usage is constrained.** Gemini Flash is the default for routine extraction and classification. A Gemini Pro-capable model is reserved for complex preparation or synthesis where evaluation shows a material benefit.
5. **Serverless by default.** Cloud Run runs with minimum instances set to zero and a conservative maximum-instance limit. Cloud Tasks handles delayed work instead of a permanently running worker.
6. **Measure before expanding memory.** Firestore stores only the data needed for the active case, consent, approval and audit trail. Sensitive or unrelated history is not loaded into agent context.
7. **Improve offline, deploy deliberately.** Evaluation traces may identify a better prompt or extraction policy, but any change is versioned, tested against safety fixtures and reviewed before deployment. The live service cannot rewrite its own policies, approval rules or tool permissions.

## Training-informed acceptance checks

Before the demo, prove all of the following:

- stopping and restarting the service does not lose an in-progress case;
- a retry cannot create two calendar events or notifications;
- an approval pause cannot be bypassed by prompting or event replay;
- the emergency route makes no model call and schedules no delayed task;
- the timeline shows the event, decision, approval and external action that completed the workflow.
- a held or restarted workflow resumes at its saved state without repeating a completed side effect;
- every evaluation score is paired with a trajectory check: the agent must show the required verification and approval steps, not merely a plausible final summary.

## Recommended viewing order

1. [Build a Long-Running Agent: Persistent Workflows with Google ADK](https://cloudonair.withgoogle.com/events/build-long-running-agent-persistent-workflows-google-adk)
2. [Architecting Multi-Agent Teams: Mastering the Three Orchestration Patterns of ADK 2](https://cloudonair.withgoogle.com/events/architecting-multi-agent-teams-mastering-three-orchestration-patterns-adk-2)
3. [ADK documentation](https://google.github.io/adk-docs)
4. [Architecting Agent Memory](https://cloudonair.withgoogle.com/events/architecting-agent-memory-session-state-vector-search-managed-cloud-memory)

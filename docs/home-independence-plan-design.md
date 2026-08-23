# Home Independence Plan Design

## Goal

Turn a non-emergency home-living concern into a useful, durable plan that an older person living alone can act on independently. The first product outcome is a clear assessment-preparation plan, not clinical advice or a funding decision.

## User outcome

For the night-time bathroom scenario, the user leaves with:

1. a plain-language summary of the difficulty and their stated goal;
2. an assessment preparation checklist and the official My Aged Care pathway;
3. three actionable tasks with owner, due date and status;
4. two separately reviewable actions: a Calendar event and a contact draft; and
5. an audit trail showing what was prepared, approved, created or still blocked.

## Scope

### Included

- A versioned `HomeIndependencePlan` attached to the existing case workflow.
- Three deterministic task templates for the first scenario: arrange assessment, prepare information, and confirm home access or permission.
- A separately approval-gated Calendar action and contact-draft action.
- A production Google adapter boundary with a visible sandbox fallback when OAuth is not configured.
- Idempotent action execution, durable status updates, and overdue-task follow-up suggestions.
- A task-board user interface that shows completed work, pending approvals and the next useful action.

### Excluded

- Medical, occupational-therapy or eligibility determinations.
- Automatic provider selection, government submission, payment, or email/SMS sending.
- Real Google OAuth credentials in source control or a requirement that the hackathon demo use a personal account.
- A broad provider marketplace or a general-purpose caregiver CRM.

## Workflow

```text
concern
  -> deterministic emergency policy
  -> non-clinical intake facts
  -> Home Independence Plan + task board
  -> user reviews two proposed actions
  -> independently approves Calendar event and/or contact draft
  -> adapter creates approved artifact exactly once
  -> durable timeline + due-date follow-up suggestions
```

The emergency policy remains before model use. The model may create structured, plain-language plan content; application code controls workflow state, consent, approvals and tool execution.

## Plan model

`HomeIndependencePlan` is a typed public artifact derived from the current assessment pack. It contains a title, stated difficulty, goal, official pathway, and a list of `PlanTask` records.

Each `PlanTask` includes `id`, `title`, `description`, `owner`, `due_at`, `status` (`ready`, `blocked`, `completed`), and `blocker`. For the MVP, ownership defaults to the older person; no supporter is included unless the person explicitly adds one later.

`ProposedAction` becomes a union of two independently versioned records:

- `calendar.create`: a personal coordination event titled “Prepare for My Aged Care assessment”.
- `contact_draft.create`: a reviewable, unsent draft explaining the concern and requesting the next appropriate contact.

The user approves each revision individually. A repeated approval returns the original result and never creates a duplicate artifact.

## Integration boundary

The application exposes `CalendarAdapter` and `ContactDraftAdapter` protocols. The sandbox adapters return clearly labelled local records for repeatable demos. Production adapters are constructed only when the required Google OAuth configuration is present; otherwise the API returns an actionable `integration_unavailable` state rather than claiming an external action occurred.

The Calendar adapter is allowed to create an event only after matching approval. The draft adapter is allowed to create a draft only after matching approval. Neither adapter sends a message.

## API and state changes

The workflow response gains `plan`, `proposed_actions`, and `action_results` while retaining existing fields during the transition. New routes decide a named action revision rather than a single implicit action. A read endpoint returns the durable plan, action status and timeline after a restart.

Events distinguish `plan.created`, `task.completed`, `calendar.created`, `contact_draft.created`, `action.blocked`, and `follow_up.suggested`. Firestore serialization must round-trip all public plan and action fields.

## User interface

After intake, the primary panel is “Your Home Independence Plan”, not an abstract assessment pack. It shows:

- “What StayLong prepared for you” with the summary and assessment notes;
- a three-item task board with clear progress and due dates;
- “Waiting for your approval” cards for Calendar and contact draft actions;
- an action result section that distinguishes sandbox from connected Google results; and
- a concise safety note rather than repeating limitations as the main content.

The current visual language, logo and accessibility-first labels remain. Keyboard-accessible buttons, status announcements and visible error states are required.

## Safety and privacy

StayLong stores only non-clinical facts required for the plan. It does not infer health needs from photos, decide qualification, submit My Aged Care applications, select providers, make payments, or send contact drafts. OAuth consent and an actual external action are deliberate user steps and are never performed by a background workflow without matching approval.

## Acceptance criteria

1. A normal concern produces a Home Independence Plan with three useful tasks.
2. Calendar and contact-draft actions appear separately and cannot execute before approval.
3. The sandbox visibly states it is a sandbox; production adapters are unavailable until OAuth is configured.
4. Repeated action approval is idempotent.
5. Restart/reload returns the plan, action status and complete timeline.
6. The UI demonstrates plan creation, one approved Calendar action, one unapproved draft, and a follow-up suggestion.
7. Emergency input has no plan or tool actions.

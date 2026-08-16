# Delivery standards

This is the working agreement for every StayLong Linear task and pull request.

## Definition of done for a task

Each implemented task must link to, or add, documentation that states:

1. **Purpose and scope** — the user outcome, non-goals and linked Linear issue.
2. **Design** — data, agent, security and integration choices affected by the change.
3. **Run instructions** — local setup, configuration and test commands.
4. **Verification** — automated tests plus the manual acceptance scenario and expected result.
5. **Safety impact** — approval gates, data handling and emergency-path implications, where relevant.
6. **Deployment impact** — Terraform, GitHub Actions and rollback notes, where relevant.

Repository documentation is English-first. Chinese clarifications may be added for internal coordination when helpful.

## Human action required

The delivery agent will identify any step that requires the project owner to act using this exact heading:

```md
## Human action required

- **Why:** the authority that cannot be delegated.
- **Action:** the exact click, approval or value required.
- **Link:** a direct URL to the relevant GitHub, Google Cloud, Linear or Devpost screen.
- **Safe to continue after:** the observable confirmation state.
```

Examples include signing in, granting OAuth consent, creating or billing a Google Cloud project, approving a protected GitHub environment, adding secrets/variables, authorising a Calendar account, paying fees, or submitting the final Devpost entry. Those decisions will never be made silently.

## Autonomous engineering work

Unless a human-action gate applies, the delivery agent is authorised to:

- create task-scoped branches and commits;
- update code, tests, Terraform, GitHub Actions and project documentation;
- run relevant checks;
- open and update pull requests; and
- merge a pull request only after required automated checks and any configured repository approvals are satisfied.

Every pull request will state its linked Linear issue, verification evidence, deployment impact and any remaining human-action gate.

# StayLong flow review — Figma-ready handoff

This is the design handoff from the end-to-end public sandbox review. It is structured so the flow can be recreated as Figma frames and annotated without changing the product's calm, humanist visual language.

## Flow map

```text
01 Concern  →  02 Intake questions  →  03 Plan + preparation pack
                                      ↓
                              04 Approval actions
                                      ↓
                         05 Follow-through / continue
```

## Frame notes

| Frame | User goal | Must be visible | Current risk | Next design change |
| --- | --- | --- | --- | --- |
| 01 — Tell us what is difficult | Start in their own words | Freeform input, editable examples, emergency route | Only three examples; selection explains itself late | Keep examples, add “starting point” helper copy near them |
| 02 — Prepare for assessment | Answer only what is needed | Three plain-language questions, back navigation | Network wait can look like a failed click | Show “Preparing your questions…” inline and preserve input |
| 03 — Your Home Independence Plan | Understand the plan | Recorded concern, practical steps, preparation pack, official pathway | “Arrange assessment” overstates capability | Use “Prepare to arrange…” and keep official link prominent |
| 04 — Approve next action | Stay in control | Separate approval cards and sandbox boundary | Pack review is represented as a reminder action | Make “Review preparation pack” an actual review affordance |
| 05 — Your plan is ready to continue | Know what to do next | Completed results, next-step CTA, official pathway, return path | Completion currently ends as a static log | Add completion card with pack review, My Aged Care, and next conversation guidance |

## Completion frame (recommended)

**Eyebrow:** Follow through

**Heading:** Your plan is ready to continue

**Body:** Both actions are recorded in this sandbox plan. Nothing was sent or booked.

**Next-step guidance:** When you are ready, take these notes to your aged-care or occupational-therapy conversation.

**Actions:**

- Review preparation pack
- Open My Aged Care

## Interaction and accessibility annotations

- Every network-backed action needs a visible status message and a disabled state with changed button text.
- Focus should move to the updated result or completion section after an approved action.
- Keep the existing skip link, semantic headings, labels, and keyboard-visible focus treatment.
- On narrow screens, keep primary and secondary actions full-width and preserve the same action order.

## Audit evidence

The full synthetic-data audit captured these frames locally:

- `/tmp/staylong-audit-01-start.png`
- `/tmp/staylong-audit-02-example.png`
- `/tmp/staylong-audit-03-intake.png`
- `/tmp/staylong-audit-04-plan.png`
- `/tmp/staylong-audit-05-calendar-complete.png`
- `/tmp/staylong-audit-06-both-complete.png`

This is a Figma-ready review, not a live Figma file: the current workspace has no connected Figma canvas write capability.

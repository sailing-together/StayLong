# StayLong design system

## Product and audience

StayLong is a consent-governed coordination layer for older Australians who
live alone. It turns one non-emergency concern at home into an organised,
assessment-ready workflow: understand the concern, collect non-clinical facts,
prepare for assessment, coordinate only approved actions, follow up, and prove
completion. A trusted supporter is optional and invited only by the older
person.

The interface must feel calm, respectful, capable, and easy to understand. It
must not look clinical, institutional, childish, or like a generic chatbot.

## Core experience

The product should make this promise clear within five seconds:

> StayLong helps older Australians living alone organise practical support so
> they can remain independent at home.

The main user journey is:

1. Start a home support plan.
2. Describe what is becoming difficult.
3. Pass a deterministic emergency check.
4. Answer one practical question at a time.
5. Review and approve an assessment preparation pack.
6. Track approved appointments, reminders, follow-up, and completion.

## Information hierarchy

- Lead with what StayLong does, who it is for, and the concrete outcome.
- Use one primary action: `Start my home support plan`.
- The product experience is a focused workspace, not a long marketing page.
- Keep the active step and its single next action above the fold. Explain the
  three outcomes—assessment preparation, approved coordination, and follow-up
  to completion—inside the workspace rather than in promotional sections.
- Show progress, one next action, current status, and user control at every step.
- Keep urgent-help routing visible but compact until emergency rules activate.
- Never expose access tokens or infrastructure settings in the user interface.

## Visual language

- Commit fully to the **Organic** visual anchor: calm, tactile and capable,
  without looking clinical, institutional or nostalgic.
- Sand `#e8dcc7` is the primary background.
- Moss `#283018` is the primary text and action colour.
- Terracotta `#71311d` is a restrained accent and focus colour.
- Sage `#8b9d83`, oat `#d4b895`, and clay `#b08b6e` support surfaces and borders.
- Use Epilogue as the single display and body family, with a warm geometric,
  highly legible character. Do not use Georgia or another serif.
- Prefer generous whitespace, clear dividers, low-noise surfaces, and at most
  one visually dominant card per screen.
- Use 16–32px rounded corners and a restrained 1–2% grain texture on large
  surfaces. Motion should use gentle 300–500ms easing and respect reduced
  motion preferences.
- Avoid oversized decorative type, marketing heroes, card grids, and repeated
  explanations that push the active task below the fold.
- Avoid gradients, neon colours, glass effects, decorative illustrations, and
  healthcare stock photography.

## Brand identity

- The approved mark is **Continuous Home Path**: one deep-moss line forms a
  simple home and continues through an open terracotta doorway into a calm
  forward path. It represents independence at home and practical work that
  keeps moving.
- Use the exact supplied StayLong logo asset in every logo position. Do not
  substitute initials, emoji, a generic house, an invented mark, or text alone.
- Use `frontend/public/brand/staylong-lockup.svg` in wide headers and product
  introductions, `staylong-mark.svg` where the wordmark is already present,
  and `staylong-app-icon.svg` for compact square contexts.
- Keep clear space around the mark equal to at least the doorway width. Do not
  rotate, recolour, crop, add effects, or place it on low-contrast imagery.
- The wordmark is exactly `StayLong`, with capital S and L, set in a bold,
  highly legible humanist sans-serif.
- The signature layout move is a continuous progress spine derived from the
  logo path. It connects the four real workflow stages and visibly anchors the
  current step; it is functional navigation, not decoration.

## Interaction and accessibility

- Body copy should be at least 18px in the older-person workflow.
- Controls should be at least 48px high with obvious text labels.
- Use plain Australian English and one instruction per screen.
- Keep keyboard focus visible and logical.
- Announce async status changes and errors with clear recovery actions.
- Honour reduced-motion preferences.
- Do not rely on colour alone for progress, approval, or urgency.

## Product boundaries

StayLong sits between family care apps, provider operations software and My
Aged Care. It does not manage day-to-day care delivery, run provider rosters or
billing, or replace the government assessment and application process.

StayLong does not diagnose, decide eligibility, access MyGov, select providers,
prescribe modifications, make payments, or claim funds. Assessors and qualified
professionals make eligibility and clinical decisions. External sharing,
bookings, and costs always require the older person's explicit approval.

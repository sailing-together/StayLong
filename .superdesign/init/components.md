# Shared UI components

StayLong currently has no separately exported shared UI primitives. Buttons,
form fields, cards, the header, and the footer are implemented inline in
`frontend/src/App.tsx` and styled by `frontend/src/App.css`.

The redesign should keep the implementation lightweight, but the following
patterns are candidates for extraction after a direction is approved:

- Primary and secondary action buttons
- Progress step indicator
- Consent/approval notice
- Plan status card
- Timeline item


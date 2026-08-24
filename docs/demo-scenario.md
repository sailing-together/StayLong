# Demo-safe seeded household scenario

The canonical seeded scenario is [`fixtures/demo/seeded-household.json`](../fixtures/demo/seeded-household.json). It is deliberately synthetic and contains no real names, phone numbers, email addresses, addresses, government identifiers, credentials, clinical diagnoses or funding decisions.

## Demonstrated path

1. An older person living alone opens the Cloud Run UI and reports a bathroom-access concern.
2. The authenticated API records the concern against `demo-case-001`.
3. The intake boundary prepares non-clinical facts for an assessment pack.
4. The coordinator produces a durable **Home Independence Plan** with three practical tasks: arrange a My Aged Care assessment, prepare assessment notes, and confirm home access or permission.
5. The UI presents two independently approval-gated sandbox actions: a Calendar reminder and an unsent contact draft. Approve the Calendar action only; the contact draft remains pending and no message is sent.
6. Refresh or fetch the case again to show that the plan, completed Calendar result, still-pending contact draft and audit timeline are durable.

The scenario is intentionally non-emergency so the demo can show the normal Taskmaster workflow. Emergency text must use the deterministic Triple Zero route and must not be added to this fixture.

## Reset and safety

The fixture is a read-only seed input for local tests and demonstrations. It must not be used as a production household record. Reset by reloading the JSON fixture; never add real household data to this file.

## Visible demo proof points

- **Useful outcome:** three concrete Home Independence Plan tasks, not a chat transcript or a generic reminder.
- **Autonomy with consent:** the workflow prepares both next actions itself, but each action has a separate approval gate.
- **Honest integration state:** the sandbox label means no real calendar, provider or contact is used. With manually configured OAuth, the label changes to Google-connected actions; Gmail remains draft-only.
- **Safety:** the identical emergency wording routes to 000 and produces no plan or external actions.

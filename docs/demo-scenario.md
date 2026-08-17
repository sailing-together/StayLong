# Demo-safe seeded household scenario

The canonical seeded scenario is [`fixtures/demo/seeded-household.json`](../fixtures/demo/seeded-household.json). It is deliberately synthetic and contains no real names, phone numbers, email addresses, addresses, government identifiers, credentials, clinical diagnoses or funding decisions.

## Demonstrated path

1. An older person living alone opens the Cloud Run UI and reports a bathroom-access concern.
2. The authenticated API records the concern against `demo-case-001`.
3. The intake boundary prepares non-clinical facts for an assessment pack.
4. The coordinator proposes `prepare_assessment_pack` as a draft owned by the demo older person; a trusted supporter can be invited only after the person chooses to share a specific task.
5. The UI shows that external actions require human confirmation; no message, booking, application or payment is executed.
6. The audit/event path can be shown with synthetic IDs and a clear completion trail.

The scenario is intentionally non-emergency so the demo can show the normal Taskmaster workflow. Emergency text must use the deterministic Triple Zero route and must not be added to this fixture.

## Reset and safety

The fixture is a read-only seed input for local tests and demonstrations. It must not be used as a production household record. Reset by reloading the JSON fixture; never add real household data to this file.

# Task 4 report: Firestore-backed case state and events

## Scope and choices

- Added `CaseRepository` and `EventRepository` protocols with interchangeable
  in-memory and Firestore adapters.
- `InMemoryCaseRepository.create_concern` creates the existing immutable
  `Concern` record and keeps it scoped to its `case_id`.
- `InMemoryEventRepository.append_if_new` deduplicates by immutable `event_id`.
  `IdempotentEventProcessor` exposes the one-step processing boundary and
  returns whether processing inserted a new timeline event.
- Firestore persists concerns beneath `cases/{case_id}/concerns/{concern_id}`
  and events beneath `cases/{case_id}/events/{event_id}`. Event insertion uses
  Firestore's atomic document `create`, so repeated deliveries of the same
  event id return `False` rather than overwriting or appending another event.
- Both Firestore adapters accept an injected client for tests. Their imports of
  `google.cloud.firestore` are lazy and occur only when an adapter is created
  without a client. The local test environment therefore needs no cloud package,
  credentials, or network access.

No external tool execution, clinical decision-making, emergency-router changes,
credentials, or approval/action-intent behavior was introduced.

## TDD evidence

1. Wrote the initial in-memory concern/event tests before the service package
   existed. RED command:

   ```text
   .venv/bin/python -m pytest tests/services/test_cases.py tests/services/test_events.py
   3 failed: ModuleNotFoundError: No module named 'staylong.services'
   ```

2. Implemented the smallest in-memory repositories and processor. GREEN:

   ```text
   3 passed in 0.01s
   ```

3. Removed the untested Firestore-adapter draft, added Firestore contract tests
   using a minimal Firestore-shaped test double, and reran RED:

   ```text
   2 failed: cannot import name 'FirestoreCaseRepository' / 'FirestoreEventRepository'
   ```

4. Implemented the lazy Firestore adapters and atomic duplicate handling. GREEN:

   ```text
   5 passed in 0.01s
   ```

## Final verification

```text
.venv/bin/python -m pytest  -> 24 passed in 0.02s
.venv/bin/ruff check .      -> All checks passed!
git diff --check            -> exit 0 (no whitespace errors)
```

## Files

- `src/staylong/services/__init__.py`
- `src/staylong/services/cases.py`
- `src/staylong/services/events.py`
- `tests/services/fake_firestore.py`
- `tests/services/test_cases.py`
- `tests/services/test_events.py`

## Concerns and follow-up

- The Firestore adapters are intentionally unit-tested against a small client
  shape, not a real Firestore emulator. Deployment integration should add an
  emulator-backed test when infrastructure and cloud dependencies are in scope.
- Event ids are domain-generated UUIDs. Incoming integrations must preserve the
  original `event_id` on retries for the idempotency boundary to take effect.

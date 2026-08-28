# Private Google Calendar OAuth verification

This runbook is the release-candidate check for the optional, private Google
Calendar adapter. It is deliberately separate from the anonymous public
sandbox: the public sandbox must remain in `sandbox` integration mode and must
never receive a Google OAuth client or a user token.

## Preconditions

Use a dedicated Google test account and a throw-away calendar. In Google Cloud,
enable the Google Calendar API, configure the OAuth consent screen with that
account as a test user, and register the exact callback URL configured for the
private Cloud Run service. Do not use a personal production calendar.

The private service must be deployed with Terraform and all three non-secret
settings below. The client secret is read from Secret Manager; it is never a
Terraform variable, state value, log field, or repository file.

```text
STAYLONG_GOOGLE_OAUTH_CLIENT_ID
STAYLONG_GOOGLE_OAUTH_REDIRECT_URI
STAYLONG_GOOGLE_OAUTH_CLIENT_SECRET_ID
```

Grant the private runtime service account only the Secret Manager access needed
for that secret and the Firestore access needed for OAuth state/token records.
The Cloud Run service must be private, with the identity-aware access layer
supplying `X-Goog-Authenticated-User-Email`.

## Verification steps

1. Obtain a private-service identity token and application token using the
   existing operator procedure. Call
   `GET /v1/integrations/google/calendar/start` with both tokens and
   `X-Goog-Authenticated-User-Email: accounts.google.com:<test-account>`.
2. Open the returned `authorization_url`, approve only the
   `calendar.events` scope, and let Google redirect to the exact callback URL.
   Callbacks are one-time and bound to the authenticated account.
3. Confirm the callback response contains only `connected` and `expires_at`.
   It must not contain an access token or refresh token.
4. Create a non-emergency case and prepare its plan. Approve the proposed
   `calendar.create` action through
   `POST /v1/workflows/{case_id}/action-decision` with the same authenticated
   principal and the current `action_revision`.
5. Confirm the response records `channel=google_calendar` and a Google event
   ID, and verify exactly one event appears in the throw-away calendar. Repeat
   the request with the same revision and confirm no duplicate event is made.
6. Inspect Firestore and logs: OAuth state is consumed, no bearer or refresh
   token is present, and the audit entry contains the actor and event ID only.
7. Revoke the test account's grant in Google Account security. A subsequent
   approved action must fail safely with an actionable integration error and
   must not create a local success record.

Record the date, service revision, test account (hashed or redacted), event ID,
and screenshots of the Cloud Run revision and Calendar event in the private
release evidence file. Never put credentials, callback codes, or raw tokens in
the repository or the public submission.

## What CI does and does not do

CI runs the OAuth route, state-binding, token-redaction, approval-gate and
adapter contract tests with fakes. It does not sign into Google or create a
real event. The steps above require an operator-controlled test account and are
the only release gate for claiming a real Calendar integration in a demo.

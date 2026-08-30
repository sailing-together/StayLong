# Live Browser Acceptance Evidence (SAI-69)

This document records the end-to-end live browser acceptance pass executed against the public StayLong production deployment at [https://staylonghome.com](https://staylonghome.com) in fulfillment of **SAI-69** and **SAI-12**.

## Execution Overview

- **Target URL:** `https://staylonghome.com`
- **Execution Date:** 30 August 2026
- **Test Runner:** Playwright Chromium (Automated Live Browser Harness, `tools/live_browser_acceptance.mjs`)
- **Overall Status:** **PASSED** (0 uncaught browser console errors, 0 unhandled exceptions)

---

## Viewport Results & Timings

| Viewport | Dimensions | Emulation | Total Duration | HTTP Requests | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Desktop** | 1280 x 800 | Standard desktop browser | 17.7s | 3 (All 200/201) | **PASS** |
| **Mobile** | 375 x 667 | iPhone / Mobile Safari touch | 16.5s | 3 (All 200/201) | **PASS** |

### Step-by-Step Latency Breakdown

| Step | Desktop Latency | Mobile Latency | Outcome |
| :--- | :--- | :--- | :--- |
| 1. Landing Page Navigation & Load | 1,351 ms | 1,315 ms | HTTP 200, TLS Active |
| 2. Example Selection & Free-Text Edit | 57 ms | 53 ms | Instant local state update |
| 3. Plan Initiation (`/v1/public/workflows`) | 13,597 ms | 12,596 ms | HTTP 201 Created |
| 4. Safe Return to Concern & Navigation | 68 ms | 88 ms | State preserved safely |
| 5. Intake Submission (`/answers`) | 293 ms | 298 ms | HTTP 200 OK |
| 6. Action Deferral / "Not now" | 1,538 ms | 1,547 ms | Deferred card state verified |
| 7. Calendar Approval (`/action-decision`) | 355 ms | 362 ms | HTTP 200 OK |
| 8. Contact Draft Approval (`/action-decision`) | 360 ms | 358 ms | HTTP 200 OK |

---

## Acceptance Criteria Verification

- [x] **Full journey completes without unexplained errors:** Both Desktop and Mobile runs finished all 8 steps cleanly with 0 console errors.
- [x] **Zero real external side-effects:** Confirmed all action responses include `sandbox: true` and `delivery: draft_only`.
- [x] **Step 3 vs Step 4 differentiation:** Step 4 follow-through clearly renders the underway banner and completed cards.
- [x] **Tailored & concern-aware plan:** The Home Independence Plan, Assessment Preparation Pack, and contact draft are dynamically tailored by room and concern area.
- [x] **Draft preview & copy capability:** Unsent draft content is fully inspectable with subject, body, and one-click copy to clipboard.
- [x] **Meaningful action decline:** Declining an action transitions it to a clear deferred state with an option to reconsider anytime.
- [x] **Accessible & human-readable timeline:** Internal event types are mapped to clean plain-language audit labels.

---

## Evidence Artifacts

The complete set of step-by-step visual proofs is stored in `docs/evidence/browser-acceptance/`:

- `desktop_01_landing.png` — Landing page at 1280px width
- `desktop_02_concern_edited.png` — Example selected with customized free text
- `desktop_03_intake_questions.png` — Step 2 intake questionnaire
- `desktop_04_plan_prepared.png` — Step 3 Home Independence Plan and Preparation Pack
- `desktop_05_action_deferred.png` — Action deferral / Keep for later state
- `desktop_06_calendar_approved.png` — Step 4 follow-through with approved calendar action
- `desktop_07_draft_approved.png` — Approved contact draft with preview box
- `mobile_01_landing.png` through `mobile_07_draft_approved.png` — Mobile viewport equivalents
- `acceptance-summary.json` — Machine-readable run trace and HTTP timing metrics

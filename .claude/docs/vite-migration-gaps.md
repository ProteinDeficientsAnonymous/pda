# Vite Migration — Backend Endpoint Gap Plan

Tracks work to close gaps between the Django Ninja API and the React/Vite frontend, found in the 2026-04-19 audit.

## 🔴 Critical

### 1. "Delete" event → archive (PATCH to `status='cancelled'`)

Current: `useDeleteEvent` in `eventWrites.ts:231` calls `DELETE /api/community/events/{id}/` which does not exist on the backend (production 405).

Target: Archiving an event. Replace the DELETE with `PATCH /api/community/events/{id}/` with `{ status: 'cancelled' }` (reuses existing archive semantics — the only "destructive" path the backend exposes).

Touchpoints:
- `frontend/src/api/eventWrites.ts` — rewrite `useDeleteEvent` to PATCH status=cancelled
- `frontend/src/screens/events/EventAdminActions.tsx` — rename button/dialog copy from "delete event" to "archive event" / "cancel event" (match existing backend semantics)
- Tests: `frontend/src/screens/events/EventAdminActions.test.tsx` and any mock that asserted DELETE

### 2. `POST /surveys/view/{slug}/respond/` response type mismatch

Backend returns `SurveyResponseOut`; frontend `surveys.ts:132` decodes as `WireSurvey`.

Target: Align FE decode. Update `useSubmitSurvey` to decode as a `WireSurveyResponse` shape, then invalidate/refetch the public survey query to get the updated survey.

Touchpoints:
- `frontend/src/api/surveys.ts` — fix response type on `useSubmitSurvey`; ensure any `onSuccess` cache updates still work (invalidate instead of setQueryData if shapes don't match)
- `frontend/src/api/surveyMapper.ts` (or wherever `WireSurvey` lives) — add/confirm a `WireSurveyResponse` type matching backend `SurveyResponseOut`

## 🟠 Missing FE implementation

### 3. `POST /api/community/request-login-link/` — no FE caller

Build UI for requesting a new magic-login link. Flutter had this affordance on the login screen.

Target UX: On `LoginScreen.tsx`, add a "send me a login link" affordance (below the password field). Also consider reusing inside `MagicLoginScreen.tsx` on expired-token failures.

Touchpoints:
- `frontend/src/api/auth.ts` — add `useRequestLoginLink` mutation
- `frontend/src/screens/auth/LoginScreen.tsx` — add affordance
- `frontend/src/screens/auth/MagicLoginScreen.tsx` — surface on expired-token error
- Tests for the login screen if covered

### 4. Member profile screen

`GET /api/auth/users/{user_id}/profile/` returns `MemberProfileOut` (id, display_name, phone_number, email, bio, profile_photo_url, login_link_requested) but nothing calls it.

Target: A simple member-profile screen reachable from places that link to a user (event hosts, RSVP list, co-hosts, etc.). Route: `/members/:userId`. Respect existing privacy fields (`show_phone`, `show_email`) — backend already handles the gating, just render what comes back.

Touchpoints:
- `frontend/src/api/users.ts` (or new `memberProfile.ts`) — add `useMemberProfile(userId)`
- `frontend/src/screens/members/MemberProfileScreen.tsx` — new screen
- `frontend/src/router/*` — add route, lazy-load
- Wire links from event hosts/co-hosts/RSVP list/invited guests to `/members/:userId`

## 🟡 Cleanup / small wins

### 5. Remove `POST /api/auth/users/{user_id}/reset-password/` endpoint

We're using magic-link flow only; reset-password endpoint is a duplicate. Delete the backend route, schemas, tests, and the hook if one exists.

Touchpoints:
- `backend/users/_management.py` — remove endpoint + helper
- `backend/tests/**` — remove related tests
- Regenerate OpenAPI types (`make frontend-types`)

### 6. Drafts tab in "my events"

`GET /api/community/events/?status=draft|cancelled` is unused.

Target: In `MyEventsScreen`, add a tab row: `upcoming | past | drafts | cancelled`. Drafts fetches with `status=draft`; cancelled with `status=cancelled`. Upcoming/past stay as they are (active list, client-split by datetime).

Touchpoints:
- `frontend/src/api/events.ts` — accept optional `status` param in `useEvents`
- `frontend/src/screens/events/MyEventsScreen.tsx` — add tabs; switch query by tab
- Tests if covered

### 7. Error report — send full context

`POST /api/community/error-report/` accepts `context`, `user_agent`, `app_version`. FE currently only sends error/stack_trace/route/client_timestamp.

Target: Always send `user_agent` (from `navigator.userAgent`) and optional `context` (caller-supplied object). Skip `app_version` for now (no source).

Touchpoints:
- `frontend/src/utils/errorReporter.ts` — add `user_agent` always, optional `context` arg
- Callers passing extra context (e.g. `RootRouteError.tsx`)

### 8. Surface GitHub issue URL on feedback success

`POST /api/community/feedback/` returns `html_url`. FE discards it.

Target: In the feedback success toast, include a "view your issue" link using `html_url`.

Touchpoints:
- `frontend/src/api/feedback.ts` — return `html_url`
- `frontend/src/components/FeedbackButton.tsx` — render link in success toast

### 9. `notify_attendees` for event edits/cancels

`PATCH /events/{id}/` accepts `notify_attendees`; FE never sends it. Host cannot control whether attendees get a notification on cancel/edit. Right now: **nobody is ever notified on cancel or edit** because the default isn't being exercised from the FE.

Target: On edit save + archive flow, send `notify_attendees: true` by default (users expect to be pinged when a host cancels). Optional: add a checkbox "notify attendees" on the edit form for non-trivial edits.

Touchpoints:
- `frontend/src/api/eventWrites.ts` — `toWireBody` accepts `notifyAttendees`; include in PATCH
- `frontend/src/screens/events/EventAdminActions.tsx` — pass `notifyAttendees: true` on cancel
- `frontend/src/screens/events/form/**` — optional checkbox on edit form

## ✅ No-action confirmations (audit items we're explicitly not doing)

- **`TokenOut.refresh` ignored by FE** — correct. We use httpOnly cookie for refresh; the response-body field only existed for Flutter. Safe to keep in backend for backward compat or remove when Flutter is fully retired.
- **Quill Delta (`content` field) on docs/pages/guidelines/home** — correct. TipTap only; Delta fields can be dropped from the backend once the mobile app is gone.
- **`RSVPGuestOut.phone`, `EventFlagOut.reviewed_at`, poll `finalized_by_id`/`is_active`, survey `voters`/`user_id`/`response_count`/`created_by_id`** — mapped but not displayed. Leave alone for now; revisit per feature.
- **Doc folder rename/reorder/reparent (audit items 6–8)** — deferred.
- **Page visibility toggle (audit item 9)** — deferred.
- **`app_version` on error-report/feedback** — deferred (no source).

## Agent allocation

Each agent ≤5 files. Dependencies noted.

- **Agent A — Archive event (fixes #1, starts #9)**: `frontend/src/api/eventWrites.ts`, `frontend/src/screens/events/EventAdminActions.tsx`, `frontend/src/screens/events/EventAdminActions.test.tsx` (if exists; otherwise skip), plus test fixtures touching DELETE.
- **Agent B — Survey response type (fixes #2)**: `frontend/src/api/surveys.ts`, `frontend/src/api/surveyMapper.ts` (if exists — otherwise wherever WireSurvey lives), plus tests for `useSubmitSurvey`.
- **Agent C — Request-login-link (fixes #3)**: `frontend/src/api/auth.ts`, `frontend/src/screens/auth/LoginScreen.tsx`, `frontend/src/screens/auth/MagicLoginScreen.tsx`, related tests.
- **Agent D — Member profile screen (fixes #4)**: `frontend/src/api/users.ts` (or new `memberProfile.ts`), new `frontend/src/screens/members/MemberProfileScreen.tsx`, `frontend/src/router/*` (route wiring), 1–2 call-site hookups (EventMemberSection, RsvpGuestList). Max 5 files — pick highest-value linking sites first.
- **Agent E — Backend cleanup: remove reset-password (fixes #5)**: `backend/users/_management.py`, `backend/tests/**` (relevant test files). Regenerate OpenAPI after. Max 5 files.
- **Agent F — Drafts tab (fixes #6)**: `frontend/src/api/events.ts`, `frontend/src/screens/events/MyEventsScreen.tsx`, related tests.
- **Agent G — Error report + feedback polish (fixes #7, #8)**: `frontend/src/utils/errorReporter.ts`, `frontend/src/api/feedback.ts`, `frontend/src/components/FeedbackButton.tsx`, `frontend/src/screens/RootRouteError.tsx`.

Run A/B/C/D in parallel (independent FE surfaces). E is backend-only — also parallel. F/G parallel after those land (or sooner — no shared files).

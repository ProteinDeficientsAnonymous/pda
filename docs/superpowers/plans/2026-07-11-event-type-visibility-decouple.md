# Decouple event type from visibility (PR1) Implementation Plan

> **For agentic workers:** Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Separate `event_type` from `visibility` in the event form — move "official" out of the visibility dropdown into a permission-gated toggle under the title.

**Architecture:** Backend keeps the `official ⇒ public` invariant but generalizes the validator to a type-set so PR2 can add `club` trivially; removes the redundant `event_type == OFFICIAL` disjuncts from the two anonymous-exposure sites (behavior-preserving, since official is always public). Frontend drops the virtual `visibilityChoice` control and sends `event_type` + `visibility` as independent fields, with a new `EventFormType` toggle component under the title.

**Tech Stack:** Django Ninja, pytest; React + TypeScript, Vitest.

## Global Constraints

- Frontend user-facing text is **lowercase only**.
- Use shared enums/constants, not raw strings (`EventType.OFFICIAL`, `EventVisibility.Public`, `Permission.TagOfficialEvent`).
- No top-of-file banner comments.
- Commit from the worktree with `git -C <worktree> commit -F <file>` (no heredoc).
- Run cheap `make agent-*` steps while iterating; full `make agent-ci` once as pre-PR gate.

---

### Task 1: Backend — generalize the official-visibility validator + drop redundant anon-exposure disjuncts

**Files:**
- Modify: `backend/community/_events.py` (`_is_invalid_official_visibility` → `_is_invalid_typed_visibility`; anon-list filter line ~151; read-gate line ~248)
- Test: `backend/tests/test_event_visibility.py`

**Interfaces:**
- Produces: `_is_invalid_typed_visibility(event_type: str, visibility: str) -> bool` — True when `event_type` is a public-only type and `visibility != PUBLIC`. Public-only set is `{EventType.OFFICIAL}` in PR1.

- [ ] **Step 1:** Rename `_is_invalid_official_visibility` → `_is_invalid_typed_visibility`; body uses a module-level `_PUBLIC_ONLY_TYPES = {EventType.OFFICIAL}` frozenset and returns `event_type in _PUBLIC_ONLY_TYPES and visibility != PageVisibility.PUBLIC`. Update both call sites (create ~312, update ~95).
- [ ] **Step 2:** Anon-list filter (~151): change `qs.filter(Q(visibility=PUBLIC) | Q(event_type=OFFICIAL))` → `qs.filter(visibility=PageVisibility.PUBLIC)`.
- [ ] **Step 3:** Read-gate (~245-249): drop the `and event.event_type != EventType.OFFICIAL` clause so anon is blocked from any `members_only` event.
- [ ] **Step 4:** Run `make agent-test-since` — existing `TestOfficialEventVisibility` must stay green (official events are public, so exposure is unchanged).
- [ ] **Step 5:** Commit.

### Task 2: Frontend — send event_type + visibility as independent fields (drop visibilityChoice)

**Files:**
- Modify: `frontend/src/api/eventWrites.ts`
- Test: `frontend/src/api/eventWrites.test.ts` (if present) + `frontend/src/screens/events/form/validateEventForm.test.ts`

**Interfaces:**
- Produces: `EventFormValues` without `visibilityChoice`; `FIELD_TO_WIRE` includes `eventType → ['event_type', v]` and `visibility → ['visibility', v]`. `eventToFormValues` maps both directly.

- [ ] **Step 1:** Remove `VisibilityChoice` type, `visibilityChoiceToFields`, `fieldsToVisibilityChoice`, and the `visibilityChoice` field from `EventFormValues`.
- [ ] **Step 2:** Add `eventType`/`visibility` to `FIELD_TO_WIRE`; simplify `toWireBody`/`toPartialWireBody` to drop the `visibilityChoice` special-case.
- [ ] **Step 3:** Update `emptyEventFormValues` (drop `visibilityChoice`) and `eventToFormValues` (drop the `fieldsToVisibilityChoice` call).
- [ ] **Step 4:** `make agent-frontend-typecheck` — expect errors in `EventFormDetails.tsx`, `EventForm.tsx` referencing `visibilityChoice`; fixed in Tasks 3–4.
- [ ] **Step 5:** Commit after Tasks 3–4 make it compile (or commit here if isolated).

### Task 3: Frontend — new EventFormType toggle component

**Files:**
- Create: `frontend/src/screens/events/form/EventFormType.tsx`

**Interfaces:**
- Produces: `EventFormType({ values, onChange, canTagOfficial })` — renders a `Toggle` "make it an official pda event" when `canTagOfficial`. On check → `onChange({ eventType: 'official', visibility: 'public' })`; on uncheck → `onChange({ eventType: 'community' })`. Renders nothing if `!canTagOfficial`.

- [ ] **Step 1:** Write the component using the existing `Toggle` (see `EventFormBasics` usage) and `EventType`/`EventVisibility` enums.
- [ ] **Step 2:** `make agent-frontend-typecheck`.
- [ ] **Step 3:** Commit (with Task 4).

### Task 4: Frontend — wire toggle into form + de-conflate visibility dropdown

**Files:**
- Modify: `frontend/src/screens/events/form/EventFormBasics.tsx` (render `<EventFormType>` under title; accept `canTagOfficial` prop)
- Modify: `frontend/src/screens/events/form/EventFormDetails.tsx` (drop "official" option; lock select when type is public-only)
- Modify: `frontend/src/screens/events/form/EventForm.tsx` (pass `canTagOfficial` to `EventFormBasics`; drop `visibilityChoice` from `DETAILS_FIELDS`)
- Modify: `frontend/src/models/event.test.ts` if it references `visibilityChoice`

**Interfaces:**
- Consumes: `EventFormType` from Task 3; independent `eventType`/`visibility` from Task 2.

- [ ] **Step 1:** `EventFormDetails`: remove the `official` entry from `VISIBILITY_OPTIONS` and `VISIBILITY_HELPER`; the select `onChange` sets `visibility` directly (`eventType` no longer touched here). Add a `typeLocked: boolean` prop; when true, disable the select and show hint "official events are always public".
- [ ] **Step 2:** `EventFormBasics`: accept `canTagOfficial`; render `<EventFormType values onChange canTagOfficial />` directly under the title `TextField`.
- [ ] **Step 3:** `EventForm`: pass `canTagOfficial` to `EventFormBasics`; pass `typeLocked={values.eventType === 'official'}` to `EventFormDetails`; remove `'visibilityChoice'` from `DETAILS_FIELDS`.
- [ ] **Step 4:** `make agent-frontend-typecheck` + `make agent-frontend-test`.
- [ ] **Step 5:** Commit.

### Task 5: Verify + pre-PR gate

- [ ] **Step 1:** `make agent-ci` + `make agent-frontend-lint` + `make agent-frontend-test`.
- [ ] **Step 2:** Drive the form in the browser (create + edit) to confirm the toggle forces/locks public and the dropdown no longer lists "official".
- [ ] **Step 3:** Open draft PR.

## Self-Review

- Spec coverage: type/visibility separation (Tasks 2–4), official toggle under title (Tasks 3–4), anon-exposure cleanup (Task 1), keep official public-only (Task 1). ✓
- No `club` here — deferred to PR2 per spec. ✓
- Type consistency: `_is_invalid_typed_visibility` used in Task 1 create+update; `EventFormType` signature stable across Tasks 3–4. ✓

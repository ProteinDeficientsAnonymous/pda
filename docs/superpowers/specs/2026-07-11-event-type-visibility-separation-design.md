# Separate event type from visibility + add `club` type — Design

**Date:** 2026-07-11
**Related exploration:** `docs/superpowers/specs/2026-07-10-event-type-visibility-taxonomy-explore.md` (PR #659, issue #604)
**Issue:** #604 (taxonomy separation)

## Problem

`event_type` (community / official) and `visibility` (public / members-only / invite-only) are collapsed into a single frontend dropdown ("who can see it"). Picking **official** secretly sets `event_type=official, visibility=public`. Event planners are confused because "official" masquerades as a visibility option when it is really a *type*.

## Goal

Fully separate the two axes:

- **`event_type`** — community / official / **club** (single value, mutually exclusive). Set by permission-gated **toggles under the title**, styled like the existing "date & time tbd" toggle.
- **`visibility`** — public / members-only / invite-only. Its own dropdown; the fake "official" option is removed.

Official and club are **public-only** (validated) and **mutually exclusive** (radio-like toggles). Turning either on **forces + locks** the visibility dropdown to public.

## Decisions (locked)

| Decision | Choice |
|---|---|
| Type model | Single `event_type` with 3 values (community / official / club). Toggles are mutually exclusive. |
| Visibility coupling | Official/club stay **public-only** — validated (`event_type in (official, club) ⇒ public`). |
| Toggle → visibility | Turning a type toggle on forces visibility to public **and disables** the visibility select (hint: "official events are always public"). |
| Dual-permission users | Two toggles, radio-like: turning one on turns the other off. Default = neither (community). |
| PR split | Two PRs / two worktrees. PR2 branches off PR1. |
| Club color | Rose/magenta family — distinct hue + luminance from teal/amber/lavender/blue; CVD-safe. |
| Anon-list/read-gate cleanup | Drop redundant `event_type == OFFICIAL` disjuncts (behavior-preserving; official is public-only). Included in PR1. |

## PR 1 — decouple type from visibility + "make official" toggle

No model/migration change (`official`/`community` already exist).

### Backend (`backend/community/`)

- **`_events.py`** — rename `_is_invalid_official_visibility` → `_is_invalid_typed_visibility(event_type, visibility)`; predicate becomes `event_type in {OFFICIAL} and visibility != PUBLIC` (a set, so PR2 adds `CLUB` with a one-line change). Keep the `OFFICIAL_MUST_BE_PUBLIC` error code (message copy can stay).
- **`_events.py:151`** anon-list filter — drop the `Q(event_type=EventType.OFFICIAL)` disjunct; keep `Q(visibility=PUBLIC)`. Official is public-only so it already matches. Removes the latent coupling flagged in the exploration.
- **`_events.py:248`** read-gate — drop the `event.event_type != EventType.OFFICIAL` clause; a `members_only` event is hidden from anon regardless of type (official is never members-only, so no behavior change).
- Official permission gate on create/update is unchanged.

### Frontend (`frontend/src/`)

- **`api/eventWrites.ts`** — remove `VisibilityChoice`, `visibilityChoiceToFields`, `fieldsToVisibilityChoice`, and the `visibilityChoice` field on `EventFormValues`. Send `event_type` + `visibility` as independent wire fields (add `eventType`/`visibility` to `FIELD_TO_WIRE`). `eventToFormValues` maps the two fields directly.
- **`screens/events/form/EventFormDetails.tsx`** — visibility `Select` loses the "official" option; de-conflate helper copy (public helper stays, official helper removed).
- **New `screens/events/form/EventFormType.tsx`** — rendered in `EventFormBasics` directly under the title `TextField`. Renders a "make it an official pda event" `Toggle` when `canTagOfficial`. On → `eventType='official'`, `visibility='public'`; disables the visibility select via a new `typeLocksVisibility` signal passed to `EventFormDetails`.
- **`screens/events/form/EventForm.tsx`** — pass `canTagOfficial` down to the new type section; thread the lock state.

### Tests

- FE: `models/event.test.ts` (eventClass unchanged for official), `form/validateEventForm.test.ts`, new coverage for toggle → forced-public.
- BE: `tests/test_event_visibility.py::TestOfficialEventVisibility` stays green; add a test that official + members_only is rejected via the renamed helper, and that the anon-list/read-gate simplification preserves visibility for official events.

## PR 2 — `tag_club_event` permission + `club` type + "make club" toggle

Branches off PR1.

### Backend

- **`users/permissions.py`** — `TAG_CLUB_EVENT = "tag_club_event", "Tag club event"`.
- **`community/models/choices.py`** — `EventType.CLUB = "club", "Club"`.
- **Migration** — alter `event_type` choices to include `club` (choices-only; no data change).
- **`_events.py`** — add `CLUB` to the typed-visibility set; add a permission gate on create/update: `event_type == CLUB` requires `TAG_CLUB_EVENT` (mirror the official gate, same 403 shape). Anon-list/read-gate already correct (club is public-only ⇒ matches public filter).

### Frontend

- **`models/permissions.ts`** — `TagClubEvent: 'tag_club_event'` mirror.
- **`screens/admin/RoleFormDialog.tsx`** — `PERMISSION_LABELS[Permission.TagClubEvent] = 'tag club events'` (per standing rule: missing = silently ungrantable).
- **`models/event.ts`** — `EventType.Club = 'club'`; `eventClass` returns `pda-evt-club` for club.
- **`utils/eventColors.ts`** — add `clubLight` (`{ bg: '#F5D0E0', fg: '#5C1A3A' }`) / `clubDark` (`{ bg: '#3D1028', fg: '#F0B0D0' }`) rose/magenta; verify under CVD simulator before finalizing. `getEventColors` returns club colors when `eventType === 'club'`.
- **`index.css`** — `--color-evt-club-bg/-fg` vars (light + dark) + `.pda-evt-club` / `.rbc-event.pda-evt-club` rules, mirroring `.pda-evt-official`.
- **`screens/events/EventDetailScreen.tsx`** — club badge.
- **`screens/admin/EventManagementScreen.tsx`** — club chip.
- **`screens/calendar/AgendaList.tsx`** — "pda club" filter option.
- **`screens/events/form/EventFormType.tsx`** — second toggle "make it a pda club event" when `canTagClub`. Radio-like: turning on club turns off official (and vice versa); both force+lock visibility to public.

### Tests

- BE: club requires `tag_club_event` (403 without), club + non-public rejected, club visible to anon in list.
- FE: club badge/color/filter; mutual-exclusion toggle logic; `permissions.test.ts` club key.

## Worktrees

Both off latest `origin/main`. PR2 branches off PR1's branch (needs PR1's decoupling). PR body for PR2 notes the dependency. Draft PRs.

## Out of scope

- Splitting the shared `PageVisibility` enum into an event-specific enum (exploration Phase 2) — not required for this separation and left for a later change.
- Migrating `event_type` to an `is_official` boolean (exploration Option B) — rejected; club makes a multi-valued type axis the right model.

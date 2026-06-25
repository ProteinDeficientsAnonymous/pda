# Explore: audit current event UI for UX improvement opportunities (#546) — Findings

**Date:** 2026-06-25
**Issue:** https://github.com/ProteinDeficientsAnonymous/pda/issues/546
**Branch / PR:** `auto-546-explore-event-ui` (draft PR linked below)

## The ask

This is part of epic #545 — events UI improvements + attendance + RSVP cleanup.
Before redesigning the event UI, we need a clear picture of what exists today:
which screens exist, what information they show, what interactions are available,
and where the friction is. The deliverable is a prioritized, file-cited findings
doc so the implementation issue(s) can be filed with concrete scope.

This is **investigation only** — no application code is changed.

## What we found

The event experience spans five surfaces, each with a clear owner in the codebase.
Overall the implementation is mature and consistent: the lowercase-text tone
convention is followed almost everywhere, accessibility is generally considered
(ARIA roles on calendar grids, `role="alert"` on errors, `aria-pressed` on RSVP
pills), and files are mostly within the 300-line target. The pain points are
concentrated in **conceptual clarity** (RSVP vs. attendance), **information
surfacing** (data that exists in the model but never reaches the user), and a few
**accessibility/colour gaps**.

### 1. Public browsing — calendar & lists

`CalendarScreen.tsx` (274 lines) drives four views — month, week, day, list —
switched via a segmented `ViewSwitcher`. It uses react-big-calendar for the grid
views and custom card-based components for day/agenda. Responsiveness splits at
720px between `NarrowWeekView` (stacked day rows) and `WideWeekView` (7-column
grid that measures its container to decide how many event chips fit).

Event cards show title, date/time, and location only. Notably **none of the
browsing views surface RSVP status (`myRsvp`), attendance count
(`attendingCount`/`maxAttendees`), or capacity** even though all three are on the
`Event` type — so a user cannot tell at a glance which events they're going to or
which are full. Filtering is limited to an event-type toggle (official/community)
that **only exists in the agenda/list view**; there is no search, date-jump, or
location filter. `NarrowWeekView` hard-caps at two event chips per day
(`MAX_CHIPS_PER_DAY = 2`, NarrowWeekView.tsx:62) with a "+N more" overflow that
requires switching to day view to expand.

### 2. Event detail

`EventDetailScreen.tsx` (153 lines) is a clean orchestrator: photo, title +
visibility badges, datetime (hidden while a poll is active), add-to-calendar/share
actions, an optional datetime-poll card, the description, and then either a
`LoginOrJoinSection` (logged-out) or `EventMemberSection` (authed). Public vs.
member-gated content is enforced **server-side** — the backend blanks
location/links/cost/RSVP fields for unauthed users — and the logged-out card
explains "location, rsvp, and organizer details are shown once you sign in."

`EventMemberSection.tsx` is the structural hotspot: **479 lines** (just under the
500-line hard limit) packing hosts, location, links, cost, RSVP, invite, comments,
host-only attendance, admin actions, and the flag button into one file. It's both
a file-size risk and a cognitive-load problem — non-hosts still scroll past
sections that don't apply to them.

The poll, comments (threaded, with a 6-emoji reaction bar and a 500-char composer),
co-host invite banner, and flag dialog are all well-built with proper loading/
empty/error states.

### 3. RSVP & attendance — the epic's core concern

This is where "RSVP cleanup" originates. There are **two parallel participation
systems sharing one backend `EventRSVP` row**:

- **RSVP** (`RsvpSection.tsx`, member-facing): three pills — "i'm going" / "maybe"
  / "can't go" — plus an optional +1 and automatic waitlisting at capacity.
- **Attendance** (`EventAttendancePanel.tsx`, host-only): per-guest
  attended/no-show/unknown marks recorded at check-in (opens 1h before start).

The friction:

- **No member-facing feedback loop for attendance.** A member RSVPs "going," the
  host marks them "no-show," and the member never sees that mark. The same
  `EventRSVP` row now carries both *intent* (status) and *reality* (attendance)
  with no shared UI.
- **Waitlist is a lossy state.** Once waitlisted, the +1 toggle is disabled
  (`if (!myRsvp || onWaitlist) return`, RsvpSection.tsx:61) and the maybe/can't
  pills are hidden — to adjust a +1 you must leave the waitlist entirely.
- **Cancellation lead-time is inferred**, not tracked — derived from `updated_at`
  of current `can't go` rows, so flip-flops and the original RSVP time are lost.
- **Check-in only lists "going" guests**, so a "maybe" who actually showed can't be
  marked attended.
- The attendance panel is **collapsed by default and only appears when RSVP is
  enabled** (`canSeeInvited && event.rsvpEnabled`, EventMemberSection.tsx:71),
  making host check-in hard to discover.

### 4. Admin / host management — create, edit, admin actions

`EventForm.tsx` (347 lines) is a photo-first form with always-visible basics
(title, TBD toggle, start/end, location) and collapsible sections (hosts, details,
RSVP, links, money) that show summary badges and force open on validation error.
`EventAdminActions.tsx` gates edit/publish/cancel/delete by creator/co-host/
`manage_events` permission. Two notable behaviours:

- **Co-host picker starts empty on edit** because the wire payload carries no phone
  numbers to reconstruct `MemberSearchResult`; the form omits `coHostIds` unless
  the picker is touched (`coHostsDirty`, EventForm.tsx:99/171). Safe, but a host
  sees "0 people" and may think co-hosts were dropped.
- **Edit closes 6h after the event** (`EDIT_GRACE_MS`, EventAdminActions.tsx:220)
  with no explanation surfaced to the user.

Validation is submit-time only (no on-blur feedback), and a failed photo upload
after create is swallowed silently (no toast).

### 5. Data, routes & navigation

The `Event` type (`models/event.ts`, 165 lines) mirrors the backend
`community/models/event.py` closely. Routes: `/calendar`, `/events/:id`
(both public), `/events/mine`, `/events/add`, `/events/:id/edit` (auth),
`/events/manage`, `/admin/flagged-events` (permission-gated). Navigation to events
is **only** via the BottomNav (calendar icon, "my events" star, "+" add) — the
header menu surfaces no event shortcuts, so `/events/mine` relies entirely on the
star tab being noticed.

Structural gaps worth flagging for the redesign:

- **Parallel arrays** (`coHostIds`/`Names`/`PhotoUrls`,
  `invitedUserIds`/`Names`/`PhotoUrls`) with no programmatic alignment check — a
  backend mismatch silently breaks the UI.
- **List vs. detail asymmetry**: the list endpoint omits `guests`, `myRsvp`,
  invited users, and pending co-host invites, handled by `setQueryData` cache
  merges that are fragile if the list shape changes.
- **`invite_permission` exists** on the model but is not surfaced/labelled in the
  UI; **invitations are set-union only** (add, never remove) — there is no
  un-invite UI.

## Relevant code

| Area | Location | Role |
|---|---|---|
| Calendar controller | `frontend/src/screens/calendar/CalendarScreen.tsx:1` | 4-view switcher, date nav, event fetch (274 lines) |
| Narrow week view | `frontend/src/screens/calendar/NarrowWeekView.tsx:62` | `MAX_CHIPS_PER_DAY = 2` truncation |
| Agenda/list view | `frontend/src/screens/calendar/AgendaList.tsx:1` | only place the type filter lives |
| "My events" | `frontend/src/screens/events/MyEventsScreen.tsx:1` | member event list; reached only via BottomNav star |
| Detail orchestrator | `frontend/src/screens/events/EventDetailScreen.tsx:1` | public + member section composition (153 lines) |
| Member section (hotspot) | `frontend/src/screens/events/EventMemberSection.tsx:1` | **479-line** monolith; attendance gate at `:71` |
| RSVP control | `frontend/src/screens/events/RsvpSection.tsx:61` | pills, +1 toggle, waitlist guard |
| Attendance panel | `frontend/src/screens/events/EventAttendancePanel.tsx:1` | host-only check-in + cancellations (250 lines) |
| Guest list | `frontend/src/screens/events/RsvpGuestList.tsx:1` | tabbed by status; counts include +1s |
| Event form | `frontend/src/screens/events/form/EventForm.tsx:99` | `coHostsDirty` empty-picker behaviour |
| Admin actions | `frontend/src/screens/events/EventAdminActions.tsx:125` | red-only delete/error styling; `EDIT_GRACE_MS` at `:220` |
| Comments | `frontend/src/screens/events/comments/` | threaded comments, reactions, composer |
| Datetime poll | `frontend/src/screens/events/poll/` | poll card, option strip, voter popover |
| Event type | `frontend/src/models/event.ts:1` | `Event`, `EventGuest`, `AttendanceStatus` (`:43`) |
| Read hooks | `frontend/src/api/events.ts:1` | `useEvents`, `useEvent` |
| RSVP/attendance hooks | `frontend/src/api/rsvp.ts:1`, `frontend/src/api/eventStats.ts:1` | RSVP + host stats/attendance |
| Routes | `frontend/src/router/routes.tsx:102` | all event routes + guards |
| Navigation | `frontend/src/layout/BottomNav.tsx:34` | only entry point to events |
| Backend model | `backend/community/models/event.py:1` | `Event`, `EventRSVP`, `EventFlag` |

## Prioritized UX pain points

Grouped by theme; **P0** = address in the redesign, **P1** = high-value,
**P2** = polish.

### Theme A — RSVP/attendance clarity (the epic's core)
- **(P0)** Unify or visibly link RSVP and attendance so members get post-event
  feedback; today attendance is host-only and invisible to the attendee.
  *(RsvpSection.tsx, EventAttendancePanel.tsx, `EventGuest.attendance`)*
- **(P1)** Waitlist is a dead-end for +1 changes — allow +1 adjustment while
  waitlisted, or explain the constraint. *(RsvpSection.tsx:61)*
- **(P1)** Make host check-in discoverable — the attendance panel is collapsed and
  hidden unless RSVP is enabled. *(EventMemberSection.tsx:71)*
- **(P1)** Check-in lists only "going" guests; a "maybe" who attended can't be
  marked. *(EventAttendancePanel.tsx)*
- **(P2)** Cancellation lead-time is inferred from `updated_at` — note the
  imprecision in-UI, or track it properly. *(eventStats.ts, EventAttendancePanel.tsx)*

### Theme B — information surfacing in browsing
- **(P1)** Surface RSVP status and capacity on calendar/list cards — `myRsvp`,
  `attendingCount`, `maxAttendees` all exist but never appear in browsing views.
  *(CalendarScreen, AgendaList, DayEventList, week views)*
- **(P1)** Add search / keyword filtering — no way to find an event by name on a
  busy calendar. *(CalendarScreen toolbar)*
- **(P2)** Make the type filter global rather than agenda-only. *(AgendaList.tsx)*
- **(P2)** Raise the 2-chip-per-day cap in `NarrowWeekView` or make the row
  scrollable. *(NarrowWeekView.tsx:62)*
- **(P2)** Add a jump-to-date picker; chevron-only nav is slow for far dates.

### Theme C — accessibility & colour
- **(P1)** `EventAdminActions` uses red-only styling for the delete button and
  error text (`border-red-300 text-red-700`, `text-red-600` at lines 125/132/150/188).
  Errors already carry `role="alert"`, but the delete affordance and error text
  lean on hue alone — pair with an icon/label for colour-blind safety.
  *(EventAdminActions.tsx:125)*
- **(P2)** Comment author names are lowercased via `toLowerCase()` at render,
  mangling proper nouns — prefer CSS `text-transform` to preserve semantics.
  *(comments/CommentItem)*

### Theme D — form & management UX
- **(P1)** Co-host picker shows "0 people" on edit despite existing co-hosts —
  render existing co-hosts read-only above the picker, or pre-hydrate them.
  *(EventForm.tsx:99/171)*
- **(P2)** Explain the 6-hour edit window instead of silently hiding the edit
  button. *(EventAdminActions.tsx:220)*
- **(P2)** Surface failed photo uploads with a toast; currently swallowed.
  *(EventForm.tsx)*
- **(P2)** Add on-blur validation for date fields rather than submit-only.
  *(EventForm.tsx)*

### Theme E — structure / maintainability (enabling work for the redesign)
- **(P1)** Split `EventMemberSection.tsx` (479 lines) into sibling section files
  (HostSection, LocationSection, LinksSection, CostSection, …) before layering new
  UI on top — it's at the size limit and mixes unrelated concerns.
  *(EventMemberSection.tsx)*
- **(P2)** Add an un-invite UI / decide the invite model — invitations are
  currently add-only (set-union) and `invite_permission` is unlabelled.
  *(_event_invitations, EventForm)*

## Recommendation

**Investigation complete — recommend filing the implementation work as a small set
of scoped issues under epic #545, sequenced as:**

1. **RSVP/attendance model cleanup (P0/P1, Theme A)** — the epic's named goal and
   the highest-impact clarity win. Decide whether attendance becomes member-visible
   and how waitlist/+1 transitions behave before any visual redesign, since this
   shapes the data the UI must show.
2. **`EventMemberSection` split (P1, Theme E)** — a low-risk enabling refactor
   (follows the repo's STEP 0 / file-size rules) that should land before new detail
   UI is added.
3. **Browsing information surfacing + search (P1, Theme B)** — high visible value,
   largely additive, uses data already on the `Event` type.
4. **Accessibility colour fixes (P1, Theme C)** — small, can ship independently.
5. **Form/management polish (Theme D)** — bundle the co-host-on-edit fix and edit
   smaller items.

No change is recommended from this spike itself; it is scoping input for #545.

## Open questions

Since this skill never asks the user, the following decisions are recorded for the
implementation issues to resolve:

1. **RSVP vs. attendance — unify or keep separate?** Should attendance become a
   member-visible continuation of RSVP ("going → attended/no-show"), or remain a
   private host record? This is the central product question behind "RSVP cleanup"
   and determines most of Theme A.
2. **Should the public calendar show capacity/RSVP-status to logged-out users, or
   only to members?** The data is member-gated server-side today; surfacing it on
   cards needs a privacy decision.
3. **Waitlist +1 behaviour** — is disabling +1 on the waitlist intentional
   (capacity-protection) or an oversight to fix?
4. **Invitation model** — is add-only (set-union, no un-invite) the intended
   design, or should hosts be able to rescind invitations from the UI?
5. **Scope of the redesign** — is #545 a full visual redesign, or targeted UX fixes
   on the existing layout? The recommended sequencing assumes the latter (additive,
   incremental); a ground-up redesign would reorder the work.
6. **Edit window** — is the 6-hour post-event edit cutoff a product rule to keep
   (and explain) or to revisit?

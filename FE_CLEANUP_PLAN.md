# Issue #218 — Frontend Cleanup Plan

## Overview

This document breaks down the items from issue #218 into discrete subtasks, grouped by session. Each session is self-contained and can be worked independently.

---

## Codebase Map (for reference)

| File | Purpose |
|------|---------|
| `frontend/lib/screens/calendar_screen.dart` (222 lines) | Calendar screen + toolbar + "today" button |
| `frontend/lib/screens/calendar/month_view.dart` (229 lines) | Month grid, "+N more" overflow logic |
| `frontend/lib/screens/calendar/event_detail_panel.dart` (301 lines) | `EventDetailContent` — top-level event detail layout |
| `frontend/lib/screens/calendar/event_member_section.dart` (231 lines) | Auth-gated member section: hosts, invite, links, RSVP |
| `frontend/lib/screens/calendar/rsvp_section.dart` (241 lines) | RSVP buttons + `RsvpGuestList` |
| `frontend/lib/screens/calendar/rsvp_guest_list.dart` (122 lines) | Guest list grouped by RSVP status, expand/collapse |
| `frontend/lib/screens/calendar/event_form_dialog.dart` (1161 lines) | The main create/edit event form — very large |
| `frontend/lib/screens/calendar/event_detail_widgets.dart` (225 lines) | `EventDetailHostChip`, `EventDetailRow`, `EventLinkRow`, etc. |
| `frontend/lib/screens/calendar/live_poll_editor.dart` (148 lines) | Inline poll editor shown when editing an event with an open poll |
| `frontend/lib/screens/calendar/co_host_picker.dart` (179 lines) | Co-host + invite member search/picker |
| `frontend/lib/widgets/embedded_event_poll.dart` (296 lines) | Embedded poll shown in event detail "when" card |
| `frontend/lib/router/app_router.dart` (308 lines) | GoRouter config; `/events/:id` is a flat top-level route |
| `frontend/lib/models/event.dart` (61 lines) | Freezed `Event` model |
| `frontend/lib/config/constants.dart` (74 lines) | `EventType`, `RsvpStatus`, `PageVisibility`, etc. |
| `backend/community/models/event.py` (93 lines) | `Event` + `EventRSVP` Django models |
| `backend/community/_events.py` (314 lines) | Event CRUD API endpoints |
| `backend/community/_event_schemas.py` (137 lines) | Pydantic schemas for events |
| `backend/community/models/poll.py` (96 lines) | `EventPoll`, `PollOption`, `PollVote` models |
| `backend/community/_polls.py` (329 lines) | Poll CRUD endpoints |

---

## Session 1 — Quick Text / Copy Fixes

**Scope:** 2–3 files, pure UI copy changes. No logic.

### 1a. "members only" → "pda members only"

- **File:** `frontend/lib/screens/calendar/event_detail_panel.dart` (~line 162–185)
- **Change:** The badge chip text that reads `'members only'` should become `'pda members only'`
- **How to find it:** Search for `'members only'` in that file

### 1b. Fix "set by poll" display

- **Context:** In `event_form_dialog.dart`, around lines 362–451 (`_buildWhenSection`), when a poll has been finalized (`datetimeTbd == false` but the poll still exists), the UI shows a "set by poll" badge (check icon + green text). The issue is: after the user manually changes the date, it still shows "set by poll" because the badge is tied to `hasPoll` rather than whether the date was actually set from the poll.
- **File:** `frontend/lib/screens/calendar/event_form_dialog.dart` — `_buildWhenSection` method
- **Fix:** Track a local `_dateSetByPoll` bool in state. Set it to `true` only when a poll is finalized and the winning datetime is loaded. Set it to `false` when the user manually edits the date/time pickers after the fact. Show the "set by poll" badge only when `_dateSetByPoll == true`.
- **Open question from issue:** "should you still be able to poll users again even if there was a poll before that you chose a date from?" — The recommended approach: if there is no currently **open** (active, non-finalized) poll, always show the "add a poll" button so the creator can start a new one. Finalized polls do not block re-polling.

### 1c. Remove duplicate `_buildCostSection` call

- **File:** `frontend/lib/screens/calendar/event_form_dialog.dart` — around lines 1091–1097
- **Bug:** `_buildCostSection(theme)` is called **twice** in the `build` method (once at ~1091, once at ~1095), separated by a `Divider`. Remove the duplicate call and the stray `Divider`.

---

## Session 2 — Layout Fixes (RSVP + Overflow)

**Scope:** 3 files. Pure layout/UI, no backend changes.

### 2a. RSVP buttons — single line

- **File:** `frontend/lib/screens/calendar/rsvp_section.dart`
- **Current:** Three `_RsvpToggleButton` widgets in a `Wrap` (lines 125–161). Each button has `padding: EdgeInsets.symmetric(horizontal: 16, vertical: 12)` and font size 14. The `Wrap` causes them to break to a second line on narrow screens.
- **Fix:** Replace the `Wrap` with a `Row` using `Expanded` (or `Flexible`) children so all three buttons always fit on one line. Reduce padding if needed (e.g., `horizontal: 10, vertical: 8`). Keep the `_RsvpToggleButton` internal structure the same.

### 2b. Month view "+N more" overflow

- **File:** `frontend/lib/screens/calendar/month_view.dart`
- **Current:** The space for "+N more" text is hard-coded as a `- 16` pixel reservation in `_buildGrid` (lines 203–206). This can overflow on small screens or when 6 weeks appear in the month.
- **Fix:** The `- 16` is probably fine for the text itself, but `availableForChips` can go negative on very short rows, and `clamp(1, _maxEventRows)` forces at least 1 chip even when there is no room. Fix: only show events (and the "+N more" row) when `availableForChips > 0`. If `fittableRows == 0`, show just the day number and a compact dot/overflow indicator instead of trying to render chips.
- **Also:** Check if `MonthRow` (in `month_row.dart`) clips or overflows. If `MonthRow` itself has overflow issues with the "+1" text, read that file and fix there.

---

## Session 3 — Event Detail Reorganization

**Scope:** 2–3 files. Reordering sections, UI structural changes.

### 3a. Move co-hosts to top of member section (under title)

- **File:** `frontend/lib/screens/calendar/event_member_section.dart`
- **Current order in authenticated view (lines 181–224):** co-hosts → invited → details → RSVP → admin actions
- **Requested order:** The issue says "move co-hosts up to the top under title." Currently co-hosts are already first in `EventMemberSection`. The likely intent is to move co-hosts **up into `EventDetailContent`** (in `event_detail_panel.dart`), rendering them directly below the title/badges instead of behind the member section gate. If co-hosts are public info, this makes sense.
- **Decision needed:** Are co-host names public (visible to unauthenticated users)? If yes, move the co-host display to `event_detail_panel.dart`, above `EventMemberSection`. If no, keep them in the member section but ensure they are the very first card.
- **Files:** `event_detail_panel.dart` and `event_member_section.dart`

### 3b. Move invite list to event details

- **Context:** Currently `event_member_section.dart` renders an "invited" section card (lines 194–199) as a standalone card between co-hosts and details. The issue requests moving the invite list into the "details" card.
- **File:** `frontend/lib/screens/calendar/event_member_section.dart`
- **Fix:** Remove the standalone "invited" `EventSectionCard`. Instead, add the invited user list as a row inside the "details" `EventSectionCard`, after location and links.

### 3c. Links section: hide by default, show "add links" affordance

- **Context:** The issue says "maybe hide links section and say add links (matching cost)." Currently the details card always shows the link rows (WhatsApp, Partiful, other link). For events with no links, this creates empty space.
- **File:** `frontend/lib/screens/calendar/event_member_section.dart`
- **Fix:** If all link fields are empty, collapse the links row and show nothing (or a subtle "no links" placeholder). This is view-only behavior; in the form, links are already optional fields.

---

## Session 4 — Event Form Improvements

**Scope:** `event_form_dialog.dart` (1161 lines — very large, handle carefully). Read in chunks.

### 4a. Date/time pickers: dismiss on click outside

- **Context:** The issue asks if date and time pickers can be closed by clicking outside. Currently they likely use `showDialog` which defaults to `barrierDismissible: true`, but the custom `showDateTimePicker` in `widgets/date_time_picker_dialog.dart` may override this.
- **Files:** `frontend/lib/widgets/date_time_picker_dialog.dart` and `frontend/lib/widgets/date_time_picker.dart`
- **Fix:** Ensure `showDialog(barrierDismissible: true)` is set. If a custom modal sheet is used instead, add a `GestureDetector` wrapping the barrier or use `barrierDismissible`.

### 4b. Add "flexible time" option

- **Context:** Issue says "maybe add an option to make time flexible?" This would allow an event to have a loose time or no specific time. Could be a simple checkbox/toggle "time is flexible" that, when checked, hides exact time pickers and shows a freeform text field (e.g., "afternoon", "evening"), OR simply maps to `datetimeTbd`.
- **Backend check needed:** Does the `Event` model / `EventIn` schema support a freeform flexible time string? Currently `datetimeTbd` is a bool. A freeform string would need a new model field.
- **Approach:**
  - Backend: Add `time_flexible_note: str | None` to `Event` model and `EventIn`/`EventOut`/`EventPatchIn` schemas. Add migration.
  - Frontend: Add a checkbox "time is flexible" in `_buildWhenSection`. When checked, hide time pickers, show a text field for a note like "afternoon" or "evening." Map to `datetimeTbd = true` + new `timeFlexibleNote` field.
  - This is a **medium** scope change spanning backend + frontend.

### 4c. Allow +1s setting

- **Context:** Issue says "maybe a setting to allow +1s and then an rsvp to allow +1s."
- **Backend:** Add `allow_plus_ones: bool` field to `Event` model. Add `plus_one_count: int` field to `EventRSVP` (or a separate `PlusOne` model). Add to `EventIn`, `EventOut`, `EventPatchIn`, `EventRSVP`-related schemas.
- **Frontend form:** Add a toggle "allow +1s" in `event_form_dialog.dart`.
- **Frontend RSVP:** In `rsvp_section.dart`, if `event.allowPlusOnes`, show a stepper/number input after the user RSVPs "going" or "maybe" to specify how many +1s they're bringing.
- **Guest list:** In `rsvp_guest_list.dart`, show +1 count alongside each guest's chip.
- This is a **larger** scope change requiring migrations. Consider a separate issue/PR.

### 4d. Re-poll button even after finalized poll

- **Context:** See Session 1b. After a poll is finalized and a date is set, the "set by poll" badge should disappear when the user manually edits the date. Additionally, the "add a poll" button should reappear whenever there is no open active poll (regardless of whether a past poll exists).
- **File:** `frontend/lib/screens/calendar/event_form_dialog.dart` — `_buildWhenSection`
- **Fix:** Change the condition that shows the "add a poll" option from "never if poll exists" to "only hide if poll is currently active (`hasPoll == true && event.datetimeTbd == true`)."

---

## Session 5 — RSVP Guest List Toggle

**Scope:** 2 files. Behavioral change to guest list display.

### 5a. Toggle between RSVP types

- **Context:** Issue says "you should be able to toggle between the diff rsvp types to see who's going." Currently `rsvp_guest_list.dart` shows all three groups vertically (going / maybe / can't make it), each individually expandable.
- **File:** `frontend/lib/screens/calendar/rsvp_guest_list.dart`
- **Current:** `RsvpGuestList` → `Column` of three `GuestStatusGroup` widgets (each independently expand/collapse).
- **Fix:** Replace the `Column` of three groups with a `TabBar` or `SegmentedButton` at the top of `RsvpGuestList`, showing "going (N)", "maybe (N)", "can't make it (N)". The selected tab shows that group's `Wrap` of `GuestChip` widgets. Keep the count visible in the tabs even when the tab isn't selected so it's easy to compare.
- **Where to render the toggle:** Currently `RsvpGuestList` is rendered inside `RSVPSection` (in `rsvp_section.dart`), which is wrapped in an `EventSectionCard` labeled "rsvp." The toggle tabs should live inside `RsvpGuestList` itself.

---

## Session 6 — Invite Permissions (Backend + Frontend)

**Scope:** 3–4 files. New event setting + conditional UI gating. Medium complexity.

### 6a. "Who can invite" event setting

- **Context:** Issue says "control who can invite people based on event setting set by co-host in the add/edit event modal — if only co-hosts can invite people then hide the invite search bar unless you're a co-host, otherwise allow it."
- **Backend:**
  - Add `invite_permission: str` field to `Event` model with choices `'all_members'` (default) and `'co_hosts_only'`.
  - Add to `EventIn`, `EventPatchIn`, `EventOut` schemas.
  - Add migration.
- **Frontend form (`event_form_dialog.dart`):**
  - Add a dropdown/segmented control "who can invite?" with options "all members" and "co-hosts only."
  - Map to the new `invitePermission` field.
- **Frontend detail view (`event_member_section.dart` or a new invite widget):**
  - Currently the invite search bar is presumably shown to all logged-in members (need to verify where it lives — it may be in `EventAdminActions` or elsewhere in the member section; search for `InvitePicker` or similar).
  - Conditionally hide the invite search if `event.invitePermission == 'co_hosts_only'` and the current user is not a co-host or creator.

### 6b. Find where invite UI lives in the detail view

- **Action:** Before starting 6a, search for the invite-in-detail-view code. It may be in `event_member_section.dart` under admin actions, or in a separate widget. Run:
  ```
  grep -r "invite" frontend/lib/screens/calendar/ --include="*.dart" -l
  ```
  Identify the file and line numbers before making changes.

---

## Session 7 — Navigation Bug Fix

**Scope:** 1–2 files. Router/navigation fix.

### 7a. Refresh on `/events/:id` should stay on event detail

- **Context:** Issue says "when you open an event from cal view on the mobile screen and you refresh, it goes back to cal view." This means navigating to an event currently does NOT change the URL to `/events/:id` — the event is shown as a panel/overlay on top of `/calendar`, so on refresh the browser restores `/calendar`.
- **Root cause:** In `calendar_screen.dart`, `_openEventDetail` likely uses `showEventDetail()` (from `event_detail_panel.dart`) which either pushes a material route (no URL change) or opens a side panel (no URL change). Neither updates the browser URL.
- **File:** `frontend/lib/screens/calendar_screen.dart` — find how events are opened from the calendar
- **Fix:** When opening an event from the calendar, use `context.go('/events/${event.id}')` (GoRouter) instead of `showEventDetail()` on narrow/mobile screens. On wide screens (desktop panel view), the panel is fine since the URL won't be the only way to restore state. Alternatively, push `/events/:id` on mobile and keep the panel on desktop.
- **Files:** `calendar_screen.dart`, possibly `event_detail_panel.dart` (`showEventDetail` function), and `app_router.dart` if routing needs adjustment.

---

## Session 8 — "Today" Button Fix

**Scope:** 1 file. Small targeted fix.

### 8a. Rethink "today" button placement/behavior

- **Context:** Issue says "today button is not working where it is — need to rethink this."
- **Current behavior:** `calendar_screen.dart` has `_goToToday()` which sets `_selectedDate = DateTime.now()` and is wired to an `OutlinedButton('today')` in `AppScaffold.actions`. The toolbar's own today button is hidden in compact mode.
- **Likely issue:** On mobile, the `AppScaffold.actions` area may be too small, inaccessible, or the button may not visually scroll the calendar. Also, in `week_view` and `day_view`, the today action may not scroll the time column.
- **Fix options:**
  1. Move "today" button into the `_CalendarToolbar` (remove the `if (!compact)` guard so it always shows).
  2. Or float it as a `FloatingActionButton` so it's always accessible.
  3. Verify that setting `_selectedDate` to today actually causes the month/week/day views to scroll to today — check if `WeekView`, `DayView`, and `MonthView` all respond to `selectedDate` changes by scrolling.
- **Files:** `calendar_screen.dart`, and possibly `month_view.dart`, `week_view.dart`, `day_view.dart` to verify scroll-to-today behavior.

---

## Recommended Session Order

1. **Session 1** — Quick copy fixes (1b duplicate cost section bug, "pda members only" text) — lowest risk
2. **Session 8** — Today button fix — small, isolated
3. **Session 2** — RSVP single-line + month overflow — pure layout
4. **Session 7** — Navigation refresh bug — router change
5. **Session 3** — Event detail reorganization — structural but no backend
6. **Session 5** — RSVP guest list toggle — behavioral
7. **Session 4** — Event form improvements (flexible time, re-poll button) — moderate
8. **Session 6** — Invite permissions — largest scope, requires backend + migration

---

## Notes

- `event_form_dialog.dart` is 1161 lines — well over the 500-line hard limit. Any session touching this file should also split it. Natural seams: `_buildWhenSection`, `_buildLinksSection`, `_buildCostSection`, `_buildCoHostPicker`, and the state class could each become their own files or widgets.
- The "allow +1s" feature (4c) is scope-creep territory — consider filing a separate issue.
- Always run `make ci` before committing each session.

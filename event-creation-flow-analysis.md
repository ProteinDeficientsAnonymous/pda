# Event Creation Flow Analysis

> Exploration for [issue #224](https://github.com/leahpeker/pda/issues/224): fewest possible clicks to get an event on the calendar.

## Current Minimum Interactions

| Scenario | Taps | Text entries | Total |
|----------|------|-------------|-------|
| Authenticated user, calendar screen | 2 | 1 (title) | **3** |
| Authenticated user, event management screen | 4 | 1 (title) | **5** |
| Unauthenticated user, calendar screen | 4 | 3 (phone, password, title) | **7** |

The absolute minimum for an authenticated user is: **tap "add event" → type title → tap "add"**. Start datetime auto-fills to today + next hour. All other fields have defaults.

## Entry Points

### A. Calendar Screen — "add event" button
- `frontend/lib/screens/calendar_screen.dart:132-139`
- `FilledButton.icon` at the bottom of the calendar column, below the calendar view
- Passes `_selectedDate` as `initialDate` so the date matches the calendar view
- Unauthenticated users get `GuestAddEventDialog` (phone + password login first)

### B. Event Management Screen — "new event" button
- `frontend/lib/screens/event_management_screen.dart:186-189`
- Available on `/events/mine` (any authenticated user) and `/events/manage` (requires `manage_events`)
- Does **not** pass `initialDate` — defaults to `DateTime.now()`

No other entry points exist (no FAB, no day-tap, no long-press, no keyboard shortcut, no inline quick-create).

## Form Fields

| Field | Required? | Default | Notes |
|-------|-----------|---------|-------|
| Title | **Yes** | empty | Only required field (`v.required()`) |
| Start datetime | **Yes** | Today + next hour | Auto-filled, no interaction needed |
| End datetime | No | hidden | User must tap "add end time" to show |
| Photo | No | none | |
| Location | No | empty | With autocomplete |
| Description | No | empty | |
| Links (WhatsApp, Partiful, Other) | No | hidden | Behind expandable section |
| Cost (price, Venmo, CashApp, Zelle) | No | hidden | Behind expandable section |
| RSVPs enabled | No | `false` | |
| Visibility | No | `public` | |
| Event type | No | `community` | `official` requires permission |
| Co-hosts | No | empty | |
| Invited members | No | empty | |

Backend required fields: `title` + `start_datetime` only (`community/events/schemas.py:83-103`).

## Submission Flow

1. Dialog pops with `EventFormResult`
2. POST `/api/community/events/` with form data
3. If photo selected → separate POST `/api/community/events/{id}/photo/`
4. If datetime poll options → `createDatetimePoll()`
5. Invalidate `eventsProvider` cache
6. Navigate to `/events/$eventId`
7. No success toast — navigation is the implicit confirmation

## Permissions

Any authenticated user can create events. No special role/permission needed. Only exception: marking as `official` requires `tag_official_event` permission.

## Simplification Opportunities

### 1. "Add event" button is below the fold
The button sits at the bottom of a `Column` under the expanded calendar view (`calendar_screen.dart:132`). On shorter viewports, users must scroll past the calendar to find it. A **FAB overlay** would be always visible and more discoverable.

### 2. No day-tap-to-create
Tapping a day on month/week view switches to day view — it doesn't create an event. A **long-press on a calendar day** could open the create dialog with that date pre-filled, which is a common pattern in Google Calendar, Apple Calendar, etc.

### 3. Full form shown for simple events
The dialog shows all sections (photo, links, cost, settings, co-hosts, invites) even when someone just wants to put "Dinner at 7pm" on the calendar. Options:
- **Progressive disclosure**: show only title + date + location initially, with an "add more details" expander for the rest
- **Two-step flow**: quick create (title + date), then redirect to event detail where they can edit to add more
- **Collapsible sections**: the links/cost sections are already collapsed, but photo and settings are always visible

### 4. No success feedback
After creation, the user is navigated to the event detail page with no toast/snackbar. A brief "event created 🌱" confirmation would provide closure.

### 5. Event management doesn't pass `initialDate`
Events created from `/events/mine` or `/events/manage` default to `DateTime.now()` instead of being date-aware. Minor issue since most creation happens from the calendar.

### 6. No keyboard shortcut or quick-add
No "n" key to open new event, no quick-add bar at the top of the calendar. These are lower priority but worth noting.

## Recommended Investigation Areas

If pursuing simplification:
- **Lowest effort, highest impact**: Add a FAB to the calendar screen (replaces the below-fold button)
- **Medium effort**: Add long-press on calendar day cells to trigger create with that date
- **Higher effort**: Progressive disclosure on the form (title + date first, details expandable)
- **Quick win**: Add success snackbar after event creation

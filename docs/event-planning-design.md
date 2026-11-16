# Event Planning: Yearly Planner Schedule

Issue: [#2121](https://github.com/ProteinDeficientsAnonymous/pda/issues/2121)

## Why

Leah runs the yearly event-planning schedule in a spreadsheet: one row per slot (12 monthly meetups, mostly walks, plus the june anniversary and dec holiday biannuals), one column per planner, each cell "available", "proposed" or "committed". Planners fill in what they could take, Leah proposes slots, and then chases people to commit. This moves that into the app so availability, proposals, commitments and reminders live in one place, and each committed slot links to the real event once it's created.

## Goals

- Planners submit availability for a year through a form.
- The coordinator sees a spreadsheet-style grid and proposes month slots to one or more planners.
- Proposed planners commit or decline; unanswered proposals get email reminders until they answer.
- Committed planners see their schedule and their teammates per slot, and are notified before their slot comes up.
- A committed planner creates the real event from the slot; the slot then links to that event.

## Non-goals

- Showing slots on the community calendar. A slot reaches the calendar only as the real event created from it (option A in the design conversation).
- Specific dates on slots. Slots are months; the planner picks the date when creating the event.
- Auto-assigning planners to slots.
- Reminders for planners who haven't filled out the availability form.

## Approaches considered

1. **New planning models (chosen).** Year, slot, availability and assignment tables; the grid reads straight from them. All new code, but each piece maps one-to-one to the spreadsheet.
2. **Availability via the existing surveys.** Saves building the form, but the grid would parse slot picks out of free-form survey answers, which breaks silently when slots or the survey change.
3. **Slots as draft events, proposals as co-host invites.** Reuses invite statuses and reminders, but events need a date or tbd, drafts need an owner before anyone commits, attendance pauses rewrite drafts, and availability still has no home.

## Permissions

Two new keys in `PermissionKey`, mirrored in `frontend/src/models/permissions.ts`:

- `manage_event_planning`: set up years and slots, see the full grid, propose and withdraw.
- `view_event_planning`: the planner tab: fill in availability, answer proposals, see own slots and teammates.

Only a role that grants `view_event_planning` makes someone a planner. Neither `manage_event_planning` nor the admin role's all-permissions default does, so a coordinator who also plans slots needs both. Grid rows for a year are every active member holding a granted `view_event_planning`, plus anyone with availability or an assignment in that year, so past years keep people who've since lost the role. No data migration: Leah grants `view_event_planning` to the `event planner` role in the roles screen.

## Data model (`backend/community/models/planning.py`)

- **PlanningYear**: `year` (unique int), `created_at`.
- **PlanningSlot**: `planning_year` FK, `label` (e.g. "march", "june anniversary"), `month` (1–12), `kind` (`monthly` | `biannual`), `event` FK nullable (`SET_NULL`), `order`.
- **PlanningAvailability**: one per (year, user): `biannual_interest` (`yes` | `maybe` | `no`), `monthly_count` (int), `available_slots` M2M to PlanningSlot, `updated_at`.
- **SlotAssignment**: one per (slot, user): `status` (`draft` | `proposed` | `committed` | `declined` | `withdrawn`), `proposed_by`, `proposed_at`, `responded_at`, `last_reminded_at`, `reminder_count`, `upcoming_notified_at`.

Creating a year pre-fills 12 monthly slots and the two biannuals (june anniversary, dec holiday); the coordinator can rename, add or remove slots.

## Flows

**Availability.** A planner opens the planning tab, picks the year, and submits: slots they could plan (toggles), biannual interest, and how many monthlies they'll take. Editable any time.

**Proposing.** The coordinator clicks a cell to stage that planner for that slot, including planners who didn't mark it available. Several planners can be staged on one slot. A staged proposal is a `draft`: nobody is notified, and clicking it again removes it silently. When done, the coordinator hits **send proposals**, which turns every draft in the year into `proposed` and sends each planner one in-app notification and one email listing all their new slots. The coordinator can withdraw a sent proposal or remove a committed planner; the planner is notified.

**Answering.** The planner commits or declines from the tab. Both notify every `manage_event_planning` holder in-app. A decline returns the slot to the coordinator: the cell shows "declined" and the slot is flagged as needing a planner. A committed planner can back out later, which acts as a decline.

**Reminders.** A daily job emails every planner with a `proposed` assignment every 3 days until they answer, with no cap, stopping once the slot's month has started. Each planner gets one reminder email listing all their unanswered slots, not one per slot. A proposal never answered stays `proposed`; the grid shows it as "awaiting answer" once the month has started. Reminders go only to active members who still hold `view_event_planning`.

**Upcoming notice.** The same daily job sends committed planners one email and in-app notification once the slot is within 6 weeks of the 1st of its month (so a late commit gets it on the next run), stamped in `upcoming_notified_at`, and skipped if the slot already has an event.

**No email.** Proposals and the upcoming notice always create an in-app notification too; reminders are email-only. The grid marks planners with no email so the coordinator knows to chase them directly.

**Creating the event.** A committed slot shows "create event" to its committed planners and to the coordinator. It opens the event form prefilled as an official event with the slot's label as title and a date in the slot's month, and passes the slot id. The form offers only the event types the creator can tag, and the backend's existing type-to-permission check still applies. On create, the backend links `slot.event` and sends co-host invites to the other committed planners on that slot. The grid then shows the slot as scheduled, with the event's status.

**After the event exists** the link is one-way: the event's hosts own it. A planner who commits later gets a co-host invite; backing out or being removed doesn't touch `co_hosts`, and declining a co-host invite doesn't change the assignment. A draft or cancelled event stays linked and shows its status; a deleted event counts as no event, so "create event" comes back and the upcoming notice can fire.

## Screens

- **Admin hub tile "event planning"**, visible with either permission.
- **Header** for everyone: title and year select.
- **Planner view** (`view_event_planning`), the coordinator's **mine** tab: "waiting on you" list of proposals with commit / decline; "your slots" list showing month, teammates (others proposed or committed on that slot, with their status), and the create-event button or event link; then the availability form, with a toggle per slot (monthlies in two columns, extra slots below).
- **Coordinator view** (`manage_event_planning`): tabs **schedule** (default), **mine** and **slots**, kept in `?tab=`; with no tab set, a coordinator with an unanswered proposal of their own lands on mine. Planners without manage get the mine content with no tabs. Logged-out visitors are sent to login and back.
  - **schedule**: summary pills (slots needing a planner, not counting months that have ended; proposals waiting; planners with no form); the grid; the month panel; the send proposals bar at the bottom, shown while drafts wait, so showing it shifts nothing above.
  - **The grid** is turned on its side so it fits a phone: planners down (no-form planners below a divider), slots across at fixed widths (monthlies in month order with a gap per quarter, then extra slots with ★ / ◆ markers explained in a key), plus a "month" summary row, a monthlies column (taken/offered) and a biannual column (yes/maybe/no). Each cell is a 15px tile in the app's greens where shape carries the state: in ✓ square, sent ? circle, awaiting answer ! circle, not sent yet (draft) dashed square, declined ✕, free dotted pale square, blank. Tapping a cell drafts, removes a draft, or confirms a withdraw, as in Proposing.
  - **The month panel** opens when a month letter is tapped (under the grid): the slot's status and event link, who's free with their load and a propose button, who's been asked in what state (decliners included), and "add someone" for everyone else. It's the large-button way to do everything the small cells do.
  - **slots**: one compact row per slot with "edit" opening the label / month / kind / delete controls; add a slot; start the year after the latest one.

Grid states by priority: committed > proposed (awaiting answer once the month starts) > draft > declined > available > blank. Never colour alone; no red/green.

All text lowercase.

## Visibility

Planners see their own availability and assignments, plus teammates' names and statuses on slots they're proposed or committed to. Only the coordinator sees the full grid and everyone's availability.

## Ops

The daily job is a management command, `send_planning_reminders`, run from `scripts/cron_daily.sh` by the existing `cron-daily` service.

## Delivery

Stacked PRs, each at most ~200 changed lines with tests (`/open-pr` hard-blocks at 250), so roughly 10–12:

1. Permissions (backend + frontend mirror).
2. Models + migration.
3. Coordinator year/slot API.
4. Availability API.
5. Admin hub tile + planner availability form.
6. Proposal API: propose / withdraw.
7. Proposal API: commit / decline + notifications and emails.
8. Coordinator year/slot setup UI.
9. Coordinator grid UI.
10. Planner "waiting on you" / "your slots" UI with teammates.
11. `send_planning_reminders` command (reminders + upcoming notice).
12. Create event from slot + link + co-host invites.

## Left to the builder

API routes and schema shapes, file layout of the screens, and the email copy.

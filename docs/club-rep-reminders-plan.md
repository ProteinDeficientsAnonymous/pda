# Club Reps: Assignment and Monthly Event Reminders — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Admins assign reps to clubs; reps can post club events only for their clubs; reps get emailed on the 10th, last day − 7, and last day while their club has nothing for next month.

**Architecture:** `Club.reps` M2M is the single source of truth for who reps what. Two manage_events-gated endpoints read and replace a club's reps; `/me` exposes `rep_club_ids`. The existing `enforce_type_tag_permission` choke point learns "or reps this club". A daily management command picks the due stage, finds uncovered clubs, claims a `ClubEventReminder` row per (club, month, stage), and emails active reps.

**Tech Stack:** Django + Django Ninja, pytest; Vite + React + TS, TanStack Query, Vitest.

**Spec:** `docs/club-rep-reminders-design.md`

## Global Constraints

- All user-facing frontend text and email copy lowercase.
- Each PR ≤ 250 changed lines incl. tests (target 200); `frontend/src/api/types.gen.ts` excluded from the count — say so in the PR body. Split further along task lines if a PR goes over.
- Run scoped tests only (`uv run pytest backend/tests/<file>` / `pnpm vitest run <file>`), plus `make agent-lint`, `make agent-typecheck`, `make agent-frontend-lint`, `make agent-frontend-typecheck`. Never `make agent-ci` or the full suite locally.
- Audit `details` hold user ids, never names.
- Dates in `settings.COMMUNITY_TZ`.
- After any backend schema change: `make frontend-types`; after a new `Code`: `python backend/manage.py dump_validation_codes` (regenerates `frontend/src/api/validationCodes.gen.ts`).
- No top-of-file comments; one-line comments only for non-obvious why.
- Branches `feat-club-reps-…`, stacked in PR order; commits conventional, no Co-Authored-By; PR bodies without the generated-by footer.

## Review Focus

1. **Month edges in community time** — an event at 23:30 local on the last day of the target month covers the club; one at 00:30 local on the 1st of the month after does not. (Task 5)
2. **Year rollover** — on Dec 10 the target is January of next year; on Jan 10, February. (Task 5)
3. **Short months** — in February, `week` falls on the 21st and `final` on the 28th (29th in a leap year). (Task 5)
4. **Rep of two clubs, one covered** — gets exactly one email, for the uncovered club; a second run the same day sends nothing. (Task 6)
5. **Rep posting for another club via a side door** — a rep creating a *draft* club event, or PATCHing `club_id` on an existing club event, for a club they don't rep gets 403. (Task 3)

---

## PR 1 — backend: assign reps

### Task 1: `Club.reps` + read/replace endpoints

**Files:**
- Modify: `backend/community/models/club.py`
- Create: `backend/community/migrations/0161_club_reps.py` (via `makemigrations`)
- Modify: `backend/community/clubs/api.py`
- Modify: `backend/community/validation.py` (`Code.Club.REP_NOT_ELIGIBLE = "club.rep_not_eligible"`)
- Modify: `backend/mcp_gateway/tools/members_roles.py:23` (example role in description: "event planner" instead of "club rep")
- Test: `backend/tests/test_club_reps.py`

**Interfaces:**
- Produces: `Club.reps = models.ManyToManyField("users.User", blank=True, related_name="rep_clubs")`
- Produces: `ClubRepOut(BaseModel): id: str; full_name: str; phone_number: str` (same shape the frontend `MemberSearchResult` maps from)
- Produces: `ClubRepsOut(BaseModel): club_id: str; reps: list[ClubRepOut]`
- Produces: `ClubRepsIn(BaseModel): user_ids: list[UUID]`
- Produces: view `list_club_reps(request)` at `GET /api/community/clubs/reps/` → `200 list[ClubRepsOut]` (every club, reps ordered by full_name), `auth=gated_jwt`, `_require_manage_clubs`
- Produces: view `set_club_reps(request, club_id: UUID, payload: ClubRepsIn)` at `PUT /api/community/clubs/{club_id}/reps/` → `200 ClubRepsOut`; 400 `club.rep_not_eligible` (field `user_ids`) if any id isn't in `User.objects.members()`; 404 unknown club; 403 without manage_events
- `GET /api/community/clubs/` and `ClubOut` unchanged.

- [ ] **Step 1: Write failing tests** in `test_club_reps.py`:
  - `test_put_replaces_reps_and_returns_them` — PUT `[a, b]` then PUT `[b]` → `club.reps` == `{b}`, response `reps[0]["id"] == str(b.id)`.
  - `test_put_dedupes_ids` — PUT `[a, a]` → one rep.
  - `test_put_rejects_non_member_and_unknown_ids` — archived user id → 400 `club.rep_not_eligible`; random uuid → same; reps unchanged.
  - `test_put_requires_manage_events` / `test_get_requires_manage_events` — plain member → 403.
  - `test_get_lists_every_club_with_its_reps` — two clubs, one with reps → both listed, empty `reps` for the other.
  - `test_put_audits_added_and_removed_ids` — audit row action `club_reps_updated`, `details == {"name": club.name, "added": [str(b.id)], "removed": [str(a.id)]}`.
  - `test_public_club_list_has_no_reps` — anonymous `GET /clubs/` items have exactly keys `{"id", "name", "requirements"}`.
- [ ] **Step 2:** `uv run pytest backend/tests/test_club_reps.py` → FAIL (404 routes / no field).
- [ ] **Step 3:** Add the field, `makemigrations community -n club_reps`, add schemas + two routes in `clubs/api.py` (reuse `_require_manage_clubs`, `_get_club`, `audit_log` with `AuditTargetType.CLUB`). PUT does `club.reps.set(users)` in `transaction.atomic()`. Add the `Code`, update the MCP description.
- [ ] **Step 4:** Re-run → PASS. Also `uv run pytest backend/tests/test_clubs.py backend/tests/test_mcp_members_roles.py`.
- [ ] **Step 5:** `dump_validation_codes`, `make frontend-types`, lint/typecheck, commit `feat(clubs): assign reps to clubs`.

## PR 1b — mcp: club rep tools (stacked on PR 1; independent of PR 2+)

### Task 1b: `list_club_reps` + `set_club_reps` MCP tools

**Files:**
- Modify: `backend/mcp_gateway/tools/clubs.py`
- Test: `backend/tests/test_mcp_club_reps.py`

**Interfaces:**
- Consumes: views `list_club_reps`, `set_club_reps`, schema `ClubRepsIn` from `community.clubs.api` (Task 1), imported as `list_reps_view` / `set_reps_view`; `Confirmed`, `issue_confirm_token`, `use_confirm_token`, `call_view` as in `delete_club` / `set_member_roles`.
- Produces tool `list_club_reps()`, `PermissionKey.MANAGE_EVENTS` → the view's list: `[{"club_id", "reps": [{"id", "full_name", "phone_number"}]}]`, with `club_name` added to each item from `list_clubs`. Description: `"list each pda club's reps (the members who get its monthly event reminders and can post its events). member ids work with set_club_reps."`
- Produces tool `set_club_reps(club_id: ClubId, add_member_ids: list[UUID] | None = None, remove_member_ids: list[UUID] | None = None, confirm_token: ConfirmToken = None)`, `PermissionKey.MANAGE_EVENTS`. Mirrors `set_member_roles`: add/remove leaves the club's other reps as they are. Description: `"add and/or remove reps on one club, leaving its other reps as they are. member ids come from find_members; only members can be reps. reps get the club's monthly event reminder emails and can post its events. the first call changes nothing and returns the club, its current reps, the resulting reps and a confirm_token: show that, get an explicit yes, then call again with the same arguments and the token."`
  - Errors (`ToolError`, lowercase): neither list given → `"give add_member_ids and/or remove_member_ids"`; overlap → `"a member can't be both added and removed"`; an add id not in `User.objects.members()` → `"not members: <ids>; use find_members"`; no change → `"<club> already has exactly those reps; nothing to do"`; unknown club → existing `_club` error.
  - Preview: `{"club": {"id", "name"}, "current_reps": [{"id", "name"}], "resulting_reps": [...], "confirm_token"}`; `Confirmed(user.pk, target_id=str(club_id), action="set_club_reps", changes=sorted(new_ids), state=sorted(current_ids))`.
  - Confirmed call: `call_view(set_reps_view, user, club_id=club_id, payload=ClubRepsIn(user_ids=new_ids))` → `{"club": {...}, "reps": [{"id", "name"}]}`.

- [ ] **Step 1: Write failing tests** in `test_mcp_club_reps.py` (helpers from `tests/_mcp_tool_helpers.py`):
  - `test_tools_need_manage_events` — neither tool in `tool_names(make_user())`; both in `tool_names(manager)`.
  - `test_list_club_reps` — book with rep a → item `{"club_id": str(book.id), "club_name": "book club", "reps": [{"id": str(a.id), …}]}`.
  - `test_preview_changes_nothing` — add b to book (rep a) → `current_reps` ids `[a]`, `resulting_reps` ids `{a, b}`, `confirm_token` set, `book.reps` still `{a}`.
  - `test_confirm_applies_add_and_remove` — add b, remove a with token → `book.reps == {b}`; audit row `club_reps_updated` exists.
  - `test_token_rejected_after_reps_change_elsewhere` — preview, then `book.reps.add(c)` directly, confirm → `tool_error`; reps still `{a, c}`.
  - `test_refuses_non_member_overlap_and_noop` — archived user id → message contains `"not members"`; same id in add and remove → overlap message; adding an existing rep only → `"nothing to do"`.
- [ ] **Step 2:** `uv run pytest backend/tests/test_mcp_club_reps.py` → FAIL.
- [ ] **Step 3:** Implement both tools in `clubs.py` per Interfaces.
- [ ] **Step 4:** Re-run + `backend/tests/test_mcp_clubs.py` → PASS. Lint/typecheck.
- [ ] **Step 5:** Commit `feat(mcp): list and set club reps`.

## PR 2 — frontend: assign reps on /admin/clubs

### Task 2: rep picker in the club dialog, reps shown in the list

**Files:**
- Modify: `frontend/src/api/clubs.ts`
- Modify: `frontend/src/screens/admin/ClubDialog.tsx`
- Modify: `frontend/src/screens/admin/ClubsAdminScreen.tsx`
- Test: `frontend/src/api/clubs.reps.test.ts`, `frontend/src/screens/admin/ClubsAdminScreen.test.tsx`

**Interfaces:**
- Consumes: Task 1 endpoints.
- Produces: `useClubReps(): UseQueryResult<Map<string, MemberSearchResult[]>>` (key `[...clubKeys.all, 'reps']`), `useSetClubReps(clubId: string)` mutation taking `userIds: string[]`, invalidates `clubKeys.all` (prefix covers reps).

- [ ] **Step 1: Write failing tests:**
  - `clubs.reps.test.ts`: `useClubReps` maps `{club_id, reps:[{id, full_name, phone_number}]}` to a map of `MemberSearchResult`; `useSetClubReps('c1')` PUTs `/api/community/clubs/c1/reps/` with `{ user_ids: ['u1'] }`.
  - `ClubsAdminScreen.test.tsx`: a club row shows `reps: ada, bo` (lowercased); a club with none shows `no reps yet`; editing a club, picking a member and saving calls the reps PUT with that id; creating a club with a picked rep POSTs the club, then PUTs reps with the new club's id.
- [ ] **Step 2:** `pnpm vitest run src/api/clubs.reps.test.ts src/screens/admin/ClubsAdminScreen.test.tsx` → FAIL.
- [ ] **Step 3:** Add hooks; in `ClubDialogBody` add `<MemberPicker label="reps" hint="they get reminder emails and can post this club's events" … />` seeded from `useClubReps().data?.get(existing.id)`; on save, save the club then call reps PUT only if the selected id set changed. In the list, a muted line `reps: …` or `no reps yet`.
- [ ] **Step 4:** Re-run → PASS. `make agent-frontend-lint agent-frontend-typecheck`.
- [ ] **Step 5:** Commit `feat(clubs): pick club reps on the clubs admin page`.

## PR 3 — backend: reps post only for their clubs

### Task 3: rep-aware club permission + `rep_club_ids` on `/me`

**Files:**
- Modify: `backend/community/events/helpers.py:470-494` (`enforce_type_tag_permission`)
- Modify: `backend/community/events/crud.py:216`
- Modify: `backend/community/events/_update.py:38-39`
- Modify: `backend/users/schemas.py` (`UserOut`)
- Modify: `backend/users/_auth.py` (all six `UserOut.from_user(user)` returns)
- Test: `backend/tests/test_event_club_reps.py`, `backend/tests/test_auth_me_rep_clubs.py`

**Interfaces:**
- Consumes: `Club.reps` / `User.rep_clubs` (Task 1).
- Produces: `enforce_type_tag_permission(request, event_type: str, endpoint: str, event_id=None, *, club_id: UUID | None = None) -> None` — for `EventType.CLUB`, passes if `has_permission(TAG_CLUB_EVENT)` or `club_id is not None and request.auth.rep_clubs.filter(pk=club_id).exists()`.
- Produces: `UserOut.rep_club_ids: list[str] = []` and `UserOut.for_self(user: User) -> UserOut` (= `from_user` + `rep_club_ids` sorted). Only `_auth.py` (the self endpoints) uses `for_self`; `list_users` etc. stay `from_user` (no N+1, no leak).
- Update rule: in `_validate_update_payload`, if `"event_type" in updates or "club_id" in updates`, call with `effective_type = updates.get("event_type", event.event_type)` and `club_id = updates.get("club_id", event.club_id)`.

- [ ] **Step 1: Write failing tests** (`test_event_club_reps.py`, rep = `make_user()` added to `book.reps`, no permission):
  - `test_rep_creates_club_event_for_own_club` → 201.
  - `test_rep_cannot_create_for_other_club` → 403.
  - `test_rep_cannot_create_draft_for_other_club` → 403 (Review Focus 5).
  - `test_rep_cannot_move_event_to_other_club` — rep hosts a `book` club event, PATCH `club_id=movie` → 403; event's club unchanged.
  - `test_tag_club_event_holder_posts_for_any_club` → 201.
  - `test_non_rep_without_permission_cannot_create_club_event` → 403.
  - `test_auth_me_rep_clubs.py`: `GET /api/auth/me/` returns `rep_club_ids == sorted([str(book.id), str(movie.id)])` for a rep of both; `[]` for a non-rep; `GET /api/auth/users/` items carry `rep_club_ids == []`.
- [ ] **Step 2:** Run both files → FAIL.
- [ ] **Step 3:** Implement per Interfaces.
- [ ] **Step 4:** Run both + `backend/tests/test_event_club.py backend/tests/test_event_club_field.py` → PASS.
- [ ] **Step 5:** `make frontend-types`, lint/typecheck, commit `feat(events): reps post club events only for their clubs`.

## PR 4 — frontend: club picker scoped to rep clubs

### Task 4: `repClubIds` on the user, gray out non-rep clubs

**Files:**
- Modify: `frontend/src/models/user.ts` (`User.repClubIds: string[]`), `frontend/src/api/auth.ts` (`mapUser`: `repClubIds: u.rep_club_ids ?? []`), `frontend/src/test/fixtures.ts` (default `[]`)
- Modify: `frontend/src/components/ui/Select.tsx` (`Option.disabled?: boolean`, passed to `<option>`)
- Modify: `frontend/src/screens/events/form/EventForm.tsx:92`, `EventFormBasics.tsx`, `EventFormClub.tsx`
- Test: `frontend/src/screens/events/form/EventFormClub.test.tsx`

**Interfaces:**
- Consumes: `rep_club_ids` on `/me` (Task 3).
- Produces: in `EventForm`, `canTagAnyClub = hasPermission(user, Permission.TagClubEvent)`, `canTagClub = canTagAnyClub || (user?.repClubIds.length ?? 0) > 0`. `EventFormClub` gets `allowedClubIds: readonly string[] | null` (`null` = all allowed), threaded through `EventFormBasics`.

- [ ] **Step 1: Write failing tests** in `EventFormClub.test.tsx`:
  - with `allowedClubIds={['book']}`, the `movie club` option is `disabled` and `book club` isn't.
  - with `allowedClubIds={null}`, no option is disabled.
  - a rep (no `tag_club_event`, `repClubIds: ['book']`) rendering `EventForm` sees the club type option.
- [ ] **Step 2:** `pnpm vitest run src/screens/events/form/EventFormClub.test.tsx` → FAIL.
- [ ] **Step 3:** Implement per Interfaces. When a rep has exactly one club and `clubId` is empty, leave it empty (no auto-select — my call, keeps the existing "pick a club" validation path).
- [ ] **Step 4:** Re-run + `EventFormDescriptionTemplate.test.tsx` → PASS; frontend lint/typecheck.
- [ ] **Step 5:** Commit `feat(events): only a rep's own clubs are pickable`.

PR 4 body notes the ops step: once deployed and reps are assigned, delete the "club rep" role.

## PR 5 — backend: reminder emails

### Task 5: reminder schedule + coverage (pure logic and model)

**Files:**
- Create: `backend/community/models/club_event_reminder.py` (export from `community/models/__init__.py`)
- Create: `backend/community/migrations/0162_clubeventreminder.py`
- Create: `backend/community/clubs/reminders.py`
- Test: `backend/tests/test_club_reminder_schedule.py`

**Interfaces:**
- Produces: `class ClubReminderStage(models.TextChoices): EARLY = "early"; WEEK = "week"; FINAL = "final"`
- Produces: `ClubEventReminder(id UUID pk, club FK Club CASCADE related_name="event_reminders", month DateField, stage CharField(choices), sent_at DateTimeField(auto_now_add))`, `UniqueConstraint(fields=["club", "month", "stage"], name="club_event_reminder_unique")`
- Produces: `target_month(today: date) -> date` — first day of next month.
- Produces: `due_stage(today: date) -> ClubReminderStage | None` — latest of `EARLY` (10th), `WEEK` (last day − 7), `FINAL` (last day) whose date ≤ today; `None` on the 1st–9th.
- Produces: `uncovered_clubs(month: date) -> QuerySet[Club]` — clubs with no `Event` where `event_type=CLUB`, `status=ACTIVE`, `start_datetime` in `[month 00:00, next month 00:00)` local (`COMMUNITY_TZ`-aware bounds).

- [ ] **Step 1: Write failing tests:**
  - `due_stage`: `(2026,11,9)→None`, `(11,10)→EARLY`, `(11,22)→EARLY`, `(11,23)→WEEK`, `(11,29)→WEEK`, `(11,30)→FINAL`, `(2027,2,21)→WEEK`, `(2027,2,28)→FINAL`, `(2028,2,22)→WEEK`, `(2028,2,29)→FINAL`.
  - `target_month`: `(2026,11,10)→2026-12-01`, `(2026,12,10)→2027-01-01`.
  - `uncovered_clubs(date(2026,12,1))`: active club event 2026-12-31 23:30 local → covered; one at 2027-01-01 00:30 local only → uncovered; draft, cancelled, tbd (`start_datetime=None`), and community-type events with that club → uncovered; covered regardless of `created_by`.
  - Unique constraint: second `ClubEventReminder.objects.create(same triple)` raises `IntegrityError`.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement; `makemigrations community -n clubeventreminder`.
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit `feat(clubs): club event reminder schedule`.

### Task 6: send the emails + command + cron

**Files:**
- Create: `backend/notifications/club_reminder_email.py`
- Create: `backend/templates/emails/club_event_reminder.html`, `.txt` (follow `planning_availability.*`, include `_no_reply_footer`)
- Modify: `backend/community/clubs/reminders.py`
- Create: `backend/community/management/commands/send_club_event_reminders.py`
- Modify: `scripts/cron_daily.sh` (append `timeout 300 uv run --no-dev python manage.py send_club_event_reminders || status=1` after `send_planning_reminders`)
- Test: `backend/tests/test_club_event_reminders.py`

**Interfaces:**
- Consumes: Task 5 functions and model; `fake_email_sender` fixture; `send_best_effort`, `get_email_sender`.
- Produces: `ClubReminderEmailDetails(to: str, display_name: str, club_name: str, month_label: str, deadline_label: str, stage: ClubReminderStage, create_url: str)` (frozen dataclass) and `send_club_reminder_email(*, sender: EmailSender, details: ClubReminderEmailDetails) -> SendResult`.
- Subjects (exact, lowercase): EARLY `"{month} {club} events get shared on the 15th"`, WEEK `"{club}: {month} events due by {deadline}"`, FINAL `"{club}: {month} events due today"`. `month_label` like `"december"`, `deadline_label` like `"nov 30"`. `create_url = f"{settings.FRONTEND_BASE_URL}/events/add"`.
- Produces: `send_club_event_reminders(now: datetime) -> int` (emails sent). For each `uncovered_clubs(target)` when `due_stage(today)` is set: `_, created = ClubEventReminder.objects.get_or_create(club=…, month=target, stage=stage)`; skip if not created; recipients `club.reps.filter(pk__in=User.objects.active_members().values("pk")).filter(HAS_EMAIL)`; zero recipients → `logger.info` with the club id, row stays.

- [ ] **Step 1: Write failing tests** (freeze `now` by passing it in):
  - `test_emails_every_active_rep_of_uncovered_club` — two reps with email → 2 sends, subject `"december book club events get shared on the 15th"` on 2026-11-10.
  - `test_skips_paused_archived_and_emailless_reps`.
  - `test_covered_club_gets_nothing`.
  - `test_rep_of_two_clubs_one_covered_gets_one_email_and_rerun_sends_none` (Review Focus 4).
  - `test_missed_day_catches_up_with_latest_stage_only` — first run 2026-11-24 → one WEEK email, no EARLY row.
  - `test_nothing_sent_on_the_9th`.
  - `test_final_subject` — 2026-11-30 → `"book club: december events due today"`.
  - `test_command_runs` — `call_command("send_club_event_reminders")` exits clean.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement email module, templates (body: greeting, one line per stage — early: "next month's club events get shared in the whatsapp on the 15th. post {club}'s {month} events by then so they make the list."; week/final: "{club}'s {month} events are due by {deadline}." / "…are due today." — then the link), reminders function, command (pattern of `send_planning_reminders.py`), cron line.
- [ ] **Step 4:** Run + Task 5 tests → PASS. Lint/typecheck.
- [ ] **Step 5:** Commit `feat(clubs): email reps when next month has no club event`.

If PR 5 exceeds 250 lines, ship Task 5 and Task 6 as separate PRs.

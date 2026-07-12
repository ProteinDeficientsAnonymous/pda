# Split display name into first / last name

**Issue:** [#532](https://github.com/ProteinDeficientsAnonymous/pda/issues/532) — change display name to full name
**Also closes:** [#540](https://github.com/ProteinDeficientsAnonymous/pda/issues/540) — `${FIRST_NAME}` welcome-template variable
**Date:** 2026-07-11

## Motivation

Members currently have a single free-form `display_name`. Some use non-name usernames,
which creates unwanted anonymity for an in-person-oriented community. Split the name into
a required `first_name` and an optional `last_name`, parse existing values as best we can,
and remove `display_name` entirely.

## Scope & PR staging

Delivered as a sequence of small PRs, each targeting **<500 diff lines (ideally <300)** and
each independently green. The `display_name` → first/last rename touches ~96 files, so the
core split (PR1) is decomposed backend-first with a transitional kept column.

- **PR1a — backend split.** Add `first_name`/`last_name`, backfill migration, **keep the
  `display_name` column** (synced `display_name = full_name` on save), expose both old and
  new fields in the API, update join-request + welcome vars + backend tests/conftest. Old
  frontend keeps working unchanged.
- **PR1b — frontend split.** Swap read sites `displayName` → `fullName`, add first/last form
  inputs (join form = both required), update fixtures + frontend tests. May be split further
  into read-sites vs. forms if it exceeds ~500 lines.
- **PR1c — drop transitional column.** Remove the `display_name` column (migration) and its
  schema fields once nothing reads it.
- **PR2 — hide last name.** Per-member settings toggle; last name suppressed for non-admin
  viewers, enforced on the backend.
- **PR3 — nickname.** Optional nickname displayed beneath the real name on the profile.

Each PR builds on the previous and is specified here so the data model is designed once, but
each ships and reviews on its own branch. A plan may propose further sub-splits at planning
time if a PR is trending over the line budget.

### Transition mechanic (PR1a → PR1c)

The `display_name` column is **kept and synced**, not dropped, until the frontend is off it:

- **PR1a:** add `first_name`/`last_name`; backfill both from `display_name`; keep
  `display_name` and set `display_name = full_name` in `User.save()` (and the equivalent
  write paths) so it stays correct as names change. API output sends `display_name`
  **and** `first_name`/`last_name`/`full_name`.
- **PR1b:** frontend reads `full_name`; forms write `first_name`/`last_name`.
- **PR1c:** drop the `display_name` column and remove it from all schemas.

This keeps every migration trivial and DB-rollback-friendly, with no computed "phantom"
`display_name` masquerading as a real column mid-transition.

---

## PR1a — backend split

### Data model

**User** (`backend/users/models.py`)

- Add `first_name = CharField(max_length=64)` — **required** (non-blank enforced at the
  schema layer; the column itself is non-null after backfill).
- Add `last_name = CharField(max_length=64, blank=True, default="")` — optional.
- **Keep** the `display_name` column through PR1a/PR1b; drop it in PR1c. Sync it on write:
  `display_name = full_name` in `User.save()` so it stays correct as names change.
- Add a `full_name` property: `f"{self.first_name} {self.last_name}".strip()`. Canonical
  display string, never stored.
- `__str__` → `self.full_name or self.phone_number`.
- `REQUIRED_FIELDS = ["first_name"]`.

**JoinRequest** (`backend/community/models/join_form.py`)

- Same two columns; keep `display_name` through PR1a/PR1b (sync on save), drop in PR1c.
  (Both first **and** last are required on the public join form — see Forms below — but the
  model keeps `last_name` blankable to match User and allow admin edits.)

### Migration (parse existing data)

Per model, in PR1a (column drop is deferred to PR1c):

1. Add `first_name` / `last_name` as nullable.
2. Data migration backfilling from `display_name` using the parse rule below.
3. Make `first_name` non-null (`default=""` transitional). **Leave `display_name` in place.**

PR1c adds the column-drop migration once nothing reads `display_name`.

**Parse rule** (from the issue comment):

- Split `display_name` on whitespace into words.
- **0 words (blank):** `first_name = ""`, `last_name = ""`. These are legacy accounts the
  onboarding gate already catches (`passwordSetupRedirect` sees an empty name and routes to
  `/onboarding`), so the member is prompted to fill it in on next login.
- **1 word:** `first_name = word`, `last_name = ""`.
- **2+ words:** `last_name = <last word>`, `first_name = <everything before it, space-joined>`.

Applies identically to `User` and `JoinRequest`. The backfill's reverse operation is a
no-op (the `display_name` column is untouched in PR1a), so the migration is trivially
reversible.

### API / schemas (`backend/users/schemas.py`)

**Output schemas** — **add** `first_name`, `last_name`, and a server-computed `full_name`
alongside the existing `display_name` (which stays until PR1c):

- `UserOut`, `MemberProfileOut`, `MemberDirectoryOut`, `UserSearchOut`, `UserCreateOut`.
- New read surfaces will consume `full_name` (in PR1b). `first_name` / `last_name` are also
  sent for forms and (in PR2) viewer-dependent suppression.

**Input schemas** — **add** `first_name` (required where a name is required) + `last_name`
(optional). Keep accepting `display_name` as optional through PR1a so old clients don't
break; when first/last are provided they win and `display_name` is derived:

- `UserCreateIn`, `UserPatchIn`, `MePatchIn`, `OnboardingIn`.

**Field limits** (`backend/community/_field_limits.py`):

- Add `FIRST_NAME = 64`, `LAST_NAME = 64`.
- `DISPLAY_NAME (64)` is also reused by unrelated public fields — `_public_rsvp` (RSVP
  submitter name) and `_join_request_submit` (honeypot `website`). Those are **not** the
  user's structured name; leave a neutral 64-char limit for them (keep `DISPLAY_NAME` or
  rename to a neutral constant), do not repoint them at first/last.

**Join submit / resend / approval** (`backend/community/_join_request_*.py`): accept and
carry `first_name` + `last_name`. Approval copies both to the new `User` directly — no
parsing at approval time anymore (parsing only happens once, in the migration).

### Testing (PR1a)

- Migration parse tests (0 / 1 / 2 / 3+ words) for `User` and `JoinRequest`.
- Schema round-trips: output includes `first_name`/`last_name`/`full_name` **and**
  `display_name`; input accepts first/last and derives `display_name`.
- Join-request approval copies both names to the new `User`.
- `User.save()` keeps `display_name == full_name`.
- Update shared `tests/conftest.py` fixtures to set `first_name`/`last_name` — ripples
  through the ~40 test files that build users. (Fixtures can set both old and new during the
  transition, but prefer new-only so PR1c is a clean removal.)

---

## PR1b — frontend split

### Welcome message variables

Rendered frontend-side in `renderWelcomeMessage` (`frontend/src/utils/welcomeMessage.ts`):

- `${NAME}` → **first name only** (satisfies #540).
- Add `${FULL_NAME}` → `full_name`.
- Update `WelcomeMessageVars`, `renderWelcomeMessage`, and the template help/placeholder
  text listing available variables.
- `buildWelcomeMessage` (legacy hardcoded body) greets with first name.

### Model + read sites

`User` model (`frontend/src/models/user.ts`): add `firstName`, `lastName`, `fullName`
(drop `displayName` here — the API still sends it, but nothing should read it after this
PR). Update `passwordSetupRedirect`'s name check to `firstName.length > 0`.

**Read sites** — mechanical `displayName` → `fullName` rename (member cards, profile
headings, initials, directory/admin search + sort):

- `screens/members/MemberProfileScreen.tsx`, `MembersDirectoryScreen.tsx`
- `screens/admin/MembersTab.tsx`, `MemberDetailScreen.tsx`
- `screens/profile/ProfileScreen.tsx`
- plus remaining `displayName` references surfaced by grep.

### Forms

Two inputs, first required / last optional (except join = both required):

- `screens/auth/OnboardingScreen.tsx`
- `screens/settings/SettingsScreen.tsx`
- `screens/admin/MemberCreateDialog.tsx`
- `screens/public/JoinScreen.tsx` — **both required** here.

`validators.ts`: reuse the existing name-char regex for both first and last; rename/param
the `displayName` validator accordingly.

> If PR1b trends over ~500 lines, split into **PR1b-read** (model + read sites + fixtures)
> and **PR1b-forms** (the four form screens + their tests). The read-sites rename is
> independently green because the forms still write the old shape until they're updated.

### Testing (PR1b)

Update `test/fixtures.ts`; update form / directory / profile / onboarding / settings /
member-create tests and the `JoinScreen` a11y test for the new second field; welcome-var
rendering tests (first vs full).

---

## PR1c — drop the transitional column

- Migration dropping `display_name` from `User` and `JoinRequest`.
- Remove `display_name` from all output/input schemas and the `sync_display_name`
  save-sync logic (`users/_name_parsing.py`), plus the `save()` overrides that call it.
- Remove any lingering `display_name` acceptance in input schemas.
- Grep-sweep for `display_name` / `displayName` to confirm nothing references it.
- **Dedupe the name-resolution logic (deferred from PR1a review).** PR1a extracted the
  save-sync into a shared helper, but the "first/last wins, else parse a bare legacy
  `display_name`" resolution rule is still hand-rolled in three places:
  `_resolve_name_fields` (`users/_helpers.py`, used by PATCH /me + admin patch + onboarding),
  the inline block in `_join_request_submit.py`, and the inline block in
  `_management.py::create_user`. Once `display_name` is dropped, the legacy-parse fallback
  goes away entirely, so collapse these into one shared resolver (or delete the fallback
  branch). Doing it here avoids editing three copies in lockstep while the fallback still exists.
- Small, mostly-deletion PR.

---

## PR2 — hide last name

### Goal

A member can hide their last name from other members. The guarantee must be real: the last
name is **omitted from the API payload** for non-admin viewers, not merely hidden in the UI
(a client-side hide still ships the value in the response and leaks via DevTools / direct
API calls). This mirrors the existing `show_phone` / `show_email` server-side gating and the
PII-leak hardening from #452.

### Model

**User:** add `hide_last_name = BooleanField(default=False)`.

### Viewer-dependent output

`full_name` and `last_name` become viewer-dependent in member-facing schemas:

- **Admin viewer** (or **self**): always full — `full_name = "First Last"`, `last_name`
  populated.
- **Non-admin viewer** of a member with `hide_last_name = True`: `full_name = "First"`,
  `last_name` omitted / empty in the payload.

Compose this in the schema factory using the requesting user's admin status and the target's
flag. Affected member-facing schemas: `MemberDirectoryOut`, `MemberProfileOut`,
`UserSearchOut`. `UserOut` for self always shows full. Admin schemas
(`MembersTab` / member detail source) always show full.

### Search / sort

Directory search + sort for non-admins operate only on exposed values, so a hidden last
name simply won't match a non-admin's last-name query — which is the intended behavior. Keep
the admin/non-admin branch in the queryset/serialization, not in the client.

### Settings UI

Add a toggle in `SettingsScreen` ("hide my last name from other members" — lowercase per
project text rules), wired to `MePatchIn.hide_last_name`. Surface the flag in `UserOut`
(self) so the toggle reflects state.

### Testing (PR2)

- Backend: non-admin request omits last name when flag on; admin request includes it; self
  always sees own last name; directory search doesn't match hidden last names for non-admins.
- Frontend: settings toggle round-trip; directory renders first-name-only for hidden members.

---

## PR3 — nickname

### Goal

Optional nickname, shown **beneath** the real name on the profile. Real name stays primary
for cards, search, and sort; the nickname does not replace `full_name`. (Placement is
explicitly interim — likely redesigned later.)

### Model

**User:** add `nickname = CharField(max_length=64, blank=True, default="")`.

### API

Add `nickname` to `UserOut`, `MemberProfileOut`, and `MePatchIn`. Not folded into
`full_name`; sent as its own field.

### UI

- Settings: optional nickname input.
- `MemberProfileScreen` / `ProfileScreen`: render the nickname as a secondary line beneath
  the `full_name` heading when present.

### Testing (PR3)

- Backend: nickname patch round-trip; present/absent in profile output.
- Frontend: nickname renders beneath the name when set, hidden when empty; settings round-trip.

---

## Non-goals

- Redesigning how nickname displays (PR3 placement is interim).
- Changing the public RSVP / honeypot fields that happen to share the old 64-char limit.
- Audio/text name pronunciation (separate issue #420).

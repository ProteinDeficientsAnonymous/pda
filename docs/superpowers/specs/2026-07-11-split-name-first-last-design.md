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

Delivered as **three independent PRs**, one implementation plan each, under this single spec.

- **PR1 — name split (end-to-end).** Model, migration, API, all read sites, all forms.
- **PR2 — hide last name.** Per-member settings toggle; last name suppressed for
  non-admin viewers, enforced on the backend.
- **PR3 — nickname.** Optional nickname displayed beneath the real name on the profile.

PR2 and PR3 build on PR1 and are specified here so the data model is designed once, but
each ships and reviews on its own branch.

---

## PR1 — name split

### Data model

**User** (`backend/users/models.py`)

- Add `first_name = CharField(max_length=64)` — **required** (non-blank enforced at the
  schema layer; the column itself is non-null after backfill).
- Add `last_name = CharField(max_length=64, blank=True, default="")` — optional.
- Remove the `display_name` column.
- Add a `full_name` property: `f"{self.first_name} {self.last_name}".strip()`. Canonical
  display string, never stored.
- `__str__` → `self.full_name or self.phone_number`.
- `REQUIRED_FIELDS = ["first_name"]`.

**JoinRequest** (`backend/community/models/join_form.py`)

- Same two columns, remove `display_name`. (Both first **and** last are required on the
  public join form — see Forms below — but the model keeps `last_name` blankable to match
  User and allow admin edits.)

### Migration (parse existing data)

Three-step sequence per model to stay reversible and non-null-safe:

1. Add `first_name` / `last_name` as nullable.
2. Data migration backfilling from `display_name` using the parse rule below.
3. Make `first_name` non-null (`default=""` transitional, then drop `display_name`).

**Parse rule** (from the issue comment):

- Split `display_name` on whitespace into words.
- **0 words (blank):** `first_name = ""`, `last_name = ""`. These are legacy accounts the
  onboarding gate already catches (`passwordSetupRedirect` sees an empty name and routes to
  `/onboarding`), so the member is prompted to fill it in on next login.
- **1 word:** `first_name = word`, `last_name = ""`.
- **2+ words:** `last_name = <last word>`, `first_name = <everything before it, space-joined>`.

Applies identically to `User` and `JoinRequest`. Include a reverse migration that
recombines (`full_name` → `display_name`) so the step is reversible.

### API / schemas (`backend/users/schemas.py`)

**Output schemas** — replace `display_name` with `first_name`, `last_name`, and a
server-computed `full_name`:

- `UserOut`, `MemberProfileOut`, `MemberDirectoryOut`, `UserSearchOut`, `UserCreateOut`.
- Read surfaces consume `full_name`. `first_name` / `last_name` are also sent for forms
  and (in PR2) viewer-dependent suppression.

**Input schemas** — replace `display_name` with `first_name` (required where a name is
required) + `last_name` (optional):

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

### Welcome message variables

Rendered frontend-side in `renderWelcomeMessage` (`frontend/src/utils/welcomeMessage.ts`):

- `${NAME}` → **first name only** (satisfies #540).
- Add `${FULL_NAME}` → `full_name`.
- Update `WelcomeMessageVars`, `renderWelcomeMessage`, and the template help/placeholder
  text listing available variables.
- `buildWelcomeMessage` (legacy hardcoded body) greets with first name.

### Frontend (~56 files)

`User` model (`frontend/src/models/user.ts`): `displayName` → `firstName`, `lastName`,
`fullName`. Update `passwordSetupRedirect`'s name check to `firstName.length > 0`.

**Read sites** — mechanical `displayName` → `fullName` rename (member cards, profile
headings, initials, directory/admin search + sort):

- `screens/members/MemberProfileScreen.tsx`, `MembersDirectoryScreen.tsx`
- `screens/admin/MembersTab.tsx`, `MemberDetailScreen.tsx`
- `screens/profile/ProfileScreen.tsx`
- plus remaining `displayName` references surfaced by grep.

**Forms** — two inputs, first required / last optional (except join = both required):

- `screens/auth/OnboardingScreen.tsx`
- `screens/settings/SettingsScreen.tsx`
- `screens/admin/MemberCreateDialog.tsx`
- `screens/public/JoinScreen.tsx` — **both required** here.

`validators.ts`: reuse the existing name-char regex for both first and last; rename/param
the `displayName` validator accordingly.

### Testing (PR1)

- **Backend:** migration parse tests (0 / 1 / 2 / 3+ words), schema round-trips,
  join-request approval copies both names, welcome-var rendering (first vs full). Update
  shared `tests/conftest.py` fixtures (`display_name` → `first_name`/`last_name`) — ripples
  through the ~40 test files that build users.
- **Frontend:** update `test/fixtures.ts`; update form / directory / profile / onboarding /
  settings / member-create tests and the `JoinScreen` a11y test for the new second field.

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

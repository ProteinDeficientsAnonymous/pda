# seed_staging — staging demo data (Issue 653)

## Problem

Staging is thin, making it hard to eyeball how calendar/event lists, permission
gating, and the role editor behave with volume and variety. We need realistic
demo data on the **staging** deploy only — not local dev `make seed`, not prod.

Three related data sets:

1. Varied events spanning past/current/future.
2. One role per grantable `PermissionKey`, each granting exactly one permission.
3. One member user per single-permission role, holding only that role. Users are
   **onboarding-complete** (logged-in-ready) and carry a **variety of
   profile-completeness conditions** so staging exercises those states.

## Approach

A dedicated, idempotent Django management command `seed_staging`, separate from
the existing `seed` command so `make seed` never emits demo accounts. Data
constants live in a sibling `_seed_staging_data.py` to keep the command file
lean (file-size rule).

Roles and users are **driven off the `PermissionKey` enum**, so "every grantable
permission is represented" holds by construction — no hand-maintained list.

### Files

- `backend/community/management/commands/seed_staging.py` — orchestrator.
- `backend/community/management/commands/_seed_staging_data.py` — event
  templates, phone-number block, name helpers.
- `backend/tests/test_seed_staging.py` — tests.

### 1. Events

~10 varied events built from templates with `delta_days` spanning past
(negative), current (~0), and future (positive); varied titles, descriptions,
locations, and `event_type`. Titles are prefixed `"[staging] "` so they are
recognizable and scoped. Idempotent via `Event.objects.get_or_create(title=...)`,
matching `seed.py`. `created_by` = the staging admin user (created below), or the
first existing admin if present.

### 2. Single-permission roles

Iterate every `PermissionKey` value:

```python
Role.objects.get_or_create(
    name=f"perm: {key}",
    defaults={"permissions": [key]},
)
```

On re-run the command **reconciles** `role.permissions` to exactly `[key]` so
drift self-heals. Roles are non-default (`is_default=False`).

### 3. One user per role

Phone numbers in a reserved staging block `+1702555_01NN` (index-based),
disjoint from the dev seed users at `+1702555000x`, so the command never touches
real or dev accounts. Each user:

- `is_member=True` (required by the `reject_role_for_non_member` m2m signal).
- **Onboarding complete**: `needs_onboarding=False`, `onboarded_at` set,
  `set_password(PASSWORD)` — logged-in-ready, not magic-link/onboarding-pending.
- `display_name = f"perm: {key}"`.
- Assigned **only** its single-permission role via `user.roles.add(role)`. There
  is no "member role required" enforcement on direct `.add()` (only the API path
  enforces that), so the user holds exactly one role — matching AC.

Idempotent via `get_or_create(phone_number=...)`; role assignment reconciled to
exactly `{role}` on re-run. Profile-condition fields (below) are also reconciled
on re-run so the intended pattern is stable.

### Profile-condition variants

Each user carries one of the profile-completeness patterns formed by three
independent conditions:

- **no email** — `email = None` (has phone, no email).
- **needs guidelines consent** — `guidelines_consent_at = None`.
- **needs sms consent** — `sms_consent_at = None`.

"Complete" for a condition means the opposite: a real email, and a
timestamp (`timezone.now()`) for each consent field. Emails must be **distinct
per user** (the `unique_non_blank_email` partial constraint), so a user with an
email gets a key-derived address like `perm.manage_events@staging.example`.

The 3 booleans give **8 combinations** (all-complete, each single condition, each
pair, all-three). All 8 are assigned deterministically across the 12
per-permission users by index; the remaining 4 users repeat the more interesting
multi-condition patterns (the two-condition and three-condition ones). Every
combination is therefore present at least once.

The pattern for a user is derived from its index (stable, deterministic — no
randomness), so re-runs reproduce the exact same assignment. A small pure helper
in `_seed_staging_data.py` maps `index → (has_email, guidelines_done, sms_done)`.

### Credentials — known shared password

Login is phone + password. Every seeded user gets the same documented password
`testPassword1@` via `set_password()` (passes all `AUTH_PASSWORD_VALIDATORS`:
length ≥ 8, mixed case, not all-numeric, not common, not similar to
phone/display_name). Testers log in directly with the user's phone number + this
password — no magic link, no onboarding step. The printed summary lists each
user's phone so they can be logged into.

### Idempotency & `--reset`

- All creates use `get_or_create` by natural key (title / role name / phone).
- Roles reconcile `permissions`; users reconcile role set. Re-running never
  duplicates and only ever touches its own reserved names/phone block.
- Support a `--reset` flag (per Django-ninja standards) that deletes only the
  staging-scoped rows (roles named `perm: *`, users in the reserved phone block,
  events titled `[staging] *`) before re-seeding. `--reset` never touches
  non-scoped data.

### Output

Summary table printed at the end: each `PermissionKey` → role name → user phone →
profile-condition pattern (email? / guidelines? / sms?). Plus the shared password
and counts of events/roles/users created vs skipped.

## Testing

`backend/tests/test_seed_staging.py`:

- Idempotency: run twice → stable counts, no duplicates.
- One role per `PermissionKey`; each role has exactly one permission equal to its
  key.
- One user per role; each user holds exactly its one single-permission role and
  is a member that is **onboarding-complete** (`needs_onboarding=False`,
  `onboarded_at` set) with a usable password that authenticates.
- All **8 profile-condition combinations** appear across the seeded users
  (assert by collecting each user's `(has_email, guidelines_done, sms_done)`
  tuple and checking the set of 8 is fully covered).
- The condition assignment is deterministic — running twice yields the same
  pattern per user.
- Events created span past/current/future (`start_datetime` before/around/after
  now).
- `--reset` removes only staging-scoped rows and re-seeds cleanly.

## Out of scope

- No frontend changes. `PERMISSION_LABELS` in `RoleFormDialog.tsx` is separate;
  this command surfaces every permission as a role, which incidentally makes any
  missing label visible in the editor, but syncing that mirror is not this task.
- Not wired into any automatic deploy step — run on demand against staging.

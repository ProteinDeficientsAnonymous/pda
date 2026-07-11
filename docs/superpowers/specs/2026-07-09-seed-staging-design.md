# seed_staging — staging demo data (Issue 653)

## Problem

Staging is thin, making it hard to eyeball how calendar/event lists, permission
gating, and the role editor behave with volume and variety. We need realistic
demo data on the **staging** deploy only — not local dev `make seed`, not prod.

Data sets:

1. Varied events spanning past/current/future.
2. One role per grantable `PermissionKey`, each granting exactly one permission.
3. **Per-permission users** — one member per single-permission role, holding only
   that role, with a **complete** profile. All onboarding-complete
   (logged-in-ready).
4. **Profile-condition users** — a *separate* set of members (built-in `member`
   role only) that exercise the **profile-completeness conditions**: one user per
   combination of (no email / needs guidelines consent / needs sms consent). Also
   onboarding-complete. These are in addition to the per-permission users, so
   role/permission testing stays clean and independent of profile-state testing.

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

### Phone-number blocks

All seeded users live in a reserved staging block disjoint from the dev seed
users (`+1702555000x`), so the command never touches real or dev accounts. Two
non-overlapping sub-ranges keep the two groups distinct:

- **Per-permission users**: `+170255501NN` (NN = permission index, 00–11).
- **Profile-condition users**: `+170255502NN` (NN = combination index, 00–07).

### 3. Per-permission users (complete profiles)

One member per single-permission role. Each user:

- `is_member=True` (required by the `reject_role_for_non_member` m2m signal).
- **Onboarding complete**: `needs_onboarding=False`, `onboarded_at` set,
  `set_password(PASSWORD)` — logged-in-ready, not magic-link/onboarding-pending.
- **Complete profile**: a distinct email, `guidelines_consent_at` and
  `sms_consent_at` both set to `timezone.now()`.
- `display_name = f"perm: {key}"`.
- Assigned **only** its single-permission role via `user.roles.add(role)`. There
  is no "member role required" enforcement on direct `.add()` (only the API path
  enforces that), so the user holds exactly one role — matching AC.

Idempotent via `get_or_create(phone_number=...)`; role assignment reconciled to
exactly `{role}` on re-run.

### 4. Profile-condition users (separate set)

A *separate* batch of members whose purpose is exercising profile-completeness
states — independent of permission testing. Three independent conditions:

- **no email** — `email = None` (has phone, no email).
- **needs guidelines consent** — `guidelines_consent_at = None`.
- **needs sms consent** — `sms_consent_at = None`.

"Complete" for a condition means the opposite: a real email and a
`timezone.now()` timestamp for the consent field. The 3 booleans give **8
combinations** (all-complete → each single → each pair → all-three); the set
contains **exactly 8 users, one per combination**.

Each condition user:

- `is_member=True`, onboarding-complete (`needs_onboarding=False`, `onboarded_at`
  set, `set_password(PASSWORD)`).
- Assigned **only the built-in `member` role** (no permission role) — so these
  users add no permission coverage and isolate profile-state testing.
- `display_name` encodes its pattern, e.g. `cond: no-email+needs-sms`.
- Emails must be **distinct per user** (the `unique_non_blank_email` partial
  constraint); a user that has an email gets an index-derived address like
  `cond05@staging.example`.

Combinations are enumerated deterministically (fixed order over the 3 booleans),
so re-runs reproduce the exact same assignment. A small pure helper in
`_seed_staging_data.py` yields the 8 `(has_email, guidelines_done, sms_done)`
tuples. Idempotent + reconciled per re-run like the per-permission users.

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
  staging-scoped rows (roles named `perm: *`, users in **both** reserved phone
  sub-ranges `+170255501xx`/`+170255502xx`, events titled `[staging] *`) before
  re-seeding. `--reset` never touches non-scoped data.

### Running on staging & the production guard

The container entrypoint (`entrypoint.sh`) runs `migrate` then uvicorn — it does
**not** seed. The command is run **on demand** as a Railway one-off against the
staging environment:

```bash
railway run --environment staging python backend/manage.py seed_staging
```

This executes inside the deployed container with staging's real `DATABASE_URL`.
No deploy-config / entrypoint changes are needed.

**Production guard.** The command inspects `RAILWAY_ENVIRONMENT_NAME` — the same
Railway-provided env-name variable `community/_version.py` already reads (values
like `staging` / `production`; unset locally). Note `settings.IS_PRODUCTION`
cannot distinguish staging from prod (it only checks that `RAILWAY_ENVIRONMENT` is
*set*, which is true for both), so the guard keys off the `_NAME` value:

- `RAILWAY_ENVIRONMENT_NAME == "staging"` → run.
- Unset (local dev / CI) → run (so tests and `make`-driven local runs work).
- Any other value (`production`, etc.) → **refuse** with a clear error, unless
  `--force` is passed.

The command prints the detected environment before doing anything so the operator
sees where it is about to seed. A tiny pure helper (`_is_seed_allowed(env_name,
force) -> bool`) makes this unit-testable without env manipulation.

### Output

Two summary tables printed at the end:

- **Per-permission users**: `PermissionKey` → role name → user phone.
- **Profile-condition users**: pattern (email? / guidelines? / sms?) → user phone.

Plus the shared password and counts of events / roles / per-permission users /
condition users created vs skipped.

## Testing

`backend/tests/test_seed_staging.py`:

- Idempotency: run twice → stable counts, no duplicates.
- One role per `PermissionKey`; each role has exactly one permission equal to its
  key.
- One per-permission user per role; each holds exactly its one single-permission
  role, is **onboarding-complete** (`needs_onboarding=False`, `onboarded_at` set)
  with a usable password that authenticates, and has a **complete profile**
  (email + both consent timestamps).
- Exactly **8 profile-condition users** exist (separate from the per-permission
  users), each holding **only the built-in `member` role**, and together they
  cover all 8 `(has_email, guidelines_done, sms_done)` combinations exactly once.
- Condition users are also onboarding-complete with usable passwords.
- The two groups are disjoint (distinct phone sub-ranges; per-permission users
  carry no `member`-only-condition entanglement).
- Assignment is deterministic — running twice yields the same per-user pattern.
- Events created span past/current/future (`start_datetime` before/around/after
  now).
- `--reset` removes only staging-scoped rows and re-seeds cleanly.
- Production guard: `_is_seed_allowed` returns True for `"staging"` and for
  unset/local, False for `"production"`, and True for `"production"` only when
  `force=True`. The command exits non-zero and seeds nothing when the guard
  refuses.

## Out of scope

- No frontend changes. `PERMISSION_LABELS` in `RoleFormDialog.tsx` is separate;
  this command surfaces every permission as a role, which incidentally makes any
  missing label visible in the editor, but syncing that mirror is not this task.
- Not wired into any automatic deploy step — run on demand via a Railway one-off
  (see "Running on staging"). No entrypoint/CI changes.

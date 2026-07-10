# seed_staging — staging demo data (Issue 653)

## Problem

Staging is thin, making it hard to eyeball how calendar/event lists, permission
gating, and the role editor behave with volume and variety. We need realistic
demo data on the **staging** deploy only — not local dev `make seed`, not prod.

Three related data sets:

1. Varied events spanning past/current/future.
2. One role per grantable `PermissionKey`, each granting exactly one permission.
3. One member user per single-permission role, holding only that role.

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
- `needs_onboarding=True`, `set_unusable_password()` — real onboarding path.
- `display_name = f"perm: {key}"`.
- Assigned **only** its single-permission role via `user.roles.add(role)`. There
  is no "member role required" enforcement on direct `.add()` (only the API path
  enforces that), so the user holds exactly one role — matching AC.

Idempotent via `get_or_create(phone_number=...)`; role assignment reconciled to
exactly `{role}` on re-run.

### Credentials — magic-link onboarding

Login is phone + password, and seeded users have an unusable password. On **every
run**, the command (re)issues a fresh `MagicLoginToken` per user
(`MagicLoginToken.create_for_user`) and prints the onboarding URL. Following the
link lands the user on `/onboarding` to set their own password — the real
first-login flow. The printed table (permission → role → phone → onboarding URL)
is how staging testers log in.

The onboarding base URL comes from a settings/env value (site URL); default to a
relative `/onboarding?...` path if unset, and always print the raw token so the
URL can be assembled by hand on staging.

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
onboarding magic-link (or token). Plus counts of events/roles/users created vs
skipped.

## Testing

`backend/tests/test_seed_staging.py`:

- Idempotency: run twice → stable counts, no duplicates.
- One role per `PermissionKey`; each role has exactly one permission equal to its
  key.
- One user per role; each user holds exactly its one single-permission role and
  is a member with `needs_onboarding=True` and an unusable password.
- Events created span past/current/future (`start_datetime` before/around/after
  now).
- A fresh `MagicLoginToken` exists per user after a run.
- `--reset` removes only staging-scoped rows and re-seeds cleanly.

## Out of scope

- No frontend changes. `PERMISSION_LABELS` in `RoleFormDialog.tsx` is separate;
  this command surfaces every permission as a role, which incidentally makes any
  missing label visible in the editor, but syncing that mirror is not this task.
- Not wired into any automatic deploy step — run on demand against staging.

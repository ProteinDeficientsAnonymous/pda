# Explore: Investigate an `is_admin` concept to simplify admin/permission checks (#530) — Findings

**Date:** 2026-06-24
**Issue:** https://github.com/ProteinDeficientsAnonymous/pda/issues/530
**Branch / PR:** `auto-530-is-admin-explore` (draft PR linked from the issue)

## The ask

Raised in review of PR #521. A handful of recipient/permission queries express
"is this user an admin-or-event-manager" with a repeated two-part `Q` filter, e.g.
`backend/notifications/service.py:159`:

```python
UserModel.objects.filter(
    Q(roles__name="admin", roles__is_default=True)
    | Q(roles__permissions__contains=PermissionKey.MANAGE_EVENTS)
).distinct()
```

The reviewer asked whether we can stop repeating this `admin role OR permission`
check. One idea floated was an `is_admin` flag, true only for the role literally
named `admin`, so call sites do a clean `is_admin` check. This is an
**investigation, not a directed change** — output is a recommendation, no
production behavior change in this issue.

Acceptance criteria:
1. Enumerate every site that hand-rolls the `admin role OR <permission>` filter.
2. Evaluate options (derived property/manager, stored field, permission-only, leave as-is) with trade-offs.
3. Recommend one approach with a migration/refactor sketch and blast radius.
4. No production behavior change here.

## What we found

### The model already treats "admin" as "has every permission"

The admin role is identified **consistently** by the pair `name == "admin"
AND is_default == True` — never by name alone. Two places already encode "admin
grants everything":

- `Role.effective_permissions` (`backend/users/roles.py:28-38`): if the role is
  the default admin role, returns the full `PermissionKey.values` set; otherwise
  returns the stored `permissions` list.
- `User.has_permission()` (`backend/users/models.py:99-112`): iterates the user's
  roles; if any role is the default admin role it returns `True` for *any* key,
  otherwise checks membership in that role's `permissions` list. It uses the
  prefetch cache when available to avoid N+1 in list views.

Because of this, **the vast majority of admin/permission call sites are already
clean**: they call `request.auth.has_permission(PermissionKey.X)` and the admin
short-circuit inside `has_permission` does the right thing. There were ~56 such
call sites across `users/` and `community/`, and none of them repeat the compound
filter — they are already terse and correct.

### Only three sites hand-roll the compound `Q` filter — all in one file

The repeated `admin role OR permission` pattern the issue calls out exists in
**exactly three places, all in `backend/notifications/service.py`**, and all three
are *queryset* filters ("find the set of users who should receive this
notification"), not boolean checks on a single user:

| # | Location | Permission OR'd with admin | Asking |
|---|---|---|---|
| 1 | `notifications/service.py:133-136` | `APPROVE_JOIN_REQUESTS` | who to notify of a new join request |
| 2 | `notifications/service.py:159-162` | `MANAGE_EVENTS` | who to notify of a flagged event |
| 3 | `notifications/service.py:186-189` | `APPROVE_JOIN_REQUESTS` | who to notify of a magic-link request |

These can't reuse `has_permission()` directly because that method tests a single
user in Python, whereas these need a single DB query returning the recipient set.
This is the real, narrow problem: **the compound filter is duplicated three times
because there is no queryset-level "users who can do X" helper.**

### A helper for the boolean check already exists (but not for querysets)

`backend/users/_helpers.py:49-51` already has the single-user admin check:

```python
def _is_admin(user: User) -> bool:
    """True if the user holds the built-in admin role."""
    return user.roles.filter(name="admin", is_default=True).exists()
```

It's used by the admin-protection guards (`_guard_admin_role_grant`,
`_validate_admin_role_change`, `_is_last_admin`, pause validation). So the
single-user case is already centralized; only the *queryset* case is duplicated.

### The frontend already mirrors this correctly without an `is_admin` field

The frontend re-implements the same derivation in
`frontend/src/models/permissions.ts`:

- `hasPermission(user, key)` (`:44-49`) returns true if any role grants the key
  **or** the user holds the role named `ADMIN_ROLE_NAME` (`'admin'`, `:23`) with
  `isDefault`.
- `hasAnyAdminPermission(user)` (`:51-54`) rolls up the admin-ish permissions.

The API already serializes everything the client needs to derive admin status:
`UserOut.roles` carries `is_default` + `permissions` per role
(`backend/users/schemas.py:55-82`, mirrored in
`frontend/src/api/types.gen.ts` `RoleOut`/`UserOut`). There is **no `is_admin`
field on the wire today**, and none is needed for the frontend to know who's an
admin — `MemberDetailScreen.tsx` derives `targetIsAdmin` from
`member.roles.some(r => r.name === ADMIN_ROLE_NAME && r.isDefault)`.

### Data-integrity reality: "one admin role" is convention, not a constraint

- `Role.name` is unique; `is_default` has **no** uniqueness constraint
  (`backend/users/migrations/0002_add_role_model.py`). Multiple roles could in
  principle carry `is_default=True` (member and admin both do — see
  `0003_seed_default_roles.py`).
- The "exactly one default admin role" invariant is enforced only by convention:
  the seed migration, the seed command
  (`backend/community/management/commands/seed.py:304`), and the superuser
  post-save signal (`backend/users/models.py:143-151`) all assume
  `Role.objects.get(name="admin", is_default=True)` resolves to one row.
- Latest migration is `0027_user_sms_consent_at.py`; a new field migration would
  be `0028`.

### Tests pin the current semantics

A refactor must preserve at least:

- `test_admin_role_grants_all_permissions` (`backend/tests/test_api.py:127-132`) —
  admin role ⇒ `has_permission` true for any key.
- `test_notifies_admin_role_user` (`backend/tests/test_in_app_notifications.py:392`)
  — admin-role users receive join-request notifications.
- `test_no_duplicate_for_user_with_admin_and_explicit_permission`
  (`backend/tests/test_in_app_notifications.py:404`) — a user who is *both* admin
  and has the explicit permission gets **one** notification, not two. Any
  queryset-helper refactor must keep the `.distinct()` semantics.
- Admin-protection tests (`_guard_admin_role_grant`, `_is_last_admin`,
  superuser auto-assignment) around `backend/tests/test_api.py:137-428`.

## Relevant code

| Area | Location | Role |
|---|---|---|
| Role model + admin grant | `backend/users/roles.py:14-38` | `name`/`is_default`/`permissions`; `effective_permissions` grants all for admin |
| Permission enum | `backend/users/permissions.py:4-17` | `PermissionKey` values incl. `MANAGE_EVENTS`, `APPROVE_JOIN_REQUESTS` |
| Single-user permission check | `backend/users/models.py:99-112` | `has_permission()` with admin short-circuit + prefetch cache |
| Single-user admin check (exists) | `backend/users/_helpers.py:49-51` | `_is_admin()` — already centralized |
| **Compound filter site 1** | `backend/notifications/service.py:133-136` | join-request recipients |
| **Compound filter site 2** | `backend/notifications/service.py:159-162` | event-flag recipients |
| **Compound filter site 3** | `backend/notifications/service.py:186-189` | magic-link recipients |
| Superuser → admin signal | `backend/users/models.py:143-151` | assumes one default admin role |
| Seed | `backend/community/management/commands/seed.py:304` | `get_or_create(name="admin", ...)` |
| Role/User serialization | `backend/users/schemas.py:55-82` | `RoleOut`/`UserOut`; no `is_admin` on the wire |
| Frontend mirror | `frontend/src/models/permissions.ts:23-54` | `hasPermission`/`hasAnyAdminPermission`/`ADMIN_ROLE_NAME` |
| Notification recipient tests | `backend/tests/test_in_app_notifications.py:392-413` | de-dup + admin recipient invariants |

## Options

### (a) Derived helper — add a queryset method `User.objects.with_permission(key)`

Add a manager/queryset method that returns the *set of users* who hold a given
permission, encapsulating the admin short-circuit once:

```python
# users/models.py (UserQuerySet / UserManager)
def with_permission(self, key: str):
    return self.filter(
        Q(roles__name="admin", roles__is_default=True)
        | Q(roles__permissions__contains=key)
    ).distinct()
```

The three notification sites collapse to
`User.objects.with_permission(PermissionKey.MANAGE_EVENTS)` etc. This is the
queryset analogue of the existing `has_permission()` / `_is_admin()` helpers.

- **Pro:** removes the duplication exactly where it lives; one source of truth for
  "users who can do X"; zero drift (always derived from roles); no migration;
  preserves `.distinct()` semantics so the de-dup test stays green; mirrors a
  pattern the codebase already uses (`has_permission`, `effective_permissions`,
  `_is_admin`).
- **Con:** doesn't introduce a literal `is_admin` token, so a call site that
  *specifically* wants "is this user the admin" still uses `_is_admin()` (already
  fine). Slightly more than "leave as-is."

### (b) Stored `User.is_admin` boolean kept in sync with the admin role

Add a real column, backfilled and maintained by M2M signals.

- **Pro:** dead-simple `Q(is_admin=True)` at call sites.
- **Con:** introduces a **second source of truth** that must be kept in sync with
  `roles` on every M2M change, superuser creation, role rename/delete, and the
  backfill migration. High drift risk: a user could be `is_admin=True` without the
  role (or vice-versa), silently breaking auth. It also only addresses the *admin*
  half of the compound filter — the three real sites are `admin OR <permission>`,
  so `is_admin` alone wouldn't remove the `Q(...permissions__contains...)` half.
  Net: more moving parts, more risk, doesn't fully solve the stated problem.

### (c) Permission-only — drop the special-cased admin role; give admin every permission key explicitly

Stop checking `name == "admin"` anywhere; instead store the full permission list
on the admin role and rely solely on `permissions__contains`.

- **Pro:** removes the name-based special case; a single uniform mechanism.
- **Con:** large, behavior-affecting refactor touching `has_permission`,
  `effective_permissions`, the admin-protection guards, and the seed/migration
  path. The admin role's stored `permissions` is currently *ignored* by design
  (so it can't drift out of date with newly-added keys); option (c) would make it
  load-bearing and require a migration to keep it exhaustive forever. This trades
  one well-contained special case for a brittle "remember to add every new key to
  the admin row" obligation. Out of proportion to a 3-site duplication.

### (d) Leave as-is

- **Pro:** zero work, zero risk.
- **Con:** the duplication remains; the next reviewer asks the same question; a
  future caller copy-pastes the compound filter a fourth time and risks dropping
  the `.distinct()` or mis-typing the admin pair.

## Recommendation

**Adopt option (a): a derived `User.objects.with_permission(key)` queryset helper**
(naming TBD — see Open Questions). It is the smallest change that actually solves
the stated problem, it has **no drift risk** (purely derived from roles), needs
**no migration**, and it fits the existing pattern language of the codebase
(`has_permission`, `effective_permissions`, `_is_admin` are all derived). It
preserves every pinned test, including the `.distinct()` de-dup invariant.

Explicitly **reject the stored `is_admin` field (b)**: it adds a second source of
truth and synchronization burden for a 3-site duplication, and — because the real
sites are `admin OR <permission>`, not pure admin — it wouldn't even remove the
`permissions__contains` half. The frontend likewise needs no `is_admin` field; it
already derives admin status from the serialized roles.

### Refactor sketch (for the follow-up implementation issue — not done here)

1. Add a `UserQuerySet`/`UserManager` with
   `with_permission(key) -> QuerySet[User]` wrapping the compound `Q` + `.distinct()`,
   defined once (`backend/users/models.py`). Keep the admin pair
   (`name="admin", is_default=True`) identical to today's three sites so behavior
   is byte-for-byte equivalent.
2. Replace the three `notifications/service.py` filters
   (`:133-136`, `:159-162`, `:186-189`) with calls to the new helper.
3. (Optional, same PR) add a thin `User.objects.admins()` for the pure-admin
   queryset case if any future site needs it; not required by the three sites.
4. Tests: existing `test_in_app_notifications.py` recipient tests already cover the
   behavior; add one direct unit test for `with_permission` (admin user + perm
   user + neither → correct set, no duplicates).

**Blast radius:** one new method in `backend/users/models.py`; three call-site
edits in `backend/notifications/service.py`; one new test. **No migration, no
schema change, no frontend change, no API change.** Roughly 2 files of production
code + 1 test.

## Open questions

- **Helper name/shape.** `User.objects.with_permission(key)` vs.
  `User.objects.who_can(key)` vs. a module-level function in
  `notifications/service.py`. A manager method reads best and is most reusable,
  but the exact name is a style call for the implementer/reviewer. (Does not block
  the recommendation; only the label.)
- **Should the helper live on a custom `UserManager`/`UserQuerySet`?** The User
  model currently has no custom queryset (only the inherited manager). Adding one
  is the idiomatic Django home for this, but it's a slightly larger touch than a
  free function. Recommend the manager/queryset for reuse; flagging because it's
  the one non-trivial structural choice.
- **Do we want a literal `is_admin`/`is_admin()` anywhere?** The single-user case
  is already covered by `_helpers._is_admin`. If a future caller wants the boolean
  on the model itself (e.g. `request.auth.is_admin`), a thin `@property` wrapping
  `_is_admin(self)` would be cheap and drift-free — but no current site needs it,
  so it's deliberately left out of the recommendation to keep scope minimal.
- **Confirm no production behavior change is intended in the follow-up** beyond
  de-duplication. This spike assumes the follow-up is a pure refactor that keeps
  the exact admin-pair + `.distinct()` semantics; if the team instead wants to,
  e.g., stop special-casing the admin role (option c), that's a different, larger
  decision.

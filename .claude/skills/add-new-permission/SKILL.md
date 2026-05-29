---
name: add-new-permission
description: Add a new permission key to the PDA app — the backend PermissionKey enum and the frontend Permission mirror, kept in sync. Use when you need a new role-grantable permission. Does NOT build a page or endpoint; for a permission-gated editable page use add-permission-gated-page.
argument-hint: "<permission_key> [\"Human label\"]"
---

# Add a New Permission Key

Adds a single permission key to PDA in the two places it must exist: the Django
`PermissionKey` enum (backend source of truth) and the TypeScript `Permission` object
(hand-maintained frontend mirror). These two MUST stay in sync — there is no codegen.

This skill only adds the key. A permission does nothing on its own until:
- a **role** grants it (managed at runtime via the roles UI / `manage_roles`), and
- some **endpoint** checks it (`request.auth.has_permission(...)`) and/or some **UI** gates
  on it (`hasPermission(user, Permission.X)`).

If you want a full permission-gated editable page wired end-to-end, use
**`add-permission-gated-page`** instead — it includes this step.

## Arguments

- `permission_key` — snake_case, e.g. `edit_resources` or `manage_sponsors`.
- `Human label` — optional; the admin-facing label (defaults to a title-cased key).

Derive before starting:
- `PERM_CONST` = SCREAMING_SNAKE of the key, e.g. `EDIT_RESOURCES`
- `PermCamel` = PascalCase of the key, e.g. `EditResources`

## Step 1 — Backend enum: `backend/users/permissions.py`

Add a member to the `PermissionKey(models.TextChoices)` class:

```python
EDIT_RESOURCES = "edit_resources", "Edit resources"
```

The enum is **grouped logically, NOT alphabetical.** Place the new key with its peers:
- `EDIT_*` content keys (`EDIT_FAQ`, `EDIT_GUIDELINES`, `EDIT_HOMEPAGE`, …) go together.
- `MANAGE_*` admin keys go together.

Match the closest existing group rather than appending blindly.

## Step 2 — Frontend mirror: `frontend/src/models/permissions.ts`

Add a matching entry to the `Permission` object. **The string value must equal the backend
key exactly** — this is the contract between the two files:

```ts
export const Permission = {
  // ...
  EditResources: 'edit_resources',
  // ...
} as const;
```

Do not touch `hasPermission()` — it already works for any key by membership check.

## Step 3 — Verify

```bash
make ci
```

`make ci` runs backend lint/typecheck/tests and the frontend build/tests. A new key alone
shouldn't break anything; if a test enumerates all permission keys, update it to include
the new one.

## Notes / gotchas

- **Sync is manual.** `backend/users/permissions.py` and `frontend/src/models/permissions.ts`
  are two independent sources that mirror each other. Changing one without the other is the
  most common mistake — always edit both.
- The frontend value is the *string*, not the constant name: `EditResources: 'edit_resources'`.
- A key with no role granting it and no code checking it is dead weight — make sure something
  downstream actually uses it (see `add-permission-gated-page`).

## Files touched

| File | Change |
|------|--------|
| `backend/users/permissions.py` | Add `PermissionKey` member (in its logical group) |
| `frontend/src/models/permissions.ts` | Add matching `Permission` entry (same string) |

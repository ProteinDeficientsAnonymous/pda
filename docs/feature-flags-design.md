# Feature flags — design

Resolves the spike in Issue 874 (decouple feature work from bug-fix releases via dark deploys). This is the design of record; the implementation epic and its child issues are derived from it.

## Goal

Let incomplete features merge to `main` and deploy dark, so bug fixes ship on their own cadence instead of waiting on half-finished feature work. A flag is a named on/off switch, defined in code, whose state is toggleable per environment (`local` and `staging`) from the admin UI, and never toggleable on `production`.

Two hard requirements from the user:
1. **Adding a flag is trivial** — one line, type-safe, autocompletes at the call site.
2. **Admin UI to toggle flags exists on `local` + `staging` only; hidden on `production`.**

## Core architecture: code-defined registry + per-environment DB state

Flags are **defined in code** (a typed enum with a hardcoded default), and their **on/off state is stored per-flag in the database**. Because each environment (`local`, `staging`, `production`) already has its own database, per-environment state is automatic — no environment column, no cross-env leakage.

- **Definition (code):** the set of flags, their keys, and their default value live in a `FeatureFlag` `TextChoices` enum on the backend, mirrored by a frozen `Feature` const on the frontend. Admins **toggle** flags; they never create, name, or delete them. This is what makes "add a flag = one line" and `useFlag(Feature.X)` type-safe.
- **State (DB):** a per-flag row `FeatureFlagState(key unique, enabled)`. Resolution: DB row if present, else the code default. Rows for unknown/removed keys are ignored. This mirrors the existing `EditablePage` per-slug pattern in `community/models/content.py`, not the single-blob singleton.

Why this over the alternatives:
- **vs. a hosted provider (Railway flags / LaunchDarkly / etc.):** rejected. Adds a dependency, an outage surface, and per-request network cost for a community app at small scale. #874's own framing ("lightweight in-house") and the codebase's self-hosted-everything posture point in-house. The whole need is "toggle a boolean per environment" — a DB row does that.
- **vs. admin-created flags (free-text keys, rows are the source of truth):** rejected. Loses type-safety, loses "delete the enum member to find every call site," and invites permanent flag debt. Code-defined is the ergonomic win the user asked for.
- **vs. a single-row JSON blob singleton (`content.py` `WhatsAppLinkConfig` style):** rejected. Per-flag rows give clean per-flag audit/`updated_at`, avoid read-modify-write races on one row, and let unknown keys be ignored individually.

## Environment scoping — the "not on prod" gate

The three-way environment name is `RAILWAY_ENVIRONMENT_NAME` → `"local"` / `"staging"` / `"production"` (unset ⇒ `"local"`), already exposed publicly at `GET /api/community/version/` in the `environment` field. Do **not** use `settings.IS_PRODUCTION` — it is `True` on staging too (it only means "on Railway at all") and cannot express "local + staging only."

Gate on an **allowlist** (`environment in {"local", "staging"}`), never a blocklist, so an unknown/new environment name never accidentally exposes toggling on prod.

Two enforcement layers (both required; the client one is UX, the server one is the boundary):
- **Backend (real gate):** the write endpoint returns `403` when `environment == "production"` (in addition to the permission check). Reads stay allowed everywhere (prod just reads code defaults).
- **Frontend (UX):** the admin tile + route are hidden when `environment === "production"`, read from `useVersion()`.

Add a settings constant next to `IS_PRODUCTION` for reuse:
```python
ENVIRONMENT_NAME = os.environ.get("RAILWAY_ENVIRONMENT_NAME") or "local"
FLAG_TOGGLING_ALLOWED = ENVIRONMENT_NAME in ("local", "staging")
```

## Backend

Lives in the `community` app, following the split-`_file` router convention.

- **Model** — `community/models/feature_flag.py`, re-exported in `community/models/__init__.py`:
  ```python
  class FeatureFlagState(models.Model):
      key = models.CharField(max_length=100, unique=True)
      enabled = models.BooleanField(default=False)
      updated_at = models.DateTimeField(auto_now=True)
  ```
  `AutoField` PK (not UUID — matches the config-model precedent). No `enabled` default assumption in resolution: the *code* default (from the enum) wins when no row exists.
- **Registry** — `FeatureFlag(models.TextChoices)` in `community/models/choices.py`, plus a small `FLAG_DEFAULTS: dict[str, bool]` mapping (or a `default` carried alongside each member). Resolution helper `resolve_flags() -> dict[str, bool]`: start from defaults, overlay DB rows whose key is a known member.
- **Read endpoint** — `GET /api/community/feature-flags/`, `auth=None`, returns `{ "flags": { key: bool, ... } }` (all known flags, resolved). Public so anon UI can gate too.
- **Write endpoint** — `PATCH /api/community/feature-flags/{key}/`, `auth=gated_jwt`, body `{ "enabled": bool }`:
  1. `403` if `not settings.FLAG_TOGGLING_ALLOWED` (prod gate).
  2. `403` if `not request.auth.has_permission(PermissionKey.MANAGE_FEATURE_FLAGS)` (with `audit_log` + `raise_validation`, per the guidelines endpoint pattern).
  3. `422`/`404` if `key` is not a known `FeatureFlag` member.
  4. `get_or_create(key=key)`, set `enabled`, save; `audit_log` the change; return resolved state.
- **Router** — new `community/_feature_flags.py` (`router = Router()`), one line in `community/api.py`: `router.add_router("", feature_flags_router)`.
- **Permission** — add `MANAGE_FEATURE_FLAGS = "manage_feature_flags", "Manage feature flags"` to `PermissionKey` (grouped with the other `MANAGE_*`).
- **Backend consumption** — a `flag_enabled(FeatureFlag.X) -> bool` helper for gating endpoint logic when a dark feature has server behavior. Reads the resolved map (cache within request is fine; flags change rarely).

## Frontend

Server-driven ⇒ **no Zustand store**; TanStack Query cache is the global state, mirroring `useRoles` / `useHasPermission`.

- **Registry mirror** — `frontend/src/models/featureFlags.ts`: a frozen `Feature` const + `FeatureFlagKey` union (clone of `models/permissions.ts`). String values must equal the backend keys exactly.
- **API hook** — `frontend/src/api/featureFlags.ts`: `useFeatureFlags()` (`useQuery(['feature-flags'], GET /api/community/feature-flags/)`, `staleTime` generous — flags change rarely) + `useSetFeatureFlag()` mutation (`PATCH`, `onSuccess` → `invalidateQueries(['feature-flags'])`).
- **Consumption hook** — `useFlag(key: FeatureFlagKey): boolean` — one-liner reading the cached query, mirrors `useHasPermission`. Missing/loading ⇒ `false` (fail-closed: a dark feature stays dark until proven on).
- **Route guard** — `RequireFlag` in `auth/guards.tsx`, cloned from `RequirePermission` (redirect to `/calendar` when the flag is off). For gating whole routes behind a dark feature.
- **Admin screen** — `frontend/src/screens/admin/FeatureFlagsScreen.tsx`: lists every `Feature` with a `Toggle` (the existing `components/ui/Toggle.tsx` switch), wired to `useSetFeatureFlag`. Shows the current environment. Renders read-only note if somehow reached on prod.
- **Admin tile + route** — an `AdminHub` tile gated by `Permission.ManageFeatureFlags` **and** `environment !== "production"` (via a new `useVersion()` hook reading `GET /api/community/version/`); a `RequirePermission perm={Permission.ManageFeatureFlags}` route in `router/routes.tsx`.
- **RBAC sync** — add `ManageFeatureFlags` to `models/permissions.ts` and to `PERMISSION_LABELS` in `RoleFormDialog.tsx` (else silently ungrantable). The `add-new-permission` skill covers the enum+mirror sync.

## Developer ergonomics — adding and removing a flag

**Add a flag (the one-line promise):**
1. Add one member to `FeatureFlag` (backend `choices.py`) with its default.
2. Add the matching member to `Feature` (frontend `featureFlags.ts`).
3. Use it: `useFlag(Feature.X)` / `flag_enabled(FeatureFlag.X)` / `<RequireFlag flag={Feature.X}>`.

No migration, no admin data entry, no endpoint change — the read/write endpoints are generic over the registry, and the admin screen renders every member automatically. (The registry is two hand-synced files, exactly like permissions; a tiny `feature_flags.test` parity test asserts the two enums match, same spirit as the permission-parity checks.)

**Remove a flag (avoid permanent flag debt):**
When a feature fully launches, **delete the enum member** in both files. TypeScript and Python then fail to compile at every call site — the compiler hands you the cleanup list. Delete the gating, delete the flag. Stale DB rows for removed keys are inert (ignored by resolution) and can be dropped later; no migration is required to remove a flag. Convention, stated in the spec and the epic: **a flag is temporary by default.**

## Testing

- **Backend:** parametrize both flag states. Toggle by writing a `FeatureFlagState` row (or a small `set_flag(key, enabled)` test helper). Cover: read endpoint resolves defaults + overrides; write endpoint 403 on prod env (monkeypatch `settings`), 403 without permission, 404/422 on unknown key, happy path flips the row; `resolve_flags` ignores unknown DB rows. Follows `test_docs.py` gated-endpoint shape.
- **Frontend:** mock `@/api/client`; test `useFlag` returns the resolved boolean and fail-closed default; test `RequireFlag` redirect; test the admin screen renders a toggle per flag and calls the mutation. Follows `api/content.test.ts` + guard-test patterns.
- **Parity:** one test asserting the backend `FeatureFlag` keys and frontend `Feature` values match (guards the two-file sync).

## Decisions made (resolved, not deferred)

- **Targeting is environment-scoped only** — no per-user / per-role / percentage rollout. #874 lists those as "if warranted"; the stated use case (dark-deploy per environment) doesn't warrant them, and RBAC already covers per-role access gating. *Deferred, not designed out:* if per-user targeting is later needed, it's an additive `FeatureFlagState` extension, not a rearchitecture.
- **Prod is read-only for flags, not flag-free** — prod evaluates flags (from code defaults, or its own DB rows if ever seeded by a migration), it just can't toggle them from the UI. This is what lets a feature ship "on" to prod: flip the default to `True` in code, or seed the prod row via a data migration, then delete the flag once stable.
- **Fail-closed** — unknown/missing/loading flag ⇒ `False`. A dark feature must never flicker on by accident.
- **No new app, no new dependency** — everything lives in `community` + `users`, reusing the singleton-config, RBAC, and TanStack-Query patterns already in the codebase.

## Rollout as an epic

Implementation is sequenced so each PR is independently shippable and the flag system is usable as early as possible:

1. **Backend foundation** — settings constant, `FeatureFlag` registry + `FeatureFlagState` model + migration, `resolve_flags`/`flag_enabled` helpers, read + write endpoints, `MANAGE_FEATURE_FLAGS` permission, backend tests. (Delivers a working, curl-able flag system.)
2. **Frontend read path** — `Feature` mirror, `useFeatureFlags`/`useFlag`, `RequireFlag`, parity test. (Delivers flag consumption in the app.)
3. **Admin UI** — `useVersion` hook, `FeatureFlagsScreen`, tile + route, env-hiding, permission mirror + role-editor label, tests. (Delivers the toggle UI.)
4. **Docs + first real flag (optional / demonstrative)** — a short "how to add/remove a flag" doc and, if useful, converting one in-flight feature to a flag as the reference example.
```

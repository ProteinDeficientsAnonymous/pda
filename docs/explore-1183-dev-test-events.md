# Explore: Add dev-only tab for quickly creating test events (#1183) — Findings

**Date:** 2026-07-31
**Issue:** https://github.com/ProteinDeficientsAnonymous/pda/issues/1183
**Branch / PR:** `explore-1183-dev-test-events`

## The ask

Manually creating events for testing is tedious. The issue asks for a dev-only tab
exposing a quick "create test event" action, visible on local dev and staging,
never reachable in production — with the gate enforced on the backend, not just
hidden in the UI. Minimal defaults, a few overridable fields, ideally a way to
create several at once, created events obviously identifiable as test data, and
all user-facing text lowercase.

## What we found

**The environment gate is the crux of this issue, and the codebase has exactly one
correct way to do it plus one very tempting wrong way.**

`settings.IS_PRODUCTION` (`backend/config/settings.py:12`) is a misnomer:
`os.environ.get("RAILWAY_ENVIRONMENT") is not None` is **true on staging**, because
staging is itself a Railway deployment. Gating on `not IS_PRODUCTION` would hide the
feature on staging — the primary place the issue wants it. The only reliable
staging-vs-production discriminator is `RAILWAY_ENVIRONMENT_NAME`, read in exactly
one place today: `backend/community/_version.py:21`, defaulting to `"local"`.

The precise predicate this issue needs is **already written and already tested**:

```python
def is_seed_allowed(env_name: str | None, force: bool) -> bool:
    """Allow local/unset and staging; refuse any other env unless forced."""
    if not env_name or env_name == "staging":
        return True
    return force
```

`backend/community/management/commands/_seed_staging_data.py:92-96`, called from
`seed_staging.py:55-60`, with a production-refusal test at
`backend/tests/test_seed_staging.py:211`. It is an allow-list, not a
`!= "production"` deny-list, so a new or typo'd environment name fails closed.

**The frontend cannot gate this at build time.** `frontend/src/config/env.ts:1-5` is
the entire frontend config module, and `VITE_API_URL` is the only `import.meta.env`
usage in the whole app — and it is never actually set anywhere. `Dockerfile:10` runs
`pnpm build:docker` with no build args, so **staging and production build the
identical image from the same `main` commit**. A `VITE_` flag or `import.meta.env.DEV`
therefore cannot distinguish staging from production. Any staging-visible gate must
come from the server at runtime.

That runtime channel already exists: `GET /api/community/version/`
(`backend/community/_version.py:18-30`, `auth=None`) returns `environment`, consumed
by `useVersion()` at `frontend/src/api/version.ts:17-30` with `staleTime: Infinity`,
and already rendered by `FeatureFlagsScreen.tsx:26`. The frontend can learn its
environment with zero new plumbing.

**Creating events does not spam anyone — with one caveat.** The issue's implicit
worry about notification fan-out on staging is narrower than feared.
`create_event` (`backend/community/_events.py:303-372`) has exactly three side
effects beyond the ORM write: `_set_event_participants`, `_set_event_tags`, and
`audit_log`. It does **not** call `broadcast_event_update` — the production call
sites are `_event_helpers.py:71` (the PATCH/update path) and `notifications/service.py:63`
(a comment-related live-update ping), neither on create. Membership-wide notification
fan-out happens at *publish* (`_event_transitions.py:104-106`) and *cancel*
(`_event_transitions.py:30`), not create.

The one real spam vector is `_set_event_participants`
(`_event_transitions.py:72-87`), which fires only when `co_host_ids` is non-empty —
and then sends both in-app notifications **and real cohost-invite emails**. A dev
endpoint must hard-code `co_host_ids=[]`.

**The reuse-the-existing-endpoint option is undermined by a rate limit.**
`create_event` carries `@rate_limit(key_func=..., rate="10/d")` at `_events.py:308` —
ten per **day** per user. A dev "spin up test events" button that reuses it is
useless after ten clicks, which defeats the entire point of the issue.

**Defaults already exist in the seed layer.** `SeedEvent`
(`_seed_shared.py:12-22`) is precisely the shape the issue describes: title,
description, `delta_days`, `duration_hours`, location, plus `event_type=COMMUNITY`,
`visibility=PUBLIC`, `rsvp_enabled=False`. `seed_events()` (`_seed_shared.py:25-42`)
computes `start = now + delta_days`, `end = start + duration_hours`, and uses
`get_or_create(title=...)` — idempotent by title. `e2e_seed.py:_random_event` is a
second precedent using `secrets.token_hex(4)` for unique titles.

`seed_staging.py:87` establishes the **title-prefix convention** for test data:
`Event.objects.filter(title__startswith="[staging] ").delete()`. That directly
satisfies the issue's "obviously identifiable as test data" criterion and gives a
free cleanup story.

**Surface placement.** The bottom nav is the wrong home: `BottomNav.tsx:26` is a
hardcoded `grid-cols-5` with inline JSX slots and no declarative item array, so a
conditionally-rendered sixth tab makes the grid reflow between environments.
`AdminHubScreen.tsx:14-69` is tile-driven and filtered by `hasPermission` at `:73` —
the natural extension point, though `Tile.perm` is a required `PermissionKey`
(`:11`) with no natural value for a dev tile. `PdaMenuSheet.tsx:19-30` is also
array-driven (`ALWAYS_ITEMS` / `AUTHED_ITEMS`, merged at `:51`) and is the cheapest
conditional-append surface.

The feature-flags feature is the closest precedent for the whole wiring trio —
commit `9d9b96f0`, 271 lines added, zero deleted: lazy route import
(`routes.tsx:58`) + guard block (`:173-176`), hub tile (`AdminHubScreen.tsx:63-68`),
and a 44-line screen. There is even a codified `.claude/skills/add-permission-gated-page/`
skill for this path.

**Feature flags are not a substitute for the env gate.** The system landed fully on
main (`backend/community/models/choices.py:105-117`, `_feature_flags.py`,
`frontend/src/models/featureFlags.ts`), but it is deliberately environment-agnostic:
`backend/tests/test_feature_flags.py:77-85` is literally named
`test_update_flag_allowed_on_production` and asserts a flag *can* be enabled in prod.
Anyone with `manage_feature_flags` could switch a dev-tools flag on in production. A
flag may be AND-ed with an env check, never used in place of one.

**Codegen risk if the router is conditionally registered.**
`make frontend-types` → `dump_openapi_schema` imports `config.urls` and introspects
the live API (`dump_openapi_schema.py:33-35`); `--check` diffs the committed JSON and
exits 1 on mismatch (`:38-42`), wired into CI via `make check-codes`
(`Makefile:243-246`). If a dev router is registered conditionally on an env var, the
committed `openapi_schema.json` and CI's regeneration will disagree and fail. No
router is conditionally registered anywhere today — every `add_router` call in
`config/urls.py:11-16` and `community/api.py:56-101` is unguarded.

Mitigating: only two files import from `types.gen.ts` (`eventBlast.ts:6`,
`publicRsvp.ts:6`), both `import type` only. Every other hook hand-writes its `Wire*`
interface, so a dev hook should do the same and never touch generated types.

## Relevant code

| Area | Location | Role |
|---|---|---|
| Env gate (correct) | `backend/community/management/commands/_seed_staging_data.py:92-96` | `is_seed_allowed` — allow local/unset + staging, deny else |
| Env gate (wrong) | `backend/config/settings.py:12` | `IS_PRODUCTION` — **true on staging**, do not use |
| Env name source | `backend/community/_version.py:18-30` | `GET /version/`, `auth=None`, returns `RAILWAY_ENVIRONMENT_NAME` or `"local"` |
| Frontend env hook | `frontend/src/api/version.ts:17-30` | `useVersion()`, `staleTime: Infinity` |
| Frontend config | `frontend/src/config/env.ts:1-5` | Only `import.meta.env` usage; `VITE_API_URL` never set |
| Shared build | `Dockerfile:10` | `pnpm build:docker`, no build args — staging == prod bundle |
| Event create API | `backend/community/_events.py:303-372` | `POST /events/`, `auth=gated_jwt` |
| Rate limit | `backend/community/_events.py:308` | `10/d` per user — blocks endpoint reuse |
| Cohost fan-out | `backend/community/_event_transitions.py:72-87` | Notifications + **real emails**; only if `co_host_ids` non-empty |
| Event model | `backend/community/models/event.py:53` | `title` the only required field; `status`/`visibility` default ACTIVE/PUBLIC |
| Host auto-seed | `backend/community/models/event.py:186-191` | `post_save` adds `created_by` to `co_hosts` |
| Seed defaults | `backend/community/management/commands/_seed_shared.py:12-42` | `SeedEvent` dataclass + `seed_events()`, `get_or_create` by title |
| Test-data prefix | `backend/community/management/commands/seed_staging.py:87` | `title__startswith="[staging] "` cleanup convention |
| Random test event | `backend/community/management/commands/e2e_seed.py:26-37` | `_random_event` with `secrets.token_hex` titles |
| Permission check | `backend/community/_feature_flags.py:30-46` | House pattern: `audit_log` then `raise_validation(403)` |
| Auth | `backend/config/auth.py:42,80` | `GatedJWTAuth` / `gated_jwt`; no global `auth=` on the API |
| Router registration | `backend/community/api.py:56-101` | All `add_router("", ...)`, none conditional |
| Codegen check | `backend/community/management/commands/dump_openapi_schema.py:33-42` | `--check` exits 1 on schema drift |
| Route guards | `frontend/src/auth/guards.tsx:103-161` | `RequireAuth` / `RequirePermission` / `RequireFlag`; no env guard exists |
| Routes | `frontend/src/router/routes.tsx:58,173-176` | Lazy import + guard block pattern |
| Admin hub | `frontend/src/screens/admin/AdminHubScreen.tsx:14-73` | Tile array filtered by `hasPermission`; `perm` required |
| Menu sheet | `frontend/src/layout/PdaMenuSheet.tsx:19-30,51` | Array-driven, cheapest conditional-append surface |
| Bottom nav | `frontend/src/layout/BottomNav.tsx:26-63` | Hardcoded `grid-cols-5`, inline JSX — poor fit |
| FE test pattern | `frontend/src/screens/admin/FeatureFlagsScreen.test.tsx:7-50` | `vi.mock` API module; already mocks `useVersion` env |
| BE test pattern | `backend/tests/test_feature_flags.py:47-94` | 200/403/401/404 matrix + `monkeypatch.setenv` env idiom |

## Options

**A. New dev-only router, unconditionally registered, env-gated in the body.**
Add `backend/community/_dev_tools.py` with `POST /dev/test-events/`, registered
normally in `community/api.py`. In the handler, check
`is_seed_allowed(os.environ.get("RAILWAY_ENVIRONMENT_NAME"), force=False)` and return
404 if refused, plus `auth=gated_jwt`. Build events from `SeedEvent` + `seed_events()`
with a `[test]` title prefix, `co_host_ids=[]`, and an optional `count` for bulk
creation. Frontend: a screen gated on `useVersion().data.environment`, reached from
AdminHub or PdaMenuSheet, with a hand-written wire type.

*Pros:* schema stays deterministic across environments so `check-codes` stays green;
reuses the existing tested gate; no rate limit; skips the only email fan-out; the
`[test]` prefix satisfies the identifiability criterion and mirrors the existing
`[staging] ` cleanup convention. *Cons:* the endpoint appears in the public OpenAPI
schema in production (returning 404) — cosmetic disclosure only.

**B. Reuse `POST /events/` from a dev-gated UI.**
No new endpoint; the dev screen just posts to the existing create endpoint with
prefilled defaults.

*Pros:* smallest possible backend diff — zero. *Cons:* **fails the issue's explicit
requirement** that the backing endpoint be gated in production, since the existing
endpoint must stay available in prod. Also capped at `10/d` per user
(`_events.py:308`), which defeats the purpose. Not viable as specified.

**C. Conditionally register the dev router.**
Wrap `add_router` in an environment check so the routes do not exist in production.

*Pros:* strongest possible gate — the path genuinely does not exist. *Cons:*
breaks `dump_openapi_schema --check` in CI (`Makefile:243-246`), because the committed
schema and CI's regeneration will differ by environment. Establishes a new
conditional-registration pattern where none exists today.

## Recommendation

**Option A.** The env predicate, the event defaults, the test-data title-prefix
convention, and the runtime environment channel to the frontend all already exist —
this is mostly assembly, not new design. Specifically:

- Backend: reuse `is_seed_allowed` verbatim (no `--force` equivalent on an HTTP
  endpoint), register the router unconditionally, gate in the body, return **404**
  rather than 403 so production does not confirm the route's existence.
- Require `auth=gated_jwt` **in addition to** the env gate — an env-only gate leaves
  the endpoint open to any anonymous caller on staging.
- Hard-code `co_host_ids=[]` to avoid the cohost-invite email fan-out
  (`_event_transitions.py:72-87`), the only real spam vector on the create path.
- Title prefix `[test] ` (or `[dev] `) for identifiability, matching
  `seed_staging.py:87`'s `[staging] ` precedent.
- Frontend: gate on `useVersion().data.environment !== 'production'`, handling the
  async pending state the way `RequireFlag` does (`guards.tsx:149-151`) so the tab
  does not flicker in. Place it behind AdminHub or PdaMenuSheet, not BottomNav.
- Hand-write the wire type; do not touch `types.gen.ts`.
- All new strings lowercase — already universal house style.

The frontend gate is cosmetic in every option; the backend 404 is the real gate.

## Open questions

1. **Which surface should host the tab?** AdminHub needs `Tile.perm` widened to
   optional (`AdminHubScreen.tsx:11`) or a dev tile reusing an existing permission;
   PdaMenuSheet is a cheaper conditional append. The issue says "tab," which literally
   suggests BottomNav — but that is a hardcoded `grid-cols-5` and reflows badly.
   Recommending AdminHub/PdaMenuSheet over a literal tab is an interpretation of the
   ask, not a certainty.

2. **Should the dev screen require a permission at all, or is the env gate enough?**
   On staging, any authenticated member would otherwise see it. A permission adds the
   three-place sync burden (backend enum, frontend mirror, `PERMISSION_LABELS`) with
   no parity test to catch drift.

3. **404 vs 403 in production.** 404 hides the route's existence; 403 is more honest
   and matches the house `raise_validation(Code.Perm.DENIED, status_code=403)` pattern
   (`_feature_flags.py:30-46`). Recommended 404, but this is a judgment call.

4. **Is the OpenAPI disclosure acceptable?** Option A leaves `/dev/test-events/` in
   production's public schema (returning 404). Option C hides it but breaks CI's
   schema check. Assumed acceptable; worth confirming.

5. **Bulk creation shape.** A `count` parameter is cheap, but `seed_events()` uses
   `get_or_create(title=...)` (`_seed_shared.py:33`), so identical titles silently
   dedupe. Bulk creation needs unique titles — `e2e_seed.py:29`'s
   `secrets.token_hex(4)` suffix is the existing answer. Not specified whether bulk
   events should vary in date/type or be near-identical.

6. **Cleanup affordance.** `seed_staging --reset` deletes by title prefix
   (`seed_staging.py:87`). The issue does not ask for a delete-all-test-events action,
   but the prefix makes it nearly free. Out of scope unless requested.

7. **Should created test events be `DRAFT` or `ACTIVE`?** ACTIVE satisfies the
   "shows up on the calendar" acceptance criterion, which is why it is assumed — but
   ACTIVE public events on staging are visible to anyone browsing the public calendar.

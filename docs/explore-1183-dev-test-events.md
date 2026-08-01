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
fan-out happens at _publish_ (`_event_transitions.py:104-106`) and _cancel_
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
`test_update_flag_allowed_on_production` and asserts a flag _can_ be enabled in prod.
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

| Area                | Location                                                                                      | Role                                                                          |
| ------------------- | --------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| Env gate (correct)  | `backend/community/management/commands/_seed_staging_data.py:92-96`                           | `is_seed_allowed` — allow local/unset + staging, deny else                    |
| Env gate (wrong)    | `backend/config/settings.py:12`                                                               | `IS_PRODUCTION` — **true on staging**, do not use                             |
| Env name source     | `backend/community/_version.py:18-30`                                                         | `GET /version/`, `auth=None`, returns `RAILWAY_ENVIRONMENT_NAME` or `"local"` |
| Frontend env hook   | `frontend/src/api/version.ts:17-30`                                                           | `useVersion()`, `staleTime: Infinity`                                         |
| Frontend config     | `frontend/src/config/env.ts:1-5`                                                              | Only `import.meta.env` usage; `VITE_API_URL` never set                        |
| Shared build        | `Dockerfile:10`                                                                               | `pnpm build:docker`, no build args — staging == prod bundle                   |
| Event create API    | `backend/community/_events.py:303-372`                                                        | `POST /events/`, `auth=gated_jwt`                                             |
| Rate limit          | `backend/community/_events.py:308`                                                            | `10/d` per user — blocks endpoint reuse                                       |
| Cohost fan-out      | `backend/community/_event_transitions.py:72-87`                                               | Notifications + **real emails**; only if `co_host_ids` non-empty              |
| Event model         | `backend/community/models/event.py:53`                                                        | `title` the only required field; `status`/`visibility` default ACTIVE/PUBLIC  |
| Host auto-seed      | `backend/community/models/event.py:186-191`                                                   | `post_save` adds `created_by` to `co_hosts`                                   |
| Seed defaults       | `backend/community/management/commands/_seed_shared.py:12-42`                                 | `SeedEvent` dataclass + `seed_events()`, `get_or_create` by title             |
| Test-data prefix    | `backend/community/management/commands/seed_staging.py:87`                                    | `title__startswith="[staging] "` cleanup convention                           |
| Random test event   | `backend/community/management/commands/e2e_seed.py:26-37`                                     | `_random_event` with `secrets.token_hex` titles                               |
| Permission check    | `backend/community/_feature_flags.py:30-46`                                                   | House pattern: `audit_log` then `raise_validation(403)`                       |
| Auth                | `backend/config/auth.py:42,80`                                                                | `GatedJWTAuth` / `gated_jwt`; no global `auth=` on the API                    |
| Router registration | `backend/community/api.py:56-101`                                                             | All `add_router("", ...)`, none conditional                                   |
| Codegen check       | `backend/community/management/commands/dump_openapi_schema.py:33-42`                          | `--check` exits 1 on schema drift                                             |
| Route guards        | `frontend/src/auth/guards.tsx:103-161`                                                        | `RequireAuth` / `RequirePermission` / `RequireFlag`; no env guard exists      |
| Routes              | `frontend/src/router/routes.tsx:58,173-176`                                                   | Lazy import + guard block pattern                                             |
| Floating button     | `frontend/src/layout/AppShell.tsx:53`, `frontend/src/components/FeedbackButton.tsx:17-19,119` | **Recommended surface** — `position: fixed`, self-gates and returns null      |
| Admin hub           | `frontend/src/screens/admin/AdminHubScreen.tsx:14-73`                                         | Tile array filtered by `hasPermission`; `perm` required                       |
| Menu sheet          | `frontend/src/layout/PdaMenuSheet.tsx:19-30,51`                                               | Array-driven, cheapest conditional-append surface                             |
| Bottom nav          | `frontend/src/layout/BottomNav.tsx:26-63`                                                     | Hardcoded `grid-cols-5`, inline JSX — poor fit                                |
| FE test pattern     | `frontend/src/screens/admin/FeatureFlagsScreen.test.tsx:7-50`                                 | `vi.mock` API module; already mocks `useVersion` env                          |
| BE test pattern     | `backend/tests/test_feature_flags.py:47-94`                                                   | 200/403/401/404 matrix + `monkeypatch.setenv` env idiom                       |

## Options

**A. New dev-only router, unconditionally registered, env-gated in the body.**
Add `backend/community/_dev_tools.py` with `POST /dev/test-events/`, registered
normally in `community/api.py`. In the handler, check
`is_seed_allowed(os.environ.get("RAILWAY_ENVIRONMENT_NAME"), force=False)` and return
404 if refused, plus `auth=gated_jwt`. Build events from `SeedEvent` + `seed_events()`
with a `[test]` title prefix, `co_host_ids=[]`, and an optional `count` for bulk
creation. Frontend: a floating corner button self-gating on
`useVersion().data.environment` (see Decisions #1), with a hand-written wire type.

_Pros:_ schema stays deterministic across environments so `check-codes` stays green;
reuses the existing tested gate; no rate limit; skips the only email fan-out; the
`[test]` prefix satisfies the identifiability criterion and mirrors the existing
`[staging] ` cleanup convention. _Cons:_ the endpoint appears in the public OpenAPI
schema in production (returning 404) — cosmetic disclosure only.

**B. Reuse `POST /events/` from a dev-gated UI.**
No new endpoint; the dev screen just posts to the existing create endpoint with
prefilled defaults.

_Pros:_ smallest possible backend diff — zero. _Cons:_ **fails the issue's explicit
requirement** that the backing endpoint be gated in production, since the existing
endpoint must stay available in prod. Also capped at `10/d` per user
(`_events.py:308`), which defeats the purpose. Not viable as specified.

**C. Conditionally register the dev router.**
Wrap `add_router` in an environment check so the routes do not exist in production.

_Pros:_ strongest possible gate — the path genuinely does not exist. _Cons:_
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
- Frontend: a floating corner button in `AppShell`, self-gating on
  `useVersion().data.environment !== 'production'` — see Decisions #1 below.
- Hand-write the wire type; do not touch `types.gen.ts`.
- All new strings lowercase — already universal house style.

The frontend gate is cosmetic in every option; the backend 404 is the real gate.

## Decisions

Resolved with the issue author on 2026-07-31. These supersede the open questions
this exploration originally raised.

1. **Surface: a floating corner button, not a nav tab.** `AppShell.tsx:53` already
   renders `<FeedbackButton />` as a floating element (`position: 'fixed'`,
   `FeedbackButton.tsx:119`) outside the nav grid, and that component **self-gates
   internally** — it computes `canShowFeedback` from auth state
   (`FeedbackButton.tsx:17-19`) and returns null when it shouldn't render, so
   `AppShell` renders it unconditionally with no wrapper logic.

   A dev button copies that shape exactly: render it unconditionally in `AppShell`,
   and have the component itself return null unless
   `useVersion().data?.environment !== 'production'`. This avoids the
   `BottomNav.tsx:26` `grid-cols-5` reflow problem entirely, needs no change to
   `AdminHubScreen`'s required `Tile.perm` (`:11`), and needs no route guard.
   Because `useVersion` is async, return null (not a spinner) while pending — a
   dev affordance popping in a beat late is fine; a flicker in the corner is not.

2. **Auth only, no permission.** `auth=gated_jwt` on the endpoint; no new
   `PermissionKey`. This deliberately avoids the three-place sync burden (backend
   enum `users/permissions.py:4-18`, frontend mirror `models/permissions.ts:1-16`,
   `PERMISSION_LABELS` in `RoleFormDialog.tsx:16-31`), which has no parity test to
   catch drift. On staging any logged-in member sees the button; that is acceptable.

3. **404 in production**, not 403 — production should not confirm the route exists.
   Note this intentionally departs from the house
   `raise_validation(Code.Perm.DENIED, status_code=403)` pattern
   (`_feature_flags.py:30-46`); worth a one-line comment at the call site so a
   future reader doesn't "fix" it to 403.

4. **OpenAPI disclosure accepted.** `/dev/test-events/` stays in production's public
   schema returning 404. The alternative (Option C, conditional registration) breaks
   `dump_openapi_schema --check` in CI (`Makefile:243-246`), and what leaks is a path
   name that 404s — not a trade worth CI fragility.

5. **Bulk create is in scope.** A `count` parameter, but titles **must be unique**:
   `seed_events()` uses `get_or_create(title=...)` (`_seed_shared.py:33`), so N
   identical titles would silently collapse into one event. Use the existing
   `secrets.token_hex(4)` suffix idiom from `e2e_seed.py:29`.

6. **Cleanup affordance is in scope** — delete-by-title-prefix, mirroring
   `seed_staging.py:87`'s `Event.objects.filter(title__startswith=...).delete()`.
   Nearly free given the prefix convention.

7. **ACTIVE by default, with overrides behind a disclosure.** The governing
   constraint is "as few clicks as possible": the primary button creates a sensible
   ACTIVE event immediately with zero configuration, and an optional expandable panel
   exposes overrides (status, visibility per #8, date, type, RSVP) for the cases that
   need them. No click cost on the common path.

8. **`visibility` defaults to `PUBLIC`, exposed as an override control.** This
   matches the `SeedEvent` default (`_seed_shared.py:19`) and what real events look
   like. Accepted consequence: ACTIVE + PUBLIC test events appear on staging's
   **public** calendar, visible to anonymous visitors — the `[test] ` title prefix
   (Decision #6) is what keeps them identifiable, and the cleanup affordance is what
   keeps them from accumulating.

   Expose all three `PageVisibility` values (`choices.py:6-9`) in the overrides
   panel. There is an existing three-option control to match at
   `SurveyAdminListScreen.tsx:202` (`{ value: 'members_only', label: 'members only' }`)
   — note the lowercase, space-separated labels, per house style. A dropdown handles
   all three cleanly; a checkbox would only cover two.

## Open questions

None — all design questions resolved with the issue author. Implementation notes
live in the Decisions section above.

---
name: add-permission-gated-page
description: Scaffold a new permission-gated admin/restricted page in the PDA app — a page whose ACCESS requires a permission. Wires the RequirePermission route guard + AdminHub tile (frontend UX) and a backend GET endpoint that returns 403 without the permission (the real gate). Use for an admin/management screen only certain roles may open. For an openly-viewable page whose editing is gated, use add-editable-page instead.
argument-hint: "<route_slug> [\"Title\"] <permission_key>"
---

# Add a Permission-Gated Page

Adds a page whose **access** is restricted to users holding a permission — the
Docs / JoinRequests / Members-admin pattern. Wired full-stack across the React/TS frontend
and the Django backend.

**Gating model — important.** Unlike an editable content page (which is openly viewable),
this page should not be reachable at all without the permission:
- **Frontend** wraps the route in `<RequirePermission perm={...} />` (redirects before the
  screen mounts) and surfaces the page as an **AdminHub tile** that only appears for
  permitted users. This is UX/routing only.
- **Backend is the real gate** — the page's data endpoint checks
  `request.auth.has_permission(MANAGE_X)` and returns **403** otherwise. A redirect alone is
  not security; the 403 is what actually enforces access. (To instead make a page openly
  viewable but edit-gated, use `add-editable-page`.)

## Permission key

This page is gated by a permission (typically a `manage_*` key). **If it needs a NEW
permission, run `add-new-permission` first** (it adds the `PermissionKey` enum member + the
frontend `Permission` mirror). If you're reusing an existing key (e.g. an admin screen under
`manage_users`), skip that. The steps below assume the key already exists.

## Arguments

- `route_slug` — the URL path, e.g. `sponsors` → `/admin/sponsors` (admin screens conventionally
  live under `/admin/...`; some, like `/join-requests`, are top-level — match the closest peer).
- `Title` — human-facing label for the AdminHub tile and the `<h1>` (lowercase, like the
  existing tiles: `members`, `join requests`).
- `permission_key` — the gating key, e.g. `manage_sponsors` → `Permission.ManageSponsors` /
  `PermissionKey.MANAGE_SPONSORS`.

Derive (example slug `sponsors`, key `manage_sponsors`):
- `PermCamel` = `ManageSponsors`, `PERM_CONST` = `MANAGE_SPONSORS`
- `ScreenName` = `SponsorsScreen`, route `/admin/sponsors`, API path `/api/community/sponsors/`

---

## Frontend

### Step 1 — Route guard: `frontend/src/router/routes.tsx`

Add a lazy import alongside the other admin screens:

```tsx
const Sponsors = lazyWithRetry(() => import('@/screens/admin/SponsorsScreen'));
```

Then add the route wrapped in `RequirePermission`. If a sibling admin route already uses the
SAME permission, add your path to its existing `children`; otherwise add a new block:

```tsx
{
  element: <RequirePermission perm={Permission.ManageSponsors} />,
  children: [{ path: '/admin/sponsors', element: el(<Sponsors />) }],
},
```

`RequirePermission` (in `frontend/src/auth/guards.tsx`) redirects unauthed users to
`/login?redirect=...` and authed-but-unpermitted users to `/calendar` — so the screen never
mounts without the permission.

### Step 2 — AdminHub tile: `frontend/src/screens/admin/AdminHubScreen.tsx`

Permission-gated pages are **not** added to the main nav (`PdaMenuSheet.tsx`) — that's only
for public/authed-everyone links. Instead they're discovered through the AdminHub, which
filters tiles by permission (`TILES.filter((t) => hasPermission(user, t.perm))`).

Add an entry to the `TILES` array:

```tsx
{
  to: '/admin/sponsors',
  label: 'sponsors',
  description: 'manage the sponsor list',
  perm: Permission.ManageSponsors,
},
```

### Step 3 — Screen: `frontend/src/screens/admin/SponsorsScreen.tsx` (new file)

A starter screen. It does **not** need its own `hasPermission` check — the route guard
already enforces access. Use `ContentContainer` / `ContentLoading` / `ContentError` like the
other admin screens (reference `JoinRequestsScreen.tsx`). Data-driven version:

```tsx
import { useSponsors } from '@/api/sponsors';
import { ContentContainer, ContentError, ContentLoading } from '@/screens/public/ContentContainer';

export default function SponsorsScreen() {
  const { data = [], isPending, isError } = useSponsors();

  if (isPending) return <ContentLoading />;
  if (isError) return <ContentError message="couldn't load sponsors — try refreshing" />;

  return (
    <ContentContainer>
      <h1 className="mb-6 text-2xl font-medium tracking-tight">sponsors</h1>
      {/* render data */}
    </ContentContainer>
  );
}
```

If the page is static (no data), drop the hook and just render the content (see
`SmsPolicyScreen.tsx` for the bare shape). The data hook (`useSponsors`) lives in a new or
existing `frontend/src/api/*.ts` module using react-query + `apiClient` — model it on the
existing query hooks in `frontend/src/api/content.ts` / `join.ts`.

### Step 4 — Screen test: `frontend/src/screens/admin/SponsorsScreen.test.tsx` (new file)

Test the screen renders its states (loading / error / data) with the data hook mocked,
following the existing admin/public screen tests (they mock the `@/api/*` hook and wrap in
`QueryClientProvider` + `MemoryRouter`; drive `useAuthStore.setState` for the user).

Note: the route guard's redirect-without-permission behavior is exercised by
`RequirePermission`'s own tests, not per-screen — but if you want belt-and-suspenders, render
the route subtree with an unpermitted user and assert the screen does not appear.

---

## Backend

> Only if the page has its own data endpoint. If it reuses an existing gated endpoint, skip
> to Verify. If it's a purely static page, there's no backend at all.

### Step 5 — Gated endpoint: `backend/community/_sponsors.py` (new file)

The **real gate.** Copy the `backend/community/_docs.py` shape — a `_has_x` helper plus a GET
that 403s before returning any data:

```python
"""Sponsors (admin) endpoints."""

import logging

from config.audit import audit_log
from config.auth import gated_jwt
from ninja import Router
from ninja.responses import Status
from users.permissions import PermissionKey

from community._shared import ErrorOut
from community._validation import Code, raise_validation

router = Router()


def _has_manage_sponsors(user) -> bool:
    return user.has_permission(PermissionKey.MANAGE_SPONSORS)


@router.get("/sponsors/", response={200: list[SponsorOut], 403: ErrorOut}, auth=gated_jwt)
def list_sponsors(request):
    if not _has_manage_sponsors(request.auth):
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            details={
                "endpoint": "list_sponsors",
                "required_permission": PermissionKey.MANAGE_SPONSORS,
            },
        )
        raise_validation(Code.Perm.DENIED, status_code=403, action="manage_sponsors")
    # ... return the data ...
    return Status(200, [...])
```

This 403-before-data is the difference from an editable page (where GET is open). Define
`SponsorOut` and any model the same way the existing `_docs.py` / models do.

> **Use `auth=gated_jwt`, never `auth=JWTAuth()`.** `gated_jwt` (from `config.auth`) is the
> project's single chokepoint that also rejects tokens for blocked/inactive accounts — every
> protected community endpoint uses it. Raw `JWTAuth()` authenticates any valid token and
> skips that account-state check, opening a security gap. This matters most here, where the
> gated GET *is* the access boundary.

### Step 6 — Register the router: `backend/community/api.py`

```python
from community._sponsors import router as sponsors_router
# ...
router.add_router("", sponsors_router)
```

### Step 7 — Backend tests: `backend/tests/test_community.py` (or `test_sponsors.py`)

Add a fixture for a user whose role grants `MANAGE_SPONSORS` (unused `+1202555XXXX` phone)
and assert the **access** gate:

```python
@pytest.mark.django_db
class TestSponsorsAccess:
    def test_list_with_permission(self, api_client, manage_sponsors_headers):
        assert api_client.get("/api/community/sponsors/", **manage_sponsors_headers).status_code == 200

    def test_list_without_permission(self, api_client, auth_headers):
        # authed but lacks manage_sponsors → 403 (NOT just hidden)
        assert api_client.get("/api/community/sponsors/", **auth_headers).status_code == 403

    def test_list_unauthenticated(self, api_client):
        assert api_client.get("/api/community/sponsors/").status_code == 401
```

### Step 8 — Migration (if a model was added)

```bash
make migrate
```

---

## Step 9 — Verify

```bash
make ci
```

## Reference files (read these — they are the source of truth)

| Concern | File |
|---------|------|
| Permission key (if new — run `add-new-permission`) | `backend/users/permissions.py`, `frontend/src/models/permissions.ts` |
| Route guard | `frontend/src/auth/guards.tsx` (`RequirePermission`) |
| Route wrap pattern | `frontend/src/router/routes.tsx` |
| AdminHub tiles | `frontend/src/screens/admin/AdminHubScreen.tsx` |
| Admin screen example | `frontend/src/screens/admin/JoinRequestsScreen.tsx` |
| Backend gated read (403) | `backend/community/_docs.py` (`_has_manage_docs` + GET 403) |
| Auth (`gated_jwt`) | `backend/config/auth.py` (account-state chokepoint — use this, not `JWTAuth()`) |
| Router registration | `backend/community/api.py` |
| Backend tests | `backend/tests/test_community.py` |

## Note — gating ACCESS vs gating EDITING

This skill gates *who can open the page* (route guard + backend GET 403). If instead you want
an openly-viewable page whose *content* can be edited by a permission-holder (FAQ/Guidelines
style — GET open, PATCH gated), use **`add-editable-page`**.

---
name: add-editable-page
description: Scaffold a new in-app-editable rich-text singleton content page in the PDA app end-to-end (Django singleton model + ninja GET/PATCH endpoints + React screen + data hooks + route + nav + tests), following the FAQ/Guidelines pattern. The page is openly viewable; editing is gated by an edit_* permission enforced on the backend PATCH. Use for an editable content page like FAQ or Guidelines.
argument-hint: "<page_slug> [\"Page Title\"] [public|authed]"
---

# Add an Editable Content Page

Adds a new **editable singleton content page** (one DB row, rich-text body) end-to-end across
the Django backend and the React/TS frontend. The canonical template is the existing **FAQ**
(public) and **Guidelines** (authed) pages — copy them exactly.

**Gating model — important.** This page is *openly viewable* (by everyone or any authed user);
only *editing* is gated:
- **Frontend** shows/hides the Edit button via `canEdit = hasPermission(user, Permission.EditX)`
  — this is UX only.
- **Backend `PATCH` is the real gate** — it checks `request.auth.has_permission(EDIT_X)` and
  returns 403 otherwise. The GET is open. (To gate *access to the page itself*, that's a
  different skill — see `add-permission-gated-page`.)

## Permission key

This page is gated by an `edit_*` permission. **If it needs a NEW permission key, run
`add-new-permission` first** (it adds the `PermissionKey` enum member + the frontend
`Permission` mirror). If you're reusing an existing key, skip that and proceed. The steps
below assume `Permission.EditResources` / `PermissionKey.EDIT_RESOURCES` already exist.

## Arguments

- `page_slug` — snake/kebab single word used in the URL and API path, e.g. `resources`.
- `Page Title` — human-facing label for the nav and `<h1>` (defaults to the slug, lowercased
  — note the existing pages render lowercase titles like `faq`, `guidelines`).
- `public|authed` — whether the page is viewable logged-out (`public`, like FAQ) or
  requires login (`authed`, like Guidelines). Default `authed`. Ask if unclear.

Derive before starting (example for slug `resources`):
- `PERM_CONST` = `EDIT_RESOURCES`, perm string `edit_resources`, `Permission.EditResources`
- `ModelName` = `Resources` (PascalCase of slug)
- route `/resources`, API path `/api/community/resources/`
- query key `['resources']`

---

## Backend

### Step 1 — Singleton model: `backend/community/models/content.py`

Add a model copying `FAQ` / `CommunityGuidelines` exactly (three content fields + the
`get()` singleton accessor):

```python
class Resources(models.Model):
    """Singleton model — only one row ever exists (pk=1)."""

    content = models.TextField(default="", max_length=50000)        # legacy Quill delta
    content_pm = models.TextField(default="", max_length=50000)     # ProseMirror/TipTap JSON
    content_html = models.TextField(default="", max_length=100000)  # rendered HTML (read)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "community"
        verbose_name = "Resources"
        verbose_name_plural = "Resources"

    def __str__(self):
        return "Resources"

    @classmethod
    def get(cls) -> "Resources":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
```

### Step 2 — Export it: `backend/community/models/__init__.py`

Add `Resources` to BOTH the `from community.models.content import (...)` block AND the
content section of `__all__` (keep both lists tidy).

### Step 3 — Endpoints: `backend/community/_resources.py` (new file)

Copy `backend/community/_guidelines.py`. **Reuse the existing `GuidelinesOut` /
`GuidelinesPatchIn` schemas and the `_singleton_out` / `_apply_update` shape** — every
singleton page shares the same wire format, so import or replicate them rather than
inventing new schemas. New file:

```python
"""Resources endpoints."""

import logging
from datetime import datetime

from config.audit import audit_log
from config.auth import gated_jwt
from ninja import Router
from ninja.responses import Status
from pydantic import BaseModel, Field
from users.permissions import PermissionKey

from community._content_render import render_content_payload
from community._field_limits import FieldLimit
from community._shared import ErrorOut
from community._validation import Code, raise_validation
from community.models import Resources

router = Router()


class ResourcesOut(BaseModel):
    content: str
    content_pm: str
    content_html: str
    updated_at: datetime


class ResourcesPatchIn(BaseModel):
    content: str | None = Field(default=None, max_length=FieldLimit.CONTENT)
    content_pm: str | None = Field(default=None, max_length=FieldLimit.CONTENT)


def _singleton_out(obj: Resources) -> ResourcesOut:
    return ResourcesOut(
        content=obj.content,
        content_pm=obj.content_pm,
        content_html=obj.content_html,
        updated_at=obj.updated_at,
    )


def _apply_update(obj: Resources, payload: ResourcesPatchIn) -> None:
    rendered = render_content_payload(delta=payload.content, prosemirror=payload.content_pm)
    obj.content = rendered.content
    obj.content_pm = rendered.content_pm
    obj.content_html = rendered.content_html
    obj.save()


# GET auth: use `auth=None` for a PUBLIC page (like FAQ/Guidelines, which are open so join
# applicants can read them), or `auth=gated_jwt` for an AUTHED page. Pick per the
# public|authed argument. Never use raw `JWTAuth()` — `gated_jwt` (from `config.auth`) is the
# project chokepoint that also rejects blocked/inactive accounts.
@router.get("/resources/", response={200: ResourcesOut}, auth=None)
def get_resources(request):
    return Status(200, _singleton_out(Resources.get()))


@router.patch("/resources/", response={200: ResourcesOut, 403: ErrorOut}, auth=gated_jwt)
def update_resources(request, payload: ResourcesPatchIn):
    if not request.auth.has_permission(PermissionKey.EDIT_RESOURCES):
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            details={
                "endpoint": "update_resources",
                "required_permission": PermissionKey.EDIT_RESOURCES,
            },
        )
        raise_validation(Code.Perm.DENIED, status_code=403, action="manage_resources")
    r = Resources.get()
    _apply_update(r, payload)
    audit_log(
        logging.INFO,
        "resources_updated",
        request,
        target_type="resources",
        details={"format": "prosemirror" if payload.content_pm else "delta"},
    )
    return Status(200, _singleton_out(r))
```

> **This PATCH permission check is the real gate.** The frontend `canEdit` (step 8) only
> hides the Edit button; a determined client can still call PATCH, so the 403 here is what
> actually enforces edit access. Never rely on the frontend check alone.

> Tip: if you prefer not to duplicate the schema/helpers, you can `from community._guidelines
> import GuidelinesOut, GuidelinesPatchIn` and reuse them — that's what FAQ and Guidelines
> already do (they share one `_singleton_out`). The standalone version above is fine too.

### Step 4 — Register the router: `backend/community/api.py`

Add the import with the other `_xxx import router as xxx_router` lines and register it with
the other `router.add_router("", xxx_router)` calls:

```python
from community._resources import router as resources_router
# ...
router.add_router("", resources_router)
```

### Step 5 — Tests: `backend/tests/test_community.py`

Add fixtures (pick an unused `+1202555XXXX` phone number — scan the file for the next free
one) and a test class. Pattern:

```python
@pytest.fixture
def edit_resources_user(db):
    from users.models import User

    user = User.objects.create_user(
        phone_number="+12025550404",  # next unused number in this file
        password="resourcespass",
        display_name="Resources Editor",
    )
    role = Role.objects.create(name="resources_editor", permissions=[PermissionKey.EDIT_RESOURCES])
    user.roles.add(role)
    return user


@pytest.fixture
def edit_resources_headers(edit_resources_user):
    from ninja_jwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(edit_resources_user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


@pytest.mark.django_db
class TestResources:
    def test_get_authenticated(self, api_client, auth_headers):
        r = api_client.get("/api/community/resources/", **auth_headers)
        assert r.status_code == 200
        assert "content" in r.json() and "updated_at" in r.json()

    def test_get_unauthenticated(self, api_client):
        # 200 if the page is PUBLIC (auth=None), 401 if AUTHED (auth=gated_jwt).
        r = api_client.get("/api/community/resources/")
        assert r.status_code == 401  # flip to 200 for a public page

    def test_update_with_permission(self, api_client, edit_resources_headers):
        r = api_client.patch(
            "/api/community/resources/",
            {"content_pm": '{"type":"doc","content":[]}'},
            content_type="application/json",
            **edit_resources_headers,
        )
        assert r.status_code == 200

    def test_update_requires_permission(self, api_client, auth_headers):
        r = api_client.patch(
            "/api/community/resources/",
            {"content_pm": "{}"},
            content_type="application/json",
            **auth_headers,
        )
        assert r.status_code == 403

    def test_update_requires_auth(self, api_client):
        r = api_client.patch(
            "/api/community/resources/",
            {"content_pm": "{}"},
            content_type="application/json",
        )
        assert r.status_code == 401
```

### Step 6 — Migration

```bash
make migrate
```

---

## Frontend

### Step 7 — Data hooks: `frontend/src/api/content.ts`

Add a query hook and reuse the `makeSimplePatch` factory for the mutation. Choose the read
variant by public|authed:

```ts
// PUBLIC page (like FAQ): no auth gate, simple key.
export function useResources() {
  return useQuery({
    queryKey: ['resources'],
    queryFn: () => fetchSimple('/api/community/resources/'),
  });
}

// AUTHED page (like Guidelines): gate the fetch on auth, include {authed} in the key.
// export function useResources() {
//   const isAuthed = useAuthStore((s) => s.status === 'authed');
//   return useQuery({
//     queryKey: ['resources', { authed: isAuthed }],
//     queryFn: () => fetchSimple('/api/community/resources/'),
//     enabled: isAuthed,
//   });
// }

export const useUpdateResources = makeSimplePatch('/api/community/resources/', ['resources']);
```

Reuse the existing `fetchSimple` and `makeSimplePatch` helpers — do not hand-roll axios calls.

### Step 8 — Screen: `frontend/src/screens/public/ResourcesScreen.tsx` (new file)

Copy `FaqScreen.tsx` verbatim, swapping faq→resources:

```tsx
import { useResources, useUpdateResources } from '@/api/content';
import { useAuthStore } from '@/auth/store';
import { EditableHtmlBlock } from '@/components/EditableHtmlBlock';
import { Permission, hasPermission } from '@/models/permissions';
import { ContentContainer, ContentError, ContentLoading } from './ContentContainer';

export default function ResourcesScreen() {
  const { data, isPending, isError } = useResources();
  const user = useAuthStore((s) => s.user);
  const canEdit = hasPermission(user, Permission.EditResources);
  const update = useUpdateResources();

  if (isPending) return <ContentLoading />;
  if (isError) return <ContentError message="couldn't load resources — try refreshing" />;

  return (
    <ContentContainer>
      <h1 className="mb-4 text-2xl font-medium tracking-tight">resources</h1>
      <EditableHtmlBlock
        canEdit={canEdit}
        contentHtml={data.contentHtml}
        initialPm={data.contentPm}
        onSave={(contentPm) => update.mutateAsync(contentPm).then(() => undefined)}
        placeholder="resources content"
      />
    </ContentContainer>
  );
}
```

`EditableHtmlBlock` already provides the Edit button, autosave, TipTap editor, and view mode —
do not rebuild any of that.

### Step 9 — Route: `frontend/src/router/routes.tsx`

Add the lazy import alongside the other `public/` screens, then add the route:

```tsx
const Resources = lazyWithRetry(() => import('@/screens/public/ResourcesScreen'));
```

Place `{ path: '/resources', element: el(<Resources />) }`:
- **Authed page** → inside the `<RequireAuth />` children group (like `/guidelines`).
- **Public page** → with the public routes (like `/faq`), outside `RequireAuth`.

### Step 10 — Nav: `frontend/src/layout/PdaMenuSheet.tsx`

Add a menu item to the right array:
- **Public** → `ALWAYS_ITEMS` (shown logged-out, like `/faq`).
- **Authed** → `AUTHED_ITEMS` (shown only when logged in, like `/guidelines`).

```ts
{ to: '/resources', label: 'resources' },
```

### Step 11 — Screen test: `frontend/src/screens/public/ResourcesScreen.test.tsx` (new file)

Copy `FaqScreen.test.tsx`, swapping faq→resources. It mocks `@/api/content` and the
`RichEditor`, drives `useAuthStore.setState`, and asserts: loading state, no Edit button
for a member without `edit_resources`, Edit button for a user whose role has `edit_resources`.

---

## Step 12 — Verify

```bash
make ci
```

Fix anything that fails — especially tests that enumerate permission keys or that assumed a
fixed set of `/api/community/*` routes.

## Reference files (read these — they are the source of truth)

| Concern | File |
|---------|------|
| Permission key (if new — run `add-new-permission`) | `backend/users/permissions.py`, `frontend/src/models/permissions.ts` |
| Singleton models | `backend/community/models/content.py`, `models/__init__.py` |
| Endpoint pattern | `backend/community/_guidelines.py` (FAQ + Guidelines) |
| Auth (`gated_jwt`) | `backend/config/auth.py` (account-state chokepoint — use this, not `JWTAuth()`) |
| Router registration | `backend/community/api.py` |
| Backend tests | `backend/tests/test_community.py` |
| Data hooks | `frontend/src/api/content.ts` |
| Screen + editor | `frontend/src/screens/public/FaqScreen.tsx`, `components/EditableHtmlBlock.tsx` |
| Route + nav | `frontend/src/router/routes.tsx`, `frontend/src/layout/PdaMenuSheet.tsx` |
| Screen test | `frontend/src/screens/public/FaqScreen.test.tsx` |

## Note — not the same as `EditablePage`

PDA also has a generic `EditablePage` model with a `community/_pages.py` router and
`useEditablePage(slug)` hook — that's a *different* mechanism (dynamic, slug-addressed pages).
This skill scaffolds a **dedicated singleton page** like FAQ/Guidelines. Don't conflate them.

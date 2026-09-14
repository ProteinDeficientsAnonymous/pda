# Routes (React Router)

Source of truth: `frontend/src/router/routes.tsx`. All lazy-loaded screens sit under `AppShell` except auth edge routes.

## Public (no `RequireAuth`)

| Path | Screen |
|------|--------|
| `/` | Landing |
| `/join` | Join request form |
| `/join/success` | Join success |
| `/calendar` | Community calendar (member details gated inline) |
| `/events/:id` | Event detail (member details gated inline) |
| `/events/:id/edit` | Event edit (form handles auth; backend may 401) |
| `/events/add` | Create event |
| `/surveys/:slug` | Public / members survey |
| `/donate` | Donate |
| `/install` | Install / PWA |
| `/faq` | FAQ |

## Auth-only (no `AppShell` chrome grouping — still top-level routes)

| Path | Screen |
|------|--------|
| `/login` | Login |
| `/magic-login/:token` | Magic login consume |
| `/onboarding` | First-login onboarding |
| `/new-password` | Password reset completion |

## Authed (`RequireAuth`)

| Path | Screen |
|------|--------|
| `/guidelines` | Guidelines |
| `/settings` | Settings (profile, accessibility, **calendar ICS feed**) |
| `/profile` | Profile |
| `/volunteer` | Volunteer |
| `/docs` | Docs index (**manage_documents**: folder/doc admin) |
| `/docs/:id` | Doc detail / editor |
| `/events/mine` | My events |

## Admin hub

| Path | Screen |
|------|--------|
| `/admin` | Admin hub (tiles by permission) |

## Permissioned

| Path | Permission |
|------|------------|
| `/members` | `manage_users` |
| `/members/:id` | `manage_users` (member detail, roles, magic link) |
| `/join-requests` | `approve_join_requests` |
| `/events/manage` | `manage_events` |
| `/admin/flagged-events` | `manage_events` |
| `/admin/whatsapp` | `manage_whatsapp` |
| `/admin/join-form` | `edit_join_questions` |
| `/admin/surveys` | `manage_surveys` |
| `/admin/surveys/:id` | `manage_surveys` |
| `/admin/surveys/:id/responses` | `manage_surveys` (raw responses + **poll tallies / finalize**) |

## Catch-all

| Path | Screen |
|------|--------|
| `*` | `NotImplemented` (“coming soon”) — unknown paths only |

## Router errors

Route render errors bubble to `RootRouteError` (`frontend/src/router/RootRouteError.tsx`), which reports to `/api/community/error-report/`.

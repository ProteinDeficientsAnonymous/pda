# Plan: Flutter → Vite + React Migration

## Context

The PDA frontend is currently Flutter web, shipped as compiled JS/WASM embedded in the Django container and served via WhiteNoise. The stated pain is **production runtime performance** — large initial bundle (Flutter baseline ~2–3MB before app code), canvas-based rendering that bypasses browser native paint, and font/paint blocking on cold loads.

Rather than continuing to optimize Flutter web, we're migrating the frontend to **Vite + React + TypeScript**. This swaps a non-native rendering pipeline for the browser's native DOM pipeline, keeps the existing Django API backend untouched, and preserves the current deploy story (static files served by Django on Railway). Mobile is a future concern and can be addressed later via Capacitor wrapping the Vite build or a PWA install flow.

This plan captures the target architecture, the risky/complex translations, and an execution strategy that minimizes rework.

---

## Why Vite (not Next.js)

Decided in prior conversation. Recap:
- Current deploy is Django + WhiteNoise on Railway → Vite static output drops in with zero infra changes. Next.js on Railway requires running a Node server alongside Django.
- 28 of 38 screens are authed (admin, surveys, profile, event management) — SSR benefits are small and concentrated in 3–4 public routes (`/`, `/calendar`, `/events/:id`, `/join`).
- App is client-heavy (Quill/TipTap, drag-reorder, calendar, image crop, SSE) — in Next.js these become `'use client'` islands, eroding the framework's advantage.
- Vite's build output is smaller, simpler, and CDN-cacheable. Public routes can be prerendered with `vite-plugin-ssg` later if SEO becomes real.

---

## Target Stack

| Concern | Choice | Rationale |
|---|---|---|
| Build tool | **Vite** | Fast builds, static output, drops into existing Django static pipeline |
| UI | **React 18 + TypeScript (strict)** | Industry standard, excellent type-safety, best library ecosystem |
| Router | **React Router v6** (`createBrowserRouter`) | Maps cleanly onto GoRouter patterns including nested routes and permission guards |
| Data | **TanStack Query v5** | Direct analog of Riverpod `FutureProvider` + invalidation model |
| Client state | **Zustand** (auth, accessibility prefs only) | Minimal footprint, no provider pyramid; everything else lives in TanStack Query cache |
| Forms | **react-hook-form + Zod** | Perf (uncontrolled inputs), Zod schemas double as runtime validation and TS types |
| API types | **openapi-typescript** against Django Ninja's OpenAPI schema | End-to-end type safety from backend to frontend, generated not hand-written |
| HTTP | **axios** with request/response interceptors | Matches current Dio refresh-lock semantics best; single module exports typed `api` |
| Styling | **Tailwind CSS + shadcn/ui (Radix primitives)** | Radix = WCAG-AA accessibility out of the box (project has strict accessibility rules), shadcn = owned-component pattern means no library lock-in |
| Calendar | **react-big-calendar** | Month/week/day/agenda semantics map 1:1 to current views; themeable; MIT-licensed |
| Rich editor | **TipTap** | ProseMirror JSON ≈ Quill Delta JSON (eases dual-write migration), `generateHTML()` mirrors existing server-rendered HTML pattern, SSR-safe read-only renderer |
| Drag-reorder | **dnd-kit** | Keyboard + screen-reader accessible (required by project a11y rules); react-beautiful-dnd is deprecated |
| Image crop | **react-easy-crop** | Returns cropped canvas directly, native `cropShape="round"` for avatar, `restrictPosition` hook for event-cover aspect clamp |
| SSE | Native `EventSource` + custom `useEventSource` hook | 1:1 port of `notification_sse_web.dart` |
| i18n / dates | **date-fns** | Used by react-big-calendar; smaller than moment; tree-shakeable |
| Testing | **Vitest + React Testing Library + Playwright** | Vitest = Jest API with Vite speed; Playwright for E2E (calendar, auth flow, survey builder) |
| Lint/format | **ESLint (flat config) + Prettier + typescript-eslint strict** | Industry standard |

---

## Architectural Decisions

### 1. Token storage (security change, not a port)

Current: Dart `flutter_secure_storage` stores both access + refresh JWTs in WebCrypto-encrypted IndexedDB on web. This is marginally better than localStorage but still JS-accessible and vulnerable to XSS.

Target: **httpOnly refresh cookie + in-memory access token**. This is the modern SPA standard.
- Backend work required: Django Ninja auth endpoints must set the refresh token as an `HttpOnly; Secure; SameSite=Lax` cookie rather than returning it in the JSON body.
- `/api/auth/refresh/` reads the cookie, issues a new access token in the JSON body.
- Frontend keeps access token only in a Zustand store (memory); on page reload, calls `/api/auth/refresh/` (cookie is sent automatically) to rehydrate.
- CSRF: use SameSite=Lax + double-submit cookie or header-based CSRF token on state-changing endpoints.

This removes refresh tokens from JS entirely — a real security improvement, not just a port.

### 2. API contract (generated types)

- Django Ninja already emits an OpenAPI schema. Add a frontend script: `npm run types:api` → runs `openapi-typescript http://localhost:8000/api/openapi.json -o src/api/types.gen.ts`.
- All `api.ts` functions typed against the generated schema — no hand-maintained duplicated DTOs.
- Freezed models → generated types + a small `src/models/` layer with domain helpers (e.g. `userHasPermission(user, key)`).

### 3. Auth & routing

- `AuthProvider` (React Context wrapping Zustand) exposes `{ user, isLoading, login, logout, ... }`.
- `useAuth()` hook + selectors (`useHasPermission('manage_users')`).
- Route guards as element wrappers:
  - `<RequireAuth>` — unauthed → `/login?redirect=<original>`
  - `<RequirePermission perm="manage_users">` — unauthed or missing perm → `/calendar`
  - `<OnboardingGate>` — forces `/onboarding` or `/new-password` if `user.needsOnboarding` per the current logic
- Router configured via `createBrowserRouter` with one top-level `<OnboardingGate>` layout route wrapping everything.
- Lazy loading via `React.lazy()` + `<Suspense>` — 1:1 replacement for `DeferredScreen`.

### 4. HTTP client (refresh-lock port)

Port the Dio `_refreshLock` Completer pattern to axios:

```ts
// src/api/client.ts
let refreshPromise: Promise<string | null> | null = null;

axios.interceptors.response.use(
  r => r,
  async (err) => {
    const cfg = err.config;
    if (err.response?.status !== 401 || cfg._retried) throw err;
    cfg._retried = true;
    if (!refreshPromise) {
      refreshPromise = doRefresh().finally(() => { refreshPromise = null; });
    }
    const token = await refreshPromise;
    if (!token) { useAuthStore.getState().forceLogout(); throw err; }
    cfg.headers.Authorization = `Bearer ${token}`;
    return axios(cfg);
  }
);
```

Two axios instances: one plain (`authAxios` for `/login/` and `/refresh/`), one with interceptors for everything else.

### 5. SSE notifications

Direct port of `notification_sse_web.dart`:
- `useEventSource(url, { onMessage, onError })` hook
- Exponential backoff (1s → 30s cap) on error
- On `notification` event → `queryClient.invalidateQueries({ queryKey: ['notifications'] })` and `['notifications', 'unread-count']`
- TanStack Query handles polling fallback: `refetchInterval: sseConnected ? 300_000 : 30_000`, `refetchIntervalInBackground: false` (replaces `isTabHidden()`)

### 6. Autosave

- `useAutosave({ value, onSave, delay = 2000 })` hook wrapping `useDebounce` + `useMutation`
- Status state: `idle | saving | saved | error`
- Replaces `autosave_mixin.dart` across doc_detail, home, faq, guidelines, editable_content_block

### 7. Rich editor migration strategy

- **Read-only path (high-traffic)**: Keep backend `page.contentHtml` field. Render via `<HtmlContent html={page.contentHtml} />` (a wrapper around `dangerouslySetInnerHTML` inside a sanitized container — use `DOMPurify` at the backend or frontend boundary).
- **Edit path**: TipTap with JSON storage. Backend stores ProseMirror JSON (new field `content_json`) alongside rendered HTML.
- **Migration from Quill Delta → ProseMirror JSON**: one-time backend migration. Quill Delta and TipTap JSON are both semantic block-level representations — write a Python migration using `prosemirror-py` or a custom converter for the limited formatting used (headings, lists, inline bold/italic/link). Event descriptions are currently plain text → no migration needed there.

### 8. Image handling

- Pick: `<input type="file" accept="image/*">` — no library needed
- Crop: react-easy-crop with `cropShape="round"` for avatar, rectangle with custom `restrictPosition` for event cover
- Upload: native `FormData` with field name `photo` — same as current backend contract
- Cache-bust: append `?v=${user.photoUpdatedAt}` or `?v=${event.photoUpdatedAt}` to image URLs instead of `imageCache.evict`

### 9. Deploy

Unchanged from today:
- `make frontend-build` invokes `vite build` → outputs to `frontend/dist/`
- Dockerfile copies `frontend/dist/` → `backend/staticfiles/spa/`
- Django catch-all route serves `spa/index.html` for non-API routes (same pattern as today)
- Railway unchanged, WhiteNoise unchanged

---

## Target Directory Layout

```
frontend/
├── index.html
├── vite.config.ts
├── tsconfig.json
├── tailwind.config.ts
├── package.json
├── src/
│   ├── main.tsx                  # Root: QueryClientProvider, AuthProvider, RouterProvider
│   ├── api/
│   │   ├── client.ts             # axios instances + refresh interceptor
│   │   ├── types.gen.ts          # generated from openapi
│   │   ├── auth.ts               # login, refresh, me, onboarding
│   │   ├── events.ts             # list, detail, create, rsvp, photo upload
│   │   ├── surveys.ts
│   │   ├── notifications.ts
│   │   ├── docs.ts
│   │   ├── users.ts
│   │   └── feedback.ts
│   ├── auth/
│   │   ├── store.ts              # Zustand auth store
│   │   ├── useAuth.ts
│   │   ├── guards.tsx            # RequireAuth, RequirePermission, OnboardingGate
│   │   └── permissions.ts        # hasPermission, hasAnyAdminPermission
│   ├── hooks/
│   │   ├── useEventSource.ts
│   │   ├── useAutosave.ts
│   │   ├── useDebounce.ts
│   │   └── useResponsive.ts      # replaces LayoutBuilder for >=720 side-panel
│   ├── router/
│   │   └── index.tsx             # createBrowserRouter + route tree
│   ├── layout/
│   │   ├── AppShell.tsx          # nav + outlet (replaces AppScaffold)
│   │   └── Nav.tsx
│   ├── screens/                  # one folder per screen, lazy-loaded
│   │   ├── home/
│   │   ├── login/
│   │   ├── calendar/
│   │   │   ├── CalendarScreen.tsx
│   │   │   ├── MonthView.tsx
│   │   │   ├── WeekView.tsx
│   │   │   ├── DayView.tsx
│   │   │   └── ListView.tsx
│   │   ├── events/
│   │   │   ├── EventDetailScreen.tsx
│   │   │   ├── EventForm.tsx
│   │   │   └── EventMemberSection.tsx
│   │   ├── surveys/
│   │   │   ├── SurveyScreen.tsx
│   │   │   ├── SurveyBuilderScreen.tsx
│   │   │   └── SurveyQuestionDialog.tsx
│   │   ├── admin/                # members, join-requests, flagged-events, whatsapp, join-form
│   │   ├── profile/
│   │   ├── onboarding/
│   │   ├── docs/
│   │   ├── guidelines/
│   │   ├── faq/
│   │   ├── donate/
│   │   └── install/
│   ├── components/               # shared presentational components
│   │   ├── ui/                   # shadcn primitives (button, dialog, input, etc.)
│   │   ├── RichEditor/           # TipTap wrapper + toolbar
│   │   ├── HtmlContent.tsx       # sanitized HTML renderer
│   │   ├── ImageCropDialog.tsx
│   │   ├── EventCard.tsx
│   │   └── ...
│   ├── models/                   # domain types built on top of api/types.gen.ts
│   │   ├── user.ts               # User + userHasPermission helpers
│   │   ├── event.ts
│   │   └── ...
│   └── utils/
│       ├── datetime.ts           # date-fns wrappers
│       ├── sanitize.ts           # DOMPurify wrapper
│       └── cn.ts                 # clsx + tailwind-merge
└── public/
    ├── fonts/                    # OpenDyslexic
    └── favicon, etc.
```

---

## Execution Rules (apply to every phase)

These are hard rules for how the work is carried out, not suggestions:

1. **Sub-agent swarming** — every phase with more than 5 new/modified files MUST be decomposed into parallel sub-agents, with **no single agent responsible for more than 5 files**. Agents run in parallel (single message, multiple Agent tool calls) and each receives explicit file scope, context, and style rules in its prompt. This protects context windows and prevents decay on large phases. Each sub-agent prompt must include: its exact file list, the behavioral spec it's porting from, the target stack conventions (from the "Target Stack" table above), and the file-size rule.
2. **File-size discipline**:
   - **Target**: ≤300 lines per file. Past 300 lines, start heeding the warning and look for a natural split (extract widgets → `components/`, extract hooks → `hooks/`, extract schemas → `models/`, extract constants/types to a sibling module).
   - **Hard cap**: 500 lines. Never exceed. A file approaching 500 must be split in the same phase, not deferred.
   - Count lines as-written, excluding generated files (`*.gen.ts`, `*.d.ts` from codegen).
   - Applies equally to screens, components, hooks, api modules, and tests.
3. **Verification gate per phase** — the phase is not done until: `npm run typecheck` is clean, `npm run lint` is clean, `npm run test` is green, and a manual smoke of the phase's screens passes. No proceeding to the next phase until these pass and the user explicitly approves.
4. **Re-read before edit** — per the CLAUDE.md override: after 10+ messages or any extended agent run, re-read files before editing. Agent tool results can be truncated and stale memory will corrupt edits.
5. **Senior-dev review filter** — before closing a phase, self-review: "what would a perfectionist senior dev reject in code review?" Duplicated state, inconsistent patterns, flaky tests, unsafe types (`any`/`as unknown as`), inaccessible components. Fix all of it before declaring the phase complete.

## Phased Execution

Per project rules: phased execution, no more than 5 files per agent per phase, verify before proceeding.

### Phase 0 — Scaffold (branch: `migration/vite-scaffold`)
- Create `frontend-next/` alongside current `frontend/` (keep Flutter app alive during migration)
- Vite scaffold, TS strict, Tailwind, ESLint flat config, Vitest
- `openapi-typescript` pipeline wired to Django OpenAPI endpoint
- Basic CI: typecheck + lint + test

### Phase 1 — Foundation (auth + routing + API client)
- Axios client + refresh interceptor
- Zustand auth store + `useAuth` hook
- Route guards
- Backend change: httpOnly refresh cookie (small Django Ninja change)
- Login + onboarding + new-password screens (proof of auth end-to-end)
- **Checkpoint**: manual test login → onboarding → landing

### Phase 2 — Public screens
- Home, join, join-success, login, magic-login, faq, donate, install, guidelines (read-only), calendar (read-only, list view only), event detail (read-only, public fields)
- react-big-calendar integration with month/week/day views
- **Checkpoint**: all public routes parity with Flutter

### Phase 3 — Member screens
- Profile, settings, event RSVP, event poll voting, volunteer, docs (read-only), surveys (respond)
- SSE notifications wired
- Image crop (avatar)
- **Checkpoint**: full member UX parity

### Phase 4 — Admin + editor screens
- TipTap rich editor + backend ProseMirror JSON migration
- Event create/edit form + photo upload/crop
- Docs editor + autosave
- Members, join-requests, event management, survey builder (dnd-kit), flagged events, whatsapp config, join-form admin, survey responses
- **Checkpoint**: full admin parity

### Phase 5 — Deploy cutover
- Dockerfile serves new Vite build; old Flutter build removed
- Delete `frontend/` (Flutter), rename `frontend-next/` → `frontend/`
- Monitor Railway for a week before tearing down any rollback path
- **Checkpoint**: production cutover

Each phase ends with a `make ci` pass + manual smoke of the phase's screens.

---

## Critical Files to Reference (not modify in this plan)

These are the behavioral specs the new implementation must match:

- `/Users/leahpeker/development/pda/frontend/lib/router/app_router.dart` — routing + guards
- `/Users/leahpeker/development/pda/frontend/lib/providers/auth_provider.dart` — auth state machine
- `/Users/leahpeker/development/pda/frontend/lib/services/api_client.dart` — refresh-lock semantics
- `/Users/leahpeker/development/pda/frontend/lib/services/notification_sse_web.dart` — SSE + backoff
- `/Users/leahpeker/development/pda/frontend/lib/widgets/autosave_mixin.dart` — autosave semantics
- `/Users/leahpeker/development/pda/frontend/lib/screens/calendar_screen.dart` — calendar view switching, side-panel rule
- `/Users/leahpeker/development/pda/frontend/lib/screens/calendar/event_detail_panel.dart` — event detail layout
- `/Users/leahpeker/development/pda/frontend/lib/screens/survey_builder_screen.dart` — drag-reorder + question types
- `/Users/leahpeker/development/pda/frontend/lib/widgets/quill_content_editor.dart` — Quill Delta serialization
- `/Users/leahpeker/development/pda/frontend/lib/widgets/photo_crop_dialog.dart` — crop modes
- `/Users/leahpeker/development/pda/frontend/lib/config/constants.dart` — FieldType, Permission, EventType enums
- `/Users/leahpeker/development/pda/backend/` — API endpoints (unchanged except auth cookie flip)

---

## Verification Strategy

At each phase checkpoint:

1. **Type check**: `npm run typecheck` (tsc --noEmit, strict) — zero errors
2. **Lint**: `npm run lint` (eslint strict) — zero warnings
3. **Unit tests**: `npm run test` (vitest) — all green, every hook and permission helper covered
4. **E2E tests** (Playwright): auth flow, calendar navigation, RSVP, survey builder drag-reorder, rich editor round-trip
5. **Bundle analysis**: `vite build --mode analyze` — baseline target ≤250kb gzipped for initial route, lazy chunks per deferred screen
6. **Accessibility**: axe-core run via Playwright on every public route — zero critical violations (project a11y rule)
7. **Manual cross-browser**: Safari (mobile quirks), Chrome, Firefox
8. **Performance check** (the actual goal): Lighthouse before/after comparison, specifically time-to-interactive and total bundle size. Target: ≥50% TTI reduction, ≥80% bundle reduction vs Flutter baseline.

Full end-to-end before cutover: run `make ci` (backend + frontend lint/test/typecheck), deploy to a Railway preview environment, run full E2E suite against it.

# app store readiness — systematic dive

_date: 2026-05-29 · based on a parallel audit of the current Vite + React SPA and Django backend_

## the headline answer

**no, you do not translate react into xcode.** the app is a pure browser SPA (Vite + React 19,
React Router 7, Zustand, TanStack Query, axios, Tailwind). there is no React Native, no Capacitor,
no PWA layer today.

there are three ways onto the App Store, and they differ by an order of magnitude in effort:

| path | what it is | effort | code reuse | apple 4.2 risk |
|------|-----------|--------|-----------|----------------|
| **A — Capacitor wrap** (recommended) | existing React runs unchanged in a native WKWebView; Capacitor generates the Xcode project + native plugin bridge | ~1–2 weeks | ~95% | medium → **low** once real native features are added |
| **B — PWA + thin shell** | make it an installable PWA first; optionally wrap for the store | ~3–10 days | ~98% | **high** as a store path (thinnest wrapper = likeliest rejection); PWA-only isn't *on* the store |
| **C — React Native rewrite** | re-implement every screen in RN, reuse only api/models/logic | ~3–6 months | ~30–40% | low |

xcode is still required for **all** paths — to build, sign, and upload (a Mac is mandatory). but
under path A you only open Xcode to configure signing/capabilities and submit; you don't rewrite code.

## recommendation: path A (Capacitor), with a deliberate 4.2 mitigation plan

- **why not C:** it throws away ~60–70% of a codebase you *just* migrated from Flutter — every
  screen, plus the DOM-bound libraries (`react-big-calendar`, `tiptap`, `react-image-crop`,
  `react-day-picker`, `dnd-kit`, `react-phone-number-input`), styling, and navigation. a second
  rewrite for a small team, and it doubles maintenance forever.
- **why not B as a destination:** PWA-only doesn't put you on the App Store (the actual goal), and a
  *thin* wrapper is the single highest-risk thing to show Apple's 4.2 reviewers. the moment you add
  native value to survive review, you've reconverged on path A. **do** the PWA layer first as a cheap
  win, then wrap.
- **bonus:** `npx cap add android` gets you Google Play from the same codebase almost for free.

## performance vs. maintenance tradeoff (Capacitor vs. React Native)

the two paths trade off against each other on exactly one axis: **Capacitor trades some performance
polish for a single codebase; React Native trades a permanent second codebase for native
performance.** for a small team that just finished one migration, the single-codebase win is large
and the performance cost is modest for *this* app's workload.

| | Capacitor (A) | React Native (C) |
|---|---|---|
| codebases to maintain | **1** — web = iOS = Android | **2** — the web app *plus* a separate RN app |
| feature built how many times | once | twice (web + native) |
| performance | good, with caveats (below) | best-in-class native |

### does React Native mean maintaining 2 versions? — **yes**

this is the counterintuitive part: **Capacitor is the one-codebase option, RN is the two-codebase
option.**

- **Capacitor:** the existing web app *is* the mobile app. the same `src/` ships to web (Railway),
  iOS, and Android. one source of truth, no divergence. thin extra surface (Capacitor config, native
  plugins, Xcode upgrades, store resubmits) — but the app itself is built once.
- **React Native:** RN is **not** the web. `react-big-calendar`, `tiptap`, `react-image-crop`,
  `react-day-picker`, `dnd-kit`, and Tailwind styling **do not run in RN** — they're DOM/browser
  libraries with no drop-in RN equivalents. so you'd keep the **web app** (you still serve a website)
  *and* build a **separate RN app**: two UI codebases, two navigation systems, two styling systems,
  maintained in parallel forever. they *will* drift. the genuinely shared code is the **non-visual**
  layer only — `src/api`, `src/models`, `types.gen.ts`, zod schemas, auth *logic* (~30–40%). the
  entire visual layer (~60–70%) is duplicated.

### are there performance issues with the Capacitor wrap?

Capacitor runs your React app in **WKWebView** — the same engine as Safari, with the same JIT-enabled
JS compiler Apple grants its own browser. raw JS/render perf is "modern mobile Safari," which is fast.
the honest gaps vs. native:

- **slower cold start** — boots the native shell, *then* spins up the WebView, loads the JS bundle,
  hydrates React, and runs `restoreSession()` before first paint. noticeably longer than native; the
  splash screen hides it. lazy-loaded routes help.
- **scroll/gesture feel** — good but slightly "webby" (momentum, rubber-band overscroll). native uses
  recycled cell rendering; the DOM does not.
- **heavy DOM is the real risk** — `react-big-calendar` (dense grid, many nodes), `dnd-kit` drag, and
  long member/event lists are the spots most likely to drop frames, especially on older devices.
  tunable with list virtualization and a lighter mobile calendar view.
- **native bridge latency** — tiny per-call overhead for push/camera/storage; irrelevant at this
  app's frequency.
- **animations** — CSS transitions are fine; no free native-quality page/shared-element transitions.

**totally fine:** API-driven screens (forms, detail views, settings) are indistinguishable from
native in practice, and the app is already mobile-shaped (`AppShell` + `BottomNav`, safe-area).

**bottom line:** for a members-only community app (calendar, events, RSVPs, notifications, profiles),
Capacitor performance is good enough and most users won't notice. the real caveats are cold-start
time and scroll/drag feel on the calendar + long lists — tunable, not dealbreakers. this calculus
would change for a game, a heavy-animation social feed, or a maps-heavy app.

### the escape hatch

ship Capacitor now (one codebase, on the store fast). if a *specific* screen later proves too janky,
drop a single native view for just that screen via a Capacitor plugin — without rewriting the whole
app. you don't have to choose perfection up front.

## the real prep work: it's not "translation," it's these buckets

### 🔴 blockers — the app won't function in a wrapper without these

1. **API base URL is relative / same-origin.** `src/config/env.ts` defaults `VITE_API_URL` to `""`,
   and the whole prod setup relies on nginx proxying `/api` and `/media` same-origin. inside a
   `capacitor://` origin, every relative request and image breaks. **fix:** parameterize
   `VITE_API_URL` (Dockerfile `ARG` + Railway build-arg) to an absolute `https://` API URL, and make
   the wrapper build use it.
   - files: `frontend/src/config/env.ts`, `frontend/src/api/client.ts`, `Dockerfile`,
     `nginx.conf.template`

2. **media/image URLs are relative** (`/media/...` from `media_path()`). avatars and event photos
   won't load from a `capacitor://` origin. **fix:** return absolute media URLs (domain in an env
   var) or serve media via an origin-agnostic API endpoint.
   - files: `backend/config/media_proxy.py`, `backend/users/schemas.py`,
     `frontend/src/screens/settings/AvatarUpload.tsx`

3. **CORS doesn't allow the WebView origin.** prod `CORS_ALLOWED_ORIGINS` is env-driven and won't
   include `capacitor://localhost`. with `CORS_ALLOW_CREDENTIALS = True` + httpOnly cookies this
   matters. **fix:** add the WebView origin(s) to the allowlist.
   - file: `backend/config/settings.py`

4. **magic-login email links break on iOS.** the primary onboarding path emails an
   `https://…/magic-login/{token}` link; tapped from Mail on iOS it opens Safari, not the app, and
   the httpOnly refresh cookie set in Safari is isolated from the WebView → user lands logged out.
   **fix:** Universal Links — host `/.well-known/apple-app-site-association`, add the Associated
   Domains entitlement, handle Capacitor's `appUrlOpen` and route into React Router. scope AASA
   `paths` to the auth/magic-login routes only.
   - files: `frontend/src/screens/auth/MagicLoginScreen.tsx`,
     `frontend/src/utils/welcomeMessage.ts`, `backend/config/settings.py` (`FRONTEND_BASE_URL`),
     new `.well-known/apple-app-site-association` served by Django/WhiteNoise

### managing the two notification channels (SSE + native push)

after wrapping you have **two transports**, but they cover **different app states** — they're
complementary, not redundant:

| | **foreground** (app open) | **background** (app closed/minimised) |
|---|---|---|
| transport | SSE (`useEventSource`) | APNs native push |
| effect | live badge + dropdown refresh + in-app toast | lock-screen alert + app-icon badge |

SSE can't reach a backgrounded app (iOS kills the connection); push is the only way to reach a closed
app. so the rule is: **SSE owns the foreground, APNs owns the background.**

**one source of truth — the backend.** both channels are driven from the existing 13
`create_*_notification()` functions in `backend/notifications/service.py`. every one already ends with
the same pattern: write `Notification` row(s) → call `_notify_users(ids)`. push is **one new helper,
`_push_users(ids, …)`, called right after `_notify_users`** — not 13 scattered edits. the
`Notification` table stays authoritative; SSE and APNs are just two ways to *announce* a new row.

**avoiding double-notification** (the only real coordination problem):

- **foreground:** SSE updates the UI; the client's `pushNotificationReceived` handler **suppresses the
  banner** when the app is active (just invalidates caches). user never sees a banner over an open app.
- **background:** SSE is dead → APNs banner fires; tapping deep-links into the screen (reuses the
  Universal Links machinery from blocker #4).
- **reopened:** `useEventSource` reconnects and the bell re-reads `unread-count` from the table —
  anything that arrived via push while away is already reflected. no reconciliation logic; the table
  is authoritative.

**`event_updated` pings (`_ping_event_update`) stay SSE-only** — they're silent cache invalidations
with no notification row, so they should never become a push (no value buzzing a backgrounded user
about a co-host roster refresh).

**build cost (additive — SSE is untouched):**
- backend: `PushSubscription` model (user + device token + platform), subscribe/unsubscribe endpoints,
  `_apns_sender.py` (token-based `.p8`), one `_push_users()` call per service function, and dead-token
  pruning (APNs reports invalid tokens).
- client: `@capacitor/push-notifications` — request permission, register, POST token to
  `/api/push/subscribe/`, suppress foreground banners. re-register on login; delete token on logout.
- web: unchanged — browsers keep using SSE only.

**iOS-only vs. also-Android:** direct APNs is simplest if iOS-only. if you'll add Android later,
routing both through Firebase Cloud Messaging (`@capacitor-firebase/messaging`) gives one token format
and one send path (on iOS, FCM still rides on APNs underneath).

### 🟠 major — needed for the app to feel real & survive review

5. **no native push.** today notifications are SSE (`useEventSource` + `NotificationBell`) — these
   work in a WebView but die when the app is backgrounded, and **web push does not work in iOS
   WebViews at all.** an "app" with no background notifications both feels broken and invites a 4.2
   rejection. **fix:** add `@capacitor/push-notifications` on the client + an APNs path on the
   backend: a `PushSubscription` model (device token + platform), subscribe/unsubscribe endpoints,
   an APNs sender (token-based `.p8` key), and hook the 13 existing
   `create_*_notification()` functions to also push.
   - files: `frontend/src/hooks/useEventSource.ts`, `frontend/src/layout/NotificationBell.tsx`,
     `backend/notifications/service.py`, new `backend/notifications/_apns_sender.py` + model

6. **httpOnly refresh-cookie persistence across app launches is unreliable in WKWebView.** the
   session may not survive killing the app. **fix:** test it; if it doesn't persist, move the refresh
   token to Capacitor secure storage (iOS Keychain) with a header-based refresh flow.
   - files: `frontend/src/api/client.ts`, `frontend/src/auth/store.ts`,
     `backend/users/_refresh_cookie.py`

7. **Guideline 4.2 (minimum functionality).** a bare "website in a box" is the textbook rejection.
   mitigate by shipping ≥2 genuine native features in v1 (push is #1; native camera/photo picker for
   the existing crop/upload flow is #2), plus a native shell (splash, status-bar styling, no browser
   chrome), persistent login, and a graceful offline screen. provide **reviewer demo credentials**
   in App Review notes — the app is members-only with no self-signup.

### 🟡 minor — polish / cleanup

8. **router history:** `createBrowserRouter` assumes real URLs; under a `file://`/custom-scheme
   origin switch to hash/memory history or serve via Capacitor's local server.
9. **`window.location.href` navigation** in `EventManagementScreen.tsx:159` → use `navigate()`.
10. **COOP/COEP headers** in `backend/config/middleware.py` are leftover from Flutter (Skwasm) and
    inappropriate for React in a WebView; review/remove. consider adding a real CSP.
11. **localStorage** (accessibility prefs) can be purged by WKWebView → prefs reset on relaunch;
    consider native storage via `@capacitor/preferences`.
12. **safe-area insets** are already handled correctly (`env(safe-area-inset-*)` in BottomNav /
    AppShell). ✅ nothing to do.
13. **.ics download** `download` attribute is ignored on iOS; file opens instead of saving.
14. **file upload / HEIC** support varies in WebView; no in-app camera without a native plugin.

## non-code requirements (Apple logistics)

- **Apple Developer account:** $99/yr (Individual = fastest, ~24–48h, your personal name as seller).
  Organization = org name as publisher but needs a **D-U-N-S number** + ~1–3 weeks verification.
  **Nonprofit fee waiver** (free) exists but requires an Org account, D-U-N-S, recognized-nonprofit
  docs, and no paid apps/IAP — budget weeks. start this early; it's the long pole.
- **Sign in with Apple: NOT required.** Guideline 4.8 only triggers on third-party/social login
  (Google/Facebook/etc.). PDA's first-party email magic-link qualifies for the "exclusively uses your
  own account system" exemption — *as long as you never add a social login button.*
- **Privacy:** a public **Privacy Policy URL** (required) + App Privacy "nutrition label" declaring
  email/name/phone (+pronouns) as "linked, App Functionality," and declare **no tracking** (so no ATT
  prompt). add an **in-app account-deletion** path (Apple requires it for account-based apps).
  watch for `PrivacyInfo.xcprivacy` (Capacitor plugins usually ship their own).
- **Submission:** Mac + Xcode + App Store Connect; TestFlight for member beta; ~24–48h review;
  top first-time rejection reasons are 4.2 (wrapper), missing/mismatched privacy, and login walls
  with no reviewer demo account.

## suggested sequence

1. **PWA layer first** (~few days): `vite-plugin-pwa`, manifest, icons, offline shell. improves the
   web product now and primes Android install. (the existing `/install` screen already coaches users
   on "add to home screen.")
2. **make the app wrapper-safe** (the 🔴 blockers): absolute API + media URLs, build-time
   `VITE_API_URL`, CORS for the WebView origin, Universal Links + AASA for magic-login.
3. **add native value** (the 🟠 majors): Capacitor + APNs push, native camera, secure-storage auth,
   `cap add ios`, native shell polish.
4. **Apple logistics in parallel** from day 1: developer account (+ D-U-N-S/waiver if org), privacy
   policy, account-deletion path, reviewer demo credentials.
5. **submit** via TestFlight → App Store. `cap add android` afterward for Play.

## what's already in good shape

- safe-area insets handled; app is already mobile-shaped (`AppShell` + `BottomNav`).
- SSE realtime + polling fallback is solid for web and works in a WebView (just not backgrounded).
- DOMPurify sanitization, httpOnly refresh token, in-memory access token — good security posture.
- an `/install` screen already exists — the team already thinks in PWA/home-screen terms.

# Flutter → React Test Migration Plan

Analysis of all 56 Flutter test files in `frontend/test/` and whether each can be
ported to `frontend-next` without new feature implementation.

**Status as of 2026-04-18:**
- Already ported (earlier sessions): 6 new test files, ~10 tests added to existing files
- Remaining: 45 test files analysed below

---

## Already Ported

| React test file | Flutter source | What it covers |
|---|---|---|
| `api/eventMapper.test.ts` | implicit in provider tests | `mapEvent`/`mapGuest`: field mapping, null defaults, Date conversion |
| `models/event.test.ts` | `unit/event_colors_test.dart` | `eventClass`: precedence (cancelled > official > invite > members > community) |
| `utils/datetime.test.ts` (extended) | screen/widget tests | `formatEventDateTime` (4 branches), `formatDayHeader` |
| `screens/events/form/datetimeUtils.test.ts` | `unit/ics_generator_test.dart` | `isoToLocalInput`/`localInputToIso`: null, invalid, roundtrip |
| `screens/events/form/validateEventForm.test.ts` | — | `validateEventForm`: all 7 rule branches |
| `accessibility/store.test.ts` | `unit/accessibility_preferences_provider_test.dart` | Zustand store: defaults, setThemeMode, toggleDyslexiaFont, setTextScale |

Already existed in React (equivalent coverage):
`utils/validators.test.ts`, `utils/errors.test.ts`, `utils/eventColors.test.ts`,
`App.test.tsx` (login flow), `api/client.test.ts` (token refresh),
`models/permissions.test.ts`, `components/HtmlContent.test.tsx`, `utils/cn.test.ts`

---

## Tier 1 — Port directly, no new feature code

All these test existing React implementations. Only test files need to be written.

### Auth store (`auth/store.ts`)
**From:** `providers/auth_provider_test.dart`
**Test file:** `src/auth/store.test.ts`

React's Zustand store has identical operations to Flutter's `AuthNotifier`. Tests
mock `@/api/auth` with `vi.mock` and assert `useAuthStore.getState()`.

| # | Test case |
|---|---|
| 1 | `restoreSession` with no stored session → `status: 'unauthed'` |
| 2 | `login` success → `status: 'authed'`, user populated |
| 3 | `login` success → access token stored in state |
| 4 | `logout` → `status: 'unauthed'`, user null |
| 5 | `forceLogout` → synchronous, `status: 'unauthed'` |
| 6 | `login` 401 → re-throws axios error, `status: 'unauthed'` |
| 7 | `login` network failure → re-throws, `status: 'unauthed'` |
| 8 | `login` 500 → re-throws, `status: 'unauthed'` |

---

### Auth guards (`auth/guards.tsx`)
**From:** `router/public_access_test.dart`, `flows/auth_flow_test.dart`
**Test file:** `src/auth/guards.test.tsx`

React has `RequireAuth`, `RequirePermission`, `OnboardingGate`. Tests use RTL +
`MemoryRouter` with `useAuthStore.setState()` to simulate auth states.

| # | Test case |
|---|---|
| 1 | Unauthed user hitting `RequireAuth` → redirected to `/login?redirect=…` |
| 2 | Authed user hitting `RequireAuth` → renders outlet |
| 3 | Authed user without permission hitting `RequirePermission` → redirected to `/calendar` |
| 4 | Authed user with permission hitting `RequirePermission` → renders outlet |
| 5 | Unauthed user hitting `RequirePermission` → redirected to `/login` |
| 6 | `OnboardingGate`: `needsOnboarding` + empty displayName → redirected to `/onboarding` |
| 7 | `OnboardingGate`: `needsOnboarding` + has displayName → redirected to `/new-password` |
| 8 | `OnboardingGate`: authed + complete on `/onboarding` → redirected to `/guidelines` |
| 9 | `OnboardingGate`: authed + complete on `/login` → redirected to `/calendar` |

**Not ported (Flutter-specific):** Case-insensitive routing (`/Calendar`, `/LOGIN`) —
React Router is case-sensitive by design.

---

### API hooks — content (`api/content.ts`)
**From:** `providers/home_provider_test.dart`, `providers/guidelines_provider_test.dart`
**Test file:** `src/api/content.test.ts`

Uses `renderHook` + `QueryClient` with `retry: false`. Mocks `apiClient` via `vi.mock`.

| # | Test case |
|---|---|
| 1 | `useHome` fetches and returns home content + donateUrl |
| 2 | `useHome` donateUrl defaults to empty string when null |
| 3 | `useUpdateHome` PATCHes API and invalidates home query |
| 4 | `useUpdateHome` propagates error on failure |
| 5 | `useGuidelines` fetches and returns guidelines content |
| 6 | `useGuidelines` propagates error on failure |
| 7 | `useUpdateGuidelines` PATCHes API and invalidates guidelines query |

---

### API hooks — notifications (`api/notifications.ts`)
**From:** `providers/notification_provider_test.dart`
**Test file:** `src/api/notifications.test.ts`

| # | Test case |
|---|---|
| 1 | `useNotifications` returns list of notifications when authed |
| 2 | `useNotifications` query disabled when unauthed (enabled: false) |
| 3 | `useNotifications` propagates error on API failure |
| 4 | `useUnreadCount` returns count from API |
| 5 | `useMarkAllNotificationsRead` POSTs and invalidates notifications query |

---

### API hooks — join requests (`api/join.ts`)
**From:** `providers/join_request_management_provider_test.dart`, `providers/join_request_provider_test.dart`
**Test file:** `src/api/join.test.ts`

| # | Test case |
|---|---|
| 1 | `useJoinRequests` returns list on success |
| 2 | `useJoinRequests` surfaces 403 as a distinct error |
| 3 | `useJoinRequests` re-throws other API errors |
| 4 | `useSubmitJoinRequest` throws `AlreadyInvitedError` on 409 |
| 5 | `useSubmitJoinRequest` surfaces validation detail on 400 |
| 6 | `useSubmitJoinRequest` propagates network errors |

---

### Home screen (`screens/public/HomeScreen.tsx`)
**From:** `screens/home_screen_test.dart`
**Test file:** `src/screens/public/HomeScreen.test.tsx`

| # | Test case |
|---|---|
| 1 | Shows loading indicator while fetching |
| 2 | Shows join CTA for unauthenticated user |
| 3 | Hides join CTA for authenticated user |
| 4 | Shows donate button when `donateUrl` is non-empty |
| 5 | Hides donate button when `donateUrl` is empty |
| 6 | Shows edit buttons for user with `edit_homepage` permission |

---

### FAQ screen (`screens/public/FaqScreen.tsx`)
**From:** `screens/faq_screen_test.dart`
**Test file:** `src/screens/public/FaqScreen.test.tsx`

| # | Test case |
|---|---|
| 1 | Shows loading indicator while fetching |
| 2 | Hides edit button for member without `edit_faq` |
| 3 | Shows edit button for user with `edit_faq` permission |

---

### Guidelines screen (`screens/public/GuidelinesScreen.tsx`)
**From:** `screens/guidelines_screen_test.dart`
**Test file:** `src/screens/public/GuidelinesScreen.test.tsx`

| # | Test case |
|---|---|
| 1 | Shows loading indicator while fetching |
| 2 | Hides edit button for member without `manage_guidelines` |
| 3 | Shows edit button for user with `manage_guidelines` permission |

---

### Install app screen (`screens/public/InstallAppScreen.tsx`)
**From:** `screens/install_app_screen_test.dart`
**Test file:** `src/screens/public/InstallAppScreen.test.tsx`

| # | Test case |
|---|---|
| 1 | Renders page title and subtitle |
| 2 | Shows both platform section titles (Android and iOS) |
| 3 | Shows step content |
| 4 | Accessible to unauthenticated users (no crash) |
| 5 | Accessible to authenticated users |

---

### Join screen + join flow (`screens/public/JoinScreen.tsx`, `JoinSuccessScreen.tsx`)
**From:** `screens/join_screen_test.dart`, `flows/join_flow_test.dart`
**Test file:** `src/screens/public/JoinScreen.test.tsx`

| # | Test case |
|---|---|
| 1 | Renders required form fields |
| 2 | Shows validation error when required fields are empty |
| 3 | Shows error message on submission failure |
| 4 | Navigates to `/join/success` on successful submission |
| 5 | End-to-end: fill form and submit → success screen |

---

### Calendar screen (`screens/calendar/CalendarScreen.tsx`)
**From:** `screens/calendar_screen_test.dart`
**Test file:** `src/screens/calendar/CalendarScreen.test.tsx`

| # | Test case |
|---|---|
| 1 | Renders view switcher (month/week/day/list) |
| 2 | Renders today button |
| 3 | Shows loading indicator while events load |
| 4 | FAB shown for user with `create_events` permission |
| 5 | FAB hidden for user without `create_events` permission |

---

### Notification bell (`layout/NotificationBell.tsx`)
**From:** `widgets/notification_bell_test.dart`
**Test file:** `src/layout/NotificationBell.test.tsx`

| # | Test case |
|---|---|
| 1 | Shows badge when unread count > 0 |
| 2 | Badge not visible when unread count is 0 |
| 3 | Tapping bell opens notifications panel |
| 4 | Shows empty state when no notifications |
| 5 | Shows mark-all-as-read button |
| 6 | Tapping event_invite notification navigates to `/events/:id` |

---

### App shell + bottom nav (`layout/AppShell.tsx`, `layout/BottomNav.tsx`)
**From:** `widgets/app_scaffold_test.dart`, `widgets/app_scaffold_a11y_test.dart`
**Test file:** `src/layout/AppShell.test.tsx`

| # | Test case |
|---|---|
| 1 | Bottom nav renders expected destinations |
| 2 | Tapping a destination navigates |
| 3 | Bottom nav visible on narrow viewport |
| 4 | Bottom nav visible on wide viewport |

---

### Event detail screen (`screens/events/EventDetailScreen.tsx`, `EventMemberSection.tsx`)
**From:** `screens/event_detail_screen_test.dart`, `widgets/event_detail_panel_test.dart`
**Test file:** `src/screens/events/EventDetailScreen.test.tsx`

| # | Test case |
|---|---|
| 1 | Renders event title |
| 2 | Shows location for authenticated member |
| 3 | Hides location for guest |
| 4 | Shows description |
| 5 | Shows WhatsApp link for authenticated member |
| 6 | Hides WhatsApp link for guest |
| 7 | Shows login prompt for guest |

---

### Event admin actions (`screens/events/EventAdminActions.tsx`)
**From:** `widget/event_detail_edit_button_test.dart`, `widgets/event_detail_panel_test.dart`
**Test file:** `src/screens/events/EventAdminActions.test.tsx`

| # | Test case |
|---|---|
| 1 | Creator sees edit + delete for upcoming event with no attendees |
| 2 | Co-host sees edit + cancel for upcoming event |
| 3 | Creator sees only delete (no edit) for past event |
| 4 | Regular member sees no admin actions |
| 5 | Unauthenticated user sees no admin actions |

---

### Image crop dialog (`components/ImageCropDialog.tsx`)
**From:** `widgets/photo_crop_dialog_test.dart`
**Test file:** `src/components/ImageCropDialog.test.tsx`

| # | Test case |
|---|---|
| 1 | Circle mode renders with correct title and action buttons |
| 2 | Rectangle mode renders with correct title |
| 3 | Renders helper instruction text |
| 4 | Cancel button calls onClose/onCancel |
| 5 | Dialog has `role="dialog"` (Semantics equivalent) |

---

### Settings screen — accessibility section (`screens/settings/SettingsScreen.tsx`)
**From:** `widget/settings_accessibility_test.dart`
**Test file:** `src/screens/settings/SettingsScreen.test.tsx`

| # | Test case |
|---|---|
| 1 | Renders theme mode selector with `system` selected by default |
| 2 | Tapping dark segment updates `useAccessibilityStore.themeMode` |

---

## Tier 2 — Port with `jest-axe` (no new feature code)

**Required package:** `npm install --save-dev jest-axe @types/jest-axe`

The 10 Flutter accessibility test files use Flutter's `AccessibilityGuideline` and
`SemanticsController` APIs. The web equivalents are `jest-axe` (axe-core) + RTL
semantic queries. All screens being tested already exist in React.

| Flutter file | React equivalent | Blocked? |
|---|---|---|
| `calendar_views_a11y_test.dart` | Event chips have `aria-label` with title | No |
| `date_time_picker_a11y_test.dart` | Date/time inputs are labeled | Partially — no custom picker |
| `focus_traversal_test.dart` | Join/login forms have correct tab order | No |
| `gesture_detector_audit_test.dart` | No `<div onClick>` — only `<button>` | No |
| `guidelines_test.dart` | Join/login pass axe scan | No |
| `install_app_a11y_test.dart` | Install screen passes axe scan | No |
| `month_view_a11y_test.dart` | Day cells + event chips have `aria-label` | No |
| `photo_crop_dialog_a11y_test.dart` | Crop dialog passes axe scan | No |
| `semantics_test.dart` | Submit/Login buttons discoverable by role | No |
| `feedback_a11y_test.dart` | Feedback button/form axe scan | **Yes — feedback not implemented** |

---

## Tier 3 — Requires new feature implementation first

### Feedback feature (~16 tests across 4 files)
**Flutter files:** `widgets/feedback_button_test.dart` (5), `widgets/feedback_form_test.dart` (5),
`providers/feedback_provider_test.dart` (2), `accessibility/feedback_a11y_test.dart` (4)

**What's missing in React:** Everything — no feedback component, no API hook.

**Implementation required:**

1. **`api/feedback.ts`** — `useSubmitFeedback` mutation hook, POSTs to
   `/api/community/feedback/` with `{ title, description, route, user_agent }`

2. **`components/FeedbackButton.tsx`** — Floating `?` button in the bottom-right
   corner. Enabled/disabled via a compile-time flag (default: off). Opens `FeedbackForm`
   in a bottom sheet on tap.

3. **`components/FeedbackForm.tsx`** — Title field (`maxLength=200`) + description
   field (`maxLength=2000`). Sends current pathname and `navigator.userAgent` as
   metadata. Cancel and submit actions. Does not display metadata to the user.

**Tests that unlock after implementation:**
- FeedbackButton renders `?` icon
- Tap opens form; cancel closes form
- Title/description fields with correct maxLength constraints
- `useSubmitFeedback` POSTs correct payload; sets error state on failure
- Form passes axe scan (Tier 2)

---

### Members screen + user management API (~10 tests across 2 files)
**Flutter files:** `screens/members_screen_test.dart` (5),
`providers/user_management_provider_test.dart` (5)

**What's missing in React:** `/members` is a `<Stub />` placeholder. No user
management mutations exist.

**Implementation required:**

1. **`api/users.ts`** — `useUsers` (GET list), `useCreateUser` (POST), `useBulkCreateUsers`
   (POST), `useDeleteUser` (DELETE). Each mutation must invalidate the users query on success.
   403 responses should surface as a distinct error (not swallowed).

2. **`screens/admin/MembersScreen.tsx`** — Member list with Members + Roles tabs.
   Add-member button gated on `manage_users` permission. Empty state. Clicking a member
   row navigates to `/members/:id`.

3. **`screens/admin/MemberDetailScreen.tsx`** — Referenced by notification bell
   navigation (`magic_link` → `/members/:id`) but not yet implemented.

**Tests that unlock after implementation:**
- `useUsers` returns list; surfaces 403 distinctly; re-throws other errors
- `useCreateUser` returns user data and invalidates users query
- `useBulkCreateUsers` returns result map and invalidates users query
- `useDeleteUser` calls delete endpoint and invalidates users query
- Members screen: renders Members/Roles tabs
- Members screen: displays member names
- Members screen: add-member button shown/hidden based on `manage_users`
- Members screen: shows empty state when no members

---

### Error reporter (~4 tests)
**Flutter file:** `services/error_reporter_test.dart`

**What's missing in React:** No equivalent service. Flutter's `ErrorReporter` POSTs
to the backend with route context when a token is available.

**Implementation required:**

1. **`utils/errorReporter.ts`** — `reportError(error, route)` function that:
   - Requires `accessToken` from `useAuthStore` (skip + console.error if absent)
   - POSTs `{ message, stack, route, timestamp }` to `/api/community/error-report/`
   - Falls back to `console.error` if POST fails

**Tests that unlock after implementation:**
- POSTs error with token when authed
- Includes current route in payload
- Does not POST when no token (falls back to console.error)
- Falls back to console.error when POST itself fails

---

### Calendar list view with search and filtering (~10 tests)
**Flutter file:** `screens/calendar/list_view_test.dart`

**What's missing in React:** React's calendar uses `react-big-calendar`'s agenda
view which has no search, type filter, or sort capabilities.

**Implementation required:**

1. **Custom list view component** — Scrollable event list grouped by day, replacing
   or augmenting react-big-calendar's agenda view when the "list" tab is active.

2. **Upcoming / Past toggle** — Filters events by `isPast` flag.

3. **Title search** — Text input with clear button; filters by title substring
   (case-insensitive).

4. **Event type filter** — Chip/dropdown filter for `official` / `community`
   event types.

5. **Sort direction toggle** — Ascending / descending by start date.

6. **Empty states** — "no upcoming events", "no matches for search".

**Tests that unlock after implementation:**
- Renders all upcoming events by default
- Past tab shows past events
- Search by title filters results
- Clear search button resets query
- Type filter "official" shows only official events
- Type filter "community" shows only community events
- Empty state shown when no upcoming events
- Empty state shown when search has no matches
- Tapping a row navigates to `/events/:id`
- Sort direction toggle changes order

---

## Tier 4 — Not applicable (Flutter-specific)

| Flutter test file | Reason |
|---|---|
| `screens/calendar/month_placement_calculator_test.dart` | Custom grid placement algorithm — React uses `react-big-calendar` which handles layout internally |
| `screens/calendar/week_placement_calculator_test.dart` | Same |
| `router/app_router_test.dart` | Tests GoRouter instance identity across state changes — not a concern in React Router's `createBrowserRouter` |
| `router/app_router_semantics_test.dart` | GoRoute `name:` field for Flutter semantics — React Router uses paths, not named routes |
| `unit/config/app_theme_test.dart` | Material Theme platform page transition config — React uses Tailwind CSS |
| `services/app_logger_test.dart` | Flutter `logging` package — React has no equivalent centralised logger |
| `widgets/date_time_picker_test.dart` | Custom wheel-based date/time picker widget — React uses `<input type="datetime-local">`. Time-clamping, controller sync, and firstDate constraint tests have no browser input equivalent. |

---

## Summary

| Tier | Files | Est. tests | Effort |
|---|---|---|---|
| **Already ported** | 6 new + 1 extended | ~50 | Done |
| **Tier 1** — port now | ~20 files | ~85 | Write tests only |
| **Tier 2** — add jest-axe | 9 files | ~20 | Add package + write tests |
| **Tier 3** — needs implementation | 4 feature areas | ~30 | Implement features first |
| **Tier 4** — N/A | 7 files | ~30 | Skip |

**Recommended sequence:** Tier 1 → Tier 3 implementations → Tier 2 → done.

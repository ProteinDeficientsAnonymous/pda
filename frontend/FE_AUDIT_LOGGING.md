# Frontend Audit Logging Plan

## Current State

The app has solid logging **infrastructure** that is barely used:

| Layer | Files | With Logger | Coverage |
|-------|-------|-------------|----------|
| Services | 6 | 4 | Good — `api_client`, `secure_storage`, `error_reporter`, `app_logger` |
| Providers | 18 | 3 | Poor — only `auth`, `event`, `notification` |
| Screens | ~45 | 0 | None |
| Widgets | 19 | 2 | `photo_crop_dialog`, `profile_avatar` only |
| Router | 1 | 0 | None |

**70+ catch blocks across screens have zero logging.** 10+ use `catch (_)` discarding the error entirely. All user actions, admin operations, and most errors are invisible beyond the HTTP-level Dio interceptor.

### Existing infrastructure to reuse

- `AppLogger.get(name)` → returns a named `Logger` (`frontend/lib/services/app_logger.dart`)
- `ErrorReporter.report()` → POSTs to `/api/community/error-report/` (`frontend/lib/services/error_reporter.dart`)
- Release mode logs WARNING+ only; debug logs ALL

### Standard pattern (from `auth_provider.dart`, `notification_provider.dart`)

```dart
final _log = Logger('ProviderName');

// Success at INFO
_log.info('created user ${user.id}');

// Failure at WARNING with error + stack
_log.warning('failed to create user', e, st);

// Catch blocks: always capture error + stack trace
try {
  await doThing();
  _log.info('did thing');
} catch (e, st) {
  _log.warning('failed to do thing', e, st);
  rethrow; // or show snackbar
}
```

---

## Phase 1 — Security-Critical Providers (5 files)

### 1. `frontend/lib/providers/user_management_provider.dart` (133 lines, NO Logger)

Add `Logger('UserManagement')`. Log at INFO level on success, WARNING on failure for:

| Method | Lines | Log message |
|--------|-------|-------------|
| `createUser()` | 38-56 | `'created user {phone}'` |
| `bulkCreateUsers()` | 58-67 | `'bulk created {count} users'` |
| `deleteUser()` | 69-73 | `'deleted user {id}'` |
| `resetPassword()` | 75-79 | `'reset password for user {id}'` |
| `generateMagicLink()` | 81-85 | `'generated magic link for user {id}'` |
| `togglePause()` | 87-91 | `'toggled pause for user {id}'` |
| `updateUserRoles()` | 93-101 | `'updated roles for user {id}'` |
| `createRole()` | 103-110 | `'created role {name}'` |
| `updateRole()` | 112-120 | `'updated role {id}'` |
| `deleteRole()` | 122-127 | `'deleted role {id}'` |

All methods lack try/catch — wrap each in try/catch with `_log.warning(...)` + rethrow.

### 2. `frontend/lib/providers/auth_provider.dart` (165 lines, HAS Logger — gaps)

Already has `Logger('AuthProvider')`. Add logging to uncovered methods:

| Method | Lines | Issue | Add |
|--------|-------|-------|-----|
| `magicLogin()` | 74-86 | No try/catch, no logging | Wrap, log success + failure |
| `updateProfile()` | 88-102 | No try/catch, no logging | Wrap, log success + failure |
| `changePassword()` | 104-113 | No try/catch, no logging | Wrap, log success + failure |
| `completeOnboarding()` | 115-131 | No try/catch, no logging | Wrap, log success + failure |
| `uploadProfilePhoto()` | 133-141 | No try/catch, no logging | Wrap, log success + failure |
| `deleteProfilePhoto()` | 143-147 | No try/catch, no logging | Wrap, log success + failure |

### 3. `frontend/lib/router/app_router.dart` (310 lines, NO Logger)

Add `Logger('Router')`. Log at INFO when redirect function bounces a user:

| Location | Lines | Log message |
|----------|-------|-------------|
| Auth guard redirect | 87-88 | `'unauthenticated user redirected from {path} to /login'` |
| Permission-denied redirects | 96-122 | `'permission denied: {path} requires {permission}'` |
| Onboarding redirect | 62-69 | `'redirecting to onboarding'` |

### 4. `frontend/lib/services/api_client.dart` (149 lines, HAS Logger — gap)

| Location | Lines | Issue | Fix |
|----------|-------|-------|-----|
| `_tryRefresh()` catch | 121 | `catch (_)` silently swallows refresh failure | Change to `catch (e, st)`, log `_log.warning('token refresh failed', e, st)` |

### 5. `frontend/lib/services/secure_storage.dart` (68 lines, HAS Logger — gap)

| Location | Lines | Issue | Fix |
|----------|-------|-------|-----|
| `_clearAll()` catch | 62 | `catch (_)` silently swallows | Change to `catch (e, st)`, log `_log.warning('failed to clear storage', e, st)` |

---

## Phase 2 — Admin/Destructive Providers (5 files)

### 1. `frontend/lib/providers/event_poll_provider.dart` (105 lines, NO Logger)

Add `Logger('EventPoll')`. All methods lack try/catch — wrap each with logging:

| Method | Lines | Log message |
|--------|-------|-------------|
| `finalizeEventPoll()` | 37-50 | `'finalized poll {id} with option {optionId}'` |
| `deleteEventPoll()` | 78-87 | `'deleted poll for event {eventId}'` |
| `createEventPoll()` | 90-105 | `'created poll for event {eventId}'` |
| `addPollOption()` | 53-64 | `'added poll option to {pollId}'` |
| `deletePollOption()` | 67-75 | `'deleted poll option {id}'` |
| `submitPollVote()` | 23-34 | `'submitted vote on poll {pollId}'` |

### 2. `frontend/lib/providers/docs_provider.dart` (105 lines, NO Logger)

Add `Logger('Docs')`:

| Method | Lines | Log message |
|--------|-------|-------------|
| `createFolder()` | 17-24 | `'created folder {name}'` |
| `deleteFolder()` | 35-39 | `'deleted folder {id}'` |
| `createDocument()` | 47-56 | `'created document in folder {folderId}'` |
| `deleteDocument()` | 59-63 | `'deleted document {id}'` |
| `DocDetailNotifier.save()` | 89-99 | `'saved document {id}'` |

### 3. `frontend/lib/providers/survey_admin_provider.dart` (153 lines, NO Logger)

Add `Logger('SurveyAdmin')`:

| Method | Lines | Log message |
|--------|-------|-------------|
| `createSurvey()` | 17-39 | `'created survey {title}'` |
| `deleteSurvey()` | 47-51 | `'deleted survey {id}'` |
| `addQuestion()` | 80-97 | `'added question to survey {id}'` |
| `deleteQuestion()` | 119-125 | `'deleted question {id}'` |
| `updateQuestion()` | 99-117 | `'updated question {id}'` |
| `reorder()` | 127-134 | `'reordered questions for survey {id}'` |

### 4. `frontend/lib/providers/whatsapp_config_provider.dart` (60 lines, NO Logger)

Add `Logger('WhatsAppConfig')`:

| Method | Lines | Log message |
|--------|-------|-------------|
| `save()` | 30-47 | `'saved whatsapp config'` (do NOT log secret values) |

### 5. `frontend/lib/providers/join_form_admin_provider.dart` (80 lines, NO Logger)

Add `Logger('JoinFormAdmin')`:

| Method | Lines | Log message |
|--------|-------|-------------|
| `addQuestion()` | 18-36 | `'added join form question'` |
| `updateQuestion()` | 38-57 | `'updated join form question {id}'` |
| `deleteQuestion()` | 59-64 | `'deleted join form question {id}'` |
| `reorder()` | 66-74 | `'reordered join form questions'` |

---

## Phase 3 — Content & Config Providers (5 files)

### 1. `frontend/lib/providers/home_provider.dart` (62 lines, NO Logger)

Add `Logger('HomePage')`:

| Method | Lines | Log message |
|--------|-------|-------------|
| `saveContent()` | 32-39 | `'saved home content'` |
| `saveJoinContent()` | 41-48 | `'saved join content'` |
| `saveDonateUrl()` | 50-57 | `'saved donate URL'` |

### 2. `frontend/lib/providers/guidelines_provider.dart` (46 lines, NO Logger)

Add `Logger('Guidelines')`:

| Method | Lines | Log message |
|--------|-------|-------------|
| `saveContent()` | 29-40 | `'saved guidelines content'` |

### 3. `frontend/lib/providers/faq_provider.dart` (36 lines, NO Logger)

Add `Logger('FAQ')`:

| Method | Lines | Log message |
|--------|-------|-------------|
| `saveContent()` | 24-31 | `'saved FAQ content'` |

### 4. `frontend/lib/providers/editable_page_provider.dart` (64 lines, NO Logger)

Add `Logger('EditablePage')`:

| Method | Lines | Log message |
|--------|-------|-------------|
| `saveContent()` | 38-46 | `'saved page {slug} content'` |
| `saveVisibility()` | 48-57 | `'changed page {slug} visibility to {visibility}'` |

### 5. `frontend/lib/providers/calendar_provider.dart` (18 lines, NO Logger)

Add `Logger('Calendar')`:

| Method | Lines | Log message |
|--------|-------|-------------|
| `generateCalendarToken()` | 12-18 | `'generated calendar subscription token'` |

---

## Phase 4 — Auth & Join Screens (5 files)

### 1. `frontend/lib/screens/auth/login_screen.dart` (416 lines)

Add `Logger('LoginScreen')`:

| Location | Lines | Fix |
|----------|-------|-----|
| Phone check catch | 66 | Log `'phone check failed'` at WARNING |
| Login catch | 105 | Log `'login failed for {phone}'` at WARNING |
| Successful login | ~100 | Log `'login succeeded'` at INFO |

### 2. `frontend/lib/screens/auth/magic_login_screen.dart` (69 lines)

Add `Logger('MagicLogin')`:

| Location | Lines | Fix |
|----------|-------|-----|
| `catch (_)` | 28 | Change to `catch (e, st)`, log `'magic link login failed'` at WARNING |
| Success | ~25 | Log `'magic link login succeeded'` at INFO |

### 3. `frontend/lib/screens/auth/new_password_screen.dart` (153 lines)

Add `Logger('NewPassword')`:

| Location | Lines | Fix |
|----------|-------|-----|
| Catch block | 40 | Log `'password set failed'` at WARNING |
| Success | ~38 | Log `'password set succeeded'` at INFO |

### 4. `frontend/lib/screens/auth/onboarding_screen.dart` (195 lines)

Add `Logger('Onboarding')`:

| Location | Lines | Fix |
|----------|-------|-----|
| Catch block | 55 | Log `'onboarding failed'` at WARNING |
| Success | ~53 | Log `'onboarding completed'` at INFO |

### 5. `frontend/lib/screens/join_requests_screen.dart` (308 lines)

Add `Logger('JoinRequests')`:

| Location | Lines | Fix |
|----------|-------|-----|
| Approve/reject catch | 51 | Log `'failed to {action} join request {id}'` at WARNING |
| Approve/reject success | ~49 | Log `'{action} join request {id}'` at INFO |

---

## Phase 5 — Member Admin Screens (4 files)

### 1. `frontend/lib/screens/members/member_card.dart` (410 lines)

Add `Logger('MemberCard')`. Fix 5 catch blocks:

| Location | Lines | Fix |
|----------|-------|-----|
| Edit roles catch | 246 | Log `'failed to update roles for {userId}'` |
| Generate magic link catch | 271 | Log `'failed to generate magic link for {userId}'` |
| Reset password catch | 285 | Log `'failed to reset password for {userId}'` |
| Toggle pause catch | 327 | Log `'failed to toggle pause for {userId}'` |
| Delete member catch | 365 | Log `'failed to delete member {userId}'` |

Also log success for each operation at INFO.

### 2. `frontend/lib/screens/members/members_tab.dart` (254 lines)

Add `Logger('MembersTab')`:

| Location | Lines | Fix |
|----------|-------|-----|
| Add member catch | 227 | Log `'failed to add member'` |
| Add member success | ~225 | Log `'added member {phone}'` |

### 3. `frontend/lib/screens/members/add_member_dialog.dart` (331 lines)

Add `Logger('AddMember')`:

| Location | Lines | Fix |
|----------|-------|-----|
| Add member catch | 155 | Log `'failed to add member'` |

### 4. `frontend/lib/screens/members/roles_tab.dart` (260 lines)

Add `Logger('RolesTab')`:

| Location | Lines | Fix |
|----------|-------|-----|
| Create role catch | 74 | Log `'failed to create role'` |
| Edit role catch | 190 | Log `'failed to update role {id}'` |
| Delete role catch | 230 | Log `'failed to delete role {id}'` |

---

## Phase 6 — Calendar & Event Screens (5 files)

### 1. `frontend/lib/screens/calendar_screen.dart` (265 lines)

Add `Logger('CalendarScreen')`:

| Location | Lines | Fix |
|----------|-------|-----|
| Event creation catch | 95 | Log `'failed to create event'` (error `e` is currently unused) |
| Event creation success | ~93 | Log `'created event {title}'` |

### 2. `frontend/lib/screens/calendar/rsvp_section.dart` (297 lines)

Add `Logger('RSVP')`:

| Location | Lines | Fix |
|----------|-------|-----|
| RSVP set catch | 32 | Log `'failed to set RSVP for event {id}'` |
| RSVP remove catch | 85 | Log `'failed to remove RSVP for event {id}'` |
| RSVP success | | Log `'RSVP {status} for event {id}'` |

### 3. `frontend/lib/screens/calendar/event_login_gate.dart` (374 lines)

Add `Logger('EventLoginGate')`. Fix 4 catch blocks:

| Location | Lines | Fix |
|----------|-------|-----|
| Phone check catch | 56 | Log at WARNING |
| Inline login catch | 94 | Log `'inline login failed'` |
| Event delete catch | 187 | Log `'failed to delete event {id}'` |
| Event edit catch | 204 | Log `'failed to edit event {id}'` |

### 4. `frontend/lib/screens/event_management_row.dart` (245 lines)

Add `Logger('EventManagement')`:

| Location | Lines | Fix |
|----------|-------|-----|
| Edit event catch | 44 | Log `'failed to edit event {id}'` |
| Delete event catch | 79 | Log `'failed to delete event {id}'` |

### 5. `frontend/lib/screens/calendar/invite_modal.dart` (231 lines)

Add `Logger('InviteModal')`. Fix `catch (_)` blocks:

| Location | Lines | Fix |
|----------|-------|-----|
| Member search catch | 57 | Change `catch (_)` → `catch (e, st)`, log warning |
| Submit invites catch | 79 | Change `catch (_)` → `catch (e, st)`, log warning |

---

## Phase 7 — Survey Screens (5 files)

### 1. `frontend/lib/screens/survey_screen.dart` (221 lines)

Add `Logger('Survey')`:

| Location | Lines | Fix |
|----------|-------|-----|
| Submit response catch | 61 | Log `'failed to submit survey response'` |

### 2. `frontend/lib/screens/survey_admin_screen.dart` (349 lines)

Add `Logger('SurveyAdmin')`:

| Location | Lines | Fix |
|----------|-------|-----|
| Create survey catch | 107 | Log at WARNING |
| Toggle active catch | 129 | Log at WARNING |
| Delete survey catch | 168 | Log at WARNING |

### 3. `frontend/lib/screens/survey_builder_screen.dart` (351 lines)

Add `Logger('SurveyBuilder')`:

| Location | Lines | Fix |
|----------|-------|-----|
| 4 catch blocks | 89, 113, 150, 166 | Log each at WARNING |

### 4. `frontend/lib/screens/survey_poll_results_section.dart` (280 lines)

Add `Logger('PollResults')`:

| Location | Lines | Fix |
|----------|-------|-----|
| Finalize poll catch | 79 | Log `'failed to finalize poll'` |

### 5. `frontend/lib/screens/survey_question_form_dialog.dart` (356 lines)

Fix `catch (_)` blocks:

| Location | Lines | Fix |
|----------|-------|-----|
| DateTime parse catch | 43 | Change to `catch (e, st)`, log warning |
| DateTime parse catch | 90 | Change to `catch (e, st)`, log warning |

---

## Phase 8 — Settings, Docs, & Remaining Screens (5 files)

### 1. `frontend/lib/screens/settings_screen.dart` (301 lines)

Add `Logger('Settings')`:

| Location | Lines | Fix |
|----------|-------|-----|
| Edit name catch | 152 | Log at WARNING |
| Edit email catch | 180 | Log at WARNING |
| Change password catch | 212 | Log at WARNING |

### 2. `frontend/lib/screens/settings_dialogs.dart` (280 lines)

Add `Logger('SettingsDialog')`:

| Location | Lines | Fix |
|----------|-------|-----|
| Change password catch | 133 | Log `'password change failed'` |

### 3. `frontend/lib/screens/docs_screen.dart` (280 lines)

Add `Logger('Docs')`:

| Location | Lines | Fix |
|----------|-------|-----|
| Create folder catch | 166 | Log at WARNING |
| Create document catch | 212 | Log at WARNING |
| Third catch | 268 | Log at WARNING |

### 4. `frontend/lib/screens/docs_folder_widgets.dart` (198 lines)

Add `Logger('DocsFolders')`:

| Location | Lines | Fix |
|----------|-------|-----|
| Delete document catch | 141 | Log at WARNING |
| Delete folder catch | 192 | Log at WARNING |

### 5. `frontend/lib/screens/whatsapp_config_screen.dart` (238 lines)

Add `Logger('WhatsAppConfig')`:

| Location | Lines | Fix |
|----------|-------|-----|
| Save config catch | 79 | Log `'failed to save whatsapp config'` (do NOT log secret values) |

---

## Phase 9 — Widgets with Swallowed Errors (5 files)

### 1. `frontend/lib/widgets/autosave_mixin.dart` (121 lines)

| Location | Lines | Fix |
|----------|-------|-----|
| `catch (_)` | 71 | Change to `catch (e, st)`, add `Logger('Autosave')`, log `'autosave failed'` at WARNING |

### 2. `frontend/lib/widgets/quill_content_editor.dart` (156 lines)

| Location | Lines | Fix |
|----------|-------|-----|
| `catch (_)` in `_buildController` | 99 | Change to `catch (e, st)`, add `Logger('QuillEditor')`, log `'failed to parse document JSON — falling back to blank'` at WARNING (data loss risk) |

### 3. `frontend/lib/widgets/editable_content_block.dart` (207 lines)

Add `Logger('EditableContent')`:

| Location | Lines | Fix |
|----------|-------|-----|
| `_save()` catch | 54 | Log `'failed to save content'` at WARNING |
| `_changeVisibility()` catch | 69 | Log `'failed to change visibility'` at WARNING |

### 4. `frontend/lib/widgets/embedded_event_poll.dart` (295 lines)

Add `Logger('EmbeddedPoll')`:

| Location | Lines | Fix |
|----------|-------|-----|
| `_submit()` catch | 71 | Log `'failed to submit poll vote'` at WARNING |

### 5. `frontend/lib/widgets/poll_option_widgets.dart` (317 lines)

Add `Logger('PollOption')`:

| Location | Lines | Fix |
|----------|-------|-----|
| `_confirm()` catch | 228 | Log `'failed to finalize poll'` at WARNING |

---

## Phase 10 — Remaining Catch-All (4 files)

### 1. `frontend/lib/screens/calendar/live_poll_editor.dart` (147 lines)

Fix `catch (_)` blocks:

| Location | Lines | Fix |
|----------|-------|-----|
| Add option catch | 41 | Change to `catch (e, st)`, log warning |
| Remove option catch | 59 | Change to `catch (e, st)`, log warning |

### 2. `frontend/lib/screens/calendar/co_host_picker.dart` (178 lines)

| Location | Lines | Fix |
|----------|-------|-----|
| `catch (_)` | 78 | Change to `catch (e, st)`, log warning |

### 3. `frontend/lib/screens/calendar/event_form_location_field.dart` (146 lines)

| Location | Lines | Fix |
|----------|-------|-----|
| `catch (_)` | 77 | Change to `catch (e, st)`, log warning |

### 4. `frontend/lib/screens/home_screen.dart` (334 lines)

Add `Logger('HomeScreen')`:

| Location | Lines | Fix |
|----------|-------|-----|
| 3 catch blocks | ~153, ~275 area | Log at WARNING |

---

## Verification

After each phase:
1. `make frontend-lint` — ensure no analysis errors
2. `make frontend-test` — ensure no test regressions
3. Spot-check in browser that affected screens still function

After all phases:
1. `make ci` — full CI check
2. Trigger a few actions in the app and verify logs appear in the debug console

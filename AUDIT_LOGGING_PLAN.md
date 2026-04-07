# Backend Audit Logging Plan

## Current State

73 API endpoints. Only 5 produce any application-level logs. No audit trail model. `RequestLoggingMiddleware` captures method/path/status/duration but not user identity.

Existing infrastructure is solid: `JsonFormatter` for production, `SensitiveDataFilter` redacts phone/token/password, logger namespace `pda.*` at INFO level.

---

## Log Format

Every audit log uses structured `extra` fields via Python logging:

| Field | Type | Description |
|-------|------|-------------|
| `audit` | `bool` | Always `True` — filterable marker |
| `action` | `str` | Verb (e.g. `login_success`, `user_deleted`) |
| `actor_id` | `str` | UUID of acting user, or `"anonymous"` |
| `actor_name` | `str` | Display name of actor |
| `target_type` | `str` | Object type (e.g. `user`, `event`, `role`) |
| `target_id` | `str` | UUID of affected object |
| `details` | `dict` | Context-specific data |
| `ip_address` | `str` | Client IP |

---

## Implementation Approach

1. **New file `backend/config/audit.py`** — helper function `audit_log()` that wraps `logging.getLogger("pda.audit")` with the structured fields above
2. **New logger `pda.audit`** — inherits from `pda` parent (INFO level, console handler). No config change needed unless separate routing is desired
3. **Centralized permission check helper** — replaces repeated `if not request.auth.has_permission(...)` blocks, logs `permission_denied` in one place
4. **No DB model yet** — structured JSON logs to Railway are sufficient. Revisit if in-app audit trail UI is needed
5. **Middleware reorder** — move `RequestLoggingMiddleware` after `AuthenticationMiddleware` to capture user identity in request logs

---

## Endpoints by File

### `backend/users/_auth.py` — P0 (security-critical)

Existing logging: login failure warning (line ~47), refresh error (line ~84).

| Endpoint | Action | Level | What to Log |
|----------|--------|-------|-------------|
| `login` (success) | `login_success` | INFO | actor, ip |
| `login` (paused user) | `login_paused` | WARNING | actor_id, ip |
| `magic_login` (success) | `magic_login_success` | INFO | actor, token_id |
| `magic_login` (invalid/expired/used) | `magic_login_failure` | WARNING | reason, ip |
| `magic_login` (paused) | `magic_login_paused` | WARNING | actor_id |
| `complete_onboarding` | `onboarding_completed` | INFO | actor |
| `change_password` (success) | `password_changed` | INFO | actor |
| `change_password` (wrong current) | `password_change_failed` | WARNING | actor |
| `update_me` | `profile_updated` | INFO | actor, fields_changed |
| `upload_photo` / `delete_photo` | `profile_photo_*` | INFO | actor |

### `backend/users/_management.py` — P1 (admin actions)

No existing logging.

| Endpoint | Action | Level | What to Log |
|----------|--------|-------|-------------|
| `create_user` | `user_created` | INFO | actor, target user, role |
| `bulk_create_users` | `users_bulk_created` | INFO | actor, count created/failed |
| `update_user` | `user_updated` | INFO | actor, target, fields + old/new values |
| `update_user` (pause toggle) | `user_paused` / `user_unpaused` | WARNING | actor, target |
| `delete_user` | `user_deleted` | WARNING | actor, target, display_name |
| `update_user_roles` | `user_roles_changed` | WARNING | actor, target, old/new role IDs |
| `generate_magic_link` | `magic_link_generated` | INFO | actor, target |
| `reset_password` | `password_reset_by_admin` | WARNING | actor, target |
| All (403) | `permission_denied` | WARNING | actor, required permission |

### `backend/users/_roles.py` — P1

No existing logging.

| Endpoint | Action | Level | What to Log |
|----------|--------|-------|-------------|
| `create_role` | `role_created` | INFO | actor, name, permissions |
| `update_role` | `role_updated` | WARNING | actor, old/new permissions, old/new name |
| `delete_role` | `role_deleted` | WARNING | actor, role name |
| All (403) | `permission_denied` | WARNING | actor, required permission |

### `backend/community/_join_requests.py` — P1

Existing: join request submission logged at INFO.

| Endpoint | Action | Level | What to Log |
|----------|--------|-------|-------------|
| `update_status` (approve) | `join_request_approved` | INFO | actor, target, user created? |
| `update_status` (reject) | `join_request_rejected` | INFO | actor, target |
| `create_question` | `join_form_question_created` | INFO | actor, question_id |
| `update_question` | `join_form_question_updated` | INFO | actor, question_id |
| `delete_question` | `join_form_question_deleted` | INFO | actor, question_id |
| `reorder_questions` | `join_form_questions_reordered` | INFO | actor |
| All (403) | `permission_denied` | WARNING | actor |

### `backend/community/_guidelines.py` — P1

| Endpoint | Action | Level | What to Log |
|----------|--------|-------|-------------|
| `update_guidelines` | `guidelines_updated` | INFO | actor, content_length |
| `update_faq` | `faq_updated` | INFO | actor, content_length |

### `backend/community/_home.py` — P1

| Endpoint | Action | Level | What to Log |
|----------|--------|-------|-------------|
| `update_home` | `homepage_updated` | INFO | actor, fields_changed |

### `backend/community/_pages.py` — P1

| Endpoint | Action | Level | What to Log |
|----------|--------|-------|-------------|
| `update_page` | `page_updated` | INFO | actor, slug, fields_changed |

### `backend/community/_whatsapp.py` — P1

| Endpoint | Action | Level | What to Log |
|----------|--------|-------|-------------|
| `update_config` | `whatsapp_config_updated` | WARNING | actor, fields_changed (never log bot_secret value) |

### `backend/community/_surveys.py` — P1/P2

| Endpoint | Action | Level | What to Log |
|----------|--------|-------|-------------|
| `create_survey` | `survey_created` | INFO | actor, title, slug |
| `update_survey` | `survey_updated` | INFO | actor, fields_changed |
| `delete_survey` | `survey_deleted` | WARNING | actor, title |
| `create/update/delete_question` | `survey_question_*` | INFO | actor, question_id |
| `reorder_questions` | `survey_questions_reordered` | INFO | actor |
| `finalize_poll` | `survey_poll_finalized` | INFO | actor, winning_datetime |
| `submit_response` | `survey_response_submitted` | INFO | actor or anonymous |

### `backend/community/_events.py` — P2

| Endpoint | Action | Level | What to Log |
|----------|--------|-------|-------------|
| `create_event` | `event_created` | INFO | actor, title, type, visibility |
| `update_event` | `event_updated` | INFO | actor, fields_changed |
| `delete_event` | `event_deleted` | INFO | actor, title |
| `upload/delete_photo` | `event_photo_*` | INFO | actor, event_id |
| `upsert_rsvp` | `rsvp_changed` | INFO | actor, status |
| `delete_rsvp` | `rsvp_deleted` | INFO | actor, event_id |
| All (403) | `permission_denied` | WARNING | actor, event_id |

### `backend/community/_polls.py` — P2

| Endpoint | Action | Level | What to Log |
|----------|--------|-------|-------------|
| `create_event_poll` | `poll_created` | INFO | actor, event_id |
| `finalize_event_poll` | `poll_finalized` | INFO | actor, winning_datetime |
| `delete_event_poll` | `poll_deleted` | INFO | actor, poll_id |
| `vote` | `poll_vote` | INFO | actor |
| `add/delete_option` | `poll_option_*` | INFO | actor |

### `backend/community/_docs.py` — P2

| Endpoint | Action | Level | What to Log |
|----------|--------|-------|-------------|
| `create_folder` | `doc_folder_created` | INFO | actor, name, parent_id |
| `update_folder` | `doc_folder_updated` | INFO | actor |
| `delete_folder` | `doc_folder_deleted` | INFO | actor, name |
| `create_document` | `document_created` | INFO | actor, title, folder_id |
| `update_document` | `document_updated` | INFO | actor, fields_changed |
| `delete_document` | `document_deleted` | INFO | actor, title |
| `reorder_*` | `doc_*_reordered` | INFO | actor |

### `backend/community/_calendar.py` — P2

| Endpoint | Action | Level | What to Log |
|----------|--------|-------|-------------|
| `generate_token` | `calendar_token_generated` | INFO | actor |
| `feed` (invalid token) | `calendar_feed_invalid_token` | WARNING | ip, reason |

### `backend/config/middleware.py` — P2

| Change | Description |
|--------|-------------|
| Reorder in settings | Move after `AuthenticationMiddleware` |
| Add user_id | Include `user_id` in `extra` when authenticated |

### `backend/notifications/service.py` — P3

| Function | Action | Level | What to Log |
|----------|--------|-------|-------------|
| `notify_new_event` | `whatsapp_event_notification_sent` | INFO | event_id |
| `admin_broadcast` | `whatsapp_broadcast_sent` | INFO | message_length |

### `backend/community/_feedback.py` — already logged ✓

### `backend/notifications/api.py` — P3, no logging needed (read-only)

---

## Cross-Cutting: Permission Denials

~25 inline `if not request.auth.has_permission(...)` checks return 403 silently. Replace with a centralized helper that logs `permission_denied` at WARNING with actor, endpoint, and required permission. **Priority: P0.**

---

## Implementation Phases

| Phase | Priority | Files | Log Statements |
|-------|----------|-------|----------------|
| **1 — Auth & Security** | P0 | `config/audit.py` (new), `users/_auth.py`, `config/settings.py` | ~15 |
| **2 — Admin User Mgmt** | P1 | `users/_management.py`, `users/_roles.py`, `community/_join_requests.py` | ~22 |
| **3 — Admin Content** | P1 | `community/_guidelines.py`, `community/_home.py`, `community/_pages.py`, `community/_whatsapp.py`, `community/_surveys.py` | ~18 |
| **4 — Member Content** | P2 | `community/_events.py`, `community/_polls.py`, `community/_docs.py`, `config/middleware.py` | ~22 |
| **5 — Nice-to-Have** | P3 | `community/_calendar.py`, `notifications/service.py` | ~5 |

**Total: ~82 log statements across 16 files (1 new, 15 existing), in 5 phases of ≤5 files each.**

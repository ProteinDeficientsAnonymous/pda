# Audit: Raw String Literals → Shared Enums/Constants (GH #156)

## Summary

**45 backend violations** (15 production, 30 tests) + **~109 frontend violations** across ~18 files.

Production code is clean for permission keys, RSVP status, and join request status — those violations are test-only. The worst offenders in prod are survey question type dispatching and Pydantic schema defaults.

---

## Backend

### Enum Definitions (all exist already)

| Enum | File | Values |
|------|------|--------|
| `PermissionKey` | `backend/users/permissions.py:4` | 11 keys |
| `EventType` | `backend/community/models.py:10` | `OFFICIAL`, `COMMUNITY` |
| `RSVPStatus` | `backend/community/models.py:321` | `ATTENDING`, `MAYBE`, `CANT_GO` |
| `JoinRequestStatus` | `backend/community/models.py:15` | `PENDING`, `APPROVED`, `REJECTED` |
| `SurveyVisibility` | `backend/community/models.py:223` | `PUBLIC`, `MEMBERS_ONLY` |
| `SurveyQuestionType` | `backend/community/models.py:228` | 8 types |
| `JoinFormQuestionType` | `backend/community/models.py:21` | `TEXT`, `SELECT` |

### Production Violations (`backend/community/api.py`)

| Line(s) | Raw String | Replace With |
|---------|-----------|-------------|
| 143, 169, 213 | `event_type: str = "community"` (schema defaults) | `EventType.COMMUNITY` |
| 1181 | `visibility: str = "public"` (SurveyIn) | `SurveyVisibility.PUBLIC` |
| 108 | `field_type: str = "text"` (JoinFormQuestionIn) | `JoinFormQuestionType.TEXT` |
| 526 | `if q.field_type == "select"` | `JoinFormQuestionType.SELECT` |
| 1197 | `field_type: str = "text"` (SurveyQuestionIn) | `SurveyQuestionType.TEXT` |
| 1286-1291 | `_SURVEY_VALIDATORS` dict keys: `"select"`, `"dropdown"`, `"multiselect"`, `"number"`, `"yes_no"`, `"rating"` | `SurveyQuestionType.*` |

### Test Violations

| File | Category | Count |
|------|----------|-------|
| `tests/test_api.py` | Permission keys | 3 |
| `tests/test_api.py` | Join request status | 14 |
| `tests/test_community.py` | Join request status | 3 |
| `tests/test_events.py` | RSVP status | 10 |

*(Migration files are frozen snapshots — NOT violations)*

---

## Frontend

### No constants file exists yet — need to create one

Recommended: `frontend/lib/config/constants.dart` with `abstract class` + `static const String` fields (preserves JSON compat).

### Violations by Category

**Permission keys (~36 occurrences, 10 files)**
- `user.dart:44-48` — `hasAnyAdminPermission` getter
- `app_router.dart:86-108` — route guards
- `admin_screen.dart:26-61` — admin nav tiles
- `event_detail_panel.dart:452`, `event_form_dialog.dart:493` — manage_events checks
- `members_screen.dart:34-35` — tab visibility
- `guidelines_screen.dart:18`, `home_screen.dart:20`, `faq_screen.dart:18` — edit permission checks
- `editable_content_block.dart:83` — manage_guidelines
- `role_form_dialog.dart:6-16` — `kPermissionLabels` map keys

**Event types (13 occurrences, 6 files)**
- `event.dart:38` — default value
- `event_form_dialog.dart:71,501,505` — form state
- `day_view.dart:246,258`, `week_view.dart:436,723`, `month_view.dart:484` — calendar rendering
- `event_management_screen.dart:261,275` — my events

**RSVP statuses (13 occurrences, 1 file)**
- `rsvp_section.dart:60-107` — all status comparisons and button logic

**Join request statuses (6 occurrences, 1 file)**
- `join_requests_screen.dart:43,117,124,178,179,225`

**Visibility values (9 occurrences, 4 files)**
- `survey.dart:52,67`, `editable_content_block.dart:178,180`
- `survey_admin_screen.dart:252,314,316,320`, `survey_admin_provider.dart:20`

**Field types (~30 occurrences, 6 files)**
- `survey_builder_screen.dart` — labels, icons, options config
- `survey_screen.dart:171-220` — field rendering switch
- `join_screen.dart:49,200`, `join_form_config_screen.dart`
- `join_form_admin_provider.dart:19,40`, `survey_admin_provider.dart:76,96`

**Role names (2 occurrences, 2 files)**
- `user.dart:38` — `r.name == 'admin'`
- `members_tab.dart:306` — find admin role

---

## Suggested Constants File (`frontend/lib/config/constants.dart`)

```dart
abstract class EventType {
  static const official = 'official';
  static const community = 'community';
}

abstract class RsvpStatus {
  static const attending = 'attending';
  static const maybe = 'maybe';
  static const cantGo = 'cant_go';
}

abstract class Permission {
  static const createUser = 'create_user';
  static const manageUsers = 'manage_users';
  static const manageRoles = 'manage_roles';
  static const approveJoinRequests = 'approve_join_requests';
  static const manageEvents = 'manage_events';
  static const manageGuidelines = 'manage_guidelines';
  static const manageWhatsapp = 'manage_whatsapp';
  static const editFaq = 'edit_faq';
  static const editHomepage = 'edit_homepage';
  static const editJoinQuestions = 'edit_join_questions';
  static const manageSurveys = 'manage_surveys';
}

abstract class JoinRequestStatus {
  static const pending = 'pending';
  static const approved = 'approved';
  static const rejected = 'rejected';
}

abstract class PageVisibility {
  static const public_ = 'public';
  static const membersOnly = 'members_only';
}

abstract class FieldType {
  static const text = 'text';
  static const textarea = 'textarea';
  static const select = 'select';
  static const multiselect = 'multiselect';
  static const dropdown = 'dropdown';
  static const number = 'number';
  static const yesNo = 'yes_no';
  static const rating = 'rating';
}

abstract class RoleName {
  static const admin = 'admin';
}
```

# Prefer Types Over Raw Strings

When writing new code or modifying existing code, use shared types, enums, and constants instead of raw string literals for any non-UI values.

## Backend (Python/Django)

- Use `TextChoices` enum values (e.g. `EventType.OFFICIAL`, `RSVPStatus.ATTENDING`) instead of raw strings like `"official"`, `"attending"`
- Use `PermissionKey` constants instead of raw permission strings
- Use `SurveyQuestionType`, `SurveyVisibility`, `PageVisibility`, `JoinRequestStatus` etc. from `community/models.py`
- If no shared type exists for a repeated string value, create one

## Frontend (Dart/Flutter)

- Use constants from `config/constants.dart` (e.g. `EventType.official`, `RsvpStatus.attending`) instead of inline strings like `'official'`, `'attending'`
- If a constant doesn't exist yet for a value used in comparisons or API payloads, add it to the appropriate constants class
- This does **not** apply to UI text (button labels, headings, error messages, etc.) — those stay as inline strings

# feat: pause membership (#192)

## Context

Need a way to pause a member's account. When paused, they can't log in and see a "membership paused" message. Django's `is_active=False` already prevents `authenticate()` from returning the user, but the error is generic "Invalid credentials" — no way for the user to know they're paused vs wrong password.

## Current state

- `User` inherits `is_active` from `AbstractUser` (default `True`)
- `authenticate()` returns `None` for inactive users — same as bad credentials
- `UserPatchIn` already has `is_active: bool | None` — backend can already toggle it
- No frontend UI for pausing/unpausing
- No distinct error message for paused users

## Changes

### Backend (`backend/users/api.py`)

**Login endpoint**: Before calling `authenticate()`, look up the user by phone number to check `is_active`. If the user exists but `is_active=False`, return a specific error:

```python
try:
    user_record = User.objects.get(phone_number=payload.phone_number)
    if not user_record.is_active:
        return Status(401, ErrorOut(detail="Your membership is currently paused."))
except User.DoesNotExist:
    pass
user = authenticate(...)
```

This gives a distinct message without revealing whether the account exists (the "Invalid credentials" fallback handles both no-account and wrong-password).

### Frontend — login screen (`frontend/lib/screens/auth/login_screen.dart`)

The login screen already displays error messages from the API. The "Your membership is currently paused." message will show automatically via the existing error handling. No changes needed unless we want special styling for pause messages.

### Frontend — members tab (`frontend/lib/screens/members/members_tab.dart`)

Add a "pause" / "unpause" button to each `MemberCard`:
- Show a pause icon button (or toggle) next to existing action buttons
- When paused: show a visual indicator (e.g. dimmed card, "paused" badge)
- Calls `PATCH /auth/users/{id}/` with `{ "is_active": false/true }`

### Frontend — User model (`frontend/lib/models/user.dart`)

Add `@Default(true) bool isActive` to the Freezed User model + codegen. This is already returned from `UserOut` via Django's built-in field.

Wait — check if `UserOut` includes `is_active`:

## Verified

- `UserOut` does NOT include `is_active` — need to add it + `from_user`
- `list_users` returns all users (no `is_active` filter) — admins see paused members ✓

## Files to modify

- `backend/users/api.py` — login check + ensure UserOut includes is_active
- `frontend/lib/models/user.dart` — add isActive field
- `frontend/lib/screens/members/members_tab.dart` — pause/unpause button + visual indicator

## Verification

1. Pause a member via admin → they see "membership paused" on login
2. Unpause → they can log in again
3. Paused members show as paused in the member list

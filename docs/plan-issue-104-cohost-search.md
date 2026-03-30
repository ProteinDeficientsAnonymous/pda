# Issue #104: Co-host picker — search by name or number + invite prompt

## Context

The co-host picker in the event form only says "Search by name…" but the backend **already** searches both `display_name` and `phone_number`. Users don't know they can search by number. Additionally, when a phone number isn't found (person isn't a member), there's no way to invite them. Since there's no SMS integration, we'll prompt the user to share the join link.

## Changes — single file

**`frontend/lib/screens/calendar/event_form_dialog.dart`**

### 1. Add imports
- `import 'package:flutter/services.dart';` — for `Clipboard.setData`
- `import 'package:pda/utils/snackbar.dart';` — for `showSnackBar`

### 2. Add phone number detection helper (top-level near `_CoHostResult`)
```dart
bool _looksLikePhoneNumber(String query) {
  final stripped = query.replaceAll(RegExp(r'[\s\-\(\)\+]'), '');
  return stripped.length >= 4 && RegExp(r'^\d+$').hasMatch(stripped);
}
```
Strips formatting chars, checks if remainder is 4+ digits.

### 3. Add `_hasSearched` state flag to `_CoHostPickerState`
- `false` initially and when query is cleared
- `true` after search completes (success or error)
- Distinguishes "haven't searched yet" from "searched and got no results"

### 4. Update hint text (line 717)
`'Search by name…'` → `'search by name or number…'` (lowercase per tone rules)

### 5. Add "not found" UI after results list
When `_hasSearched && !_searching && _results.isEmpty`:
- **Phone-number-like query** → invite prompt with copy-join-link button
- **Name query** → simple "no members found" text

### 6. Extract `_buildInvitePrompt` method
- Message: `'no member found — share the join link to invite them 🌱'`
- Copy button using `InkWell` + `Semantics(button: true, label: 'copy join link')` (accessibility rules)
- Copies `Uri.base.replace(path: '/join', query: '').toString()`
- Snackbar: `'join link copied ✓'`
- Reuses existing patterns from `event_detail_panel.dart` and `settings_screen.dart`

## Existing code to reuse
- `Clipboard.setData` — used in 4 places already (e.g., `settings_screen.dart`, `event_detail_panel.dart`)
- `showSnackBar()` — `frontend/lib/utils/snackbar.dart`
- `Uri.base.replace(path: '/join', query: '')` — pattern from `event_detail_panel.dart`
- Backend search endpoint unchanged — already filters on both fields

## Verification
1. `make frontend-lint` — passes
2. `make frontend-test` — passes (no existing tests for `_CoHostPicker`)
3. `make ci` — full suite passes
4. Manual: open event form → co-host picker → type a name → see results → type a phone number not in the system → see invite prompt → tap "copy join link" → verify clipboard + snackbar

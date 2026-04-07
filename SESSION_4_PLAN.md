# Session 4 — Event Form Improvements

## Context

Issue #218 cleanup, Session 4. Three subtasks: inline picker dismiss (4a), allow +1s (4c), and re-poll button after finalized poll (4d). 4b (flexible time) dropped — `datetime_tbd` + description covers it.

---

## Phase 1: Backend — +1s fields (Agent 1 — worktree)

### Model changes (`backend/community/models/event.py`)

On `Event` (after `datetime_tbd` line 34):
- `allow_plus_ones = models.BooleanField(default=False)`

On `EventRSVP` (after `status` line ~88):
- `plus_one_count = models.PositiveIntegerField(default=0)`

### Schema changes (`backend/community/_event_schemas.py`)

- `RSVPGuestOut` (line 10): add `plus_one_count: int = 0`
- `EventListOut` (line 18): add `allow_plus_ones: bool = False`
- `EventOut` (line 43): add `allow_plus_ones: bool = False`
- `RSVPIn` (line 80): add `plus_one_count: int = 0`
- `EventIn` (line 84): add `allow_plus_ones: bool = False`
- `EventPatchIn` (line 108): add `allow_plus_ones: bool | None = None`

### Endpoint changes

- `_events.py` `create_event` (line 120): add `allow_plus_ones=payload.allow_plus_ones` to `Event.objects.create()`
- `_events.py` `upsert_rsvp` (line 292): add `"plus_one_count": payload.plus_one_count` to `defaults` dict
- `_event_helpers.py` `_build_guest_list` (line 30): add `plus_one_count=r.plus_one_count` to `RSVPGuestOut`
- `_event_helpers.py` `_event_out` (line 122): add `allow_plus_ones=event.allow_plus_ones`
- `_events.py` `list_events`: add `allow_plus_ones=e.allow_plus_ones` to each `EventListOut`

### Migration

- `python manage.py makemigrations community && python manage.py migrate`

### Update endpoint

- No changes needed — `update_event` uses `setattr` loop on `model_dump(exclude_unset=True)`.

---

## Phase 2: Frontend Model + Codegen (Agent 2 — worktree)

### Event model (`frontend/lib/models/event.dart`)

On `EventGuest` (after `photoUrl` line 14):
```dart
@Default(0) int plusOneCount,
```

On `Event` (after `rsvpEnabled` line 39):
```dart
@Default(false) bool allowPlusOnes,
```

### Run codegen
```bash
cd frontend && dart run build_runner build --delete-conflicting-outputs
```

---

## Phase 3A: Form UI — 4a + 4d (Agent 3 — worktree)

Touches: `event_form_when_section.dart` only

### 4a: Dismiss inline pickers on tap outside

Wrap inline `DateTimePicker` widgets (lines 92-104 start, lines 167-179 end) in `TapRegion`. On `onTapOutside`, call `setState(() { _startPickerMode = null; _endPickerMode = null; })`.

### 4d: Re-poll button after finalized poll

In `_dateSetByPoll` branch (lines 200-224), after the "set by poll" badge, add a "re-poll members for a time" button (same outlined pill style as lines 283-314). On tap: `widget.onAddPollOption()` + `setState(() => _dateSetByPoll = false)`.

---

## Phase 3B: RSVP +1s UI — 4c (Agent 4 — worktree)

Touches: `event_form_dialog.dart`, `event_form_settings_section.dart`, `rsvp_section.dart`, `rsvp_guest_list.dart`, `guest_chip.dart`

### Event form settings

**In `event_form_dialog.dart`:**
- Add `late bool _allowPlusOnes;` (init from `e.allowPlusOnes`)
- In `_submit()`: add `'allow_plus_ones': _allowPlusOnes`
- Pass to `EventFormSettingsSection`

**In `event_form_settings_section.dart`:**
- Add `bool allowPlusOnes` and `ValueChanged<bool> onAllowPlusOnesChanged` params
- After RSVP toggle (line 71), when `rsvpEnabled` is true, show:
```dart
SwitchListTile(
  value: allowPlusOnes,
  onChanged: onAllowPlusOnesChanged,
  title: const Text('allow +1s'),
  subtitle: const Text('guests can bring additional people'),
  contentPadding: EdgeInsets.zero,
),
```

### RSVP +1 stepper (`rsvp_section.dart`)

After RSVP buttons (line 172), when `liveEvent.allowPlusOnes && myRsvp is attending or maybe`:
- Row with "bringing +1s", minus button, count, plus button
- Track `_plusOneCount` in state, init from current user's guest entry
- On change: call RSVP endpoint with `plus_one_count` in data payload
- Update `_setRsvp` to accept optional `plusOneCount` and include in POST body

### Guest list display (`rsvp_guest_list.dart`, `guest_chip.dart`)

- `GuestChip`: if `guest.plusOneCount > 0`, append "+N" badge
- RSVP summary counts (rsvp_section.dart lines 103-106): include plus ones in totals

---

## Merge Order

1. Agent 1 (backend)
2. Agent 2 (model + codegen)
3. Agent 3 (4a + 4d) and Agent 4 (4c) — minor merge conflict in `event_form_dialog.dart` `initState`/`_submit`, resolve manually

## Verification

1. `make migrate`
2. `make frontend-codegen`
3. `make ci`
4. Manual: create event with +1s, RSVP + add +1s, verify guest list; edit event with finalized poll — verify re-poll button; open inline picker, tap outside — verify dismiss

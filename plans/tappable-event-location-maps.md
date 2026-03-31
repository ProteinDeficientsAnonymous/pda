# Plan: feat(events) — open location in maps (#135)

## Context

Event locations are currently displayed as static text in the detail view. Users should be able to tap a location to open it in their maps app — Google Maps on web, native maps on iOS/Android.

## Changes

### 1. Update `launcher_stub.dart` to use `url_launcher` for native

**File:** `frontend/lib/utils/launcher_stub.dart`

Currently a no-op. Replace with a real implementation using `url_launcher`'s `launchUrl()` so that `openUrl()` works on native platforms too.

### 2. Add `geo:` scheme to web URL safelist

**File:** `frontend/lib/utils/launcher_web.dart`

Add `'geo'` to the `allowedSchemes` set so the web launcher doesn't block geo URIs (though on web we'll use the Google Maps HTTPS URL instead).

### 3. Add an `openLocationInMaps()` helper to `launcher.dart`

**File:** `frontend/lib/utils/launcher.dart` (+ web/stub variants)

Add a new exported function `openLocationInMaps(String location)` that:
- **Web:** opens `https://maps.google.com/?q=${Uri.encodeComponent(location)}` in a new tab via `web.window.open`
- **Native:** calls `launchUrl(Uri.parse('geo:0,0?q=${Uri.encodeComponent(location)}'))`

This keeps the platform-conditional logic inside the launcher files (same pattern as `openUrl`).

### 4. Make the location row tappable in `EventDetailPanel`

**File:** `frontend/lib/screens/calendar/event_detail_panel.dart`

In `_MemberSection` (~line 625), replace the plain `_DetailRow` for location with an `InkWell`-wrapped version that calls `openLocationInMaps(location)` on tap. Style it like the existing `_LinkRow` pattern (primary color, underline, `borderRadius: BorderRadius.circular(4)`). Wrap with `Semantics(button: true, label: 'Open $location in maps')`.

## Files to modify

| File | What |
|------|------|
| `frontend/lib/utils/launcher_stub.dart` | Implement `openUrl` with `url_launcher` + add `openLocationInMaps` |
| `frontend/lib/utils/launcher_web.dart` | Add `openLocationInMaps` (Google Maps URL) |
| `frontend/lib/utils/launcher.dart` | Export new function |
| `frontend/lib/screens/calendar/event_detail_panel.dart` | Wrap location row in tappable `InkWell` |

## Verification

1. `make frontend-lint` — no analysis errors
2. `make frontend-test` — existing tests pass
3. `make ci` — full check passes
4. Manual: open an event with a location on web → tapping opens Google Maps in new tab
5. Manual: on mobile → tapping opens native maps app

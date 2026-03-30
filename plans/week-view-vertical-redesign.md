# Redesign week view: transposed grid (days as rows)
**Status: implemented**

## Context

The current week view uses a horizontal grid (days as columns, events as horizontal spanning chips). This makes it hard to show event times — the chips are tiny (22px tall) and only fit a single truncated line. The user wants days on the vertical axis instead, so each day is a row with its events listed underneath, giving room to show the time on a second line.

## Approach

Rewrite `week_view.dart` to use a vertical scrollable list of day sections. Each day section has a day label header and a list of event cards underneath (similar to the day view's `_DayEventCard` but more compact — just title + time, no description/location).

### Layout

```
← Mar 23 – Mar 29, 2026 →

Mon 23
  ┌─────────────────────────┐
  │ Movie Night              │
  │ 7:00 PM – 9:00 PM       │
  └─────────────────────────┘

Tue 24
  nothing today 🌿

Wed 25
  ┌─────────────────────────┐
  │ Potluck                  │
  │ 6:30 PM                  │
  └─────────────────────────┘
  ┌─────────────────────────┐
  │ Book Club                │
  │ 8:00 PM – 9:30 PM       │
  └─────────────────────────┘
...
```

### Changes

**`frontend/lib/screens/calendar/week_view.dart`** — Full rewrite of the body:
- Keep the week navigation header (prev/next arrows + range label) as-is
- Replace the `_WeekGrid` + `_buildEventChip` + `SpanPlacement` approach with a `ListView` of 7 day sections
- Each day section: day label (e.g. "mon 24", bold + highlighted if today) + list of compact event cards
- Event card: colored left border (using `eventColors`), title on first line, time on second line
- Empty days: subtle "–" or skip entirely (keep it compact)
- Tapping an event still calls `showEventDetail`
- Tapping the day label still calls `onDayTapped` (switches to day view)
- Multi-day events appear under each day they span

**No other files need changes** — `WeekPlacementCalculator`, `SpanPlacement`, and `placement_types.dart` can remain (still used internally or by tests) but won't be imported by the new week view. The public API (`WeekView` constructor) stays the same so `calendar_screen.dart` doesn't change.

### Event card style
- Compact: ~48px tall, colored left border (4px, using `eventColors` bg color), white/surface background
- Title: 13px, bold
- Time: 12px, secondary color, formatted as "7:00 PM" or "7:00 PM – 9:00 PM"
- Multi-day events show "Mon Mar 23 – Wed Mar 25" instead of times
- Reuse `eventColors()` from `event_colors.dart` for the accent border
- Accessibility: `Semantics(button: true, label: title)` + `InkWell`

### Existing utilities to reuse
- `eventColors()` from `frontend/lib/screens/calendar/event_colors.dart`
- `showEventDetail()` from `frontend/lib/screens/calendar/event_detail_panel.dart`
- `dayContains()` from `frontend/lib/screens/calendar/placement_types.dart` — for filtering events per day
- Time formatting pattern from `day_view.dart`'s `_buildTimeRange()`

## Files to modify

- `frontend/lib/screens/calendar/week_view.dart` — rewrite body layout

## Verification

1. `make frontend-lint` — no analysis issues
2. `make frontend-test` — existing tests pass (week placement calculator tests are independent)
3. Visual: check week view shows days vertically with title + time, today highlighted, multi-day events listed under each day they span

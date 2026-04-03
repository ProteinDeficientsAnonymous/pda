# File Size Limit

Aim to keep files under ~300 lines. 500 lines is the hard max — never exceed it.

## How to Split

- **Dart/Flutter**: Extract widgets to `widgets/` or a sibling file (e.g., `event_detail_panel.dart` → `event_detail_poll.dart`, `event_detail_member_section.dart`). Extract reusable logic to `utils/` or `providers/`.
- **Python/Django**: Extract model groups, schema groups, or endpoint groups into separate `_module.py` files (e.g., `_surveys.py`, `_events.py`). Helpers go in a `utils.py` or `helpers.py` in the same package.

## What Counts

- ~300 lines is the target; files between 300–500 should be split when practical. Files over 500 must be split immediately.
- Use judgment — a 320-line file with a single clear responsibility is fine; a 250-line file with four unrelated widgets is already too big.
- Count lines in the file as-written, not including generated `.freezed.dart` / `.g.dart` files.

## When You Notice a Violation

- **Over 500 lines**: Split before or alongside your change — don't leave it for later.
- **Over 300 lines**: If you're adding code, look for a natural seam to split. If no clean split exists, it's okay to defer, but flag it.

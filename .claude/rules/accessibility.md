---
paths:
  - "frontend/**/*.dart"
  - "**/lib/**/*.dart"
  - "**/test/**/*.dart"
---

# Flutter Accessibility Standards

All interactive UI must be accessible to screen readers and keyboard navigation. Flutter's CanvasKit renderer uses a semantics overlay to generate a shadow DOM with ARIA attributes — this only works if widgets expose semantic information.

## Core Rules

### Never Use Bare GestureDetector for User-Facing Interactions

`GestureDetector` does NOT create a semantic node — screen readers skip it entirely.

| Instead of | Use |
|------------|-----|
| `GestureDetector(onTap: ...)` | `InkWell(onTap: ...)` for tappable areas |
| `GestureDetector` + `Container` | `InkWell` + `Semantics(button: true, label: '...')` |
| Icon-only `GestureDetector` | `IconButton(tooltip: '...')` |

**Exception:** Non-user-facing gesture handlers (e.g., backdrop dismiss overlays) may use `GestureDetector` since they're not interactive elements for assistive tools.

To suppress ripple when replacing GestureDetector with InkWell:
```dart
InkWell(
  splashColor: Colors.transparent,
  highlightColor: Colors.transparent,
  onTap: ...,
)
```

### All Interactive Elements Need Semantic Labels

| Widget | How to Add Label |
|--------|-----------------|
| `InkWell` wrapping custom content | Wrap with `Semantics(button: true, label: '...')` |
| `IconButton` | Set `tooltip:` parameter |
| `TextButton` / `ElevatedButton` / `FilledButton` | Implicit from child `Text` widget |
| `TextFormField` | Implicit from `decoration.labelText` |
| `ListTile` | Implicit from `title:` text |

### Drawer Must Have semanticLabel

Flutter's `Drawer` widget skips setting the semantic route label on macOS/iOS, triggering a "self-labelled route missing label" warning. Always set it explicitly:

```dart
Drawer(
  semanticLabel: 'Navigation menu',
  child: ...,
)
```

### GoRoutes Must Have Names

Every `GoRoute` must have a `name` parameter. GoRouter passes this to `MaterialPage` as the semantic route label:

```dart
GoRoute(
  path: '/calendar',
  name: 'calendar',
  builder: (_, __) => const CalendarScreen(),
)
```

### Keyboard Navigation

Forms must have explicit focus traversal order using `FocusTraversalGroup` and `NumericFocusOrder` so Tab key follows visual order.

### Semantics on Flutter Web

Do NOT call `SemanticsBinding.instance.ensureSemantics()` in `main()`. On Flutter web (CanvasKit), forcing the semantics overlay to always be active intercepts pointer/keyboard events and breaks text input. Flutter automatically activates semantics when a screen reader is detected, which is sufficient for accessibility. Use `tester.ensureSemantics()` in tests instead.

## Testing Requirements

### Every New Screen Must Have Accessibility Tests

When adding a new screen, add tests in `test/accessibility/` that verify:

1. **`labeledTapTargetGuideline`** — all tappable elements have labels (catches bare GestureDetectors and unlabeled buttons)
2. **`textContrastGuideline`** — text meets WCAG contrast requirements
3. **`androidTapTargetGuideline`** — tap targets are at least 48x48dp

```dart
testWidgets('my screen meets labeled tap target guideline', (tester) async {
  final handle = tester.ensureSemantics();
  // ... pump widget with provider overrides ...
  await expectLater(tester, meetsGuideline(labeledTapTargetGuideline));
  handle.dispose();
});
```

### GestureDetector Audit Test

`test/accessibility/gesture_detector_audit_test.dart` scans all Dart source files for `GestureDetector` usage. Any new usage must be explicitly approved in the allowlist (with a comment explaining why it's not a user-facing interaction).

## Verification

When modifying or adding interactive widgets:

- [ ] No bare `GestureDetector` for user-facing interactions
- [ ] All buttons/tappable elements have semantic labels
- [ ] Accessibility guideline tests pass
- [ ] `dart analyze` clean
- [ ] GestureDetector audit test passes

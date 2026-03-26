# Accessibility

This document covers the Flutter web frontend's accessibility implementation.

## Semantics Tree

The app enables Flutter's semantics tree at startup via `SemanticsBinding.instance.ensureSemantics()` in `main.dart`. This forces the CanvasKit renderer to generate a shadow DOM with ARIA-annotated elements, making the app accessible to:

- Screen readers (VoiceOver, NVDA, JAWS)
- Browser automation tools (Playwright, Puppeteer)
- AI assistants interacting via the browser

Without this call, Flutter only generates the semantics tree when a screen reader is detected by the platform — which excludes automation tools.

## Renderer Comparison

### CanvasKit + Semantics (default)

The default renderer. Draws to a `<canvas>` element with a parallel semantics overlay (shadow DOM with ARIA attributes).

**Pros:**
- Pixel-perfect rendering matching mobile
- Consistent typography and layout
- Better performance for complex animations
- Semantics overlay provides full ARIA tree when enabled

**Cons:**
- Larger initial download (CanvasKit WASM ~2MB)
- Semantics overlay may not cover all edge cases
- Third-party widgets (e.g., `IntlPhoneField`) may not expose full semantics

### HTML Renderer

Alternative renderer that uses native HTML/CSS elements.

**Pros:**
- Native DOM elements — inherently accessible
- Smaller initial download
- Better SEO (content in DOM)
- Browser DevTools work directly on elements

**Cons:**
- Visual differences from mobile app
- Text rendering varies across browsers
- Some Flutter features may not render identically
- Potential layout inconsistencies

### How to Test

```bash
# CanvasKit (default) — port 3000
make frontend-run

# HTML renderer — port 3001
make frontend-run-html
```

### Recommendation

**Use CanvasKit with semantics enabled** for production. The semantics overlay provides sufficient accessibility for screen readers and automation tools. The HTML renderer is available as a fallback via `make frontend-run-html` for comparison testing.

If a specific screen or widget is inaccessible via CanvasKit semantics, consider:
1. Adding explicit `Semantics` widgets to the affected elements
2. Replacing `GestureDetector` with `InkWell` (which creates semantic nodes)
3. Switching to HTML renderer only as a last resort

## Accessible Patterns Used

### Interactive Elements

All user-facing interactive elements use widgets that create semantic nodes:

| Widget | Use Case | Semantic Behavior |
|--------|----------|-------------------|
| `InkWell` | Tappable areas (calendar cells, event chips) | Creates button node with `onTap` action |
| `Semantics` | Custom labels for complex widgets | Explicit label, role, and state |
| `IconButton` with `tooltip` | Icon-only buttons | Tooltip becomes semantic label |
| `FilledButton` / `TextButton` | Standard buttons | Implicit button semantics from text |
| `TextFormField` with `labelText` | Form inputs | Label becomes semantic label |

### What to Avoid

- **`GestureDetector`** for user-facing interactions — does NOT create a semantic node
- **`Container` with `onTap`** via `GestureDetector` — invisible to assistive tools
- **`IconButton` without `tooltip`** — the icon is meaningless to screen readers

### Text Contrast

Subtitle/helper text uses `Colors.grey[700]` (not `grey[600]`) to meet WCAG AA 4.5:1 contrast ratio against the default background.

## Known Limitations

- **`IntlPhoneField`** (third-party): Internal accessibility is limited; phone number input may not be fully navigable via screen reader. Consider replacing with a custom widget if this becomes a blocker.
- **`MarkdownToolbar`** (third-party): Toolbar buttons may lack semantic labels.
- **Calendar event chips**: Small tap targets (18px height in month view) may not meet iOS tap target guidelines (44x44). They pass Android guidelines (48x48 includes padding).
- **Flutter `textContrastGuideline`**: Known false positives with Material 3 `FilledButton` tonal elevation — the test framework's pixel sampling doesn't accurately reflect rendered contrast.

## Testing

```bash
# Run all accessibility tests
cd frontend && flutter test test/accessibility/

# Tests include:
# - Semantics smoke tests (key elements in semantics tree)
# - WCAG text contrast guidelines
# - Android tap target size guidelines
# - Calendar view semantic labels
# - No bare GestureDetector audit
```

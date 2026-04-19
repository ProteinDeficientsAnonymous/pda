---
paths:
  - "**/*.css"
  - "**/*.scss"
  - "**/*.tsx"
  - "**/*.jsx"
  - "frontend/**"
---

# Color-Blind Friendly Palettes

All color palettes and color-coded UI in this project MUST be color-blind friendly.

## Rules

- **Never rely on color alone** to convey meaning — always pair with text labels, icons, or patterns.
- **Avoid red-green pairs** — they are indistinguishable for ~8% of men (deuteranopia/protanopia).
- **Use colors that differ in luminance**, not just hue — luminance differences survive all forms of color vision deficiency.
- **Test with a CVD simulator** when adding new color-coded elements (e.g., Chrome DevTools > Rendering > Emulate vision deficiencies).

## Safe Color Families

These hue families remain distinguishable across deuteranopia, protanopia, and tritanopia:

| Family | Use case | Light example | Dark example |
|--------|----------|--------------|-------------|
| Blue | Primary/official | `#D0E8FF` bg | `#1A3050` bg |
| Teal | Secondary/public | `#CCE8E4` bg | `#103028` bg |
| Warm amber | Accent/restricted | `#FFE0B2` bg | `#3D2810` bg |
| Lavender | Tertiary/special | `#E0D0F0` bg | `#201040` bg |

## Unsafe Combinations

- Red + green (classic CVD conflict)
- Orange + green (deuteranopia)
- Blue + purple without luminance difference (tritanopia)
- Any two colors that differ only in the red-green axis

## When Adding Colors

1. Pick from the safe families above, or choose colors that differ on at least two of: hue, saturation, luminance.
2. Verify the palette works under simulated deuteranopia and protanopia.
3. If more than 4 categories need color-coding, add shape/pattern/icon differentiation — don't rely on subtle color distinctions.

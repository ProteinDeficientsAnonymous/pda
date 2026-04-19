---
paths:
  - "backend/**/*.py"
  - "Makefile"
  - "pyproject.toml"
---

# Complexity Analysis

## When cognitive complexity checks fail

`make complexity` (Python cognitive complexity) is part of CI. When it fails:

1. **Never relax thresholds** (pyproject.toml, analysis_options.yaml, Makefile exit levels) without explicit user permission.
2. **Never add `# noqa: CCR001`, `# noqa: C901`, or `// ignore:` comments** without explicit user permission.
3. **Ask the user** how they want to handle violations:
   - **"Just fix them"** — refactor to reduce complexity below the threshold, using your best judgment on approach.
   - **"Give me options"** — present 2-3 concrete refactoring approaches per violation with trade-offs, then let the user choose or discuss before implementing.

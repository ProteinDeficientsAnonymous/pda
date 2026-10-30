---
paths:
  - "backend/**/*.py"
---

# Private Modules

A module whose name starts with a single `_` (e.g. `community/events/_update.py`) is private to its parent package: only modules inside that package or its subpackages may import it.

- When a module needs to be imported from outside its package, drop the underscore (rename it) instead of importing it anyway.
- New modules default to private (`_name.py`) unless something outside the package imports them.
- Tests under `backend/tests/` are exempt and may import private modules.
- Importing private *symbols* (`from x import _helper`) is not covered by this rule.
- Enforced in CI by `make check-private-modules` / `make agent-check-private-modules`.

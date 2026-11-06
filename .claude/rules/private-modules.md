---
paths:
  - "backend/**/*.py"
---

# Private Modules and Symbols

A module whose name starts with a single `_` (e.g. `community/events/_update.py`) is private to its parent package: only modules inside that package or its subpackages may import it.

- When a module needs to be imported from outside its package, drop the underscore (rename it) instead of importing it anyway.
- New modules default to private (`_name.py`) unless something outside the package imports them.
- Tests under `backend/tests/` are exempt and may import private modules.

A symbol whose name starts with a single `_` (e.g. `_release_upcoming_rsvps`) is private to the module that defines it. Once any other module imports it, tests included, it is part of that module's interface: drop the underscore. A `_module.py` already keeps its public names inside the package.

- Existing violations are grandfathered in `scripts/private_symbol_imports_baseline.txt`, one line per importing file. Never add to it; when you rename a symbol, delete its entry (the check fails on stale entries).
- Enforced in CI by `make check-private-modules` / `make agent-check-private-modules`.

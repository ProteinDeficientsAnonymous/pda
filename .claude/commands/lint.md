# Python Linter

Run the project's linting and formatting pipeline: ruff check (lint + auto-fix) → ruff format.

## Usage

```
/lint
```

## Quick Run

```bash
make lint
```

This runs `ruff check --fix` (unused imports, import sorting, pyupgrade) then `ruff format` on the entire `backend/` directory.

## Individual Tools

```bash
# Lint + auto-fix
cd backend && uv run ruff check --fix .

# Format only
cd backend && uv run ruff format .

# Check without fixing (CI mode)
cd backend && uv run ruff check . && uv run ruff format --check .

# Type check
cd backend && uv run ty check .
```

# Python Linter

Run the project's linting pipeline: autoflake (remove unused imports) → isort (sort imports) → black (format).

## Usage

```
/lint
```

## Quick Run

```bash
make lint
```

This runs `autoflake --in-place --remove-all-unused-imports --remove-unused-variables --recursive`, then `isort`, then `black` on `listings/`, `config/`, and `tests/` inside `backend/`.

## Individual Tools

```bash
# Format with black
cd backend && uv run python -m black listings/ config/ tests/

# Sort imports
cd backend && uv run python -m isort listings/ config/ tests/

# Remove unused imports
cd backend && uv run python -m autoflake --in-place --remove-all-unused-imports --remove-unused-variables --recursive listings/ config/ tests/

# Static analysis (not part of make lint, but available)
cd backend && uv run python -m flake8 listings/ config/ tests/
cd backend && uv run python -m mypy listings/ config/
```

## Full CI Check

```bash
make ci    # lint → check → test → frontend-test
```

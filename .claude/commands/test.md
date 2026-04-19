# Test Runner

Run the Vedgy test suite with pytest.

## Usage

```
/test
```

## Quick Run

```bash
make test    # runs: cd backend && uv run python -m pytest tests/ -v
```

## Targeted Tests

```bash
# Single test file
cd backend && uv run python -m pytest tests/test_views.py

# Single test function
cd backend && uv run python -m pytest tests/test_views.py::TestClassName::test_function_name

# By keyword
cd backend && uv run python -m pytest -k "listing" -v

# App-level tests
cd backend && uv run python -m pytest listings/tests/ -v
cd backend && uv run python -m pytest users/tests/ -v
```

## Configuration

Pytest config is in `pyproject.toml`:
- `DJANGO_SETTINGS_MODULE = "config.settings"`
- Uses `--reuse-db` for speed
- Requires `@pytest.mark.django_db` marker for DB access
- Shared fixtures in `backend/tests/conftest.py`

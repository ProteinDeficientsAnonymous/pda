# Explore: Investigate and speed up slow backend tests (#699) — Findings

**Date:** 2026-07-13
**Issue:** https://github.com/ProteinDeficientsAnonymous/pda/issues/699
**Branch / PR:** `auto-699-explore-slow-backend-tests` (draft PR linked below)

## The ask

The backend pytest suite is slow (measured **243s / ~4m for 1186 tests across 8 xdist workers**). The issue lists the top offenders by file:

- `test_seed_staging.py` — the three slowest tests in the whole suite (18.0s / 17.4s / 11.4s); the file re-runs the full `seed_staging` command ~11 times.
- Heavy per-test **fixture setup** (5–10s) in `test_event_capacity.py::TestWaitlistPromotion`, `test_event_stats.py`, `test_event_cohost_invites.py`, `test_event_email_blast.py`, `test_auth_update_me.py`.
- `test_users_crud.py::TestSearchUsers::test_search_limits_to_ten_results` — 8.6s inline bulk creation.

Investigate the root cause of the top offenders, propose concrete low-risk speedups, and quantify the win — keeping behavior/coverage identical.

## What we found

**The single root cause behind nearly every offender is that tests use Django's default password hasher.** There is **no `PASSWORD_HASHERS` override anywhere** in the repo (confirmed: `grep -rn PASSWORD_HASHERS backend/` returns nothing). `config/settings.py:81` defines only `AUTH_PASSWORD_VALIDATORS`; there is no test settings module and no pytest branch, so tests run under `config.settings` with the default **PBKDF2-SHA256 hasher (~600k iterations)**.

`UserManager.create_user` (`backend/users/models.py:61-66`) calls `user.set_password(password)` unconditionally, so **every `create_user(...)` in every fixture and test pays a full PBKDF2 hash**. The flagged suites are exactly the ones that create many users per test, and the "slow setup" in `--durations` is that hashing.

**Empirically verified on this worktree** (SQLite dev.db, single worker, PBKDF2 vs. injected `MD5PasswordHasher`):

| Measurement | Default PBKDF2 | Fast MD5 hasher | Speedup |
|---|---|---|---|
| `test_auth_update_me.py` (11 tests, 1 user each) | 4.96s | 1.77s | **~64%** |
| `test_seed_staging.py` — 2 slowest tests | 16.58s | 1.40s | **~92%** |

The seed_staging result is decisive: the two slowest tests in the entire suite drop from 16.58s to 1.40s **with no code change other than the hasher** — proving the cost is password hashing, not the seed data volume. `seed_staging` creates ~36 rows but **21 real password hashes per run** (13 perm users + 8 condition users via `set_password`; 4 non-members use the cheap `set_unusable_password`), and the file runs the command ~16 times across 12 DB tests → **~300 PBKDF2 hashes in one file**.

Two secondary levers exist but are far smaller than the hasher:

- **`--reuse-db` is already on** (`pyproject.toml:44` and the Makefile agent targets), so per-worker DB *creation* is already amortized. `--no-migrations` is **not** set — adding it would trim the one-time per-worker DB bootstrap that `--durations` attributes to the first test's "setup" on each xdist worker (a worker-startup artifact, not real per-test cost).
- **Fixture scope** — the flagged fixtures are all function-scoped and rebuild a constant user/event graph per test. Widening to class/module scope (or `bulk_create` / `set_unusable_password`) helps, but once the fast hasher lands, most of the win is already captured.

### Which seed_staging tests can share a pre-seeded fixture

The seed is **deterministic and idempotent** (fixed natural keys via `get_or_create`; two tests already prove re-running adds nothing). 7–8 DB tests only *read* post-seed state and could share one module-scoped seed. Five tests **cannot** and must keep seeding themselves:

- `test_seed_staging_is_idempotent` (`:162`) — self-double-seeds.
- `test_seed_staging_reset_removes_only_scoped_rows` (`:174`) — creates a real user first, needs a clean DB.
- `test_seed_staging_reset_removes_non_member_band` (`:220`) — captures pre-`--reset` PKs and asserts they change.
- `test_seed_staging_refuses_in_production` (`:188`) — asserts **zero** rows created; a pre-seeded DB would break it.
- `test_seed_staging_non_members_idempotent` (`:237`) — self-double-seeds.

## Relevant code

| Area | Location | Role |
|---|---|---|
| Missing hasher override | `backend/config/settings.py:81` | Only `AUTH_PASSWORD_VALIDATORS`; no `PASSWORD_HASHERS` → default PBKDF2 in tests |
| Per-user hash cost | `backend/users/models.py:61-66` | `create_user` → `set_password` (PBKDF2) on every user |
| pytest config | `pyproject.toml:38-52` | `-n auto --reuse-db`; no `--no-migrations`; `DJANGO_SETTINGS_MODULE = "config.settings"` |
| Agent test addopts | `Makefile:259, 265, 270` | Replaces pyproject addopts; also lacks `--no-migrations` — a global flag must land here too |
| Top offender file | `backend/tests/test_seed_staging.py:88-243` | 12 DB tests, ~16 `call_command("seed_staging")` calls |
| Seed command | `backend/community/management/commands/seed_staging.py:44-209` | Builds full dataset per call; 21 `set_password` hashes/run |
| Seed data | `backend/community/management/commands/_seed_staging_data.py:76, 167` | `STAGING_EVENTS` (11), `NON_MEMBER_SPECS` (4) |
| Permission keys | `backend/users/permissions.py:3-17` | 13 keys → 13 perm roles + 13 perm users per seed |
| Heavy setup fixtures | `test_event_capacity.py:21-92`, `test_event_stats.py:24-92`, `test_event_cohost_invites.py:27-81`, `test_event_email_blast.py:55-91`, `test_auth_update_me.py` (via `conftest.py:83-97`) | Function-scoped fixtures each hashing multiple users per test |
| Inline bulk test | `backend/tests/users/test_users_crud.py:193-202` | `range(15)` × `create_user(password="pass")` — 15 PBKDF2 hashes |
| Shared fixtures | `backend/tests/conftest.py:59-97`, `backend/tests/users/conftest.py` | Function-scoped `create_user` fixtures; autouse consent monkeypatch |

## Options

**Option A — Fast test password hasher only (recommended first).** Add `PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]` for tests. One change, zero coverage loss (no test verifies real hash strength — auth is via `RefreshToken.for_user`; seed tests only call `check_password`/`has_usable_password`, which work under MD5). Measured ~64–92% on the flagged suites. Should reclaim most of the suite-wide cost.

- *Placement:* the cleanest option, given `config.settings` has no test branch, is an autouse-or-`pytest_configure` override in `backend/tests/conftest.py` (a pytest-only hook, no prod impact), or a dedicated `settings_test.py` importing `from config.settings import *` and setting the hasher + `DJANGO_SETTINGS_MODULE`. A conftest override keeps it scoped strictly to the test run.

**Option B — A + `--no-migrations`.** Also add `--no-migrations` to `pyproject.toml:44` **and** the three Makefile agent addopts lines. Trims per-worker DB bootstrap. Low risk given `--reuse-db` is already trusted; verify no test relies on a data-migration side effect.

**Option C — A + B + targeted fixture refactors.** Additionally widen the constant fixtures to class/module scope, build `event_with_pending_invite` via the ORM instead of a round-trip through the API, `bulk_create` the multi-user fixtures, and shrink `test_search_limits_to_ten_results` to `range(11)` with `bulk_create` + `set_unusable_password`. Highest total win but more diff surface and more per-file review; largely redundant once A lands.

## Recommendation

**Ship Option A as the foundational PR** — a fast test password hasher. It is one small, low-risk change that the measurements show reclaims the overwhelming majority of the cost (the three slowest tests in the whole suite go from ~16.6s to ~1.4s), with identical coverage. It benefits the entire suite, not just the flagged files.

**Then, as a small follow-up (Option B),** add `--no-migrations` to the pytest and Makefile agent addopts to shave the per-worker bootstrap.

**Defer Option C's fixture refactors** unless a post-A re-measurement shows specific suites still hot. After A, re-run `uv run pytest backend/tests/ --durations=25` for the before/after wall-clock the acceptance criteria ask for; only the residual offenders warrant the higher-surface fixture-scope work. This keeps each PR under the 400-line gate and lands the biggest win first.

## Open questions

1. **Hasher placement — conftest override vs. `settings_test.py`?** A `conftest.py` `pytest_configure` override is the smallest diff and is strictly test-scoped; a `settings_test.py` module is more conventional/discoverable but adds a `DJANGO_SETTINGS_MODULE` switch in `pyproject.toml` and the Makefile. Recommendation leans conftest; either is safe.
2. **Which hasher — `MD5PasswordHasher` vs. `UnsaltedMD5`/a custom fast hasher?** `MD5PasswordHasher` is the standard Django test choice and is what was benchmarked. No known reason to prefer another; flagged only for confirmation.
3. **Does CI preserve `--reuse-db` across runs?** Config-wise it's on in both pyproject and the agent targets, but if the CI environment wipes the DB volume or forces `--create-db`, the reuse benefit (and the value of `--no-migrations`) changes. Not verifiable from the repo alone.
4. **Scope of the implementing PR(s).** This spec recommends A first, then B, then (maybe) C — landing as separate focused PRs. The exact split is left to the implementer, subject to the 400-line-per-PR gate.

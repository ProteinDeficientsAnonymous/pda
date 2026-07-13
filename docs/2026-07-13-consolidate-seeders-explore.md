# Explore: investigate whether local and staging seeders should be consolidated (#717) — Findings

**Date:** 2026-07-13
**Issue:** https://github.com/ProteinDeficientsAnonymous/pda/issues/717
**Branch:** auto-717-explore-seeder-consolidation

## The ask

The seed layer under `backend/community/management/commands/` has two command/data pairs:

| Command | Data module | Purpose |
|---|---|---|
| `seed.py` | `_seed_data.py` | local dev seed (`make seed`) |
| `seed_staging.py` | `_seed_staging_data.py` | staging seed (`seed_staging`, env-gated) |

The within-pair split (orchestration vs static data) is intentional and stays. The
real question is whether the **two pairs** overlap enough to consolidate behind one
command (e.g. `seed --target=local|staging`) or a shared data/helper module — rather
than maintaining two parallel code paths that can drift.

## What we found

**The two seeders share a skeleton but seed almost entirely disjoint data for
different audiences.**

### Structural overlap is real but shallow

The one genuinely duplicated piece of orchestration is `_seed_events`. The two
implementations are near-identical: both walk a `*_EVENTS` list, compute
`start`/`end` from `delta_days`/`duration_hours` off `timezone.now()`, and
`get_or_create` by `title` with the same core defaults
(`seed.py:128-152` vs `seed_staging.py:154-173`). Local additionally sets
`rsvp_enabled`, `allow_plus_ones`, `max_attendees`; staging omits those. Beyond
that, both share only the generic `get_or_create` user/role idiom and a shared test
`PASSWORD` constant — each defined separately in its own data module
(`_seed_data.py:13` = `"testpass123"` vs `_seed_staging_data.py:7` = `"testPassword1@"`).

### The seeded data domains barely intersect

- **`seed` only:** join-form questions (`seed.py:104-120`), event tags
  (`seed.py:122-126`), RSVPs across all statuses incl. waitlist/attendance
  (`seed.py:154-182`), join requests with approve/reject metadata
  (`seed.py:184-211`), and content singletons — HomePage / Guidelines / FAQ
  (`seed.py:213-216`).
- **`seed_staging` only:** one `perm: <key>` role **per `PermissionKey`** value with
  drift-correction (`seed_staging.py:72-85`), one member user per permission
  (`seed_staging.py:87-109`), an 8-way onboarding condition-matrix of users
  (`seed_staging.py:111-152`), and a non-member RSVP band with token-issued manage
  links (`seed_staging.py:175-207`, added by #711).

There is no overlap in users (disjoint phone blocks — local `+1702555000x`, staging
`+170255501xx`/`502xx`/`503xx`, asserted disjoint at `test_seed_staging.py:43-47`),
roles, join requests, or content pages.

### Safety posture differs sharply

`seed_staging.py` is env-gated, transaction-wrapped, and resettable; `seed.py` is
none of these.

- **Env gate:** `seed_staging.py:44-50` reads `RAILWAY_ENVIRONMENT_NAME` and raises
  `CommandError` unless `is_seed_allowed(env_name, force)` passes
  (`_seed_staging_data.py:69-73`: allow unset/`"staging"`, else require `--force`).
  It deliberately does **not** use `settings.IS_PRODUCTION`
  (`config/settings.py:12`), which keys off `RAILWAY_ENVIRONMENT` and cannot
  distinguish staging from prod. `seed.py` has **no** gate at all.
- **Transaction:** `seed_staging.py:52` wraps all seeding in `transaction.atomic()`;
  `seed.py:41-49` does not (partial failure leaves partial data).
- **Reset:** `seed_staging.py` has `--reset` (`_reset`, `:63-70`) scoped precisely to
  its own rows (`[staging] ` titles, `+170255501/02/03` phones, `perm: ` roles);
  `seed.py` has no reset and is purely additive.

### Downstream consumers are also disjoint

- `backend/tests/test_seed.py` (7 tests) hard-codes the local shape: 4 events, 8
  join requests, 5 `+1702555` users, `max_attendees=3`, past-event attendance.
- `backend/tests/test_seed_staging.py` (~20 tests) asserts enum-driven per-permission
  counts, the 8-combo matrix, `--reset` scoping, production refusal
  (`test_seed_staging.py:188-194`), and the non-member/token band.
- Invocation sites differ: `seed` is wired into `Makefile:136-137`,
  `scripts/dev_sqlite_db.sh:47`, `scripts/dev_pg_db.sh:131`; `seed_staging` has **no**
  Makefile target and **no** CI/entrypoint call — it is a documented on-demand
  Railway one-off only (`CLAUDE.md:34-35`).

### Documented intent: the separation is deliberate

The design spec (`docs/superpowers/specs/2026-07-09-seed-staging-design.md`, now
gitignored — recoverable from git history) states the staging command is
*"separate from the existing `seed` command so `make seed` never emits demo
accounts."* The per-permission fixtures are enum-driven "so 'every grantable
permission is represented' holds by construction." That guarantee — local dev never
gets the staging demo bands, and staging fixtures are exhaustive by construction — is
the core reason the two exist.

### Two incidental maintenance gaps surfaced

1. `scripts/list_affected_tests.py:66` maps `tests/test_seed.py` into the community
   bundle but **omits `tests/test_seed_staging.py`** — staging-seeder-only changes may
   not trigger their own tests via the affected-tests selector.
2. The dev-db stamp caches fingerprint only `seed.py`/`_seed_data.py`
   (`scripts/dev_sqlite_db.sh:14-16`, `scripts/dev_pg_db.sh:77-78`) — correct today
   (staging seeder isn't run locally), but any shared module would need adding here to
   avoid stale caches.

## Relevant code

| Area | Location | Role |
|---|---|---|
| Local command | `backend/community/management/commands/seed.py:41-49` | `handle()` — no gate, no transaction |
| Local data | `backend/community/management/commands/_seed_data.py:81-333` | 5 users, 4 events, 14 RSVPs, 8 join requests, 3 content pages |
| Staging command | `backend/community/management/commands/seed_staging.py:44-61` | `handle()` — env gate + `transaction.atomic` + `--reset`/`--force` |
| Staging data | `backend/community/management/commands/_seed_staging_data.py` | perm/cond/non-member helpers, 11 events, env gate `is_seed_allowed` (`:69-73`) |
| Duplicated logic | `seed.py:128-152` ↔ `seed_staging.py:154-173` | `_seed_events` — near-identical |
| Env gate | `seed_staging.py:44-50` + `_seed_staging_data.py:69-73` | `RAILWAY_ENVIRONMENT_NAME` guard |
| Local tests | `backend/tests/test_seed.py` | 7 tests, local shape |
| Staging tests | `backend/tests/test_seed_staging.py` | ~20 tests, enum/matrix/gate |
| Affected-tests gap | `scripts/list_affected_tests.py:66` | `test_seed_staging.py` missing |
| Stamp fingerprints | `scripts/dev_sqlite_db.sh:14-16`, `scripts/dev_pg_db.sh:77-78` | fingerprint local seeder only |

## Options

### A. Keep two independent pairs (status quo)
- **Pros:** Zero migration risk. Preserves the "`make seed` never emits demo
  accounts" guarantee, the env gate, disjoint phone blocks, and both test suites
  untouched. Each file already fits the ~300-line limit.
- **Cons:** `_seed_events` stays duplicated (~20 lines, two places). The deliberate
  separation isn't documented in code, so this question can be re-raised.

### B. Extract a shared helper module both import
- **Pros:** Removes the one real duplication (`_seed_events` + the `get_or_create`
  user idiom) into e.g. `_seed_shared.py`. Each command keeps its own data module,
  gate, and orchestration.
- **Cons:** Adds a third module and an import edge for ~20 lines of savings. Must
  update the two stamp-fingerprint lists so shared-module edits bust the dev-db cache.
  Modest churn, modest payoff.

### C. Unify into one command with `--target=local|staging`
- **Pros:** Single entry point.
- **Cons:** High risk, low reward. The data domains are ~90% disjoint, so the
  unified `handle()` becomes a big `if target == "staging"` fork — more complex than
  two focused commands, not less. It endangers the "`make seed` never emits demo
  accounts" guarantee (one command now capable of both) and forces the env gate to
  reason about a `--target` flag. Both test suites would need rework. Rejected.

## Recommendation

**Keep the two pairs separate (Option A), and document the separation so it isn't
re-litigated.** The evidence is decisive: the seeders share only a thin skeleton
(`_seed_events` + generic `get_or_create`) while their data, safety posture, tests,
and invocation paths are essentially disjoint. Consolidation into one command
(Option C) would add a target-fork branch and threaten the "`make seed` never emits
demo accounts" guarantee for no real simplification.

Concretely, a small follow-up PR should:

1. Add a one-line rationale comment near the top of `seed_staging.py`'s `handle()`
   (or a short "why two seeders" note in `CLAUDE.md`) so the deliberate split is
   understood — capturing: staging needs enum-driven per-permission + condition-matrix
   + non-member fixtures and an env gate that local dev deliberately must not emit.
2. **Optionally** extract only `_seed_events` into a shared helper (Option B) if the
   duplication bothers a future reader — but this is a nice-to-have, not required; the
   ~20 duplicated lines are low-risk and the two variants already diverge (local sets
   RSVP fields, staging doesn't).
3. Fix the incidental gap: add `tests/test_seed_staging.py` to the community bundle in
   `scripts/list_affected_tests.py:66` so staging-seeder changes run their own tests.
   (Independent of the consolidation decision.)

## Open questions

- **Where does this findings spec live in git?** The skill prescribes
  `docs/superpowers/specs/`, but commit `006decd` (2026-07-11) deliberately untracked
  and gitignored all of `docs/superpowers/` as "workflow design docs — not tracked."
  Committing there now requires `git add -f`, re-introducing exactly what that commit
  removed. To keep this explore PR's diff meaningful, the spec is placed at the
  tracked `docs/` root (alongside existing analysis docs like
  `docs/event-attendance-stats-plan.md`) instead. If the team prefers explore specs to
  stay untracked like the other superpowers docs, this file can be moved back under
  `docs/superpowers/specs/` and the PR closed without merge — but then explore PRs
  produce no reviewable artifact, which is worth deciding on deliberately.
- **Should `_seed_events` be extracted now or left duplicated?** Recommendation leaves
  it as-is (low-risk, already diverging), but a maintainer may prefer the shared helper
  — a judgment call, not a correctness issue.

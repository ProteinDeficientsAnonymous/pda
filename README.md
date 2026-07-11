# Protein Deficients Anonymous (PDA)

A vegan collective liberation community platform.

## Stack

- **Backend**: Django 5.2 + Django Ninja (API) + PostgreSQL
- **Frontend**: Vite + React + TypeScript
- **Deployment**: Railway
- **Auth**: JWT (admin-only user creation)

## Quick Start

```bash
cp .env.example .env
make install
make db-start
make migrate
make createsuperuser
make dev  # runs Django :8000 + Vite :3000
```

See [docs/local-environment-setup.md](docs/local-environment-setup.md) for prerequisites and first-time setup details.

## Features

- Public landing page with group info and values
- Join request form (submitted requests emailed to vetting group)
- Members-only calendar (JWT auth, admin-created accounts only)
- Django admin for managing users, join requests, and events

## Commands

See [CLAUDE.md](./CLAUDE.md) for full command reference.

## Environments

| Environment | URL | Branch | Deploys |
|-------------|-----|--------|---------|
| **Staging** | [staging-pda.up.railway.app](https://staging-pda.up.railway.app) | `main` | On push to `main` (auto) |
| **Production** | [proteindeficientsanonymous.com](https://proteindeficientsanonymous.com) | `main` | Manual via GitHub Actions |

Staging is the preview environment — merging to `main` auto-deploys staging. Verify there, then manually promote to production via the `deploy railway (production)` workflow in GitHub Actions.

Manual Railway deploys via GitHub Actions (`workflow_dispatch`) are documented in [CLAUDE.md](./CLAUDE.md) (environment section).

## Contributing

1. Branch off `main`: `git checkout main && git pull && git checkout -b your-feature`
2. Open a pull request targeting `main`
3. Verify on [staging-pda.up.railway.app](https://staging-pda.up.railway.app) after merge
4. When ready, run the `deploy railway (production)` GitHub Action to promote to production

Direct pushes to `main` are not allowed for contributors.

## releases

versioning and the changelog are automated with semantic-release. every push
to `main` runs `.github/workflows/release.yml`, which computes the next semver
version from conventional commits, updates `CHANGELOG.md`, bumps the version in
`frontend/package.json` and `pyproject.toml`, tags the release, and
publishes a github release.

**one-time setup (owner):**
1. create a `RELEASE_TOKEN` repo actions secret — a fine-grained PAT or github
   app token with `contents: write` on this repo, on an identity allowed to
   bypass `main` branch protection.
2. add that identity to the branch-protection bypass allowlist (main requires a
   PR + approval; `enforce_admins` is off).
3. push a seed tag on `main` before the first release:
   `git tag v0.1.0 && git push origin v0.1.0`
   (prevents the first changelog from spanning the entire history).

commits follow conventional commits: `feat` → minor, `fix`/`perf` → patch,
`BREAKING CHANGE` → major; `chore`/`docs`/`test`/`refactor` → no release.

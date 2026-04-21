# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project Overview

PDA (Protein Deficients Anonymous) is a vegan collective liberation community platform. The Django backend is API-only (Django Ninja). The Vite + React + TypeScript frontend (Zustand + React Router + Axios + TanStack Query) handles all UI.

**Key design decisions:**
- No user self-signup — accounts are created by admins via the members screen
- Join requests are submitted publicly and routed to a vetting group via email
- The community calendar is publicly accessible; member-only details (location, links, RSVP) are gated behind login
- New users are redirected to `/onboarding` to set display name + password on first login
- Password resets redirect to `/new-password` (password only, no display name)

## Development Commands

```bash
make install          # Install dependencies (uv sync + pnpm install)
make run              # Run Django dev server on localhost:8000
make dev              # Run Django + Vite concurrently
make db-start         # Start local PostgreSQL via Docker
make db-stop          # Stop local PostgreSQL
make migrate          # makemigrations + migrate
make seed             # Seed database with sample data (local dev)
make agent-test       # Run pytest (quiet)
make agent-test-since # Run pytest subset from git diff
make agent-lint       # Run ruff (lint + format; minimal output)
make agent-typecheck  # Run ty type checker (minimal output)
make agent-complexity # Run cognitive complexity check (minimal output)
make agent-ci         # Full pre-commit check (minimal output — prefer this in agents)
make agent-frontend-test      # Run Vitest suite (minimal output)
make agent-frontend-lint      # ESLint + Prettier check (minimal output)
make agent-frontend-typecheck # Run tsc --noEmit (plain output)
make frontend-types   # Regenerate API types from OpenAPI
make frontend-build   # Build Vite production bundle
```

Use `make test`, `make lint`, `make ci`, etc. for verbose output when debugging.

## Architecture

### Project Layout

```
backend/
├── config/       # Django settings, urls, wsgi
├── users/        # Custom User model (phone_number login, UUID PKs) — admin-only creation
├── community/    # JoinRequest, Event models + API
└── tests/        # Pytest tests

frontend/
└── src/
    ├── api/          # axios client, TanStack Query hooks, generated API types
    ├── auth/         # Zustand auth store, route guards
    ├── components/   # Reusable UI primitives (Button, Dialog, TextField, etc.)
    ├── layout/       # AppShell, BottomNav, NotificationBell
    ├── models/       # Domain types: User, Event, Notification, Permissions
    ├── router/       # React Router config, lazy-loaded routes
    └── screens/      # auth, public, admin, calendar, events, profile, settings, surveys, docs
```

### Key Models

- **User** (`users/models.py`): `AbstractUser` with phone number as `USERNAME_FIELD`, UUID PK. Created by admins only via members screen.
- **JoinRequest** (`community/models.py`): name, email, pronouns, how_they_heard, why_join, submitted_at
- **Event** (`community/models.py`): title, description, start_datetime, end_datetime, location

### API & Routes

Full API: see `/api/openapi.json` when the server is running. Run `make frontend-types` to regenerate `frontend/src/api/types.gen.ts`.

Routes: see `.claude/docs/routes.md`

## Environment

- **Dev database**: PostgreSQL via Docker (`make db-start`)
- **Prod database**: PostgreSQL via `DATABASE_URL`
- **Deployed on**: Railway (`railway.json`)
- **Manual Railway deploy (GitHub Actions):** `.github/workflows/deploy-railway.yml` — `workflow_dispatch` with choice `staging` | `production`; only `refs/heads/staging` or `refs/heads/main`. Uses dockerized CLI image (digest pinned in the workflow; bump when upgrading CLI). **Repository secrets:** `RAILWAY_TOKEN_STAGING`, `RAILWAY_TOKEN_PRODUCTION` (Railway **project tokens**, one per environment). **Repository variables:** `RAILWAY_PROJECT_ID`, `RAILWAY_SERVICE_NAME`, `RAILWAY_ENVIRONMENT_STAGING`, `RAILWAY_ENVIRONMENT_PRODUCTION`. **GitHub Environments:** `railway-staging`, `railway-production` — add required reviewers on production; allow deployment from **`staging` and `main` git branches** for `railway-production` so prod can be promoted from `staging` when needed. **Governance:** `workflow_dispatch` visibility follows GitHub repo permissions (often write+); protect workflow edits with branch protection **require code owner review** on `.github/workflows/**` plus CODEOWNERS (example: `.github/workflows/ @your-org/your-team`). Auto-deploy on merge, default-branch cutover, and GHCR image flow are **not** implemented yet (phase 1 is manual dispatch only).
- **Static files**: WhiteNoise
- **Required env vars**: `SECRET_KEY`, `DATABASE_URL`, `VETTING_EMAIL` (see `.env.example`)

## Standards

**Agents:** Run **`make agent-ci`** (or matching `make agent-*` step) before claiming work complete or committing.

References: `~/.claude/rules/standards-django-ninja.md`

### frontend text casing
- All user-facing text in the frontend app must be **lowercase only** — labels, headings, buttons, placeholders, toasts, error messages, date formatting, etc.
- Use `.toLowerCase()` on any dynamic/format-driven strings (e.g. `date-fns` output).

## Agent Directives

1. **STEP 0 RULE**: Before ANY structural refactor on a file >300 LOC, first remove all dead props, unused exports, unused imports, and debug logs. Commit this cleanup separately.

2. **FILE READ BUDGET**: Each file read is capped at 2,000 lines. For files over 500 LOC, use offset and limit parameters to read in chunks.

3. **TOOL RESULT BLINDNESS**: Tool results over 50,000 characters are silently truncated. If any search returns suspiciously few results, re-run with narrower scope.

4. **NO SEMANTIC SEARCH**: You have grep, not an AST. When renaming or changing any function/type/variable, search separately for: direct calls, type-level references, string literals, dynamic imports, re-exports, and test files/mocks.

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
make db-start         # Start local PostgreSQL via Docker
make db-stop          # Stop local PostgreSQL
make install          # Install dependencies (uv sync + pnpm install)
make run              # Run Django dev server on localhost:8000
make test             # Run pytest (verbose)
make agent-test       # Run pytest (quiet; same suite)
make lint             # Run ruff (lint + format; verbose)
make agent-lint       # Same as lint with minimal ruff output
make typecheck        # Run ty type checker
make agent-typecheck  # Same as typecheck with minimal ty output
make complexity       # Run Python cognitive complexity check
make agent-complexity # Same as complexity with minimal uv/flake8 output
make migrate          # makemigrations + migrate
make createsuperuser  # Create Django admin user
make seed             # Seed database with sample data (local dev)
make check            # Django system checks
make agent-check      # Same as check with minimal django output
make agent-ci         # Full pre-commit check (same as ci; minimal output — prefer this in agents)
make ci               # Same checks as agent-ci with default tool verbosity (local debugging)
make dev              # Run Django + Vite concurrently
```

### Frontend commands

```bash
make frontend-install    # pnpm install
make frontend-run        # Vite dev server (localhost:3000, proxies /api to 8000)
make frontend-build      # Build Vite production bundle
make frontend-lint       # ESLint + Prettier check
make agent-frontend-lint # Same as frontend-lint with minimal eslint output
make frontend-format     # Auto-format files
make frontend-test       # Run Vitest suite
make agent-frontend-test # Same as frontend-test with minimal vitest output
make frontend-typecheck  # Run tsc --noEmit
make agent-frontend-typecheck # Same as frontend-typecheck with plain tsc output
make frontend-types      # Regenerate API types from OpenAPI
```

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

### API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/auth/login/` | None | Get JWT tokens |
| POST | `/api/auth/refresh/` | None | Refresh access token |
| GET | `/api/auth/me/` | JWT | Get current user |
| POST | `/api/community/join-request/` | None | Submit join request |
| GET | `/api/community/events/` | JWT | List calendar events |

This table is a **subset**; see `/api/openapi.json` when the server is running. Run `make frontend-types` with the backend up to regenerate `frontend/src/api/types.gen.ts`.

### Routes (React Router)

| Path | Auth required | Screen |
|------|--------------|--------|
| `/` | No | Landing page |
| `/join` | No | Join request form |
| `/join/success` | No | Success confirmation |
| `/login` | No | Member login |
| `/calendar` | No (member details gated inline) | Community calendar |
| `/events/:id` | No (member details gated inline) | Event detail |
| `/onboarding` | JWT (first login) | Set display name + password |
| `/new-password` | JWT (password reset) | Set new password |
| `/guidelines` | Yes | Community guidelines |
| `/settings` | Yes | Account settings |
| `/events/mine` | Yes | My events |
| `/events/manage` | Yes + manage_events | Manage events |
| `/members` | Yes + manage_users | Members admin |
| `/join-requests` | Yes + approve_join_requests | Join requests |
| `/admin/whatsapp` | Yes + manage_whatsapp | WhatsApp config |

## Environment

- **Dev database**: PostgreSQL via Docker (`make db-start`)
- **Prod database**: PostgreSQL via `DATABASE_URL`
- **Deployed on**: Railway (`railway.json`)
- **Static files**: WhiteNoise
- **Required env vars**: `SECRET_KEY`, `DATABASE_URL`, `VETTING_EMAIL` (see `.env.example`)

## Standards

**Agents (Claude Code, Cursor):** Before claiming work complete or committing, run **`make agent-ci`** (or the matching **`make agent-*`** step). Use **`make ci`** / **`make test`** / etc. when you want default verbose tool output.

References: `~/.claude/rules/standards-django-ninja.md`

### frontend text casing
- All user-facing text in the frontend app must be **lowercase only** — labels, headings, buttons, placeholders, toasts, error messages, date formatting, etc.
- Use `.toLowerCase()` on any dynamic/format-driven strings (e.g. `date-fns` output).

# Agent Directives: Mechanical Overrides

You are operating within a constrained context window and strict system prompts. To produce production-grade code, you MUST adhere to these overrides:

## Pre-Work

1. THE "STEP 0" RULE: Dead code accelerates context compaction. Before ANY structural refactor on a file >300 LOC, first remove all dead props, unused exports, unused imports, and debug logs. Commit this cleanup separately before starting the real work.

2. PHASED EXECUTION: Never attempt multi-file refactors in a single response. Break work into explicit phases. Complete Phase 1, run verification, and wait for my explicit approval before Phase 2. Each phase must touch no more than 5 files.

## Code Quality

3. THE SENIOR DEV OVERRIDE: For architecture and design decisions — if architecture is flawed, state is duplicated, or patterns are inconsistent, propose and implement structural fixes. This does NOT override TDD's "simplest code that passes" during the Green phase — that applies at the implementation level.

## Context Management

4. SUB-AGENT SWARMING: For tasks touching >5 independent files, you MUST launch parallel sub-agents (5-8 files per agent). Each agent gets its own context window. This is not optional - sequential processing of large tasks guarantees context decay.

5. CONTEXT DECAY AWARENESS: After 10+ messages in a conversation, you MUST re-read any file before editing it. Do not trust your memory of file contents. Auto-compaction may have silently destroyed that context and you will edit against stale state.

6. FILE READ BUDGET: Each file read is capped at 2,000 lines. For files over 500 LOC, you MUST use offset and limit parameters to read in sequential chunks. Never assume you have seen a complete file from a single read.

7. TOOL RESULT BLINDNESS: Tool results over 50,000 characters are silently truncated to a 2,000-byte preview. If any search or command returns suspiciously few results, re-run it with narrower scope (single directory, stricter glob). State when you suspect truncation occurred.

## Edit Safety

8. EDIT INTEGRITY: Before EVERY file edit, re-read the file. After editing, read it again to confirm the change applied correctly. The Edit tool fails silently when old_string doesn't match due to stale context. Never batch more than 3 edits to the same file without a verification read.

9. NO SEMANTIC SEARCH: You have grep, not an AST. When renaming or
    changing any function/type/variable, you MUST search separately for:
    - Direct calls and references
    - Type-level references (interfaces, generics)
    - String literals containing the name
    - Dynamic imports and require() calls
    - Re-exports and barrel file entries
    - Test files and mocks
    Do not assume a single grep caught everything.

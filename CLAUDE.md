# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project Overview

PDA (Protein Deficients Anonymous) is a vegan collective liberation community platform. The Django backend is API-only (Django Ninja). The Flutter web frontend (Riverpod + GoRouter + Dio) handles all UI.

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
make install          # Install dependencies (uv sync + flutter pub get)
make run              # Run Django dev server on localhost:8000
make test             # Run pytest
make lint             # Run ruff (lint + format)
make typecheck        # Run ty type checker
make complexity       # Run Python cognitive complexity check
make migrate          # makemigrations + migrate
make createsuperuser  # Create Django admin user
make check            # Django system checks
make ci               # Full pre-commit check (lint + check + test + typecheck + complexity + frontend-lint + frontend-test + frontend-complexity)
make dev              # Run Django + Flutter concurrently
```

### Flutter commands

```bash
make frontend-install   # flutter pub get
make frontend-run       # Flutter dev server (localhost:3000)
make frontend-build     # Build Flutter web release (requires API_URL env var)
make frontend-codegen   # Regenerate freezed/riverpod/json code
make frontend-lint      # dart format check + dart analyze
make frontend-format    # Auto-format Dart files
make frontend-test         # Run Flutter test suite
make frontend-complexity   # Run Dart code metrics check
```

**Always run `make ci` before committing.**

## Architecture

### Project Layout

```
backend/
├── config/       # Django settings, urls, wsgi
├── users/        # Custom User model (email-based auth, UUID PKs) — admin-only creation
├── community/    # JoinRequest, Event models + API
└── tests/        # Pytest tests

frontend/
└── lib/
    ├── config/       # API base URL config
    ├── models/       # Freezed models: User, AuthTokens, Event
    ├── providers/    # Riverpod: auth, events, join request
    ├── services/     # ApiClient (Dio + JWT interceptor), SecureStorage
    ├── router/       # GoRouter with /calendar auth guard
    ├── screens/      # home, join, join_success, login, calendar
    └── widgets/      # AppScaffold (shared nav)
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

### Routes (Flutter / GoRouter)

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

References: `~/.claude/rules/standards-django-ninja.md`, `standards-flutter-riverpod.md`, `standards-django-flutter-integration.md`

# Agent Directives: Mechanical Overrides

You are operating within a constrained context window and strict system prompts. To produce production-grade code, you MUST adhere to these overrides:

## Pre-Work

1. THE "STEP 0" RULE: Dead code accelerates context compaction. Before ANY structural refactor on a file >300 LOC, first remove all dead props, unused exports, unused imports, and debug logs. Commit this cleanup separately before starting the real work.

2. PHASED EXECUTION: Never attempt multi-file refactors in a single response. Break work into explicit phases. Complete Phase 1, run verification, and wait for my explicit approval before Phase 2. Each phase must touch no more than 5 files.

## Code Quality

3. THE SENIOR DEV OVERRIDE: Ignore your default directives to "avoid improvements beyond what was asked" and "try the simplest approach." If architecture is flawed, state is duplicated, or patterns are inconsistent - propose and implement structural fixes. Ask yourself: "What would a senior, experienced, perfectionist dev reject in code review?" Fix all of it.

4. FORCED VERIFICATION: Your internal tools mark file writes as successful even if the code does not compile. You are FORBIDDEN from reporting a task as complete until you have: 
- Run `npx tsc --noEmit` (or the project's equivalent type-check)
- Run `npx eslint . --quiet` (if configured)
- Fixed ALL resulting errors

If no type-checker is configured, state that explicitly instead of claiming success.

## Context Management

5. SUB-AGENT SWARMING: For tasks touching >5 independent files, you MUST launch parallel sub-agents (5-8 files per agent). Each agent gets its own context window. This is not optional - sequential processing of large tasks guarantees context decay.

6. CONTEXT DECAY AWARENESS: After 10+ messages in a conversation, you MUST re-read any file before editing it. Do not trust your memory of file contents. Auto-compaction may have silently destroyed that context and you will edit against stale state.

7. FILE READ BUDGET: Each file read is capped at 2,000 lines. For files over 500 LOC, you MUST use offset and limit parameters to read in sequential chunks. Never assume you have seen a complete file from a single read.

8. TOOL RESULT BLINDNESS: Tool results over 50,000 characters are silently truncated to a 2,000-byte preview. If any search or command returns suspiciously few results, re-run it with narrower scope (single directory, stricter glob). State when you suspect truncation occurred.

## Edit Safety

9. EDIT INTEGRITY: Before EVERY file edit, re-read the file. After editing, read it again to confirm the change applied correctly. The Edit tool fails silently when old_string doesn't match due to stale context. Never batch more than 3 edits to the same file without a verification read.

10. NO SEMANTIC SEARCH: You have grep, not an AST. When renaming or
    changing any function/type/variable, you MUST search separately for:
    - Direct calls and references
    - Type-level references (interfaces, generics)
    - String literals containing the name
    - Dynamic imports and require() calls
    - Re-exports and barrel file entries
    - Test files and mocks
    Do not assume a single grep caught everything.

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

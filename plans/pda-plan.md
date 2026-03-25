# PDA — Protein Deficients Anonymous

> **Status: Initial scaffold complete.** Repo: https://github.com/leahpeker/pda

## Context

A landing page for a vegan collective liberation community called **Protein Deficients Anonymous (PDA)**. The site needs:
- A public-facing landing page with info about the group
- A join request form (submits to a vetting group — email notification initially)
- A members-only calendar page, accessible only to users with accounts
- **No self-signup** — accounts are created by admins only (via Django admin)

Stack mirrors the `vedgyproject` setup exactly: Django Ninja backend + Flutter web frontend + PostgreSQL via Docker + Railway deployment.

---

## Phase 1: Scaffold the project

Use the `django-flutter-project` skill pattern from `vedgyproject/.claude/skills/django-flutter-project/SKILL.md` as a template.

**Project name:** `pda`
**Target directory:** `/Users/leahpeker/Documents/development/pda`

### Files to generate (following vedgy skill exactly):
- `pyproject.toml` — Django, Ninja, JWT, psycopg, whitenoise, gunicorn, etc.
- `Makefile` — all standard targets
- `docker-compose.yml` — postgres:16 service, db=`pda`, user=`pda`, password=`pda`
- `Dockerfile` — multi-stage Flutter build + Django runtime
- `railway.json`
- `.env.example`
- `.gitignore`
- `CLAUDE.md` — project-specific
- `README.md`

---

## Phase 2: Django Backend

### Apps to create

#### `users` app (same as vedgy)
- `User` model: UUID PK, email-based auth (`AbstractUser`)
- **No signup endpoint** — users are created by admin only via Django admin panel
- `GET /api/auth/me/` — return current user (auth required)
- `POST /api/auth/login/` — return JWT tokens
- `POST /api/auth/refresh/` — refresh access token

`backend/users/admin.py` — register User in admin so superusers can create accounts

#### `community` app (new)
Models:
- `JoinRequest` — stores: `name`, `email`, `pronouns`, `how_they_heard`, `why_join`, `submitted_at`

Endpoints:
- `POST /api/community/join-request/` — public, no auth. Saves to DB, sends email notification to vetting group.
- `GET /api/community/events/` — **auth required**. Returns calendar events.

Model:
- `Event` — `title`, `description`, `start_datetime`, `end_datetime`, `location` (optional)

Admin:
- Register `JoinRequest` and `Event` in Django admin

#### Email notification
On join request submission, send email to a configurable `VETTING_EMAIL` env var (falls back to console backend in dev).

---

## Phase 3: Flutter Frontend

### Screens / Routes (GoRouter)

| Route | Auth Required | Description |
|-------|--------------|-------------|
| `/` | No | Landing page — about PDA, collective liberation ethos |
| `/join` | No | Join request form |
| `/join/success` | No | Confirmation page after form submit |
| `/login` | No | Email + password login |
| `/calendar` | Yes (redirect to `/login`) | Members-only calendar view |

### Key Flutter pieces
- `auth_provider.dart` — Riverpod provider, JWT login/logout/me, persists tokens via `flutter_secure_storage`
- `app_router.dart` — GoRouter with redirect guard: if unauthenticated and trying to access `/calendar`, redirect to `/login`
- `join_request_provider.dart` — Riverpod provider for form submission
- `event_provider.dart` — Riverpod provider for fetching calendar events

### Screens
- `home_screen.dart` — Landing page with group description, values, CTA to join
- `join_screen.dart` — Form: name, email, pronouns, how_they_heard, why_join
- `join_success_screen.dart` — Thank you page
- `login_screen.dart` — Email + password, JWT
- `calendar_screen.dart` — List of upcoming events (members only)

---

## Phase 4: GitHub Repo + Initial Commit

1. Initialize git in `/Users/leahpeker/Documents/development/pda`
2. Create GitHub repo: `gh repo create pda --private --source=. --remote=origin --push`
   - Confirm with user whether repo should be **public** or **private** before running
3. Initial commit: `feat: scaffold pda with Django + Flutter`
4. Collaborator: user will add manually via GitHub settings later

---

## Critical Files

| File | Purpose |
|------|---------|
| `backend/config/settings.py` | Django settings, JWT config, CORS, email |
| `backend/config/urls.py` | API routes + Flutter SPA catch-all |
| `backend/users/models.py` | Custom User (UUID, email auth) |
| `backend/users/api.py` | Login, refresh, me (no signup) |
| `backend/users/admin.py` | Admin user creation |
| `backend/community/models.py` | JoinRequest, Event |
| `backend/community/api.py` | Join request POST, events GET |
| `backend/community/admin.py` | Admin for JoinRequest + Event |
| `frontend/lib/router/app_router.dart` | Route guard for /calendar |
| `frontend/lib/providers/auth_provider.dart` | JWT auth state |
| `frontend/lib/screens/home_screen.dart` | Landing page |
| `frontend/lib/screens/join_screen.dart` | Join request form |
| `frontend/lib/screens/calendar_screen.dart` | Members-only calendar |

---

## Environment Variables (`.env.example`)

```bash
DATABASE_URL=postgresql://pda:pda@localhost:5432/pda
DEBUG=True
SECRET_KEY=
VETTING_EMAIL=         # Email address for join request notifications
EMAIL_HOST=
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
DEFAULT_FROM_EMAIL=
```

---

## Verification

1. `make db-start && make migrate` — DB starts, migrations apply cleanly
2. `make createsuperuser` — Create admin user
3. `make run` + `make frontend-run` (or `make dev`) — Both servers start
4. Visit `http://localhost:3000/` — Landing page renders
5. Submit join form — Request saved in DB, email sent (console in dev)
6. Visit `http://localhost:3000/calendar` — Redirects to `/login`
7. Login with superuser credentials — Redirects to `/calendar`, events visible
8. `make ci` — All lint + tests pass

# Django Views Generator

Create views following Vedgy patterns.

## Usage

```
/views
```

## Vedgy View Patterns

### Server-Rendered (HTMX)
- Function-based views in `backend/listings/views.py`
- Templates in `backend/templates/`
- HTMX partials prefixed with `_` (e.g., `_listings_partial.html`)
- Alpine.js for client-side interactivity
- Forms use Django ModelForms with Tailwind CSS widget classes (`backend/listings/forms.py`)

### REST API (Django Ninja)
- API views in `backend/listings/api.py`
- Mounted at `/api/` via Django Ninja router
- JWT auth via `django-ninja-jwt`
- Pydantic schemas for request/response validation

### Auth
- Rate-limited: signup 5/hr, login 10/hr (`django-ratelimit`)
- Open redirect prevention in login/signup
- `@login_required` on create/edit/dashboard views

## URL Routing

- Server-rendered routes: `backend/listings/urls.py` → included at root in `config/urls.py`
- API routes: `backend/listings/api.py` → mounted at `/api/`

## Key Routes

`/` (index), `/browse/` (HTMX filtered), `/listing/<uuid>/`, `/create/`, `/edit/<uuid>/`, `/dashboard/`, `/api/auth/`, `/api/listings/`

# Protein Deficients Anonymous (PDA)

A vegan collective liberation community platform.

## Stack

- **Backend**: Django 5.2 + Django Ninja (API) + PostgreSQL
- **Frontend**: Flutter web + Riverpod + GoRouter
- **Deployment**: Railway
- **Auth**: JWT (admin-only user creation)

## Quick Start

```bash
cp .env.example .env
make install
make db-start
make migrate
make createsuperuser
make dev  # runs Django :8000 + Flutter :3000
```

## Features

- Public landing page with group info and values
- Join request form (submitted requests emailed to vetting group)
- Members-only calendar (JWT auth, admin-created accounts only)
- Django admin for managing users, join requests, and events

## Commands

See [CLAUDE.md](./CLAUDE.md) for full command reference.

## Contributing

All changes go through `staging` before `main`.

1. Branch off `staging`: `git checkout staging && git pull && git checkout -b your-feature`
2. Open a pull request targeting `staging` (not `main`)
3. Get at least one approval before merging

Direct pushes to `staging` and `main` are not allowed for contributors.

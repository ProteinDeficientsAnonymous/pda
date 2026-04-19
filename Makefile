.PHONY: help install run test lint lint-check format typecheck lint-file typecheck-file check migrate \
        createsuperuser seed db-start db-stop ci agent-ci dev complexity \
        frontend-install frontend-run frontend-build frontend-lint \
        frontend-format frontend-test frontend-typecheck frontend-types \
        parallel-frontend parallel-agent-frontend \
        agent-lint agent-check agent-test agent-typecheck agent-complexity \
        agent-frontend-lint agent-frontend-test agent-frontend-typecheck

help:
	@echo "Backend commands:"
	@echo "  make install          Install dependencies (uv sync + pnpm install)"
	@echo "  make run              Run Django dev server (localhost:8000)"
	@echo "  make test             Run pytest suite"
	@echo "  make lint             Run ruff (lint + format)"
	@echo "  make typecheck        Run ty type checker"
	@echo "  make check            Run Django system checks"
	@echo "  make migrate          makemigrations + migrate"
	@echo "  make createsuperuser  Create Django admin user"
	@echo "  make seed             Seed database with sample data"
	@echo "  make complexity       Run Python cognitive complexity check"
	@echo "  make db-start         Start local PostgreSQL (Docker)"
	@echo "  make db-stop          Stop local PostgreSQL (Docker)"
	@echo ""
	@echo "Frontend commands:"
	@echo "  make frontend-install   pnpm install (frontend)"
	@echo "  make frontend-run        Run Vite dev server (localhost:3000, proxies /api to 8000)"
	@echo "  make frontend-build     Build Vite production bundle"
	@echo "  make frontend-lint      Run ESLint + Prettier check"
	@echo "  make frontend-format    Auto-format files"
	@echo "  make frontend-test      Run Vitest suite"
	@echo "  make frontend-typecheck Run TypeScript check"
	@echo "  make frontend-types     Generate API types from OpenAPI"
	@echo ""
	@echo "Workflow commands:"
	@echo "  make dev              Run Django + Vite concurrently (default)"
	@echo "  make ci               Run all pre-commit checks"
	@echo "  make agent-ci         Same as ci with minimal output (for agents / logs)"

# Backend + Frontend
install:
	uv sync
	cd frontend && pnpm install

run:
	cd backend && uv run uvicorn config.asgi:application --host 0.0.0.0 --port 8000 --reload

test:
	cd backend && uv run python -m pytest tests/ -v

lint:
	cd backend && uv run ruff check --fix . && uv run ruff format .

lint-check:
	cd backend && uv run ruff check . && uv run ruff format --check .

format:
	cd backend && uv run ruff format .

typecheck:
	cd backend && uv run ty check .

complexity:
	cd backend && uvx --with flake8-cognitive-complexity flake8 --max-cognitive-complexity 10 --select CCR001 .
	@violations=$$(find backend -name '*.py' -not -path '*/migrations/*' | while read f; do lines=$$(wc -l < "$$f"); if [ "$$lines" -gt 500 ]; then echo "$$f: $$lines lines"; fi; done); \
	if [ -n "$$violations" ]; then echo "Error: files exceed 500-line limit:\n$$violations"; exit 1; fi

lint-file:
	@uv run ruff check --fix "$(FILE)" && uv run ruff format "$(FILE)"

typecheck-file:
	@uv run ty check "$(FILE)"

check:
	cd backend && uv run python manage.py check

migrate:
	cd backend && uv run python manage.py makemigrations users community && uv run python manage.py migrate

createsuperuser:
	cd backend && uv run python manage.py createsuperuser

seed:
	cd backend && uv run python manage.py seed

# Database
db-start:
	docker compose up -d db

db-stop:
	docker compose down

# Frontend (Vite + React)
frontend-install:
	cd frontend && pnpm install

frontend-run:
	cd frontend && pnpm dev

frontend-build:
	cd frontend && pnpm build

frontend-lint:
	cd frontend && pnpm lint

frontend-format:
	cd frontend && pnpm format

frontend-test:
	cd frontend && pnpm test

frontend-typecheck:
	cd frontend && pnpm typecheck

frontend-types:
	cd frontend && pnpm types:api

# CI (run before every commit)
ci: lint check test typecheck complexity parallel-frontend

# ESLint, Vitest, and tsc are independent — run in parallel to cut wall-clock time.
parallel-frontend:
	$(MAKE) -j3 frontend-lint frontend-test frontend-typecheck

# CI with quiet runners (same steps as ci; still auto-fixes via ruff)
agent-lint:
	cd backend && uv run ruff check -q --fix . && uv run ruff format -q .

agent-check:
	cd backend && uv run python manage.py check --verbosity 0 --no-color

agent-test:
	cd backend && uv run python -m pytest tests/ \
		-o addopts="--strict-markers -n auto --tb=line --reuse-db" -q --disable-warnings

agent-typecheck:
	cd backend && uv run ty check -qq .

agent-complexity:
	cd backend && env UV_NO_PROGRESS=1 uvx -q --with flake8-cognitive-complexity flake8 -q \
		--max-cognitive-complexity 10 --select CCR001 .
	violations=$$(find backend -name '*.py' -not -path '*/migrations/*' | while read f; do lines=$$(wc -l < "$$f"); if [ "$$lines" -gt 500 ]; then echo "$$f: $$lines lines"; fi; done); \
	if [ -n "$$violations" ]; then echo "Error: files exceed 500-line limit:\n$$violations"; exit 1; fi

agent-frontend-lint:
	cd frontend && pnpm exec eslint . --max-warnings 0

agent-frontend-test:
	cd frontend && pnpm exec vitest run --reporter=dot --silent passed-only

agent-frontend-typecheck:
	cd frontend && pnpm exec tsc -b --noEmit --pretty false

agent-ci: agent-lint agent-check agent-test agent-typecheck agent-complexity parallel-agent-frontend

parallel-agent-frontend:
	$(MAKE) -j3 agent-frontend-lint agent-frontend-test agent-frontend-typecheck

# Dev (concurrent backend + frontend)
dev:
	./dev.sh


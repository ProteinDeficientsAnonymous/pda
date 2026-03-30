.PHONY: help install run test lint format typecheck lint-file typecheck-file check migrate \
        createsuperuser seed db-start db-stop ci dev build-dev complexity \
        frontend-install frontend-run frontend-run-html frontend-build frontend-codegen frontend-lint \
        frontend-format frontend-test frontend-fix frontend-complexity

help:
	@echo "Backend commands:"
	@echo "  make install          Install dependencies (uv sync + flutter pub get)"
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
	@echo "  make frontend-install   flutter pub get"
	@echo "  make frontend-run       Run Flutter web server (localhost:3000)"
	@echo "  make frontend-build     Build Flutter web release"
	@echo "  make frontend-codegen   Regenerate freezed/riverpod/json code"
	@echo "  make frontend-lint      Run dart format check + dart analyze"
	@echo "  make frontend-format    Auto-format Dart files"
	@echo "  make frontend-fix       Auto-apply dart fix suggestions"
	@echo "  make frontend-test         Run Flutter test suite"
	@echo "  make frontend-complexity   Run Dart code metrics check"
	@echo ""
	@echo "Workflow commands:"
	@echo "  make build-dev        Install deps, codegen, migrate, then run dev"
	@echo "  make dev              Run Django + Flutter concurrently"
	@echo "  make ci               Run all pre-commit checks (lint, check, test, typecheck, complexity, frontend-lint, frontend-test, frontend-complexity)"

# Backend
install:
	uv sync
	cd frontend && flutter pub get

run:
	cd backend && uv run python manage.py runserver 0.0.0.0:8000

test:
	cd backend && uv run python -m pytest tests/ -v

lint:
	cd backend && uv run ruff check --fix . && uv run ruff format .

format:
	cd backend && uv run ruff format .

typecheck:
	cd backend && uv run ty check .

complexity:
	cd backend && uvx --with flake8-cognitive-complexity flake8 --max-cognitive-complexity 10 --select CCR001 .

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

# Frontend
frontend-install:
	cd frontend && flutter pub get

frontend-run:
	cd frontend && flutter run -d web-server --web-port 3000 --web-hostname 0.0.0.0

frontend-run-html:
	cd frontend && flutter run -d web-server --web-port 3001 --web-hostname 0.0.0.0

frontend-build:
	cd frontend && flutter build web --dart-define=API_URL=$(API_URL)

frontend-codegen:
	cd frontend && dart run build_runner build --delete-conflicting-outputs

frontend-lint:
	cd frontend && dart format --set-exit-if-changed lib/ test/ && dart analyze

frontend-format:
	cd frontend && dart format lib/ test/

frontend-fix:
	cd frontend && dart fix --apply

frontend-test:
	cd frontend && flutter test

frontend-complexity:
	dart pub global activate dart_code_metrics 2>/dev/null; dart pub global run dart_code_metrics:metrics analyze frontend/lib/ --disable-sunset-warning --set-exit-on-violation-level=warning

# CI (run before every commit)
ci: lint check test typecheck complexity frontend-lint frontend-test frontend-complexity

# Install deps, codegen, migrate, then run dev
build-dev: install frontend-codegen migrate dev

# Dev (concurrent backend + frontend)
dev:
	make run & make frontend-run


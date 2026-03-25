.PHONY: install run test lint check migrate createsuperuser seed db-start db-stop ci dev \
        frontend-install frontend-run frontend-build frontend-codegen frontend-lint \
        frontend-format frontend-test frontend-fix

# Backend
install:
	uv sync
	cd frontend && flutter pub get

run:
	cd backend && uv run python manage.py runserver 0.0.0.0:8000

test:
	cd backend && uv run python -m pytest tests/ -v

clean:
	cd backend && uv run autoflake --remove-all-unused-imports --remove-unused-variables -r --in-place .

format:
	cd backend && uv run black .

sort-imports:
	cd backend && uv run isort .

lint: clean sort-imports format

check:
	cd backend && uv run python manage.py check

migrate:
	cd backend && uv run python manage.py makemigrations users community && uv run python manage.py migrate

createsuperuser:
	cd backend && uv run python manage.py createsuperuser

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

# CI (run before every commit)
ci: lint check test frontend-lint frontend-test

# Dev (concurrent backend + frontend)
dev:
	trap 'kill 0' SIGINT; make run & make frontend-run & wait

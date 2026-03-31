# Stage 1: Build Flutter web
FROM ghcr.io/cirruslabs/flutter:3.41.4 AS flutter-build

WORKDIR /app/frontend
COPY frontend/pubspec.yaml frontend/pubspec.lock ./
RUN flutter pub get

COPY frontend/ ./
RUN dart run build_runner build --delete-conflicting-outputs
RUN flutter build web --release --dart-define=API_URL= --no-pub --no-wasm-dry-run

# Stage 2: Python/Django runtime
FROM python:3.13-slim AS runtime

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

COPY backend/ ./backend/
COPY static/ ./static/

COPY --from=flutter-build /app/frontend/build/web/ ./backend/staticfiles/flutter/
COPY --from=flutter-build /app/frontend/build/web/index.html ./backend/templates/flutter/index.html

RUN DJANGO_SETTINGS_MODULE=config.settings \
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))") \
    uv run --no-dev python backend/manage.py collectstatic --noinput

EXPOSE ${PORT:-8000}

CMD ["sh", "-c", "cd backend && uv run python manage.py migrate && uv run gunicorn config.wsgi --bind 0.0.0.0:${PORT:-8000}"]

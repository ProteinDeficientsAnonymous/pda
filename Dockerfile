# Stage 1: Build Vite React frontend
FROM node:22-alpine AS vite-build
RUN corepack enable
WORKDIR /app/frontend-next

COPY frontend-next/package.json frontend-next/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

COPY frontend-next/ ./
RUN pnpm build

# Stage 2: Python/Django + nginx runtime
FROM python:3.13-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends nginx && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

COPY backend/ ./backend/
COPY static/ ./static/

COPY --from=vite-build /app/frontend-next/dist/ /usr/share/nginx/html/

COPY nginx.conf.template /app/nginx.conf.template

COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

RUN DJANGO_SETTINGS_MODULE=config.settings \
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))") \
    uv run --no-dev python backend/manage.py collectstatic --noinput

EXPOSE 8080

CMD ["/app/entrypoint.sh"]

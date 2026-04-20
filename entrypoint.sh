#!/usr/bin/env sh
set -e

export NGINX_PORT="${PORT:-8080}"

envsubst '${NGINX_PORT}' < /app/nginx.conf.template > /etc/nginx/sites-available/default
rm -f /etc/nginx/sites-enabled/default
ln -s /etc/nginx/sites-available/default /etc/nginx/sites-enabled/default

nginx -g 'daemon off;' &

cd backend
uv run python manage.py migrate
uv run uvicorn config.asgi:application --host 0.0.0.0 --port 8000

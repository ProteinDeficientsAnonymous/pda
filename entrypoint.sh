#!/usr/bin/env sh
set -e

export NGINX_PORT="${PORT:-8080}"

envsubst '${NGINX_PORT}' < /app/nginx.conf.template > /etc/nginx/sites-available/default
rm -f /etc/nginx/sites-enabled/default
ln -s /etc/nginx/sites-available/default /etc/nginx/sites-enabled/default

# Fail the deploy loudly on a bad config instead of a silent backgrounded death
# that leaves uvicorn up but the front door dead (→ 502 on every route).
nginx -t

# If nginx exits for any reason, take the whole container down so Railway
# restarts it and the failure is visible — don't limp on with only uvicorn.
nginx -g 'daemon off;' || kill "$$" &

cd backend
uv run --no-dev python manage.py migrate
# Table creation isn't atomic; a concurrent replica may win the race and create it first.
uv run --no-dev python manage.py createcachetable || true

# gunicorn_conf: max-requests 100 + max-age (PDA_WORKER_MAX_AGE) recycle RSS;
# graceful-timeout covers the SSE notification stream (notifications/sse.py).
if [ "${PDA_MEMORY_PROFILE:-}" = "1" ]; then
  export PYTHONTRACEMALLOC="${PYTHONTRACEMALLOC:-1}"
fi
uv run --no-dev python -m config.run_gunicorn

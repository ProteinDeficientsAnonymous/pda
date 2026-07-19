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

# Railway's private network (internal IPv6 mesh + DNS) can lag the container
# boot, so the first DB connect times out even though Postgres is up. Poll until
# reachable instead of letting a single-shot migrate kill the whole deploy.
# ponytail: fixed 60s ceiling, bump the loop count if cold starts get slower.
attempt=1
until uv run python manage.py migrate; do
  if [ "$attempt" -ge 12 ]; then
    echo "database unreachable after $attempt attempts, giving up" >&2
    exit 1
  fi
  echo "database not ready (attempt $attempt), retrying in 5s..." >&2
  attempt=$((attempt + 1))
  sleep 5
done

uv run uvicorn config.asgi:application --host 0.0.0.0 --port 8000

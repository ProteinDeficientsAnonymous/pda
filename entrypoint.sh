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
uv run python manage.py migrate
uv run python manage.py createcachetable

# --max-requests recycles each worker periodically to release memory the
# allocator holds onto but never returns to the OS (RSS grows ~200MB -> ~650MB
# over a day otherwise); jitter staggers recycles across workers. gunicorn
# keeps the listening socket open across a worker restart, so this is a
# clean respawn rather than the downtime a bare `uvicorn` restart would cause.
uv run gunicorn config.asgi:application \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --max-requests 10000 \
    --max-requests-jitter 1000

#!/usr/bin/env sh
set -e

# Daily maintenance sweeps, run by a Railway cron service (start command:
# `sh scripts/cron.sh`, schedule e.g. `0 3 * * *`). Mirrors entrypoint.sh:
# from /app, cd into backend and invoke management commands via uv.
cd backend
uv run python manage.py expire_stale_cohost_invites
uv run python manage.py purge_deleted_events

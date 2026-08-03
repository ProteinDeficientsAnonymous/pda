#!/usr/bin/env sh
set -e

cd backend
uv run python manage.py hard_delete_old_events
uv run python manage.py cleanup_notifications
uv run python manage.py purge_audit_logs

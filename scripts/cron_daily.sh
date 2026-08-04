#!/usr/bin/env sh
cd backend

status=0
uv run python manage.py hard_delete_old_events || status=1
uv run python manage.py cleanup_notifications || status=1
uv run python manage.py purge_audit_logs || status=1

exit $status

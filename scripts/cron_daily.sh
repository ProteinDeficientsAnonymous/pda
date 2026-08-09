#!/usr/bin/env sh
cd backend

status=0
timeout 300 uv run python manage.py hard_delete_old_events || status=1
timeout 300 uv run python manage.py cleanup_notifications || status=1
timeout 300 uv run python manage.py purge_audit_logs || status=1
timeout 300 uv run python manage.py send_attendance_reminders || status=1

exit $status

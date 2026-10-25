#!/usr/bin/env sh
cd backend

status=0
timeout 300 uv run --no-dev python manage.py purge_deleted_events || status=1
timeout 300 uv run --no-dev python manage.py cleanup_notifications || status=1
timeout 300 uv run --no-dev python manage.py purge_audit_logs || status=1
timeout 300 uv run --no-dev python manage.py clear_expired_cache || status=1
timeout 300 uv run --no-dev python manage.py prune_mcp_oauth || status=1
timeout 300 uv run --no-dev python manage.py send_whatsapp_join_reminders || status=1
timeout 300 uv run --no-dev python manage.py send_event_feedback_requests || status=1
timeout 300 uv run --no-dev python manage.py send_host_digests || status=1

exit $status

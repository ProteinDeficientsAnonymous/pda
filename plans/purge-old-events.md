# Plan: Purge Old Events — Soft Delete + Cron (#164)

## Context

Old events and their B2-stored photos accumulate indefinitely. Issue #164 asks for a cleanup process. User chose: **soft delete first** (archive → purge after grace period), **no pinning**, **configurable threshold**, **Railway cron service**.

## Approach: Two-Phase Cleanup

**Phase 1 — Archive**: Set `archived_at` on events older than `--days`. Archived events become invisible to all API queries via a custom default manager.

**Phase 2 — Purge**: Hard-delete archived events older than `--grace-days`, deleting B2 photos first.

---

## Step 1: Add `archived_at` field + custom manager

**File**: `backend/community/models.py`

- Add `archived_at = models.DateTimeField(null=True, blank=True)` to `Event`
- Add `ActiveEventManager` that filters `archived_at__isnull=True`
- Set `objects = ActiveEventManager()` as the default manager
- Add `all_objects = models.Manager()` for admin/management command access

This automatically filters archived events from all 13+ `Event.objects` queries in `api.py` with zero code changes.

## Step 2: Migration

- Run `make migrate` to generate the `archived_at` field migration

## Step 3: Update admin

**File**: `backend/community/admin.py` (line 45-51)

- Override `get_queryset` to use `Event.all_objects.all()`
- Add `archived_at` to `list_display`, `list_filter`, `readonly_fields`

## Step 4: `archive_old_events` management command

**File**: `backend/community/management/commands/archive_old_events.py` (new)

```
manage.py archive_old_events --days=90 [--dry-run]
```

- Query `Event.all_objects.filter(archived_at__isnull=True)` where `Coalesce(end_datetime, start_datetime) < now - days`
- Bulk update: `.update(archived_at=timezone.now())` (per Django standards — bulk, not per-object loop)
- `--dry-run` logs count + titles without updating
- Log each archived event for audit trail

## Step 5: `purge_archived_events` management command

**File**: `backend/community/management/commands/purge_archived_events.py` (new)

```
manage.py purge_archived_events --grace-days=30 [--dry-run]
```

- Query `Event.all_objects.filter(archived_at__lt=now - grace_days)`
- For each event: delete photo from B2 (`event.photo.delete(save=False)` if photo exists), then `event.delete()` — must be per-object loop because photo cleanup requires individual handling
- Uses `.iterator()` to avoid loading all into memory
- `--dry-run` logs what would be purged
- Cascade: RSVPs auto-deleted, Survey.linked_event set to NULL (preserving survey data)

## Step 6: Tests

**File**: `backend/tests/test_archive_events.py` (new)

Test cases:
- Events older than threshold get archived; newer ones don't
- `end_datetime=None` falls back to `start_datetime`
- Already-archived events preserve their `archived_at` timestamp
- `--dry-run` makes no changes
- Archived events excluded from `list_events` API (returns only active)
- Archived events return 404 from `get_event` API
- Purge deletes archived events older than grace period
- Photos are deleted from storage before model deletion
- RSVPs cascade, surveys preserved with null FK

## Step 7: Railway cron service

**File**: `scripts/cleanup_cron.sh` (new)

```bash
#!/usr/bin/env bash
set -euo pipefail
cd backend
uv run python manage.py archive_old_events --days="${ARCHIVE_DAYS:-90}"
uv run python manage.py purge_archived_events --grace-days="${PURGE_GRACE_DAYS:-30}"
```

Configure via Railway dashboard: new cron service pointing at same repo, override start command to `bash scripts/cleanup_cron.sh`, schedule `0 3 * * *` (daily 3 AM). Thresholds configurable via env vars.

## Step 8: Makefile targets

**File**: `Makefile`

```makefile
archive-events:
	cd backend && uv run python manage.py archive_old_events --days=$(DAYS)

purge-events:
	cd backend && uv run python manage.py purge_archived_events --grace-days=$(GRACE_DAYS)
```

---

## Files Summary

| File | Action |
|------|--------|
| `backend/community/models.py` | Add `archived_at`, `ActiveEventManager`, `all_objects` |
| `backend/community/admin.py` | Override queryset, add `archived_at` to display |
| `backend/community/management/commands/archive_old_events.py` | New |
| `backend/community/management/commands/purge_archived_events.py` | New |
| `backend/tests/test_archive_events.py` | New |
| `scripts/cleanup_cron.sh` | New |
| `Makefile` | Add convenience targets |

## Verification

1. `make migrate` — generates and applies `archived_at` migration
2. `make test` — all existing tests still pass (manager swap is transparent)
3. New tests pass for both commands + API filtering
4. Manual test: seed old events, run `archive_old_events --dry-run`, then without `--dry-run`, confirm they disappear from API
5. `make ci` — full check before commit

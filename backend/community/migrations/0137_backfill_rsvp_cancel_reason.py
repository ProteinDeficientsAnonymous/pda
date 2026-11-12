from datetime import timedelta

from django.db import migrations

# A release stamps cancelled_at in the same request that writes its audit row.
_WINDOW = timedelta(minutes=5)
_PAUSE_ACTIONS = ("user_attendance_paused", "user_paused")
_ARCHIVE_ACTIONS = ("user_archived", "user_self_deleted")


def _released_by(rsvps, entry):
    return rsvps.filter(
        user_id=entry.target_id,
        cancelled_at__gte=entry.created_at - _WINDOW,
        cancelled_at__lte=entry.created_at + _WINDOW,
    )


def backfill_cancel_reason(apps, schema_editor):
    EventRSVP = apps.get_model("community", "EventRSVP")
    AuditLogEntry = apps.get_model("audit", "AuditLogEntry")
    unset = EventRSVP.objects.filter(cancelled_at__isnull=False, cancel_reason__isnull=True)
    entries = AuditLogEntry.objects.filter(target_type="user").exclude(target_id="")
    for entry in entries.filter(action__in=_PAUSE_ACTIONS):
        event_ids = (entry.details or {}).get("removed_rsvp_event_ids") or []
        _released_by(unset, entry).filter(event_id__in=event_ids).update(cancel_reason="pause")
    for entry in entries.filter(action__in=_ARCHIVE_ACTIONS):
        _released_by(unset, entry).update(cancel_reason="archive")
    unset.update(cancel_reason="self")


class Migration(migrations.Migration):
    dependencies = [
        ("community", "0136_eventrsvp_cancel_reason"),
        ("audit", "0006_member_restored_email_target_type"),
    ]

    operations = [
        migrations.RunPython(backfill_cancel_reason, migrations.RunPython.noop),
    ]

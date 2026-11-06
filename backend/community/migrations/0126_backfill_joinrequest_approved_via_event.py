from datetime import timedelta

from django.db import migrations

# Check-in promotion logs attendance_marked right after stamping approved_at.
MATCH_WINDOW = timedelta(minutes=1)


def backfill_approved_via_event(apps, schema_editor):
    AuditLogEntry = apps.get_model("audit", "AuditLogEntry")
    Event = apps.get_model("community", "Event")
    JoinRequest = apps.get_model("community", "JoinRequest")

    manually_approved = set(
        AuditLogEntry.objects.filter(
            action="join_request_approved", target_type="join_request"
        ).values_list("target_id", flat=True)
    )
    candidates = JoinRequest.objects.filter(
        status="approved",
        tentative_at__isnull=False,
        approved_at__isnull=False,
        user__isnull=False,
        approved_via_event__isnull=True,
    )

    updated = []
    for jr in candidates:
        if str(jr.id) in manually_approved:
            continue
        entry = (
            AuditLogEntry.objects.filter(
                action="attendance_marked",
                target_type="event",
                details__user_id=str(jr.user_id),
                details__attendance="attended",
                created_at__gte=jr.approved_at,
                created_at__lte=jr.approved_at + MATCH_WINDOW,
            )
            .order_by("created_at")
            .first()
        )
        if entry is None or not Event.objects.filter(id=entry.target_id).exists():
            continue
        jr.approved_via_event_id = entry.target_id
        updated.append(jr)
    JoinRequest.objects.bulk_update(updated, ["approved_via_event"], batch_size=500)


class Migration(migrations.Migration):
    dependencies = [
        ("audit", "0002_alter_auditlogentry_target_type"),
        ("community", "0125_joinrequest_approved_via_event"),
    ]

    operations = [
        migrations.RunPython(backfill_approved_via_event, migrations.RunPython.noop),
    ]

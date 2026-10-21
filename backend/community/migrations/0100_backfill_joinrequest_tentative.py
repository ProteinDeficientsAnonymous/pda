from django.db import migrations

TENTATIVE_ACTION = "join_request_tentative"
JOIN_REQUEST_TARGET = "join_request"


def backfill_tentative(apps, schema_editor):
    AuditLogEntry = apps.get_model("audit", "AuditLogEntry")
    JoinRequest = apps.get_model("community", "JoinRequest")

    # Oldest first so a later re-stamp for the same request wins.
    latest = {}
    entries = AuditLogEntry.objects.filter(
        action=TENTATIVE_ACTION, target_type=JOIN_REQUEST_TARGET
    ).order_by("created_at")
    for entry in entries:
        latest[entry.target_id] = entry

    updated = []
    for jr in JoinRequest.objects.filter(id__in=list(latest), tentative_at__isnull=True):
        entry = latest[str(jr.id)]
        jr.tentative_at = entry.created_at
        jr.tentative_by_id = entry.actor_id
        updated.append(jr)
    JoinRequest.objects.bulk_update(updated, ["tentative_at", "tentative_by"], batch_size=500)


class Migration(migrations.Migration):
    dependencies = [
        ("audit", "0002_alter_auditlogentry_target_type"),
        ("community", "0099_joinrequest_tentative_at_by"),
    ]

    operations = [
        migrations.RunPython(backfill_tentative, migrations.RunPython.noop),
    ]

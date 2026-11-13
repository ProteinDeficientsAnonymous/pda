from django.db import migrations
from django.db.models import F, OuterRef, Subquery

_STAMPS = {
    "tentative": ("tentative_at", "tentative_by"),
    "approved": ("approved_at", "approved_by"),
    "rejected": ("rejected_at", "rejected_by"),
}


def backfill_status_changed(apps, schema_editor):
    JoinRequest = apps.get_model("community", "JoinRequest")
    # Only the current status's stamp counts; a pending row's stamps describe an earlier status.
    for status, (at, by) in _STAMPS.items():
        JoinRequest.objects.filter(status=status, status_changed_at__isnull=True).update(
            status_changed_at=F(at), status_changed_by=F(by)
        )


def close_archived_tentative_requests(apps, schema_editor):
    JoinRequest = apps.get_model("community", "JoinRequest")
    User = apps.get_model("users", "User")
    archived_at = User.objects.filter(pk=OuterRef("user_id")).values("archived_at")[:1]
    # An open tentative request would block an archived person from applying again.
    JoinRequest.objects.filter(status="tentative", user__archived_at__isnull=False).update(
        status="closed", status_changed_at=Subquery(archived_at), status_changed_by=None
    )


class Migration(migrations.Migration):
    dependencies = [
        ("community", "0133_joinrequest_status_changed"),
        ("users", "0059_backfill_membership_status"),
    ]

    operations = [
        migrations.RunPython(backfill_status_changed, migrations.RunPython.noop),
        migrations.RunPython(close_archived_tentative_requests, migrations.RunPython.noop),
    ]

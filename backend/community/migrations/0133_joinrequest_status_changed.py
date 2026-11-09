import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

_STAMPS = (
    ("tentative_at", "tentative_by"),
    ("approved_at", "approved_by"),
    ("rejected_at", "rejected_by"),
)


def fill_status_changed(apps, schema_editor):
    JoinRequest = apps.get_model("community", "JoinRequest")
    # A pending row was never decided or was un-rejected; its old stamps describe an earlier status.
    for jr in JoinRequest.objects.exclude(status="pending").iterator():
        stamps = [(getattr(jr, at), getattr(jr, by + "_id")) for at, by in _STAMPS]
        stamped = [s for s in stamps if s[0] is not None]
        if not stamped:
            continue
        jr.status_changed_at, jr.status_changed_by_id = max(stamped, key=lambda s: s[0])
        jr.save(update_fields=["status_changed_at", "status_changed_by"])


class Migration(migrations.Migration):
    dependencies = [
        ("community", "0132_member_restored_email_template"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="joinrequest",
            name="status_changed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="joinrequest",
            name="status_changed_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="status_changed_join_requests",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.RunPython(fill_status_changed, migrations.RunPython.noop),
    ]

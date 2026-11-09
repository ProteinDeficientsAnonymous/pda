import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.db.models import F

_STAMPS = {
    "tentative": ("tentative_at", "tentative_by"),
    "approved": ("approved_at", "approved_by"),
    "rejected": ("rejected_at", "rejected_by"),
}


def fill_status_changed(apps, schema_editor):
    JoinRequest = apps.get_model("community", "JoinRequest")
    # Only the current status's stamp counts; a pending row's stamps describe an earlier status.
    for status, (at, by) in _STAMPS.items():
        JoinRequest.objects.filter(status=status).update(
            status_changed_at=F(at), status_changed_by=F(by)
        )


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

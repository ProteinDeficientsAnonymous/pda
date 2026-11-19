import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

STAMPS = ["tentative", "approved", "rejected"]


def _stamp_fk(stamp):
    # Django stops emulating SET_NULL once the field leaves state, so a user delete can't hit the FK.
    return migrations.AlterField(
        model_name="joinrequest",
        name=f"{stamp}_by",
        field=models.ForeignKey(
            blank=True,
            db_constraint=False,
            null=True,
            on_delete=django.db.models.deletion.SET_NULL,
            related_name=f"{stamp}_join_requests",
            to=settings.AUTH_USER_MODEL,
        ),
    )


class Migration(migrations.Migration):
    dependencies = [
        ("community", "0134_backfill_joinrequest_status_changed"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    # State-only removal: the columns stay until 0136 drops them.
    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RemoveField(model_name="joinrequest", name=f"{stamp}_{suffix}")
                for stamp in STAMPS
                for suffix in ("at", "by")
            ],
            database_operations=[_stamp_fk(stamp) for stamp in STAMPS],
        ),
    ]

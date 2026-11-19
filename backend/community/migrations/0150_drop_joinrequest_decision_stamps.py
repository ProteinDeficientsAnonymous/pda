import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

STAMPS = ["tentative", "approved", "rejected"]


def _legacy_fields(stamp):
    return {
        f"{stamp}_at": models.DateTimeField(blank=True, null=True),
        f"{stamp}_by": models.ForeignKey(
            blank=True,
            db_constraint=False,
            null=True,
            on_delete=django.db.models.deletion.SET_NULL,
            related_name=f"{stamp}_join_requests",
            to=settings.AUTH_USER_MODEL,
        ),
    }


LEGACY_FIELDS = {name: field for stamp in STAMPS for name, field in _legacy_fields(stamp).items()}


class Migration(migrations.Migration):
    dependencies = [
        ("community", "0135_remove_joinrequest_decision_stamps"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    # Re-add the fields to state only so RemoveField can drop the columns, SQLite included.
    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.SeparateDatabaseAndState(
                    state_operations=[
                        migrations.AddField(model_name="joinrequest", name=name, field=field)
                        for name, field in LEGACY_FIELDS.items()
                    ],
                ),
                *[
                    migrations.RemoveField(model_name="joinrequest", name=name)
                    for name in LEGACY_FIELDS
                ],
            ],
        ),
    ]

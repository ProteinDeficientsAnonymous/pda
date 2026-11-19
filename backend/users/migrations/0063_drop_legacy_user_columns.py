from django.db import migrations, models

LEGACY_FIELDS = {
    "is_member": models.BooleanField(default=False, db_default=False, db_index=True),
    "is_paused": models.BooleanField(default=False, db_default=False),
}


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0061_remove_user_is_paused"),
    ]

    # Re-add the fields to state only so RemoveField can drop the columns, SQLite included.
    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.SeparateDatabaseAndState(
                    state_operations=[
                        migrations.AddField(model_name="user", name=name, field=field)
                        for name, field in LEGACY_FIELDS.items()
                    ],
                ),
                *[migrations.RemoveField(model_name="user", name=name) for name in LEGACY_FIELDS],
            ],
        ),
    ]

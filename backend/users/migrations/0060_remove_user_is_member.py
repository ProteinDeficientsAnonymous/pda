from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0059_backfill_membership_status"),
    ]

    # The column stays, with a DB default for inserts that omit it, until 0062 drops it.
    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RemoveField(model_name="user", name="is_member"),
            ],
            database_operations=[
                migrations.AlterField(
                    model_name="user",
                    name="is_member",
                    field=models.BooleanField(default=False, db_default=False, db_index=True),
                ),
            ],
        ),
    ]

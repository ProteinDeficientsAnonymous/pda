from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0060_remove_user_is_member"),
    ]

    # The column stays, with a DB default for inserts that omit it, until 0062 drops it.
    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RemoveField(model_name="user", name="is_paused"),
            ],
            database_operations=[
                migrations.AlterField(
                    model_name="user",
                    name="is_paused",
                    field=models.BooleanField(default=False, db_default=False),
                ),
            ],
        ),
    ]

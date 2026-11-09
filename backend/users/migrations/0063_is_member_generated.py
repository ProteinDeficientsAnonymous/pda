from django.db import migrations, models

# A stored column can't be altered into a generated one, so drop and re-add it.


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0062_guidelines_paused_status"),
    ]

    operations = [
        migrations.RemoveField(model_name="user", name="is_member"),
        migrations.AddField(
            model_name="user",
            name="is_member",
            field=models.GeneratedField(
                db_index=True,
                db_persist=True,
                expression=models.Q(
                    ("membership_status", "member"),
                    models.Q(
                        ("attendance_paused_at__isnull", True),
                        ("membership_status", "guidelines_paused"),
                    ),
                    _connector="OR",
                ),
                output_field=models.BooleanField(),
            ),
        ),
    ]

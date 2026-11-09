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
                expression=models.Q(("membership_status__in", ("member", "guidelines_paused"))),
                output_field=models.BooleanField(),
            ),
        ),
    ]

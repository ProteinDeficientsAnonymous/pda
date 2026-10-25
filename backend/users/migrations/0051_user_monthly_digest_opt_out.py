from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0050_user_attendance_nudge_opt_out"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="monthly_digest_opt_out",
            field=models.BooleanField(default=False),
        ),
    ]

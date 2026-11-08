from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0053_carry_weekly_digest_opt_out_to_monthly"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="host_digest_last_sent_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="user",
            name="host_digest_opt_out",
            field=models.BooleanField(default=False),
        ),
    ]

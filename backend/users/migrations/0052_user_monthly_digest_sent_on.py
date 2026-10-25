from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0051_user_monthly_digest_opt_out"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="monthly_digest_sent_on",
            field=models.DateField(blank=True, null=True),
        ),
    ]

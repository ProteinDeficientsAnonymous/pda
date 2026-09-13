from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0046_user_veganversary_privacy"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="user",
            name="veganversary_shoutout_opt_out",
        ),
        migrations.AddField(
            model_name="user",
            name="veganversary_shoutout_consent",
            field=models.BooleanField(default=False),
        ),
    ]

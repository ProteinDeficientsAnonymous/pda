from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0045_user_veganversary"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="show_veganversary",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="user",
            name="veganversary_shoutout_opt_out",
            field=models.BooleanField(default=False),
        ),
    ]

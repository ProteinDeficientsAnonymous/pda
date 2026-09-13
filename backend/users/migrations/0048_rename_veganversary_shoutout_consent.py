from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0047_user_veganversary_shoutout_consent"),
    ]

    operations = [
        migrations.RenameField(
            model_name="user",
            old_name="veganversary_shoutout_consent",
            new_name="veganversary_shoutout_opt_in",
        ),
    ]

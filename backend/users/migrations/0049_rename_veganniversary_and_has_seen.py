from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0048_rename_veganversary_shoutout_consent"),
    ]

    operations = [
        migrations.RenameField(
            model_name="user",
            old_name="veganversary_month",
            new_name="veganniversary_month",
        ),
        migrations.RenameField(
            model_name="user",
            old_name="veganversary_day",
            new_name="veganniversary_day",
        ),
        migrations.RenameField(
            model_name="user",
            old_name="veganversary_year",
            new_name="veganniversary_year",
        ),
        migrations.RenameField(
            model_name="user",
            old_name="show_veganversary",
            new_name="show_veganniversary",
        ),
        migrations.RenameField(
            model_name="user",
            old_name="veganversary_shoutout_opt_in",
            new_name="veganniversary_shoutout_opt_in",
        ),
        migrations.AddField(
            model_name="user",
            name="has_seen_veganniversary",
            field=models.BooleanField(default=False),
        ),
    ]

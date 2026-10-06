from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0045_user_has_joined_whatsapp"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="veganniversary_day",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="user",
            name="veganniversary_month",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="user",
            name="veganniversary_year",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="user",
            name="show_veganniversary",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="user",
            name="veganniversary_shoutout_opt_in",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="user",
            name="has_seen_veganniversary",
            field=models.BooleanField(default=False),
        ),
    ]

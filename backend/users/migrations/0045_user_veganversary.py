from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0044_user_calendar_feed_excluded_types"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="veganversary_day",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="user",
            name="veganversary_month",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="user",
            name="veganversary_year",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
    ]
